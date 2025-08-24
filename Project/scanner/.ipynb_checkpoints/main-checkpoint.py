# Scanner/main.py

import asyncio
import logging
from tqdm.asyncio import tqdm
from telegram.ext import Application
from datetime import datetime
import pandas as pd
import numpy as np
from custom_strategies import detect_volume_surge, detect_weak_uptrend, detect_pin_down, detect_confluence, detect_consolidation, detect_consolidation_breakout, detect_channel_breakout, detect_sma50_breakout
from breakout_vsa import vsa_detector, breakout_bar_vsa, stop_bar_vsa, reversal_bar_vsa, start_bar_vsa, loaded_bar_vsa, test_bar_vsa
from utils.config import VOLUME_THRESHOLDS
import os

from exchanges.sf_kucoin_client import SFKucoinClient
from exchanges.sf_mexc_client import SFMexcClient

# Function to check if progress bars should be disabled
def should_disable_progress():
    return os.environ.get("DISABLE_PROGRESS") == "1"
    
kline_cache = {}

class UnifiedScanner:
    def __init__(self, exchange_client, strategies, telegram_config=None, min_volume_usd=None):
        self.exchange_client = exchange_client
        self.strategies = strategies
        self.telegram_config = telegram_config or {}
        
        timeframe = exchange_client.timeframe
        self.min_volume_usd = min_volume_usd if min_volume_usd is not None else VOLUME_THRESHOLDS.get(timeframe, 50000)
        
        self.batch_size = 10
        self.telegram_apps = {}
        self.exchange_name = self._get_exchange_name()
        self.strategy_titles = {
            'volume_surge': 'Sudden Volume Surge',
            'weak_uptrend': 'Weak Uptrend Detection',
            'pin_down': 'Pin Down Detection',
            'confluence': 'Confluence Signal',
            'consolidation': 'Consolidation Pattern',
            'consolidation_breakout': 'Consolidation Breakout Pattern',
            'channel_breakout': 'Channel Breakout Pattern',
            'sma50_breakout': '50SMA Breakout',
            'hbs_breakout': 'HBS Breakout', 
            'breakout_bar': 'Breakout Bar',
            'stop_bar': 'Stop Bar',
            'reversal_bar': 'Reversal Bar',
            'start_bar': 'Start Bar',
            'loaded_bar': 'Loaded Bar',
            'test_bar': 'Test Bar'
        }
        self.vsa_detectors = {
            'breakout_bar': breakout_bar_vsa,
            'stop_bar': stop_bar_vsa,
            'reversal_bar': reversal_bar_vsa,
            'start_bar': start_bar_vsa,
            'loaded_bar': loaded_bar_vsa,
            'test_bar': test_bar_vsa,
        }

    def _get_exchange_name(self):
        class_name = self.exchange_client.__class__.__name__
        mappings = {
            "MexcFuturesClient": "MEXC Futures",
            "GateioFuturesClient": "Gateio Futures",
            "BinanceFuturesClient": "Binance Futures",
            "BybitFuturesClient": "Bybit Futures",
            "BinanceSpotClient": "Binance Spot",
            "BybitSpotClient": "Bybit Spot",
            "GateioSpotClient": "Gateio Spot",
            "KucoinSpotClient": "KuCoin Spot",
            "MexcSpotClient": "MEXC Spot",
            "SFKucoinClient": "KuCoin Spot",
            "SFMexcClient": "MEXC Spot"
        }
        return mappings.get(class_name, class_name.replace("Client", ""))

    async def init_session(self):
        await self.exchange_client.init_session()
        for strategy, config in self.telegram_config.items():
            if 'token' in config and config['token'] and strategy not in self.telegram_apps:
                self.telegram_apps[strategy] = Application.builder().token(config['token']).build()

    async def close_session(self):
        await self.exchange_client.close_session()
        for app in self.telegram_apps.values():
            if hasattr(app, 'running') and app.running:
                await app.stop()
                await app.shutdown()
        self.telegram_apps = {}

    async def send_telegram_message(self, strategy, results):
        if not results or strategy not in self.telegram_config or strategy not in self.telegram_apps:
            return
        try:
            chat_ids = self.telegram_config[strategy].get('chat_ids', [])
            if not chat_ids:
                return
            timeframe = self.exchange_client.timeframe
            title = self.strategy_titles.get(strategy, strategy.replace('_', ' ').title())
            
            # Create the header message
            header = f"🚨 {title} - {self.exchange_name} {timeframe.upper()}\n\n"
            
            # Create a list to store complete signal messages
            signal_messages = []
            
            # Generate a complete message for each signal
            for result in results:
                symbol = result.get('symbol', 'Unknown')
                tv_symbol = symbol.replace('_', '').replace('-', '')
                tv_timeframe = timeframe.upper() if timeframe.upper() != "4H" else "240"
                suffix = ".P" if "Futures" in self.exchange_name else ""
                tv_exchange = self.exchange_name.upper().replace(" ", "").replace("FUTURES", "").replace("SPOT", "")
                tv_link = f"https://www.tradingview.com/chart/?symbol={tv_exchange}:{tv_symbol}{suffix}&interval={tv_timeframe}"
                date = result.get('date') or result.get('timestamp')
                bar_status = "CURRENT BAR" if result.get('current_bar') else "Last Closed Bar"
                volume_period = "Weekly" if timeframe == "1w" else \
                                "4-Day" if timeframe == "4d" else \
                                "3-Day" if timeframe == "3d" else \
                                "2-Day" if timeframe == "2d" else \
                                "Daily" if timeframe == "1d" else \
                                "4-Hour"
    
                # Create message specific to each strategy type
                if strategy in self.vsa_detectors:
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Volume Ratio: {result.get('volume_ratio', 0):,.2f}x\n"
                        f"{volume_period} Volume: ${result.get('volume', 0):,.2f}\n"
                        f"Close Off Low: {result.get('close_off_low', 0):,.1f}%\n"
                        f"Angular Ratio: {result.get('arctan_ratio', np.nan):.2f}\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'pin_down':
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Volume Ratio: {result.get('volume_ratio', 0):,.2f}x\n"
                        f"{volume_period} Volume: ${result.get('volume_usd', 0):,.2f}\n"
                        f"Bearish top bars ago: {result.get('bearishtop_dist', 0)}\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'confluence':
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Volume Ratio: {result.get('volume_ratio', 0):,.2f}x\n"
                        f"{volume_period} Volume: ${result.get('volume_usd', 0):,.2f}\n"
                        f"Close Off Low: {result.get('close_off_low', 0):,.1f}%\n"
                        f"Momentum Score: {result.get('momentum_score', 0):,.2f}\n"
                        f"Components: Vol={result.get('high_volume', False)}, "
                        f"Spread={result.get('spread_breakout', False)}, "
                        f"Mom={result.get('momentum_breakout', False)}\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'consolidation':
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Box High: ${result.get('box_hi', 0):,.8f}\n"
                        f"Box Low: ${result.get('box_lo', 0):,.8f}\n"
                        f"Box Age: {result.get('box_age', 0)} bars\n"
                        f"Bars Inside: {result.get('bars_inside', 0)}/{result.get('min_bars_inside_req', 0)}\n"
                        f"Height %: {result.get('height_pct', 0):,.2f}%\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'consolidation_breakout':
                    # Get volume info
                    volume_usd = result.get('volume_usd', 0)
                    volume_ratio = result.get('volume_ratio', 0)
                    direction = result.get('direction', 'Unknown')
                    direction_emoji = "🟢" if direction == "Up" else "🔴" if direction == "Down" else "⚪"
                    
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Direction: {direction_emoji} {direction} Breakout\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Volume Ratio: {volume_ratio:,.2f}x\n"
                        f"{volume_period} Volume: ${volume_usd:,.2f}\n"
                        f"Box Age: {result.get('box_age', 0)} bars\n"
                        f"Bars Inside: {result.get('bars_inside', 0)}/{result.get('min_bars_inside_req', 0)}\n"
                        f"Height %: {result.get('height_pct', 0):,.2f} (≤ {result.get('max_height_pct_req', 0):,.2f})\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'channel_breakout':  # NEW: Channel Breakout message format
                    volume_usd = result.get('volume_usd', 0)
                    volume_ratio = result.get('volume_ratio', 0)
                    direction = result.get('direction', 'Unknown')
                    direction_emoji = "🟢" if direction == "Up" else "🔴" if direction == "Down" else "⚪"
                    channel_direction = result.get('channel_direction', 'Unknown')
                    
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Channel Direction: {channel_direction}\n"
                        f"Direction: {direction_emoji} {direction} Breakout\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Volume Ratio: {volume_ratio:,.2f}x\n"
                        f"{volume_period} Volume: ${volume_usd:,.2f}\n"
                        f"Channel Age: {result.get('channel_age', 0)} bars\n"
                        f"Channel Slope: {result.get('channel_slope', 0):,.4f}\n"
                        f"Bars Inside: {result.get('bars_inside', 0)}/{result.get('min_bars_inside_req', 0)}\n"
                        f"Height %: {result.get('height_pct', 0):,.2f} (≤ {result.get('max_height_pct_req', 0):,.2f})\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'sma50_breakout':
                    volume_usd = result.get('volume_usd', 0)
                    volume_ratio = result.get('volume_ratio', 0)
                    direction = result.get('direction', 'Up')
                    direction_emoji = "🟢"  # Always bullish for SMA breakout
                    breakout_type = result.get('breakout_type', 'classic_breakout')
                    breakout_strength = result.get('breakout_strength', 'Unknown')
                    
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Price vs SMA: {result.get('price_vs_sma_pct', 0):+.2f}%\n"
                        f"Low vs SMA: {result.get('low_vs_sma_pct', 0):+.2f}%\n"
                        f"{volume_period} Volume: ${volume_usd:,.2f}\n"
                        f"Close Off Low: {result.get('close_off_low', 0):,.1f}%\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'hbs_breakout':
                    # Extract needed values
                    volume_usd = result.get('volume_usd', 0)
                    direction = result.get('direction', 'Unknown')
                    
                    # Determine direction emoji and text
                    if direction == "Up":
                        direction_display = "🟢⬆️ UP"
                    elif direction == "Down":
                        direction_display = "🔴⬇️ DOWN"
                    else:
                        direction_display = "⚪ NEUTRAL"
                    
                    # Determine context (what type of breakout)
                    context = result.get('breakout_type', '')  # You'll need to pass this from scan_market
                    if context == 'both':
                        context_display = "📈 Both"
                    elif context == 'channel_breakout':
                        context_display = "␥ Channel BO"
                    else:
                        context_display = "☲ Consolidation BO"
                    
                    # Determine extreme conditions
                    has_extreme_volume = result.get('extreme_volume', False)
                    has_extreme_spread = result.get('extreme_spread', False)
                    
                    if has_extreme_volume and has_extreme_spread:
                        extreme_display = "🟠 Volume and Spread"
                    elif has_extreme_volume:
                        extreme_display = "🟠 Volume"
                    elif has_extreme_spread:
                        extreme_display = "🟠 Spread"
                    else:
                        extreme_display = "🟢 None"
                    
                    # Format price and volume
                    price_formatted = f"${result.get('close', 0):,.2f}"
                    volume_formatted = f"${volume_usd:,.1f}M" if volume_usd >= 1000000 else f"${volume_usd:,.0f}"
                    
                    # Create compact message with clickable symbol
                    signal_message = (
                        f"<a href='{tv_link}'>{symbol}</a> | {price_formatted} | Vol: {volume_formatted}\n"
                        f"Time: {date} | {bar_status}\n"
                        f"----\n"
                        f"Context: {context_display}\n"
                        f"Is extreme: {extreme_display}\n"
                        f"Direction: {direction_display}\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'volume_surge':
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Volume Ratio: {result.get('volume_ratio', 0):,.2f}x\n"
                        f"{volume_period} Volume: ${result.get('volume_usd', 0):,.2f}\n"
                        f"Score: {result.get('score', 0):,.2f}\n"
                        f"Price Extreme: {result.get('price_extreme', 'Unknown')}\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'weak_uptrend':
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"Volume: ${result.get('volume_usd', 0):,.2f}\n"
                        f"Uptrend age: {result.get('uptrend_age', 0)} bars\n"
                        f"Weakness level: {result.get('weakness_level', 0):,.2f}\n"
                        f"{'='*30}\n"
                    )
                else:
                    # Generic format for any other strategy
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"{'='*30}\n"
                    )
                
                # Add signal message to list
                signal_messages.append(signal_message)
            
            # Initialize Telegram app
            app = self.telegram_apps[strategy]
            if not hasattr(app, '_initialized') or not app._initialized:
                await app.initialize()
                await app.start()
            
            # Send messages to each chat ID with smart chunking
            for chat_id in chat_ids:
                # Maximum message size for Telegram
                max_message_size = 4000  # Slightly less than the 4096 limit to be safe
                
                # Start with the header
                current_chunk = header
                
                # Process each signal message
                for signal in signal_messages:
                    # If adding this signal would exceed the limit, send the current chunk and start a new one
                    if len(current_chunk) + len(signal) > max_message_size:
                        # Send the current chunk
                        await app.bot.send_message(
                            chat_id=chat_id, 
                            text=current_chunk, 
                            parse_mode='HTML', 
                            disable_web_page_preview=True
                        )
                        # Wait to avoid rate limits
                        await asyncio.sleep(0.3)
                        # Start a new chunk with the header
                        current_chunk = header + signal
                    else:
                        # Add the signal to the current chunk
                        current_chunk += signal
                
                # Send the final chunk if there's anything left
                if current_chunk and current_chunk != header:
                    await app.bot.send_message(
                        chat_id=chat_id, 
                        text=current_chunk, 
                        parse_mode='HTML', 
                        disable_web_page_preview=True
                    )
                    
        except Exception as e:
            logging.error(f"Error sending {strategy} Telegram message: {str(e)}")
    
    async def scan_market(self, symbol):
        cache_key = f"{self.exchange_name}_{self.exchange_client.timeframe}_{symbol}"
        if cache_key not in kline_cache:
            df = await self.exchange_client.fetch_klines(symbol)
            kline_cache[cache_key] = df
        else:
            logging.info(f"Using cached data for {symbol}")
        df = kline_cache[cache_key]
        
        if df is None or len(df) < 10:
            return {}
        
        # Only check volume filter on closed bars
        if len(df) > 1:
            volume_usd = df['volume'].iloc[-2] * df['close'].iloc[-2]
            if volume_usd < self.min_volume_usd:
                return {}
        
        results = {}
        for strategy in self.strategies:
            # Handle VSA-based strategies
            if strategy in self.vsa_detectors:
                # Special handling for test_bar (like start_bar)
                if strategy == 'test_bar':
                    from breakout_vsa.core import test_bar_vsa
                    condition, result = test_bar_vsa(df)
                    arctan_ratio_series = result['arctan_ratio']
                else:
                    # Get strategy parameters for other VSA strategies
                    if strategy == 'reversal_bar':
                        from breakout_vsa.strategies.reversal_bar import get_params
                        params = get_params()
                    elif strategy == 'breakout_bar':
                        from breakout_vsa.strategies.breakout_bar import get_params
                        params = get_params()
                    elif strategy == 'stop_bar':
                        from breakout_vsa.strategies.stop_bar import get_params
                        params = get_params()
                    elif strategy == 'start_bar':
                        from breakout_vsa.strategies.start_bar import get_params
                        params = get_params()
                    elif strategy == 'loaded_bar':
                        from breakout_vsa.strategies.loaded_bar import get_params
                        params = get_params()
                    else:
                        # Fallback to default extraction if specific import not available
                        params = self.vsa_detectors[strategy].__defaults__[0] if self.vsa_detectors[strategy].__defaults__ else {}
                    
                    # Run the detector with proper parameters
                    from breakout_vsa.core import vsa_detector
                    condition, result = vsa_detector(df, params)
                    
                    # Fix for start_bar which might have a different return signature
                    if strategy == 'start_bar' and not isinstance(condition, tuple):
                        arctan_ratio_series = pd.Series(np.nan, index=df.index)  # Default to NaN
                    else:
                        arctan_ratio_series = result['arctan_ratio']
                
                # Process detections for both current and previous bars
                detected_results = []
                
                # Process current bar detection
                if condition.iloc[-1]:
                    idx = df.index[-1]
                    volume_mean = df['volume'].rolling(7).mean().iloc[-1]
                    bar_range = df['high'].iloc[-1] - df['low'].iloc[-1]
                    close_off_low = (df['close'].iloc[-1] - df['low'].iloc[-1]) / bar_range * 100 if bar_range > 0 else 0
                    volume_usd_current = df['volume'].iloc[-1] * df['close'].iloc[-1]
                    arctan_ratio = arctan_ratio_series.iloc[-1] if not pd.isna(arctan_ratio_series.iloc[-1]) else 0.0
                    
                    detected_results.append({
                        'symbol': symbol,
                        'date': idx,
                        'close': df['close'].iloc[-1],
                        'volume': volume_usd_current,
                        'volume_ratio': df['volume'].iloc[-1] / volume_mean if volume_mean > 0 else 0,
                        'close_off_low': close_off_low,
                        'current_bar': True,
                        'arctan_ratio': arctan_ratio
                    })
                    logging.info(f"{strategy} detected for {symbol} (current bar)")
                
                # Process last closed bar detection
                if len(df) > 1 and condition.iloc[-2]:
                    idx = df.index[-2]
                    volume_mean = df['volume'].rolling(7).mean().iloc[-2]
                    bar_range = df['high'].iloc[-2] - df['low'].iloc[-2]
                    close_off_low = (df['close'].iloc[-2] - df['low'].iloc[-2]) / bar_range * 100 if bar_range > 0 else 0
                    volume_usd_closed = df['volume'].iloc[-2] * df['close'].iloc[-2]
                    arctan_ratio = arctan_ratio_series.iloc[-2] if not pd.isna(arctan_ratio_series.iloc[-2]) else 0.0
                    
                    detected_results.append({
                        'symbol': symbol,
                        'date': idx,
                        'close': df['close'].iloc[-2],
                        'volume': volume_usd_closed,
                        'volume_ratio': df['volume'].iloc[-2] / volume_mean if volume_mean > 0 else 0,
                        'close_off_low': close_off_low,
                        'current_bar': False,
                        'arctan_ratio': arctan_ratio
                    })
                    logging.info(f"{strategy} detected for {symbol} (last closed bar)")
                
                # Store all detected results
                if detected_results:
                    # If multiple detections, prioritize the most recent one
                    results[strategy] = detected_results[-1]  # Take the last (most recent) detection
                    
            # Handle volume_surge strategy
            elif strategy == 'volume_surge':
                from custom_strategies import detect_volume_surge
                
                # Check last closed bar
                if len(df) > 1:
                    detected, result = detect_volume_surge(df, check_bar=-2)  # Explicitly check last closed bar
                    
                    if detected:
                        results[strategy] = {
                            'symbol': symbol,
                            'date': result['timestamp'],
                            'close': result['close_price'],
                            'volume': result['volume'],
                            'volume_usd': result['volume_usd'],
                            'volume_ratio': result['volume_ratio'],
                            'score': result['score'],
                            'price_extreme': result['price_extreme'],
                            'current_bar': False  # Last closed bar
                        }
                        logging.info(f"{strategy} detected for {symbol} (current bar)")
                        
            # Handle weak_uptrend strategy
            elif strategy == 'weak_uptrend':
                from custom_strategies import detect_weak_uptrend
                detected, result = detect_weak_uptrend(df)
                
                if detected:
                    result['symbol'] = symbol
                    results[strategy] = result
                    logging.info(f"{strategy} detected for {symbol}")
            
            # Handle pin_down strategy
            elif strategy == 'pin_down':
                from custom_strategies import detect_pin_down
                detected, result = detect_pin_down(df)
                
                if detected:
                    result['symbol'] = symbol
                    result['volume_usd'] = df['volume'].iloc[-2] * df['close'].iloc[-2] if len(df) > 1 else 0
                    results[strategy] = result
                    logging.info(f"{strategy} detected for {symbol}")

            # Handle confluence strategy
            elif strategy == 'confluence':
                from custom_strategies import detect_confluence
                
                # Check last closed bar
                if len(df) > 1:
                    detected, result = detect_confluence(df, check_bar=-2)  # Last closed bar
                    
                    if detected:
                        results[strategy] = {
                            'symbol': symbol,
                            'date': result['timestamp'],
                            'close': result['close_price'],
                            'volume': result['volume'],
                            'volume_usd': result['volume_usd'],
                            'volume_ratio': result['volume_ratio'],
                            'close_off_low': result['close_off_low'],
                            'momentum_score': result['momentum_score'],
                            'high_volume': result['high_volume'],
                            'extreme_volume': result.get('extreme_volume', False),
                            'extreme_spread': result.get('extreme_spread', False),
                            'spread_breakout': result['spread_breakout'],
                            'momentum_breakout': result['momentum_breakout'],
                            'current_bar': False  # Last closed bar
                        }
                        logging.info(f"{strategy} detected for {symbol} (last closed bar)")
                
                # Check current bar
                if len(df) > 2:  # Need sufficient data for proper calculation
                    detected, result = detect_confluence(df, check_bar=-1)  # Current bar
                    
                    if detected:
                        results[strategy] = {
                            'symbol': symbol,
                            'date': result['timestamp'],
                            'close': result['close_price'],
                            'volume': result['volume'],
                            'volume_usd': result['volume_usd'],
                            'volume_ratio': result['volume_ratio'],
                            'close_off_low': result['close_off_low'],
                            'momentum_score': result['momentum_score'],
                            'high_volume': result['high_volume'],
                            'extreme_volume': result.get('extreme_volume', False),
                            'extreme_spread': result.get('extreme_spread', False),
                            'spread_breakout': result['spread_breakout'],
                            'momentum_breakout': result['momentum_breakout'],
                            'current_bar': True  # Current bar
                        }
                        logging.info(f"{strategy} detected for {symbol} (current bar)")
                        
            # Handle consolidation breakout strategy
            elif strategy == 'consolidation_breakout':                
                from custom_strategies import detect_consolidation_breakout  # Correct import
                
                # Check last closed bar
                if len(df) > 1:
                    detected, result = detect_consolidation_breakout(df, check_bar=-2)  # Correct function call
                    if detected:
                        # Calculate volume info for breakout
                        volume_usd = df['volume'].iloc[-2] * df['close'].iloc[-2]
                        volume_mean = df['volume'].rolling(7).mean().iloc[-2]
                        volume_ratio = df['volume'].iloc[-2] / volume_mean if volume_mean > 0 else 0
                        
                        results[strategy] = {
                            'symbol': symbol,
                            'direction': result.get('direction'),
                            'date': result.get('timestamp', df.index[-2]),
                            'close': df['close'].iloc[-2],
                            'current_bar': False,
                            'volume_usd': volume_usd,
                            'volume_ratio': volume_ratio,
                            # Payload from detector
                            'box_hi': result.get('box_hi'),
                            'box_lo': result.get('box_lo'),
                            'box_age': result.get('box_age'),
                            'bars_inside': result.get('bars_inside'),
                            'min_bars_inside_req': result.get('min_bars_inside_req'),
                            'height_pct': result.get('height_pct'),
                            'max_height_pct_req': result.get('max_height_pct_req'),
                        }
                        logging.info(f"{strategy} detected for {symbol} (last closed bar)")

                # Check current bar
                if len(df) > 2:
                    detected, result = detect_consolidation_breakout(df, check_bar=-1)
                    if detected:
                        # Calculate volume info for breakout
                        volume_usd = df['volume'].iloc[-1] * df['close'].iloc[-1]
                        volume_mean = df['volume'].rolling(7).mean().iloc[-1]
                        volume_ratio = df['volume'].iloc[-1] / volume_mean if volume_mean > 0 else 0
                        
                        results[strategy] = {
                            'symbol': symbol,
                            'direction': result.get('direction'),
                            'date': result.get('timestamp', df.index[-1]),
                            'close': df['close'].iloc[-1],
                            'current_bar': True,
                            'volume_usd': volume_usd,
                            'volume_ratio': volume_ratio,
                            # Payload from detector
                            'box_hi': result.get('box_hi'),
                            'box_lo': result.get('box_lo'),
                            'box_age': result.get('box_age'),
                            'bars_inside': result.get('bars_inside'),
                            'min_bars_inside_req': result.get('min_bars_inside_req'),
                            'height_pct': result.get('height_pct'),
                            'max_height_pct_req': result.get('max_height_pct_req'),
                        }
                        logging.info(f"{strategy} detected for {symbol} (current bar)")

            # Handle channel_breakout strategy (NEW)
            elif strategy == 'channel_breakout':
                from custom_strategies import detect_channel_breakout
                
                # Check last closed bar
                if len(df) > 23:  # Minimum required data
                    detected, result = detect_channel_breakout(df, check_bar=-2)
                    if detected:
                        # Calculate volume info for breakout
                        volume_usd = df['volume'].iloc[-2] * df['close'].iloc[-2]
                        volume_mean = df['volume'].rolling(7).mean().iloc[-2]
                        volume_ratio = df['volume'].iloc[-2] / volume_mean if volume_mean > 0 else 0
                        
                        results[strategy] = {
                            'symbol': symbol,
                            'direction': result.get('direction'),
                            'date': result.get('timestamp', df.index[-2]),
                            'close': df['close'].iloc[-2],
                            'current_bar': False,
                            'volume_usd': volume_usd,
                            'volume_ratio': volume_ratio,
                            # Channel-specific information
                            'channel_age': result.get('channel_age'),
                            'channel_direction': result.get('channel_direction'),
                            'channel_slope': result.get('channel_slope'),
                            'channel_offset': result.get('channel_offset'),
                            'bars_inside': result.get('bars_inside'),
                            'min_bars_inside_req': result.get('min_bars_inside_req'),
                            'height_pct': result.get('height_pct'),
                            'max_height_pct_req': result.get('max_height_pct_req'),
                            'atr_ok': result.get('atr_ok'),
                            'window_size': result.get('window_size'),
                        }
                        logging.info(f"{strategy} detected for {symbol} (last closed bar)")

                # Check current bar
                if len(df) > 24:  # Need one more bar for current analysis
                    detected, result = detect_channel_breakout(df, check_bar=-1)
                    if detected:
                        # Calculate volume info for breakout
                        volume_usd = df['volume'].iloc[-1] * df['close'].iloc[-1]
                        volume_mean = df['volume'].rolling(7).mean().iloc[-1]
                        volume_ratio = df['volume'].iloc[-1] / volume_mean if volume_mean > 0 else 0
                        
                        results[strategy] = {
                            'symbol': symbol,
                            'direction': result.get('direction'),
                            'date': result.get('timestamp', df.index[-1]),
                            'close': df['close'].iloc[-1],
                            'current_bar': True,
                            'volume_usd': volume_usd,
                            'volume_ratio': volume_ratio,
                            # Channel-specific information
                            'channel_age': result.get('channel_age'),
                            'channel_direction': result.get('channel_direction'),
                            'channel_slope': result.get('channel_slope'),
                            'channel_offset': result.get('channel_offset'),
                            'bars_inside': result.get('bars_inside'),
                            'min_bars_inside_req': result.get('min_bars_inside_req'),
                            'height_pct': result.get('height_pct'),
                            'max_height_pct_req': result.get('max_height_pct_req'),
                            'atr_ok': result.get('atr_ok'),
                            'window_size': result.get('window_size'),
                        }
                        logging.info(f"{strategy} detected for {symbol} (current bar)")

            # Handle sma50_breakout strategy
            elif strategy == 'sma50_breakout':
                from custom_strategies import detect_sma50_breakout
                
                # Check last closed bar
                if len(df) > 50:  # Need enough data for 50SMA
                    detected, result = detect_sma50_breakout(df, use_pre_breakout=False, check_bar=-2)
                    if detected:
                        results[strategy] = {
                            'symbol': symbol,
                            'direction': result.get('direction'),
                            'date': result.get('timestamp', df.index[-2]),
                            'close': df['close'].iloc[-2],
                            'current_bar': False,
                            'volume_usd': result.get('volume_usd'),
                            'volume_ratio': result.get('volume_ratio'),
                            # SMA-specific information
                            'sma50': result.get('sma50'),
                            'atr': result.get('atr'),
                            'price_vs_sma_pct': result.get('price_vs_sma_pct'),
                            'low_vs_sma_pct': result.get('low_vs_sma_pct'),
                            'breakout_type': result.get('breakout_type'),
                            'breakout_strength': result.get('breakout_strength'),
                            'pre_breakout_threshold': result.get('pre_breakout_threshold'),
                            'atr_threshold_distance': result.get('atr_threshold_distance'),
                            'close_off_low': result.get('close_off_low'),
                            'bar_range': result.get('bar_range'),
                        }
                        logging.info(f"{strategy} detected for {symbol} (last closed bar)")
            
                # Check current bar
                if len(df) > 51:  # Need one more bar for current analysis
                    detected, result = detect_sma50_breakout(df, use_pre_breakout=False, check_bar=-1)
                    if detected:
                        results[strategy] = {
                            'symbol': symbol,
                            'direction': result.get('direction'),
                            'date': result.get('timestamp', df.index[-1]),
                            'close': df['close'].iloc[-1],
                            'current_bar': True,
                            'volume_usd': result.get('volume_usd'),
                            'volume_ratio': result.get('volume_ratio'),
                            # SMA-specific information
                            'sma50': result.get('sma50'),
                            'atr': result.get('atr'),
                            'price_vs_sma_pct': result.get('price_vs_sma_pct'),
                            'low_vs_sma_pct': result.get('low_vs_sma_pct'),
                            'breakout_type': result.get('breakout_type'),
                            'breakout_strength': result.get('breakout_strength'),
                            'pre_breakout_threshold': result.get('pre_breakout_threshold'),
                            'atr_threshold_distance': result.get('atr_threshold_distance'),
                            'close_off_low': result.get('close_off_low'),
                            'bar_range': result.get('bar_range'),
                        }
                        logging.info(f"{strategy} detected for {symbol} (current bar)")
            
            # Handle hbs_breakout strategy (combination of consolidation_breakout + confluence)
            elif strategy == 'hbs_breakout':
                from custom_strategies import detect_consolidation_breakout, detect_confluence, detect_channel_breakout
                
                cb_detected_prev, cb_result_prev = detect_consolidation_breakout(df, check_bar=-2)
                cb_detected_curr, cb_result_curr = detect_consolidation_breakout(df, check_bar=-1)
                cf_detected_prev, cf_result_prev = detect_confluence(df, check_bar=-2)
                cf_detected_curr, cf_result_curr = detect_confluence(df, check_bar=-1)
                chb_detected_prev, chb_result_prev = detect_channel_breakout(df, check_bar=-2)
                chb_detected_curr, chb_result_curr = detect_channel_breakout(df, check_bar=-1)
                
                if cf_detected_curr and (cb_detected_curr or chb_detected_curr):
                    if cb_detected_curr and chb_detected_curr:
                        # Prefer channel_breakout if both occur
                        breakout_result = chb_result_curr
                        breakout_type = "channel_breakout"
                    elif cb_detected_curr:
                        breakout_result = cb_result_curr
                    else:
                        breakout_result = chb_result_curr
                        breakout_type = "consolidation_breakout"
                    
                    volume_usd = df['volume'].iloc[-1] * df['close'].iloc[-1]
                    volume_mean = df['volume'].rolling(7).mean().iloc[-1]
                    volume_ratio = df['volume'].iloc[-1] / volume_mean if volume_mean > 0 else 0
                    
                    results[strategy] = {
                        'symbol': symbol,
                        'direction': breakout_result.get('direction'),
                        'date': breakout_result.get('timestamp', df.index[-1]),
                        'close': df['close'].iloc[-1],
                        'current_bar': True,
                        'volume_usd': volume_usd,
                        'volume_ratio': volume_ratio,
                        'bars_inside': breakout_result.get('bars_inside'),
                        'min_bars_inside_req': breakout_result.get('min_bars_inside_req'),
                        'height_pct': breakout_result.get('height_pct'),
                        'max_height_pct_req': breakout_result.get('max_height_pct_req'),
                        'extreme_volume': cf_result_curr.get('extreme_volume', False),
                        'extreme_spread': cf_result_curr.get('extreme_spread', False),
                        'breakout_type': 'both' if (cb_detected_curr and chb_detected_curr) else 'channel_breakout' if chb_detected_curr else 'consolidation_breakout',
                    }
                    logging.info(f"{strategy} detected for {symbol} (current bar)")
                
                elif cf_detected_prev and (cb_detected_prev or chb_detected_prev):
                    if cb_detected_prev and chb_detected_prev:
                        # Prefer channel_breakout if both occur
                        breakout_result = chb_result_prev
                    elif cb_detected_prev:
                        breakout_result = cb_result_prev
                    else:
                        breakout_result = chb_result_prev
                    
                    volume_usd = df['volume'].iloc[-2] * df['close'].iloc[-2]
                    volume_mean = df['volume'].rolling(7).mean().iloc[-2]
                    volume_ratio = df['volume'].iloc[-2] / volume_mean if volume_mean > 0 else 0
                    
                    results[strategy] = {
                        'symbol': symbol,
                        'direction': breakout_result.get('direction'),
                        'date': breakout_result.get('timestamp', df.index[-2]),
                        'close': df['close'].iloc[-2],
                        'current_bar': False,
                        'volume_usd': volume_usd,
                        'volume_ratio': volume_ratio,
                        'bars_inside': breakout_result.get('bars_inside'),
                        'min_bars_inside_req': breakout_result.get('min_bars_inside_req'),
                        'height_pct': breakout_result.get('height_pct'),
                        'max_height_pct_req': breakout_result.get('max_height_pct_req'),
                        'extreme_volume': cf_result_prev.get('extreme_volume', False),
                        'extreme_spread': cf_result_prev.get('extreme_spread', False),
                        'breakout_type': 'both' if (cb_detected_prev and chb_detected_prev) else 'channel_breakout' if chb_detected_prev else 'consolidation_breakout',
                    }
                    logging.info(f"{strategy} detected for {symbol} (last closed bar)")            
                
        return results

    async def scan_all_markets(self):
        try:
            await self.init_session()
            symbols = await self.exchange_client.get_all_spot_symbols()
            timeframe = self.exchange_client.timeframe
            logging.info(f"Found {len(symbols)} markets on {self.exchange_name} for {timeframe} timeframe")
            
            all_results = {strategy: [] for strategy in self.strategies}
            # Always disable progress bars for parallel scans
            logging.info(f"Processing {len(symbols)} symbols for {self.exchange_name}...")
            for i in range(0, len(symbols), self.batch_size):
                batch = symbols[i:i + self.batch_size]
                tasks = [self.scan_market(symbol) for symbol in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, dict) and result:
                        for strategy, res in result.items():
                            if res:
                                all_results[strategy].append(res)
                                logging.info(f"{strategy} detected for {res['symbol']}")
                await asyncio.sleep(1.0)
            
            for strategy, results in all_results.items():
                if results and strategy in self.telegram_config:
                    await self.send_telegram_message(strategy, results)
            return all_results
        except Exception as e:
            logging.error(f"Error in scan_all_markets: {str(e)}")
            return {strategy: [] for strategy in self.strategies}
        finally:
            await self.close_session()

