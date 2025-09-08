# direct_test.py
# Historical Signals Scanner Module
# Save this file as direct_test.py in your project root directory

import asyncio
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings('ignore')

# Import exchange clients
from exchanges import (
    BinanceFuturesClient, BinanceSpotClient, BybitFuturesClient, BybitSpotClient,
    GateioFuturesClient, GateioSpotClient, KucoinSpotClient, MexcSpotClient, MexcFuturesClient
)

# Import strategy detectors
from custom_strategies import (
    detect_volume_surge, detect_weak_uptrend, detect_pin_down, detect_confluence,
    detect_consolidation, detect_consolidation_breakout, detect_channel_breakout,
    detect_sma50_breakout, detect_wedge_breakout, detect_channel
)
from breakout_vsa import (
    vsa_detector, breakout_bar_vsa, stop_bar_vsa, reversal_bar_vsa,
    start_bar_vsa, loaded_bar_vsa, test_bar_vsa
)

class HistoricalSignalScanner:
    """Scanner for detecting historical signals across multiple timeframes and strategies"""
    
    def __init__(self, exchange_name, timeframe="1d", limit=500):
        """
        Initialize the historical scanner
        
        Args:
            exchange_name: Exchange to scan (e.g., 'binance_futures', 'binance_spot', etc.)
            timeframe: Timeframe for analysis ('1h', '4h', '1d', '1w', etc.)
            limit: Number of historical candles to fetch (default: 500, max varies by exchange)
        """
        self.exchange_name = exchange_name
        self.timeframe = timeframe
        self.limit = min(limit, 1000)  # Cap at 1000 for safety
        
        # Exchange mapping
        self.exchange_map = {
            "binance_futures": BinanceFuturesClient,
            "binance_spot": BinanceSpotClient,
            "bybit_futures": BybitFuturesClient,
            "bybit_spot": BybitSpotClient,
            "gateio_futures": GateioFuturesClient,
            "gateio_spot": GateioSpotClient,
            "kucoin_spot": KucoinSpotClient,
            "mexc_spot": MexcSpotClient,
            "mexc_futures": MexcFuturesClient
        }
        
        # Available strategies
        self.available_strategies = [
            'volume_surge', 'weak_uptrend', 'pin_down', 'confluence',
            'consolidation', 'consolidation_breakout', 'channel_breakout',
            'channel', 'wedge_breakout', 'sma50_breakout', 'hbs_breakout',
            'breakout_bar', 'stop_bar', 'reversal_bar', 'start_bar', 'loaded_bar', 'test_bar'
        ]
        
        # VSA strategy mapping
        self.vsa_detectors = {
            'breakout_bar': breakout_bar_vsa,
            'stop_bar': stop_bar_vsa,
            'reversal_bar': reversal_bar_vsa,
            'start_bar': start_bar_vsa,
            'loaded_bar': loaded_bar_vsa,
            'test_bar': test_bar_vsa,
        }
        
        self.client = None
        
    async def initialize(self):
        """Initialize the exchange client"""
        if self.exchange_name not in self.exchange_map:
            raise ValueError(f"Unsupported exchange: {self.exchange_name}")
        
        client_class = self.exchange_map[self.exchange_name]
        self.client = client_class(timeframe=self.timeframe)
        await self.client.init_session()
        
    async def close(self):
        """Close the exchange client session"""
        if self.client:
            await self.client.close_session()
    
    def detect_strategy_signal(self, df, strategy, bar_idx):
        """
        Detect if a strategy signal occurs at a specific bar index
        
        Args:
            df: DataFrame with OHLCV data
            strategy: Strategy name to check
            bar_idx: Bar index to check (negative indexing from end)
            
        Returns:
            tuple: (detected: bool, result: dict)
        """
        try:
            if strategy in self.vsa_detectors:
                # VSA strategies
                if strategy == 'test_bar':
                    from breakout_vsa.core import test_bar_vsa
                    condition, result = test_bar_vsa(df)
                else:
                    # Get strategy parameters
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
                    
                    from breakout_vsa.core import vsa_detector
                    condition, result = vsa_detector(df, params)
                
                # Check if signal exists at the specified bar
                if len(condition) > abs(bar_idx) and condition.iloc[bar_idx]:
                    return True, {
                        'timestamp': df.index[bar_idx],
                        'close': df['close'].iloc[bar_idx],
                        'volume': df['volume'].iloc[bar_idx],
                        'high': df['high'].iloc[bar_idx],
                        'low': df['low'].iloc[bar_idx],
                        'strategy': strategy
                    }
                    
            elif strategy == 'volume_surge':
                detected, result = detect_volume_surge(df, check_bar=bar_idx)
                if detected:
                    return True, result
                    
            elif strategy == 'weak_uptrend':
                detected, result = detect_weak_uptrend(df)
                if detected and result.get('bar_index') == len(df) + bar_idx:
                    return True, result
                    
            elif strategy == 'pin_down':
                detected, result = detect_pin_down(df)
                if detected:
                    return True, result
                    
            elif strategy == 'confluence':
                detected, result = detect_confluence(df, check_bar=bar_idx, is_bullish=True)
                if detected:
                    return True, result
                    
            elif strategy == 'consolidation':
                detected, result = detect_consolidation(df, check_bar=bar_idx)
                if detected:
                    return True, result
                    
            elif strategy == 'consolidation_breakout':
                detected, result = detect_consolidation_breakout(df, check_bar=bar_idx)
                if detected:
                    return True, result
                    
            elif strategy == 'channel_breakout':
                detected, result = detect_channel_breakout(df, check_bar=bar_idx)
                if detected:
                    return True, result
                    
            elif strategy == 'channel':
                detected, result = detect_channel(df, check_bar=bar_idx)
                if detected:
                    return True, result
                    
            elif strategy == 'wedge_breakout':
                detected, result = detect_wedge_breakout(df, check_bar=bar_idx)
                if detected:
                    return True, result
                    
            elif strategy == 'sma50_breakout':
                detected, result = detect_sma50_breakout(df, check_bar=bar_idx)
                if detected:
                    return True, result
                    
            elif strategy == 'hbs_breakout':
                # HBS combines consolidation_breakout/channel_breakout + confluence
                cb_detected, cb_result = detect_consolidation_breakout(df, check_bar=bar_idx)
                chb_detected, chb_result = detect_channel_breakout(df, check_bar=bar_idx)
                cf_detected, cf_result = detect_confluence(df, check_bar=bar_idx)
                
                if cf_detected and (cb_detected or chb_detected):
                    breakout_result = chb_result if chb_detected else cb_result
                    return True, {**breakout_result, **cf_result, 'strategy': 'hbs_breakout'}
                    
            return False, None
            
        except Exception as e:
            logging.warning(f"Error detecting {strategy} at bar {bar_idx}: {str(e)}")
            return False, None
    
    async def scan_symbol_historical(self, symbol, strategies=None):
        """
        Scan a single symbol for historical signals
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            strategies: List of strategies to check (default: all available)
            
        Returns:
            dict: Dictionary with strategy names as keys and list of signals as values
        """
        if strategies is None:
            strategies = self.available_strategies
            
        # Fetch historical data
        df = await self.client.fetch_klines(symbol, limit=self.limit)
        if df is None or len(df) < 50:
            logging.warning(f"Insufficient data for {symbol}")
            return {}
        
        print(f"Scanning {symbol} - {len(df)} bars from {df.index[0]} to {df.index[-1]}")
        
        results = {strategy: [] for strategy in strategies}
        
        # Scan each bar for signals (skip last 2 bars to ensure we have enough context)
        for i in range(-len(df), -2):
            # Create a DataFrame up to the current bar
            current_df = df.iloc[:len(df) + i]
            
            if len(current_df) < 50:  # Minimum data requirement
                continue
                
            for strategy in strategies:
                detected, result = self.detect_strategy_signal(current_df, strategy, -1)
                if detected:
                    signal_data = {
                        'symbol': symbol,
                        'timestamp': current_df.index[-1],
                        'strategy': strategy,
                        'close': current_df['close'].iloc[-1],
                        'volume': current_df['volume'].iloc[-1],
                        'bar_index': len(current_df) - 1
                    }
                    
                    # Add strategy-specific data
                    if result:
                        signal_data.update(result)
                    
                    results[strategy].append(signal_data)
        
        # Filter out empty strategies
        results = {k: v for k, v in results.items() if v}
        
        total_signals = sum(len(signals) for signals in results.values())
        print(f"Found {total_signals} total signals for {symbol}")
        
        return results
    
    async def scan_multiple_symbols(self, symbols, strategies=None):
        """
        Scan multiple symbols for historical signals
        
        Args:
            symbols: List of trading pair symbols
            strategies: List of strategies to check (default: all available)
            
        Returns:
            dict: Nested dictionary {symbol: {strategy: [signals]}}
        """
        results = {}
        
        for symbol in symbols:
            try:
                symbol_results = await self.scan_symbol_historical(symbol, strategies)
                if symbol_results:
                    results[symbol] = symbol_results
                    
                # Small delay to avoid rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Error scanning {symbol}: {str(e)}")
                continue
        
        return results
    
    async def get_all_symbols(self, limit=None):
        """Get all available symbols from the exchange"""
        symbols = await self.client.get_all_spot_symbols()
        if limit:
            symbols = symbols[:limit]
        return symbols
    
    def create_signals_dataframe(self, scan_results):
        """
        Convert scan results to a pandas DataFrame for analysis
        
        Args:
            scan_results: Results from scan_symbol_historical or scan_multiple_symbols
            
        Returns:
            pd.DataFrame: Flattened DataFrame with all signals
        """
        all_signals = []
        
        # Handle single symbol results
        if isinstance(scan_results, dict) and not any(isinstance(v, dict) and 'strategy' not in v for v in scan_results.values()):
            for strategy, signals in scan_results.items():
                for signal in signals:
                    all_signals.append(signal)
        
        # Handle multiple symbol results
        else:
            for symbol, symbol_results in scan_results.items():
                for strategy, signals in symbol_results.items():
                    for signal in signals:
                        signal['symbol'] = symbol  # Ensure symbol is set
                        all_signals.append(signal)
        
        if not all_signals:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_signals)
        
        # Convert timestamp to datetime if it's not already
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df

