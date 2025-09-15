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
                
            self.actualizar_labels(silent=True)
            self.main_app.menu_bar.update_buttons_state()
            
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido")
            
    def actualizar_labels(self, silent=False):
        """Actualiza las etiquetas de dinero, beneficios y pérdidas"""
        # Solo actualizar GUI, sin logging adicional
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
        
        try:
            from app.backtesting_modal import BacktestingModal
            BacktestingModal(self.main_app.root, self.main_app.csv_handler.df_actual, self.main_app)
        except ImportError:
            # Si no existe el modal, crear una funcionalidad básica de backtesting
            self._ejecutar_backtesting_basico()
            
    def _ejecutar_backtesting_basico(self):
        """Ejecuta un backtesting básico usando ForexBacktester"""
        try:
            from backtesting.backtester import ForexBacktester
            
            # Obtener capital inicial del strategy handler
            capital_inicial = self.dinero_ficticio if self.dinero_ficticio > 0 else 1000
            
            # Crear instancia del backtester
            backtester = ForexBacktester(self.main_app.csv_handler.df_actual, capital_inicial)
            
            self.log(f"Iniciando backtesting con capital inicial: ${capital_inicial:,.2f}", color='cyan')
            
            # Ejecutar comparación de estrategias
            results = backtester.compare_strategies()
            
            if results:
                self.log(f"Backtesting completado:", color='green')
                
                # Mostrar resultados de cada estrategia
                total_strategies = len(results)
                best_strategy = max(results, key=results.get)
                worst_strategy = min(results, key=results.get)
                
                for strategy_name, balance in results.items():
                    pnl = balance - capital_inicial
                    rendimiento = ((balance - capital_inicial) / capital_inicial) * 100
                    color = 'green' if pnl >= 0 else 'red'
                    self.log(f"  - {strategy_name}: ${balance:,.2f} ({rendimiento:+.2f}%)", color=color)
                
                # Mostrar mejor y peor estrategia
                self.log(f"  - Mejor estrategia: {best_strategy}", color='green')
                self.log(f"  - Peor estrategia: {worst_strategy}", color='red')
                
                # Usar la mejor estrategia para el resumen final
                balance_final = results[best_strategy]
                pnl_total = balance_final - capital_inicial
                
                # Separar beneficios y pérdidas
                if pnl_total >= 0:
                    beneficios_totales = pnl_total
                    perdidas_totales = 0.0
                else:
                    beneficios_totales = 0.0
                    perdidas_totales = abs(pnl_total)
                
                # Mostrar resumen final
                self.log("\n" + "="*60, color='white')
                self.log("RESUMEN FINAL DEL BACKTESTING", color='yellow')
                self.log("="*60, color='white')
                self.log(f"Dinero total: ${balance_final:,.2f}", color='white')
                self.log(f"Beneficios totales: ${beneficios_totales:,.2f}", color='green')
                self.log(f"Pérdidas totales: ${perdidas_totales:,.2f}", color='red')
                self.log("="*60, color='white')
            else:
                self.log("No se generaron resultados en el backtesting", color='yellow')
                
        except Exception as e:
            self.log(f"Error en backtesting: {str(e)}", color='red')
            
    def entrenar_ia(self):
        """Muestra el modal de entrenamiento de IA"""
        import os
        import time
        from datetime import datetime
        
        def on_accept(
            seleccion_fx=None,
            seleccion_patterns=None,
            seleccion_candle=None,
            max_orders=5,
            use_winrate=False,
            winrate=0.0,
            selected_model_path=None,
            save_best=True,
            timesteps_per_attempt=3000,
        ):
            """Recibe selecciones del modal e inicia el entrenador en hilo de fondo."""
            seleccion_fx = seleccion_fx or {}
            seleccion_patterns = seleccion_patterns or []
            seleccion_candle = seleccion_candle or []

            # Preparar archivo de log por sesión
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                logs_dir = os.path.join(project_root, 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self._training_log_path = os.path.join(logs_dir, f'log_{timestamp}.txt')
            except Exception:
                self._training_log_path = None

            def _file_log(line: str):
                try:
                    if not getattr(self, '_training_log_path', None):
                        return
                    ts = datetime.now().strftime('%H:%M:%S')
                    with open(self._training_log_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{ts}] {line}\n")
                except Exception:
                    pass

            # Obtener capital del dinero ficticio
            try:
                capital_inicial = self.dinero_ficticio if self.dinero_ficticio > 0 else 1000
                if capital_inicial <= 0:
                    raise ValueError("El capital debe ser mayor a 0")
            except Exception:
                messagebox.showerror("Entrenamiento IA", "Debe tener dinero ficticio cargado para entrenar")
                return

            # Callbacks seguros para UI
            def ui_log(msg: str, color: str = 'white'):
                try:
                    text = str(msg)
                    self.log(text, color)
                    _file_log(text)
                except Exception:
                    pass

            def ui_finish(stats: dict):
                try:
                    err = stats.get('error')
                    if err:
                        ui_log(f"Entrenamiento detenido: {err}", 'red')
                        return
                except Exception:
                    pass

                try:
                    capital_final = float(stats.get('capital_final', self.dinero_ficticio))
                    beneficio_total = float(stats.get('beneficio_total', 0.0))
                    dinero_ganado = float(stats.get('dinero_ganado', 0.0))
                    dinero_perdido = float(stats.get('dinero_perdido', 0.0))
                    self.dinero_ficticio = capital_final
                    self.beneficios = max(0.0, dinero_ganado)
                    self.perdidas = abs(dinero_perdido)
                    self.actualizar_labels()
                except Exception:
                    pass

                try:
                    ops_g = int(stats.get('operaciones_ganadas', 0))
                    ops_p = int(stats.get('operaciones_perdidas', 0))
                    ops_a = int(stats.get('operaciones_activas', 0))
                    max_ops = int(stats.get('max_operaciones', 0))
                    winrate = float(stats.get('winrate', 0.0))
                    ui_log("="*60, 'white')
                    ui_log("RESUMEN ENTRENAMIENTO IA", 'yellow')
                    ui_log(f"Capital final: ${capital_final:,.2f}", 'cyan')
                    ui_log(f"Beneficio total: ${beneficio_total:,.2f}", 'cyan')
                    ui_log(f"Operaciones ganadas: {ops_g}", 'green')
                    ui_log(f"Operaciones perdidas: {ops_p}", 'red')
                    ui_log(f"Dinero ganado en operaciones ganadoras: ${float(stats.get('dinero_ganado', 0.0)):,.2f}", 'green')
                    ui_log(f"Dinero perdido en operaciones perdedoras: -${abs(float(stats.get('dinero_perdido', 0.0))):,.2f}", 'red')
                    ui_log(f"Win Rate: {winrate:.1f}%", 'white')
                    ui_log(f"Slots usados: {ops_a}/{max_ops}", 'blue')
                    ui_log("="*60, 'white')
                except Exception:
                    pass

                try:
                    # Aviso visual al finalizar entrenamiento IA
                    messagebox.showinfo("IA", "Entrenamiento IA completado y modelo guardado")
                except Exception:
                    pass

            # Preparar agente RL
            try:
                from rl.rl_agent import RLTradingAgent
                from app.ai_trainer import AITrainer
                
                if not hasattr(self.main_app, 'rl_agent') or self.main_app.rl_agent is None:
                    self.main_app.rl_agent = RLTradingAgent(
                        self.main_app.csv_handler.df_actual,
                        estrategias_fx=seleccion_fx,
                        estrategias_candle=seleccion_candle,
                        patrones=seleccion_patterns,
                        log_fn=lambda m: ui_log(m, 'cyan')
                    )
            except Exception as e:
                ui_log(f"No se pudo preparar el agente RL: {e}", 'red')
                return

            # Iniciar entrenador
            try:
                trainer = AITrainer(
                    df=self.main_app.csv_handler.df_actual,
                    seleccion_fx=seleccion_fx,
                    seleccion_patterns=seleccion_patterns,
                    seleccion_candle=seleccion_candle,
                    max_orders=max_orders,
                    capital_inicial=capital_inicial,
                    use_winrate=use_winrate,
                    winrate_target=winrate,
                    save_best=save_best,
                    timesteps_per_attempt=timesteps_per_attempt,
                    on_log=ui_log,
                    on_finish=ui_finish,
                )
                
                self.main_app._ai_trainer = trainer

                # Habilitar opción "Detener IA" y deshabilitar "Entrenar IA" durante el entrenamiento
                self._set_menu_opcion_state("Detener IA", "normal")
                self._set_menu_opcion_state("Entrenar IA", "disabled")

                # Escribir cabecera de sesión
                ui_log("="*60, 'white')
                ui_log("INICIO SESIÓN ENTRENAMIENTO IA", 'yellow')
                ui_log(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'white')
                ui_log(f"Max órdenes: {max_orders}", 'white')
                stop_desc = f"WinRate objetivo: {winrate:.1f}%" if use_winrate else "Sin condición explícita"
                ui_log(f"Parada: {stop_desc}", 'white')
                
                if selected_model_path:
                    ui_log(f"Modelo RL: {selected_model_path}", 'white')
                if seleccion_fx:
                    ui_log(f"Estrategias FX: {', '.join(seleccion_fx.keys())}", 'white')
                if seleccion_candle:
                    ui_log(f"Estrategias Candle: {', '.join(seleccion_candle)}", 'white')
                if seleccion_patterns:
                    ui_log(f"Patrones: {', '.join(seleccion_patterns)}", 'white')
                ui_log("="*60, 'white')
                
                trainer.start()
                
            except Exception as e:
                ui_log(f"Error iniciando entrenador: {e}", 'red')
                return

        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Datos requeridos", "Por favor, carga los datos primero.")
            return

        try:
            from app.ai_training_modal import AITrainingModal
            modal = AITrainingModal(self.main_app.root, on_accept_callback=on_accept)
            modal.show()
        except ImportError:
            self.log("Modal de entrenamiento IA no disponible", 'yellow')
            # Ejecutar con configuración básica
            on_accept()

                
    def _calcular_dinero_visible(self, precio_actual: float) -> float:
        """Calcula el dinero visible en tiempo real (capital - riesgo reservado + PnL flotante)"""
        try:
            capital = float(self.risk_manager.capital) if hasattr(self, 'risk_manager') and self.risk_manager is not None else float(self.dinero_ficticio)
        except Exception:
            capital = float(self.dinero_ficticio)

        total_pnl_flotante = 0.0
        try:
            for op in getattr(self.risk_manager, 'operaciones_activas', []):
                if getattr(op, 'estado', 'ACTIVA') != 'ACTIVA':
                    continue
                if getattr(op, 'tipo', 'BUY') == 'BUY':
                    # Para BUY: P&L flotante = (precio_actual - precio_entrada) * lote_size
                    pnl_flotante = (float(precio_actual) - float(op.precio_apertura)) * float(op.lote_size)
                    total_pnl_flotante += pnl_flotante
                else:
                    # Para SELL: P&L flotante = (precio_entrada - precio_actual) * lote_size
                    pnl_flotante = (float(op.precio_apertura) - float(precio_actual)) * float(op.lote_size)
                    total_pnl_flotante += pnl_flotante
        except Exception:
            pass

        # EQUIDAD = capital + P&L flotante total
        equidad_total = capital + total_pnl_flotante
        return equidad_total
        
    def _actualizar_dinero_visible(self, precio_actual: float):
        """Actualiza la visualización del dinero y equidad por separado"""
        try:
            # Calcular valores separados
            capital_disponible = float(self.risk_manager.capital) if hasattr(self, 'risk_manager') and self.risk_manager is not None else float(self.dinero_ficticio)
            equidad_total = self._calcular_dinero_visible(precio_actual)
            
            # Actualizar usando el nuevo sistema separado
            if hasattr(self.main_app, 'status_bar') and hasattr(self.main_app.status_bar, 'actualizar_dinero_visible'):
                self.main_app.status_bar.actualizar_dinero_visible(equidad_total, capital_disponible)
            else:
                # Fallback para compatibilidad
                if hasattr(self.main_app, 'status_bar') and hasattr(self.main_app.status_bar, 'label_cash'):
                    self.main_app.status_bar.label_cash.config(text=f"Dinero: ${capital_disponible:,.2f}")
        except Exception as e:
            self.log(f"Error actualizando dinero visible: {e}", color='red')
            
    def detener_entrenamiento_ia(self):
        """Detiene el entrenamiento de IA en curso si existe."""
        try:
            if hasattr(self.main_app, "_ai_trainer") and self.main_app._ai_trainer:
                trainer = self.main_app._ai_trainer
                trainer.stop()
                # Evitar múltiples solicitudes de parada
                self._set_menu_opcion_state("Detener IA", "disabled")
                self._set_menu_opcion_state("Entrenar IA", "normal")
                
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