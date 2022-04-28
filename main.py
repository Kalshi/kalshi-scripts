import sys
from pathlib import Path

from market_maker.classes.market_maker import MarketMaker

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please enter an operation.")

    operation = sys.argv[1]
    profile = "default" if len(sys.argv) == 2 else sys.argv[2]

    auth = Path("./credentials.yaml")
    if not auth.is_file():
        print("Please create an authentication file as specified in the README.")

    MarketMaker(operation, profile)
