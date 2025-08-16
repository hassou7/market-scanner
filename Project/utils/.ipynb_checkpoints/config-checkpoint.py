# utils/config.py

# Telegram bot tokens for different strategies
TELEGRAM_TOKENS = {
    "volume_surge": "7553154813:AAG4KU9eAEhSpFRgIgNR5vpG05mT8at4Udw",
    "start_trend": "7501317114:AAHqd8BYNqR81zWEHAuwQhKji1fOM9HxjdQ",
    "weakening_trend": "7837067804:AAE1H2XWMlwvogCdhQ7vJpufv6VpXaBFg8Q",
    "confluence": "8066329517:AAHVr6kufZWe8UqCKPfmsRhSPleNlt_7G-g",
    "breakout": "8346095660:AAF0oUOfcMVsrbvTmklOnO-9KohlUH5JmqE",
}

# Telegram users configuration
TELEGRAM_USERS = {
    "default": {"name": "Houssem", "chat_id": "375812423"},
    "user1": {"name": "Samed", "chat_id": "2008960887"},
    "user2": {"name": "Moez", "chat_id": "6511370226"}, 
}

# Strategy to channel mapping
STRATEGY_CHANNELS = {
    "breakout_bar": "start_trend",
    "stop_bar": "start_trend",
    "reversal_bar": "weakening_trend",
    "volume_surge": "volume_surge",
    "weak_uptrend": "weakening_trend",
    "pin_down": "weakening_trend",
    "confluence": "confluence",
    "start_bar": "start_trend",
    "loaded_bar": "volume_surge",
    "test_bar": "weakening_trend",
    "consolidation": "start_trend",           # NEW: Consolidation pattern detection
    "consolidation_breakout": "start_trend",  # NEW: Consolidation breakout detection
    "hbs_breakout": "breakout"              # NEW: HBS (consolidation + confluence) breakout
}

# Volume thresholds for different timeframes
VOLUME_THRESHOLDS = {
    "1w": 300000,  # Weekly volume threshold in USD
    "4d": 200000,  # 4-day volume threshold in USD
    "3d": 150000,  # 3-day volume threshold in USD
    "2d": 100000,  # 2-day volume threshold in USD
    "1d": 50000,   # Daily volume threshold in USD
    "4h": 20000    # 4-hour volume threshold in USD
}

def get_telegram_config(strategies, users):
    """
    Get Telegram configuration for specified strategies and users
    
    Args:
        strategies (list): List of strategies to get config for
        users (list): List of users to notify
        
    Returns:
        dict: Telegram configuration
    """
    config = {}
    
    for strategy in strategies:
        channel = STRATEGY_CHANNELS.get(strategy)
        if channel and channel in TELEGRAM_TOKENS:
            token = TELEGRAM_TOKENS[channel]
            chat_ids = []
            
            for user in users:
                if user in TELEGRAM_USERS:
                    chat_ids.append(TELEGRAM_USERS[user]["chat_id"])
            
            if chat_ids:
                config[strategy] = {
                    'token': token,
                    'chat_ids': chat_ids
                }
    
    return config