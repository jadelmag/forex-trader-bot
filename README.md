# Forex Trader Bot — Visión General y Guía Profesional

Este documento resume el estado actual de la aplicación, las optimizaciones clave realizadas y el nuevo esquema de archivos, con una descripción clara del propósito de cada módulo.

Bot de trading Forex con interfaz gráfica (Tkinter) y soporte de Reinforcement Learning (FinRL + Stable-Baselines3).

Este proyecto permite:

* Cargar pares de divisas en CSV.
* Cargar gráficos de velas con tooltips.
* Ejecutar estrategias de RL y backtesting.
* Exportar datos históricos a PKL.

[Ver descripción completa de la aplicación (Overview)](docs/overview.md)

## Requisitos

* Python 3.11 [Download: https://www.python.org/downloads/]
* Conexión a internet (para descargar datos de Yahoo Finance y FinRL)
* Git (para clonar el repositorio) [Download: https://git-scm.com/downloads]

## Características Principales

- Detección de patrones de velas (candlestick) y estrategias forex integradas.
- Sistema de gestión de riesgo robusto con soporte completo para operaciones BUY/SELL.
- Simulación de mercado en “tiempo real” usando datos CSV: una nueva vela cada 5 segundos.
- Sincronización precisa entre el dibujado del gráfico y la detección/operación.
- Optimización de rendimiento, threading seguro y métricas internas.
- Configuración dinámica de límites de capital y parámetros de patrones.

## Flujo de Funcionamiento

1. `trading_view/candle_streamer.py` simula la llegada de velas nuevas cada 5 segundos desde CSV.
2. En cada paso:
   - Se dibuja la nueva vela en el gráfico (thread UI, no bloqueante).
   - Inmediatamente (sin delays artificiales) se ejecutan las detecciones de patrones y las estrategias en un thread separado.
   - Las estrategias generan señales que son procesadas por `strategies/risk_manager_integration.py`, el cual delega a `strategies/risk_manager.py` para abrir/cerrar operaciones con reglas de riesgo.
3. El sistema registra logs y estadísticas, y actualiza la UI en tiempo real.

## Optimizaciones Clave Implementadas

- Sincronización adaptada al contexto reemplazada por ejecución inmediata tras el dibujado: detección/operaciones ya no esperan delays.
- Intervalo de simulación realista: 5 segundos entre velas en `_schedule_next_simulation_step()`.
- Detección en paralelo (`thread` daemon) para no bloquear la UI del gráfico.
- Consolidación de trailing stops y cierre de operaciones en `RiskManager` con thread safety.
- Reducción de ruido en logs: mensajes detallados solo en `debug_mode`.
- Correcciones y mejoras de patrones de velas con configuración centralizada en `patterns/`.

## Esquema de Directorios y Archivos (Resumen)

```
app/
├── __init__.py
├── __main__.py
├── gui/
│   ├── __init__.py
│   ├── main_window.py              # Clase GUIPrincipal: integra modales, gráficos y control general
│   ├── components/
│   │   ├── __init__.py
│   │   ├── menu_bar.py             # Componentes de menú
│   │   ├── status_bar.py           # Barra de estado con información financiera
│   │   ├── log_panel.py            # Panel de logs
│   │   ├── telegram_panel.py       # Panel de Telegram
│   │   └── progress_bar.py         # Barra de progreso
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── csv_handler.py          # Manejo de CSV (carga, validaciones, parsing)
│   │   ├── pattern_handler.py      # Orquestación de detección de patrones de velas
│   │   ├── strategy_handler.py     # Gestión de estrategias seleccionadas
│   │   ├── rl_handler.py           # Manejo de aprendizaje por refuerzo
│   │   ├── simulation_handler.py   # Control del ciclo de simulación
│   │   └── telegram_handler.py     # Integración con Telegram
│   └── managers/
│       ├── __init__.py
│       ├── thread_manager.py       # Gestión de threads y colas
│       ├── cache_manager.py        # Gestión de caché (datos y resultados)
│       └── strategy_manager.py     # Gestión y coordinación de estrategias
|
├── logs/
│   ├── audit_YYYYMMDD.jsonl        # Auditoría de acciones
│   └── log_YYYYMMDD_HHMMSS.txt     # Logs de aplicación
|
├── assets/
│   └── icon.png
|
├── backtesting/
│   └── backtester.py               # Infraestructura para pruebas históricas
|
├── config/
│   ├── app_config.json             # Límites de capital y preferencias de app
│   ├── candle_bearish_engulfing_reversal.json
│   ├── candle_bearish_engulfing_strategy.json
│   ├── candle_bullish_engulfing_reversal.json
│   ├── ... (más configuraciones de estrategias de velas)
│   └── ... (más configuraciones de estrategias de velas)
├── csv/
│   ├── audusd/
│   │   ├── DAT_ASCII_AUDUSD_M1_2000.csv
│   │   ├── DAT_ASCII_AUDUSD_M1_2001.csv
│   │   └── ...
│   └── eurusd/
│       ├── DAT_ASCII_EURUSD_M1_2000.csv
│       ├── DAT_ASCII_EURUSD_M1_2001.csv
│       └── ...
├── docs/
|   ├── PROJECT_README.md               
|   ├── market_scene.md                              
|   ├── schema.md                       
|   ├── tasks.txt
|   └── requests.txt
|
├── ia/
│   ├── __init__.py
│   ├── candle_strategy_optimizer.py    # Optimizador y utilidades IA
│   ├── smart_order_analyzer.py
│   └── trading_rl_agent.py
|
├── logs/                               # Carpeta general de logs (si aplica)
|
├── models_rl/
│   └── ppo_trading.zip
|
├── old_code/
|   ├── candlestickpatterns_optimized.py
|   ├── candlestickpatterns_original.py
|   ├── candlestickpatterns_v0.py
|   └── gui_main_backup.py
|
├── patterns/
│   ├── __init__.py
│   ├── candlestickpatterns.py          # Implementación de patrones, configurable
│   └── pattern_utils.py
|
├── processed/
|   ├── 2024_first_1000_candles.pkl
|   ├── DAT_ASCII_EURUSD_M1_2023.pkl
|   ├── EURUSD_2022.pkl
|   ├── ...
|   └── processed_data_2024.pkl
|
├── reports/
|
├── rl/
│   ├── __init__.py
│   ├── rl_agent.py
│   └── rl_env.py
|
├── strategies/
│   ├── __init__.py
│   ├── candle_strategies.py            # Estrategias basadas en patrones de velas
│   ├── market_strategy_mapper.py       # Mapeo de estrategias según contexto de mercado
│   ├── risk_manager.py                 # Gestión de riesgo consolidada (BUY/SELL, SL/TP, trailing)
│   └── risk_manager_integration.py     # Integración señales -> operaciones con RiskManager
|
├── symbols/
│   └── symbols.csv
|
├── telegram/
│   ├── __init__.py
│   └── telegram-notifier.py
|
├── temp/
|
├── tensorboard_logs/
|
├── trading_view/
│   ├── __init__.py
│   ├── trading_view_csv/
|   |  └── [currency]_data.csv  
│   ├── candle_streamer.py              # Simulación de mercado; dibujado + notificación de velas
│   └── config_modal.py                 # Configuración de streaming/visualización
├── .gitignore
├── csv_parser.py
├── LICENSE
├── README.md                           # README del proyecto (original)
├── requirements.txt
└── setup.py
```

## Detalles Técnicos por Módulo Clave

- `trading_view/candle_streamer.py`
  - Simula la llegada de velas desde CSV cada 5s.
  - Método `_execute_simulation_step()`:
    - Dibuja la vela con `_update_simulation_chart(df_current)` (UI thread).
    - Lanza detección/operaciones en paralelo con `_execute_pattern_detection_and_trading(df_current)`.
  - Threading seguro con locks de datos para evitar condiciones de carrera.
  - Callbacks de estrategias registrados via `on_candle_update()`.

- `strategies/risk_manager.py`
  - Gestión de riesgo integral: BUY/SELL, SL/TP, trailing stops, cierres por señal, métricas.
  - Thread safety con `RLock` para estructuras compartidas.
  - Sistema de caché para conteo de operaciones activas y limpieza periódica.
  - Lógica de cierre centralizada, estadísticas y control de capital configurable (lee `config/app_config.json`).

- `strategies/risk_manager_integration.py`
  - Traduce señales (1, -1, 2, -2, 0) a acciones concretas usando `RiskManager`.
  - Soporta modo síncrono (`sync_mode=True`) para integraciones con GUI que requieren la Operación devuelta.
  - Logs de éxito/fallo solo en `debug_mode` para minimizar ruido.

- `patterns/candlestickpatterns.py`
  - Implementación corregida y robusta de patrones de velas (bullish/bearish) con parámetros configurables:
    - `doji_threshold`, `tweezer_tolerance`, `min_confidence`, `partial_factor`, `atr_period`, etc.
  - Correcciones de índices Timestamp vs enteros y lógica bullish/bearish coherente.
  - `combined_signal_optimized()` usa conteo de patrones y resolución de conflictos.

- `strategies/candle_strategies.py`
  - Orquesta el uso de patrones para generar señales operativas.
  - Integra parámetros de configuración y filtros por contexto de mercado.

- `app/gui/main_window.py`
  - Control de simulaciones y lanzamiento de modales (Estrategias, Binance, Config).
  - Correcciones de estructura `try/except` y flujo de validaciones.

- `trading_view/config_modal.py`
  - Parámetros visuales, conexión y setup de la simulación/streaming.

- `config/app_config.json`
  - Persistencia de límite de capital y otros ajustes de aplicación (con fallback seguro).

## Señales y Convenciones (Resumen)

- `1`: Abrir BUY
- `-1`: Abrir SELL (si `enable_sell_operations=True`) o cerrar si no se permite SELL
- `-2`: Forzar abrir SELL siempre
- `2`: Cerrar operaciones SELL por señal
- `0`: Cerrar todas las operaciones de la estrategia

## Simulación “Tiempo Real” con CSV

- Intervalo fijo de 5 segundos entre velas.
- Dibujo y detección desacoplados:
  - El gráfico se actualiza en el hilo principal.
  - Las estrategias se ejecutan inmediatamente en paralelo, sin afectar la UI.
- Esto emula un feed en vivo estable sin depender del WebSocket de Binance.

## Configuración y Requisitos

- Python 3.9+
- Instalar dependencias: `pip install -r requirements.txt`
- Configurar límites de capital y preferencias en `config/app_config.json`.

## Buenas Prácticas y Depuración

- Activar `debug_mode` para ver logs detallados (detecciones, timings, callbacks).
- Verificar el rendimiento con `verify_timing_performance()` en `candle_streamer.py`.
- Mantener actualizado `app_config.json` para límites y credenciales.

## Próximos Pasos Recomendados

- Integración con MetaTrader para ejecución real.
- Afinar estrategias para mercados laterales de baja volatilidad.
- Añadir IA para clasificación del contexto de mercado en tiempo real.

---

## Instalación paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/jadelmag/forex-trader-bot.git
cd forex-trader-bot
```

### 2. Crear un entorno virtual

```bash
python -m venv forex-env
```

### 3. Activar el entorno virtual

* Windows:

```bash
.\forex-env\Scripts\activate
```

* Linux/macOS:

```bash
source forex-env/bin/activate
```

### 4. Actualizar pip

```bash
python -m pip install --upgrade pip
```

### 5. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 6. Instalar el paquete en modo editable

```bash
pip install -e .
```

Esto creará el comando `forex-trader-bot`.

### 7. Ejecutar el bot

```bash
forex-trader-bot
```

> Esto abrirá la interfaz gráfica de Tkinter.

### 8. Salir del entorno virtual

```bash
deactivate
```

---

## Sin entorno virtual

### 1. Clonar el repositorio

```bash
git clone https://github.com/jadelmag/forex-trader-bot.git
cd forex-trader-bot
```

### 2. Instalar dependencias

Si no quieres usar un entorno virtual, puedes instalar las dependencias directamente en tu sistema:

```bash
pip install -r requirements.txt
```

### 3. Ejecutar el bot

Opcion 1:

```bash
forex-trader-bot
```

Opcion 2:

```bash
python -m app.main
```

> Esto abrirá la interfaz gráfica de Tkinter.

---

## Comandos

#### Lanzar la aplicación principal
```bash
python -m app run
```

#### Lanzar la aplicación principal (alias)
```bash
python -m app start
```

#### Ejecutar todos los tests
```bash
python -m app test
```

#### Ver ayuda
```bash
python -m app help
```

---


## Uso básico

0. Opcional: Descarga más datos de velas de `https://drive.google.com/drive/folders/1IG_5SM3SLsxVeaDJlmL2qskex5EsTwjG`.
1. Haz clic en **Cargar Gráfica** para visualizar las velas.
2. Guarda los datos en el archivo `processed/processed_EURUSD_M1_2024.pkl` para cargarlos más rápido en otro momento y para que puedas usarlos en el backtesting.
3. Usa los botones **Zoom**, **Pan** y **Exportar** según necesites.
4. Aplica diferentes estrategias de RL en el botón **Estrategia**.
5. Enseñale a encontrar patrones de velas en el botón **Entrenar**.
6. Ejecuta el backtesting en el botón **Backtesting**.


Si queremos entrenar la IA con 2000 velas tendremos que ir al fichero rl/rl_agent.py y modificar la variable window_size y que sea coincida con el tamaño de la ventana de la gráfica, que en este caso es 2000.

2️⃣ Recomendación práctica

Rango óptimo: 500 – 2000 velas
---
500 velas → rápido, suficiente para muchas estrategias intradía

1000 velas → equilibrio entre información y rendimiento

2000 velas → solo si tu estrategia necesita analizar tendencias muy largas

***Nunca pases más de 2000–3000 velas a menos que tengas hardware muy potente, porque el vector de observación crecerá demasiado.***

---

## Exportar datos

* Puedes exportar los datos históricos de la gráfica a un archivo CSV usando el botón **Exportar**.

---

## Recomendaciones

* Mantén conexión estable a Internet.
* No mezcles librerías de este entorno con otros proyectos para evitar conflictos.
* Para actualizar FinRL:

```bash
pip install --upgrade git+https://github.com/AI4Finance-Foundation/FinRL.git
```

---

## Estrategias

#### 1. ADX Strategy
Estrategia de tendencia que usa el Índice de Movimiento Direccional Promedio (ADX) para identificar la fuerza de la tendencia y su dirección.

#### 2. Trend Following (EMA Crossover)
Estrategia de seguimiento de tendencia que utiliza el cruce de medias móviles exponenciales (EMA) para generar señales de compra/venta.

#### 3. Breakout (HH/LL)
Estrategia de ruptura que identifica nuevos máximos y mínimos para entrar en posiciones en la dirección de la ruptura.

#### 4. RSI Strategy
Estrategia de sobrecompra/sobreventa basada en el Índice de Fuerza Relativa (RSI).

#### 5. Moving Average Crossover (SMA)
Estrategia que utiliza el cruce de medias móviles simples para generar señales de trading.

#### 6. MACD Strategy
Estrategia basada en la convergencia/divergencia de medias móviles (MACD).

#### 7. Bollinger Bands Strategy
Estrategia que utiliza las bandas de Bollinger para identificar condiciones de sobrecompra/sobreventa.

#### 8. Stochastic Oscillator Strategy
Estrategia basada en el oscilador estocástico para identificar puntos de reversión.

#### 9. Ichimoku Cloud Strategy
Sistema de trading completo que utiliza la nube de Ichimoku para identificar tendencias, soportes y resistencias.

#### 10. Support & Resistance Strategy
Estrategia que identifica y opera en niveles de soporte y resistencia.

#### 11. Supply & Demand Zones
Estrategia que identifica zonas de oferta y demanda basadas en fractales para operaciones de reversión.

#### 12. Trendline Strategy
Utiliza regresión lineal móvil para identificar líneas de tendencia y operar en rupturas o rebotes.

#### 13. Scalping 1M Strategy
Estrategia de scalping en gráficos de 1 minuto que combina EMA y RSI para entradas rápidas.

#### 14. News Trading Strategy
Estrategia que opera en eventos de noticias, identificando picos de volatilidad para entradas estratégicas.

#### 15. Range Trading Strategy
Estrategia de reversión a la media que opera en mercados laterales identificados por el ancho de banda de las Bandas de Bollinger.

#### 16. Carry Trade Strategy
Estrategia que aprovecha los diferenciales de tasas de interés entre divisas.

#### 17. Hedging Overlay
Estrategia de cobertura que reduce la exposición en períodos de alta volatilidad.

#### 18. Grid Trading Strategy
Estrategia que coloca órdenes por encima y por debajo del precio actual en una cuadrícula predefinida.

## Estrategias de Velas

#### 1. Hammer Reversal
Identifica patrones de martillo en tendencias bajistas como señales de reversión alcista. Se confirma con el cierre por encima de la EMA20.

#### 2. Bullish Engulfing Reversal
Detecta patrones envolventes alcistas que indican una posible reversión de tendencia bajista. Incluye filtros de volumen y tamaño de vela.

#### 3. Morning Star Swing
Patrón de 3 velas que indica una reversión alcista, especialmente efectivo en tendencias bajistas. Se confirma con el cierre por encima de la EMA50.

#### 4. Hanging Man Reversal
Patrón de vela que señala una posible reversión bajista después de una tendencia alcista. Se confirma con el cierre por debajo de la EMA20.

#### 5. Bearish Engulfing Reversal
Patrón de envolvente bajista que indica una posible reversión de tendencia alcista. Incluye validación de volumen y contexto de mercado.

#### 6. Evening Star Swing
Patrón de 3 velas que señala una reversión bajista, especialmente efectivo en tendencias alcistas. Se confirma con el cierre por debajo de la EMA50.

#### 7. Doji Indecision
Patrón de vela que muestra indecisión en el mercado, con apertura y cierre prácticamente iguales. Útil para identificar posibles cambios de tendencia cuando aparece en niveles clave.

#### 8. Marubozu Trend
Vela con cuerpo largo y sombras pequeñas que indica fuerte presión compradora (verde) o vendedora (roja). Se utiliza para confirmar la continuación de la tendencia.

#### 9. Three White Soldiers
Patrón de continuación alcista formado por tres velas alcistas consecutivas con cierres progresivamente más altos, indicando fuerte impulso comprador.

#### 10. Three Black Crows
Patrón de continuación bajista formado por tres velas bajistas consecutivas con cierres progresivamente más bajos, indicando fuerte presión vendedora.

#### 11. Piercing Line
Patrón de dos velas que sugiere una reversión alcista. La segunda vela se abre por debajo del mínimo de la primera pero cierra por encima de su punto medio.

#### 12. Dark Cloud Cover
Patrón de dos velas que sugiere una reversión bajista. La segunda vela se abre por encima del máximo de la primera pero cierra por debajo de su punto medio.

#### 13. Tweezer Tops/Bottoms
Patrón de dos velas que marca un cambio de tendencia, donde los máximos (tops) o mínimos (bottoms) de las velas son casi idénticos.

#### 14. Harami Cross
Patrón de dos velas donde una vela Doji está contenida dentro del rango de la vela anterior, indicando indecisión después de una tendencia fuerte.

#### 15. Abandoned Baby
Raro patrón de tres velas que incluye un gap de precios y una vela Doji, que señala una posible reversión de tendencia.

## Patrones de Velas

#### 1. Doji
Indica indecisión en el mercado, con apertura y cierre prácticamente iguales. Aparece en techos, suelos o como confirmación de continuación.

#### 2. Hammer
Patrón de reversión alcista con un cuerpo pequeño en la parte superior y una sombra inferior larga (al menos el doble del cuerpo). Aparece en tendencias bajistas.

#### 3. Hanging Man
Similar al martillo pero aparece en una tendencia alcista, indicando posible reversión bajista. Tiene un pequeño cuerpo superior y una larga sombra inferior.

#### 4. Shooting Star
Patrón de reversión bajista con una sombra superior larga y un cuerpo pequeño cerca del mínimo. Aparece en tendencias alcistas.

#### 5. Spinning Top
Indica indecisión en el mercado, con un cuerpo pequeño y sombras de longitud similar. Sugiere un posible cambio de tendencia.

#### 6. Inverted Hammer
Patrón de reversión alcista con una sombra superior larga y un cuerpo pequeño cerca del mínimo. Aparece en tendencias bajistas.

#### 7. Morning Star
Patrón de reversión alcista de tres velas: una vela bajista grande, seguida por una pequeña vela con un gap a la baja, y luego una vela alcista grande.

#### 8. Evening Star
Patrón de reversión bajista de tres velas: una vela alcista grande, seguida por una pequeña vela con un gap al alza, y luego una vela bajista grande.

#### 9. Bullish Engulfing
Patrón de dos velas donde la segunda vela alcista "envuelve" completamente a la vela bajista anterior, indicando un cambio en el control del mercado.

#### 10. Bearish Engulfing
Patrón de dos velas donde la segunda vela bajista "envuelve" completamente a la vela alcista anterior, indicando un cambio en el control del mercado.

#### 11. Piercing Line
Patrón de dos velas alcistas donde la segunda vela cierra por encima del punto medio de la vela anterior, indicando un posible cambio de tendencia.

#### 12. Dark Cloud Cover
Patrón de dos velas bajistas donde la segunda vela cierra por debajo del punto medio de la vela anterior, indicando un posible cambio de tendencia.

#### 13. Tweezer Tops/Bottoms
Patrón de dos velas donde los máximos (tops) o mínimos (bottoms) son casi idénticos, indicando un posible cambio de dirección.

#### 14. Harami Cross
Patrón de dos velas donde una vela Doji está completamente contenida dentro del rango de la vela anterior, indicando indecisión.

#### 15. Abandoned Baby
Raro patrón de tres velas que incluye un gap de precios y una vela Doji, que señala una posible reversión de tendencia.

#### 16. Three Inside Up/Down
Patrón de tres velas que confirma un cambio de tendencia, con la tercera vela cerrando por encima/abajo del cierre de la primera vela.

#### 17. Three Outside Up/Down
Fuerte patrón de reversión de tres velas donde la segunda vela envuelve a la primera, y la tercera confirma la dirección.

#### 18. Breakaway
Patrón de cinco velas que comienza con una fuerte tendencia seguida por una consolidación y luego una continuación en la dirección original.

#### 19. Three-Line Strike
Patrón de continuación de cuatro velas donde tres velas muestran una fuerte tendencia, seguidas por una cuarta vela que retrocede pero no rompe la tendencia.

#### 20. Two Black Gapping
Patrón de continuación bajista que ocurre después de una ruptura de soporte, con dos velas negras separadas por un gap a la baja.

#### 21. Mean Reversion Overlay
Estrategia que identifica condiciones de sobrecompra/sobreventa extremas para operar contra la tendencia actual, basada en la teoría de que los precios tienden a volver a su media histórica.

#### 22. Martingale Overlay
Sistema de gestión de capital que duplica el tamaño de la posición después de una pérdida, diseñado para recuperar pérdidas pasadas con una sola operación ganadora. Se recomienda usar con extrema precaución.

#### 23. Price Action Patterns
Estrategia avanzada que combina múltiples patrones de acción del precio, incluyendo velas individuales, formaciones de múltiples velas y estructuras de mercado para identificar oportunidades de trading de alta probabilidad.

#### 24. Stochastic Strategy
Estrategia basada en el oscilador estocástico que identifica condiciones de sobrecompra y sobreventa, con filtros de tendencia para mejorar la precisión de las señales.

#### 25. Stochastic Oscillator Strategy
Variante avanzada que utiliza múltiples configuraciones del oscilador estocástico (rápido y lento) junto con divergencias para identificar posibles puntos de reversión del mercado.


---

## Ficheros CSV - FX-1-Minute-Data

Los ficheros se han obtenido de `https://github.com/philipperemy/FX-1-Minute-Data`.

Su proyecto permite [descargar los ficheros de velas de Forex](https://drive.google.com/drive/folders/1IG_5SM3SLsxVeaDJlmL2qskex5EsTwjG) y guardarlos en el directorio `csv/`.



El repositorio https://github.com/philipperemy/FX-1-Minute-Data de Philippe Remy es una base de datos completa de datos históricos de Forex (FX) en resolución de 1 minuto.

📊 Qué contiene:
Datos de 27 pares de divisas principales:

- EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, NZD/USD
- Y cruces como EUR/GBP, EUR/JPY, GBP/JPY, etc.
- Período cubierto: Desde 1999 hasta 2020 (dependiendo del par)
- Datos en formato CSV comprimido (.zip)

Estructura de datos:
Cada archivo CSV contiene:

| Timestamp           | Open   | High   | Low     | Close  | Volume |
|---------------------|--------|--------|---------|--------|--------|
| 2003-05-04 17:00:00 | 1.1234 | 1.1235 | 1.1233  | 1.1234 |   125  |
| 2003-05-04 17:01:00 | 1.1234 | 1.1236 | 1.1233  | 1.1235 |   118  |

🚀 Para qué sirve:
1. Backtesting de alta frecuencia
Ideal para probar estrategias de scalping o trading intradía

Resolución de 1 minuto permite análisis detallado

2. Investigación cuantitativa
Entrenamiento de modelos de machine learning

Análisis estadístico de mercados Forex

3. Desarrollo de bots de trading
Datos limpios y consistentes para desarrollo

Gran volumen de datos históricos

⚡ Ventajas para tu bot de trading:
✅ Calidad de datos:
Datos ya limpios y preprocesados

Sin gaps significativos en las series temporales

✅ Evita límites de APIs:
No dependes de Yahoo Finance ni sus límites

Datos disponibles localmente

✅ Mayor histórico:
+20 años de datos vs. límite de Yahoo Finance

Ideal para backtesting a largo plazo
* Yahoo Finance tiene datos de 1 minuto pero con histórico muy limitado

## Telegram API

Pasos para obtenerlos:

Ve a 👉 https://my.telegram.org

1. Inicia sesión con tu número de teléfono (el mismo que usas en la app de Telegram).

2. Te llegará un código por Telegram para verificar.

3. Una vez dentro, haz clic en ``API development tools``.

4. Rellena el formulario con cualquier nombre de aplicación (ejemplo: ForexNotifier) y una URL (puedes poner cualquier cosa, no es obligatorio que exista).

5. Después de enviarlo, verás:

    * **API_ID** → un número entero.
    * **API_HASH** → una cadena larga de letras y números.


## Funcionalidades Principales

### 📧 Sistema de Reportes Automáticos por Email

**Configuración:**
- Accede al menú **Streamer → Configuración** para configurar el sistema de reportes
- Configura tu email, contraseña y frecuencia de envío (en horas)
- Soporta Gmail, Outlook, Yahoo y otros proveedores SMTP

**Características:**
- **Envío automático:** Reportes programados cada X horas según configuración
- **Contenido completo:** Estado del capital, operaciones abiertas, P&L, estadísticas
- **Archivos adjuntos:** Reportes en formato .txt para historial
- **Detección automática:** Configuración SMTP automática según proveedor de email
- **Gestión inteligente:** Limpieza automática de reportes antiguos (30 días)

**Métodos principales:**
- `SchedulerService._should_send_report()` - Detecta cuando han pasado las horas configuradas
- `EmailService.send_report_email()` - Envía el reporte por correo electrónico
- `ReportGenerator.generate_trading_report()` - Genera el contenido del reporte

**Archivos de configuración:**
- `config/app_config.json` - Configuración de email y frecuencia
- `config/scheduler_state.json` - Estado del último envío
- `reports/trading_report_*.txt` - Reportes generados

### 🔄 Gestión Automática
- El scheduler se inicia automáticamente al abrir la aplicación
- Se reinicia automáticamente al cambiar la configuración
- Se detiene correctamente al cerrar la aplicación
- Manejo robusto de errores de conexión SMTP


## Videos

[Como realizar backtesting](https://youtu.be/NNO-L6AWeSM)

[Como realizar operaciones en tiempo real seleccionando las estrategias](https://youtu.be/QaaT-ywXcuU)


## Licencia

Commons Clause + Apache/MIT