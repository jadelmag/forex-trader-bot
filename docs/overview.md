# Forex Trader Bot — Overview

Aplicación de trading para Forex con interfaz gráfica (Tkinter), simulación con datos históricos y en vivo, gestión de riesgo profesional, estrategias técnicas y de velas, patrones de velas, backtesting y entrenamiento de agentes de RL (FinRL + Stable-Baselines3).

---

## 1) Funcionalidades Clave

- Datos y gráficos
  - Carga de CSV históricos y preprocesados PKL.
  - Streaming de velas en vivo (TradingView/Binance) vía `trading_view/candle_streamer.py`.
  - Gráfico de velas con zoom/pan y tooltips (`app/candlestick_chart.py`).
- Estrategias y patrones
  - Estrategias técnicas clásicas y de price action en `strategies/`.
  - Estrategias de velas con entradas/salidas explícitas y trailing stop (`strategies/candle_strategies.py`).
  - Detección robusta de patrones de velas en `patterns/`.
- Ejecución y riesgo
  - Gestor de riesgo centralizado, tamaño de posición basado en riesgo fijo (% capital).
  - Aperturas por señales, cierres automáticos por SL/TP, cambio de señal y trailing ATR.
- Simulación y backtesting
  - Simulaciones por modal con datos CSV/PKL y con datos en vivo (Binance/TradingView).
  - Backtesting en `backtesting/`.
- IA/Reinforcement Learning
  - Entrenamiento de agentes RL (FinRL + SB3) con `rl/` y `ia/` y modales de entrenamiento.
- Reportes y automatización
  - Reportes de trading por email programados (Scheduler/SMTP).
  - Generación de reportes `.txt` en `reports/`.
- Integraciones
  - Notificaciones Telegram (opcional).
  - Configuración centralizable desde la app.

---

## 2) Interfaz Gráfica y Módulos Principales

- Ventana principal
  - `app/gui_main.py`: orquesta frames, menús, modales y callbacks.
  - `app/window.py`: ventana principal.
- Gráficos y carga de datos
  - `app/candlestick_chart.py`: dibuja velas (CSV/yfinance).
  - `app/grafico_manager.py`: coordinación del gráfico y herramientas.
  - `app/csv_loader_modal.py`, `app/csv_to_pkl_modal.py`: carga CSV y conversión a PKL.
  - `app/processed_loader_modal.py`: carga de `.pkl` listos para backtesting/simulación.
- Simulaciones
  - `app/strategies_modal.py`: simulación de estrategias técnicas con datos históricos.
  - `app/candle_strategies_modal.py`: simulación de estrategias de velas.
  - `app/binance_modal.py`: simulación con flujo en vivo (usa `trading_view/candle_streamer.py`).
- Reporting y configuración
  - `app/config_app_modal.py`: configuración de email y frecuencia de reportes.
  - `app/scheduler_service.py`, `app/email_service.py`, `app/report_generator.py`: pipeline de reportes programados.
- Entrenamiento IA/RL
  - `app/ai_training_modal.py`, `app/rl_training_modal.py`, `app/ai_trainer.py`.
- Utilidades
  - `app/progress_modal.py`, `app/reports.py`, `app/test_runner.py`, `app/csv_manager.py`, `app/tooltip_zoom_pan.py`.
- Entrada principal
  - `app/__main__.py` y `app/main.py`.

---

## 3) Datos: CSV, PKL y Streaming en Vivo

- CSV históricos
  - Directorio `csv/` con múltiples activos (ej. `csv/eurusd/*.csv`).
  - Conversión a `.pkl` en `processed/` para carga rápida y backtesting.
- Preprocesados PKL
  - Archivos en `processed/` listos para simulación/backtesting.
- Streaming TradingView/Binance
  - `trading_view/candle_streamer.py`: flujo de velas en vivo y callbacks.
  - `trading_view/config_modal.py`: configuración de la conexión.
  - Validación en `app/binance_modal.py` para usar data en vivo aunque no haya CSV cargado.
  - Timeouts y reconexión con backoff mejorados para evitar "ping/pong timed out".

---

## 4) Estrategias Técnicas (carpeta `strategies/`)

- `strategies/strategies.py`: colección de estrategias Forex (ADX, RSI, SMA/EMA crossovers, MACD, Bollinger, Stochastic, Ichimoku, Soporte/Resistencia, HH/LL breakouts, scalping, range, etc.). Ver lista extendida en `README.md`.
- `strategies/strategies_utils.py`: utilidades de señales y cálculos.
- Gestión de riesgo
  - `strategies/risk_manager.py`: tamaño de posición, slots máximos, P&L y cierres por señal/SL/TP.

---

## 5) Estrategias de Velas con Cierres Explícitos

- `strategies/candle_strategies.py` (rediseñado)
  - Columnas `ExecSignal` (-1/0/1) y `Position`.
  - Cierres automáticos por:
    - Señal contraria (SIGNAL_CHANGE).
    - Stop Loss / Take Profit automáticos.
    - Trailing stop basado en ATR (opcional).
    - Reversión por patrón opuesto (PATTERN_REVERSAL).
  - Cálculo y tracking de `StopLoss`, `TakeProfit` y `ExitReason`.
  - Estrategias ejemplo: `hammer_reversal_strategy()`, `bullish_engulfing_strategy()`, `morning_star_strategy()`, `scalping_reversal_strategy()`, `aggressive_reversal_strategy()`, `conservative_swing_strategy()`.
