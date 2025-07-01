#utils/config.py

# Volume thresholds for different timeframes (in USD)
VOLUME_THRESHOLDS = {
    "1w": 300000,  # Weekly
    "2d": 100000,  # 2-day
    "1d": 50000,   # Daily
    "4h": 20000    # 4-hour
}

TELEGRAM_TOKENS = {
    "volume_surge": "7553154813:AAG4KU9eAEhSpFRgIgNR5vpG05mT8at4Udw",
    "start_trend": "7501317114:AAHqd8BYNqR81zWEHAuwQhKji1fOM9HxjdQ",
    "weakening_trend": "7837067804:AAE1H2XWMlwvogCdhQ7vJpufv6VpXaBFg8Q",
    "confluence": "8066329517:AAHVr6kufZWe8UqCKPfmsRhSPleNlt_7G-g"
}

TELEGRAM_USERS = {
    "default": {"name": "Houssem", "chat_id": "375812423"},
    "user1": {"name": "Samed", "chat_id": "2008960887"},
    "user2": {"name": "Moez", "chat_id": "6511370226"}, 
}

STRATEGY_CHANNELS = {
    "breakout_bar": "start_trend",
    "stop_bar": "start_trend",
    "reversal_bar": "weakening_trend",
    "volume_surge": "volume_surge",
    "weak_uptrend": "weakening_trend",
    "pin_down": "weakening_trend",
    "confluence": "confluence",
    "start_bar": "start_trend",
    "loaded_bar":"volume_surge",
    "test_bar":"weakening_trend",
}

def get_telegram_config(strategies, users=["default"]):
    config = {}
    for strategy in strategies:
        channel = STRATEGY_CHANNELS.get(strategy)
        if channel:
            config[strategy] = {
                "token": TELEGRAM_TOKENS.get(channel),
                "chat_ids": [TELEGRAM_USERS[user]["chat_id"] for user in users if user in TELEGRAM_USERS]
            }
    return config