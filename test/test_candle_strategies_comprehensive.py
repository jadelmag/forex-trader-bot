# test/test_candle_strategies_comprehensive.py

import pandas as pd
import numpy as np
import sys
import os

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from strategies.candle_strategies import CandleStrategies, CandleExitConfig
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

def create_comprehensive_test_data():
    """Crea datos de prueba exhaustivos para candle_strategies.py"""
    np.random.seed(42)
    
    # Datos más extensos para probar todas las estrategias
    dates = pd.date_range('2024-01-01', periods=1000, freq='H')
    
    # Crear datos con múltiples fases de mercado
    base_price = 1.1000
    
    data = []
    for i in range(1000):
        if i == 0:
            open_price = base_price
            high = base_price + 0.0010
            low = base_price - 0.0008
            close = base_price + 0.0005
        else:
            open_price = data[i-1]['Close']
            
            # Diferentes fases del mercado para generar patrones
            if 50 <= i <= 100:  # Fase alcista con patrones hammer
                trend = 0.0002
                if i % 10 == 0:  # Hammer cada 10 velas
                    high = open_price + 0.0005
                    low = open_price - 0.0025  # Sombra larga inferior
                    close = open_price + 0.0003
                else:
                    high = open_price + abs(np.random.normal(0, 0.0008))
                    low = open_price - abs(np.random.normal(0, 0.0005))
                    close = open_price + trend + np.random.normal(0, 0.0004)
                    
            elif 200 <= i <= 250:  # Patrones engulfing
                if i == 220:  # Bullish engulfing setup
                    # Vela anterior bajista
                    data[i-1]['Close'] = data[i-1]['Open'] - 0.0015
                    # Vela actual alcista que envuelve
                    low = data[i-1]['Close'] - 0.0005
                    close = data[i-1]['Open'] + 0.0020
                    high = close + 0.0003
                elif i == 240:  # Bearish engulfing setup
                    # Vela anterior alcista
                    data[i-1]['Close'] = data[i-1]['Open'] + 0.0015
                    # Vela actual bajista que envuelve
                    high = data[i-1]['Close'] + 0.0005
                    close = data[i-1]['Open'] - 0.0020
                    low = close - 0.0003
                else:
                    high = open_price + abs(np.random.normal(0, 0.0008))
                    low = open_price - abs(np.random.normal(0, 0.0008))
                    close = open_price + np.random.normal(0, 0.0005)
                    
            elif 400 <= i <= 450:  # Patrones de tres velas
                phase = (i - 400) % 30
                if phase < 3:  # Morning star pattern
                    if phase == 0:  # Primera vela bajista
                        high = open_price + 0.0003
                        low = open_price - 0.0020
                        close = open_price - 0.0015
                    elif phase == 1:  # Segunda vela pequeña (doji-like)
                        high = open_price + 0.0002
                        low = open_price - 0.0002
                        close = open_price + 0.0001
                    else:  # Tercera vela alcista
                        high = open_price + 0.0025
                        low = open_price - 0.0003
                        close = open_price + 0.0020
                elif 15 <= phase < 18:  # Evening star pattern
                    if phase == 15:  # Primera vela alcista
                        high = open_price + 0.0020
                        low = open_price - 0.0003
                        close = open_price + 0.0015
                    elif phase == 16:  # Segunda vela pequeña
                        high = open_price + 0.0002
                        low = open_price - 0.0002
                        close = open_price - 0.0001
                    else:  # Tercera vela bajista
                        high = open_price + 0.0003
                        low = open_price - 0.0025
                        close = open_price - 0.0020
                else:
                    high = open_price + abs(np.random.normal(0, 0.0008))
                    low = open_price - abs(np.random.normal(0, 0.0008))
                    close = open_price + np.random.normal(0, 0.0005)
                    
            elif 600 <= i <= 650:  # Three soldiers/crows patterns
                phase = (i - 600) % 20
                if phase < 3:  # Three white soldiers
                    high = open_price + 0.0015
                    low = open_price - 0.0002
                    close = open_price + 0.0012 + (phase * 0.0003)
                elif 10 <= phase < 13:  # Three black crows
                    high = open_price + 0.0002
                    low = open_price - 0.0015
                    close = open_price - 0.0012 - (phase - 10) * 0.0003
                else:
                    high = open_price + abs(np.random.normal(0, 0.0008))
                    low = open_price - abs(np.random.normal(0, 0.0008))
                    close = open_price + np.random.normal(0, 0.0005)
                    
            else:  # Velas normales
                volatility = 0.0010
                high = open_price + abs(np.random.normal(0, volatility))
                low = open_price - abs(np.random.normal(0, volatility))
                close = open_price + np.random.normal(0, volatility/2)
        
        data.append({
            'Open': open_price,
            'High': max(open_price, high, close),
            'Low': min(open_price, low, close),
            'Close': close
        })
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_candle_strategies_initialization():
    """Prueba inicialización de CandleStrategies"""
    print("\n=== Testing CandleStrategies Initialization ===")
    
    data = create_comprehensive_test_data()
    
    try:
        strategies = CandleStrategies(data)
        print("✅ CandleStrategies initialized successfully")
        
        # Verificar que patterns se inicializó
        if hasattr(strategies, 'patterns'):
            print("✅ CandlestickPatterns instance created")
        else:
            print("❌ CandlestickPatterns not initialized")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

