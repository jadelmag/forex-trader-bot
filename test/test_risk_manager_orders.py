#!/usr/bin/env python3
# Test para verificar que RiskManager abre operaciones SHORT/LONG correctamente

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Añadir el directorio raíz al path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from strategies.risk_manager import RiskManager
from strategies.risk_manager_integration import RiskManagerIntegration, RiskConfig

def test_risk_manager_short_long_orders():
    """Test completo para verificar apertura de operaciones BUY/SELL"""
    print("🧪 INICIANDO TEST: RiskManager SHORT/LONG Orders")
    print("=" * 60)
    
    # 1. Configurar RiskManager con capital inicial
    capital_inicial = 1000.0
    risk_manager = RiskManager(
        capital_inicial=capital_inicial,
        max_operaciones_activas=10,
        debug_mode=True
    )
    
    # 2. Configurar RiskManagerIntegration con SELL habilitado
    config = RiskConfig(
        enable_sell_operations=True,
        force_open_operations=True,
        default_risk_percent=0.02,  # 2%
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=2.0
    )
    
    integration = RiskManagerIntegration(risk_manager, config=config, debug_mode=True)
    
    # 3. Datos de prueba
    precio_actual = 1.1000
    timestamp = datetime.now()
    atr_value = 0.0020
    
    print(f"💰 Capital inicial: {capital_inicial}€")
    print(f"📊 Precio actual: {precio_actual}")
    print(f"📈 ATR: {atr_value}")
    print()
    
    # 4. TEST BUY (Señal = 1)
    print("🟢 TEST 1: Operación BUY (LONG)")
    print("-" * 30)
    
    operacion_buy = integration.procesar_senal(
        senal=1,
        precio_actual=precio_actual,
        timestamp=timestamp,
        atr_value=atr_value,
        estrategia_nombre="test_buy_strategy",
        sync_mode=True
    )
    
    if operacion_buy and hasattr(operacion_buy, 'id'):
        print(f"✅ Operación BUY abierta correctamente")
        print(f"   ID: {operacion_buy.id}")
        print(f"   Tipo: {operacion_buy.tipo}")
        print(f"   Precio entrada: {operacion_buy.precio_apertura}")
        print(f"   Stop Loss: {operacion_buy.stop_loss:.5f}")
        print(f"   Take Profit: {operacion_buy.take_profit:.5f}")
        print(f"   Lote: {operacion_buy.lote_size}")
    else:
        print("❌ ERROR: No se pudo abrir operación BUY")
        return False
    
    print()
    
    # 5. TEST SELL (Señal = -1)
    print("🔴 TEST 2: Operación SELL (SHORT)")
    print("-" * 30)
    
    precio_sell = 1.1050  # Precio ligeramente diferente
    operacion_sell = integration.procesar_senal(
        senal=-1,
        precio_actual=precio_sell,
        timestamp=timestamp,
        atr_value=atr_value,
        estrategia_nombre="test_sell_strategy",
        sync_mode=True
    )
    
    if operacion_sell and hasattr(operacion_sell, 'id'):
        print(f"✅ Operación SELL abierta correctamente")
        print(f"   ID: {operacion_sell.id}")
        print(f"   Tipo: {operacion_sell.tipo}")
        print(f"   Precio entrada: {operacion_sell.precio_apertura}")
        print(f"   Stop Loss: {operacion_sell.stop_loss:.5f}")
        print(f"   Take Profit: {operacion_sell.take_profit:.5f}")
        print(f"   Lote: {operacion_sell.lote_size}")
    else:
        print("❌ ERROR: No se pudo abrir operación SELL")
        return False
    
    print()
    
    # 6. Verificar operaciones activas
    print("📋 RESUMEN DE OPERACIONES ACTIVAS")
    print("-" * 30)
    
    operaciones_activas = [op for op in risk_manager.operaciones_activas if op.estado == 'ACTIVA']
    print(f"Total operaciones activas: {len(operaciones_activas)}")
    
    buy_count = sum(1 for op in operaciones_activas if op.tipo == 'BUY')
    sell_count = sum(1 for op in operaciones_activas if op.tipo == 'SELL')
    
    print(f"Operaciones BUY (LONG): {buy_count}")
    print(f"Operaciones SELL (SHORT): {sell_count}")
    
    # 7. Verificar capital reservado
    capital_disponible = risk_manager.capital
    capital_reservado = risk_manager.capital_inicial - capital_disponible
    
    print(f"Capital disponible: {capital_disponible:.2f}€")
    print(f"Capital reservado: {capital_reservado:.2f}€")
    
    print()
    
    # 8. TEST de cálculo de profit para SELL
    print("🧮 TEST 3: Cálculo de profit SELL")
    print("-" * 30)
    
    # Simular movimiento de precio bajista (favorable para SELL)
    precio_cierre_sell = precio_sell - 0.0030  # Precio baja 30 pips
    profit_sell = operacion_sell.calcular_profit(precio_cierre_sell)
    
    print(f"Precio entrada SELL: {operacion_sell.precio_apertura}")
    print(f"Precio cierre simulado: {precio_cierre_sell}")
    print(f"Profit calculado: {profit_sell:.2f}€")
    
    if profit_sell > 0:
        print("✅ Profit SELL calculado correctamente (positivo cuando precio baja)")
    else:
        print("❌ ERROR: Profit SELL debería ser positivo cuando precio baja")
        return False
    
    print()
    
    # 9. Resultado final
    print("🎯 RESULTADO DEL TEST")
    print("=" * 60)
    
    if buy_count >= 1 and sell_count >= 1:
        print("✅ TEST EXITOSO: RiskManager abre correctamente operaciones BUY y SELL")
        print("✅ Sistema configurado correctamente para operaciones SHORT/LONG")
        print("✅ Cálculos de profit funcionan correctamente")
        return True
    else:
        print("❌ TEST FALLIDO: No se abrieron ambos tipos de operaciones")
        return False

if __name__ == "__main__":
    try:
        success = test_risk_manager_short_long_orders()
        if success:
            print("\n🎉 TODOS LOS TESTS PASARON CORRECTAMENTE")
            sys.exit(0)
        else:
            print("\n💥 ALGUNOS TESTS FALLARON")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERROR EN EL TEST: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
