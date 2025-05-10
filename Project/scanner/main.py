# Scanner/main.py

import asyncio
import logging
from tqdm.asyncio import tqdm
from telegram.ext import Application
from datetime import datetime
import pandas as pd
import numpy as np
from custom_strategies import detect_volume_surge, detect_weak_uptrend, detect_pin_down
from breakout_vsa import vsa_detector, breakout_bar_vsa, stop_bar_vsa, reversal_bar_vsa, start_bar_vsa, loaded_bar_vsa, test_bar_vsa
from utils.config import VOLUME_THRESHOLDS
import os

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
            "MexcSpotClient": "MEXC Spot"
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
                volume_period = "Weekly" if timeframe == "1w" else "2-Day" if timeframe == "2d" else "Daily" if timeframe == "1d" else "4-Hour"
    
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
                # Get strategy parameters and detect patterns
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
                elif strategy == 'test_bar':
                    from breakout_vsa.strategies.test_bar import get_params
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
                
                # Process current bar detection
                if condition.iloc[-1]:
                    idx = df.index[-1]
                    volume_mean = df['volume'].rolling(7).mean().iloc[-1]
                    bar_range = df['high'].iloc[-1] - df['low'].iloc[-1]
                    close_off_low = (df['close'].iloc[-1] - df['low'].iloc[-1]) / bar_range * 100 if bar_range > 0 else 0
                    volume_usd_current = df['volume'].iloc[-1] * df['close'].iloc[-1]
                    arctan_ratio = arctan_ratio_series.iloc[-1] if not pd.isna(arctan_ratio_series.iloc[-1]) else 0.0
                    
                    results[strategy] = {
                        'symbol': symbol,
                        'date': idx,
                        'close': df['close'].iloc[-1],
                        'volume': volume_usd_current,
                        'volume_ratio': df['volume'].iloc[-1] / volume_mean if volume_mean > 0 else 0,
                        'close_off_low': close_off_low,
                        'current_bar': True,
                        'arctan_ratio': arctan_ratio
                    }
                    logging.info(f"{strategy} detected for {symbol}")
                
                # Process last closed bar detection
                elif len(df) > 1 and condition.iloc[-2]:
                    idx = df.index[-2]
                    volume_mean = df['volume'].rolling(7).mean().iloc[-2]
                    bar_range = df['high'].iloc[-2] - df['low'].iloc[-2]
                    close_off_low = (df['close'].iloc[-2] - df['low'].iloc[-2]) / bar_range * 100 if bar_range > 0 else 0
                    volume_usd_closed = df['volume'].iloc[-2] * df['close'].iloc[-2]
                    arctan_ratio = arctan_ratio_series.iloc[-2] if not pd.isna(arctan_ratio_series.iloc[-2]) else 0.0
                    
                    results[strategy] = {
                        'symbol': symbol,
                        'date': idx,
                        'close': df['close'].iloc[-2],
                        'volume': volume_usd_closed,
                        'volume_ratio': df['volume'].iloc[-2] / volume_mean if volume_mean > 0 else 0,
                        'close_off_low': close_off_low,
                        'current_bar': False,
                        'arctan_ratio': arctan_ratio
                    }
                    logging.info(f"{strategy} detected for {symbol}")
                    
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
                        logging.info(f"{strategy} detected for {symbol} (last closed bar)")
                
                # Check current bar
                if len(df) > 2:  # Need at least 3 bars for proper calculation
                    detected, result = detect_volume_surge(df, check_bar=-1)  # Check current bar
                    
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
                            'current_bar': True  # Current bar
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
        "mexc_spot": MexcSpotClient
    }
    
    client_class = exchange_map.get(exchange)
    if not client_class:
        raise ValueError(f"Unsupported exchange: {exchange}")
    
    client = client_class(timeframe=timeframe)
    scanner = UnifiedScanner(client, strategies, telegram_config, min_volume_usd)
    return await scanner.scan_all_markets()