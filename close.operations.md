### Métodos de Salida Implementados:
1. STOP_LOSS (líneas 96-100)
    - Para LONG: cierre cuando current_low <= stop_loss
    - Para SHORT: cierre cuando current_high >= stop_loss
    - Basado en ATR con multiplicador configurable (default: 1.5x ATR)
2. TAKE_PROFIT (líneas 103-107)
    - Para LONG: cierre cuando current_high >= take_profit
    - Para SHORT: cierre cuando current_low <= take_profit
    - Basado en ATR con multiplicador configurable (default: 3.0x ATR)
3. SIGNAL_CHANGE (líneas 127-131)
    - Cierre cuando la señal cambia de dirección
    - LONG se cierra con señal -1, SHORT se cierra con señal 1
4. TRAILING_STOP (líneas 109-124)
    - Stop móvil que se ajusta a favor de la posición
    - Basado en ATR con multiplicador configurable (default: 2.0x ATR)
    - DESACTIVADO por defecto (use_trailing_stop: bool = False)

### Métodos NO Utilizados:
1. PATTERN_REVERSAL
    - Definido en el enum pero no implementado en 
    - _apply_exit_logic()
    - DESACTIVADO por defecto (use_pattern_reversal: bool = False)

### Configuración por Defecto:

```
use_signal_change: bool = True     # ✅ ACTIVO
use_stop_loss: bool = True         # ✅ ACTIVO  
use_take_profit: bool = True       # ✅ ACTIVO
use_trailing_stop: bool = False    # ❌ INACTIVO
use_pattern_reversal: bool = False # ❌ INACTIVO
```

### Revisando el código, hay 2 razones principales por las que no se usan los 5 métodos:

1. TRAILING_STOP está desactivado por defecto
En CandleExitConfig (línea 24): 

        use_trailing_stop: bool = False

    - Razón técnica: El trailing stop puede ser muy agresivo y cerrar posiciones prematuramente
    - Impacto: Reduce la rentabilidad en tendencias fuertes donde el precio podría seguir subiendo/bajando

2. PATTERN_REVERSAL no está implementado
    - Está definido en el enum (línea 16) pero falta la lógica en 
    - _apply_exit_logic()
    - En CandleExitConfig (línea 25): use_pattern_reversal: bool = False
    - Código faltante: No hay verificación de patrones de reversión en el bucle principal


¿Por qué esta configuración?
Enfoque conservador: Se priorizan métodos de salida más confiables:

STOP_LOSS/TAKE_PROFIT: Gestión de riesgo fundamental
SIGNAL_CHANGE: Lógica de estrategia directa
TRAILING_STOP: Opcional (puede ser muy sensible)
PATTERN_REVERSAL: Requiere implementación adicional