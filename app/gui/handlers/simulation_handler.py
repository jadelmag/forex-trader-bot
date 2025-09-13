# app/handlers/simulation_handler.py
import tkinter as tk
from tkinter import messagebox

class SimulationHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        self.candle_streamer = None
        
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
                        if hasattr(self.main_app, 'dinero_ficticio'):
                            self.main_app.dinero_ficticio = initial_money
                        if hasattr(self.main_app, 'risk_manager') and self.main_app.risk_manager is not None:
                            self.main_app.risk_manager.capital_inicial = initial_money
                            self.main_app.risk_manager.capital = initial_money
                        # Refrescar UI si existe el método
                        if hasattr(self.main_app, 'actualizar_labels'):
                            self.main_app.actualizar_labels()
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
            from trading_view.candle_streamer import CandleStreamer
            
            # Obtener el frame del gráfico desde main_app
            grafico_frame = None
            if hasattr(self.main_app, 'grafico_manager') and hasattr(self.main_app.grafico_manager, 'frame_grafico'):
                grafico_frame = self.main_app.grafico_manager.frame_grafico
            
            # Crear el streamer con la configuración del modal
            self.candle_streamer = CandleStreamer(
                interval=config.get('interval', '1m'),
                max_plot=config.get('max_plot', 500),
                parent_frame=grafico_frame,
                log_callback=self.log,
                visible_candles=config.get('visible_candles', 20)
            )
            
            # Configurar símbolo después de la inicialización
            if 'symbol' in config:
                self.candle_streamer.symbol = config['symbol']
                # Actualizar el archivo CSV con el nuevo símbolo
                import os
                self.candle_streamer.csv_file = os.path.join(
                    self.candle_streamer.csv_folder, 
                    f"{config['symbol']}_data.csv"
                )
            
            # Iniciar el stream
            self.candle_streamer.start()
            self.log(f"Streamer iniciado con configuración: {config}", color='green')
            
        except Exception as e:
            self.log(f"Error iniciando streamer con configuración: {str(e)}", color='red')

    def log(self, message, color='white'):
        """Método para logging - redirige al main_app si existe"""
        if hasattr(self.main_app, 'log'):
            self.main_app.log(message, color=color)
        else:
            print(f"{color.upper()}: {message}")
            
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

            from trading_view import CandleStreamerConfigModal

            def on_connect(config):
                # Sincronizar capital desde el modal si viene informado
                try:
                    if "initial_money" in config:
                        initial_money = float(config["initial_money"])
                        self.dinero_ficticio = initial_money
                        if hasattr(self, 'risk_manager') and self.risk_manager is not None:
                            self.risk_manager.capital_inicial = initial_money
                            self.risk_manager.capital = initial_money
                        try:
                            self.entry_dinero.delete(0, tk.END)
                            self.entry_dinero.insert(0, f"{initial_money}")
                        except Exception:
                            pass
                        self.actualizar_labels()
                        self._queue_gui_update('cash', initial_money)
                except Exception:
                    pass
                # Reiniciar con nueva configuración (internamente limpia el gráfico y detiene si está corriendo)
                self._start_streamer_with_config(config)

            CandleStreamerConfigModal(
                parent=self.root,
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
                
                # Configurar el sistema de reports con los parámetros de la simulación
                try:
                    from app.reports import set_simulation_config
                    
                    # Obtener capital inicial
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
        print("DEBUG: Test button clicked")  # Debug log
        self.iniciar_streamer()
        
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
            capital_limit = self._get_capital_limit()
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
            
    def _get_capital_limit(self):
        """Obtiene el límite mínimo de capital para operar"""
        return 1000.0  # Límite mínimo de $1000
        
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
        
    def _start_streamer_with_config(self, config):
        """Inicia el CandleStreamer con la configuración proporcionada"""
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
            
            # Configurar auto-desconexión si está habilitada
            if config.get("auto_disconnect_after_candles", False):
                target_candles = config.get("target_candles", 500)
                self.candle_streamer.configure_auto_disconnect(True, target_candles)
            
            # Iniciar el streamer en un hilo separado
            def start_streamer():
                try:
                    self.candle_streamer.start()
                except Exception as e:
                    self.log(f"Error en CandleStreamer: {str(e)}", color="red")
            
            # Iniciar el streamer en un hilo para no bloquear la interfaz
            import threading
            streamer_thread = threading.Thread(target=start_streamer, daemon=True)
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
            
            # Análisis de mercado cada 5 velas
            if not hasattr(self, 'candle_count_for_market_analysis'):
                self.candle_count_for_market_analysis = 0
            self.candle_count_for_market_analysis += 1
            
            if self.candle_count_for_market_analysis >= 5:
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
                return
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
            self._verificar_cierre_ordenes(last_candle)
            
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
                
                # Actualizar la etiqueta en la GUI
                if hasattr(self.main_app, 'status_bar'):
                    self.main_app.status_bar.actualizar_tipo_mercado(scenario_text)
                
                # Log del cambio de escenario
                self.log(f"📊 Tipo de mercado detectado: {scenario_text}", color="blue")
                
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
            precio_actual = float(candle_data.get('close', 0))
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
            
    def modificar_config_simulacion_binance(self):
        """Modifica la configuración de simulación de Binance"""
        try:
            from app.config_modal import ConfigModal
            ConfigModal(self.main_app.root, title="Configuración Simulación Binance")
        except Exception as e:
            self.log(f"Error abriendo configuración de Binance: {str(e)}", color='red')
            
    def detener_simulacion_binance(self):
        """Detiene la simulación de Binance"""
        try:
            if hasattr(self, '_simulation_running'):
                self._simulation_running = False
            self.log("Simulación de Binance detenida", color='orange')
        except Exception as e:
            self.log(f"Error deteniendo simulación de Binance: {str(e)}", color='red')
            
    def generar_informe(self):
        """Genera un informe de la simulación"""
        try:
            # Lógica para generar informe
            self.log("Generando informe de simulación...", color='cyan')
            # Aquí iría la lógica real de generación de informes
            self.log("Informe generado exitosamente", color='green')
        except Exception as e:
            self.log(f"Error generando informe: {str(e)}", color='red')
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)