import yaml

from market_maker.classes.credentials import Credentials
from market_maker.classes.environment import Environment


def get_credentials(env: Environment) -> Credentials:
    with open("./credentials.yaml") as f:
        data = yaml.safe_load(f.read())[env.name.lower()]
    return Credentials(data["email"], data["password"], data["advanced_api"])
