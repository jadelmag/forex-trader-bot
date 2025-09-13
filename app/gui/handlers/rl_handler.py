# app/handlers/rl_handler.py
import tkinter as tk
import threading
import queue
from tkinter import messagebox
from app.rl_training_modal import RLTrainingModal
from rl.rl_agent import RLTradingAgent

class RLHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        self._training_active = False
        self._log_queue = queue.Queue()
        self.num_posiciones_activas = 50
        self._processing_thread = None
        self._stop_processing = threading.Event()
        

    def entrenar_rl(self):
        """Mostrar modal de entrenamiento"""
        def _start_training(iterations: int, on_complete, on_progress=None, cancel_event=None):
            try:
                # Logger thread-safe hacia el log inferior
                def _log_ts(msg: str, color='white'):
                    try:
                        self.main_app.root.after(0, lambda: self.main_app.log_panel.log(str(msg), color))
                    except Exception:
                        pass
                # Obtener estrategias seleccionadas actualmente en la GUI
                estrategias_fx_seleccionadas = {}
                estrategias_candle_seleccionadas = []
                
                # Obtener estrategias forex seleccionadas
                try:
                    if hasattr(self, 'forex_strategies') and self.forex_strategies:
                        for nombre_estrategia in self.forex_strategies.get_strategy_names():
                            if hasattr(self, f'var_fx_{nombre_estrategia}'):
                                var = getattr(self, f'var_fx_{nombre_estrategia}')
                                if var.get():
                                    estrategias_fx_seleccionadas[nombre_estrategia] = {}
                except Exception as e:
                    _log_ts(f"Error obteniendo estrategias forex: {e}", 'yellow')
                
                # Obtener estrategias de velas seleccionadas
                try:
                    if hasattr(self, 'candle_strategies') and self.candle_strategies:
                        for nombre_estrategia in self.candle_strategies.get_strategy_names():
                            if hasattr(self, f'var_candle_{nombre_estrategia}'):
                                var = getattr(self, f'var_candle_{nombre_estrategia}')
                                if var.get():
                                    estrategias_candle_seleccionadas.append(nombre_estrategia)
                except Exception as e:
                    _log_ts(f"Error obteniendo estrategias de velas: {e}", 'yellow')
                
                
                # Log de selecciones para debugging
                _log_ts(f"Estrategias FX seleccionadas: {list(estrategias_fx_seleccionadas.keys())}", 'cyan')
                _log_ts(f"Estrategias Candle seleccionadas: {estrategias_candle_seleccionadas}", 'cyan')
                
                self.rl_agent = RLTradingAgent(
                    self.main_app.csv_handler.df_actual,
                    estrategias_fx=estrategias_fx_seleccionadas,
                    estrategias_candle=estrategias_candle_seleccionadas,
                    patrones=[],
                    log_fn=lambda m: _log_ts(m, 'cyan')
                )
                success = self.rl_agent.entrenar(timesteps=iterations, progress_cb=on_progress, cancel_event=cancel_event)
                
                # Check if training was cancelled
                if cancel_event and cancel_event.is_set():
                    on_complete(success=False, error_msg="Entrenamiento cancelado por el usuario")
                    return
                
                # Avisar al modal que el entrenamiento terminó OK o con error
                on_complete(success=success)
                
                # Only show completion message and apply signals if successful
                if success:
                    # Aviso visual de fin de entrenamiento
                    try:
                        self.main_app.root.after(0, lambda: messagebox.showinfo("IA", "Entrenamiento completado y modelo guardado"))
                    except Exception:
                        pass
                    # Tras finalizar el entrenamiento, aplicar automáticamente las señales RL
                    # para calcular y reflejar Beneficios/Pérdidas en la barra superior.
                    try:
                        self.main_app.root.after(0, lambda: (
                            self.main_app.log_panel.log("Aplicando señales RL post-entrenamiento...", 'yellow'),
                            self.aplicar_senales_rl()
                        ))
                    except Exception:
                        pass
            except Exception as e:
                on_complete(success=False, error_msg=str(e))

        RLTrainingModal(self.main_app.root, start_training_callback=_start_training)
   
    def detener_entrenamiento(self):
        """Detiene el entrenamiento de IA en curso si existe."""
        try:
            if hasattr(self, "_ai_trainer") and self._ai_trainer:
                trainer = self._ai_trainer
                trainer.stop()
                # Evitar múltiples solicitudes de parada
                try:
                    if hasattr(self, 'menu_opciones'):
                        self.menu_opciones.entryconfig(self._menu_label_detener_ia, state="disabled")
                except Exception:
                    pass
                self.main_app.log_panel.log("Solicitud de detener entrenamiento enviada.", "yellow")
                if hasattr(self, "lbl_ai_status"):
                    self.lbl_ai_status.config(text="Listo para entrenar", fg="blue")

                self._ai_trainer = None
            else:
                self.main_app.log_panel.log("⚠️ No hay entrenamiento en curso para detener.", "orange")
        except Exception as e:
            self.main_app.log_panel.log(f"Error al detener el entrenamiento: {e}", "red")
          
    def cargar_rl(self):
        """Carga un modelo RL existente"""
        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Atención", "Debe cargar un CSV primero")
            return
        self.rl_agent = RLTradingAgent(
            self.main_app.csv_handler.df_actual,
            estrategias_fx={},
            estrategias_candle=[],
            patrones=[]
        )
        cargado = self.rl_agent.cargar_modelo()
        if cargado:
            messagebox.showinfo("RL", "Modelo cargado correctamente")
        
    def aplicar_senales_rl(self):
        """Aplica señales de compra/venta generadas por el agente RL usando threading"""
        # Validación más robusta
        if self.rl_agent is None:
            messagebox.showwarning("Atención", "No hay agente RL cargado. Entrene o cargue primero el agente.")
            return
        
        if self.main_app.csv_handler.df_actual is None or self.main_app.csv_handler.df_actual.empty:
            messagebox.showwarning("Atención", "No hay datos para procesar. Cargue primero los datos.")
            return

        # Verificar si ya hay un procesamiento en curso
        if self._processing_thread and self._processing_thread.is_alive():
            messagebox.showwarning("Atención", "Ya hay un procesamiento de señales RL en curso.")
            return

        # Limpiar interfaz/estado
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.limpiar_log()

        # Resetear evento de parada
        self._stop_processing.clear()
        
        # Iniciar procesamiento en hilo separado
        self._processing_thread = threading.Thread(
            target=self._procesar_senales_thread,
            daemon=True
        )
        self._processing_thread.start()
        
        # Iniciar procesamiento de cola de logs
        self._process_log_queue()

    def _procesar_senales_thread(self):
        """Procesa las señales RL en un hilo separado"""
        try:
            # Generar señales
            self._queue_log_update("Generando señales RL...", "cyan")
            self.rl_signals = self.rl_agent.generar_senales()
            
            # Validar que las señales coincidan con los datos
            if len(self.rl_signals) != len(self.main_app.csv_handler.df_actual):
                self._queue_log_update(f"Ajustando señales: {len(self.rl_signals)} -> {len(self.main_app.csv_handler.df_actual)}", "yellow")
                # Ajustar señales si es necesario
                if len(self.rl_signals) > len(self.main_app.csv_handler.df_actual):
                    self.rl_signals = self.rl_signals[:len(self.main_app.csv_handler.df_actual)]
                else:
                    import numpy as np
                    self.rl_signals = np.pad(self.rl_signals, 
                                           (0, len(self.main_app.csv_handler.df_actual) - len(self.rl_signals)), 
                                           'constant')

            # Precalcular confirmación por patrones de velas
            try:
                self._queue_log_update("Calculando patrones de confirmación...", "cyan")
                from patterns.candlestickpatterns import CandlestickPatterns
                patterns = CandlestickPatterns(self.main_app.csv_handler.df_actual)
                df_patterns = patterns.combined_signal_optimized()
                # Alinear por índice
                self._pattern_signals = df_patterns['Final_Signal'].reindex(self.main_app.csv_handler.df_actual.index).fillna(0)
            except Exception:
                self._pattern_signals = None

            # Inicializar posiciones activas por defecto
            self.posiciones_activas = []
            self.operaciones = []
            
            # Crear posiciones iniciales con el primer precio disponible
            if len(self.main_app.csv_handler.df_actual) > 0:
                precio_inicial = float(self.main_app.csv_handler.df_actual.iloc[0]['Close'])
                timestamp_inicial = self.main_app.csv_handler.df_actual.index[0]
                
                for i in range(self.num_posiciones_activas):
                    if self._stop_processing.is_set():
                        return
                        
                    pos = {
                        'precio': precio_inicial,
                        'fecha': timestamp_inicial,
                        'indice': i
                    }
                    self.posiciones_activas.append(pos)
                    
                    # Registrar operación inicial
                    self.operaciones.append({
                        'tipo': 'compra_inicial',
                        'precio': precio_inicial,
                        'fecha': timestamp_inicial,
                        'signal_idx': 0
                    })
                
                self._queue_log_update(f"Inicializadas {len(self.posiciones_activas)} posiciones activas por defecto a precio {precio_inicial:.5f}", 'cyan')

            # Procesar cada señal con progreso
            total_signals = len(self.main_app.csv_handler.df_actual)
            self._queue_log_update(f"Procesando {total_signals} señales RL...", "cyan")
            
            for idx, (timestamp, row) in enumerate(self.main_app.csv_handler.df_actual.iterrows()):
                if self._stop_processing.is_set():
                    self._queue_log_update("Procesamiento cancelado por el usuario", "orange")
                    return
                    
                self._procesar_senal_rl(idx, timestamp, row)
                
                # Mostrar progreso cada 100 señales
                if (idx + 1) % 100 == 0:
                    progreso = ((idx + 1) / total_signals) * 100
                    self._queue_log_update(f"Progreso: {idx + 1}/{total_signals} ({progreso:.1f}%)", "white")

            # Actualizar gráfico en el hilo principal
            def update_gui():
                try:
                    if hasattr(self.main_app, 'grafico_manager') and self.main_app.grafico_manager:
                        self.main_app.grafico_manager.dibujar_senales_rl(self.rl_signals)
                except Exception as e:
                    self._queue_log_update(f"Error actualizando gráfico: {e}", "red")
            
            self.main_app.root.after(0, update_gui)
                
            # Mostrar resumen
            self._mostrar_resumen_operaciones_rl()
            self._queue_log_update("✅ Procesamiento de señales RL completado", "green")

        except Exception as e:
            self._queue_log_update(f"Error en procesamiento RL: {str(e)}", "red")

    def _process_log_queue(self):
        """Procesa la cola de logs de manera asíncrona"""
        try:
            while True:
                try:
                    message, color = self._log_queue.get_nowait()
                    if hasattr(self.main_app, 'log_panel'):
                        self.main_app.log_panel.log(message, color)
                except queue.Empty:
                    break
        except Exception:
            pass
        
        # Programar siguiente procesamiento
        if self._processing_thread and self._processing_thread.is_alive():
            self.main_app.root.after(100, self._process_log_queue)

    def stop_processing(self):
        """Detiene el procesamiento de señales RL"""
        self._stop_processing.set()
        if self._processing_thread and self._processing_thread.is_alive():
            self.main_app.log_panel.log("Deteniendo procesamiento de señales RL...", "orange")

    def _mostrar_resumen_operaciones_rl(self):
        """Muestra un resumen de las operaciones RL realizadas"""
        if not hasattr(self, 'operaciones') or not self.operaciones:
            return
            
        operaciones_completas = [op for op in self.operaciones if 'ganancia' in op]
        
        if operaciones_completas:
            ganancias = [op['ganancia'] for op in operaciones_completas]
            ganancia_total = sum(ganancias)
            porcentaje_total = sum(op['porcentaje_ganancia'] for op in operaciones_completas)
            
            self.main_app.log_panel.log(f"\nRESUMEN RL: {len(operaciones_completas)} operaciones | "
                    f"Ganancia total: {ganancia_total:.5f} | "
                    f"Rendimiento: {porcentaje_total:.2f}%", 
                    "blue" if ganancia_total >= 0 else "red")

            # Resumen monetario con el dinero base introducido
            try:
                if hasattr(self.main_app, 'strategy_handler'):
                    capital_inicial = float(self.main_app.strategy_handler.dinero_ficticio)
                else:
                    capital_inicial = 1000.0
            except Exception:
                capital_inicial = 1000.0

            beneficios_totales = sum(g for g in ganancias if g >= 0)
            perdidas_totales = sum(-g for g in ganancias if g < 0)
            ganancia_neta = beneficios_totales - perdidas_totales
            capital_final = capital_inicial + ganancia_neta

            self.main_app.log_panel.log("="*60, 'white')
            self.main_app.log_panel.log("RESUMEN MONETARIO RL", 'yellow')
            self.main_app.log_panel.log(f"Capital inicial: ${capital_inicial:,.2f}", 'white')
            self.main_app.log_panel.log(f"Beneficios: ${beneficios_totales:,.2f}", 'green')
            self.main_app.log_panel.log(f"Pérdidas: ${perdidas_totales:,.2f}", 'red')
            self.main_app.log_panel.log(f"Resultado neto: ${ganancia_neta:+,.2f}", 'cyan' if ganancia_neta >= 0 else 'orange')
            self.main_app.log_panel.log(f"Capital final: ${capital_final:,.2f}", 'cyan')
            self.main_app.log_panel.log("="*60, 'white')

    def _procesar_senal_rl(self, idx, timestamp, row):
        """Procesa una señal individual RL"""
        signal = self.rl_signals[idx] if idx < len(self.rl_signals) else 0

        if signal == 1:  # Señal de COMPRA
            self._procesar_compra_rl(idx, row, timestamp)
        elif signal == 2:  # Señal de VENTA
            self._procesar_venta_rl(idx, row, timestamp)
        # No mostramos mensaje cuando no hay señal

    def _procesar_compra_rl(self, idx, row, timestamp):
        """Procesa una señal de compra RL"""
        # Mensaje base para logs RL
        try:
            mensaje_base = f"[RL] {timestamp}"
        except Exception:
            mensaje_base = "[RL]"
        # Confirmación por patrones (si disponible): solo comprar si Final_Signal == 1
        if self._pattern_signals is not None:
            patt = int(self._pattern_signals.iloc[idx])
            if patt != 1:
                mensaje = mensaje_base + " | SEÑAL RL: COMPRA NO CONFIRMADA POR PATRONES"
                self._queue_log_update(mensaje, color="gray")
                return

        # Abrir nueva posición (multi-posición permitida)
        pos = {
            'precio': float(row["Close"]),
            'fecha': timestamp,
            'indice': len(self.operaciones)
        }
        self.posiciones_activas.append(pos)

        mensaje = mensaje_base + f" | SEÑAL RL: COMPRA a {row['Close']:.5f} (posiciones activas: {len(self.posiciones_activas)})"
        self._queue_log_update(mensaje, color="green")

        # Registrar operación (apertura)
        self.operaciones.append({
            'tipo': 'compra',
            'precio': float(row["Close"]),
            'fecha': timestamp,
            'signal_idx': idx
        })

    def _procesar_venta_rl(self, idx, row, timestamp):
        """Procesa una señal de venta RL"""
        # Mensaje base para logs RL
        try:
            mensaje_base = f"[RL] {timestamp}"
        except Exception:
            mensaje_base = "[RL]"
        if not self.posiciones_activas:
            mensaje = mensaje_base + " | SEÑAL RL: VENTA IGNORADA (no hay posiciones activas)"
            self._queue_log_update(mensaje, color="orange")
            return

        # Confirmación por patrones (si disponible): solo vender si Final_Signal == -1
        if self._pattern_signals is not None:
            patt = int(self._pattern_signals.iloc[idx])
            if patt != -1:
                mensaje = mensaje_base + " | SEÑAL RL: VENTA NO CONFIRMADA POR PATRONES"
                self._queue_log_update(mensaje, color="gray")
                return

        precio_venta = float(row["Close"])
        # Cerrar todas las posiciones activas al precio actual
        cerradas = 0
        for pos in list(self.posiciones_activas):
            precio_compra = float(pos['precio'])
            ganancia = precio_venta - precio_compra
            porcentaje_ganancia = (ganancia / precio_compra) * 100 if precio_compra != 0 else 0.0

            color, msg_gan = self._formatear_resultado_rl(ganancia, porcentaje_ganancia)
            msg = (f"{mensaje_base} | SEÑAL RL: VENTA a {precio_venta:.5f} | "
                   f"Compra: {precio_compra:.5f} | {msg_gan}")
            self._queue_log_update(msg, color=color)

            # Actualizar operación correspondiente a esta compra (por indice)
            if pos['indice'] < len(self.operaciones):
                self.operaciones[pos['indice']].update({
                    'venta_precio': precio_venta,
                    'venta_fecha': timestamp,
                    'ganancia': ganancia,
                    'porcentaje_ganancia': porcentaje_ganancia
                })

            self.posiciones_activas.remove(pos)
            cerradas += 1

        if cerradas > 0:
            self._queue_log_update(f"Cerradas {cerradas} posiciones", color="blue")

    def _formatear_resultado_rl(self, ganancia, porcentaje):
        """Formatea el resultado de la operación RL"""
        if ganancia >= 0:
            return "green", f"Ganancia: +{ganancia:.5f} (+{porcentaje:.2f}%)"
        else:
            return "red", f"Pérdida: {ganancia:.5f} ({porcentaje:.2f}%)"

    def _mostrar_resumen_operaciones_rl(self):
        """Muestra un resumen de las operaciones RL realizadas"""
        if not hasattr(self, 'operaciones') or not self.operaciones:
            return
            
        operaciones_completas = [op for op in self.operaciones if 'ganancia' in op]
        
        if operaciones_completas:
            ganancias = [op['ganancia'] for op in operaciones_completas]
            ganancia_total = sum(ganancias)
            porcentaje_total = sum(op['porcentaje_ganancia'] for op in operaciones_completas)
            
            self._queue_log_update(f"\nRESUMEN RL: {len(operaciones_completas)} operaciones | "
                    f"Ganancia total: {ganancia_total:.5f} | "
                    f"Rendimiento: {porcentaje_total:.2f}%", 
                    color="blue" if ganancia_total >= 0 else "red")

            # Resumen monetario con el dinero base introducido
            try:
                if hasattr(self.main_app, 'strategy_handler'):
                    capital_inicial = float(self.main_app.strategy_handler.dinero_ficticio)
                else:
                    capital_inicial = 1000.0
            except Exception:
                capital_inicial = 1000.0

            beneficios_totales = sum(g for g in ganancias if g >= 0)
            perdidas_totales = sum(-g for g in ganancias if g < 0)
            ganancia_neta = beneficios_totales - perdidas_totales
            capital_final = capital_inicial + ganancia_neta

            self._queue_log_update("="*60, color='white')
            self._queue_log_update("RESUMEN MONETARIO RL", color='yellow')
            self._queue_log_update(f"Capital inicial: ${capital_inicial:,.2f}", color='white')
            self._queue_log_update(f"Beneficios: ${beneficios_totales:,.2f}", color='green')
            self._queue_log_update(f"Pérdidas: ${perdidas_totales:,.2f}", color='red')
            self._queue_log_update(f"Resultado neto: ${ganancia_neta:+,.2f}", color='cyan' if ganancia_neta >= 0 else 'orange')
            self._queue_log_update(f"Capital final: ${capital_final:,.2f}", color='cyan')
            self._queue_log_update("="*60, color='white')

    def _queue_log_update(self, message, color):
        """Encola un log para procesamiento asíncrono"""
        try:
            self._log_queue.put((message, color), block=False)
        except queue.Full:
            pass  # Descartar si la cola está llena