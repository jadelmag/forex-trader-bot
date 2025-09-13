# app/gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from pathlib import Path

from app.gui.components.menu_bar import MenuBar
from app.gui.components.status_bar import StatusBar
from app.gui.components.log_panel import LogPanel
from app.gui.components.telegram_panel import TelegramPanel
from app.gui.managers.thread_manager import ThreadManager
from app.gui.managers.cache_manager import CacheManager
from app.gui.managers.strategy_manager import StrategyManager
from app.gui.handlers import CSVHandler, PatternModalHandler, StrategyHandler, RLHandler, SimulationHandler, TelegramHandler
from app.gui.utils.helpers import setup_styles, load_icon
from app.gui.utils.constants import COLORS, DIMENSIONS

# Importaciones adicionales del sistema original
from app.grafico_manager import GraficoManager

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
        self.strategy_manager = StrategyManager(self)
        
    def _initialize_handlers(self):
        """Inicializa los manejadores de funcionalidad"""
        self.csv_handler = CSVHandler(self)
        self.pattern_modal_handler = PatternModalHandler(self)
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
        
        # Inicializar el gestor de gráficos
        self.grafico_manager = GraficoManager(frame=self.frame_grafico)
        
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
        
    def reiniciar_app(self):
        """Reinicia la aplicación reemplazando el proceso actual por `python -m app.main`."""
        confirmar = messagebox.askyesno(
            "Reiniciar",
            "¿Seguro que quieres reiniciar la aplicación? Se perderá el estado actual.",
        )
        if not confirmar:
            return
        import sys
        import os
        python = sys.executable
        # Reemplaza el proceso: no regresa
        os.execl(python, python, "-m", "app.main")
            
    def log(self, message, color="white"):
        """Método de conveniencia para logging"""
        self.log_panel.log(message, color)
        
    def limpiar_grafico(self):
        """Limpia el gráfico actual"""
        self.df_actual = None
        if hasattr(self.grafico_manager, "limpiar"):
            self.grafico_manager.limpiar()
        if hasattr(self.grafico_manager, "canvas") and self.grafico_manager.canvas:
            self.grafico_manager.canvas.get_tk_widget().pack_forget()
            self.grafico_manager.canvas = None
            
    def _on_patrones_aplicados(self, df_actualizado):
        """Callback desde PatternsModal tras aplicar y dibujar patrones.
        Reasigna df_actual y reinstala los handlers de zoom/hover sobre el nuevo canvas/figura.
        """
        self.df_actual = df_actualizado
        # Actualizar el gráfico con los nuevos datos
        if hasattr(self.grafico_manager, "dibujar_csv"):
            self.grafico_manager.dibujar_csv(df_actualizado)
            
    def _dibujar_grafico(self, df):
        """Dibuja el gráfico con los datos proporcionados"""
        if hasattr(self, 'grafico_manager'):
            self.grafico_manager.dibujar_csv(df)
            
    def abrir_modal_patrones(self):
        """Abre el modal de patrones"""
        if self.csv_handler.df_actual is not None:
            try:
                from app.gui.modals.patterns_modal import PatternsModal
                PatternsModal(self.root, self.csv_handler.df_actual, self.grafico_manager, self, callback=self._on_patrones_aplicados)
            except Exception as e:
                self.log(f"Error abriendo modal de patrones: {str(e)}", color='red')
        else:
            from tkinter import messagebox
            messagebox.showwarning("Atención", "No hay datos cargados para aplicar patrones")
            
    def abrir_modal_candle_strategies(self):
        """Abre el modal de estrategias de velas"""
        if self.csv_handler.df_actual is not None:
            try:
                from app.gui.modals.candle_strategies_modal import CandleStrategiesModal
                CandleStrategiesModal(self.root, self.csv_handler.df_actual, self)
            except Exception as e:
                self.log(f"Error abriendo modal de estrategias de velas: {str(e)}", color='red')
        else:
            from tkinter import messagebox
            messagebox.showwarning("Atención", "No hay datos cargados para aplicar candle estrategias")
            
    def cleanup_on_exit(self):
        """Limpieza completa al cerrar la aplicación"""
        try:
            self.log("🧹 Iniciando limpieza de la aplicación...", color="orange")
            
            # 1. Detener streamer si está activo
            if hasattr(self, 'simulation_handler') and self.simulation_handler.candle_streamer:
                try:
                    self.log("🚫 Deteniendo streamer...", color="orange")
                    self.simulation_handler.candle_streamer.stop()
                except Exception as e:
                    print(f"Error deteniendo streamer: {e}")
            
            # 2. Detener entrenamiento IA si está activo
            if hasattr(self, '_ai_trainer') and self._ai_trainer:
                try:
                    self.log("🤖 Deteniendo entrenamiento IA...", color="orange")
                    self._ai_trainer.stop()
                except Exception as e:
                    print(f"Error deteniendo AI trainer: {e}")
            
            # 3. Cerrar operaciones activas del RiskManager
            if hasattr(self, 'simulation_handler') and hasattr(self.simulation_handler, 'risk_manager'):
                try:
                    self.log("💹 Cerrando operaciones activas...", color="orange")
                    risk_manager = self.simulation_handler.risk_manager
                    if hasattr(risk_manager, 'operaciones_activas'):
                        operaciones_activas = getattr(risk_manager, 'operaciones_activas', [])
                        for op in operaciones_activas[:]:
                            if hasattr(op, 'estado') and op.estado == 'ACTIVA':
                                try:
                                    precio_cierre = getattr(op, 'precio_entrada', 1.0)
                                    if hasattr(self.csv_handler, 'df_actual') and self.csv_handler.df_actual is not None and not self.csv_handler.df_actual.empty:
                                        precio_cierre = self.csv_handler.df_actual['Close'].iloc[-1]
                                    op.cerrar(precio_cierre, "CIERRE_APLICACION")
                                except Exception as e:
                                    print(f"Error cerrando operación {op}: {e}")
                except Exception as e:
                    print(f"Error procesando operaciones del RiskManager: {e}")
            
            # 4. Detener procesos de entrenamiento IA/RL
            if hasattr(self, 'rl_handler') and hasattr(self.rl_handler, 'rl_agent') and self.rl_handler.rl_agent:
                try:
                    self.log("🤖 Deteniendo agente RL...", color="orange")
                    if hasattr(self.rl_handler.rl_agent, 'cleanup'):
                        self.rl_handler.rl_agent.cleanup()
                except Exception as e:
                    print(f"Error deteniendo RL agent: {e}")
            
            # 5. Terminar threads activos
            import threading
            active_threads = threading.active_count()
            if active_threads > 1:
                self.log(f"🧵 Esperando {active_threads-1} threads activos...", color="orange")
                import time
                time.sleep(1.0)
            
            # 6. Limpiar recursos de gráficos
            if hasattr(self, 'grafico_manager') and self.grafico_manager:
                try:
                    import matplotlib.pyplot as plt
                    plt.close('all')
                except Exception as e:
                    print(f"Error cerrando gráficos: {e}")
            
            # 7. Cerrar thread manager
            if hasattr(self, 'thread_manager'):
                try:
                    self.thread_manager.shutdown()
                except Exception as e:
                    print(f"Error cerrando thread manager: {e}")
            
            self.log("✅ Limpieza completada. Cerrando aplicación...", color="green")
            
        except Exception as e:
            print(f"Error durante limpieza general: {e}")
        finally:
            # Forzar cierre de la ventana principal
            try:
                self.root.quit()
            except:
                pass
            try:
                self.root.destroy()
            except:
                pass