async def run_scanner(exchange, timeframe, strategies, telegram_config=None, min_volume_usd=None):
    from exchanges import (MexcFuturesClient, GateioFuturesClient, BinanceFuturesClient, 
                          BybitFuturesClient, BinanceSpotClient, BybitSpotClient, 
                          GateioSpotClient, KucoinSpotClient, MexcSpotClient)
    
    exchange_map = {
        "mexc_futures": MexcFuturesClient,
        "gateio_futures": GateioFuturesClient,
        "binance_futures": BinanceFuturesClient,
        "bybit_futures": BybitFuturesClient,
        "binance_spot": BinanceSpotClient,
        "bybit_spot": BybitSpotClient,
        "gateio_spot": GateioSpotClient,
        "kucoin_spot": KucoinSpotClient,
        "mexc_spot": MexcSpotClient,
        "sf_kucoin_1w": SFKucoinClient,
        "sf_mexc_1w": SFMexcClient
    }
    if exchange in ["sf_kucoin_1w", "sf_mexc_1w"] and timeframe != "1w":
        raise ValueError(f"SF exchange {exchange} only supports 1w timeframe, got {timeframe}")
            
    client_class = exchange_map.get(exchange)
    if not client_class:
        raise ValueError(f"Unsupported exchange: {exchange}")
    
    client = client_class(timeframe=timeframe)
    scanner = UnifiedScanner(client, strategies, telegram_config, min_volume_usd)
    return await scanner.scan_all_markets()