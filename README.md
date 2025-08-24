# Forex Trader Bot

Bot de trading Forex con interfaz gráfica (Tkinter) y soporte de Reinforcement Learning (FinRL + Stable-Baselines3).

Este proyecto permite:

* Seleccionar pares de divisas.
* Cargar gráficos de velas con tooltips.
* Ejecutar estrategias de RL y backtesting.
* Exportar datos históricos a CSV.

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
├─ app/                     # Paquete principal
│ ├─ __init__.py            # Inicializa el paquete, importa Window
│ ├─ window.py              # Clase Window principal, coordina la GUI
│ ├─ gui_main.py            # Clase GUIPrincipal que organiza frames y widgets
│ ├─ candlestick_chart.py   # Clase CandlestickChart, dibuja velas de CSV o yfinance
│ ├─ forex_pairs.py         # Lista de pares de divisas e intervalos permitidos
│ ├─ tooltip_zoom_pan.py    # Funciones para tooltip, zoom y pan
│ ├─ csv_manager.py         # Clase CSVManager para manejar archivos CSV
│ ├─ grafico_manager.py     # Clase GraficoManager para manejar gráficos
│ ├─ yfinance_manager.py    # Clase YFinanceManager para manejar datos de Yahoo Finance
│ ├─ processed_data/        # Carpeta donde se guardan los archivos procesados (.pkl)
│ └─ main.py                # Función main() para ejecutar la app
│
├─ setup.py                 # Configuración del paquete y entry point
├─ requirements.txt         # Dependencias necesarias
├─ csv_parser.py            # Script para convertir CSV crudos de Dukascopy al formato estándar
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

## Uso básico

1. Selecciona la **moneda base** y la **moneda cotizada**.
2. Haz clic en **Confirmar**.
3. Selecciona el **periodo** y el **intervalo** de las velas.
4. Haz clic en **Cargar Gráfica** para visualizar las velas.
5. Usa los botones **Zoom**, **Pan** y **Exportar** según necesites.
6. Ejecuta estrategias RL haciendo clic en **Estrategia**.

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

## Problemas comunes

1. **Error de `websockets`**: asegúrate de tener la versión exacta `websockets==10.4`.
2. **Datos no encontrados**: algunos pares exóticos pueden no estar disponibles en Yahoo Finance.
3. **Problemas de Python**: este proyecto está probado con Python 3.11.

## Licencia

MIT

