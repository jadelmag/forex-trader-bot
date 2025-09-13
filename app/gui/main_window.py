# app/gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from pathlib import Path

from ..gui.components.menu_bar import MenuBar
from ..gui.components.status_bar import StatusBar
from ..gui.components.log_panel import LogPanel
from ..gui.components.telegram_panel import TelegramPanel
from ..gui.managers.thread_manager import ThreadManager
from ..gui.managers.cache_manager import CacheManager
from ..handlers.csv_handler import CSVHandler
from ..handlers.pattern_handler import PatternHandler
from ..handlers.strategy_handler import StrategyHandler
from ..handlers.rl_handler import RLHandler
from ..handlers.simulation_handler import SimulationHandler
from ..handlers.telegram_handler import TelegramHandler
from ..utils.helpers import setup_styles, load_icon
from ..utils.constants import COLORS, DIMENSIONS

class GUIPrincipal:
    def __init__(self, root):
        self.root = root
        self._setup_main_window()
        self._initialize_managers()
        self._initialize_handlers()
        self._setup_gui_components()
        self._setup_bindings()
        
    def _setup_main_window(self):
        """Configura la ventana principal"""
        self.root.title("Trading Bot - Forex Market")
        self.root.geometry(DIMENSIONS['MAIN_WINDOW'])
        self.root.configure(bg=COLORS['BACKGROUND'])
        self.root.resizable(True, True)
        
        # Configurar estilos
        setup_styles()
        
        # Configurar icono
        load_icon(self.root)
        
    def _initialize_managers(self):
        """Inicializa los gestores de la aplicación"""
        self.thread_manager = ThreadManager(self)
        self.cache_manager = CacheManager()
        
    def _initialize_handlers(self):
        """Inicializa los manejadores de funcionalidad"""
        self.csv_handler = CSVHandler(self)
        self.pattern_handler = PatternHandler(self)
        self.strategy_handler = StrategyHandler(self)
        self.rl_handler = RLHandler(self)
        self.simulation_handler = SimulationHandler(self)
        self.telegram_handler = TelegramHandler(self)
        
    def _setup_gui_components(self):
        """Configura los componentes de la interfaz gráfica"""
        # Frame principal de controles
        self.frame_controls = tk.Frame(self.root, bg=COLORS['BACKGROUND'])
        self.frame_controls.pack(fill="x", padx=20, pady=10)
        
        # Contenedor central: gráfico + panel Telegram
        self.frame_middle = tk.Frame(self.root, bg=COLORS['BACKGROUND'])
        self.frame_middle.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Frame del gráfico
        self.frame_grafico = tk.Frame(self.frame_middle, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(side="left", fill="both", expand=True)
        
        # Panel de Telegram
        self.telegram_panel = TelegramPanel(self.frame_middle)
        
        # Panel de logs
        self.log_panel = LogPanel(self.root)
        
        # Barra de estado
        self.status_bar = StatusBar(self.frame_controls)
        
        # Barra de menús
        self.menu_bar = MenuBar(self, self.frame_controls)
        
    def _setup_bindings(self):
        """Configura los enlaces de eventos"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def run(self):
        """Inicia la aplicación"""
        self.root.mainloop()
        
    def on_closing(self):
        """Maneja el cierre de la aplicación"""
        # Limpiar recursos antes de cerrar
        self.thread_manager.shutdown()
        self.simulation_handler.cleanup()
        self.root.quit()