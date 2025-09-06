import pandas as pd
import numpy as np

# Create simple test data
data = {
    'Open': [1.1000, 1.1010, 1.1005, 1.0995, 1.1020],
    'High': [1.1015, 1.1020, 1.1010, 1.1000, 1.1025],
    'Low': [1.0995, 1.1005, 1.0990, 1.0985, 1.1015],
    'Close': [1.1010, 1.1005, 1.0995, 1.1020, 1.1022]
}

df = pd.DataFrame(data)
print("Test data created:")
print(df)

try:
    from strategies.candle_strategies import CandleStrategies, CandleExitConfig
    print("\n✅ Import successful")
    
    # Test basic functionality
    strategies = CandleStrategies(df)
    print("✅ CandleStrategies instance created")
    
    # Test a simple strategy
    result = strategies.hammer_reversal_strategy()
    print("✅ hammer_reversal_strategy executed")
    
    # Check columns
    expected_cols = ['ExecSignal', 'Position', 'StopLoss', 'TakeProfit', 'ExitReason']
    missing = [col for col in expected_cols if col not in result.columns]
    
    if not missing:
        print("✅ All required columns present")
        print(f"Columns: {list(result.columns)}")
        
        # Show sample of results
        print("\nSample results:")
        print(result[['Close', 'Signal', 'ExecSignal', 'Position']].head())
        
    else:
        print(f"❌ Missing columns: {missing}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
