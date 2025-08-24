# app/tooltip_zoom_pan.py

from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import tkinter as tk
import numpy as np
from datetime import datetime

class TooltipZoomPan:
    def __init__(self, root, canvas, grafico):
        self.root = root
        self.canvas = canvas
        self.grafico = grafico
        self.tooltip = None
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.zoom_initial = None
        self.dragging = False

        # Guardar límites iniciales
        self._guardar_zoom_inicial()

        # Conectar eventos
        self.cid_motion = self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.cid_scroll = self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.cid_press = self.canvas.mpl_connect("button_press_event", self.on_press)
        self.cid_release = self.canvas.mpl_connect("button_release_event", self.on_release)

    def _guardar_zoom_inicial(self):
        """Guarda los límites iniciales del gráfico"""
        if self.grafico and hasattr(self.grafico, 'ax'):
            self.zoom_initial = {
                'xlim': self.grafico.ax.get_xlim(),
                'ylim': self.grafico.ax.get_ylim()
            }

    def reset_zoom(self):
        """Restaura el zoom inicial"""
        if self.zoom_initial and self.grafico and hasattr(self.grafico, 'ax'):
            self.grafico.ax.set_xlim(self.zoom_initial['xlim'])
            self.grafico.ax.set_ylim(self.zoom_initial['ylim'])
            self.canvas.draw()

    def on_scroll(self, event):
        """Zoom centrado en la posición del puntero"""
        if event.inaxes != self.grafico.ax or event.xdata is None or event.ydata is None:
            return

        # Factor de zoom
        scale_factor = 1.1 if event.button == 'up' else 0.9

        # Límites actuales
        xlim = self.grafico.ax.get_xlim()
        ylim = self.grafico.ax.get_ylim()

        # Posición del cursor
        x_center = event.xdata
        y_center = event.ydata

        # Nuevo ancho y alto del zoom
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor

        # Ajustar límites manteniendo el cursor como centro
        x_min = x_center - (x_center - xlim[0]) * scale_factor
        x_max = x_center + (xlim[1] - x_center) * scale_factor
        y_min = y_center - (y_center - ylim[0]) * scale_factor
        y_max = y_center + (ylim[1] - y_center) * scale_factor

        self.grafico.ax.set_xlim([x_min, x_max])
        self.grafico.ax.set_ylim([y_min, y_max])
        self.canvas.draw_idle()

    def on_press(self, event):
        """Inicia la selección de área"""
        if event.inaxes != self.grafico.ax:
            return
        
        if event.button == 1:  # Click izquierdo
            self.start_x = event.xdata
            self.start_y = event.ydata
            self.dragging = True
            self._ocultar_tooltip()  # Ocultar tooltip durante el drag

    def on_motion(self, event):
        """Maneja tanto el tooltip como el drag"""
        if self.dragging:
            self.on_drag_motion(event)
        else:
            self.mostrar_tooltip(event)

    def on_drag_motion(self, event):
        """Maneja el movimiento durante el drag"""
        if not self.dragging or event.inaxes != self.grafico.ax:
            return

        # Eliminar rectángulo anterior si existe
        if self.rect:
            self.rect.remove()
            self.rect = None

        # Crear nuevo rectángulo
        self.end_x = event.xdata
        self.end_y = event.ydata

        width = abs(self.end_x - self.start_x)
        height = abs(self.end_y - self.start_y)
        x = min(self.start_x, self.end_x)
        y = min(self.start_y, self.end_y)

        self.rect = Rectangle(
            (x, y), width, height,
            fill=False, edgecolor='gray', linestyle='--', linewidth=1, alpha=0.7
        )
        self.grafico.ax.add_patch(self.rect)
        self.canvas.draw()

    def on_release(self, event):
        """Aplica el zoom al área seleccionada"""
        if not self.dragging or event.inaxes != self.grafico.ax:
            return

        self.dragging = False
        self.end_x = event.xdata
        self.end_y = event.ydata

        # Verificar que ambos puntos estén definidos
        if self.start_x is None or self.start_y is None or self.end_x is None or self.end_y is None:
            return

        # Calcular límites del área seleccionada
        x_min = min(self.start_x, self.end_x)
        x_max = max(self.start_x, self.end_x)
        y_min = min(self.start_y, self.end_y)
        y_max = max(self.start_y, self.end_y)

        # Evitar zoom con área demasiado pequeña
        if abs(x_max - x_min) < 1e-6 or abs(y_max - y_min) < 1e-6:
            if self.rect:
                self.rect.remove()
                self.rect = None
            self.canvas.draw_idle()
            return

        # Aplicar límites al gráfico
        self.grafico.ax.set_xlim([x_min, x_max])
        self.grafico.ax.set_ylim([y_min, y_max])

        # Limpiar rectángulo
        if self.rect:
            self.rect.remove()
            self.rect = None

        self.canvas.draw_idle()

    def mostrar_tooltip(self, event):
        """Muestra tooltip con información de la vela"""
        if (event.inaxes is None or self.grafico is None or 
            not hasattr(self.grafico, 'data') or self.grafico.data is None or
            self.grafico.data.empty):
            self._ocultar_tooltip()
            return

        try:
            # Convertir la fecha del evento a timestamp
            event_time = event.xdata
            if event_time is None:
                self._ocultar_tooltip()
                return

            # Encontrar la vela más cercana usando las fechas del índice
            if hasattr(self.grafico.data.index, 'view'):
                # Convertir fechas a numéricas para comparación
                dates_numeric = self.grafico.data.index.view('int64') / 1e9  # Convertir nanosegundos a segundos
                
                # Encontrar el índice más cercano
                idx = np.abs(dates_numeric - event_time).argmin()
                
                if idx < len(self.grafico.data):
                    vela = self.grafico.data.iloc[idx]
                    fecha = self.grafico.data.index[idx]
                    
                    texto = (
                        f"Fecha: {fecha.strftime('%Y-%m-%d %H:%M')}\n"
                        f"Open: {vela['Open']:.5f}\n"
                        f"High: {vela['High']:.5f}\n"
                        f"Low: {vela['Low']:.5f}\n"
                        f"Close: {vela['Close']:.5f}\n"
                        f"Volume: {vela['Volume']:,.0f}"
                    )
                    self._crear_tooltip(event.guiEvent.x_root + 20, event.guiEvent.y_root + 20, texto)
                    return
                    
        except Exception as e:
            print(f"Error en tooltip: {e}")
        
        self._ocultar_tooltip()

    def _crear_tooltip(self, x, y, texto):
        """Crea la ventana de tooltip"""
        self._ocultar_tooltip()
        
        try:
            self.tooltip = tk.Toplevel(self.root)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{int(x)}+{int(y)}")
            self.tooltip.wm_attributes("-topmost", True)
            
            label = tk.Label(
                self.tooltip, 
                text=texto, 
                background="lightyellow", 
                relief="solid", 
                borderwidth=1,
                font=("Consolas", 8),
                justify="left"
            )
            label.pack(padx=3, pady=3)
        except Exception as e:
            print(f"Error creando tooltip: {e}")

    def _ocultar_tooltip(self):
        """Oculta el tooltip"""
        if self.tooltip:
            try:
                self.tooltip.destroy()
            except:
                pass
            finally:
                self.tooltip = None

    def cleanup(self):
        """Limpia todas las conexiones de eventos"""
        try:
            self.canvas.mpl_disconnect(self.cid_motion)
            self.canvas.mpl_disconnect(self.cid_scroll)
            self.canvas.mpl_disconnect(self.cid_press)
            self.canvas.mpl_disconnect(self.cid_release)
        except:
            pass