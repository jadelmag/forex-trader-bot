import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
from datetime import datetime
import time


class ChartInteractionManager:
    """
    Clase para manejar la interacción con gráficos de velas japonesas.
    Proporciona funcionalidades de zoom, pan y tooltips interactivos.
    """
    
    def __init__(self, canvas, ax, data=None):
        """
        Inicializa el gestor de interacciones del gráfico.
        
        Args:
            canvas: Canvas de matplotlib
            ax: Axes del gráfico
            data: DataFrame con datos de velas (opcional)
        """
        self.canvas = canvas
        self.ax = ax
        self.data = data
        
        # Estado del zoom y pan
        self.original_xlim = None
        self.original_ylim = None
        self.zoom_factor = 1.1
        
        # Estado del mouse
        self.mouse_pressed = False
        self.pan_start = None
        self.zoom_start = None
        self.last_click_time = 0
        self.double_click_threshold = 0.5  # segundos
        
        # Rectángulo de selección para zoom
        self.zoom_rect = None
        self.zoom_rect_start = None
        
        # Tooltip
        self.tooltip = None
        self.tooltip_line = None
        
        # Conectar eventos
        self._connect_events()
        
        # Guardar límites originales
        self._save_original_limits()
    
    def _connect_events(self):
        """Conecta todos los eventos del mouse al canvas."""
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.canvas.mpl_connect('button_press_event', self._on_button_press)
        self.canvas.mpl_connect('button_release_event', self._on_button_release)
        motion_id = self.canvas.mpl_connect('motion_notify_event', self._on_motion)
    
    def _save_original_limits(self):
        """Guarda los límites originales del gráfico."""
        self.original_xlim = self.ax.get_xlim()
        self.original_ylim = self.ax.get_ylim()
    
    def _on_scroll(self, event):
        """
        Maneja el evento de scroll del mouse (zoom in/out).
        Botón de enmedio hacia arriba = zoom in, hacia abajo = zoom out.
        """
        if event.inaxes != self.ax:
            return
        
        # Determinar dirección del zoom
        if event.button == 'up':
            scale_factor = 1 / self.zoom_factor
        elif event.button == 'down':
            scale_factor = self.zoom_factor
        else:
            return
        
        # Obtener límites actuales
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Calcular nuevo zoom centrado en la posición del mouse
        xdata, ydata = event.xdata, event.ydata
        
        # Calcular nuevos límites
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        
        new_x_range = x_range * scale_factor
        new_y_range = y_range * scale_factor
        
        # Centrar el zoom en la posición del mouse
        x_center_ratio = (xdata - xlim[0]) / x_range
        y_center_ratio = (ydata - ylim[0]) / y_range
        
        new_xlim = [
            xdata - new_x_range * x_center_ratio,
            xdata + new_x_range * (1 - x_center_ratio)
        ]
        new_ylim = [
            ydata - new_y_range * y_center_ratio,
            ydata + new_y_range * (1 - y_center_ratio)
        ]
        
        # Aplicar nuevos límites
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw_idle()
    
    def _on_button_press(self, event):
        """Maneja los eventos de presionar botones del mouse."""
        if event.inaxes != self.ax:
            return
        
        current_time = time.time()
        
        # Botón de enmedio - detectar doble click para reset zoom
        if event.button == 2:  # Botón de enmedio
            if current_time - self.last_click_time < self.double_click_threshold:
                self._reset_zoom()
            self.last_click_time = current_time
        
        # Botón izquierdo - iniciar selección de zoom
        elif event.button == 1:  # Botón izquierdo
            self.zoom_start = (event.xdata, event.ydata)
            self.mouse_pressed = True
        
        # Botón derecho - iniciar pan
        elif event.button == 3:  # Botón derecho
            self.pan_start = (event.xdata, event.ydata)
            self.mouse_pressed = True
    
    def _on_button_release(self, event):
        """Maneja los eventos de soltar botones del mouse."""
        if not self.mouse_pressed:
            return
        
        # Botón izquierdo - finalizar zoom de selección
        if event.button == 1 and self.zoom_start:
            # Aplicar zoom ANTES de limpiar el rectángulo
            zoom_applied = self._finish_zoom_selection(event)
            
            # Limpiar rectángulo de zoom
            if self.zoom_rect:
                self.zoom_rect.remove()
                self.zoom_rect = None
                # Solo redibujar si no se aplicó zoom (para evitar doble redibujado)
                if not zoom_applied:
                    self.canvas.draw_idle()
        
        # Limpiar estado
        self.mouse_pressed = False
        self.pan_start = None
        self.zoom_start = None
    
    def _on_motion(self, event):
        """Maneja el movimiento del mouse."""
        if event.inaxes != self.ax:
            return
        
        # Si el mouse está presionado
        if self.mouse_pressed:
            # Pan con botón derecho
            if self.pan_start and event.button == 3:
                self._handle_pan(event)
            
            # Zoom de selección con botón izquierdo
            elif self.zoom_start and event.button == 1:
                self._handle_zoom_selection(event)
        
        # Tooltip en hover (solo si no hay botones presionados)
        else:
            self._handle_tooltip(event)
    
    def _reset_zoom(self):
        """Resetea el zoom a la vista original."""
        if self.original_xlim and self.original_ylim:
            self.ax.set_xlim(self.original_xlim)
            self.ax.set_ylim(self.original_ylim)
            self.canvas.draw_idle()
    
    def _handle_pan(self, event):
        """Maneja el paneo del gráfico con botón derecho."""
        if not self.pan_start:
            return
        
        # Calcular desplazamiento
        dx = event.xdata - self.pan_start[0]
        dy = event.ydata - self.pan_start[1]
        
        # Obtener límites actuales
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Aplicar desplazamiento
        self.ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
        self.ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
        
        self.canvas.draw_idle()
    
    def _handle_zoom_selection(self, event):
        """Maneja la selección de área para zoom con botón izquierdo."""
        if not self.zoom_start:
            return
        
        # Limpiar rectángulo anterior
        if self.zoom_rect:
            self.zoom_rect.remove()
        
        # Calcular dimensiones del rectángulo
        x_start, y_start = self.zoom_start
        width = event.xdata - x_start
        height = event.ydata - y_start
        
        # Crear rectángulo con líneas discontinuas grises
        self.zoom_rect = Rectangle(
            (x_start, y_start), width, height,
            linewidth=1.5,
            edgecolor='gray',
            facecolor='none',
            linestyle='--',
            alpha=0.7
        )
        
        self.ax.add_patch(self.zoom_rect)
        self.canvas.draw_idle()
    
    def _finish_zoom_selection(self, event):
        """Finaliza la selección de zoom y aplica el nuevo zoom."""
        if not self.zoom_start or not event.xdata or not event.ydata:
            return False
        
        x_start, y_start = self.zoom_start
        x_end, y_end = event.xdata, event.ydata
        
        # Obtener límites actuales para calcular área mínima relativa
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()
        x_range = current_xlim[1] - current_xlim[0]
        y_range = current_ylim[1] - current_ylim[0]
        
        # Área mínima relativa (1% del rango actual)
        min_x_area = x_range * 0.01
        min_y_area = y_range * 0.01
        
        # Asegurar que tenemos un área válida
        if abs(x_end - x_start) < min_x_area or abs(y_end - y_start) < min_y_area:
            return False
        
        # Determinar límites del zoom
        xlim = [min(x_start, x_end), max(x_start, x_end)]
        ylim = [min(y_start, y_end), max(y_start, y_end)]
        
        # Aplicar zoom
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.canvas.draw_idle()
        return True
    
    def _handle_tooltip(self, event):
        """Maneja el tooltip al hacer hover sobre las velas."""
        if self.data is not None and len(self.data) > 0:
            self._show_candle_tooltip(event)
        else:
            self._hide_tooltip()
    
    def _show_candle_tooltip(self, event):
        """Muestra tooltip con información de la vela."""
        if event.xdata is None or event.ydata is None:
            self._hide_tooltip()
            return
        
        try:
            # Encontrar la vela más cercana - mapear coordenadas del gráfico al índice de datos
            xlim = self.ax.get_xlim()
            data_range = len(self.data)
            
            # Mapear la posición x del mouse al índice del DataFrame
            if xlim[1] != xlim[0]:  # Evitar división por cero
                # Normalizar la posición x al rango [0, 1]
                normalized_x = (event.xdata - xlim[0]) / (xlim[1] - xlim[0])
                # Mapear al índice de datos
                x_pos = int(round(normalized_x * (data_range - 1)))
            else:
                x_pos = 0
            
            # Verificar si está dentro del rango de datos
            if x_pos < 0 or x_pos >= len(self.data):
                self._hide_tooltip()
                return
            
            # Obtener datos de la vela - manejar tanto DataFrame con índice como sin índice
            if hasattr(self.data, 'iloc'):
                candle_data = self.data.iloc[x_pos]
            else:
                self._hide_tooltip()
                return
            
            # Crear información del tooltip
            tooltip_info = self._format_tooltip_text(candle_data, x_pos)
            
            # Mostrar tooltip
            self._display_tooltip(event.xdata, event.ydata, tooltip_info)
            
        except (IndexError, AttributeError, KeyError, ValueError) as e:
            self._hide_tooltip()
    
    def _format_tooltip_text(self, candle_data, index):
        """Formatea el texto del tooltip con información de la vela."""
        try:
            # Intentar obtener timestamp si existe
            if hasattr(candle_data, 'name') and candle_data.name is not None:
                if isinstance(candle_data.name, (pd.Timestamp, datetime)):
                    timestamp = candle_data.name.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp = str(candle_data.name)
            else:
                timestamp = f"Vela #{index}"
            
            # Obtener valores OHLC - intentar múltiples variaciones de nombres de columnas
            open_val = 'N/A'
            high_val = 'N/A'
            low_val = 'N/A'
            close_val = 'N/A'
            
            # Intentar diferentes nombres de columnas
            for open_name in ['Open', 'open', 'OPEN', 'o']:
                if hasattr(candle_data, open_name):
                    open_val = getattr(candle_data, open_name)
                    break
            
            for high_name in ['High', 'high', 'HIGH', 'h']:
                if hasattr(candle_data, high_name):
                    high_val = getattr(candle_data, high_name)
                    break
                    
            for low_name in ['Low', 'low', 'LOW', 'l']:
                if hasattr(candle_data, low_name):
                    low_val = getattr(candle_data, low_name)
                    break
                    
            for close_name in ['Close', 'close', 'CLOSE', 'c']:
                if hasattr(candle_data, close_name):
                    close_val = getattr(candle_data, close_name)
                    break
            
            # Formatear valores y determinar colores
            def format_price_with_color(val):
                if val == 'N/A':
                    return val, 'black'
                try:
                    return f"{float(val):.5f}", 'black'
                except:
                    return str(val), 'black'
            
            # Determinar color solo para el precio de cierre
            close_color = 'black'  # Color por defecto
            if close_val != 'N/A' and open_val != 'N/A':
                try:
                    close_float = float(close_val)
                    open_float = float(open_val)
                    if close_float > open_float:
                        close_color = 'green'
                    elif close_float < open_float:
                        close_color = 'red'
                    else:
                        close_color = 'gray'
                except:
                    close_color = 'black'
            
            # Crear texto con información de colores
            tooltip_info = {
                'timestamp': timestamp,
                'open': format_price_with_color(open_val)[0],
                'high': format_price_with_color(high_val)[0], 
                'low': format_price_with_color(low_val)[0],
                'close': format_price_with_color(close_val)[0],
                'close_color': close_color
            }
            
            # Agregar volumen si existe
            volume = getattr(candle_data, 'Volume', getattr(candle_data, 'volume', None))
            if volume is not None:
                tooltip_info['volume'] = str(volume)
            
            return tooltip_info
            
        except Exception as e:
            return {'error': f"Vela #{index}\nError: {str(e)}", 'close_color': 'black'}
    
    def _display_tooltip(self, x, y, tooltip_info):
        """Muestra el tooltip en la posición especificada."""
        try:
            # Limpiar tooltip anterior
            self._hide_tooltip()
            
            # Crear línea vertical en la posición del mouse
            self.tooltip_line = self.ax.axvline(x, color='gray', linestyle=':', alpha=0.7, linewidth=1)
            
            # Manejar caso de error
            if 'error' in tooltip_info:
                text = tooltip_info['error']
                text_color = 'black'
                border_color = 'gray'
            else:
                # Construir texto - todo en negro excepto el cierre
                close_color = tooltip_info['close_color']
                
                lines = [
                    f"Tiempo: {tooltip_info['timestamp']}",
                    f"Apertura: {tooltip_info['open']}",
                    f"Máximo: {tooltip_info['high']}",
                    f"Mínimo: {tooltip_info['low']}",
                    f"Cierre: {tooltip_info['close']}"
                ]
                
                if 'volume' in tooltip_info:
                    lines.append(f"Volumen: {tooltip_info['volume']}")
                
                text = '\n'.join(lines)
                text_color = 'black'  # Todo el texto en negro
                border_color = close_color  # Solo el borde refleja el color del cierre
            
            # Crear tooltip con padding aumentado
            bbox_props = dict(
                boxstyle="round,pad=0.6",
                facecolor='lightyellow',
                edgecolor=border_color,
                alpha=0.95,
                linewidth=2
            )
            
            # Posicionar tooltip
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            # Determinar posición del tooltip (evitar que se salga del gráfico)
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            
            if x > xlim[0] + x_range * 0.7:  # Si está muy a la derecha
                tooltip_x = x - x_range * 0.02
            else:
                tooltip_x = x + x_range * 0.02
            
            if y > ylim[0] + y_range * 0.7:  # Si está muy arriba
                va = 'top'
                tooltip_y = y - y_range * 0.02
            else:
                va = 'bottom'
                tooltip_y = y + y_range * 0.02
            
            self.tooltip = self.ax.text(
                tooltip_x, tooltip_y, text,
                bbox=bbox_props,
                fontsize=8,
                ha='left',
                va=va,
                zorder=1000,
                linespacing=1.3,
                family='monospace',
                color=text_color
            )
            
            self.canvas.draw_idle()
        except Exception:
            pass
    
    def _hide_tooltip(self):
        """Oculta el tooltip actual."""
        try:
            if self.tooltip:
                self.tooltip.remove()
                self.tooltip = None
            
            if self.tooltip_line:
                self.tooltip_line.remove()
                self.tooltip_line = None
        except Exception:
            pass
    
    def set_data(self, data):
        """
        Establece los datos para el tooltip.
        
        Args:
            data: DataFrame con datos de velas
        """
        self.data = data
    
    def update_limits(self):
        """Actualiza los límites originales (llamar después de cambiar datos)."""
        self._save_original_limits()
    
    def cleanup(self):
        """Limpia recursos y desconecta eventos."""
        self._hide_tooltip()
        if self.zoom_rect:
            self.zoom_rect.remove()
            self.zoom_rect = None