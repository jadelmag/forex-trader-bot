# app/handlers/rl_handler.py
import tkinter as tk
from tkinter import messagebox

class RLHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        self._training_active = False
        
    def entrenar_rl(self):
        """Abre modal para entrenar modelo RL"""
        try:
            self._training_active = True
            self._update_menu_states()
            from app.rl_training_modal import RLTrainingModal
            RLTrainingModal(self.main_app.root, self.main_app)
        except Exception as e:
            self._training_active = False
            self._update_menu_states()
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")
            
    def detener_entrenamiento(self):
        """Detiene el entrenamiento de IA activo"""
        self._training_active = False
        self._update_menu_states()
        self.log("Entrenamiento de IA detenido", color='orange')
        
    def _update_menu_states(self):
        """Actualiza los estados de los menús cuando cambia el estado de entrenamiento"""
        if hasattr(self.main_app, 'menu_bar'):
            has_data = hasattr(self.main_app, 'csv_handler') and self.main_app.csv_handler.df_actual is not None
            has_money = hasattr(self.main_app, 'strategy_handler') and self.main_app.strategy_handler.dinero_ficticio > 0
            enable_analysis = has_data and has_money
            self.main_app.menu_bar._update_menu_items_state(enable_analysis)
            
    def cargar_rl(self):
        """Carga un modelo RL existente"""
        self.log("Función de cargar modelo RL no implementada", color='yellow')
        
    def aplicar_senales_rl(self):
        """Aplica señales del modelo RL"""
        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
        self.log("Función de aplicar señales RL no implementada", color='yellow')
        
    def _procesar_senal_rl(self, idx, timestamp, row):
        """Procesa una señal individual RL"""
        try:
            if not hasattr(self, 'rl_signals') or idx >= len(self.rl_signals):
                return
                
            signal = self.rl_signals[idx]
            
            if signal == 1:  # Señal de COMPRA
                self._procesar_compra_rl(idx, row, timestamp)
            elif signal == 2:  # Señal de VENTA
                self._procesar_venta_rl(idx, row, timestamp)
            # No mostramos mensaje cuando no hay señal
        except Exception as e:
            self.log(f"Error procesando señal RL: {str(e)}", color='red')

    def _procesar_compra_rl(self, idx, row, timestamp):
        """Procesa una señal de compra RL"""
        try:
            # Mensaje base para logs RL
            try:
                mensaje_base = f"[RL] {timestamp}"
            except Exception:
                mensaje_base = "[RL]"
                
            # Confirmación por patrones (si disponible): solo comprar si Final_Signal == 1
            if hasattr(self, '_pattern_signals') and self._pattern_signals is not None:
                patt = int(self._pattern_signals.iloc[idx])
                if patt != 1:
                    mensaje = mensaje_base + " | SEÑAL RL: COMPRA NO CONFIRMADA POR PATRONES"
                    self.log(mensaje, color="gray")
                    return

            # Abrir nueva posición (multi-posición permitida)
            if not hasattr(self, 'posiciones_activas'):
                self.posiciones_activas = []
            if not hasattr(self, 'operaciones'):
                self.operaciones = []
                
            pos = {
                'precio': float(row["Close"]),
                'fecha': timestamp,
                'indice': len(self.operaciones)
            }
            self.posiciones_activas.append(pos)

            mensaje = mensaje_base + f" | SEÑAL RL: COMPRA a {row['Close']:.5f} (posiciones activas: {len(self.posiciones_activas)})"
            self.log(mensaje, color="green")

            # Registrar operación (apertura)
            self.operaciones.append({
                'tipo': 'compra',
                'precio': float(row["Close"]),
                'fecha': timestamp,
                'signal_idx': idx
            })
        except Exception as e:
            self.log(f"Error procesando compra RL: {str(e)}", color='red')

    def _procesar_venta_rl(self, idx, row, timestamp):
        """Procesa una señal de venta RL"""
        try:
            # Mensaje base para logs RL
            try:
                mensaje_base = f"[RL] {timestamp}"
            except Exception:
                mensaje_base = "[RL]"
                
            if not hasattr(self, 'posiciones_activas') or not self.posiciones_activas:
                mensaje = mensaje_base + " | SEÑAL RL: VENTA IGNORADA (no hay posiciones activas)"
                self.log(mensaje, color="orange")
                return

            # Confirmación por patrones (si disponible): solo vender si Final_Signal == -1
            if hasattr(self, '_pattern_signals') and self._pattern_signals is not None:
                patt = int(self._pattern_signals.iloc[idx])
                if patt != -1:
                    mensaje = mensaje_base + " | SEÑAL RL: VENTA NO CONFIRMADA POR PATRONES"
                    self.log(mensaje, color="gray")
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
                self.log(msg, color=color)

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
                self.log(f"Cerradas {cerradas} posiciones", color="blue")
                
        except Exception as e:
            self.log(f"Error procesando venta RL: {str(e)}", color='red')

    def _formatear_resultado_rl(self, ganancia, porcentaje):
        """Formatea el resultado de la operación RL"""
        if ganancia >= 0:
            return "green", f"Ganancia: +{ganancia:.5f} (+{porcentaje:.2f}%)"
        else:
            return "red", f"Pérdida: {ganancia:.5f} ({porcentaje:.2f}%)"

    def _mostrar_resumen_operaciones_rl(self):
        """Muestra un resumen de las operaciones RL realizadas"""
        try:
            if not hasattr(self, 'operaciones') or not self.operaciones:
                return
                
            operaciones_completas = [op for op in self.operaciones if 'ganancia' in op]
            
            if operaciones_completas:
                ganancias = [op['ganancia'] for op in operaciones_completas]
                ganancia_total = sum(ganancias)
                porcentaje_total = sum(op['porcentaje_ganancia'] for op in operaciones_completas)
                
                self.log(f"\nRESUMEN RL: {len(operaciones_completas)} operaciones | "
                        f"Ganancia total: {ganancia_total:.5f} | "
                        f"Rendimiento: {porcentaje_total:.2f}%", 
                        color="blue" if ganancia_total >= 0 else "red")

                # Resumen monetario con el dinero base introducido
                try:
                    if hasattr(self.main_app, 'strategy_handler'):
                        capital_inicial = float(self.main_app.strategy_handler.dinero_ficticio)
                    else:
                        capital_inicial = 10000.0
                except Exception:
                    capital_inicial = 10000.0

                beneficios_totales = sum(g for g in ganancias if g >= 0)
                perdidas_totales = sum(-g for g in ganancias if g < 0)
                ganancia_neta = beneficios_totales - perdidas_totales
                capital_final = capital_inicial + ganancia_neta

                self.log("="*60, color='white')
                self.log("RESUMEN MONETARIO RL", color='yellow')
                self.log(f"Capital inicial: ${capital_inicial:,.2f}", color='white')
                self.log(f"Beneficios: ${beneficios_totales:,.2f}", color='green')
                self.log(f"Pérdidas: ${perdidas_totales:,.2f}", color='red')
                self.log(f"Resultado neto: ${ganancia_neta:+,.2f}", color='cyan' if ganancia_neta >= 0 else 'orange')
                self.log(f"Capital final: ${capital_final:,.2f}", color='cyan')
                self.log("="*60, color='white')

                # Actualizar etiquetas de la interfaz
                if hasattr(self.main_app, 'strategy_handler'):
                    self.main_app.strategy_handler.dinero_ficticio = capital_final
                    self.main_app.strategy_handler.beneficios = beneficios_totales
                    self.main_app.strategy_handler.perdidas = perdidas_totales
                    self.main_app.strategy_handler.actualizar_labels()
                    
        except Exception as e:
            self.log(f"Error mostrando resumen RL: {str(e)}", color='red')
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)