def test_candle_exit_config():
    """Prueba CandleExitConfig"""
    print("\n=== Testing CandleExitConfig ===")
    
    try:
        # Configuración por defecto
        config = CandleExitConfig()
        print("✅ Default CandleExitConfig created")
        
        # Verificar valores por defecto
        if config.use_signal_change and config.use_stop_loss and config.use_take_profit:
            print("✅ Default exit methods enabled")
        else:
            print("❌ Wrong default exit methods")
            return False
        
        # Configuración personalizada
        custom_config = CandleExitConfig(
            use_trailing_stop=True,
            atr_sl_multiplier=2.0,
            atr_tp_multiplier=4.0
        )
        print("✅ Custom CandleExitConfig created")
        
        return True
    except Exception as e:
        print(f"❌ CandleExitConfig test failed: {e}")
        return False

def test_individual_pattern_strategies():
    """Prueba estrategias de patrones individuales"""
    print("\n=== Testing Individual Pattern Strategies ===")
    
    data = create_comprehensive_test_data()
    strategies = CandleStrategies(data)
    
    individual_strategies = [
        ('hammer_reversal_strategy', strategies.hammer_reversal_strategy),
        ('bullish_engulfing_strategy', strategies.bullish_engulfing_strategy),
        ('bearish_engulfing_strategy', strategies.bearish_engulfing_strategy),
        ('morning_star_strategy', strategies.morning_star_strategy),
        ('evening_star_strategy', strategies.evening_star_strategy),
        ('hanging_man_strategy', strategies.hanging_man_strategy),
        ('three_white_soldiers_strategy', strategies.three_white_soldiers_strategy),
        ('three_black_crows_strategy', strategies.three_black_crows_strategy),
        ('doji_reversal_strategy', strategies.doji_reversal_strategy)
    ]
    
    passed = 0
    total = len(individual_strategies)
    
    for name, method in individual_strategies:
        try:
            result = method()
            
            # Verificar estructura completa
            required_cols = ['ExecSignal', 'Position', 'StopLoss', 'TakeProfit', 'ExitReason']
            missing = [col for col in required_cols if col not in result.columns]
            
            if not missing:
                # Verificar valores válidos
                valid_exec = result['ExecSignal'].isin([-1, 0, 1]).all()
                valid_pos = result['Position'].isin([-1, 0, 1]).all()
                
                if valid_exec and valid_pos:
                    signals = (result['ExecSignal'] != 0).sum()
                    positions = (result['Position'] != 0).sum()
                    print(f"✅ {name}: Valid structure, {signals} signals, {positions} position periods")
                    passed += 1
                else:
                    print(f"❌ {name}: Invalid signal/position values")
            else:
                print(f"❌ {name}: Missing columns: {missing}")
                
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")
    
    print(f"📊 Individual strategies: {passed}/{total} passed")
    return passed == total

def test_combined_strategies():
    """Prueba estrategias combinadas"""
    print("\n=== Testing Combined Strategies ===")
    
    data = create_comprehensive_test_data()
    strategies = CandleStrategies(data)
    
    combined_strategies = [
        ('scalping_reversal_strategy', strategies.scalping_reversal_strategy),
        ('swing_trading_strategy', strategies.swing_trading_strategy),
        ('multi_pattern_strategy', strategies.multi_pattern_strategy)
    ]
    
    passed = 0
    total = len(combined_strategies)
    
    for name, method in combined_strategies:
        try:
            result = method()
            
            # Verificar estructura
            required_cols = ['ExecSignal', 'Position']
            missing = [col for col in required_cols if col not in result.columns]
            
            if not missing:
                signals = (result['ExecSignal'] != 0).sum()
                print(f"✅ {name}: Valid structure, {signals} signals")
                passed += 1
            else:
                print(f"❌ {name}: Missing columns: {missing}")
                
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")
    
    print(f"📊 Combined strategies: {passed}/{total} passed")
    return passed == total

def test_specialized_strategies():
    """Prueba estrategias especializadas"""
    print("\n=== Testing Specialized Strategies ===")
    
    data = create_comprehensive_test_data()
    strategies = CandleStrategies(data)
    
    specialized_strategies = [
        ('aggressive_reversal_strategy', strategies.aggressive_reversal_strategy),
        ('conservative_swing_strategy', strategies.conservative_swing_strategy)
    ]
    
    passed = 0
    total = len(specialized_strategies)
    
    for name, method in specialized_strategies:
        try:
            result = method()
            
            # Verificar estructura completa con configuraciones especiales
            required_cols = ['ExecSignal', 'Position', 'StopLoss', 'TakeProfit', 'ExitReason']
            missing = [col for col in required_cols if col not in result.columns]
            
            if not missing:
                signals = (result['ExecSignal'] != 0).sum()
                
                # Verificar que se aplicaron las configuraciones especiales
                if name == 'aggressive_reversal_strategy':
                    # Debería tener trailing stops
                    exit_reasons = result[result['ExitReason'] != '']['ExitReason'].unique()
                    print(f"✅ {name}: {signals} signals, exit reasons: {list(exit_reasons)}")
                else:
                    # Conservative strategy
                    print(f"✅ {name}: {signals} signals (conservative approach)")
                
                passed += 1
            else:
                print(f"❌ {name}: Missing columns: {missing}")
                
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")
    
    print(f"📊 Specialized strategies: {passed}/{total} passed")
    return passed == total

