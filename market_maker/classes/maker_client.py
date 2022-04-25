from classes.environment import Environment
from classes.kalshi_client import KalshiClient


class MakerClient(KalshiClient):
    def __init__(
        self, env: Environment, email: str, password: str, use_advanced_api: bool
    ):
        super().__init__(env, email, password, use_advanced_api)
        self.markets_url = "/v1/markets"

    def get_user_url(self) -> str:
        return "/v1/users/" + self.user_id

    def get_market_url(self, ticker: str) -> str:
        return "/v1/markets_by_ticker/" + ticker
