#scanner/main.py

import asyncio
import logging
import sys
import os
from datetime import datetime
from decimal import Decimal
from tqdm.asyncio import tqdm
from telegram.ext import Application
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from utils.config import VOLUME_THRESHOLDS
from exchanges.sf_kucoin_client import SFKucoinClient
from exchanges.sf_mexc_client import SFMexcClient

# Function to check if progress bars should be disabled
def should_disable_progress():
    return os.environ.get("DISABLE_PROGRESS") == "1"
    
kline_cache = {}

def get_close_position_indicator(high, low, close):
    """Generate close position indicator with 3-dot system (0-30%, 30-70%, 70-100% ranges)"""
    bar_range = high - low
    if bar_range <= 0:
        return "○●○", 50.0  # Default to middle if no range
    
    close_position_pct = ((close - low) / bar_range) * 100
    
    if close_position_pct <= 30:
        indicator = "●○○"  # 0-30%
    elif close_position_pct <= 70:
        indicator = "○●○"  # 30-70%
    else:
        indicator = "○○●"  # 70-100%
    
    return indicator, close_position_pct

def _normalize_strength_label(label: str) -> str:
    """
    Normalize strength wording across strategies.
    We display only 'Strong' or 'Regular' (no 'Weak').
    """
    if not label:
        return ""
    label = str(label).strip().lower()
    if label == "strong":
        return "Strong"
    # treat anything else (e.g., 'Weak') as 'Regular'
    return "Regular"

