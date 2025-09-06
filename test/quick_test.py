#!/usr/bin/env python3
# quick_test.py - Quick verification of test files

import sys
import os
import traceback

# Add root directory to path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

def test_imports():
    """Test all imports work correctly"""
    print("🔍 Testing imports...")
    
    try:
        from strategies.strategies import ForexStrategies, ExitConfig, ExitMethod
        print("✅ strategies.strategies imported successfully")
    except Exception as e:
        print(f"❌ strategies.strategies import failed: {e}")
        return False
    
    try:
        from strategies.candle_strategies import CandleStrategies, CandleExitConfig
        print("✅ strategies.candle_strategies imported successfully")
    except Exception as e:
        print(f"❌ strategies.candle_strategies import failed: {e}")
        return False
    
    try:
        from patterns.candlestickpatterns import CandlestickPatterns
        print("✅ patterns.candlestickpatterns imported successfully")
    except Exception as e:
        print(f"❌ patterns.candlestickpatterns import failed: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality of each module"""
    print("\n🧪 Testing basic functionality...")
    
    try:
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
        
        # Test ForexStrategies
        from strategies.strategies import ForexStrategies
        strategies = ForexStrategies(df)
        result = strategies.trend_following()
        print("✅ ForexStrategies.trend_following() works")
        
        # Test CandleStrategies
        from strategies.candle_strategies import CandleStrategies
        candle_strategies = CandleStrategies(df)
        result = candle_strategies.hammer_reversal_strategy()
        print("✅ CandleStrategies.hammer_reversal_strategy() works")
        
        # Test CandlestickPatterns
        from patterns.candlestickpatterns import CandlestickPatterns
        patterns = CandlestickPatterns(df)
        result = patterns.doji()
        print("✅ CandlestickPatterns.doji() works")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def run_individual_test(test_file):
    """Run an individual test file"""
    print(f"\n🧪 Running {test_file}...")
    
    try:
        # Import and run the test
        if test_file == "test_strategies.py":
            from test.test_strategies import main
            return main()
        elif test_file == "test_candlestick_patterns.py":
            from test.test_candlestick_patterns import main
            return main()
        elif test_file == "test_candle_strategies_comprehensive.py":
            from test.test_candle_strategies_comprehensive import main
            return main()
        else:
            print(f"❌ Unknown test file: {test_file}")
            return False
            
    except Exception as e:
        print(f"❌ {test_file} failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test runner"""
    print("🚀 QUICK TEST VERIFICATION")
    print("=" * 50)
    
    # Test imports first
    if not test_imports():
        print("\n❌ Import tests failed. Cannot proceed.")
        return False
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality tests failed.")
        return False
    
    # Run individual tests
    test_files = [
        "test_strategies.py",
        "test_candlestick_patterns.py", 
        "test_candle_strategies_comprehensive.py"
    ]
    
    passed = 0
    total = len(test_files)
    
    for test_file in test_files:
        if run_individual_test(test_file):
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"🏁 QUICK TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
