# test/test_strategies.py

import pandas as pd
import numpy as np
import sys
import os

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from strategies.strategies import ForexStrategies, ExitConfig, ExitMethod
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

def create_test_data():
    """Crea datos de prueba para strategies.py"""
    np.random.seed(42)
    
    # Generar datos más extensos para probar todas las estrategias
    dates = pd.date_range('2024-01-01', periods=500, freq='h')
    
    # Crear datos con tendencias y patrones específicos
    base_price = 1.1000
    trend = np.linspace(0, 0.0100, 500)  # Tendencia alcista
    noise = np.random.normal(0, 0.0015, 500)
    
    prices = base_price + trend + noise
    
    # Crear OHLC con volatilidad realista
    data = []
    for i, price in enumerate(prices):
        if i == 0:
            open_price = price
            high = price + abs(np.random.normal(0, 0.0008))
            low = price - abs(np.random.normal(0, 0.0008))
            close = price + np.random.normal(0, 0.0005)
        else:
            open_price = data[i-1]['Close']
            volatility = 0.0012
            
            # Añadir algunos movimientos específicos para probar estrategias
            if 100 <= i <= 120:  # Período de alta volatilidad
                volatility *= 2
            elif 200 <= i <= 220:  # Período de baja volatilidad
                volatility *= 0.5
            elif 300 <= i <= 320:  # Tendencia bajista fuerte
                trend_adjustment = -0.0020
            else:
                trend_adjustment = 0
            
            high = open_price + abs(np.random.normal(0, volatility))
            low = open_price - abs(np.random.normal(0, volatility))
            close = open_price + np.random.normal(trend_adjustment, volatility/2)
        
        data.append({
            'Open': open_price,
            'High': max(open_price, high, close),
            'Low': min(open_price, low, close),
            'Close': close
        })
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_forex_strategies_initialization():
    """Prueba la inicialización de ForexStrategies"""
    print("\n=== Testing ForexStrategies Initialization ===")
    
    data = create_test_data()
    
    try:
        strategies = ForexStrategies(data)
        print("✅ ForexStrategies initialized successfully")
        
        # Verificar que los datos se cargaron correctamente
        if len(strategies.data) == len(data):
            print("✅ Data loaded correctly")
        else:
            print("❌ Data length mismatch")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

def test_exit_config():
    """Prueba la configuración de ExitConfig"""
    print("\n=== Testing ExitConfig ===")
    
    try:
        # Configuración por defecto
        config = ExitConfig()
        print("✅ Default ExitConfig created")
        
        # Configuración personalizada
        custom_config = ExitConfig(
            method=ExitMethod.HYBRID,
            trailing_atr_mult=2.5,
            max_bars=30
        )
        print("✅ Custom ExitConfig created")
        
        # Verificar valores por defecto
        if config.method == ExitMethod.SIGNAL_REVERSAL:
            print("✅ Default exit method is SIGNAL_REVERSAL")
        else:
            print("❌ Wrong default exit method")
            return False
            
        return True
    except Exception as e:
        print(f"❌ ExitConfig test failed: {e}")
        return False

def test_basic_strategies():
    """Prueba estrategias básicas"""
    print("\n=== Testing Basic Strategies ===")
    
    data = create_test_data()
    strategies = ForexStrategies(data)
    
    basic_strategies = [
        ('trend_following', strategies.trend_following),
        ('rsi_strategy', strategies.rsi_strategy),
        ('bollinger_bands_strategy', strategies.bollinger_bands_strategy),
        ('macd_strategy', strategies.macd_strategy)
    ]
    
    passed = 0
    total = len(basic_strategies)
    
    for name, method in basic_strategies:
        try:
            result = method()
            
            # Verificar estructura básica
            required_cols = ['ExecSignal', 'Position']
            missing = [col for col in required_cols if col not in result.columns]
            
            if not missing:
                # Verificar valores válidos
                valid_exec = result['ExecSignal'].isin([-1, 0, 1]).all()
                valid_pos = result['Position'].isin([-1, 0, 1]).all()
                
                if valid_exec and valid_pos:
                    signals = (result['ExecSignal'] != 0).sum()
                    print(f"✅ {name}: Valid structure, {signals} signals")
                    passed += 1
                else:
                    print(f"❌ {name}: Invalid signal/position values")
            else:
                print(f"❌ {name}: Missing columns: {missing}")
                
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")
    
    print(f"📊 Basic strategies: {passed}/{total} passed")
    return passed == total

