from datetime import datetime
from time import sleep
from typing import Dict, List, Set, Tuple

import pandas as pd

from market_maker.classes.maker_client import MakerClient
from market_maker.classes.order import Order
from market_maker.classes.profiles import MarketProfile
from market_maker.config.custom import get_strategies
from market_maker.utils.credentials import get_credentials

# Increasing the polling frequency could lead to
# rate limiting.
POLLING_FREQUENCY_SECS = 15
MARKET_TIMEOUT_SECS = 1


class MarketMaker:
    def __init__(self, operation: str, profile: str):
        self.profile = profile

        print("Running Strategy:", profile)
        strategies = get_strategies()

        if profile not in strategies:
            print("No strategy found with this name.")
            return

        self.strategy = strategies[profile]
        print(self.strategy)
        print()

        self.expiration_ts = {
            market.market_ticker: int(datetime.timestamp(market.clear_time))
            if market.clear_time is not None
            else 0
            for market in self.strategy.markets
        }

        self.credentials = get_credentials(self.strategy.env)
        self.client = MakerClient(
            self.strategy.env,
            self.credentials.email,
            self.credentials.password,
            self.credentials.advanced_api,
        )

        # Produce a list of markets to monitor.
        self.all_active_markets = self.client.get_public_markets()
        self.last_positions: Dict[str, int] = {}
        self.fair_values: Dict[str, int] = {}
        self.last_snipes: Dict[str, datetime] = {}

        self.active_market_ids: Set[str] = set()
        self.market_ids_to_profiles: Dict[str, MarketProfile] = {}
        for market in self.strategy.markets:
            row = self.all_active_markets[
                self.all_active_markets["ticker_name"] == market.market_ticker
            ]
            if len(row) == 1:
                market_id = row.iloc[0]["id"]
                self.active_market_ids.add(market_id)
                self.market_ids_to_profiles[market_id] = market

        if operation == "make":
            self.make()
        elif operation == "clear":
            self.cleanup()

    def make(self) -> None:
        """
        Maintain resting orders per specifications.
        """
        self.cleanup()

        while True:
            print("Managing active markets:", self.active_market_ids)
            positions = self.client.get_positions()
            for market_id in self.active_market_ids:
                self.manage_orders(market_id, positions)
                sleep(MARKET_TIMEOUT_SECS)
            sleep(POLLING_FREQUENCY_SECS)

    def cleanup(self) -> None:
        """
        Remove any existing resting orders.
        """
        for market_id in self.active_market_ids:
            orders = self.client.get_market_orders(market_id=market_id)
            if len(orders) == 0:
                continue
            print("Clearing", len(orders), "orders from", market_id)
            order_ids = list(orders["order_id"])

            self.client.clear_orders(order_ids)
            sleep(MARKET_TIMEOUT_SECS)

    def manage_orders(self, market_id: str, positions: pd.DataFrame) -> None:
        profile = self.market_ids_to_profiles[market_id]

        market_details = self.client.get_market(market_id)
        orders = self.client.get_market_orders(market_id=market_id)
        order_ids: List[str] = list(orders["order_id"]) if len(orders) > 0 else []

        current_time = datetime.now()
        if profile.clear_time is not None and current_time > profile.clear_time:
            print("Clearing:", profile.market_ticker, "(passed clear time)")
            self.client.clear_orders(order_ids)
            self.active_market_ids.remove(market_id)
            return
        elif market_details["status"] != "active":
            print("Stopping:", profile.market_ticker, "(closed)")
            self.active_market_ids.remove(market_id)
            return

        # Skip a market that was recently sniped.
        if (
            market_id in self.last_snipes
            and profile.snipe_timeout_seconds is not None
            and (datetime.now() - self.last_snipes[market_id]).total_seconds()
            < profile.snipe_timeout_seconds
        ):
            return

        # If the market has never been traded on, skip it.
        if market_details["volume"] == 0:
            return

        spread_size = market_details["yes_ask"] - market_details["yes_bid"]
        spread_midpoint = market_details["yes_bid"] + spread_size / 2

        # If the spread is currently too large, skip the market.
        if profile.max_spread is not None and spread_size > profile.max_spread:
            return

        # Reset fair value in response to a snipe.
        if (
            market_id in self.fair_values
            and abs(self.fair_values[market_id] - spread_midpoint) > spread_size / 2
        ):
            self.fair_values.pop(market_id)
            self.last_positions.pop(market_id)
            self.last_snipes[market_id] = datetime.now()

        position = positions[positions["market_id"] == market_id]
        position_count = position.iloc[0]["position"] if len(position) > 0 else 0

        if market_id not in self.fair_values:
            self.fair_values[market_id] = spread_midpoint
            self.last_positions[market_id] = position_count

        changed_position = position_count - self.last_positions[market_id]
        fair_value_change = -int(changed_position / profile.price_stickyness)
        self.fair_values[market_id] += fair_value_change
        self.last_positions[market_id] += fair_value_change * profile.price_stickyness

        desired_yes_book, desired_no_book = self.produce_book(
            profile, position, orders, int(self.fair_values[market_id])
        )
        current_yes_book, current_no_book = self.client.get_indiv_orderbook(market_id)

        consistent_yes: Set[int] = set()
        consistent_no: Set[int] = set()

        orders_to_cancel: List[str] = []
        for price in current_yes_book.index:
            current_resting = current_yes_book.loc[price]["q"]
            if current_resting > 0:
                if (
                    price not in desired_yes_book
                    or current_resting != desired_yes_book[price]
                ):
                    orders_to_cancel += list(
                        orders[orders["price"] == price]["order_id"]
                    )
                else:
                    consistent_yes.add(price)

        for price in current_no_book.index:
            current_resting = current_no_book.loc[price]["q"]
            if current_resting > 0:
                if (
                    price not in desired_no_book
                    or current_resting != desired_no_book[price]
                ):
                    orders_to_cancel += list(
                        orders[orders["price"] == price]["order_id"]
                    )
                else:
                    consistent_no.add(price)

        self.client.clear_orders(orders_to_cancel)

        new_orders: List[Order] = []
        for price, count in desired_yes_book.items():
            if price in consistent_yes:
                continue
            else:
                new_orders.append(
                    Order(
                        count=count,
                        expiration_unix_ts=self.expiration_ts[profile.market_ticker],
                        market_id=market_id,
                        price=price,
                        side="yes",
                    )
                )
        for price, count in desired_no_book.items():
            if price in consistent_no:
                continue
            else:
                new_orders.append(
                    Order(
                        count=count,
                        expiration_unix_ts=self.expiration_ts[profile.market_ticker],
                        market_id=market_id,
                        price=price,
                        side="no",
                    )
                )

        try:
            self.client.post_orders(new_orders)
        except Exception as e:
            print("Failed to place orders in", profile.market_ticker)
            print(str(e))

    def produce_book(
        self,
        profile: MarketProfile,
        position: pd.DataFrame,
        orders: pd.DataFrame,
        fair_value: int,
    ) -> Tuple[Dict[int, int], Dict[int, int]]:
        exposure_cents = 0 if len(position) == 0 else position.iloc[0]["position_cost"]
        holds_yes = len(position) > 0 and position.iloc[0]["position"] > 0

        yes_order_exposure = 0
        no_order_exposure = 0
        if len(orders) > 0:
            yes_orders = orders[orders["is_yes"]]
            yes_order_exposure = (
                yes_orders["price"] * yes_orders["remaining_count"]
            ).sum()
            no_orders = orders[orders["is_yes"] is False]
            no_order_exposure = (
                no_orders["price"] * no_orders["remaining_count"]
            ).sum()

        desired_yes_book: Dict[int, int] = {}
        desired_no_book: Dict[int, int] = {}

        # Handle yes side
        cumulative_yes_exposure = exposure_cents if holds_yes else -exposure_cents
        cumulative_yes_exposure += yes_order_exposure
        yes_orders_per_level = int(
            profile.instant_liquidity_cents / profile.depth / fair_value
        )
        topOfYes = int(fair_value - (profile.spread - 1) / 2)
        for i in range(profile.depth):
            price = topOfYes - i
            if (
                price < 1
                or (profile.max_yes_price is not None and price > profile.max_yes_price)
                or (profile.min_yes_price is not None and price < profile.min_yes_price)
            ):
                break
            order_price_cents = price * yes_orders_per_level
            if (
                order_price_cents + cumulative_yes_exposure
            ) > profile.max_exposure_cents:
                break
            desired_yes_book[price] = yes_orders_per_level

        # Handle no side
        no_fair_value = 100 - fair_value
        cumulative_no_exposure = -exposure_cents if holds_yes else exposure_cents
        cumulative_no_exposure += no_order_exposure
        no_orders_per_level = int(
            profile.instant_liquidity_cents / profile.depth / no_fair_value
        )
        topOfNo = int(no_fair_value - (profile.spread - 1) / 2)
        for i in range(profile.depth):
            price = topOfNo - i
            yes_price = 100 - price
            if (
                price < 1
                or (
                    profile.max_yes_price is not None
                    and yes_price > profile.max_yes_price
                )
                or (
                    profile.min_yes_price is not None
                    and yes_price < profile.min_yes_price
                )
            ):
                break
            order_price_cents = price * no_orders_per_level
            if (
                order_price_cents + cumulative_no_exposure
            ) > profile.max_exposure_cents:
                break
            desired_no_book[price] = no_orders_per_level

        return desired_yes_book, desired_no_book
