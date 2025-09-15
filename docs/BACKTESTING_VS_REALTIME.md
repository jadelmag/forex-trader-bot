# Separación entre Backtesting y Trading en Tiempo Real

## Arquitectura del Sistema

El sistema tiene dos flujos de trabajo completamente separados:

### 1. **BACKTESTING (Datos PKL/CSV)**

**Flujo de datos:**
```
PKL/CSV → strategies_modal.py → risk_manager.abrir_operacion() → risk_manager.verificar_cierre_operaciones()
```

**Métodos específicos en RiskManager:**
- `abrir_operacion()` - Abre operaciones para simulación histórica
- `verificar_cierre_operaciones()` - Verifica SL/TP en datos históricos

**Características:**
- Usa datos pre-cargados desde archivos PKL o CSV
- Procesa todo el dataset de una vez
- Ideal para probar estrategias con datos históricos
- Usado por: `app/strategies_modal.py`, `app/ai_trainer.py`

### 2. **TRADING EN TIEMPO REAL (Binance/WebSocket)**

**Flujo de datos:**
```
Binance WebSocket → candle_streamer.py → callbacks → risk_manager_integration.py → RiskManager (métodos consolidados)
```

**Métodos usados en RiskManager:**
- `cerrar_operacion_por_estrategia()` - Cierra por señales de estrategia
- `cerrar_operacion_manual()` - Cierre manual por usuario
- `verificar_trailing_stops()` - Gestión de trailing stops dinámicos
- `_cerrar_operacion_comun()` - Método interno centralizado

**Características:**
- Recibe datos vela por vela en tiempo real
- Procesa señales conforme llegan (streaming)
- Integración con `risk_manager_integration.py` para gestión de señales
- Usado por: `trading_view/candle_streamer.py`, Binance modal

## Flujo de Señales en Tiempo Real

```python
# En risk_manager_integration.py
def process_signal(self, signal, precio_actual, timestamp, estrategia_nombre, ...):
    """
    Procesa señales en tiempo real:
    - Signal = 1: Abrir BUY
    - Signal = -1: Abrir SELL (si enabled) o cerrar operaciones
    - Signal = -2: Forzar SELL
    - Signal = 2: Cerrar SELL por señal
    - Signal = 0: Cerrar todas las operaciones
    """
```

## Separación de Responsabilidades

| Componente | Backtesting | Tiempo Real | Descripción |
|-----------|-------------|-------------|-------------|
| **risk_manager.py** | `abrir_operacion()`, `verificar_cierre_operaciones()` | `cerrar_operacion_por_estrategia()`, `verificar_trailing_stops()` | Core de gestión de riesgo |
| **risk_manager_integration.py** | ❌ | ✅ | Integración para tiempo real |
| **strategies_modal.py** | ✅ | ❌ | Modal para backtesting |
| **candle_streamer.py** | ❌ | ✅ | Streaming de velas |
| **binance_modal.py** | ❌ | ✅ | Simulación con datos Binance |

## Importante

Los métodos `abrir_operacion()` y `verificar_cierre_operaciones()` **NO interfieren** con el trading en tiempo real porque:

1. **Contextos diferentes**: Backtesting usa DataFrames completos, tiempo real usa callbacks vela por vela
2. **Flujos separados**: Los modales de backtesting no se mezclan con el streaming de Binance
3. **Gestión independiente**: RiskManagerIntegration maneja todas las operaciones en tiempo real sin usar estos métodos

## Ejemplo de Uso Correcto

### Backtesting (strategies_modal.py):
```python
# Usa métodos específicos de backtesting
operacion = risk_manager.abrir_operacion(
    tipo='BUY',
    precio=current_price,
    timestamp=idx,
    stop_loss=sl,
    take_profit=tp,
    estrategia=strategy_name
)

# Verificar cierres por SL/TP
operaciones_cerradas = risk_manager.verificar_cierre_operaciones(current_price, idx)
```

### Tiempo Real (risk_manager_integration.py):
```python
# NO usa abrir_operacion() ni verificar_cierre_operaciones()
# En su lugar, procesa señales y delega a métodos consolidados
resultado = self.process_signal(
    signal=1,  # BUY
    precio_actual=price,
    timestamp=timestamp,
    estrategia_nombre="strategy_name",
    config=strategy_config
)
```

## Conclusión

La arquitectura está diseñada para mantener **completamente separados** los flujos de backtesting y tiempo real, evitando cualquier interferencia entre ambos modos de operación.
