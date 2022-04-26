from dataclasses import asdict
from time import sleep
from typing import List

import numpy as np
import pandas as pd
from classes.environment import Environment
from classes.kalshi_client import KalshiClient
from classes.order import Order


class MakerClient(KalshiClient):
    def __init__(
        self, env: Environment, email: str, password: str, use_advanced_api: bool
    ):
        super().__init__(env, email, password, use_advanced_api)

    def get_market_orders(self, market_id: str) -> pd.DataFrame:
        orders_url = self.get_user_url() + "/orders"
        dictr = self.get(
            orders_url, params={"market_id": market_id, "status": "resting"}
        )

        recs = dictr["orders"]
        df = pd.json_normalize(recs)
        return df

    def get_orderbook(self, market_id: str) -> pd.DataFrame:
        base_url = self.get_market_url(market_id)
        order_book_url = base_url + "/order_book"
        dictr = self.get(order_book_url)

        yesData = dictr["order_book"]["yes"]
        noData = dictr["order_book"]["no"]

        yesDf = pd.DataFrame(yesData, columns=["p", "q"])
        yesDf = yesDf.sort_values("p", ascending=False).reset_index(drop=True)

        noDf = pd.DataFrame(noData, columns=["p", "q"])
        noDf = noDf.sort_values("p", ascending=False).reset_index(drop=True)

        return yesDf.set_index("p").reindex(
            np.arange(1, 100, 1), fill_value=0
        ), noDf.set_index("p").reindex(np.arange(1, 100, 1), fill_value=0)

    def get_indiv_orderbook(self, market_id: str) -> pd.DataFrame:
        orders = self.get_market_orders(market_id=market_id)

        if len(orders):
            pseudo_book = (
                orders.groupby(["price", "is_yes"])
                .sum()[["remaining_count"]]
                .reset_index()
                .rename(columns={"remaining_count": "q", "price": "p"})
            )
            noDf = pseudo_book.query("is_yes==False")[["p", "q"]].set_index("p")
            yesDf = pseudo_book.query("is_yes==True")[["p", "q"]].set_index("p")
            return yesDf.reindex(np.arange(1, 100, 1), fill_value=0), noDf.reindex(
                np.arange(1, 100, 1), fill_value=0
            )

        noDf = pd.DataFrame(0, index=np.arange(1, 100, 1), columns=["q"])
        yesDf = pd.DataFrame(0, index=np.arange(1, 100, 1), columns=["q"])

        return yesDf, noDf

    def clear_orders(self, market_id: str) -> pd.DataFrame:
        orders = self.get_market_orders(market_id=market_id)

        if self.use_advanced_api and len(orders):
            batched_url = self.user_url + "/batch_orders"
            n = min(19, len(orders))
            order_ids = list(orders.order_id)
            grouped_orders_list = [
                order_ids[i : i + n] for i in range(0, len(order_ids), n)
            ]
            for group_orders in grouped_orders_list:
                post_dict = {"ids": group_orders}
                self.delete(path=batched_url, body=post_dict)
                sleep(0.3)
        elif len(orders):
            order_url_base = self.user_url + "/orders/"
            order_ids = list(orders.order_id)
            for order_id in order_ids:
                self.delete(path=order_url_base + order_id, body={})
                sleep(0.3)

    def post_orders(self, orders: List[Order]) -> pd.DataFrame:
        recs: list = []
        if self.use_advanced_api:
            batched_url = self.user_url + "/batch_orders"
            n = min(19, len(orders))

            grouped_orders_list = [orders[i : i + n] for i in range(0, len(orders), n)]
            for group_orders in grouped_orders_list:
                orders_body = {"orders": [asdict(o) for o in group_orders]}
                dictr = self.post(path=batched_url, body=orders_body)
                recs += dictr["orders"]
        else:
            order_url_base = self.user_url + "/orders"
            for order in orders:
                order_body = {"order": asdict(order)}
                dictr = self.post(path=order_url_base, body=order_body)
                recs.append(dictr["order"])

        df = pd.json_normalize(recs)
        return df
