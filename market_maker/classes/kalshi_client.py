import json
from datetime import datetime as dt
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import requests
from classes.environment import Environment

hosts: Dict[Environment, str] = {
    Environment.DEMO: "https://demo-api.kalshi.co/",
    Environment.PROD: "https://trading-api.kalshi.com/",
}


class HttpError(Exception):
    """Represents an HTTP error with reason and status code."""

    def __init__(self, reason: str, status: int):
        super().__init__(reason)
        self.reason = reason
        self.status = status

    def __str__(self) -> str:
        return "HttpError(%d %s)" % (self.status, self.reason)


def authenticate_call(call: Any) -> Callable:
    def authenticated(self: "KalshiClient", *args: Any, **kwargs: Any) -> Any:
        time = dt.now()
        if (
            self.last_login is None
            or time - self.last_login > self.reauthenticate_duration
        ):
            self.login()
            self.last_login = time
        return call(self, *args, **kwargs)

    return authenticated


class KalshiClient:
    """A simple client that allows utils to call authenticated Kalshi API endpoints."""

    def __init__(
        self,
        env: Environment,
        email: str,
        password: str,
    ):
        self.env = env
        self.host = hosts[self.env]

        self.email = email
        self.password = password

        self.token = ""
        self.user_id = ""
        self.last_login: Optional[dt] = None

        self.reauthenticate_duration = timedelta(hours=5)

    def raise_if_bad_response(self, response: requests.Response) -> None:
        if not response.ok:
            raise HttpError(response.reason, response.status_code)

    def login(self) -> None:
        login_json = json.dumps({"email": self.email, "password": self.password})
        response = requests.post(
            self.host + "/v1/log_in",
            data=login_json,
            headers={
                "Content-Type": "application/json",
            },
        )

        self.raise_if_bad_response(response)

        result = response.json()
        self.token = result["token"]
        self.user_id = result["user_id"]

    def request_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": self.user_id + " " + self.token,
        }

    @authenticate_call
    def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """GETs from an authenticated Kalshi HTTP endpoint.

        Returns the response body. Raises an HttpError on non-2XX results."""
        response = requests.get(
            self.host + path, headers=self.request_headers(), params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    @authenticate_call
    def post(self, path: str, body: Dict[str, Any]) -> Any:
        """POSTs to an authenticated Kalshi HTTP endpoint.

        Returns the response body. Raises an HttpError on non-2XX results.
        """
        response = requests.post(
            self.host + path, data=json.dumps(body), headers=self.request_headers()
        )
        self.raise_if_bad_response(response)
        return response.json()

    @authenticate_call
    def delete(self, path: str, body: Dict[str, Any]) -> Any:
        """DELETEs at an authenticated Kalshi HTTP endpoint.

        Returns the response body. Raises an HttpError on non-2XX results.
        """
        response = requests.delete(
            self.host + path, data=json.dumps(body), headers=self.request_headers()
        )
        self.raise_if_bad_response(response)
        return response.json()
