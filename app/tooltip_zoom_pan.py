# app/tooltip_zoom_pan.py

from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import tkinter as tk

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
        self.current_event = None

        # Guardar límites iniciales
        self._guardar_zoom_inicial()

        # Conectar eventos - separados para mejor control
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
        """Zoom con scroll del ratón"""
        if event.inaxes != self.grafico.ax:
            return

        scale_factor = 1.1 if event.button == 'up' else 0.9
        xlim = self.grafico.ax.get_xlim()
        ylim = self.grafico.ax.get_ylim()

        # Centro del zoom en la posición del cursor
        x_center = event.xdata
        y_center = event.ydata

        # Aplicar zoom
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor

        self.grafico.ax.set_xlim([
            x_center - new_width / 2,
            x_center + new_width / 2
        ])
        self.grafico.ax.set_ylim([
            y_center - new_height / 2,
            y_center + new_height / 2
        ])

        self.canvas.draw()

    def on_press(self, event):
        """Inicia la selección de área"""
        if event.inaxes != self.grafico.ax:
            return
        
        if event.button == 1:  # Click izquierdo
            self.start_x = event.xdata
            self.start_y = event.ydata
            self.dragging = True
            # Desconectar temporalmente el motion para tooltip durante el drag
            self.canvas.mpl_disconnect(self.cid_motion)
            self.cid_motion = self.canvas.mpl_connect("motion_notify_event", self.on_drag_motion)

    def on_drag_motion(self, event):
        """Maneja el movimiento durante el drag (sin tooltip)"""
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

    def on_motion(self, event):
        """Maneja el movimiento normal (con tooltip)"""
        # Primero verificar si estamos en modo drag
        if self.dragging:
            return
            
        # Luego manejar el tooltip
        self.mostrar_tooltip(event)

    def on_release(self, event):
        """Aplica el zoom al área seleccionada y restaura tooltip"""
        if not self.dragging or event.inaxes != self.grafico.ax:
            return

        self.dragging = False
        self.end_x = event.xdata
        self.end_y = event.ydata

        # Aplicar zoom al área seleccionada solo si hay un área significativa
        if abs(self.end_x - self.start_x) > 5 and abs(self.end_y - self.start_y) > 5:
            x_min = min(self.start_x, self.end_x)
            x_max = max(self.start_x, self.end_x)
            y_min = min(self.start_y, self.end_y)
            y_max = max(self.start_y, self.end_y)

            self.grafico.ax.set_xlim([x_min, x_max])
            self.grafico.ax.set_ylim([y_min, y_max])

        # Limpiar rectángulo
        if self.rect:
            self.rect.remove()
            self.rect = None

        # Restaurar conexión para tooltip
        self.canvas.mpl_disconnect(self.cid_motion)
        self.cid_motion = self.canvas.mpl_connect("motion_notify_event", self.on_motion)

        self.canvas.draw()

    def mostrar_tooltip(self, event):
        """Muestra tooltip con información de la vela"""
        if event.inaxes is None or self.grafico is None or not hasattr(self.grafico, 'data'):
            self._ocultar_tooltip()
            return

        try:
            # Encontrar la vela más cercana a la posición x del cursor
            xdata = event.xdata
            if xdata is None:
                self._ocultar_tooltip()
                return

            # Convertir a índice basado en el rango de tiempo visible
            xlim = self.grafico.ax.get_xlim()
            visible_range = xlim[1] - xlim[0]
            
            # Estimación del índice basado en la posición relativa
            if len(self.grafico.data) > 0:
                rel_position = (xdata - xlim[0]) / visible_range
                index = int(rel_position * len(self.grafico.data))
                index = max(0, min(index, len(self.grafico.data) - 1))
                
                vela = self.grafico.data.iloc[index]
                texto = (
                    f"Fecha: {self.grafico.data.index[index].strftime('%Y-%m-%d %H:%M')}\n"
                    f"Open: {vela['Open']:.5f}\n"
                    f"High: {vela['High']:.5f}\n"
                    f"Low: {vela['Low']:.5f}\n"
                    f"Close: {vela['Close']:.5f}\n"
                    f"Volume: {vela['Volume']:,.0f}"
                )
                self._crear_tooltip(event.guiEvent.x_root + 20, event.guiEvent.y_root + 20, texto)
            else:
                self._ocultar_tooltip()
                
        except (IndexError, ValueError, AttributeError) as e:
            self._ocultar_tooltip()

    def _crear_tooltip(self, x, y, texto):
        """Crea la ventana de tooltip"""
        self._ocultar_tooltip()
        
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{int(x)}+{int(y)}")
        
        label = tk.Label(
            self.tooltip, 
            text=texto, 
            background="lightyellow", 
            relief="solid", 
            borderwidth=1,
            font=("Arial", 9),
            justify="left"
        )
        label.pack(padx=2, pady=2)

    def _ocultar_tooltip(self):
        """Oculta el tooltip"""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def cleanup(self):
        """Limpia todas las conexiones de eventos"""
        for cid in [self.cid_motion, self.cid_scroll, self.cid_press, self.cid_release]:
            try:
                self.canvas.mpl_disconnect(cid)
            except:
                pass