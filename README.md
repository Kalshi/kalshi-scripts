# Kalshi Scripts

### Background

This repository contains a collection of scripts for trading on [Kalshi](https://kalshi.com), an events exchange. The scripts make use of Kalshi's public API which is documented [here](https://kalshi-public-docs.s3.amazonaws.com/KalshiAPI.html).

### General Setup

1. Install [Poetry](https://python-poetry.org/).
2. Install Python 3.9 and Python 3.9 Distutils.
3. Run `poetry install` in the root directory.
4. Create a new file in the root called `credentials.yaml` with the following structure:

```
prod:
  email: ""
  password: ""
  advanced_api: false
demo:
  email: ""
  password: ""
  advanced_api: false
```

5. Fill in your credentials in `credentials.yaml`. Change `advanced_api` to `true` only if you know your account has access.

## Market Making Script

This script serves as a generic baseline for market making on Kalshi. It allows you to produce `profiles`. For every `profile`, you can define a list of markets where you'd like the script to manage your positions.

### Setup

1. Copy `market_maker/config/base.py` to create a new file: `market_maker/config/custom.py`.
2. Update `custom.py` to your specifications. Details about the options available are in the file itself.

### Running the Script

1. To run the script, execute `poetry run python main.py make [profile]`. If no `profile` is provided, the script will assume the desired profile is `default`.
2. If you exit the script early and would like to clear resting orders in the affected markets, execute `poetry run python main.py clear [profile]`.

Note: It is not recommended to manually place orders on markets affected by the script. This could inadvertently cause you to exceed your specified exposure limits.
