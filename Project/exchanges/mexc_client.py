#exchanges/mexc_spot_client.py

import asyncio
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from .base_client import BaseExchangeClient


class MexcClient(BaseExchangeClient):
    """
    MEXC Spot API client for fetching market data (1d, 2d, 3d, 4d, 1w, 4h).

    Notes:
    - /api/v3/klines returns up to 1000 rows; we page by time (ms) using endTime.
    - For 2d/3d/4d/1w we fetch 1d source bars then aggregate.
    - We return a tz-naive DateTimeIndex to avoid tz-naive/aware mix elsewhere.
    - Spot symbol format is 'BTCUSDT' (no underscore).
    """

    def __init__(self, timeframe="1d"):
        self.base_url = "https://api.mexc.com"
        self.batch_size = 20
        self.request_delay = 0.2
        super().__init__(timeframe)

    def _get_interval_map(self):
        """Map standard timeframes to MEXC spot intervals."""
        return {
            '1w': '1d',   # build weekly from daily
            '4d': '1d',   # build 4d from daily
            '3d': '1d',   # build 3d from daily
            '2d': '1d',   # build 2d from daily
            '1d': '1d',   # native
            '4h': '4h'    # native
        }

    def _get_fetch_limit(self):
        # Kept for compatibility with BaseExchangeClient if referenced elsewhere.
        return {
            '1w': 360,
            '4d': 360,
            '3d': 360,
            '2d': 360,
            '1d': 360,
            '4h': 60
        }[self.timeframe]

    def _required_source_count(self, sma_len: int = 50, warmup: int = 10) -> int:
        """
        Minimum number of source (1d) candles to reliably compute SMA(sma_len)
        on the aggregated timeframe.
        """
        if self.timeframe in ('2d', '3d', '4d', '1w'):
            mult = {'2d': 2, '3d': 3, '4d': 4, '1w': 7}[self.timeframe]
            return (sma_len + warmup) * mult
        # native frames (1d, 4h)
        return sma_len + warmup

    async def get_all_spot_symbols(self):
        """Fetch all active USDT spot trading pairs from MEXC."""
        url = f"{self.base_url}/api/v3/exchangeInfo"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; mexc-fetch/1.0)"}
        try:
            async with self.session.get(url, headers=headers) as response:
                data = await response.json()
            if 'symbols' in data:
                symbols = [
                    s['symbol'] for s in data['symbols']
                    if s['symbol'].endswith(self.quote_currency) and s.get('status') == '1'
                ]
                return sorted(symbols)
            logging.error(f"Error fetching MEXC spot symbols: {data}")
            return []
        except Exception as e:
            logging.error(f"Error fetching MEXC spot symbols: {str(e)}")
            return []

    async def fetch_klines(self, symbol: str):
        """
        Fetch candlestick data from MEXC spot with time-based pagination.
        Returns a tz-naive OHLCV DataFrame indexed by timestamps.
        """
        url = f"{self.base_url}/api/v3/klines"
        symbol = symbol.replace('_', '').upper()  # ensure spot format

        headers = {"User-Agent": "Mozilla/5.0 (compatible; mexc-fetch/1.0)"}

        # Use 1d as source for multi-day/weekly aggregation; native otherwise
        api_interval = '1d' if self.timeframe in ('2d', '3d', '4d', '1w') else self.interval_map[self.timeframe]
        target_count = self._required_source_count()

        end_time = int(time.time() * 1000)  # ms
        rows = []

        try:
            while len(rows) < target_count:
                params = {
                    'symbol': symbol,
                    'interval': api_interval,
                    'endTime': end_time,
                    'limit': 1000  # max per request
                }
                async with self.session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logging.error(f"MEXC spot klines HTTP {resp.status} for {symbol}: {text}")
                        return None
                    data = await resp.json()

                if not isinstance(data, list) or not data:
                    break

                rows.extend(data)

                # Determine earliest open time robustly (handles asc/desc)
                first_ts = int(data[0][0])
                last_ts = int(data[-1][0])
                earliest_open_ms = min(first_ts, last_ts)

                # Page further back
                end_time = earliest_open_ms - 1
                await asyncio.sleep(self.request_delay)

                if len(data) < 1000:
                    break

            if not rows:
                logging.error(f"No klines returned for {symbol} @ {api_interval}")
                return None

            cols = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades',
                'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'
            ]
            df = pd.DataFrame(rows, columns=cols[:len(rows[0])])

            # Cast + index (timestamps are ms) — tz-naive on purpose
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp'], errors='coerce'), unit='ms')
            for c in ['open', 'high', 'low', 'close', 'volume']:
                if c in df:
                    df[c] = pd.to_numeric(df[c], errors='coerce')

            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
            df = df.sort_values('timestamp').set_index('timestamp')

            # Force tz-naive (safety in case any tz sneaks in)
            if getattr(df.index, "tz", None) is not None:
                df.index = df.index.tz_localize(None)

            # Aggregate if needed (your BaseExchangeClient helpers)
            if self.timeframe == '2d':
                df = self.aggregate_to_2d(df)
            elif self.timeframe == '3d':
                df = self.aggregate_to_3d(df)
            elif self.timeframe == '4d':
                df = self.aggregate_to_4d(df)
            elif self.timeframe == '1w':
                df = self.build_weekly_candles(df)

            return df

        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching klines for {symbol} from MEXC spot")
            return None
        except Exception as e:
            logging.error(f"Error fetching klines for {symbol} from MEXC spot: {str(e)}")
            return None
