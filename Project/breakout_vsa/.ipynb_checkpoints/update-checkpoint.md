## Adding a New Strategy

1. **Create a new strategy file**:
   - Add a new file in `breakout_vsa/strategies/`, e.g., `new_strategy.py`
   - Define the strategy parameters:
   ```python
   def get_params():
       return {
           # Basic indicators
           'lookback': 14,
           'direction_opt': "Up",
           # ...other parameters
       }


2. Update the strategies __init__.py:
# breakout_vsa/strategies/__init__.py
from . import breakout_bar, stop_bar, reversal_bar, new_strategy

# Export strategy modules
__all__ = ['breakout_bar', 'stop_bar', 'reversal_bar', 'new_strategy']




3. Update the main __init__.py:
   
# breakout_vsa/__init__.py
from .core import vsa_detector, breakout_bar_vsa, stop_bar_vsa, reversal_bar_vsa, new_strategy_vsa

__all__ = ['vsa_detector', 'breakout_bar_vsa', 'stop_bar_vsa', 'reversal_bar_vsa', 'new_strategy_vsa']


4. Update the core.py file:

# Add a new function for your strategy
def new_strategy_vsa(df):
    return vsa_detector(df, 'new_strategy')


5. Update scanner.py to include the new strategy:

# In the scan_single_market method
if self.strategy == "new_strategy":
    signals = new_strategy_vsa(df)



