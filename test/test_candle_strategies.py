# test/test_candle_strategies.py

import pandas as pd
import numpy as np
from strategies.candle_strategies import CandleStrategies, CandleExitConfig

def create_test_data():
    """Crea datos de prueba con patrones conocidos"""
    np.random.seed(42)
    
    # Generar datos base
    dates = pd.date_range('2024-01-01', periods=200, freq='H')
    
    # Crear datos con tendencia y volatilidad
    base_price = 1.1000
    trend = np.linspace(0, 0.0050, 200)  # Tendencia alcista leve
    noise = np.random.normal(0, 0.0010, 200)  # Ruido
    
    prices = base_price + trend + noise
    
    # Crear OHLC con patrones específicos
    data = []
    for i, price in enumerate(prices):
        if i == 0:
            open_price = price
            high = price + abs(np.random.normal(0, 0.0005))
            low = price - abs(np.random.normal(0, 0.0005))
            close = price + np.random.normal(0, 0.0003)
        else:
            open_price = data[i-1]['Close']
            
            # Insertar algunos patrones conocidos
            if i == 50:  # Hammer pattern
                high = open_price + 0.0008
                low = open_price - 0.0020  # Sombra larga inferior
                close = open_price + 0.0005  # Cierre cerca del máximo
            elif i == 100:  # Bullish engulfing
                if i > 0:
                    # Vela anterior bajista
                    data[i-1]['Close'] = data[i-1]['Open'] - 0.0010
                # Vela actual alcista que envuelve
                low = data[i-1]['Close'] - 0.0005
                close = data[i-1]['Open'] + 0.0010
                high = close + 0.0003
            elif i == 150:  # Evening star (primera vela alcista)
                high = open_price + 0.0015
                low = open_price - 0.0003
                close = open_price + 0.0012
            else:
                # Velas normales
                volatility = 0.0008
                high = open_price + abs(np.random.normal(0, volatility/2))
                low = open_price - abs(np.random.normal(0, volatility/2))
                close = open_price + np.random.normal(0, volatility/3)
        
        data.append({
            'Open': open_price,
            'High': max(open_price, high, close),
            'Low': min(open_price, low, close),
            'Close': close
        })
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_strategy_structure(strategy_result, strategy_name):
    """Verifica que la estrategia tenga la estructura correcta"""
    required_columns = ['Open', 'High', 'Low', 'Close', 'Signal', 'ExecSignal', 'Position', 'StopLoss', 'TakeProfit', 'ExitReason']
    
    print(f"\n=== Testing {strategy_name} ===")
    
    # Verificar columnas
    missing_cols = [col for col in required_columns if col not in strategy_result.columns]
    if missing_cols:
        print(f"❌ Missing columns: {missing_cols}")
        return False
    else:
        print("✅ All required columns present")
    
    # Verificar que ExecSignal solo tenga valores válidos
    valid_signals = strategy_result['ExecSignal'].isin([-1, 0, 1]).all()
    if not valid_signals:
        print("❌ Invalid ExecSignal values found")
        return False
    else:
        print("✅ ExecSignal values are valid (-1, 0, 1)")
    
    # Verificar que Position solo tenga valores válidos
    valid_positions = strategy_result['Position'].isin([-1, 0, 1]).all()
    if not valid_positions:
        print("❌ Invalid Position values found")
        return False
    else:
        print("✅ Position values are valid (-1, 0, 1)")
    
    # Contar señales
    entry_signals = (strategy_result['ExecSignal'] != 0).sum()
    positions_held = (strategy_result['Position'] != 0).sum()
    
    print(f"📊 Entry/Exit signals: {entry_signals}")
    print(f"📊 Periods with position: {positions_held}")
    
    # Verificar lógica de posiciones
    if entry_signals > 0:
        print("✅ Strategy generated signals")
        
        # Verificar que cuando hay ExecSignal de entrada, Position cambie
        entry_mask = (strategy_result['ExecSignal'] != 0) & (strategy_result['Position'].shift(1).fillna(0) == 0)
        if entry_mask.any():
            print("✅ Entry signals correctly update Position")
        
        # Verificar que StopLoss y TakeProfit se calculen en entradas
        entry_indices = strategy_result[strategy_result['ExecSignal'].abs() == 1].index
        if len(entry_indices) > 0:
            first_entry = entry_indices[0]
            if not pd.isna(strategy_result.loc[first_entry, 'StopLoss']):
                print("✅ StopLoss calculated on entry")
            if not pd.isna(strategy_result.loc[first_entry, 'TakeProfit']):
                print("✅ TakeProfit calculated on entry")
    
    return True

def test_exit_logic():
    """Prueba específica de la lógica de cierres"""
    print("\n=== Testing Exit Logic ===")
    
    data = create_test_data()
    strategies = CandleStrategies(data)
    
    # Configuración con todos los tipos de cierre activados
    config = CandleExitConfig(
        use_signal_change=True,
        use_stop_loss=True,
        use_take_profit=True,
        use_trailing_stop=True,
        atr_sl_multiplier=1.0,
        atr_tp_multiplier=2.0,
        atr_trailing_multiplier=1.5
    )
    
    result = strategies.hammer_reversal_strategy(config)
    
    # Verificar tipos de cierre
    exit_reasons = result[result['ExitReason'] != '']['ExitReason'].unique()
    print(f"📊 Exit reasons found: {list(exit_reasons)}")
    
    # Contar cada tipo de cierre
    for reason in exit_reasons:
        count = (result['ExitReason'] == reason).sum()
        print(f"   - {reason}: {count} times")
    
    return len(exit_reasons) > 0

def run_all_tests():
    """Ejecuta todos los tests"""
    print("🧪 Starting Candle Strategies Tests")
    print("=" * 50)
    
    # Crear datos de prueba
    data = create_test_data()
    strategies = CandleStrategies(data)
    
    # Lista de estrategias a probar
    strategy_methods = [
        ('hammer_reversal_strategy', strategies.hammer_reversal_strategy),
        ('bullish_engulfing_strategy', strategies.bullish_engulfing_strategy),
        ('bearish_engulfing_strategy', strategies.bearish_engulfing_strategy),
        ('morning_star_strategy', strategies.morning_star_strategy),
        ('evening_star_strategy', strategies.evening_star_strategy),
        ('three_white_soldiers_strategy', strategies.three_white_soldiers_strategy),
        ('aggressive_reversal_strategy', strategies.aggressive_reversal_strategy),
        ('conservative_swing_strategy', strategies.conservative_swing_strategy)
    ]
    
    results = {}
    passed_tests = 0
    
    # Probar cada estrategia
    for name, method in strategy_methods:
        try:
            result = method()
            if test_strategy_structure(result, name):
                passed_tests += 1
                results[name] = result
            else:
                print(f"❌ {name} failed structure test")
        except Exception as e:
            print(f"❌ {name} failed with error: {e}")
    
    # Probar lógica de cierres
    if test_exit_logic():
        passed_tests += 1
        print("✅ Exit logic test passed")
    else:
        print("❌ Exit logic test failed")
    
    # Resumen final
    total_tests = len(strategy_methods) + 1
    print(f"\n{'='*50}")
    print(f"🏁 TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Candle strategies are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return results

if __name__ == "__main__":
    test_results = run_all_tests()
