# exchanges/kucoin_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
import re
from datetime import datetime, timedelta
from .base_client import BaseExchangeClient


class KucoinClient(BaseExchangeClient):
    """
    KuCoin Spot API client for fetching market data (1d, 2d, 3d, 4d, 1w, 4h).

    Notes:
    - /api/v1/market/candles returns ≤1500 rows per call; 'limit' is ignored.
    - Pagination is done with BOTH startAt and endAt (seconds) for reliability.
    - Response order is newest -> oldest; we sort ascending before aggregating.
    - We return a tz-naive DateTimeIndex to avoid tz-aware/naive mix elsewhere.
    - Symbol format for KuCoin spot is 'BASE-QUOTE' (e.g., 'BTC-USDT').
    """

    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.kucoin.com"
        self.batch_size = 20
        self.request_delay = 0.2
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to KuCoin spot intervals."""
        return {
            '1w': '1week',  # we'll still build Monday-based weeks from 1d below
            '4d': '1day',
            '3d': '1day',
            '2d': '1day',
            '1d': '1day',
            '4h': '4hour'
        }

    # def _get_fetch_limit(self):
    #     # Kept for compatibility; paging is driven by _required_source_count.
    #     return {
    #         '1w': 360,
    #         '4d': 360,
    #         '3d': 360,
    #         '2d': 360,
    #         '1d': 360,
    #         '4h': 60
    #     }[self.timeframe]
    def _get_fetch_limit(self):
        return {
            '1w': 60,      # 60 weekly candles (direct from API)
            '4d': 240,     # 220 daily → aggregate to ~55 4d candles  
            '3d': 180,     # 170 daily → aggregate to ~56 3d candles
            '2d': 120,     # 110 daily → aggregate to 55 2d candles
            '1d': 60,      # 60 daily candles (direct from API)
            '4h': 60       # 60 4h candles (direct from API)
        }[self.timeframe]

    def _required_source_count(self, sma_len: int = 50, warmup: int = 10) -> int:
        """
        Minimum number of source (1d) candles to compute SMA(sma_len) on aggregated frames.
        """
        if self.timeframe in ('2d', '3d', '4d', '1w'):
            mult = {'2d': 2, '3d': 3, '4d': 4, '1w': 7}[self.timeframe]
            return (sma_len + warmup) * mult
        return sma_len + warmup  # native frames (1d, 4h)

    async def get_all_spot_symbols(self):
        """Fetch all active USDT spot trading pairs from KuCoin, excluding leveraged tokens."""
        url = f"{self.base_url}/api/v1/symbols"
        # Common leveraged token suffixes (before -USDT)
        leverage_suffixes = {'2L', '2S', '3L', '3S', '5L', '5S'}  # Add more if needed (e.g., '10L')
        
        try:
            async with self.session.get(url) as response:
                data = await response.json()
            if data.get('code') == '200000' and 'data' in data:
                symbols = [
                    item['symbol'] for item in data['data']
                    if (item.get('quoteCurrency') == self.quote_currency and 
                        item.get('enableTrading', False) and
                        not any(item['symbol'].split('-')[0].endswith(suffix) for suffix in leverage_suffixes))
                ]
                return sorted(symbols)
            logging.error(f"Error fetching KuCoin spot symbols: {data}")
            return []
        except Exception as e:
            logging.error(f"Error fetching KuCoin spot symbols: {str(e)}")
            return []

    async def fetch_klines(self, symbol: str):
        """
        Fetch candlestick data from KuCoin spot with robust time-based pagination.
        Returns a tz-naive OHLCV DataFrame indexed by timestamps.
        """
        url = f"{self.base_url}/api/v1/market/candles"
        symbol = symbol.replace('_', '-').upper()  # ensure spot format

        # For aggregated frames, always pull 1day to build 2d/3d/4d/1w yourself
        api_interval = '1day' if self.timeframe in ('2d', '3d', '4d', '1w') else self.interval_map[self.timeframe]
        target_count = self._required_source_count()

        # seconds-based time windowing
        now_s = int(time.time())

        # step size per request in SECONDS for each interval (1500 bars max per call)
        interval_seconds = {
            '1min': 60, '3min': 180, '5min': 300, '15min': 900, '30min': 1800,
            '1hour': 3600, '2hour': 7200, '4hour': 14400, '6hour': 21600,
            '8hour': 28800, '12hour': 43200, '1day': 86400, '1week': 604800
        }[api_interval]
        window_seconds = 1500 * interval_seconds  # max span we can request per call

        end_at = now_s
        rows = []

        try:
            while len(rows) < target_count:
                start_at = max(0, end_at - window_seconds + interval_seconds)  # inclusive window
                params = {
                    'symbol': symbol,
                    'type': api_interval,
                    'startAt': start_at,
                    'endAt': end_at
                }
                async with self.session.get(url, params=params) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logging.error(f"KuCoin spot klines HTTP {resp.status} for {symbol}: {text}")
                        return None
                    payload = await resp.json()

                if payload.get('code') != '200000':
                    logging.error(f"KuCoin spot klines API error for {symbol}: {payload}")
                    return None

                batch = payload.get('data') or []
                if not batch:
                    # no more older data
                    break

                # API returns newest -> oldest; extend and step the window backward
                rows.extend(batch)
                earliest_ts = int(batch[-1][0])  # seconds, oldest item in this batch
                # Next window ends just before the earliest bar we already have
                end_at = earliest_ts - 1

                await asyncio.sleep(self.request_delay)

                # If the window got us fewer than the theoretical max, we're near the start of history
                if len(batch) < 1500 and (end_at - start_at + 1) < window_seconds:
                    # still continue until target_count or until the API runs out
                    continue

            if not rows:
                logging.error(f"No klines returned for {symbol} @ {api_interval}")
                return None

            # KuCoin row: [time, open, close, high, low, volume, turnover]
            columns = ['timestamp', 'open', 'close', 'high', 'low', 'volume', 'turnover']
            df = pd.DataFrame(rows, columns=columns[:len(rows[0])])

            # Cast + index (timestamps are seconds) — keep tz-naive
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype('int64'), unit='s')
            # Normalize numeric columns
            for c in ['open', 'high', 'low', 'close', 'volume']:
                if c in df:
                    df[c] = pd.to_numeric(df[c], errors='coerce')

            # Reorder & sort ascending
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
            df = df.sort_values('timestamp').set_index('timestamp')

            # Force tz-naive just in case
            if getattr(df.index, "tz", None) is not None:
                df.index = df.index.tz_localize(None)

            # Aggregate if needed (use your existing helpers)
            if self.timeframe == '2d':
                df = self.aggregate_to_2d(df)
            elif self.timeframe == '3d':
                df = self.aggregate_to_3d(df)
            elif self.timeframe == '4d':
                df = self.aggregate_to_4d(df)
            elif self.timeframe == '1w':
                df = self.build_weekly_candles(df)  # Monday-based weeks via your helper

            return df

        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol} from KuCoin spot")
            return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol} from KuCoin spot: {str(e)}")
            return None
