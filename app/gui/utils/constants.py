# app/utils/constants.py

# Dimensiones de la interfaz
DIMENSIONS = {
    'MAIN_WINDOW': '1650x1000',
    'LOG_HEIGHT': 120,
}

# Colores de la interfaz
COLORS = {
    'BACKGROUND': '#F0F0F0',
    'LOG_BACKGROUND': '#F8F8F8',
    'TEXT_WHITE': 'white',
    'TEXT_GREEN': 'green',
    'TEXT_RED': 'red',
    'TEXT_BLUE': 'blue',
    'TEXT_CYAN': 'cyan',
    'TEXT_YELLOW': 'yellow',
    'TEXT_ORANGE': 'orange',
}

# Textos de la interfaz
TEXTS = {
    'APP_TITLE': 'Trading Bot - Forex Market',
    'STATUS_INITIAL': 'Listo',
    'STATUS_LOADING': 'Cargando...',
    'STATUS_PROCESSING': 'Procesando...',
}

# Rutas de archivos
PATHS = {
    'ICON': 'icon.ico',
    'DATA_DIR': 'data',
    'PROCESSED_DIR': 'processed_data',
    'MODELS_DIR': 'models',
    'STRATEGIES_DIR': 'strategies',
}

# Configuración de estrategias
STRATEGY_CONFIG = {
    'DEFAULT_MAX_ORDERS': 5,
    'DEFAULT_RISK_PER_TRADE': 0.02,  # 2% del capital por operación
    'DEFAULT_STOP_LOSS': 0.01,       # 1% de stop loss
    'DEFAULT_TAKE_PROFIT': 0.02,     # 2% de take profit
}

# Configuración de Telegram
TELEGRAM_CONFIG = {
    'DEFAULT_CHAT_ID': '',
    'DEFAULT_BOT_TOKEN': '',
    'DEFAULT_ENABLED': False,
}