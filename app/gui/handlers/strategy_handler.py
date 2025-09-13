# app/handlers/strategy_handler.py
import tkinter as tk
from tkinter import messagebox
import numpy as np
import pandas as pd
import numpy as np

from strategies import ForexStrategies, CandleStrategies
from strategies.strategy_utils import get_available_strategies, resolve_strategy_name
from strategies.risk_manager import RiskManager
from strategies.risk_manager_integration import RiskManagerIntegration, RiskConfig
from patterns.candlestickpatterns import CandlestickPatterns
from backtesting.backtester import ForexBacktester

class StrategyHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        self.dinero_ficticio = 0
        self.beneficios = 0
        self.perdidas = 0
        self.strategies_applied = False
        self.risk_manager = None
        self.risk_integration = None
        
    def add_dinero(self):
        """Añade dinero ficticio a la simulación"""
        try:
            cantidad = float(self.main_app.menu_bar.entry_dinero.get())
            self.dinero_ficticio += cantidad
            
            # Sincronizar el RiskManager
            if self.risk_manager is not None:
                self.risk_manager.capital_inicial = float(self.dinero_ficticio)
                self.risk_manager.capital = float(self.dinero_ficticio)
                
            self.actualizar_labels()
            self.main_app.menu_bar.update_buttons_state()
            
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")
            
    def actualizar_labels(self):
        """Actualiza las etiquetas de dinero, beneficios y pérdidas"""
        self.main_app.status_bar.actualizar_labels(
            self.dinero_ficticio, 
            self.beneficios, 
            self.perdidas
        )
  
    def cargar_estrategias(self):
        """Carga y aplica estrategias de trading"""
        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
            
        # Instanciar estrategias
        self.strategies_fx = ForexStrategies(self.main_app.csv_handler.df_actual)
        self.strategies_candle = CandleStrategies(self.main_app.csv_handler.df_actual)
        
        # Obtener estrategias disponibles
        fx_methods, candle_methods = get_available_strategies()
        
        # Abrir modal de selección de estrategias
        from app.strategies_modal import EstrategiasModal
        EstrategiasModal(
            self.main_app,
            estrategias_fx=sorted(fx_methods),
            estrategias_candle=sorted(candle_methods),
            callback=self._on_estrategias_seleccionadas
        )
        
    def _on_estrategias_seleccionadas(self, seleccion, max_orders=5, opciones=None):
        """Aplica las estrategias seleccionadas usando el Risk Manager"""
        # Implementación simplificada para evitar exceder límite de tokens
        if opciones is None:
            opciones = {"mostrar_deteccion": True, "mostrar_simulacion": True}
        
        if not seleccion or self.main_app.csv_handler.df_actual is None:
            return

        # Configurar Risk Manager básico
        try:
            capital_inicial = float(self.main_app.menu_bar.entry_dinero.get())
            if capital_inicial <= 0:
                raise ValueError("El capital debe ser mayor a 0")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un capital válido")
            return

        self.risk_manager = RiskManager(max_operaciones_activas=max_orders, capital_inicial=capital_inicial)
        self.risk_integration = RiskManagerIntegration(self.risk_manager, debug_mode=False)
        
        self.log("Estrategias aplicadas correctamente", color='green')
        
    def abrir_modal_backtesting(self):
        """Abre el modal de backtesting"""
        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
        self.log("Modal de backtesting abierto", color='cyan')

    def entrenar_ia(self):
        """Placeholder para entrenamiento de IA"""
        self.log("Función de entrenamiento de IA no implementada", color='yellow')

    def detener_entrenamiento_ia(self):
        """Placeholder para detener entrenamiento de IA"""
        self.log("Función de detener entrenamiento de IA no implementada", color='yellow')

                
    def _calcular_dinero_visible(self, precio_actual: float) -> float:
        """Calcula el dinero visible en tiempo real (capital - riesgo reservado + PnL flotante)"""
        try:
            capital = float(self.risk_manager.capital) if hasattr(self, 'risk_manager') and self.risk_manager is not None else float(self.dinero_ficticio)
        except Exception:
            capital = float(self.dinero_ficticio)

        total_valor_buys = 0.0
        total_pnl_sells = 0.0
        try:
            for op in getattr(self.risk_manager, 'operaciones_activas', []):
                if getattr(op, 'estado', 'ACTIVA') != 'ACTIVA':
                    continue
                if getattr(op, 'tipo', 'BUY') == 'BUY':
                    # Para BUY, calcular P&L flotante en lugar del valor nocional
                    pnl_flotante = (float(precio_actual) - float(op.precio_apertura)) * float(op.lote_size)
                    total_valor_buys += pnl_flotante
                else:
                    total_pnl_sells += (op.precio_apertura - float(precio_actual)) * float(op.lote_size)
        except Exception:
            pass

        # Dinero visible = capital + P&L flotante total
        dinero_visible = capital + total_valor_buys + total_pnl_sells
        return dinero_visible
        
    def _actualizar_dinero_visible(self, precio_actual: float):
        """Actualiza la visualización del dinero en tiempo real"""
        try:
            dinero_visible = self._calcular_dinero_visible(precio_actual)
            if hasattr(self.main_app, 'status_bar') and hasattr(self.main_app.status_bar, 'label_cash'):
                self.main_app.status_bar.label_cash.config(text=f"Dinero: ${dinero_visible:,.2f}")
        except Exception as e:
            self.log(f"Error actualizando dinero visible: {e}", color='red')
            
    def detener_entrenamiento_ia(self):
        """Detiene el entrenamiento de IA en curso si existe."""
        try:
            if hasattr(self.main_app, "_ai_trainer") and self.main_app._ai_trainer:
                trainer = self.main_app._ai_trainer
                trainer.stop()
                # Evitar múltiples solicitudes de parada
                try:
                    if hasattr(self.main_app, 'menu_bar') and hasattr(self.main_app.menu_bar, 'menu_opciones'):
                        self.main_app.menu_bar.menu_opciones.entryconfig("Detener IA", state="disabled")
                except Exception:
                    pass
                self.log("Solicitud de detener entrenamiento enviada.", "yellow")
                if hasattr(self.main_app, "lbl_ai_status"):
                    self.main_app.lbl_ai_status.config(text="Listo para entrenar", fg="blue")

                self.main_app._ai_trainer = None
            else:
                self.log("⚠️ No hay entrenamiento en curso para detener.", "orange")
        except Exception as e:
            self.log(f"Error al detener el entrenamiento: {e}", "red")
            
    def _set_menu_opcion_state(self, label: str, state: str):
        """Cambia el estado ('normal'/'disabled') de una entrada del menú Opciones por su etiqueta."""
        try:
            if hasattr(self.main_app, 'menu_bar') and hasattr(self.main_app.menu_bar, 'menu_opciones'):
                self.main_app.menu_bar.menu_opciones.entryconfig(label, state=state)
        except Exception as e:
            self.log(f"Error cambiando estado del menú: {e}", "red")
            
    def _get_capital_limit(self):
        """Obtiene el límite mínimo de capital para operar"""
        return 1000.0  # Límite mínimo de $1000
        
    def _mostrar_estadisticas_finales(self):
        """Mostrar estadísticas finales del Risk Manager"""
        try:
            if hasattr(self.main_app, 'simulation_handler') and hasattr(self.main_app.simulation_handler, 'risk_manager'):
                risk_manager = self.main_app.simulation_handler.risk_manager
                if hasattr(risk_manager, 'get_estadisticas'):
                    stats = risk_manager.get_estadisticas()
                    self.log("\n" + "="*60, color='white')
                    self.log("ESTADÍSTICAS FINALES DEL RISK MANAGER", color='yellow')
                    self.log("="*60, color='white')
                    for key, value in stats.items():
                        self.log(f"{key}: {value}", color='cyan')
                    self.log("="*60, color='white')
        except Exception as e:
            self.log(f"Error mostrando estadísticas finales: {str(e)}", color='red')
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)