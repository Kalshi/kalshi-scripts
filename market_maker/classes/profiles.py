from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from market_maker.classes.environment import Environment


class Distribution(Enum):
    LINEAR = 1


@dataclass
class MarketProfile:
    market_ticker: str
    instant_liquidity_cents: int
    max_exposure_cents: int
    price_stickyness: int
    spread: int
    depth: int
    max_spread: Optional[int]
    max_yes_price: Optional[int]
    min_yes_price: Optional[int]
    snipe_timeout_seconds: Optional[int]
    clear_time: Optional[datetime]
    distribution: Distribution


@dataclass
class StrategyProfile:
    env: Environment
    markets: List[MarketProfile]
