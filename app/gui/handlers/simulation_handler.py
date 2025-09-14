# app/handlers/simulation_handler.py
import tkinter as tk
from tkinter import messagebox
import threading
import time
import pandas as pd
import os
import json
from trading_view.candle_streamer import CandleStreamer
from strategies.risk_manager import RiskManager
from strategies.risk_manager_integration import RiskManagerIntegration, RiskConfig
from strategies.candle_strategies import CandleStrategies
from strategies.market_strategy_mapper import MarketStrategyMapper
from strategies.strategies import ForexStrategies

class SimulationHandler:
    _current_instance = None
    def __init__(self, main_app):
        self.main_app = main_app
        self.candle_streamer = None
        # Establecer instancia actual para logs de cierre
        SimulationHandler._current_instance = self
        
    def iniciar_streamer(self):
        """Muestra el modal de configuración y luego inicia el CandleStreamer"""
        try:
            if self.candle_streamer is not None:
                self.log("El streamer ya está en ejecución", color="orange")
                return

            # Obtener símbolos disponibles sin inicializar el streamer completo
            from trading_view.candle_streamer import CandleStreamer
            symbols = CandleStreamer._load_or_fetch_symbols()

            if not symbols:
                self.log("No se pudieron cargar los símbolos disponibles", color="red")
                return

            # Mostrar el modal de configuración
            from trading_view.config_modal import CandleStreamerConfigModal

            def on_connect(config):
                # Sincronizar capital desde el modal si viene informado
                try:
                    if "initial_money" in config:
                        initial_money = float(config["initial_money"])
                        # Arquitectura modular: usar StrategyHandler si existe
                        if hasattr(self.main_app, 'strategy_handler') and self.main_app.strategy_handler is not None:
                            sh = self.main_app.strategy_handler
                            try:
                                sh.dinero_ficticio = initial_money
                                if hasattr(sh, 'risk_manager') and sh.risk_manager is not None:
                                    sh.risk_manager.capital_inicial = initial_money
                                    sh.risk_manager.capital = initial_money
                                # Refrescar labels
                                if hasattr(sh, 'actualizar_labels'):
                                    sh.actualizar_labels()
                            except Exception:
                                pass
                        else:
                            # Fallback retrocompatible
                            if hasattr(self.main_app, 'dinero_ficticio'):
                                self.main_app.dinero_ficticio = initial_money
                            if hasattr(self.main_app, 'risk_manager') and self.main_app.risk_manager is not None:
                                self.main_app.risk_manager.capital_inicial = initial_money
                                self.main_app.risk_manager.capital = initial_money
                            if hasattr(self.main_app, 'status_bar'):
                                try:
                                    self.main_app.status_bar.actualizar_labels(dinero_ficticio=initial_money)
                                except Exception:
                                    pass
                except Exception:
                    pass
                # Iniciar streamer con nueva configuración
                self._start_streamer_with_config(config)

            # Crear y mostrar el modal
            CandleStreamerConfigModal(
                parent=self.main_app.root if hasattr(self.main_app, 'root') else None,
                symbols=symbols,
                on_connect=on_connect
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar el streamer: {e}")
            self.log(f"Error al iniciar el streamer: {e}", color="red")

    def _start_streamer_with_config(self, config):
        """Inicia el streamer con configuración específica"""
        try:
            # Limpiar el frame del gráfico actual
            grafico_frame = None
            if hasattr(self.main_app, 'frame_grafico'):
                grafico_frame = self.main_app.frame_grafico
                for widget in grafico_frame.winfo_children():
                    widget.destroy()
            
            # Crear un frame para el gráfico del streamer
            import tkinter as tk
            chart_frame = tk.Frame(grafico_frame, bg='#FFFFFF')
            chart_frame.pack(fill='both', expand=True, padx=1, pady=1)
            
            if self.candle_streamer is not None:
                self.candle_streamer.stop()
                self.candle_streamer = None
            
            # Crear el streamer con el frame del gráfico y la función de log
            from trading_view.candle_streamer import CandleStreamer
            self.candle_streamer = CandleStreamer(
                interval=config["interval"],
                max_plot=config["max_plot"],
                parent_frame=chart_frame,  # Pasar el frame para el gráfico
                log_callback=self.log,
                visible_candles=config.get("visible_candles", 5)
            )
            
            # Configurar el símbolo si se proporciona
            if "symbol" in config and config["symbol"]:
                self.candle_streamer.symbol = config["symbol"]
                import os
                self.candle_streamer.csv_file = os.path.join(self.candle_streamer.csv_folder, f'{self.candle_streamer.symbol}_data.csv')
            
            # Configurar modo simulación CSV con velas iniciales
            visible_candles = config.get("visible_candles", 5)
            self.candle_streamer.visible_candles = visible_candles
            
            # Configurar auto-desconexión si está habilitada
            if config.get("auto_disconnect_after_candles", False):
                target_candles = config.get("target_candles", 500)
                self.candle_streamer.configure_auto_disconnect(True, target_candles)
            
            # Iniciar simulación CSV progresiva en lugar de streaming WebSocket
            def start_csv_simulation():
                try:
                    # Obtener velas iniciales desde la configuración del modal
                    visible_candles = getattr(self.candle_streamer, 'visible_candles', 20)
                    self.log(f"📊 Iniciando simulación CSV con {visible_candles} velas iniciales", color="blue")
                    
                    # Iniciar simulación CSV con procesamiento secuencial
                    self.candle_streamer.start_csv_simulation(visible_candles=visible_candles)
                except Exception as e:
                    self.log(f"Error en simulación CSV: {str(e)}", color="red")
            
            # Iniciar el streamer en un hilo para no bloquear la interfaz
            import threading
            streamer_thread = threading.Thread(target=start_csv_simulation, daemon=True)
            streamer_thread.start()
            
            # Inicializar el analizador de mercado si no existe
            try:
                if not hasattr(self, '_market_analyzer') or self._market_analyzer is None:
                    from ia.smart_order_analyzer import ForexMarketAnalyzer
                    self._market_analyzer = ForexMarketAnalyzer()
            except Exception:
                # No bloquear si hay problemas cargando dependencias
                self._market_analyzer = None
            
            self.log("CandleStreamer conectado correctamente", color="green")
            self.log(f"Símbolo: {self.candle_streamer.symbol} | Intervalo: {self.candle_streamer.interval} | Máx. velas: {self.candle_streamer.max_plot}", color="white")
            
            # Actualizar estados del menú si existe
            if hasattr(self.main_app, 'menu_bar') and hasattr(self.main_app.menu_bar, 'menu_streamer'):
                try:
                    menu_streamer = self.main_app.menu_bar.menu_streamer
                    menu_streamer.entryconfig("Conectar", state="disabled")
                    menu_streamer.entryconfig("Desconectar", state="normal")
                    menu_streamer.entryconfig("Cambiar símbolo/intervalo", state="normal")
                    menu_streamer.entryconfig("Iniciar simulación Binance", state="normal")
                    if hasattr(self, 'debug_mode') and self.debug_mode:
                        menu_streamer.entryconfig("Activar Debug", state="disabled")
                        menu_streamer.entryconfig("Desactivar Debug", state="normal")
                    else:
                        menu_streamer.entryconfig("Activar Debug", state="normal")
                        menu_streamer.entryconfig("Desactivar Debug", state="disabled")
                except Exception:
                    pass  # Ignorar si no existen las entradas del menú
                
            # Actualizar estado visual del streamer
            if hasattr(self.main_app, 'status_bar'):
                self.main_app.status_bar.actualizar_estado_streamer(conectado=True)
            
        except Exception as e:
            self.log(f"Error al iniciar CandleStreamer: {str(e)}", color="red")
            import traceback
            self.log(traceback.format_exc(), color="red")
            
    def detener_streamer(self):
        """Detiene el CandleStreamer"""
        if self.candle_streamer:
            try:
                self.candle_streamer.stop()
                self.candle_streamer = None
                self.log("CandleStreamer detenido", color='red')
                
                # Actualizar estados del menú
                if hasattr(self.main_app, 'menu_bar') and hasattr(self.main_app.menu_bar, 'menu_streamer'):
                    try:
                        menu_streamer = self.main_app.menu_bar.menu_streamer
                        menu_streamer.entryconfig("Conectar", state="normal")
                        menu_streamer.entryconfig("Desconectar", state="disabled")
                        menu_streamer.entryconfig("Cambiar símbolo/intervalo", state="disabled")
                        menu_streamer.entryconfig("Iniciar simulación Binance", state="disabled")
                        menu_streamer.entryconfig("Activar Debug", state="disabled")
                        menu_streamer.entryconfig("Desactivar Debug", state="disabled")
                    except Exception:
                        pass
                        
                # Actualizar estado visual del streamer
                if hasattr(self.main_app, 'status_bar'):
                    self.main_app.status_bar.actualizar_estado_streamer(conectado=False)
                    
            except Exception as e:
                self.log(f"Error deteniendo streamer: {e}", color='red')
                
    def cambiar_config_streamer(self):
        """Abre el modal para cambiar símbolo/intervalo y reinicia el streamer con la nueva configuración."""
        try:
            # Cargar símbolos disponibles
            from trading_view.candle_streamer import CandleStreamer
            symbols = CandleStreamer._load_or_fetch_symbols()
            if not symbols:
                self.log("No se pudieron cargar los símbolos disponibles", color="red")
                return

            # Valores iniciales desde el streamer actual si existe
            initial = {}
            if self.candle_streamer is not None:
                try:
                    initial = {
                        "interval": getattr(self.candle_streamer, "interval", "1m"),
                        "max_plot": int(getattr(self.candle_streamer, "max_plot", 500)),
                        "symbol": getattr(self.candle_streamer, "symbol", "")
                    }
                except Exception:
                    initial = {}

            from trading_view.config_modal import CandleStreamerConfigModal

            def on_connect(config):
                # Sincronizar capital desde el modal si viene informado
                try:
                    if "initial_money" in config:
                        initial_money = float(config["initial_money"])
                        if hasattr(self.main_app, 'strategy_handler') and self.main_app.strategy_handler is not None:
                            sh = self.main_app.strategy_handler
                            try:
                                sh.dinero_ficticio = initial_money
                                if hasattr(sh, 'risk_manager') and sh.risk_manager is not None:
                                    sh.risk_manager.capital_inicial = initial_money
                                    sh.risk_manager.capital = initial_money
                                if hasattr(sh, 'actualizar_labels'):
                                    sh.actualizar_labels()
                            except Exception:
                                pass
                        else:
                            # Fallback retrocompatible
                            if hasattr(self.main_app, 'dinero_ficticio'):
                                self.main_app.dinero_ficticio = initial_money
                            if hasattr(self.main_app, 'risk_manager') and self.main_app.risk_manager is not None:
                                self.main_app.risk_manager.capital_inicial = initial_money
                                self.main_app.risk_manager.capital = initial_money
                            if hasattr(self.main_app, 'status_bar'):
                                try:
                                    self.main_app.status_bar.actualizar_dinero_ficticio(initial_money)
                                except Exception:
                                    pass
                except Exception:
                    pass
                # Reiniciar con nueva configuración (internamente limpia el gráfico y detiene si está corriendo)
                self._start_streamer_with_config(config)

            CandleStreamerConfigModal(
                parent=self.main_app.root,
                symbols=symbols,
                on_connect=on_connect,
                initial_values=initial
            )
        except Exception as e:
            self.log(f"Error al cambiar la configuración del streamer: {str(e)}", color="red")
            import traceback
            self.log(traceback.format_exc(), color="red")
        
    def iniciar_simulacion_binance(self):
        """Inicia simulación con Binance"""
        print("Iniciando simulación Binance")
        try:
            # Get available strategies
            import sys
            import os
            # Add the project root to the Python path
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.append(project_root)
                
            from strategies import get_available_strategies
            from patterns import get_available_patterns
            
            # Get available strategies and patterns
            estrategias_fx, estrategias_candle = get_available_strategies()
            patrones_list = get_available_patterns()
            
            # Create and show the simulation modal
            from app.binance_modal import BinanceSimulationModal
            
            def on_simulation_config(config):
                # Store the simulation configuration
                self.simulation_config = config
                self.simulation_active = True
                self.simulation_candles_elapsed = 0
                self.active_orders = []
                self._sim_started_logged = False  # flag to log start once when wait reaches 0
                self.candle_count_for_market_analysis = 0  # contador para análisis de mercado cada 5 velas
                self.current_market_scenario = None  # escenario actual del mercado
                
                # Inicializar Risk Manager e Integration (T03)
                try:
                    # Obtener capital inicial desde StrategyHandler si existe; si no, fallback
                    initial_capital = None
                    if hasattr(self.main_app, 'strategy_handler') and hasattr(self.main_app.strategy_handler, 'dinero_ficticio'):
                        initial_capital = float(self.main_app.strategy_handler.dinero_ficticio)
                    else:
                        initial_capital = float(config.get('capital', 1000.0))

                    max_orders = int(config.get('max_orders', 5))
                    
                    # Config FORZADO para operaciones SHORT/LONG
                    rm_cfg = RiskConfig()
                    rm_cfg.enable_sell_operations = True  # SIEMPRE habilitado
                    rm_cfg.force_open_operations = True   # FORZAR apertura
                    rm_cfg.default_risk_percent = 0.02    # 2% riesgo por operación
                    self.risk_manager = RiskManager(capital_inicial=initial_capital,
                                                    max_operaciones_activas=max_orders,
                                                    debug_mode=getattr(self, 'debug_mode', False))
                    self.risk_integration = RiskManagerIntegration(self.risk_manager, config=rm_cfg,
                                                                   debug_mode=getattr(self, 'debug_mode', False))
                    # Reset por seguridad antes de empezar
                    self.risk_manager.reset()
                    # Estado runtime adicional
                    self._last_market_analysis_time = 0.0
                    self._cooldown_open_times = {}
                    self._cooldown_exit_times = {}
                    self._audit_log_file = None
                except Exception as e:
                    self.log(f"⚠️ Error inicializando Risk Manager: {e}", color='orange')
                
                # Configurar el sistema de reports con los parámetros de la simulación
                try:
                    from app.reports import set_simulation_config
                    
                    # Obtener capital inicial real
                    try:
                        capital_inicial = float(self.risk_manager.capital_inicial) if hasattr(self, 'risk_manager') and self.risk_manager else float(config.get('capital', 1000.0))
                    except Exception:
                        capital_inicial = float(config.get('capital', 1000.0))
                    
                    # Obtener estrategias seleccionadas
                    estrategias_seleccionadas = []
                    if config.get('forex_strategies'):
                        estrategias_seleccionadas.extend(config['forex_strategies'])
                    if config.get('candle_strategies'):
                        estrategias_seleccionadas.extend(config['candle_strategies'])
                    if config.get('patterns'):
                        estrategias_seleccionadas.extend([f"Patrón: {p}" for p in config['patterns']])
                    
                    # Obtener máximo de operaciones simultáneas
                    max_operaciones = int(config.get('max_orders', 5))
                    
                    # Configurar el sistema de reports
                    set_simulation_config(capital_inicial, estrategias_seleccionadas, max_operaciones)
                    
                    self.log(f"📊 Sistema de reports configurado: Capital {capital_inicial}€, {len(estrategias_seleccionadas)} estrategias", color="blue")
                    
                except Exception as e:
                    self.log(f"⚠️ Error configurando sistema de reports: {str(e)}", color="orange")
                
                # Update UI
                self.main_app.menu_bar.menu_streamer.entryconfig("Modificar configuración simulación Binance", state="normal")
                self.main_app.menu_bar.menu_streamer.entryconfig("Iniciar simulación Binance", state="disabled")
                self.main_app.menu_bar.menu_streamer.entryconfig("Detener simulación Binance", state="normal")
                wait_candles = config.get('wait_candles', 20)
                self.log(f"Simulación iniciada. Esperando {wait_candles} velas antes de operar...", color="green")
                # Actualizar estado visual (azul durante la espera)
                if hasattr(self.main_app, 'label_sim_status'):
                    try:
                        self.main_app.label_sim_status.configure(text=f"Esperando {wait_candles} velas...", fg="blue")
                    except Exception:
                        pass
                
                # If we have a candle streamer, connect to its update event
                if hasattr(self, 'candle_streamer') and self.candle_streamer:
                    if not hasattr(self, '_on_candle_update_connected'):
                        self._on_candle_update_connected = True
                        self.candle_streamer.on_candle_update(self._on_candle_update)

            # Show the modal
            BinanceSimulationModal(
                self.main_app.root,
                estrategias_fx=estrategias_fx,
                estrategias_candle=estrategias_candle,
                patrones_list=patrones_list,
                callback=on_simulation_config
            )
        
        except Exception as e:
            self.log(f"Error al iniciar la simulación: {e}", color='red')
            import traceback
            self.log(traceback.format_exc(), color='red')
        
    def modificar_config_simulacion_binance(self):
        """Muestra el modal de configuración de la simulación Binance"""
        try:
            # Validaciones básicas
            if not getattr(self, 'simulation_active', False) or not hasattr(self, 'simulation_config'):
                messagebox.showwarning(
                    "Simulación no activa",
                    "No hay una simulación Binance en ejecución. Inicie una simulación antes de modificar su configuración.")
                return

            # Obtener estrategias disponibles (mismo criterio que iniciar_simulacion_binance)
            try:
                import os, sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if project_root not in sys.path:
                    sys.path.append(project_root)
                from strategies import get_available_strategies
            except Exception:
                from strategies.strategy_utils import get_available_strategies

            estrategias_fx, estrategias_candle = get_available_strategies()

            # Importar modal de configuración
            from app.binance_modal_config import BinanceSimulationConfigModal

            def on_apply(new_config):
                try:
                    candles_elapsed = int(getattr(self, 'simulation_candles_elapsed', 0))
                    active_orders = list(getattr(self, 'active_orders', []))

                    if not hasattr(self, 'simulation_config') or self.simulation_config is None:
                        self.simulation_config = {}
                    self.simulation_config.update(new_config)
                    self.simulation_config['candles_elapsed'] = candles_elapsed
                    self.simulation_config['active_orders'] = active_orders

                    # Actualizar estado visual
                    wait_candles = int(self.simulation_config.get('wait_candles', 20))
                    remaining = max(0, wait_candles - candles_elapsed)
                    try:
                        if remaining > 0:
                            self.main_app.label_sim_status.configure(text=f"Esperando {remaining} velas...", fg="blue")
                        else:
                            self.main_app.label_sim_status.configure(text="Simulación en progreso!!", fg="blue")
                    except Exception:
                        pass

                    self.log("⚙️ Configuración de simulación actualizada.", color='blue')
                except Exception as e:
                    self.log(f"Error aplicando nueva configuración: {e}", color='red')

            # Mostrar modal poblado con la configuración actual
            BinanceSimulationConfigModal(
                parent=self.main_app.root,
                estrategias_fx=estrategias_fx,
                estrategias_candle=estrategias_candle,
                current_config=self.simulation_config,
                callback=on_apply,
            )

        except Exception as e:
            self.log(f"Error al abrir el configurador de simulación: {str(e)}", color='red')
        
    def detener_simulacion_binance(self):
        """Detiene la simulación del mercado"""
        try:
            if hasattr(self, 'simulation_active') and self.simulation_active:
                self.simulation_active = False
                self._on_candle_update_connected = False
                
                # Mostrar resumen de la simulación
                if hasattr(self, 'simulation_candles_elapsed'):
                    self.log(f"\n--- SIMULACIÓN FINALIZADA ---", color="blue")
                    self.log(f"Velas procesadas: {self.simulation_candles_elapsed}", color="white")
                    self.log(f"Órdenes abiertas al finalizar: {len(self.active_orders) if hasattr(self, 'active_orders') else 0}", 
                            color="white")
                
                # Limpiar estado de simulación
                if hasattr(self, 'active_orders'):
                    del self.active_orders
                if hasattr(self, 'simulation_candles_elapsed'):
                    del self.simulation_candles_elapsed
                if hasattr(self, 'simulation_config'):
                    del self.simulation_config
                
                # Limpiar sistema de reports para la próxima simulación
                try:
                    from app.reports import clear_all_operations
                    clear_all_operations()
                    self.log("📊 Sistema de reports limpiado", color="blue")
                except Exception as e:
                    self.log(f"⚠️ Error limpiando sistema de reports: {str(e)}", color="orange")
                
                # Actualizar UI
                # Rehabilitar inicio solo si el streamer sigue conectado
                start_state = "normal" if getattr(self, 'candle_streamer', None) is not None else "disabled"
                self.main_app.menu_bar.menu_streamer.entryconfig("Iniciar simulación Binance", state=start_state)
                self.main_app.menu_bar.menu_streamer.entryconfig("Detener simulación Binance", state="disabled")
                self.log("Simulación detenida correctamente", color="green")
                # Resetear estado visual
                if hasattr(self.main_app, 'label_sim_status'):
                    try:
                        self.main_app.label_sim_status.configure(text="Estado: Inactivo", fg="gray")
                    except Exception:
                        pass
            else:
                self.log("No hay ninguna simulación activa", color="orange")
                
        except Exception as e:
            self.log(f"Error al detener la simulación: {str(e)}", color="red")
            import traceback
            self.log(traceback.format_exc(), color="red")
        
    def toggle_debug_mode(self, enable):
        """Activa/desactiva modo debug"""
        mode = "activado" if enable else "desactivado"
        self.log(f"Modo debug {mode}", color='cyan')
        
        # Guardar estado del debug mode
        self.debug_mode = enable
        
        # Actualizar estados de los botones de debug
        try:
            if enable:
                # Debug activado: deshabilitar "Activar" y habilitar "Desactivar"
                self.main_app.menu_bar.menu_streamer.entryconfig("Activar Debug", state="disabled")
                self.main_app.menu_bar.menu_streamer.entryconfig("Desactivar Debug", state="normal")
            else:
                # Debug desactivado: habilitar "Activar" y deshabilitar "Desactivar"
                self.main_app.menu_bar.menu_streamer.entryconfig("Activar Debug", state="normal")
                self.main_app.menu_bar.menu_streamer.entryconfig("Desactivar Debug", state="disabled")
        except Exception as e:
            self.log(f"Error actualizando estados del menú debug: {str(e)}", color='orange')
        
    def generar_informe(self):
        """Genera un informe con los datos actuales"""
        try:
            from app.reports import generate_trading_report
            
            self.log("Generando informe de trading...")
            
            # Generar el informe
            report_path = generate_trading_report()
            
            if report_path:
                self.log(f"✅ Informe generado exitosamente: {report_path}", color="green")
            else:
                self.log("❌ Error al generar el informe", color="red")
                
        except Exception as e:
            self.log(f"❌ Error generando informe: {str(e)}", color="red")
            import traceback
            self.log(traceback.format_exc(), color="red")
        
    def configuracion(self):
        """Abre configuración"""
        try:
            from app.config_app_modal import ConfigAppModal
            ConfigAppModal(self.main_app.root)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir configuración: {e}")
            
    def test_iniciar_streamer(self):
        """Método de prueba para iniciar el streamer"""
        try:
            self.log("🔎 Probando conexión con CandleStreamer...", 'cyan')

            # Si ya hay un streamer activo, verificar su estado
            if getattr(self, 'candle_streamer', None) is not None:
                cs = self.candle_streamer
                connected = bool(getattr(cs, 'connection_established', False))
                if connected:
                    self.log(f"✅ Conexión activa: símbolo {cs.symbol} | intervalo {cs.interval}", 'green')
                else:
                    self.log("⚠️ Streamer activo pero sin conexión establecida aún", 'orange')
                return

            # Cargar símbolos y elegir uno válido
            symbols = CandleStreamer._load_or_fetch_symbols()
            if not symbols:
                self.log("❌ No hay símbolos disponibles para probar la conexión", 'red')
                return
            symbol = next((s for s in symbols if s and s != '----------'), symbols[0])

            # Crear streamer temporal sin interferir con el actual
            test_streamer = CandleStreamer(interval='1m', max_plot=100, parent_frame=None, log_callback=self.log, visible_candles=5)
            test_streamer.symbol = symbol

            # Iniciar en hilo de fondo
            t = threading.Thread(target=test_streamer.start, daemon=True)
            t.start()

            # Esperar hasta 8s a que marque conexión establecida
            timeout = 8.0
            start_time = time.time()
            connected = False
            while time.time() - start_time < timeout:
                if getattr(test_streamer, 'connection_established', False):
                    connected = True
                    break
                time.sleep(0.25)

            # Detener streamer de prueba
            try:
                test_streamer.stop()
            except Exception:
                pass

            # Resultado
            if connected:
                self.log(f"✅ Conexión OK con Binance WebSocket para {symbol} (intervalo 1m)", 'green')
            else:
                self.log("❌ No se pudo establecer conexión en el tiempo esperado", 'red')

        except Exception as e:
            self.log(f"❌ Error probando conexión del streamer: {e}", 'red')
            try:
                import traceback
                self.log(traceback.format_exc(), 'red')
            except Exception:
                pass
        
    def cleanup(self):
        """Limpia recursos de simulación"""
        if self.candle_streamer:
            try:
                self.candle_streamer.stop()
            except:
                pass
        
    def simular_estrategias_velas(self, selected_strategies, max_operations, progress_callback=None):
        """
        Simula operaciones de compra y venta usando estrategias de velas seleccionadas
        Optimizado para datos fijos con pre-cálculo de estrategias
        """
        try:
            from strategies.candle_strategies import CandleStrategies
            from strategies.risk_manager import RiskManager
            from strategies.risk_manager_integration import RiskManagerIntegration
            
            # Verificar capital inicial (configurable)
            capital_limit = RiskManager()._get_capital_limit()
            if self.main_app.strategy_handler.dinero_ficticio <= capital_limit:
                self.log(f"OPERACIÓN SALTADA: Capital insuficiente (mínimo ${capital_limit:,.2f})", color='yellow')
                if progress_callback:
                    progress_callback(100, "Simulación completada - Capital insuficiente")
                return

            # Configurar Risk Manager
            capital_inicial = float(self.main_app.strategy_handler.dinero_ficticio)
            self.risk_manager = RiskManager(capital_inicial=capital_inicial, max_operaciones_activas=max_operations)
            self.risk_integration = RiskManagerIntegration(self.risk_manager, debug_mode=False)
            self.risk_manager.reset()

            # Log inicio de simulación
            self.log("============================================================", color='cyan')
            self.log("INICIANDO SIMULACIÓN OPTIMIZADA DE ESTRATEGIAS DE VELAS", color='cyan')
            self.log("============================================================", color='cyan')
            self.log(f"Capital inicial: ${capital_inicial:,.2f}", color='white')
            self.log(f"Estrategias seleccionadas: {len(selected_strategies)}", color='white')
            self.log(f"Máximo de operaciones simultáneas: {max_operations}", color='white')

            # OPTIMIZACIÓN: Pre-calcular todas las estrategias una sola vez
            if progress_callback:
                progress_callback(10, "Pre-calculando estrategias...")
            
            strategy_signals = {}
            candle_strategies = CandleStrategies(self.main_app.csv_handler.df_actual)
            
            for i, strategy_name in enumerate(selected_strategies):
                try:
                    strategy_method = getattr(candle_strategies, strategy_name, None)
                    if strategy_method and callable(strategy_method):
                        # Ejecutar estrategia completa una sola vez
                        df_result = strategy_method()
                        if 'ExecSignal' in df_result.columns:
                            strategy_signals[strategy_name] = df_result['ExecSignal'].fillna(0)
                        
                        # Actualizar progreso del pre-cálculo
                        pre_progress = 10 + (i + 1) / len(selected_strategies) * 20
                        if progress_callback:
                            progress_callback(pre_progress, f"Pre-calculando {strategy_name}...")
                            
                except Exception as e:
                    self.log(f"Error pre-calculando {strategy_name}: {str(e)}", color='red')
                    continue
                    
            self.log("Pre-cálculo de estrategias completado", color='green')
            
        except Exception as e:
            self.log(f"Error en simulación de estrategias de velas: {str(e)}", color='red')
            
    def _mostrar_estadisticas_finales(self, balance_inicial, balance_final, beneficios_totales, perdidas_totales):
        """Muestra las estadísticas finales de la simulación"""
        # Actualizar la interfaz con los totales
        self.main_app.strategy_handler.dinero_ficticio = balance_final
        self.main_app.strategy_handler.beneficios = beneficios_totales
        self.main_app.strategy_handler.perdidas = perdidas_totales
        self.main_app.strategy_handler.actualizar_labels()
        
        # Mostrar resumen final
        self.log("\n" + "="*60, color='white')
        self.log("RESUMEN FINAL DEL BACKTESTING", color='yellow')
        self.log("="*60, color='white')
        self.log(f"Dinero total: ${balance_final:,.2f}", color='white')
        self.log(f"Beneficios totales: ${beneficios_totales:,.2f}", color='green')
        self.log(f"Pérdidas totales: ${perdidas_totales:,.2f}", color='red')
        self.log("="*60, color='white')
        
    def _on_candle_update(self, df):
        """Maneja la actualización de velas durante la simulación"""
        if not hasattr(self, 'simulation_active') or not self.simulation_active:
            return
        
        # Evitar procesamiento concurrente
        if getattr(self, '_processing_candle', False):
            return
            
        # Procesar en hilo separado para no bloquear GUI
        try:
            if hasattr(self.main_app, 'thread_manager'):
                self.main_app.thread_manager.submit_task(self._process_candle_async, df.copy())
        except Exception as e:
            self.log(f"Error procesando actualización de vela: {str(e)}", color='red')
            
    def _process_candle_async(self, df):
        """Procesa la vela en hilo separado - NO BLOQUEA LA GUI"""
        try:
            self._processing_candle = True
            
            # Incrementar el contador de velas
            if not hasattr(self, 'simulation_candles_elapsed'):
                self.simulation_candles_elapsed = 0
            else:
                self.simulation_candles_elapsed += 1
            
            # Obtener la última vela
            last_candle = df.iloc[-1]
            
            # Análisis de mercado según configuración (segundos o velas)
            try:
                every_seconds = int(self._get_config_value('market_analysis_every_seconds', 0) or 0)
            except Exception:
                every_seconds = 0
            if every_seconds > 0:
                last_ts = getattr(self, '_last_market_analysis_time', 0.0) or 0.0
                now_ts = time.time()
                if (now_ts - last_ts) >= every_seconds:
                    self._analyze_market_type(df)
                    self._last_market_analysis_time = now_ts
            else:
                # Caer a frecuencia por número de velas
                try:
                    every_candles = int(self._get_config_value('market_analysis_every_candles', 5) or 5)
                except Exception:
                    every_candles = 5
                if not hasattr(self, 'candle_count_for_market_analysis'):
                    self.candle_count_for_market_analysis = 0
                self.candle_count_for_market_analysis += 1
                if self.candle_count_for_market_analysis >= max(1, every_candles):
                    self._analyze_market_type(df)
                    self.candle_count_for_market_analysis = 0
            
            # Debug mode: mostrar información de la vela (alcista/bajista)
            if getattr(self, 'debug_mode', False):
                open_price = float(last_candle.get('Open', 0))
                close_price = float(last_candle.get('Close', 0))
                high_price = float(last_candle.get('High', 0))
                low_price = float(last_candle.get('Low', 0))
                
                if close_price > open_price:
                    candle_type = "🟢 ALCISTA"
                    color = "green"
                elif close_price < open_price:
                    candle_type = "🔴 BAJISTA"
                    color = "red"
                else:
                    candle_type = "⚪ DOJI"
                    color = "yellow"
                
                # Calcular el tamaño del cuerpo y las sombras
                body_size = abs(close_price - open_price)
                upper_shadow = high_price - max(open_price, close_price)
                lower_shadow = min(open_price, close_price) - low_price
                
                self.log(f"DEBUG Vela #{self.simulation_candles_elapsed}: {candle_type} | O:{open_price:.5f} H:{high_price:.5f} L:{low_price:.5f} C:{close_price:.5f} | Cuerpo:{body_size:.5f} Sombra↑:{upper_shadow:.5f} Sombra↓:{lower_shadow:.5f}", color)
            
            # Log throttled (solo cada 10 velas)
            if self.simulation_candles_elapsed % 10 == 0:
                self.log(f"Simulación en progreso - Velas procesadas: {self.simulation_candles_elapsed}", "blue")
            
            # Verificar si ya pasaron las velas de espera
            wait_candles = int(self.simulation_config.get('wait_candles', 20))
            remaining = wait_candles - self.simulation_candles_elapsed
            
            if remaining > 0:
                self.log(f"Esperando {remaining} velas más antes de operar...", "blue")
                # Actualizar estado visual
                if hasattr(self.main_app, 'label_sim_status'):
                    try:
                        self.main_app.label_sim_status.configure(text=f"Esperando {remaining} velas...", fg="blue")
                    except Exception:
                        pass
                # NO hacer return aquí - continuar procesando las velas para que se vean en el gráfico
            else:
                # Justo al alcanzar 0 velas de espera
                if not getattr(self, '_sim_started_logged', False):
                    self.log("Simulación en progreso!!", "blue")
                    self._sim_started_logged = True
                    # Actualizar estado visual
                    if hasattr(self.main_app, 'label_sim_status'):
                        try:
                            self.main_app.label_sim_status.configure(text="Simulación en progreso!!", fg="blue")
                        except Exception:
                            pass
            
            # Procesar señales de compra/venta
            self._procesar_senal_compra(last_candle)

            # T04: Evaluar Candle Strategies seleccionadas y enviar a RiskManagerIntegration
            try:
                # Validaciones previas
                if hasattr(self, 'simulation_config') and self.simulation_config:
                    selected_candles = self.simulation_config.get('candle_strategies', []) or []
                else:
                    selected_candles = []

                if selected_candles and hasattr(self, 'risk_integration') and self.risk_integration:
                    # Preparar límites por tipo y simultáneos
                    max_orders_total = int(self.simulation_config.get('max_orders', 5))
                    max_candle_ops = int(self.simulation_config.get('max_candle_operations', max_orders_total))

                    def count_active_by_prefix(prefix: str) -> int:
                        try:
                            return sum(1 for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                       if getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and
                                       isinstance(getattr(op, 'estrategia', None), str) and
                                       getattr(op, 'estrategia').startswith(prefix))
                        except Exception:
                            return 0

                    # Contadores actuales
                    active_total = int(self.risk_manager.get_operaciones_activas_count()) if hasattr(self, 'risk_manager') and self.risk_manager else 0
                    active_candle = count_active_by_prefix('candle_')
                    opens_candle_this_tick = 0

                    # Preparar MarketStrategyMapper
                    mapper = MarketStrategyMapper()
                    scenario = getattr(self, 'current_market_scenario', None)

                    # Reordenar Candle por prioridad (HIGH -> LOW) para consumir slots primero en las más recomendadas
                    try:
                        def _candle_weight(item):
                            try:
                                name = item.get('name') if isinstance(item, dict) else None
                                return mapper.get_priority_weight(name, scenario) if name else 0.0
                            except Exception:
                                return 0.0
                        selected_candles.sort(key=_candle_weight, reverse=True)
                    except Exception:
                        pass

                    # Para cada estrategia seleccionada
                    for item in selected_candles:
                        try:
                            strategy_name = item.get('name') if isinstance(item, dict) else None
                            candle_cfg = item.get('config') if isinstance(item, dict) else None
                            if not strategy_name:
                                continue

                            # Respetar límites simultáneos por tipo y totales
                            if active_total >= max_orders_total:
                                if getattr(self, 'debug_mode', False):
                                    self.log(f"🚫 Límite total de órdenes alcanzado ({active_total}/{max_orders_total})", 'orange')
                                try:
                                    self._audit_log({
                                        'type': 'candle', 'event': 'skipped_slot_limit_total',
                                        'strategy': strategy_name,
                                        'active_total': active_total,
                                        'max_total': max_orders_total,
                                        'scenario': getattr(scenario, 'value', None)
                                    })
                                except Exception:
                                    pass
                                break
                            if active_candle + opens_candle_this_tick >= max_candle_ops:
                                if getattr(self, 'debug_mode', False):
                                    self.log(f"🚫 Límite de órdenes Candle alcanzado en esta vela ({active_candle + opens_candle_this_tick}/{max_candle_ops})", 'orange')
                                try:
                                    self._audit_log({
                                        'type': 'candle', 'event': 'skipped_slot_limit_type',
                                        'strategy': strategy_name,
                                        'active_type': active_candle + opens_candle_this_tick,
                                        'max_type': max_candle_ops,
                                        'scenario': getattr(scenario, 'value', None)
                                    })
                                except Exception:
                                    pass
                                continue

                            # Instanciar estrategia con config de patrones (detección)
                            cs = CandleStrategies(df, config=candle_cfg)
                            method = getattr(cs, strategy_name, None)
                            if not callable(method):
                                continue

                            result_df = method(config=candle_cfg) if 'config' in method.__code__.co_varnames else method()
                            if result_df is None or len(result_df) == 0:
                                continue

                            row = result_df.iloc[-1]
                            # Determinar señal a ejecutar
                            signal_value = 0
                            if 'ExecSignal' in result_df.columns:
                                signal_value = int(row.get('ExecSignal') or 0)
                            elif 'Signal' in result_df.columns:
                                signal_value = int(row.get('Signal') or 0)

                            if signal_value == 0:
                                continue

                            # Filtrado por escenario - verificar si está desbloqueado
                            unlock_candle_scenario = False
                            try:
                                from app.config_app_modal import ConfigAppModal
                                config = ConfigAppModal.get_config() or {}
                                unlock_candle_scenario = config.get('unlock_candle_scenario', False)
                            except Exception:
                                pass
                            
                            if unlock_candle_scenario:
                                # Escenario desbloqueado - permitir todas las operaciones candle
                                if getattr(self, 'debug_mode', False):
                                    self.log(f"🔓 {strategy_name} desbloqueada por configuración (escenario candle)", 'green')
                                try:
                                    self._audit_log({
                                        'type': 'candle', 'event': 'unblocked',
                                        'strategy': strategy_name, 'signal': int(signal_value),
                                        'scenario': getattr(scenario, 'value', None), 'reason': 'unlock_candle_scenario enabled'
                                    })
                                except Exception:
                                    pass
                            else:
                                # Aplicar filtrado normal por escenario
                                try:
                                    allowed, reason = mapper.should_execute_strategy(strategy_name, scenario, signal_value)
                                except Exception:
                                    allowed, reason = True, 'No mapper'
                                if not allowed:
                                    if getattr(self, 'debug_mode', False):
                                        self.log(f"🚫 {strategy_name} bloqueada por escenario: {getattr(scenario, 'value', scenario)} ({reason})", 'orange')
                                    try:
                                        self._audit_log({
                                            'type': 'candle', 'event': 'blocked_by_scenario',
                                            'strategy': strategy_name, 'signal': int(signal_value),
                                            'scenario': getattr(scenario, 'value', None), 'reason': reason
                                        })
                                    except Exception:
                                        pass
                                    continue

                            # Evitar duplicados por estrategia/dirección (gestión interna sin nuevos campos UI)
                            try:
                                estrategia_nombre = f"candle_{strategy_name}"
                                # Determinar si es cierre por señal (-1 con operaciones activas) para NO bloquear
                                has_any_active = any(
                                    getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and getattr(op, 'estrategia', '') == estrategia_nombre
                                    for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                ) if hasattr(self, 'risk_manager') and self.risk_manager else False

                                # Cooldown por estrategia/dirección (solo aperturas)
                                try:
                                    cooldown_s = int(self._get_config_value('strategy_cooldown_seconds', 0) or 0)
                                except Exception:
                                    cooldown_s = 0
                                entry_side = None
                                if signal_value == 1:
                                    entry_side = 'BUY'
                                elif signal_value == -1 and not has_any_active:
                                    entry_side = 'SELL'
                                if entry_side is not None and cooldown_s > 0:
                                    if self._is_cooldown_hit(estrategia_nombre, entry_side, cooldown_s):
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏳ Cooldown activo para {estrategia_nombre} {entry_side}", 'yellow')
                                        try:
                                            self._audit_log({
                                                'type': 'candle', 'event': 'cooldown_skip',
                                                'strategy': strategy_name, 'entry_side': entry_side,
                                                'cooldown_seconds': cooldown_s
                                            })
                                        except Exception:
                                            pass
                                        continue

                                # Exit cooldown: si -1 y no hay activas, evitar reintentos redundantes
                                try:
                                    exit_cd_s = int(self._get_config_value('exit_cooldown_seconds', 0) or 0)
                                except Exception:
                                    exit_cd_s = 0
                                if signal_value == -1 and not has_any_active and exit_cd_s > 0:
                                    if self._is_exit_cooldown_hit(estrategia_nombre, exit_cd_s):
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏳ Exit cooldown activo para {estrategia_nombre}", 'yellow')
                                        try:
                                            self._audit_log({
                                                'type': 'candle', 'event': 'exit_cooldown_skip',
                                                'strategy': strategy_name,
                                                'cooldown_seconds': exit_cd_s
                                            })
                                        except Exception:
                                            pass
                                        continue
                                    else:
                                        self._mark_exit_cooldown(estrategia_nombre)

                                if signal_value == 1:
                                    has_buy_active = any(
                                        getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and getattr(op, 'estrategia', '') == estrategia_nombre and getattr(op, 'tipo', '') == 'BUY'
                                        for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                    ) if hasattr(self, 'risk_manager') and self.risk_manager else False
                                    if has_buy_active:
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏭️ BUY duplicado omitido para {estrategia_nombre}", 'yellow')
                                        continue
                                elif signal_value == -1 and not has_any_active:
                                    has_sell_active = any(
                                        getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and getattr(op, 'estrategia', '') == estrategia_nombre and getattr(op, 'tipo', '') == 'SELL'
                                        for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                    ) if hasattr(self, 'risk_manager') and self.risk_manager else False
                                    if has_sell_active:
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏭️ SELL duplicado omitido para {estrategia_nombre}", 'yellow')
                                        continue
                            except Exception:
                                pass

                            # Niveles SL/TP desde estrategia (si disponibles)
                            sl_override = float(row['StopLoss']) if 'StopLoss' in result_df.columns and pd.notna(row.get('StopLoss')) else None
                            tp_override = float(row['TakeProfit']) if 'TakeProfit' in result_df.columns and pd.notna(row.get('TakeProfit')) else None
                            # Calcular ATR value - usar columnas del DataFrame original si no están en result_df
                            if 'ATR' in result_df.columns and pd.notna(row.get('ATR')):
                                atr_value = float(row['ATR'])
                            elif 'High' in result_df.columns and 'Low' in result_df.columns:
                                atr_value = max(float(row['High']) - float(row['Low']), 1e-6)
                            else:
                                # Fallback: usar datos de la vela actual
                                atr_value = max(float(last_candle.get('High', 0)) - float(last_candle.get('Low', 0)), 1e-6)

                            # Preparar parámetros para integración
                            precio_actual = float(row.get('Close') or last_candle.get('Close', 0))
                            ts = result_df.index[-1]
                            estrategia_nombre = f"candle_{strategy_name}"

                            # Apertura/cierre vía integración (sync_mode=True)
                            op_result = self.risk_integration.procesar_senal(
                                senal=signal_value,
                                precio_actual=precio_actual,
                                timestamp=ts,
                                atr_value=atr_value,
                                rr_ratio=None,
                                risk_percent=None,  # usar default de configuración
                                estrategia_nombre=estrategia_nombre,
                                stop_loss_override=sl_override,
                                take_profit_override=tp_override,
                                candle_config=candle_cfg,
                                sync_mode=True,
                            )

                            # Actualizar contadores si se abrió una operación
                            if op_result is not None and hasattr(op_result, 'id'):
                                opens_candle_this_tick += 1
                                active_total += 1
                                active_candle += 1
                                self.log(f"✅ Apertura {estrategia_nombre} ({'BUY' if signal_value==1 else 'SELL'}) @ {precio_actual:.5f}", 'green')
                                try:
                                    self._audit_log({
                                        'type': 'candle', 'event': 'opened',
                                        'strategy': strategy_name,
                                        'signal': int(signal_value),
                                        'price': float(precio_actual),
                                        'scenario': getattr(scenario, 'value', None)
                                    })
                                except Exception:
                                    pass
                                # Marcar cooldown
                                if entry_side is not None:
                                    self._mark_cooldown(estrategia_nombre, entry_side)
                        except Exception as e:
                            if getattr(self, 'debug_mode', False):
                                self.log(f"Error evaluando {item}: {e}", 'red')
                            continue
            except Exception as e:
                if getattr(self, 'debug_mode', False):
                    self.log(f"Error T04 Candle Strategies: {e}", 'orange')

            # T05: Evaluar Forex Strategies seleccionadas y enviar a RiskManagerIntegration
            try:
                if hasattr(self, 'simulation_config') and self.simulation_config:
                    selected_forex = self.simulation_config.get('forex_strategies', []) or []
                else:
                    selected_forex = []

                if selected_forex and hasattr(self, 'risk_integration') and self.risk_integration:
                    max_orders_total = int(self.simulation_config.get('max_orders', 5))
                    max_forex_ops = int(self.simulation_config.get('max_forex_operations', max_orders_total))

                    def count_active_by_prefix(prefix: str) -> int:
                        try:
                            return sum(1 for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                       if getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and
                                       isinstance(getattr(op, 'estrategia', None), str) and
                                       getattr(op, 'estrategia').startswith(prefix))
                        except Exception:
                            return 0

                    active_total = int(self.risk_manager.get_operaciones_activas_count()) if hasattr(self, 'risk_manager') and self.risk_manager else 0
                    active_forex = count_active_by_prefix('forex_')
                    opens_forex_this_tick = 0

                    # Instancia única de ForexStrategies para el DF actual
                    # Crear copia con columnas en mayúsculas para compatibilidad
                    df_forex = df.copy()
                    column_mapping = {
                        'open': 'Open',
                        'high': 'High', 
                        'low': 'Low',
                        'close': 'Close',
                        'volume': 'Volume'
                    }
                    columns_to_rename = {col: column_mapping[col] for col in df_forex.columns if col in column_mapping}
                    if columns_to_rename:
                        df_forex.rename(columns=columns_to_rename, inplace=True)
                    
                    
                    fs = ForexStrategies(df_forex)

                    # Preparar mapper y reordenar por prioridad segun escenario
                    fx_mapper = MarketStrategyMapper()
                    scenario = getattr(self, 'current_market_scenario', None)
                    try:
                        # Construir prioridades por escenario
                        available_fx = [fx.get('name') for fx in selected_forex if isinstance(fx, dict) and fx.get('name')]
                        prioritized_fx = fx_mapper.get_prioritized_forex_strategies(scenario, available_fx)
                        def _fx_weight(item):
                            try:
                                n = item.get('name') if isinstance(item, dict) else None
                                pr = prioritized_fx.get(n)
                                # Convertir prioridad a peso numérico (igual que get_priority_weight para candle)
                                return {1: 1.0, 2: 0.5, 3: 0.2, 4: 0.0}.get(getattr(pr, 'value', 99), 0.0)
                            except Exception:
                                return 0.0
                        selected_forex.sort(key=_fx_weight, reverse=True)
                    except Exception:
                        pass

                    for fx in selected_forex:
                        try:
                            name = fx.get('name') if isinstance(fx, dict) else None
                            if not name:
                                continue

                            # Limites de operaciones
                            if active_total >= max_orders_total:
                                if getattr(self, 'debug_mode', False):
                                    self.log(f"🚫 Límite total de órdenes alcanzado ({active_total}/{max_orders_total})", 'orange')
                                try:
                                    self._audit_log({
                                        'type': 'forex', 'event': 'skipped_slot_limit_total',
                                        'strategy': name,
                                        'active_total': active_total,
                                        'max_total': max_orders_total,
                                        'scenario': getattr(scenario, 'value', None)
                                    })
                                except Exception:
                                    pass
                                break
                            if active_forex + opens_forex_this_tick >= max_forex_ops:
                                if getattr(self, 'debug_mode', False):
                                    self.log(f"🚫 Límite de órdenes Forex alcanzado en esta vela ({active_forex + opens_forex_this_tick}/{max_forex_ops})", 'orange')
                                try:
                                    self._audit_log({
                                        'type': 'forex', 'event': 'skipped_slot_limit_type',
                                        'strategy': name,
                                        'active_type': active_forex + opens_forex_this_tick,
                                        'max_type': max_forex_ops,
                                        'scenario': getattr(scenario, 'value', None)
                                    })
                                except Exception:
                                    pass
                                continue

                            method = getattr(fs, name, None)
                            if not callable(method):
                                continue

                            # Ejecutar estrategia (usa ExecSignal/StopLoss/TakeProfit/ATR propios)
                            try:
                                result_df = method()
                                if result_df is None or len(result_df) == 0:
                                    continue
                            except Exception as e:
                                import traceback
                                self.log(f"❌ Error ejecutando estrategia {name}: {str(e)}", 'red')
                                self.log(f"Stack trace: {traceback.format_exc()}", 'red')
                                continue
                            row = result_df.iloc[-1]

                            # Señal de ejecución
                            signal_value = 0
                            if 'ExecSignal' in result_df.columns:
                                try:
                                    signal_value = int(row.get('ExecSignal') or 0)
                                except Exception:
                                    signal_value = 0
                            elif 'Signal' in result_df.columns:
                                try:
                                    signal_value = int(row.get('Signal') or 0)
                                except Exception:
                                    signal_value = 0

                            if signal_value == 0:
                                continue

                            # Filtrado por escenario - verificar si está desbloqueado
                            unlock_forex_scenario = False
                            try:
                                from app.config_app_modal import ConfigAppModal
                                config = ConfigAppModal.get_config() or {}
                                unlock_forex_scenario = config.get('unlock_forex_scenario', False)
                            except Exception:
                                pass
                            
                            if unlock_forex_scenario:
                                # Escenario desbloqueado - permitir todas las operaciones forex
                                if getattr(self, 'debug_mode', False):
                                    self.log(f"🔓 {name} desbloqueada por configuración (escenario forex)", 'green')
                                try:
                                    self._audit_log({
                                        'type': 'forex', 'event': 'unblocked',
                                        'strategy': name, 'signal': int(signal_value),
                                        'scenario': getattr(scenario, 'value', None), 'reason': 'unlock_forex_scenario enabled'
                                    })
                                except Exception:
                                    pass
                            else:
                                # Aplicar filtrado normal por escenario (priorización/permiso) para Forex
                                try:
                                    allowed_fx, reason_fx = fx_mapper.should_execute_forex_strategy(name, scenario, signal_value)
                                except Exception:
                                    allowed_fx, reason_fx = True, 'No mapper'
                                if not allowed_fx:
                                    if getattr(self, 'debug_mode', False):
                                        self.log(f"🚫 {name} bloqueada por escenario: {getattr(scenario, 'value', scenario)} ({reason_fx})", 'orange')
                                    try:
                                        self._audit_log({
                                            'type': 'forex', 'event': 'blocked_by_scenario',
                                            'strategy': name, 'signal': int(signal_value),
                                            'scenario': getattr(scenario, 'value', None), 'reason': reason_fx
                                        })
                                    except Exception:
                                        pass
                                    continue

                            # Evitar duplicados por estrategia/dirección (gestión interna)
                            try:
                                estrategia_nombre = f"forex_{name}"
                                # -1 con operaciones activas: cierre por señal permitido
                                has_any_active = any(
                                    getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and getattr(op, 'estrategia', '') == estrategia_nombre
                                    for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                ) if hasattr(self, 'risk_manager') and self.risk_manager else False

                                # Cooldown por estrategia/dirección (solo aperturas)
                                try:
                                    cooldown_s = int(self._get_config_value('strategy_cooldown_seconds', 0) or 0)
                                except Exception:
                                    cooldown_s = 0
                                entry_side = None
                                if signal_value == 1:
                                    entry_side = 'BUY'
                                elif signal_value == -1 and not has_any_active:
                                    entry_side = 'SELL'
                                if entry_side is not None and cooldown_s > 0:
                                    if self._is_cooldown_hit(estrategia_nombre, entry_side, cooldown_s):
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏳ Cooldown activo para {estrategia_nombre} {entry_side}", 'yellow')
                                        try:
                                            self._audit_log({
                                                'type': 'forex', 'event': 'cooldown_skip',
                                                'strategy': name, 'entry_side': entry_side,
                                                'cooldown_seconds': cooldown_s
                                            })
                                        except Exception:
                                            pass
                                        continue

                                # Exit cooldown: si -1 y no hay activas, evitar reintentos redundantes
                                try:
                                    exit_cd_s = int(self._get_config_value('exit_cooldown_seconds', 0) or 0)
                                except Exception:
                                    exit_cd_s = 0
                                if signal_value == -1 and not has_any_active and exit_cd_s > 0:
                                    if self._is_exit_cooldown_hit(estrategia_nombre, exit_cd_s):
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏳ Exit cooldown activo para {estrategia_nombre}", 'yellow')
                                        try:
                                            self._audit_log({
                                                'type': 'forex', 'event': 'exit_cooldown_skip',
                                                'strategy': name,
                                                'cooldown_seconds': exit_cd_s
                                            })
                                        except Exception:
                                            pass
                                        continue
                                    else:
                                        self._mark_exit_cooldown(estrategia_nombre)

                                if signal_value == 1:
                                    has_buy_active = any(
                                        getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and getattr(op, 'estrategia', '') == estrategia_nombre and getattr(op, 'tipo', '') == 'BUY'
                                        for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                    ) if hasattr(self, 'risk_manager') and self.risk_manager else False
                                    if has_buy_active:
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏭️ BUY duplicado omitido para {estrategia_nombre}", 'yellow')
                                        continue
                                elif signal_value == -1 and not has_any_active:
                                    has_sell_active = any(
                                        getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and getattr(op, 'estrategia', '') == estrategia_nombre and getattr(op, 'tipo', '') == 'SELL'
                                        for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                    ) if hasattr(self, 'risk_manager') and self.risk_manager else False
                                    if has_sell_active:
                                        if getattr(self, 'debug_mode', False):
                                            self.log(f"⏭️ SELL duplicado omitido para {estrategia_nombre}", 'yellow')
                                        continue
                            except Exception:
                                pass

                            # Niveles desde estrategia
                            sl_override = float(row['StopLoss']) if 'StopLoss' in result_df.columns and pd.notna(row.get('StopLoss')) else None
                            tp_override = float(row['TakeProfit']) if 'TakeProfit' in result_df.columns and pd.notna(row.get('TakeProfit')) else None
                            # Calcular ATR value - usar columnas del DataFrame original si no están en result_df
                            if 'ATR' in result_df.columns and pd.notna(row.get('ATR')):
                                atr_value = float(row['ATR'])
                            elif 'High' in result_df.columns and 'Low' in result_df.columns:
                                atr_value = max(float(row['High']) - float(row['Low']), 1e-6)
                            else:
                                # Fallback: usar datos de la vela actual
                                atr_value = max(float(last_candle.get('High', 0)) - float(last_candle.get('Low', 0)), 1e-6)

                            precio_actual = float(row.get('Close') or last_candle.get('Close', 0))
                            ts = result_df.index[-1]
                            estrategia_nombre = f"forex_{name}"

                            # risk de modal está en fracción (0.01). Integration espera porcentaje (1.0 -> 1%).
                            risk_fraction = float(fx.get('risk', 0.01)) if isinstance(fx, dict) else 0.01
                            rr_ratio = float(fx.get('rr_ratio', 2.0)) if isinstance(fx, dict) else 2.0
                            risk_percent = risk_fraction * 100.0

                            op_result = self.risk_integration.procesar_senal(
                                senal=signal_value,
                                precio_actual=precio_actual,
                                timestamp=ts,
                                atr_value=atr_value,
                                rr_ratio=rr_ratio,
                                risk_percent=risk_percent,
                                estrategia_nombre=estrategia_nombre,
                                stop_loss_override=sl_override,
                                take_profit_override=tp_override,
                                candle_config=None,
                                sync_mode=True,
                            )

                            if op_result is not None and hasattr(op_result, 'id'):
                                opens_forex_this_tick += 1
                                active_total += 1
                                active_forex += 1
                                self.log(f"✅ Apertura {estrategia_nombre} ({'BUY' if signal_value==1 else 'SELL'}) @ {precio_actual:.5f} | riesgo {risk_percent:.2f}% RR {rr_ratio}", 'green')
                                try:
                                    self._audit_log({
                                        'type': 'forex', 'event': 'opened',
                                        'strategy': name,
                                        'signal': int(signal_value),
                                        'price': float(precio_actual),
                                        'risk_percent': float(risk_percent),
                                        'rr_ratio': float(rr_ratio),
                                        'scenario': getattr(scenario, 'value', None)
                                    })
                                except Exception:
                                    pass
                                # Marcar cooldown
                                if entry_side is not None:
                                    self._mark_cooldown(estrategia_nombre, entry_side)
                        except Exception as e:
                            # Mostrar error siempre, no solo en debug mode
                            self.log(f"Error evaluando forex {fx}: {e}", 'red')
                            continue
            except Exception as e:
                self.log(f"Error T05 Forex Strategies: {e}", 'orange')
            
            # Actualizar contadores de slots (para labels del encabezado de la gráfica)
            try:
                if hasattr(self, 'risk_manager') and self.risk_manager:
                    # Límites
                    max_orders_total = int(self.simulation_config.get('max_orders', 5)) if hasattr(self, 'simulation_config') else 5
                    max_candle_ops = int(self.simulation_config.get('max_candle_operations', max_orders_total)) if hasattr(self, 'simulation_config') else max_orders_total
                    max_forex_ops = int(self.simulation_config.get('max_forex_operations', max_orders_total)) if hasattr(self, 'simulation_config') else max_orders_total

                    # Contadores actuales
                    total_actual = int(self.risk_manager.get_operaciones_activas_count())
                    def _count_by_prefix(prefix: str) -> int:
                        try:
                            return sum(1 for op in getattr(self.risk_manager, 'operaciones_activas', [])
                                       if getattr(op, 'estado', 'ACTIVA') == 'ACTIVA' and
                                       isinstance(getattr(op, 'estrategia', None), str) and
                                       getattr(op, 'estrategia').startswith(prefix))
                        except Exception:
                            return 0
                    candle_actual = _count_by_prefix('candle_')
                    forex_actual = _count_by_prefix('forex_')
                    # Actualizar etiquetas en encabezado superior de la gráfica
                    try:
                        scenario = getattr(self, 'current_market_scenario', None)
                        scenario_text = scenario.value if scenario else "Indeterminado"
                        market_text = f"Tipo de mercado: {scenario_text}"
                        slots_text = (
                            f"Slots: {total_actual}/{max_orders_total} | "
                            f"Candle: {candle_actual}/{max_candle_ops} | "
                            f"Forex: {forex_actual}/{max_forex_ops}"
                        )
                        if hasattr(self, 'candle_streamer') and self.candle_streamer:
                            # Mostrar labels fuera del área de velas, en la parte superior
                            self.candle_streamer.set_header_labels(market_text, slots_text)
                    except Exception:
                        pass
            except Exception:
                pass
            
        except Exception as e:
            self.log(f"Error en procesamiento asíncrono de vela: {str(e)}", color='red')
        finally:
            self._processing_candle = False
            
    def _analyze_market_type(self, df):
        """Analiza el tipo de mercado usando ForexMarketAnalyzer cada 5 velas"""
        try:
            # Verificar que tenemos suficientes datos
            if len(df) < 20:
                return
                
            # Importar el analizador de mercado
            if not hasattr(self, '_market_analyzer') or self._market_analyzer is None:
                try:
                    from app.market_scene_detector import ForexMarketAnalyzer
                    self._market_analyzer = ForexMarketAnalyzer()
                except Exception as e:
                    if getattr(self, 'debug_mode', False):
                        self.log(f"DEBUG Error importando ForexMarketAnalyzer: {str(e)}", color="orange")
                    self._market_analyzer = None
                    return
            
            # Preparar datos para el análisis (últimas 50 velas o todas si hay menos)
            analysis_window = min(50, len(df))
            df_analysis = df.tail(analysis_window).copy()
            
            # Renombrar columnas para que coincidan con lo esperado por el analizador
            df_analysis = df_analysis.rename(columns={
                'High': 'high',
                'Low': 'low', 
                'Close': 'close',
                'Open': 'open'
            })
            
            # Detectar el escenario de mercado
            analysis_result = self._market_analyzer.analyze_market(df_analysis)
            scenario = analysis_result.get('primary_scenario', None)
            
            # Solo actualizar si el escenario cambió
            if scenario != getattr(self, 'current_market_scenario', None):
                self.current_market_scenario = scenario
                scenario_text = scenario.value if scenario else "Indeterminado"
                
                # Ya no se actualiza la etiqueta de tipo de mercado en la status bar (se muestra en el header del gráfico)

                # Log del cambio de escenario
                self.log(f"📊 Tipo de mercado detectado: {scenario_text}", color="white")
                
                # Debug: mostrar información adicional si está habilitado
                if getattr(self, 'debug_mode', False):
                    from strategies.market_strategy_mapper import MarketStrategyMapper
                    mapper = MarketStrategyMapper()
                    description = mapper.get_scenario_description(scenario)
                    self.log(f"DEBUG Mercado: {description}", color="cyan")
                    
        except Exception as e:
            if getattr(self, 'debug_mode', False):
                self.log(f"DEBUG Error analizando mercado: {str(e)}", color="orange")
                
    def _procesar_senal_compra(self, candle_data):
        """Procesa señales de compra"""
        try:
            # Lógica de procesamiento de señales de compra
            try:
                precio_actual = float(candle_data['Close'])
            except Exception:
                # Fallback defensivo si fuese un dict con clave en minúscula
                precio_actual = float(candle_data.get('close', 0)) if hasattr(candle_data, 'get') else 0.0
            if precio_actual > 0:
                # Actualizar dinero visible
                if hasattr(self.main_app, 'strategy_handler'):
                    self.main_app.strategy_handler._actualizar_dinero_visible(precio_actual)
        except Exception as e:
            self.log(f"Error procesando señal de compra: {str(e)}", color='red')
            
    def _verificar_cierre_ordenes(self, candle_data):
        """Verifica y cierra órdenes si es necesario"""
        try:
            # Lógica de verificación y cierre de órdenes
            if hasattr(self, 'risk_manager') and self.risk_manager:
                operaciones_activas = getattr(self.risk_manager, 'operaciones_activas', [])
                for operacion in operaciones_activas:
                    # Verificar condiciones de cierre
                    pass
        except Exception as e:
            self.log(f"Error verificando cierre de órdenes: {str(e)}", color='red')
            
    def _update_sim_status_color(self, status, color):
        """Actualiza el estado de la simulación con color"""
        try:
            if hasattr(self.main_app, 'thread_manager'):
                self.main_app.thread_manager.queue_gui_update('simulation_status', (status, color))
        except Exception as e:
            self.log(f"Error actualizando estado de simulación: {str(e)}", color='red')
    
    # =====================
    # Helpers de configuración y auditoría
    # =====================
    def _get_config_value(self, key: str, default=None):
        """Obtiene un valor de configuración desde la simulación o app_config.json.
        Prioridad: self.simulation_config -> app_config.json -> default.
        """
        try:
            # 1) Config específica de la simulación
            if hasattr(self, 'simulation_config') and isinstance(self.simulation_config, dict):
                if key in self.simulation_config:
                    return self.simulation_config.get(key, default)
            # 2) Config global de la aplicación
            try:
                from app.config_app_modal import ConfigAppModal
                cfg = ConfigAppModal.get_config() or {}
                if key in cfg:
                    return cfg.get(key, default)
            except Exception:
                pass
        except Exception:
            pass
        return default

    def _ensure_audit_dir(self) -> str:
        """Asegura la carpeta de audit log y devuelve su ruta absoluta."""
        try:
            audit_dir_name = str(self._get_config_value('audit_log_dir', 'logs') or 'logs')
            # Carpeta base del proyecto
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            audit_dir = os.path.join(project_root, audit_dir_name)
            os.makedirs(audit_dir, exist_ok=True)
            return audit_dir
        except Exception:
            # Fallback a carpeta local
            try:
                os.makedirs('logs', exist_ok=True)
            except Exception:
                pass
            return 'logs'

    def _audit_log(self, data: dict):
        """Escribe un evento de auditoría en formato JSONL si está habilitado en config."""
        try:
            enabled = bool(self._get_config_value('audit_log_enabled', True))
            if not enabled:
                return
            audit_dir = self._ensure_audit_dir()
            # Archivo diario
            import datetime as _dt
            date_str = _dt.datetime.utcnow().strftime('%Y%m%d')
            file_path = os.path.join(audit_dir, f'audit_{date_str}.jsonl')
            record = {
                'ts': time.time(),
                'iso': _dt.datetime.utcnow().isoformat() + 'Z',
                **(data or {})
            }
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception:
            # No romper el flujo si falla la auditoría
            pass

    # =====================
    # Helpers de cooldown
    # =====================
    def _cooldown_key(self, strategy_name: str, side: str) -> str:
        return f"{strategy_name}::{side}"

    def _is_cooldown_hit(self, strategy_name: str, side: str, cooldown_seconds: int) -> bool:
        try:
            if cooldown_seconds <= 0:
                return False
            now = time.time()
            key = self._cooldown_key(strategy_name, side)
            last = (self._cooldown_open_times or {}).get(key, 0.0)
            return (now - last) < cooldown_seconds
        except Exception:
            return False

    def _mark_cooldown(self, strategy_name: str, side: str):
        try:
            if not hasattr(self, '_cooldown_open_times') or self._cooldown_open_times is None:
                self._cooldown_open_times = {}
            key = self._cooldown_key(strategy_name, side)
            self._cooldown_open_times[key] = time.time()
        except Exception:
            pass

    def _is_exit_cooldown_hit(self, strategy_name: str, cooldown_seconds: int) -> bool:
        try:
            if cooldown_seconds <= 0:
                return False
            now = time.time()
            last = (self._cooldown_exit_times or {}).get(strategy_name, 0.0)
            return (now - last) < cooldown_seconds
        except Exception:
            return False

    def _mark_exit_cooldown(self, strategy_name: str):
        try:
            if not hasattr(self, '_cooldown_exit_times') or self._cooldown_exit_times is None:
                self._cooldown_exit_times = {}
            self._cooldown_exit_times[strategy_name] = time.time()
        except Exception:
            pass
            
    def log(self, message, color='white'):
        """Método para logging - redirige al main_app si existe"""
        if hasattr(self.main_app, 'log'):
            self.main_app.log(message, color=color)
        else:
            print(f"{color.upper()}: {message}")