from dataclasses import dataclass


@dataclass
class Order:
    count: int
    market_id: str
    price: int
    side: str
