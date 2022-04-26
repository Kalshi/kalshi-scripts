from dataclasses import dataclass


@dataclass
class Order:
    count: int
    expiration_unix_ts: int
    market_id: str
    price: int
    side: str
    sell_position_capped: bool = False