- `app/candle_strategies_modal.py`
  - Carga dinámica de estrategias con checkboxes.
  - Límite de operaciones concurrentes, barra de progreso, estadísticas en tiempo real.
  - Procesamiento por subconjuntos y orden correcto de eventos (cerrar antes de abrir).

---

## 6) Patrones de Velas (carpeta `patterns/`)

- `patterns/candlestickpatterns.py`, `patterns/pattern_utils.py`
  - Revisión completa de múltiples patrones:
    - Doji, Spinning Top, Piercing Line, Dark Cloud Cover, Three Black Crows.
    - Tweezer Top/Bottom con contexto de tendencia.
    - Morning/Evening Star con validaciones correctas.
    - Three Inside Up/Down reimplementados.
    - Rising/Falling Three Methods reimplementados.
  - Consistencia en valores de retorno y detección.
- Integración
  - Consumidos por `strategies/candle_strategies.py` (no se seleccionan manualmente en el modal).

---

## 7) Ejecución y Gestión de Riesgo

- `strategies/risk_manager.py`
  - Apertura de operaciones al recibir señal de entrada.
  - Cierres automáticos por SL/TP, cambio de señal de la misma estrategia, fin de simulación o manual.
  - Fijación de riesgo por operación: se reserva solo el monto en riesgo (p.ej. 1% del capital), no el valor nocional completo.
  - Al cierre, devuelve riesgo reservado + P&L.
  - Control de slots máximos y capital mínimo (p.ej., $100) con avisos “OPERACIÓN SALTADA”.
  - Prevención de mensajes duplicados por vela.
- Cálculo de Equity corregido en la GUI para BUY: usa P&L `(precio_actual - precio_entrada) * lot_size`.

---

## 8) Simulación y Backtesting

- Simulación histórica
  - `app/strategies_modal.py` y `app/candle_strategies_modal.py` con CSV/PKL.
- Simulación en vivo (Binance/TradingView)
  - `app/binance_modal.py` + `trading_view/candle_streamer.py`.
- Backtesting
  - `backtesting/backtester.py`.

Ambas rutas integran RiskManager, estadísticas en tiempo real y reportes.

---

## 9) RL/IA: FinRL + Stable-Baselines3

- Entorno y agente
  - `rl/rl_env.py`: entorno Gymnasium.
  - `rl/rl_agent.py`: agente RL y utilidades.
  - `ia/trading_rl_agent.py`: lógica complementaria.
- Entrenamiento y modales
  - `app/ai_training_modal.py`, `app/rl_training_modal.py`, `app/ai_trainer.py`.
- Salidas
  - Modelos en `models_rl/`, logs en `logs/` y `tensorboard_logs/`.
- Recomendaciones
  - Usar 500–2000 velas; ajustar `window_size` en `rl/rl_agent.py`.

---

## 10) Reportes Automáticos por Email

- Configuración
  - Modal: `app/config_app_modal.py`.
  - Persistencia: `config/app_config.json`.
- Programación y envío
  - `app/scheduler_service.py`: tiempos de envío y reinicios.
  - `app/email_service.py`: SMTP y manejo de errores.
  - `app/report_generator.py`: contenido del reporte (capital, operaciones, P&L, estadísticas).
- Salidas
  - Archivos en `reports/trading_report_*.txt`.

---

## 11) Notificaciones de Telegram (opcional)

- `telegram/telegram-notifier.py`, `telegram/__init__.py`.
  - Requiere `API_ID` y `API_HASH`.

---

## 12) Estructura del Proyecto (resumen)

- `app/` GUI y modales.
- `strategies/` estrategias y gestión de riesgo.
- `patterns/` patrones de velas.
- `trading_view/` streaming y configuración.
- `backtesting/`, `rl/`, `ia/` para análisis y entrenamiento.
- `csv/`, `processed/` para datasets.
- `reports/`, `logs/`, `models_rl/` para salidas.

---

## 13) Requisitos y Ejecución

- Requisitos: Python 3.11, internet, Git. Dependencias en `requirements.txt`.
- Ejecución GUI:
  - `forex-trader-bot`
  - `python -m app.main`
  - `python -m app run` (alias `start`).

---

## 14) Buenas Prácticas de Uso

- Usa `.pkl` en `processed/` para acelerar cargas.
- Limita velas a 500–2000 para rendimiento.
- Ajusta slots y riesgo en RiskManager según tu capital.
- Para streaming en vivo, conexión estable; el sistema reintenta con backoff.
- Configura reportes por email para auditoría automática.

---

## 15) Limitaciones y TODO

- Optimización continua de estrategias.
- Reconexión y resiliencia de streaming: mejorada, pero depende de la red.
- Integración futura con MetaTrader (planificada).
- Mantener consistencia de versiones de IA.

---

## 16) Licencia

- Commons Clause + Apache/MIT (ver `LICENSE`).