# Utility functions for CSV handling

def save_signals_to_csv(df, filename=None, folder="historical_signals"):
    """
    Save signals DataFrame to CSV file
    
    Args:
        df: DataFrame with signals data
        filename: Custom filename (default: auto-generated with timestamp)
        folder: Folder to save in (default: "historical_signals")
    
    Returns:
        str: Path to saved file
    """
    # Create folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not df.empty:
            symbols = "_".join(df['symbol'].unique()[:3])  # First 3 symbols
            if len(df['symbol'].unique()) > 3:
                symbols += "_etc"
            strategies = "_".join(df['strategy'].unique()[:2])  # First 2 strategies
            if len(df['strategy'].unique()) > 2:
                strategies += "_etc"
            filename = f"signals_{symbols}_{strategies}_{timestamp}.csv"
        else:
            filename = f"signals_empty_{timestamp}.csv"
    
    # Ensure .csv extension
    if not filename.endswith('.csv'):
        filename += '.csv'
    
    filepath = os.path.join(folder, filename)
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    
    print(f"Signals saved to: {filepath}")
    print(f"Total rows: {len(df)}")
    
    return filepath

def load_signals_from_csv(filepath):
    """
    Load signals DataFrame from CSV file
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        pd.DataFrame: Loaded signals DataFrame
    """
    df = pd.read_csv(filepath)
    
    # Convert timestamp column back to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"Loaded {len(df)} signals from {filepath}")
    
    return df

