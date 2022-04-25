from time import sleep

from classes.profiles import MarketProfile
from config.custom import get_strategies

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

        self.authenticate()

        # Produce a list of markets to monitor.
        self.active_markets = set([m.market_ticker for m in self.strategy.markets])
        self.validate_markets()

        if operation == "make":
            self.make()
        elif operation == "clean":
            self.cleanup()

    def authenticate(self) -> None:
        pass

    def validate_markets(self) -> None:
        """
        Confirm that all specified markets exist and
        are open.
        """
        pass

    def make(self) -> None:
        self.cleanup()

        while True:
            for market in self.strategy.markets:
                self.manage_orders(market)
                sleep(MARKET_TIMEOUT_SECS)
            sleep(POLLING_FREQUENCY_SECS)

    def cleanup(self) -> None:
        """
        Remove any existing resting orders.
        """
        pass

    def manage_orders(self, market: MarketProfile) -> None:
        pass
