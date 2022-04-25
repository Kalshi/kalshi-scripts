from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from classes.environment import Environment


class Distribution(Enum):
    LINEAR = 1


@dataclass
class MarketProfile:
    market_ticker: str
    max_exposure_cents: int
    spread: Optional[int]
    depth: Optional[int]
    fair_value: Optional[int]
    clear_time: Optional[str]
    distribution: Distribution


@dataclass
class StrategyProfile:
    env: Environment
    markets: List[MarketProfile]