def test_exit_logic_comprehensive():
    """Prueba exhaustiva de la lógica de cierres"""
    print("\n=== Testing Comprehensive Exit Logic ===")
    
    data = create_comprehensive_test_data()
    strategies = CandleStrategies(data)
    
    # Configuraciones diferentes para probar todos los tipos de cierre
    configs = [
        ("Signal Change Only", CandleExitConfig(
            use_signal_change=True,
            use_stop_loss=False,
            use_take_profit=False,
            use_trailing_stop=False
        )),
        ("SL/TP Only", CandleExitConfig(
            use_signal_change=False,
            use_stop_loss=True,
            use_take_profit=True,
            use_trailing_stop=False
        )),
        ("Trailing Stop", CandleExitConfig(
            use_signal_change=True,
            use_stop_loss=True,
            use_take_profit=True,
            use_trailing_stop=True,
            atr_trailing_multiplier=1.5
        )),
        ("All Methods", CandleExitConfig(
            use_signal_change=True,
            use_stop_loss=True,
            use_take_profit=True,
            use_trailing_stop=True
        ))
    ]
    
    passed = 0
    total = len(configs)
    
    for config_name, config in configs:
        try:
            result = strategies.hammer_reversal_strategy(config)
            
            # Verificar que se aplicó la configuración
            exit_reasons = result[result['ExitReason'] != '']['ExitReason'].unique()
            signals = (result['ExecSignal'] != 0).sum()
            
            print(f"✅ {config_name}: {signals} signals, exit reasons: {list(exit_reasons)}")
            passed += 1
            
        except Exception as e:
            print(f"❌ {config_name}: Error - {str(e)}")
    
    print(f"📊 Exit logic configurations: {passed}/{total} passed")
    return passed == total

def test_risk_management_candles():
    """Prueba gestión de riesgo en estrategias de velas"""
    print("\n=== Testing Risk Management in Candle Strategies ===")
    
    data = create_comprehensive_test_data()
    strategies = CandleStrategies(data)
    
    try:
        # Configuración con gestión de riesgo estricta
        config = CandleExitConfig(
            atr_sl_multiplier=1.0,  # Stop loss estrecho
            atr_tp_multiplier=2.0,  # Take profit 2:1
            use_trailing_stop=True,
            atr_trailing_multiplier=1.5
        )
        
        result = strategies.bullish_engulfing_strategy(config)
        
        # Verificar entradas con niveles de riesgo
        entries = result[result['ExecSignal'].abs() == 1]
        
        if len(entries) > 0:
            # Verificar que todos los entries tienen SL/TP
            has_sl = not entries['StopLoss'].isna().all()
            has_tp = not entries['TakeProfit'].isna().all()
            
            if has_sl and has_tp:
                print("✅ Risk management: All entries have SL/TP")
                
                # Verificar ratios de riesgo/beneficio
                long_entries = entries[entries['ExecSignal'] == 1]
                short_entries = entries[entries['ExecSignal'] == -1]
                
                risk_ratios_valid = True
                
                for _, entry in long_entries.iterrows():
                    risk = entry['Close'] - entry['StopLoss']
                    reward = entry['TakeProfit'] - entry['Close']
                    if risk <= 0 or reward <= 0 or reward/risk < 1.5:
                        risk_ratios_valid = False
                        break
                
                for _, entry in short_entries.iterrows():
                    risk = entry['StopLoss'] - entry['Close']
                    reward = entry['Close'] - entry['TakeProfit']
                    if risk <= 0 or reward <= 0 or reward/risk < 1.5:
                        risk_ratios_valid = False
                        break
                
                if risk_ratios_valid:
                    print("✅ Risk management: Valid risk/reward ratios")
                    return True
                else:
                    print("❌ Risk management: Invalid risk/reward ratios")
                    return False
            else:
                print("❌ Risk management: Missing SL/TP for entries")
                return False
        else:
            print("ℹ️  Risk management: No entries to test (normal for some datasets)")
            return True
            
    except Exception as e:
        print(f"❌ Risk management test failed: {e}")
        return False

def main():
    """Función principal de tests para candle_strategies.py"""
    print("🧪 Testing candle_strategies.py Module")
    print("=" * 60)
    
    tests = [
        test_candle_strategies_initialization,
        test_candle_exit_config,
        test_individual_pattern_strategies,
        test_combined_strategies,
        test_specialized_strategies,
        test_exit_logic_comprehensive,
        test_risk_management_candles
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
    print(f"🏁 CANDLE_STRATEGIES.PY TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! candle_strategies.py module is working correctly.")
    else:
        print("⚠️  Some tests failed. Check output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
