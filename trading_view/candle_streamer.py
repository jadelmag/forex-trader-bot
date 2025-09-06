# trandig-view/candle-streamer.py

import json
import websocket
import threading
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib.patches import Rectangle
import os
import requests
import tkinter as tk
import time

URL = "wss://stream.binance.com:9443/ws"
DEFAULT_INTERVAL = '1m'
DEFAULT_MAX_PLOT = 500

class CandleStreamer:
    ALLOWED_INTERVALS = ['1s','5s','10s','20s','30s','40s','50s','1m','2m','3m','4m','5m','6m','7m','8m','9m','10m']
    ALLOWED_MAX_PLOT = [100, 200, 300, 400, 500, 700, 1000, 1500, 2000]

    def __init__(self, interval: str = DEFAULT_INTERVAL, max_plot: int = DEFAULT_MAX_PLOT, 
                 base_folder: str = 'trading_view', parent_frame=None, log_callback=None):
        # Callback para logging
        self.log_callback = log_callback if callable(log_callback) else print
        self.debug_mode = False  # Flag para modo debug

        # Validar interval
        if interval not in self.ALLOWED_INTERVALS:
            self._log(f'Intervalo inválido. Se asigna por defecto: 1m', 'yellow')
            self.interval = DEFAULT_INTERVAL
        else:
            self.interval = interval

        # Validar max_plot
        if max_plot not in self.ALLOWED_MAX_PLOT:
            self._log(f'max_plot inválido. Se asigna por defecto: 500', 'yellow')
            self.max_plot = DEFAULT_MAX_PLOT
        else:
            self.max_plot = max_plot

        self.url = URL
        self.ws = None
        self.thread = None
        self.running = False
        
        # WebSocket reconnection parameters
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 1  # Initial delay in seconds
        self.max_reconnect_delay = 300  # Maximum delay (5 minutes)
        self.reconnect_thread = None

        # DataFrame inicial con DatetimeIndex
        self.df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        self.df.index.name = 'Date'
        self.df.index = pd.to_datetime(self.df.index)

        self.current_candle = None
        # Suscriptores de actualización de velas (GUI puede registrarse)
        self._candle_update_callbacks = []

        # Obtener símbolos desde archivo o API
        self.symbols = self._load_or_fetch_symbols()
        self.symbol = self.symbols[0] if self.symbols else None

        # Carpeta y CSV para velas
        self.base_folder = base_folder
        self.csv_folder = os.path.join(self.base_folder, 'trade_view_csv')
        os.makedirs(self.csv_folder, exist_ok=True)
        self.csv_file = os.path.join(self.csv_folder, f'{self.symbol}_data.csv')

        # Configuración de matplotlib
        self.parent_frame = parent_frame
        plt.ion()
        
        # Variables para refresco periódico
        self._last_refresh_time = 0
        self._refresh_interval = 1.0  # 1 segundo
        self._pending_refresh = False
        
        # Si se proporciona un frame padre, usamos FigureCanvasTkAgg
        if self.parent_frame:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            
            # Crear figura de matplotlib
            self.fig = Figure(figsize=(8, 6), dpi=100)
            
            # Configurar subplots con el layout de mplfinance
            gs = self.fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.08)
            ax1 = self.fig.add_subplot(gs[0])
            ax2 = self.fig.add_subplot(gs[1], sharex=ax1)
            # Guardar referencias claras a los ejes de precio y volumen
            self.ax_price = ax1
            self.ax_volume = ax2
            
            # Crear el canvas de Tkinter
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            # Comportamiento original si no hay frame padre
            self.fig, self.axlist = mpf.plot(
                self.df,
                type='candle',
                style='charles',
                volume=True,
                returnfig=True
            )
            # Cuando mplfinance devuelve la lista de ejes, el índice 0 es precio y 2 es volumen
            if isinstance(self.axlist, (list, tuple)) and len(self.axlist) >= 3:
                self.ax_price = self.axlist[0]
                self.ax_volume = self.axlist[2]

        # Estado para tooltips de hover
        self._last_df = pd.DataFrame()
        self._last_x = None  # posiciones x (mdates float) del último DF
        self._hover_annot = None
        self._hover_cid = None
        self.debug_hover = False  # activar para logs de eventos de hover
        self._hover_marker = None  # marcador visual en la vela
        # Zoom con scroll
        self._scroll_cid = None
        self._user_xlim = None  # conservar límites de zoom del usuario
        # Pan con arrastre
        self._press_cid = None
        self._release_cid = None
        self._pan_active = False          # pan con botón derecho
        self._pan_start_x = None
        self._pan_xlim_start = None
        # Zoom por recuadro (botón izquierdo)
        self._rect_active = False
        self._rect_start = None  # (x0, y0) en coords de datos
        self._rect_patch = None
        self._init_hover()

    def set_debug_mode(self, debug: bool):
        """Activa o desactiva el modo debug"""
        self.debug_mode = debug
        self._log(f"Modo debug {'activado' if debug else 'desactivado'}", 'blue')

    def on_candle_update(self, callback):
        """Permite registrar un callback que será llamado con el DataFrame
        de velas cada vez que haya una actualización (incluye la vela en curso).
        """
        try:
            if callable(callback) and callback not in self._candle_update_callbacks:
                self._candle_update_callbacks.append(callback)
        except Exception as e:
            if self.debug_mode:
                self._log(f"Error registrando callback: {e}", 'red')

    def _notify_candle_update(self):
        """Notifica a los suscriptores entregando un DataFrame que incluye la vela
        actual (si existe)."""
        try:
            df_current = self.df.copy()
            if self.current_candle is not None:
                cur = pd.DataFrame([self.current_candle]).set_index('Date')
                df_current = pd.concat([df_current, cur])
                if not df_current.empty:
                    df_current.sort_index(inplace=True)
            for cb in list(self._candle_update_callbacks):
                try:
                    cb(df_current)
                except Exception as e:
                    # No romper si un callback falla
                    if self.debug_mode:
                        self._log(f"Error en callback de actualización: {e}", 'red')
        except Exception as e:
            if self.debug_mode:
                self._log(f"Error en notificación de vela: {e}", 'red')

    @classmethod
    def _load_or_fetch_symbols(cls):
        symbols_folder = 'symbols'
        os.makedirs(symbols_folder, exist_ok=True)
        symbols_file = os.path.join(symbols_folder, 'symbols.csv')

        # Intentar cargar desde CSV
        if os.path.exists(symbols_file):
            try:
                df = pd.read_csv(symbols_file)
                symbols = df['symbol'].tolist()
                if symbols:
                    # Mover EURUSDT al principio si existe
                    if 'EURUSDT' in symbols:
                        symbols.remove('EURUSDT')
                        symbols = ['EURUSDT', '----------'] + sorted(symbols)
                    return symbols
            except Exception as e:
                print(f"Error leyendo symbols.csv: {e}")

        # Si no existe o falla, obtener desde API y guardar
        try:
            url = "https://api.binance.com/api/v3/exchangeInfo"
            response = requests.get(url)
            data = response.json()
            symbols = [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING']
            
            # Mover EURUSDT al principio si existe
            if 'EURUSDT' in symbols:
                symbols.remove('EURUSDT')
                symbols = ['EURUSDT', '----------'] + sorted(symbols)
            
            # Guardar en CSV
            df = pd.DataFrame(symbols, columns=['symbol'])
            df.to_csv(symbols_file, index=False)
            return symbols
        except Exception as e:
            print(f"Error obteniendo símbolos desde API: {e}")
            return []

    def _add_trade_to_candle(self, trade_price, trade_volume, trade_time):
        try:
            interval_seconds = int(self.interval[:-1]) if self.interval[-1] == 's' else int(self.interval[:-1]) * 60
            interval_start = trade_time - timedelta(seconds=trade_time.second % interval_seconds,
                                                  microseconds=trade_time.microsecond)

            if self.debug_mode:
                self._log(f"Intervalo actual: {self.interval}, Inicio del intervalo: {interval_start}", 'gray')
            
            if self.current_candle is None or self.current_candle['Date'] != interval_start:
                if self.current_candle is not None:
                    if self.debug_mode:
                        self._log(f"Nueva vela creada: {self.current_candle}", 'green')
                    new_candle = pd.DataFrame([self.current_candle])
                    new_candle.set_index('Date', inplace=True)
                    # Evitar FutureWarning: no concatenar con DataFrame vacío
                    if self.df.empty:
                        self.df = new_candle.copy()
                    else:
                        self.df = pd.concat([self.df, new_candle])
                    if self.debug_mode:
                        self._log(f"DataFrame actualizado. Total de velas: {len(self.df)}", 'gray')
                    self._update_csv()

                self.current_candle = {
                    'Date': interval_start,
                    'Open': trade_price,
                    'High': trade_price,
                    'Low': trade_price,
                    'Close': trade_price,
                    'Volume': trade_volume
                }
                if self.debug_mode:
                    self._log(f"Nueva vela iniciada: {self.current_candle}", 'green')
                # Programar refresco del gráfico en lugar de refrescar inmediatamente
                self._schedule_refresh()
                # Notificar actualización de vela
                self._notify_candle_update()
            else:
                prev_high = self.current_candle['High']
                prev_low = self.current_candle['Low']
                prev_volume = self.current_candle['Volume']
                
                self.current_candle['High'] = max(prev_high, trade_price)
                self.current_candle['Low'] = min(prev_low, trade_price)
                self.current_candle['Close'] = trade_price
                self.current_candle['Volume'] += trade_volume
                
                if self.debug_mode and (prev_high != self.current_candle['High'] or 
                    prev_low != self.current_candle['Low'] or 
                    prev_volume != self.current_candle['Volume']):
                    self._log(f"Vela actualizada: {self.current_candle}", 'gray')
                # Programar refresco del gráfico
                self._schedule_refresh()
                # Notificar actualización intra-intervalo
                self._notify_candle_update()
        except Exception as e:
            self._log(f"Error en _add_trade_to_candle: {e}", 'red')

    def _schedule_refresh(self):
        """Programa un refresco del gráfico si no hay uno pendiente"""
        if not self._pending_refresh:
            self._pending_refresh = True
            current_time = time.time()
            if current_time - self._last_refresh_time >= self._refresh_interval:
                self._refresh_plot()
            elif self.parent_frame:
                # Usar after() para refrescar en el futuro
                delay = int((self._refresh_interval - (current_time - self._last_refresh_time)) * 1000)
                self.parent_frame.after(max(10, delay), self._refresh_plot)

    def _refresh_plot(self):
        """Refresca el gráfico y reinicia el temporizador"""
        if self._pending_refresh:
            self._plot_last_candles()
            self._pending_refresh = False
            self._last_refresh_time = time.time()

    def _plot_last_candles(self):
        # Construir DataFrame a plotear incluyendo la vela en curso (si existe)
        last_df = self.df.tail(self.max_plot).copy()
        if self.current_candle is not None:
            temp = pd.DataFrame([self.current_candle]).set_index('Date')
            last_df = pd.concat([last_df, temp])
        # Asegurar orden por fecha
        if not last_df.empty:
            last_df.sort_index(inplace=True)

        # Si solo hay 1 fila, mplfinance puede no dibujar nada (ancho cero). Añadimos un punto ficticio.
        if len(last_df) == 1:
            try:
                idx = last_df.index[0]
                # Calcular delta temporal desde el intervalo
                secs = int(self.interval[:-1]) if self.interval[-1] == 's' else int(self.interval[:-1]) * 60
                idx2 = idx + timedelta(seconds=secs)
                row = last_df.iloc[0]
                dummy = pd.DataFrame({
                    'Open': [row['Close']],
                    'High': [row['Close']],
                    'Low': [row['Close']],
                    'Close': [row['Close']],
                    'Volume': [0.0]
                }, index=[idx2])
                last_df = pd.concat([last_df, dummy])
                if self.debug_mode:
                    self._log("Añadido punto ficticio para visualizar la primera vela", 'gray')
            except Exception as e:
                if self.debug_mode:
                    self._log(f"No se pudo añadir punto ficticio: {e}", 'red')

            if self.debug_mode:
                self._log(f"Plotting {len(last_df)} filas", 'gray')

        # Guardar el último DF para el manejo de hover
        self._last_df = last_df
        # Cachear posiciones X en coordenadas de Matplotlib para evitar problemas de zona horaria
        try:
            self._last_x = mdates.date2num(self._last_df.index.to_pydatetime()) if not self._last_df.empty else None
        except Exception:
            self._last_x = None
        
        if last_df.empty:
            return
            
        def _update_plot():
            try:
                # Limpiar los ejes
                if hasattr(self, 'ax_price'):
                    self.ax_price.clear()
                if hasattr(self, 'ax_volume'):
                    self.ax_volume.clear()
                
                # Dibujar el gráfico
                mpf.plot(last_df,
                         type='candle',
                         style='charles',
                         ax=self.ax_price,
                         volume=self.ax_volume,
                         show_nontrading=False)
                
                # Asegurar que la anotación de hover existe tras limpiar/redibujar
                self._ensure_hover_annotation()

                # Restaurar límites de zoom del usuario si existen
                if self._user_xlim is not None:
                    try:
                        self.ax_price.set_xlim(self._user_xlim)
                        if hasattr(self, 'ax_volume') and self.ax_volume:
                            self.ax_volume.set_xlim(self._user_xlim)
                    except Exception:
                        pass

                # Actualizar el canvas si está en modo embebido
                if hasattr(self, 'canvas'):
                    self.canvas.draw()
                else:
                    plt.pause(0.01)
            except Exception as e:
                self._log(f"Error actualizando el gráfico: {e}", 'red')
        
        # Asegurarse de que la actualización del gráfico se haga en el hilo principal
        if hasattr(self, 'parent_frame') and self.parent_frame:
            self.parent_frame.after(0, _update_plot)
        else:
            _update_plot()

    def _init_hover(self):
        """Inicializa el manejo de hover sobre las velas (anotación + evento)."""
        try:
            if not hasattr(self, 'fig'):
                return
            # Conectar evento de movimiento del ratón una sola vez
            if self._hover_cid is None:
                self._hover_cid = self.fig.canvas.mpl_connect('motion_notify_event', self._on_motion)
            # Conectar scroll para zoom
            if self._scroll_cid is None:
                self._scroll_cid = self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
            # Conectar eventos de click para pan
            if self._press_cid is None:
                self._press_cid = self.fig.canvas.mpl_connect('button_press_event', self._on_button_press)
            if self._release_cid is None:
                self._release_cid = self.fig.canvas.mpl_connect('button_release_event', self._on_button_release)
            # Crear (o posponer) la anotación
            self._ensure_hover_annotation()
        except Exception as e:
            self._log(f"Error inicializando hover: {e}", 'red')

    def _ensure_hover_annotation(self):
        """Asegura que la anotación y el marcador de hover existen y están adjuntos al eje.
        Tras un ax.clear() los artistas se eliminan del eje, así que aquí los recreamos o reanudamos.
        """
        try:
            if not hasattr(self, 'ax_price'):
                return

            # --- Anotación ---
            annot_missing = (
                self._hover_annot is None or
                self._hover_annot.axes is None or
                self._hover_annot.axes != self.ax_price or
                # Si fue removida por ax.clear(), ya no estará en los textos del eje
                self._hover_annot not in getattr(self.ax_price, 'texts', [])
            )
            if annot_missing:
                self._hover_annot = self.ax_price.annotate(
                    "",
                    xy=(0, 0),
                    xytext=(15, 15),
                    textcoords="offset points",
                    bbox=dict(
                        boxstyle="round,pad=0.5,rounding_size=0.2",
                        fc="#f8f9fa",
                        ec="#6c757d",
                        alpha=0.95,
                        linewidth=1.0
                    ),
                    arrowprops=dict(
                        arrowstyle="-|>",
                        color="#6c757d",
                        shrinkA=0,
                        shrinkB=5,
                        patchA=None,
                        patchB=None,
                        connectionstyle="arc3,rad=0.3"
                    ),
                    fontsize=9,
                    zorder=100,
                    ha='left',
                    va='bottom',
                    linespacing=1.4
                )
                self._hover_annot.set_visible(False)

            # --- Marcador ---
            marker_missing = (
                self._hover_marker is None or
                self._hover_marker.axes is None or
                self._hover_marker.axes != self.ax_price or
                self._hover_marker not in getattr(self.ax_price, 'lines', [])
            )
            if marker_missing:
                self._hover_marker, = self.ax_price.plot(
                    [], [],
                    marker='o',
                    markersize=8,
                    markerfacecolor='#1f77b4',
                    markeredgecolor='white',
                    markeredgewidth=1.0,
                    alpha=0.9,
                    zorder=99
                )
                self._hover_marker.set_visible(False)
        except Exception as e:
            self._log(f"Error creando anotación de hover: {e}", 'red')

    def _on_motion(self, event):
        """Maneja hover, pan (botón derecho) y dibujo de recuadro para zoom (botón izquierdo)."""
        try:
            # Requiere eje de precio y datos
            if not hasattr(self, 'ax_price') or self._last_df is None or self._last_df.empty:
                return
            # Mostrar sólo si el ratón está sobre el eje de precio o volumen
            if (event.inaxes not in (self.ax_price, getattr(self, 'ax_volume', None)) or
                event.xdata is None or event.ydata is None):
                # Ocultar si estaba visible
                if self._hover_annot is not None and self._hover_annot.get_visible():
                    self._hover_annot.set_visible(False)
                    if self._hover_marker is not None and self._hover_marker.get_visible():
                        self._hover_marker.set_visible(False)
                    # Redibuja de forma ociosa usando el canvas de la figura (compatible con TkAgg)
                    self.fig.canvas.draw_idle()
                return

            # Si estamos arrastrando con botón derecho, hacer pan en X
            if self._pan_active and self._pan_start_x is not None and self._pan_xlim_start is not None:
                try:
                    cur_left, cur_right = self._pan_xlim_start
                    dx = event.xdata - self._pan_start_x
                    # desplazamiento inverso: mover a la derecha cuando arrastras a la derecha
                    left = cur_left - dx
                    right = cur_right - dx
                    self.ax_price.set_xlim(left, right)
                    if hasattr(self, 'ax_volume') and self.ax_volume:
                        self.ax_volume.set_xlim(left, right)
                    self._user_xlim = (left, right)
                    # Redibuja de forma ociosa usando el canvas de la figura
                    self.fig.canvas.draw_idle()
                except Exception as e:
                    if self.debug_hover:
                        self._log(f"Pan error: {e}", 'red')
                finally:
                    # En modo pan, no mostrar tooltip para evitar parpadeo
                    if self._hover_annot is not None and self._hover_annot.get_visible():
                        self._hover_annot.set_visible(False)
                    if self._hover_marker is not None and self._hover_marker.get_visible():
                        self._hover_marker.set_visible(False)
                return

            # Si estamos dibujando recuadro (botón izquierdo), actualizar el parche
            if self._rect_active and self._rect_start is not None:
                try:
                    x0, y0 = self._rect_start
                    x1, y1 = event.xdata, event.ydata
                    xmin, xmax = sorted([x0, x1])
                    ymin, ymax = sorted([y0, y1])
                    # Crear el parche si no existe
                    if self._rect_patch is None or self._rect_patch.axes != self.ax_price:
                        self._rect_patch = Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                                                     fill=False, linestyle='--', linewidth=1.0,
                                                     edgecolor='gray', alpha=0.9)
                        self.ax_price.add_patch(self._rect_patch)
                    else:
                        self._rect_patch.set_xy((xmin, ymin))
                        self._rect_patch.set_width(max(xmax - xmin, 0))
                        self._rect_patch.set_height(max(ymax - ymin, 0))
                    self._rect_patch.set_visible(True)
                    # Redibuja de forma ociosa usando el canvas de la figura
                    self.fig.canvas.draw_idle()
                except Exception as e:
                    if self.debug_hover:
                        self._log(f"Rect draw error: {e}", 'red')
                finally:
                    # ocultar hover mientras se dibuja
                    if self._hover_annot is not None and self._hover_annot.get_visible():
                        self._hover_annot.set_visible(False)
                    if self._hover_marker is not None and self._hover_marker.get_visible():
                        self._hover_marker.set_visible(False)
                return

            # Asegurar que existe la anotación
            self._ensure_hover_annotation()

            # Buscar índice de vela más cercano usando coordenadas x numéricas (evita problemas de tz)
            if self._last_x is None or len(self._last_x) == 0:
                return
            loc = int(np.argmin(np.abs(self._last_x - event.xdata)))

            loc = max(0, min(loc, len(self._last_df) - 1))
            ts = self._last_df.index[loc]
            row = self._last_df.iloc[loc]

            # Calcular cambio y color
            open_price = float(row['Open'])
            close_price = float(row['Close'])
            change = close_price - open_price
            change_pct = (change / open_price) * 100 if open_price != 0 else 0
            color = '#28a745' if close_price >= open_price else '#dc3545'  # Verde si sube, rojo si baja
            
            # Formatear fecha y valores
            ts_str = ts.strftime('%Y-%m-%d %H:%M:%S') if hasattr(ts, 'strftime') else str(ts)
            
            # Crear texto con formato simple (sin secuencias ANSI)
            sign = '+' if change >= 0 else ''
            txt = (
                f"{ts_str}\n"
                f"--------------------\n"
                f"Open:   {open_price:.5f}\n"
                f"High:   {float(row['High']):.5f}\n"
                f"Low:    {float(row['Low']):.5f}\n"
                f"Close:  {close_price:.5f}  ({sign}{change:.5f}, {change_pct:+.2f}%)\n"
                f"--------------------\n"
                f"Volume: {float(row['Volume']):.4f}\n"
            )

            # Posicionar anotación inteligentemente
            xnum = mdates.date2num(ts)
            yval = float(row['High'])
            
            # Determinar posición óptima para no salir de la pantalla
            x, y = xnum, yval
            xlim = self.ax_price.get_xlim()
            ylim = self.ax_price.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            
            # Ajustar posición para que no se salga de los límites
            x_offset = 15 if x < (xlim[0] + xlim[1]) / 2 else -15
            y_offset = 15 if y < (ylim[0] + ylim[1]) / 2 else -15
            
            # Actualizar anotación
            self._hover_annot.xy = (x, y)
            self._hover_annot.set_position((x_offset, y_offset))
            self._hover_annot.set_text(txt)
            self._hover_annot.set_visible(True)
            
            # Actualizar marcador en el cierre con el color correspondiente
            self._hover_marker.set_data([xnum], [close_price])
            self._hover_marker.set_markerfacecolor(color)
            self._hover_marker.set_visible(True)

            # Redibujar ligero
            # Redibuja de forma ociosa usando el canvas de la figura
            self.fig.canvas.draw_idle()
        except Exception as e:
            if self.debug_hover:
                self._log(f"Hover error: {e}", 'red')

    def _on_button_press(self, event):
        """Inicia pan (botón derecho) o zoom por recuadro (botón izquierdo)."""
        try:
            if event.inaxes not in (getattr(self, 'ax_price', None), getattr(self, 'ax_volume', None)):
                return
            # Doble clic con botón central: reset de vista a estado inicial
            if getattr(event, 'dblclick', False) and event.button == 2:
                self._reset_view()
                return
            # Pan con botón derecho en cualquiera de los ejes
            if event.button == 3:
                self._pan_active = True
                self._pan_start_x = event.xdata
                self._pan_xlim_start = self.ax_price.get_xlim()
                return
            # Zoom por recuadro con botón izquierdo (con o sin Shift), solo si empieza en eje de precio
            if event.button == 1 and event.inaxes is getattr(self, 'ax_price', None):
                self._rect_active = True
                self._rect_start = (event.xdata, event.ydata)
                try:
                    if self._rect_patch is None or self._rect_patch.axes != self.ax_price:
                        from matplotlib.patches import Rectangle as _Rect
                        self._rect_patch = _Rect(self._rect_start, 0, 0, fill=False,
                                                 linestyle='--', linewidth=1.0,
                                                 edgecolor='gray', alpha=0.9)
                        self.ax_price.add_patch(self._rect_patch)
                    else:
                        self._rect_patch.set_xy(self._rect_start)
                        self._rect_patch.set_width(0)
                        self._rect_patch.set_height(0)
                    self._rect_patch.set_visible(True)
                    if hasattr(self, 'canvas'):
                        self.canvas.draw_idle()
                    else:
                        self.fig.canvas.draw_idle()
                except Exception as e:
                    if self.debug_hover:
                        self._log(f"Rect init error: {e}", 'red')
                return
        except Exception as e:
            if self.debug_hover:
                self._log(f"Button press error: {e}", 'red')

    def _reset_view(self):
        """Restaura el zoom/pan a la vista inicial (toda la serie visible y autoscale en Y)."""
        try:
            if self._last_df is None or self._last_df.empty:
                return
            # Calcular límites X completos
            if self._last_x is None or len(self._last_x) == 0:
                try:
                    xvals = mdates.date2num(self._last_df.index.to_pydatetime())
                except Exception:
                    return
            else:
                xvals = self._last_x
            xmin = float(np.min(xvals))
            xmax = float(np.max(xvals))
            # Aplicar límites X a precio y volumen
            self.ax_price.set_xlim(xmin, xmax)
            if hasattr(self, 'ax_volume') and self.ax_volume:
                self.ax_volume.set_xlim(xmin, xmax)
            # Autoscale Y en precio (y en volumen por separado)
            try:
                self.ax_price.relim()
                self.ax_price.autoscale_view()
            except Exception:
                pass
            try:
                if hasattr(self, 'ax_volume') and self.ax_volume:
                    self.ax_volume.relim()
                    self.ax_volume.autoscale_view()
            except Exception:
                pass
            # Borrar límites de usuario para que se restaure en futuros dibujados
            self._user_xlim = None
            # Ocultar recuadro si existiera
            try:
                if self._rect_patch is not None:
                    self._rect_patch.set_visible(False)
            except Exception:
                pass
            # Redibujar
            if hasattr(self, 'canvas'):
                self.canvas.draw_idle()
            else:
                self.fig.canvas.draw_idle()
        except Exception as e:
            if self.debug_hover:
                self._log(f"Reset view error: {e}", 'red')

    def _on_button_release(self, event):
        """Finaliza pan (botón derecho) o aplica zoom por recuadro (botón izquierdo)."""
        try:
            if event.inaxes not in (getattr(self, 'ax_price', None), getattr(self, 'ax_volume', None)):
                # limpiar estados aunque se suelte fuera
                self._pan_active = False
                self._rect_active = False
                return
            # Fin pan con botón derecho
            if event.button == 3:
                if self._pan_active:
                    self._user_xlim = self.ax_price.get_xlim()
                self._pan_active = False
                self._pan_start_x = None
                self._pan_xlim_start = None
                return
            # Fin zoom por recuadro con botón izquierdo
            if event.button == 1 and self._rect_active and self._rect_start is not None:
                try:
                    x0, y0 = self._rect_start
                    x1, y1 = event.xdata, event.ydata
                    if x1 is None or y1 is None:
                        return
                    xmin, xmax = sorted([x0, x1])
                    ymin, ymax = sorted([y0, y1])
                    if abs(xmax - xmin) < 1e-9 or abs(ymax - ymin) < 1e-12:
                        return
                    # Aplicar zoom X a ambos ejes y Y sólo a precio
                    self.ax_price.set_xlim(xmin, xmax)
                    if hasattr(self, 'ax_volume') and self.ax_volume:
                        self.ax_volume.set_xlim(xmin, xmax)
                    self.ax_price.set_ylim(ymin, ymax)
                    self._user_xlim = (xmin, xmax)
                except Exception as e:
                    if self.debug_hover:
                        self._log(f"Rect apply error: {e}", 'red')
                finally:
                    try:
                        if self._rect_patch is not None:
                            self._rect_patch.set_visible(False)
                    except Exception:
                        pass
                    if hasattr(self, 'canvas'):
                        self.canvas.draw_idle()
                    else:
                        self.fig.canvas.draw_idle()
                    self._rect_active = False
                    self._rect_start = None
        except Exception as e:
            if self.debug_hover:
                self._log(f"Button release error: {e}", 'red')

    def _on_scroll(self, event):
        """Zoom con la rueda del ratón centrado en el cursor. Sólo eje X, sincronizado entre subplots."""
        try:
            if event.xdata is None or event.inaxes not in (getattr(self, 'ax_price', None), getattr(self, 'ax_volume', None)):
                return
            ax = self.ax_price  # usamos el eje de precio como referencia
            cur_left, cur_right = ax.get_xlim()
            x = event.xdata
            width = cur_right - cur_left
            if width <= 0:
                return
            # Factor de zoom: rueda hacia arriba acerca, hacia abajo aleja
            base = 1.2
            if event.button == 'up':
                scale = 1 / base
            elif event.button == 'down':
                scale = base
            else:
                return
            new_width = width * scale
            # Recalcular límites manteniendo el punto del cursor como ancla
            left = x - (x - cur_left) * (new_width / width)
            right = left + new_width
            # Aplicar a ambos ejes
            self.ax_price.set_xlim(left, right)
            if hasattr(self, 'ax_volume') and self.ax_volume:
                self.ax_volume.set_xlim(left, right)
            # Guardar para persistir en redibujos
            self._user_xlim = (left, right)
            # Redibujar
            if hasattr(self, 'canvas'):
                self.canvas.draw_idle()
            else:
                self.fig.canvas.draw_idle()
        except Exception as e:
            if self.debug_hover:
                self._log(f"Scroll zoom error: {e}", 'red')

    def _update_csv(self):
        self.df.to_csv(self.csv_file)

    def _binance_interval_for_klines(self):
        """Mapea el intervalo configurado a uno soportado por la API de klines de Binance."""
        supported = {"1m", "2m", "3m", "5m", "15m", "30m"}
        if self.interval.endswith('s'):
            # La API spot de klines no soporta segundos. Omitimos seeding en este caso.
            return None
        if self.interval in supported:
            return self.interval
        # Fallback a 1m si el intervalo no está soportado
        if self.debug_mode:
            self._log(f"Intervalo {self.interval} no soportado por klines. Usando 1m para precarga.", 'yellow')
        return "1m"

    def _seed_historical(self, limit: int = 500):
        """Precarga velas históricas desde la API de klines para poblar el gráfico al inicio."""
        try:
            k_interval = self._binance_interval_for_klines()
            if not k_interval:
                if self.debug_mode:
                    self._log("Precarga histórica omitida (intervalo en segundos no soportado por klines).", 'yellow')
                return

            symbol = self.symbol.replace('/', '').replace('-', '')
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={k_interval}&limit={min(max(limit,1),1000)}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list) or len(data) == 0:
                if self.debug_mode:
                    self._log("No se recibieron klines para precarga.", 'yellow')
                return

            records = []
            for k in data:
                # kline payload: [openTime, open, high, low, close, volume, closeTime, ...]
                open_time_ms = k[0]
                o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
                records.append({
                    'Date': datetime.fromtimestamp(open_time_ms/1000),
                    'Open': o, 'High': h, 'Low': l, 'Close': c, 'Volume': v
                })

            hist_df = pd.DataFrame(records).set_index('Date')
            hist_df.sort_index(inplace=True)

            if self.df.empty:
                self.df = hist_df
            else:
                self.df = pd.concat([self.df, hist_df])
                self.df = self.df[~self.df.index.duplicated(keep='last')]
                self.df.sort_index(inplace=True)

            if self.debug_mode:
                self._log(f"Precargadas {len(hist_df)} velas históricas para {self.symbol} ({self.interval}).")
            self._plot_last_candles()
            self._update_csv()
        except Exception as e:
            self._log(f"Error en precarga histórica: {e}", 'red')

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if self.debug_mode:
                self._log(f"Mensaje recibido: {message}")
            
            if 'p' in data and 'q' in data and 'T' in data:
                trade_price = float(data['p'])
                trade_volume = float(data['q'])
                trade_time = datetime.fromtimestamp(data['T']/1000)
                if self.debug_mode:
                    self._log(f"Procesando trade - Precio: {trade_price}, Volumen: {trade_volume}, Hora: {trade_time}")
                self._add_trade_to_candle(trade_price, trade_volume, trade_time)
        except Exception as e:
            self._log(f"Error procesando mensaje: {e}", 'red')

    def _log(self, message, color='white'):
        """Método seguro para logging que puede ser llamado desde cualquier hilo"""
        try:
            if hasattr(self, 'parent_frame') and self.parent_frame:
                # Si estamos en modo GUI, programar la llamada en el hilo principal
                self.parent_frame.after(0, lambda: self.log_callback(message, color))
            else:
                # Si no hay GUI, usar print
                if self.debug_mode or color in ['red', 'yellow']:  # Mostrar errores y warnings siempre
                    print(f"{color.upper()}: {message}")
        except Exception as e:
            print(f"Error en _log: {e}")

    def _on_error(self, ws, error):
        self._log(f"Error: {error}", 'red')

    def _on_close(self, ws, close_status_code, close_msg):
        self._log("Conexión WebSocket cerrada", 'yellow')

    def _on_open(self, ws):
        self._log("Conexión WebSocket establecida", 'green')
        # Convert symbol to lowercase and remove any separators for Binance WebSocket
        binance_symbol = self.symbol.lower().replace('/', '').replace('-', '')
        if self.debug_mode:
            self._log(f"Suscribiéndose a: {binance_symbol}@trade", 'green')
        payload = {
            "method": "SUBSCRIBE",
            "params": [f"{binance_symbol}@trade"],
            "id": 1
        }
        ws.send(json.dumps(payload))

    def _reconnect(self):
        self.reconnect_attempts += 1
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), self.max_reconnect_delay)
        self._log(f"Intentando reconectar en {delay} segundos...", 'yellow')
        self.reconnect_thread = threading.Timer(delay, self.start)
        self.reconnect_thread.start()

    def start(self):
        """Inicia el stream de velas"""
        self.running = True
        # Precargar histórico antes de iniciar el stream en vivo
        try:
            self._seed_historical(limit=min(self.max_plot, 500))
        except Exception as e:
            self._log(f"No se pudo precargar histórico: {e}", 'red')

        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        self.ws.run_forever(ping_interval=20, ping_timeout=10)

        if self.reconnect_attempts < self.max_reconnect_attempts:
            self._reconnect()
        else:
            self._log("Máximo número de reintentos alcanzado. Deteniendo el stream.", 'red')
            self.stop()

    def stop(self):
        """Detiene el stream de velas y limpia los recursos"""
        self.running = False
        self._pending_refresh = False
        
        if hasattr(self, 'ws') and self.ws:
            self.ws.close()
            
        # Cerrar la figura de matplotlib
        if hasattr(self, 'fig') and self.fig:
            plt.close(self.fig)
            
        # Limpiar el canvas de Tkinter si existe
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.get_tk_widget().destroy()
            
        if hasattr(self, 'thread') and self.thread:
            self.thread.join(timeout=2.0)

    def set_symbol(self, symbol):
        """Cambia el símbolo activo y reinicia el stream"""
        if symbol != self.symbol:
            self.stop()
            self.symbol = symbol
            self.csv_file = os.path.join(self.csv_folder, f'{self.symbol}_data.csv')
            self.df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
            self.df.index.name = 'Date'
            self.df.index = pd.to_datetime(self.df.index)
            self.current_candle = None
            self.start()

    def set_interval(self, interval):
        """Cambia el intervalo de tiempo"""
        if interval in self.ALLOWED_INTERVALS and interval != self.interval:
            self.stop()
            self.interval = interval
            self.start()

    def set_max_plot(self, max_plot):
        """Cambia el número máximo de velas a mostrar"""
        if max_plot in self.ALLOWED_MAX_PLOT and max_plot != self.max_plot:
            self.max_plot = max_plot
            self._plot_last_candles()

    def get_available_symbols(self):
        """Devuelve la lista de símbolos disponibles"""
        return self.symbols

    def get_current_data(self):
        """Devuelve los datos actuales del DataFrame"""
        return self.df.copy()

    def get_current_candle(self):
        """Devuelve la vela actual en formación"""
        return self.current_candle.copy() if self.current_candle else None

    def export_to_csv(self, filename=None):
        """Exporta los datos a un archivo CSV"""
        if filename is None:
            filename = self.csv_file
        self.df.to_csv(filename)
        self._log(f"Datos exportados a: {filename}", 'green')

    def clear_data(self):
        """Limpia todos los datos almacenados"""
        self.df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        self.df.index.name = 'Date'
        self.df.index = pd.to_datetime(self.df.index)
        self.current_candle = None
        self._plot_last_candles()