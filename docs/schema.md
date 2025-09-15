```
app/
├── gui/
│   ├── __init__.py
│   ├── main_window.py          # Clase GUIPrincipal principal
│   ├── components/
│   │   ├── __init__.py
│   │   ├── menu_bar.py         # Componentes de menú
│   │   ├── status_bar.py       # Barra de estado con información financiera
│   │   ├── log_panel.py        # Panel de logs
│   │   ├── telegram_panel.py   # Panel de Telegram
│   │   └── progress_bar.py     # Barra de progreso
│   └── managers/
│       ├── __init__.py
│       ├── thread_manager.py   # Gestión de threads y colas
│       ├── cache_manager.py    # Gestión de caché
│       └── strategy_manager.py # Gestión de estrategias
├── handlers/
│   ├── __init__.py
│   ├── csv_handler.py          # Manejo de CSV
│   ├── pattern_handler.py      # Manejo de patrones
│   ├── strategy_handler.py     # Manejo de estrategias
│   ├── rl_handler.py          # Manejo de aprendizaje por refuerzo
│   ├── simulation_handler.py   # Manejo de simulaciones
│   └── telegram_handler.py     # Manejo de Telegram
└── utils/
    ├── __init__.py
    ├── helpers.py              # Funciones auxiliares
    └── constants.py            # Constantes de la aplicación
```