class UnifiedScanner:
    def __init__(self, exchange_client, strategies, telegram_config=None, min_volume_usd=None, check_bar="last_closed"):
        """
        Initialize UnifiedScanner with bar selection parameter
        
        Args:
            exchange_client: Exchange client instance
            strategies: List of strategies to run
            telegram_config: Telegram configuration
            min_volume_usd: Minimum volume threshold
            check_bar: Which bar to analyze - "current", "last_closed", or "both"
                      Default is "last_closed" for production, "both" for development
        """
        self.exchange_client = exchange_client
        self.strategies = strategies
        self.telegram_config = telegram_config or {}
        self.check_bar = check_bar
        
        timeframe = exchange_client.timeframe
        self.min_volume_usd = min_volume_usd if min_volume_usd is not None else VOLUME_THRESHOLDS.get(timeframe, 50000)
        
        self.batch_size = 25  # Optimize batch size
        self.telegram_apps = {}
        self.exchange_name = self._get_exchange_name()
        
        # Thread pool for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        self.strategy_titles = {
            'volume_surge': 'Sudden Volume Surge',
            'weak_uptrend': 'Weak Uptrend Detection',
            'pin_down': 'Pin Down Detection',
            'confluence': 'Confluence Signal',
            'consolidation': 'Consolidation Pattern',
            'consolidation_breakout': 'Consolidation Breakout Pattern',
            'channel': 'Ongoing Channel Pattern',
            'channel_breakout': 'Channel Breakout Pattern',
            'wedge_breakout': 'Wedge Breakout Pattern',
            'sma50_breakout': '50SMA Breakout',
            'hbs_breakout': 'HBS Breakout', 
            'vs_wakeup': 'VS Wakeup',
            'breakout_bar': 'Breakout Bar',
            'stop_bar': 'Stop Bar',
            'reversal_bar': 'Reversal Bar',
            'start_bar': 'Start Bar',
            'loaded_bar': 'Loaded Bar',
            'test_bar': 'Test Bar',
            'trend_breakout': 'Trend Breakout Pattern',
            'pin_up': 'Pin Up Pattern',
            'bullish_engulfing': 'Bullish Engulfing Reversal'
        }
        
        # Cache VSA params to avoid repeated imports
        self._vsa_params_cache = {}

    def _get_bars_to_check(self):
        """Get list of (check_bar, is_current) tuples based on check_bar parameter"""
        if self.check_bar == "current":
            return [(-1, True)]
        elif self.check_bar == "last_closed":
            return [(-2, False)]
        elif self.check_bar == "both":
            return [(-2, False), (-1, True)]
        else:
            # Default to last_closed for safety
            return [(-2, False)]

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

    def _get_vsa_params(self, strategy):
        """Cache VSA parameters to avoid repeated imports"""
        if strategy in self._vsa_params_cache:
            return self._vsa_params_cache[strategy]
            
        try:
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
                params = {}
            
            self._vsa_params_cache[strategy] = params
            return params
        except Exception as e:
            logging.warning(f"Failed to get VSA params for {strategy}: {e}")
            return {}

    def _import_database_utils(self):
        """Import database utilities from SFEvent/market_event_db_utils.py"""
        try:
            # Add SFEvent directory to path if not already added
            sfevent_path = os.path.join(os.getcwd(), "SFEvent")
            if sfevent_path not in sys.path:
                sys.path.append(sfevent_path)
            
            from SFEvent.market_event_db_utils import MarketEvent, insert_market_event
            return MarketEvent, insert_market_event
        except ImportError as e:
            logging.warning(f"Database utilities not available: {e}")
            return None, None

    async def init_session(self):
        await self.exchange_client.init_session()
        for strategy, config in self.telegram_config.items():
            if 'token' in config and config['token'] and strategy not in self.telegram_apps:
                self.telegram_apps[strategy] = Application.builder().token(config['token']).build()

    async def close_session(self):
        await self.exchange_client.close_session()
        self.thread_pool.shutdown(wait=True)
        for app in self.telegram_apps.values():
            if hasattr(app, 'running') and app.running:
                await app.stop()
                await app.shutdown()
        self.telegram_apps = {}

    # Parallel strategy detection methods
    async def _detect_vsa_strategy(self, strategy, df, symbol):
        """Detect VSA-based strategies in thread pool"""
        try:
            def run_vsa_detection():
                if strategy == 'test_bar':
                    from breakout_vsa.core import test_bar_vsa
                    condition, result = test_bar_vsa(df)
                    arctan_ratio_series = result['arctan_ratio']
                else:
                    params = self._get_vsa_params(strategy)
                    from breakout_vsa.core import vsa_detector
                    condition, result = vsa_detector(df, params)
                    
                    if strategy == 'start_bar' and not isinstance(condition, tuple):
                        arctan_ratio_series = pd.Series(np.nan, index=df.index)
                    else:
                        arctan_ratio_series = result['arctan_ratio']
                
                return condition, arctan_ratio_series
            
            loop = asyncio.get_event_loop()
            condition, arctan_ratio_series = await loop.run_in_executor(
                self.thread_pool, run_vsa_detection
            )
            
            detected_results = []
            
            # Check bars based on check_bar parameter
            bars_to_check = self._get_bars_to_check()
            
            for check_bar, is_current in bars_to_check:
                bar_idx = check_bar
                if abs(bar_idx) > len(condition) - 1:
                    continue
                    
                if condition.iloc[bar_idx]:
                    idx = df.index[bar_idx]
                    volume_mean = df['volume'].rolling(7).mean().iloc[bar_idx]
                    bar_range = df['high'].iloc[bar_idx] - df['low'].iloc[bar_idx]
                    close_off_low = (df['close'].iloc[bar_idx] - df['low'].iloc[bar_idx]) / bar_range * 100 if bar_range > 0 else 0
                    volume_usd_current = df['volume'].iloc[bar_idx] * df['close'].iloc[bar_idx]
                    arctan_ratio = arctan_ratio_series.iloc[bar_idx] if not pd.isna(arctan_ratio_series.iloc[bar_idx]) else 0.0
                    
                    detected_results.append({
                        'symbol': symbol,
                        'date': idx,
                        'close': df['close'].iloc[bar_idx],
                        'volume': volume_usd_current,
                        'volume_usd': volume_usd_current,
                        'volume_ratio': df['volume'].iloc[bar_idx] / volume_mean if volume_mean > 0 else 0,
                        'close_off_low': close_off_low,
                        'current_bar': is_current,
                        'arctan_ratio': arctan_ratio
                    })
            
            return detected_results[-1] if detected_results else None
            
        except Exception as e:
            logging.error(f"Error in VSA strategy {strategy} for {symbol}: {e}")
            return None

    async def _detect_volume_surge(self, df, symbol):
        """Detect volume surge in thread pool"""
        try:
            def run_detection():
                from custom_strategies import detect_volume_surge
                
                # Check based on parameter, but volume surge typically uses last closed bar
                check_bars = self._get_bars_to_check()
                for check_bar, is_current in check_bars:
                    if len(df) > abs(check_bar):
                        detected, result = detect_volume_surge(df, check_bar=check_bar)
                        if detected:
                            result['current_bar'] = is_current
                            return detected, result
                return False, {}
            
            loop = asyncio.get_event_loop()
            detected, result = await loop.run_in_executor(self.thread_pool, run_detection)
            
            if detected:
                return {
                    'symbol': symbol,
                    'date': result['timestamp'],
                    'close': result['close_price'],
                    'volume': result['volume'],
                    'volume_usd': result['volume_usd'],
                    'volume_ratio': result['volume_ratio'],
                    'score': result['score'],
                    'price_extreme': result['price_extreme'],
                    'current_bar': result.get('current_bar', False)
                }
            return None
            
        except Exception as e:
            logging.error(f"Error in volume_surge for {symbol}: {e}")
            return None

    async def _detect_weak_uptrend(self, df, symbol):
        """Detect weak uptrend in thread pool"""
        try:
            def run_detection():
                from custom_strategies import detect_weak_uptrend
                detected, result = detect_weak_uptrend(df)
                return detected, result
            
            loop = asyncio.get_event_loop()
            detected, result = await loop.run_in_executor(self.thread_pool, run_detection)
            
            if detected:
                result['symbol'] = symbol
                return result
            return None
            
        except Exception as e:
            logging.error(f"Error in weak_uptrend for {symbol}: {e}")
            return None

    async def _detect_pin_down(self, df, symbol):
        """Detect pin down in thread pool"""
        try:
            def run_detection():
                from custom_strategies import detect_pin_down
                detected, result = detect_pin_down(df)
                return detected, result
            
            loop = asyncio.get_event_loop()
            detected, result = await loop.run_in_executor(self.thread_pool, run_detection)
            
            if detected:
                result['symbol'] = symbol
                result['volume_usd'] = df['volume'].iloc[-2] * df['close'].iloc[-2] if len(df) > 1 else 0
                return result
            return None
            
        except Exception as e:
            logging.error(f"Error in pin_down for {symbol}: {e}")
            return None

    async def _detect_confluence(self, df, symbol):
        """Detect confluence in thread pool"""
        try:
            def run_detection():
                from custom_strategies import detect_confluence
                confluence_results = []
                
                # Check bars based on parameter
                bars_to_check = self._get_bars_to_check()
                
                for check_bar, is_current in bars_to_check:
                    if len(df) > abs(check_bar):
                        detected_bull, result_bull = detect_confluence(df, check_bar=check_bar, is_bullish=True)
                        if detected_bull or result_bull.get('is_engulfing_reversal', False):
                            confluence_results.append({
                                'detected_bull': detected_bull,
                                'result_bull': result_bull,
                                'bar_type': 'current' if is_current else 'last_closed'
                            })
                
                return confluence_results
            
            loop = asyncio.get_event_loop()
            confluence_results = await loop.run_in_executor(self.thread_pool, run_detection)
            
            if confluence_results:
                # Prioritize current bar and reversals
                prioritized = sorted(confluence_results, key=lambda x: (
                    1 if x['bar_type'] == 'current' else 0,
                    1 if x['result_bull'].get('is_engulfing_reversal', False) else 0,
                    -1
                ), reverse=True)
                
                top_result = prioritized[0]
                base_result = top_result['result_bull']
                
                return {
                    'symbol': symbol,
                    'date': base_result['timestamp'],
                    'close': base_result['close_price'],
                    'volume': base_result['volume'],
                    'volume_usd': base_result['volume_usd'],
                    'volume_ratio': base_result['volume_ratio'],
                    'close_off_low': base_result['close_off_low'],
                    'momentum_score': base_result['momentum_score'],
                    'high_volume': base_result['high_volume'],
                    'volume_breakout': base_result.get('volume_breakout', False),
                    'extreme_volume': base_result.get('extreme_volume', False),
                    'extreme_spread': base_result.get('extreme_spread', False),
                    'spread_breakout': base_result['spread_breakout'],
                    'momentum_breakout': base_result['momentum_breakout'],
                    'current_bar': (top_result['bar_type'] == 'current'),
                    'direction': base_result.get('direction', 'Up'),
                    'is_engulfing_reversal': base_result.get('is_engulfing_reversal', False),
                }
            return None
            
        except Exception as e:
            logging.error(f"Error in confluence for {symbol}: {e}")
            return None

    async def _detect_bullish_engulfing(self, df, symbol):
        """Detect bullish engulfing in thread pool"""
        try:
            def run_detection():
                from custom_strategies import detect_bullish_engulfing
                bullish_engulfing_results = []
                
                # Check bars based on parameter
                bars_to_check = self._get_bars_to_check()
                
                for check_bar, is_current in bars_to_check:
                    if len(df) > abs(check_bar) + 50:  # Need at least 50 candles
                        detected, result = detect_bullish_engulfing(df, check_bar=check_bar)
                        if detected:
                            result['current_bar'] = is_current
                            bullish_engulfing_results.append(result)
                
                return bullish_engulfing_results
            
            loop = asyncio.get_event_loop()
            bullish_engulfing_results = await loop.run_in_executor(self.thread_pool, run_detection)
            
            if bullish_engulfing_results:
                # Take the most recent result (prioritize current bar if both exist)
                result = bullish_engulfing_results[-1]
                
                return {
                    'symbol': symbol,
                    'date': result['date'],
                    'close': result['close'],
                    'high': result['high'],
                    'low': result['low'],
                    'volume_ratio': result['volume_ratio'],
                    'close_position': result['close_position'],
                    'is_buying_power': result['is_buying_power'],
                    'pr_low_21': result['pr_low_21'],
                    'pr_hl2_13': result['pr_hl2_13'],
                    'pr_spread_21': result['pr_spread_21'],
                    'current_bar': result['current_bar'],
                    'volume_usd': result['close'] * result['volume_ratio'] * 1000  # Approximate volume USD
                }
            return None
            
        except Exception as e:
            logging.error(f"Error in bullish_engulfing for {symbol}: {e}")
            return None

    async def _detect_pattern_strategy(self, strategy, df, symbol):
        """Generic pattern strategy detector for consolidation, breakouts, etc."""
        try:
            def run_detection():
                results = []
                bars_to_check = self._get_bars_to_check()
                
                if strategy == 'consolidation':
                    from custom_strategies import detect_consolidation
                    # Check specified bars
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar) + 22:  # Ensure enough data
                            detected, result = detect_consolidation(df, check_bar=check_bar)
                            if detected and not result.get('breakout', False):
                                results.append((result, is_current, check_bar))
                
                elif strategy == 'consolidation_breakout':
                    from custom_strategies import detect_consolidation_breakout
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar):
                            detected, result = detect_consolidation_breakout(df, check_bar=check_bar)
                            if detected:
                                # normalize strength wording
                                if 'strong' in result:
                                    result['strength_label'] = "Strong" if result['strong'] else "Regular"
                                else:
                                    result['strength_label'] = ""
                                results.append((result, is_current, check_bar))
                
                elif strategy == 'channel':
                    from custom_strategies import detect_channel
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar) + 22:
                            detected, result = detect_channel(df, check_bar=check_bar)
                            if detected:
                                results.append((result, is_current, check_bar))
                
                elif strategy == 'channel_breakout':
                    from custom_strategies import detect_channel_breakout
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar) + 22:
                            detected, result = detect_channel_breakout(df, check_bar=check_bar)
                            if detected:
                                results.append((result, is_current, check_bar))
                
                elif strategy == 'wedge_breakout':
                    from custom_strategies import detect_wedge_breakout
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar) + 22:
                            detected, result = detect_wedge_breakout(df, check_bar=check_bar)
                            if detected:
                                results.append((result, is_current, check_bar))
                
                elif strategy == 'sma50_breakout':
                    from custom_strategies import detect_sma50_breakout
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar):
                            # allow pre_breakout; strength only for "regular"
                            detected, result = detect_sma50_breakout(df, use_pre_breakout=True, check_bar=check_bar)
                            if detected:
                                br_type = result.get('breakout_type', '')
                                br_strength = _normalize_strength_label(result.get('breakout_strength', ''))
                                is_strong = (br_type == 'regular' and br_strength == 'Strong')

                                result['strong'] = is_strong
                                result['strength_label'] = br_strength  # "Strong" | "Regular" | ""

                                results.append((result, is_current, check_bar))
                
                elif strategy == 'trend_breakout':
                    from custom_strategies import detect_trend_breakout
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar):
                            detected, result = detect_trend_breakout(df, check_bar=check_bar)
                            if detected:
                                results.append((result, is_current, check_bar))
                
                elif strategy == 'pin_up':
                    from custom_strategies import detect_pin_up
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar):
                            detected, result = detect_pin_up(df, check_bar=check_bar)
                            if detected:
                                results.append((result, is_current, check_bar))
                
                elif strategy == 'hbs_breakout':
                    from custom_strategies import detect_consolidation_breakout, detect_confluence, detect_channel_breakout, detect_sma50_breakout
                    
                    # Check specified bars for HBS combo
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar) + 5:
                            cb_detected, cb_result = detect_consolidation_breakout(df, check_bar=check_bar)
                            chb_detected, chb_result = detect_channel_breakout(df, check_bar=check_bar)
                            cf_detected, cf_result = detect_confluence(df, check_bar=check_bar)

                            # Normalize consolidation strength wording if present
                            if cb_detected:
                                cb_result['strength_label'] = "Strong" if cb_result.get('strong', False) else "Regular"

                            # SMA50 component
                            sma50_detected, sma50_result = False, {}
                            if len(df) > 57 + abs(check_bar):
                                sma50_detected, sma50_result = detect_sma50_breakout(df, use_pre_breakout=True, check_bar=check_bar)
                                if sma50_detected:
                                    sla = _normalize_strength_label(sma50_result.get('breakout_strength', ''))
                                    sma50_result['strength_label'] = sla
                                    sma50_result['strong'] = (sma50_result.get('breakout_type') == 'regular' and sla == 'Strong')

                            if cf_detected and (cb_detected or chb_detected):
                                # Determine breakout type
                                if cb_detected and chb_detected:
                                    breakout_result = chb_result
                                    breakout_type = "both"
                                elif cb_detected:
                                    breakout_result = cb_result
                                    breakout_type = "consolidation_breakout"
                                else:
                                    breakout_result = chb_result
                                    breakout_type = "channel_breakout"
                                
                                result_data = {
                                    'breakout_result': breakout_result,
                                    'cf_result': cf_result,
                                    'breakout_type': breakout_type,
                                    'sma50_detected': sma50_detected,
                                    'sma50_result': sma50_result,
                                    'has_volume_breakout': (cf_result.get('volume_breakout', False) and not cf_result.get('extreme_volume', False)),
                                }
                                
                                # Propagate strength for consolidation: strong/regular wording
                                if breakout_type == "consolidation_breakout":
                                    result_data['strong'] = cb_result.get('strong', False)
                                    result_data['strength_label'] = cb_result.get('strength_label', "Regular")
                                else:
                                    result_data['strong'] = False
                                    result_data['strength_label'] = ""
                                
                                # SMA50 helper boolean for HBS
                                result_data['sma50_is_strong'] = (
                                    sma50_detected
                                    and sma50_result.get('breakout_type') == 'regular'
                                    and sma50_result.get('strength_label') == 'Strong'
                                )
                                
                                results.append((result_data, is_current, check_bar))

                elif strategy == 'vs_wakeup':
                    from custom_strategies import detect_consolidation, detect_confluence
                    # Check specified bars
                    for check_bar, is_current in bars_to_check:
                        if len(df) > abs(check_bar) + 22:  # Ensure enough data for consolidation
                            cons_detected, cons_result = detect_consolidation(df, check_bar=check_bar)
                            if cons_detected and not cons_result.get('breakout', False):
                                conf_detected, conf_result = detect_confluence(df, check_bar=check_bar, only_wakeup=True)
                                if conf_detected:
                                    # Combine results
                                    combined_result = {
                                        'consolidation_result': cons_result,
                                        'confluence_result': conf_result,
                                    }
                                    results.append((combined_result, is_current, check_bar))
                
                return results
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(self.thread_pool, run_detection)
            
            if not results:
                return None
            
            # Take the most recent result (prioritize current bar)
            result_data, is_current, check_bar = results[-1]
            idx = check_bar
            
            # Common volume calculations
            volume_usd = df['volume'].iloc[idx] * df['close'].iloc[idx]
            volume_mean = df['volume'].rolling(7).mean().iloc[idx]
            volume_ratio = df['volume'].iloc[idx] / volume_mean if volume_mean > 0 else 0
            close_indicator, close_pos_pct = get_close_position_indicator(
                df['high'].iloc[idx], 
                df['low'].iloc[idx], 
                df['close'].iloc[idx]
            )
            
            # Strategy-specific result formatting
            base_result = {
                'symbol': symbol,
                'date': result_data.get('timestamp', df.index[idx]),
                'close': df['close'].iloc[idx],
                'current_bar': is_current,
                'volume_usd': volume_usd,
                'volume_ratio': volume_ratio,
                'close_position_indicator': close_indicator,
                'close_position_pct': close_pos_pct,
            }
            
            if strategy == 'hbs_breakout':
                breakout_result = result_data['breakout_result']
                cf_result = result_data['cf_result']
                
                base_result.update({
                    'direction': breakout_result.get('direction'),
                    'date': breakout_result.get('timestamp', df.index[idx]),
                    'bars_inside': breakout_result.get('bars_inside'),
                    'min_bars_inside_req': breakout_result.get('min_bars_inside_req'),
                    'height_pct': breakout_result.get('height_pct'),
                    'max_height_pct_req': breakout_result.get('max_height_pct_req'),
                    # Strength wording for consolidation: Strong / Regular
                    'strong': result_data.get('strong', False),
                    'strength_label': result_data.get('strength_label', ''),
                    'extreme_volume': cf_result.get('extreme_volume', False),
                    'extreme_spread': cf_result.get('extreme_spread', False),
                    'breakout_type': result_data['breakout_type'],
                    'has_sma50_breakout': result_data['sma50_detected'],
                    'sma50_breakout_type': result_data['sma50_result'].get('breakout_type', '') if result_data['sma50_detected'] else '',
                    'sma50_breakout_strength': result_data['sma50_result'].get('strength_label', '') if result_data['sma50_detected'] else '',
                    'sma50_is_strong': result_data.get('sma50_is_strong', False),
                    'has_engulfing_reversal': cf_result.get('is_engulfing_reversal', False),
                    'confluence_direction': cf_result.get('direction', 'Up'),
                    'has_volume_breakout': result_data.get('has_volume_breakout', False),
                })
            elif strategy == 'vs_wakeup':
                cons_result = result_data['consolidation_result']
                conf_result = result_data['confluence_result']
                
                base_result.update({
                    'date': cons_result.get('timestamp', df.index[idx]),
                    'box_age': cons_result.get('box_age', 0),
                    'direction': conf_result.get('direction', 'Up'),
                })
            else:
                # Add all other fields from result_data
                for key, value in result_data.items():
                    if key not in ['timestamp']:
                        base_result[key] = value
            
            return base_result
            
        except Exception as e:
            logging.error(f"Error in {strategy} for {symbol}: {e}")
            return None

    async def scan_market(self, symbol):
        """Scan a single market with parallel strategy execution"""
        cache_key = f"{self.exchange_name}_{self.exchange_client.timeframe}_{symbol}"
        if cache_key not in kline_cache:
            df = await self.exchange_client.fetch_klines(symbol)
            kline_cache[cache_key] = df
        else:
            logging.debug(f"Using cached data for {symbol}")
        df = kline_cache[cache_key]
        
        if df is None or len(df) < 10:
            return {}
        
        # Volume filter on closed bars
        if len(df) > 1:
            volume_usd = df['volume'].iloc[-2] * df['close'].iloc[-2]
            if volume_usd < self.min_volume_usd:
                return {}
        
        # Create parallel tasks for each strategy
        strategy_tasks = []
        vsa_strategies = {'breakout_bar', 'stop_bar', 'reversal_bar', 'start_bar', 'loaded_bar', 'test_bar'}
        pattern_strategies = {'consolidation', 'consolidation_breakout', 'channel', 'channel_breakout', 
                            'wedge_breakout', 'sma50_breakout', 'trend_breakout', 'pin_up', 'hbs_breakout', 'vs_wakeup'}
        
        for strategy in self.strategies:
            if strategy in vsa_strategies:
                task = self._detect_vsa_strategy(strategy, df, symbol)
            elif strategy == 'volume_surge':
                task = self._detect_volume_surge(df, symbol)
            elif strategy == 'weak_uptrend':
                task = self._detect_weak_uptrend(df, symbol)
            elif strategy == 'pin_down':
                task = self._detect_pin_down(df, symbol)
            elif strategy == 'confluence':
                task = self._detect_confluence(df, symbol)
            elif strategy == 'bullish_engulfing':
                task = self._detect_bullish_engulfing(df, symbol)
            elif strategy in pattern_strategies:
                task = self._detect_pattern_strategy(strategy, df, symbol)
            else:
                logging.warning(f"Unknown strategy: {strategy}")
                continue
            
            strategy_tasks.append((strategy, task))
        
        # Execute all strategies in parallel with error handling
        results = {}
        try:
            strategy_results = await asyncio.gather(
                *[task for _, task in strategy_tasks], 
                return_exceptions=True
            )
            
            # Process results
            for (strategy, _), result in zip(strategy_tasks, strategy_results):
                if isinstance(result, Exception):
                    logging.error(f"Strategy {strategy} failed for {symbol}: {result}")
                    continue
                    
                if result is not None:
                    results[strategy] = result
                    logging.info(f"{strategy} detected for {symbol}")
                    
        except Exception as e:
            logging.error(f"Error in parallel strategy execution for {symbol}: {e}")
        
        return results

    async def send_to_database(self, results):
        """Send scan results to database - only for specified strategies"""
        from utils.config import DATABASE_CONFIG
        
        # Only process these strategies for database insertion (including bullish_engulfing)
        SUPPORTED_STRATEGIES = {
            "confluence", "consolidation_breakout", "channel_breakout", 
            "sma50_breakout", "pin_up", "trend_breakout", "loaded_bar",
            "bullish_engulfing"
        }
        
        if not DATABASE_CONFIG.get("enabled", False):
            return
        
        MarketEvent, insert_market_event = self._import_database_utils()
        if not MarketEvent or not insert_market_event:
            return
        
        conn_string = DATABASE_CONFIG.get("connection_string")
        if not conn_string:
            logging.error("Database connection string not configured")
            return
        
        # Filter results to only include supported strategies
        filtered_results = {
            strategy: res_list for strategy, res_list in results.items() 
            if strategy in SUPPORTED_STRATEGIES and res_list
        }
        
        if not filtered_results:
            logging.debug("No database-supported strategies found in results")
            return
        
        try:
            # Group results by symbol to create consolidated events
            symbol_events = {}
            
            for strategy, res_list in filtered_results.items():
                for result in res_list:
                    symbol = result.get('symbol')
                    if not symbol:
                        continue
                    
                    # Create base event if doesn't exist
                    if symbol not in symbol_events:
                        symbol_events[symbol] = self._create_market_event(result, MarketEvent)
                    
                    # Add strategy-specific flags
                    self._add_strategy_flags(symbol_events[symbol], strategy, result)
            
            # Insert all events
            for symbol, event in symbol_events.items():
                try:
                    insert_market_event(event, conn_string)
                    logging.info(f"Database: Inserted {symbol} on {self.exchange_name}")
                except Exception as e:
                    logging.error(f"Database: Failed to insert {symbol}: {e}")
                    
            # Log unsupported strategies
            unsupported = [s for s in results.keys() if s not in SUPPORTED_STRATEGIES and results[s]]
            if unsupported:
                logging.info(f"Database: Skipped unsupported strategies: {unsupported}")
                    
        except Exception as e:
            logging.error(f"Database insertion error: {e}")

    def _create_market_event(self, result, MarketEvent):
        """Create MarketEvent from scan result"""
        symbol = result.get('symbol', 'Unknown')
        symbol_clean = symbol.replace('USDT', '').rstrip('_-')
        timeframe = self.exchange_client.timeframe
    
        # Generate TradingView link
        tv_symbol = symbol.replace('_', '').replace('-', '')
        tv_timeframe = timeframe.upper() if timeframe.upper() != "4H" else "240"
        suffix = ".P" if "Futures" in self.exchange_name else ""
        tv_exchange = self.exchange_name.upper().replace(" ", "").replace("FUTURES", "").replace("SPOT", "")
        tv_link = f"https://www.tradingview.com/chart/?symbol={tv_exchange}:{tv_symbol}{suffix}&interval={tv_timeframe}"
    
        # Parse date
        date_value = result.get('date') or result.get('timestamp')
        if hasattr(date_value, 'to_pydatetime'):
            date_value = date_value.to_pydatetime()
        elif isinstance(date_value, str):
            try:
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                date_value = datetime.utcnow()
        elif not isinstance(date_value, datetime):
            date_value = datetime.utcnow()
    
        # Remove timezone for database
        if date_value.tzinfo:
            date_value = date_value.replace(tzinfo=None)
    
        return MarketEvent(
            Symbol=symbol_clean,
            Exchange=self.exchange_name.upper().replace(" ", "_"),
            Timeframe=timeframe,
            Date=date_value,
            TradingViewLink=tv_link,
            Close=Decimal(str(result.get('close', 0))),
            VolumeUsd=Decimal(str(result.get('volume_usd', 0))),
            CloseOffLow=Decimal(str(result.get('close_off_low', 0))),
            # Initialize all flags / fields
            PinDown=False,
            Confluence=False,
            IsConfReversalEngulfing=False,
            ConsolidationBo=False,
            ConsolidationBoDirectionBo=0,
            ConsolidationBoBoxAge=0,
            ConsolidationBoBoxHeight=Decimal('0.0'),
            ConsolidationBoStrength="",   # ← string: "Strong" / "Regular"
            ChannelBo=False,
            ChannelBoChannelDirection=0,
            ChannelBoChannelAge=0,
            ChannelBoChannelSlope=0.0,
            ChannelBoChannelHeight=Decimal('0.0'),
            WedgeBo=False,
            WedgeBoChannelDirection=0,
            WedgeBoChannelAge=0,
            WedgeBoChannelSlope=0.0,
            WedgeBoChannelHeight=Decimal('0.0'),
            Sma50Bo=False,
            Sma50BoType="",
            Sma50BoStrength="",           # ← string: "Strong" / "Regular"
            PinUp=False,                  
            TrendBo=False,                
            LoadedBar=False,
            IsBullishEngulfing=False        # New field for bullish engulfing
        )


    def _add_strategy_flags(self, event, strategy, result):
        """Add strategy-specific flags to MarketEvent - only for supported strategies"""
        try:
            if strategy == 'confluence':
                event.Confluence = True
                event.IsEngulfing = result.get('is_engulfing_reversal', False)
    
            elif strategy == 'consolidation_breakout':
                event.ConsolidationBo = True
                direction = result.get('direction', 'Unknown')
                event.ConsolidationBoDirectionBo = 1 if direction == 'Up' else -1 if direction == 'Down' else 0
                event.ConsolidationBoBoxAge = result.get('box_age', 0)
                event.ConsolidationBoBoxHeight = Decimal(str(result.get('height_pct', 0)))
    
                # Strength as string: "Strong" / "Regular"
                # Prefer explicit label if present; otherwise map boolean
                strength_label = result.get('strength_label')
                if not strength_label:
                    strength_label = "Strong" if result.get('strong', False) else "Regular"
                event.ConsolidationBoStrength = strength_label
    
            elif strategy == 'channel_breakout':
                event.ChannelBo = True
                direction = result.get('direction', 'Unknown')
                event.ChannelBoChannelDirection = 1 if direction == 'Up' else -1 if direction == 'Down' else 0
                event.ChannelBoChannelAge = result.get('channel_age', 0)
                event.ChannelBoChannelSlope = result.get('channel_slope', 0.0)
                event.ChannelBoChannelHeight = Decimal(str(result.get('height_pct', 0)))
    
            elif strategy == 'sma50_breakout':
                event.Sma50Bo = True
                br_type = result.get('breakout_type', '')
                event.Sma50BoType = br_type  # "regular" or "pre_breakout"
                strength_label = result.get('strength_label', '')
                event.Sma50BoStrength = strength_label if br_type == 'regular' else ""
                
            elif strategy == 'pin_up':
                event.PinUp = True

            elif strategy == 'trend_breakout':
                event.TrendBo = True
    
            elif strategy == 'loaded_bar':
                event.LoadedBar = True
                
            elif strategy == 'bullish_engulfing':
                event.IsBullishEngulfing  = True
       
            else:
                logging.debug(f"Strategy {strategy} not mapped to database columns")
    
        except Exception as e:
            logging.error(f"Error adding {strategy} flags to database event: {e}")


    async def send_telegram_message(self, strategy, results):
        """Send telegram messages with same formatting as original, with strength wording normalized"""
        if not results or strategy not in self.telegram_config or strategy not in self.telegram_apps:
            return
        try:
            chat_ids = self.telegram_config[strategy].get('chat_ids', [])
            if not chat_ids:
                return
            timeframe = self.exchange_client.timeframe
            title = self.strategy_titles.get(strategy, strategy.replace('_', ' ').title())
            
            header = f"🚨 {title} - {self.exchange_name} {timeframe.upper()}\n\n"
            signal_messages = []
            
            vsa_strategies = {'breakout_bar', 'stop_bar', 'reversal_bar', 'start_bar', 'loaded_bar', 'test_bar'}
            
            for result in results:
                symbol = result.get('symbol', 'Unknown')
                tv_symbol = symbol.replace('_', '').replace('-', '')
                tv_timeframe = timeframe.upper() if timeframe.upper() != "4H" else "240"
                suffix = ".P" if "Futures" in self.exchange_name else ""
                tv_exchange = self.exchange_name.upper().replace(" ", "").replace("FUTURES", "").replace("SPOT", "")
                tv_link = f"https://www.tradingview.com/chart/?symbol={tv_exchange}:{tv_symbol}{suffix}&interval={tv_timeframe}"
                
                raw_date = result.get('date') or result.get('timestamp')
                if hasattr(raw_date, 'strftime'):
                    date = raw_date.strftime('%Y-%m-%d')
                elif isinstance(raw_date, str):
                    try:
                        parsed_date = pd.to_datetime(raw_date)
                        date = parsed_date.strftime('%Y-%m-%d')
                    except:
                        date = raw_date
                else:
                    date = str(raw_date)
                    
                bar_status = "CURRENT BAR" if result.get('current_bar') else "Last Closed Bar"
                volume_period = "Weekly" if timeframe == "1w" else \
                                "4-Day" if timeframe == "4d" else \
                                "3-Day" if timeframe == "3d" else \
                                "2-Day" if timeframe == "2d" else \
                                "Daily" if timeframe == "1d" else \
                                "4-Hour"

                # Format messages
                if strategy in vsa_strategies:
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
                elif strategy == 'bullish_engulfing':
                    volume_usd = result.get('volume_usd', 0)
                    price_formatted = f"${result.get('close', 0):,.2f}"
                    volume_formatted = f"${volume_usd:,.1f}M" if volume_usd >= 1000000 else f"${volume_usd:,.0f}"
                    
                    signal_message = (
                        f"<a href='{tv_link}'>{symbol}</a> | {price_formatted} | Vol: {volume_formatted}\n"
                        f"Time: {date} | {bar_status}\n"
                        f"----\n"
                        f"Close Position: {result.get('close_position', 0):,.2f}\n"
                        f"Volume Ratio: {result.get('volume_ratio', 0):,.2f}x\n"
                        f"PR Low 21: {result.get('pr_low_21', 0):,.1f}%\n"
                        f"PR HL2 13: {result.get('pr_hl2_13', 0):,.1f}%\n"
                        f"PR Spread 21: {result.get('pr_spread_21', 0):,.1f}%\n"
                        f"Buying Power: {'✓' if result.get('is_buying_power', False) else '✗'}\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'hbs_breakout':
                    volume_usd = result.get('volume_usd', 0)
                    direction = result.get('direction', 'Unknown')
                    
                    direction_display = "🟢⬆️ UP" if direction == "Up" else "🔴⬇️ DOWN" if direction == "Down" else "⚪ NEUTRAL"
                    
                    context = result.get('breakout_type', '')
                    context_display = "📈 Both" if context == 'both' else "␥ Channel BO" if context == 'channel_breakout' else "☲ Consolidation BO"
                    
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
                    
                    # Strength display (Consolidation only): Strong / Regular
                    strength_display = ""
                    if context == "consolidation_breakout":
                        lbl = _normalize_strength_label(result.get('strength_label', ''))
                        strength_display = "💪 STRONG" if lbl == "Strong" else "😔 REGULAR"
                    
                    # Component analysis
                    component_lines = []
                    if result.get('has_sma50_breakout', False):
                        sma50_type = result.get('sma50_breakout_type', '')
                        sma_status = "Pre-Breakout" if sma50_type == "pre_breakout" else "Regular" if sma50_type == "regular" else sma50_type.replace('_', ' ').title()
                        sma_indicator = f"✅ 50SMA: {sma_status}"
                        s50_label = _normalize_strength_label(result.get('sma50_breakout_strength', ''))
                        # Only add strength suffix for 'regular' type
                        if sma50_type == "regular" and s50_label:
                            sma_indicator += f" ({s50_label})"
                        component_lines.append(sma_indicator)
                    
                    if result.get('has_engulfing_reversal', False):
                        component_lines.append(f"✅ Engulfing Reversal: {result.get('confluence_direction', 'Up')}")
                   
                    if result.get('has_volume_breakout', False):
                        component_lines.append("✅ Volume breakout")
                                        
                    price_formatted = f"${result.get('close', 0):,.2f}"
                    volume_formatted = f"${volume_usd:,.1f}M" if volume_usd >= 1000000 else f"${volume_usd:,.0f}"
                    
                    signal_message = (
                        f"<a href='{tv_link}'>{symbol}</a> | {price_formatted} | Vol: {volume_formatted}\n"
                        f"Time: {date} | {bar_status}\n"
                        f"----\n"
                        f"Close Position: {result.get('close_position_indicator', '○○○')} ({result.get('close_position_pct', 0):,.1f}%)\n"
                        f"Context: {context_display}\n"
                    )
                    
                    if strength_display:
                        signal_message += f"Strength: {strength_display}\n"
                    
                    signal_message += (
                        f"Is extreme: {extreme_display}\n"
                        f"Direction: {direction_display}\n"
                    )
                    
                    if component_lines:
                        signal_message += "----\n"
                        for component in component_lines:
                            signal_message += f"{component}\n"
                    
                    signal_message += f"{'='*30}\n"
                elif strategy == 'vs_wakeup':
                    volume_usd = result.get('volume_usd', 0)
                    price_formatted = f"${result.get('close', 0):,.2f}"
                    volume_formatted = f"${volume_usd:,.1f}M" if volume_usd >= 1000000 else f"${volume_usd:,.0f}K" if volume_usd >= 1000 else f"${volume_usd:,.0f}"
                    
                    signal_message = (
                        f"<a href='{tv_link}'>{symbol}</a> | {price_formatted} | Vol: {volume_formatted}\n"
                        f"Time: {date} | {bar_status}\n"
                        f"----\n"
                        f"Close Position: {result.get('close_position_indicator', '○○○')} ({result.get('close_position_pct', 0):,.1f}%)\n"
                        f"Box age: {result.get('box_age', 0)} bars\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'consolidation_breakout':
                    # Special formatting for consolidation breakout with Strong/Regular
                    direction = result.get('direction', 'Unknown')
                    strong_bool = bool(result.get('strong', False))
                    strength_display = "💪 STRONG" if strong_bool else "😔 REGULAR"
                    breakout_type = result.get('breakout_type', '')
                    type_display = breakout_type.replace('_', ' ').title()
                    
                    volume_usd = result.get('volume_usd', 0)
                    price_formatted = f"${result.get('close', 0):,.2f}"
                    volume_formatted = f"${volume_usd:,.1f}M" if volume_usd >= 1000000 else f"${volume_usd:,.0f}"
                    direction_display = "🟢⬆️ UP" if direction == "Up" else "🔴⬇️ DOWN" if direction == "Down" else "⚪ NEUTRAL"
                    
                    signal_message = (
                        f"<a href='{tv_link}'>{symbol}</a> | {price_formatted} | Vol: {volume_formatted}\n"
                        f"Time: {date} | {bar_status}\n"
                        f"----\n"
                        f"Close Position: {result.get('close_position_indicator', '○○○')} ({result.get('close_position_pct', 0):,.1f}%)\n"
                        f"Direction: {direction_display}\n"
                        f"Strength: {strength_display}\n"
                        f"Type: {type_display}\n"
                        f"Box Age: {result.get('box_age', 0)} bars\n"
                        f"Channel Ratio: {result.get('channel_ratio', 1.0):.2f}\n"
                        f"{'='*30}\n"
                    )
                elif strategy == 'sma50_breakout':
                    br_type = result.get('breakout_type', '')
                    br_type_disp = 'Regular' if br_type == 'regular' else 'Pre-Breakout'
                    strength_label = _normalize_strength_label(result.get('strength_label', ''))
                    strength_disp = f"💪 {strength_label.upper()}" if (br_type == 'regular' and strength_label) else "—"

                    price_formatted = f"${result.get('close', 0):,.2f}"
                    volume_usd = result.get('volume_usd', 0)
                    volume_formatted = f"${volume_usd:,.1f}M" if volume_usd >= 1_000_000 else f"${volume_usd:,.0f}"

                    signal_message = (
                        f"<a href='{tv_link}'>{symbol}</a> | {price_formatted} | Vol: {volume_formatted}\n"
                        f"Time: {date} | {bar_status}\n"
                        f"----\n"
                        f"Type: {br_type_disp}\n"
                        f"Strength: {strength_disp}\n"
                        f"Close Position: {result.get('close_position_indicator', '○○○')} "
                        f"({result.get('close_position_pct', 0):,.1f}%)\n"
                        f"{'='*30}\n"
                    )
                else:
                    # Generic format for other strategies
                    signal_message = (
                        f"Symbol: {symbol}\n"
                        f"Time: {date} - {bar_status}\n"
                        f"Close: <a href='{tv_link}'>${result.get('close', 0):,.8f}</a>\n"
                        f"{'='*30}\n"
                    )
                
                signal_messages.append(signal_message)
            
            # Send with chunking
            app = self.telegram_apps[strategy]
            if not hasattr(app, '_initialized') or not app._initialized:
                await app.initialize()
                await app.start()
            
            for chat_id in chat_ids:
                max_message_size = 4000
                current_chunk = header
                
                for signal in signal_messages:
                    if len(current_chunk) + len(signal) > max_message_size:
                        await app.bot.send_message(
                            chat_id=chat_id, text=current_chunk, 
                            parse_mode='HTML', disable_web_page_preview=True
                        )
                        await asyncio.sleep(0.3)
                        current_chunk = header + signal
                    else:
                        current_chunk += signal
                
                if current_chunk and current_chunk != header:
                    await app.bot.send_message(
                        chat_id=chat_id, text=current_chunk, 
                        parse_mode='HTML', disable_web_page_preview=True
                    )
                    
        except Exception as e:
            logging.error(f"Error sending {strategy} Telegram message: {str(e)}")

    async def scan_all_markets(self):
        """Scan all markets with optimized batching, parallel strategies, and database integration"""
        try:
            await self.init_session()
            symbols = await self.exchange_client.get_all_spot_symbols()
            timeframe = self.exchange_client.timeframe
            logging.info(f"Found {len(symbols)} markets on {self.exchange_name} for {timeframe} timeframe")
            
            all_results = {strategy: [] for strategy in self.strategies}
            
            logging.info(f"Processing {len(symbols)} symbols with parallel strategies (batch size: {self.batch_size})")
            for i in range(0, len(symbols), self.batch_size):
                batch = symbols[i:i + self.batch_size]
                tasks = [self.scan_market(symbol) for symbol in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logging.error(f"Batch scan error: {result}")
                        continue
                        
                    if isinstance(result, dict) and result:
                        for strategy, res in result.items():
                            if res:
                                all_results[strategy].append(res)
                
                await asyncio.sleep(0.5)  # Rate limiting
            
            # Send telegram messages
            for strategy, results in all_results.items():
                if results and strategy in self.telegram_config:
                    await self.send_telegram_message(strategy, results)
            
            # Send to database
            await self.send_to_database(all_results)
                    
            return all_results
            
        except Exception as e:
            logging.error(f"Error in scan_all_markets: {str(e)}")
            return {strategy: [] for strategy in self.strategies}
        finally:
            await self.close_session()

# Cache management utilities
def clear_cache_for_timeframe(timeframe):
    """Clear cache entries for a specific timeframe"""
    keys_to_remove = [k for k in kline_cache.keys() if f"_{timeframe}_" in k]
    for key in keys_to_remove:
        del kline_cache[key]
    logging.info(f"Cleared {len(keys_to_remove)} cache entries for timeframe {timeframe}")

def clear_all_cache():
    """Clear all cache entries"""
    count = len(kline_cache)
    kline_cache.clear()
    logging.info(f"Cleared all {count} cache entries")

async def run_scanner(exchange, timeframe, strategies, telegram_config=None, min_volume_usd=None, check_bar="last_closed"):
    """Main entry point - same API as original"""
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
    scanner = UnifiedScanner(client, strategies, telegram_config, min_volume_usd, check_bar=check_bar)
    return await scanner.scan_all_markets()