def test_advanced_strategies():
    """Prueba estrategias avanzadas"""
    print("\n=== Testing Advanced Strategies ===")
    
    data = create_test_data()
    strategies = ForexStrategies(data)
    
    # Configuración personalizada para estrategias avanzadas
    config = ExitConfig(
        method=ExitMethod.HYBRID,
        trailing_atr_mult=2.0,
        max_bars=25
    )
    
    advanced_strategies = [
        ('adx_strategy', lambda: strategies.adx_strategy(exit_config=config)),
        ('breakout', lambda: strategies.breakout(exit_config=config)),
        ('moving_average_crossover', lambda: strategies.moving_average_crossover(exit_config=config)),
        ('stochastic_strategy', lambda: strategies.stochastic_strategy(exit_config=config))
    ]
    
    passed = 0
    total = len(advanced_strategies)
    
    for name, method in advanced_strategies:
        try:
            result = method()
            
            # Verificar estructura completa
            required_cols = ['ExecSignal', 'Position', 'StopLoss', 'TakeProfit']
            missing = [col for col in required_cols if col not in result.columns]
            
            if not missing:
                signals = (result['ExecSignal'] != 0).sum()
                positions = (result['Position'] != 0).sum()
                
                # Verificar que se calcularon SL/TP
                has_sl = not result['StopLoss'].isna().all()
                has_tp = not result['TakeProfit'].isna().all()
                
                if has_sl and has_tp:
                    print(f"✅ {name}: Complete structure, {signals} signals, {positions} position periods")
                    passed += 1
                else:
                    print(f"❌ {name}: Missing SL/TP calculations")
            else:
                print(f"❌ {name}: Missing columns: {missing}")
                
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")
    
    print(f"📊 Advanced strategies: {passed}/{total} passed")
    return passed == total

def test_exit_methods():
    """Prueba diferentes métodos de cierre"""
    print("\n=== Testing Exit Methods ===")
    
    data = create_test_data()
    strategies = ForexStrategies(data)
    
    exit_methods = [
        ExitMethod.SIGNAL_REVERSAL,
        ExitMethod.TRAILING_STOP,
        ExitMethod.TIME_EXIT,
        ExitMethod.HYBRID
    ]
    
    passed = 0
    total = len(exit_methods)
    
    for method in exit_methods:
        try:
            config = ExitConfig(method=method)
            result = strategies.trend_following(exit_config=config)
            
            # Verificar que el método se aplicó
            if 'ExitReason' in result.columns:
                exit_reasons = result[result['ExitReason'] != '']['ExitReason'].unique()
                print(f"✅ {method.name}: Applied, exit reasons: {list(exit_reasons)}")
                passed += 1
            else:
                print(f"❌ {method.name}: No ExitReason column")
                
        except Exception as e:
            print(f"❌ {method.name}: Error - {str(e)}")
    
    print(f"📊 Exit methods: {passed}/{total} passed")
    return passed == total

def test_risk_management():
    """Prueba gestión de riesgo"""
    print("\n=== Testing Risk Management ===")
    
    data = create_test_data()
    strategies = ForexStrategies(data)
    
    try:
        # Estrategia con gestión de riesgo
        config = ExitConfig(
            method=ExitMethod.HYBRID,
            trailing_atr_mult=1.5
        )
        
        result = strategies.trend_following(exit_config=config)
        
        # Verificar que hay niveles de SL/TP
        entry_signals = result[result['ExecSignal'].abs() == 1]
        
        if len(entry_signals) > 0:
            # Verificar que se calcularon niveles para las entradas
            has_sl = not entry_signals['StopLoss'].isna().all()
            has_tp = not entry_signals['TakeProfit'].isna().all()
            
            if has_sl and has_tp:
                print("✅ Risk management: SL/TP calculated for entries")
                
                # Verificar que los niveles son lógicos
                long_entries = entry_signals[entry_signals['ExecSignal'] == 1]
                if len(long_entries) > 0:
                    sample = long_entries.iloc[0]
                    if sample['StopLoss'] < sample['Close'] < sample['TakeProfit']:
                        print("✅ Risk management: Logical SL/TP levels for long positions")
                        return True
                    else:
                        print("❌ Risk management: Illogical SL/TP levels")
                        return False
                else:
                    print("✅ Risk management: No long entries to verify (normal)")
                    return True
            else:
                print("❌ Risk management: Missing SL/TP calculations")
                return False
        else:
            print("ℹ️  Risk management: No entry signals to test (normal for some datasets)")
            return True
            
    except Exception as e:
        print(f"❌ Risk management test failed: {e}")
        return False

def main():
    """Función principal de tests para strategies.py"""
    print("🧪 Testing strategies.py Module")
    print("=" * 60)
    
    tests = [
        test_forex_strategies_initialization,
        test_exit_config,
        test_basic_strategies,
        test_advanced_strategies,
        test_exit_methods,
        test_risk_management
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n{'='*60}")
    print(f"🏁 STRATEGIES.PY TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! strategies.py module is working correctly.")
    else:
        print("⚠️  Some tests failed. Check output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
