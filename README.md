# Forex Trader Bot

Bot de trading Forex con interfaz gráfica (Tkinter) y soporte de Reinforcement Learning (FinRL + Stable-Baselines3).

Este proyecto permite:

* Cargar pares de divisas en CSV.
* Cargar gráficos de velas con tooltips.
* Ejecutar estrategias de RL y backtesting.
* Exportar datos históricos a PKL.

---

## Requisitos

* Python 3.11 [Download: https://www.python.org/downloads/]
* Conexión a internet (para descargar datos de Yahoo Finance y FinRL)
* Git (para clonar el repositorio) [Download: https://git-scm.com/downloads]

---

## Estructura del proyecto

```
forex-trader-bot/
│
├─ csv/                     # Archivos CSV de velas
│ ├─ DAT_ASCII_EURUSD_M1_2023.csv # Velas de EUR/USD
│ └─ DAT_ASCII_EURUSD_M1_2024.csv # Velas de EUR/USD
|
├─ assets/                  # Archivos de assets
│ └─ icon.png               # Icono de la aplicación
|
|
├─ rl/                      # Archivos de RL
│ ├─ __init__.py            # ForexRL
│ └─ rl_agent.py            # Incluye ForexRLAgent y el entorno ForexTradingEnv
│ └─ rl_env.py              # El entorno Gymnasium (TradingEnv)
|
├─ processed/               # Carpeta donde se guardan los archivos procesados (.pkl)
├─ backtesting/             # Carpeta donde se guardan los archivos de backtesting
| ├─ __init__.py            # ForexBacktester
| └─ backtester.py          # Fichero de backtesting
| 
├─ strategies/              # Carpeta donde se guardan los archivos de estrategias
| ├─ __init__.py            # ForexStrategies
| └─ strategies.py          # Estrategias de trading
├─ patterns/                # Carpeta donde se guardan los archivos de patrones de velas
| ├─ __init__.py            # CandlestickPatterns
| └─ candlestickpatterns.py # Patrones de velas
|
|
├─ app/                     # Paquete principal
│ ├─ __init__.py            # Inicializa el paquete, importa Window
│ ├─ candlestick_chart.py   # Clase CandlestickChart, dibuja velas de CSV o yfinance
│ ├─ csv_loader_modal.py    # Clase CSVLoaderModal, permite cargar CSVs
│ ├─ csv_manager.py         # Clase CSVManager para manejar archivos CSV
│ ├─ grafico_manager.py     # Clase GraficoManager para manejar gráficos
│ ├─ gui_main.py            # Clase GUIPrincipal que organiza frames y widgets
│ ├─ main.py                # Función main() para ejecutar la app
│ ├─ progress_modal.py      # Clase ProgressModal, muestra progreso de operaciones
│ ├─ tooltip_zoom_pan.py    # Funciones para tooltip, zoom y pan
│ └─ window.py              # Clase Window principal, coordina la GUI
│
├─ requirements.txt         # Dependencias necesarias
├─ csv_parser.py            # Script para convertir CSV crudos de Dukascopy al formato estándar
├─ setup.py                 # Configuración del paquete y entry point
└─ README.md                # Instrucciones de instalación y uso
```

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

--

## Uso básico

0. Opcional: Descarga más datos de velas de `https://drive.google.com/drive/folders/1IG_5SM3SLsxVeaDJlmL2qskex5EsTwjG`.
1. Haz clic en **Cargar Gráfica** para visualizar las velas.
2. Guarda los datos en el archivo `processed/processed_EURUSD_M1_2024.pkl` para cargarlos más rápido en otro momento y para que puedas usarlos en el backtesting.
3. Usa los botones **Zoom**, **Pan** y **Exportar** según necesites.
4. Aplica diferentes estrategias de RL en el botón **Estrategia**.
5. Enseñale a encontrar patrones de velas en el botón **Entrenar**.
6. Ejecuta el backtesting en el botón **Backtesting**.

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

| Timestamp           | Open | High | Low | Close | Volume |
|---------------------|------|------|-----|-------|--------|
| 2003-05-04 17:00:00 | 1.1234 | 1.1235 | 1.1233 | 1.1234 | 125 |
| 2003-05-04 17:01:00 | 1.1234 | 1.1236 | 1.1233 | 1.1235 | 118 |

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

## Licencia

MIT

## Backtesting

1. Definir la estrategia con reglas claras

Entradas: ¿Qué condiciones técnicas o fundamentales disparan una orden?
Salidas: ¿Cuándo cierras la operación? (take profit, stop loss, trailing stop, condiciones técnicas, etc.)
Gestión de riesgo: % de capital arriesgado por operación.
Sin reglas claras, no puedes medir resultados de forma consistente.

2. Conseguir datos históricos de calidad

Idealmente tick data o al menos velas de 1 minuto.

3. Simulación realista

Modelar spreads y comisiones: el spread en Forex cambia con volatilidad, no es fijo.

Slippage: en alta volatilidad, no siempre entras/sales al precio deseado.

Horario de mercado: no todos los pares tienen la misma liquidez.

Esto evita que tu backtest sea demasiado optimista.

4. Herramientas para backtesting

Plataformas listas:

MetaTrader 4/5 → con Strategy Tester.

TradingView → backtest en Pine Script.

Programación personalizada:

Python → librerías como backtrader, zipline, quantconnect.

R o Matlab para análisis más matemático.

5. Evaluación de resultados

Más allá de la ganancia neta, mide:

Sharpe ratio / Sortino ratio → relación riesgo/beneficio.

Drawdown máximo → cuánto cae tu cuenta en la peor racha.

Win rate y profit factor (ganancia promedio / pérdida promedio).

Expectancy → beneficio esperado por operación.

6. Walk-forward y validación fuera de muestra

4. Lo que quiero es que cuando después de pulsar en aceptar el modal los patrones seleccionados se muestre en la grafica se destaque los patrones y que muestre cuando empiece y cuando acaba el patron.