def analyze_signals(df):
    """Analyze signal patterns in the DataFrame"""
    if df.empty:
        print("No signals found in the data")
        return
    
    print("=== SIGNAL ANALYSIS ===")
    print(f"Total signals: {len(df)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Unique symbols: {df['symbol'].nunique()}")
    print(f"Unique strategies: {df['strategy'].nunique()}")
    print()
    
    print("Signals by strategy:")
    strategy_counts = df['strategy'].value_counts()
    for strategy, count in strategy_counts.items():
        print(f"  {strategy}: {count}")
    print()
    
    if 'symbol' in df.columns:
        print("Top symbols by signal count:")
        symbol_counts = df['symbol'].value_counts().head(10)
        for symbol, count in symbol_counts.items():
            print(f"  {symbol}: {count}")
        print()
    
    # Monthly distribution
    df['month'] = df['timestamp'].dt.to_period('M')
    monthly_counts = df['month'].value_counts().sort_index()
    print("Monthly signal distribution:")
    for month, count in monthly_counts.items():
        print(f"  {month}: {count}")

def filter_signals(df, strategy=None, symbol=None, date_from=None, date_to=None):
    """Filter signals DataFrame based on criteria"""
    filtered = df.copy()
    
    if strategy:
        filtered = filtered[filtered['strategy'] == strategy]
    
    if symbol:
        filtered = filtered[filtered['symbol'] == symbol]
    
    if date_from:
        filtered = filtered[filtered['timestamp'] >= pd.to_datetime(date_from)]
    
    if date_to:
        filtered = filtered[filtered['timestamp'] <= pd.to_datetime(date_to)]
    
    return filtered

# Convenience functions for quick analysis with auto-save option

async def scan_btc_historical(exchange="binance_futures", timeframe="1d", limit=300, strategies=None, save_csv=True):
    """Quick function to scan BTC historical signals"""
    scanner = HistoricalSignalScanner(exchange, timeframe, limit)
    try:
        await scanner.initialize()
        results = await scanner.scan_symbol_historical("BTCUSDT", strategies)
        df = scanner.create_signals_dataframe(results)
        
        if save_csv and not df.empty:
            save_signals_to_csv(df, filename=f"BTC_{exchange}_{timeframe}_{limit}bars")
        
        return df
    finally:
        await scanner.close()

async def scan_exchange_historical(exchange="binance_futures", timeframe="1d", limit=300, 
                                 strategies=None, max_symbols=10, save_csv=True):
    """Quick function to scan multiple symbols from an exchange"""
    scanner = HistoricalSignalScanner(exchange, timeframe, limit)
    try:
        await scanner.initialize()
        symbols = await scanner.get_all_symbols(limit=max_symbols)
        results = await scanner.scan_multiple_symbols(symbols, strategies)
        df = scanner.create_signals_dataframe(results)
        
        if save_csv and not df.empty:
            save_signals_to_csv(df, filename=f"{exchange}_{timeframe}_{max_symbols}symbols_{limit}bars")
        
        return df
    finally:
        await scanner.close()

# Main execution function for command line usage
async def main():
    """Main function for standalone execution"""
    logging.basicConfig(level=logging.INFO)
    
    # Example usage - customize as needed
    print("Starting historical signal scan...")
    
    # Scan BTC on Binance Futures
    df = await scan_btc_historical("binance_futures", "1d", 
                                   strategies=['confluence', 'wedge_breakout', 'channel_breakout'])
    
    if not df.empty:
        analyze_signals(df)
    else:
        print("No signals found")

if __name__ == "__main__":
    asyncio.run(main())