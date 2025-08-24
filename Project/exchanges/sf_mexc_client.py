# exchanges/sf_mexc_client.py
import pandas as pd
import sys
import os
from .base_client import BaseExchangeClient

# Import SF service
project_dir = os.path.join(os.getcwd(), "Project")
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from exchanges.sf_pairs_service import SFPairsService

class SFMexcClient(BaseExchangeClient):
    """
    SF-based MEXC client for fetching 1w data via Seven Figures service
    """
    
    def __init__(self, timeframe="1w"):
        self.exchange_name = "Mexc"
        self.sf_service = SFPairsService()
        super().__init__(timeframe)
    
    def _get_interval_map(self):
        """SF service only supports 1w for this client"""
        return {
            '1w': '1w'
        }
    
    def _get_fetch_limit(self):
        """Number of candles to fetch"""
        return {
            '1w': 60  # Fetch 60 weeks of data
        }[self.timeframe]
    
    async def get_all_spot_symbols(self):
        """Get all USDT symbols from SF service for MEXC"""
        try:
            all_pairs = self.sf_service.get_pairs_of_exchange(self.exchange_name)
            
            # Filter for USDT pairs and extract symbols
            symbols = []
            for pair in all_pairs:
                if 'Quote' in pair and pair['Quote'].upper() == "USDT":
                    token = pair.get('Token', '')
                    if token and token.upper() not in ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD']:
                        symbols.append(f"{token}USDT")
            
            print(f"✓ SF MEXC: Found {len(symbols)} USDT symbols")
            return symbols
            
        except Exception as e:
            print(f"❌ Error fetching SF MEXC symbols: {e}")
            return []
    
    def _prepare_sf_data(self, raw_df):
        """Convert SF data to strategy-compatible format"""
        if raw_df is None or len(raw_df) == 0:
            return None
        
        df = pd.DataFrame(raw_df)
        
        # Convert datetime column to pandas datetime and set as index
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
        elif 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            df = df.set_index('time')
        
        # Select only OHLCV columns needed
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        available_cols = [col for col in required_cols if col in df.columns]
        
        if len(available_cols) != 5:
            return None
        
        # Select and clean data
        result_df = df[required_cols].copy()
        
        # Ensure numeric types
        for col in required_cols:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
        
        # Drop any NaN rows
        result_df = result_df.dropna()
        
        # Sort by index (oldest first)
        result_df = result_df.sort_index()
        
        return result_df
    
    async def fetch_klines(self, symbol):
        """Fetch klines data for a symbol from SF service"""
        try:
            # Extract token from symbol (remove USDT)
            token = symbol.replace('USDT', '')
            
            # Get data from SF service (50 weeks for good analysis)
            raw_data = self.sf_service.get_ohlcv_for_pair(
                token, 'USDT', self.exchange_name, '1w', 50
            )
            
            if raw_data is None or len(raw_data) == 0:
                return None
            
            # Convert to strategy-compatible format
            df = self._prepare_sf_data(raw_data)
            return df
            
        except Exception as e:
            print(f"❌ Error fetching SF MEXC data for {symbol}: {e}")
            return None