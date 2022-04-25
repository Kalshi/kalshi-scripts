from dataclasses import dataclass


@dataclass
class Credentials:
    email: str
    password: str
    advanced_api: bool
