# trandig-view/candle-streamer.py

import json
import websocket
import threading
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import os
import requests
import tkinter as tk  # Añadido para el soporte de Tkinter

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
        # Validar interval
        if interval not in self.ALLOWED_INTERVALS:
            print(f'Intervalo inválido. Se asigna por defecto: 1m')
            self.interval = DEFAULT_INTERVAL
        else:
            self.interval = interval

        # Validar max_plot
        if max_plot not in self.ALLOWED_MAX_PLOT:
            print(f'max_plot inválido. Se asigna por defecto: 500')
            self.max_plot = DEFAULT_MAX_PLOT
        else:
            self.max_plot = max_plot

        self.url = URL
        self.ws = None
        self.thread = None

        # DataFrame inicial con DatetimeIndex
        self.df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        self.df.index.name = 'Date'
        self.df.index = pd.to_datetime(self.df.index)

        self.current_candle = None

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

            print(f"Intervalo actual: {self.interval}, Inicio del intervalo: {interval_start}", 'gray')
            
            if self.current_candle is None or self.current_candle['Date'] != interval_start:
                if self.current_candle is not None:
                    print(f"Nueva vela creada: {self.current_candle}", 'green')
                    new_candle = pd.DataFrame([self.current_candle])
                    new_candle.set_index('Date', inplace=True)
                    # Evitar FutureWarning: no concatenar con DataFrame vacío
                    if self.df.empty:
                        self.df = new_candle.copy()
                    else:
                        self.df = pd.concat([self.df, new_candle])
                    print(f"DataFrame actualizado. Total de velas: {len(self.df)}", 'gray')
                    self._update_csv()

                self.current_candle = {
                    'Date': interval_start,
                    'Open': trade_price,
                    'High': trade_price,
                    'Low': trade_price,
                    'Close': trade_price,
                    'Volume': trade_volume
                }
                print(f"Nueva vela iniciada: {self.current_candle}", 'green')
                # Refrescar gráfico con la nueva vela en curso
                self._plot_last_candles()
            else:
                prev_high = self.current_candle['High']
                prev_low = self.current_candle['Low']
                prev_volume = self.current_candle['Volume']
                
                self.current_candle['High'] = max(prev_high, trade_price)
                self.current_candle['Low'] = min(prev_low, trade_price)
                self.current_candle['Close'] = trade_price
                self.current_candle['Volume'] += trade_volume
                
                if (prev_high != self.current_candle['High'] or 
                    prev_low != self.current_candle['Low'] or 
                    prev_volume != self.current_candle['Volume']):
                    print(f"Vela actualizada: {self.current_candle}", 'gray')
                # Refrescar gráfico en cada actualización intra-intervalo
                self._plot_last_candles()
        except Exception as e:
            print(f"Error en _add_trade_to_candle: {e}", 'red')

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
                print("Añadido punto ficticio para visualizar la primera vela", 'gray')
            except Exception as e:
                print(f"No se pudo añadir punto ficticio: {e}", 'red')

            print(f"Plotting {len(last_df)} filas", 'gray')

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
                
                # Actualizar el canvas si está en modo embebido
                if hasattr(self, 'canvas'):
                    self.canvas.draw()
                else:
                    plt.pause(0.01)
            except Exception as e:
                print(f"Error actualizando el gráfico: {e}", 'red')
        
        # Asegurarse de que la actualización del gráfico se haga en el hilo principal
        if hasattr(self, 'parent_frame') and self.parent_frame:
            self.parent_frame.after(0, _update_plot)
        else:
            _update_plot()

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
        print(f"Intervalo {self.interval} no soportado por klines. Usando 1m para precarga.", 'yellow')
        return "1m"

    def _seed_historical(self, limit: int = 500):
        """Precarga velas históricas desde la API de klines para poblar el gráfico al inicio."""
        try:
            k_interval = self._binance_interval_for_klines()
            if not k_interval:
                print("Precarga histórica omitida (intervalo en segundos no soportado por klines).", 'yellow')
                return

            symbol = self.symbol.replace('/', '').replace('-', '')
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={k_interval}&limit={min(max(limit,1),1000)}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list) or len(data) == 0:
                print("No se recibieron klines para precarga.", 'yellow')
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

            print(f"Precargadas {len(hist_df)} velas históricas para {symbol} ({k_interval}).", 'green')
            # Pintar inmediatamente tras la precarga
            self._plot_last_candles()
            self._update_csv()
        except Exception as e:
            print(f"Error en precarga histórica: {e}", 'red')

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            print(f"Mensaje recibido: {message}")
            
            if 'p' in data and 'q' in data and 'T' in data:
                trade_price = float(data['p'])
                trade_volume = float(data['q'])
                trade_time = datetime.fromtimestamp(data['T']/1000)
                print(f"Procesando trade - Precio: {trade_price}, Volumen: {trade_volume}, Hora: {trade_time}")
                self._add_trade_to_candle(trade_price, trade_volume, trade_time)
        except Exception as e:
            print(f"Error procesando mensaje: {e}")

    def _log(self, message, color='white'):
        """Método seguro para logging que puede ser llamado desde cualquier hilo"""
        try:
            if hasattr(self, 'parent_frame') and self.parent_frame:
                # Si estamos en modo GUI, programar la llamada en el hilo principal
                self.parent_frame.after(0, lambda: self.log_callback(message, color))
            else:
                # Si no hay GUI, usar print
                print(message)
        except Exception as e:
            print(f"Error en _log: {e}")

    def _on_error(self, ws, error):
        print(f"Error: {error}", 'red')

    def _on_close(self, ws, close_status_code, close_msg):
        print("Conexión WebSocket cerrada")

    def _on_open(self, ws):
        print("Conexión WebSocket establecida", 'green')
        # Convert symbol to lowercase and remove any separators for Binance WebSocket
        binance_symbol = self.symbol.lower().replace('/', '').replace('-', '')
        print(f"Suscribiéndose a: {binance_symbol}@trade", 'green')
        payload = {
            "method": "SUBSCRIBE",
            "params": [f"{binance_symbol}@trade"],
            "id": 1
        }
        ws.send(json.dumps(payload))

    def start(self):
        # Precargar histórico antes de iniciar el stream en vivo
        try:
            self._seed_historical(limit=min(self.max_plot, 500))
        except Exception as e:
            print(f"No se pudo precargar histórico: {e}", 'red')

        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()
        # Evitar bloquear la GUI Tkinter si estamos embebidos
        if not (hasattr(self, 'parent_frame') and self.parent_frame):
            plt.show(block=False)

    def stop(self):
        """Detiene el stream de velas y limpia los recursos"""
        self.running = False
        if hasattr(self, 'ws') and self.ws:
            self.ws.close()
            
        # Cerrar la figura de matplotlib
        if hasattr(self, 'fig') and self.fig:
            plt.close(self.fig)
            
        # Limpiar el canvas de Tkinter si existe
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.get_tk_widget().destroy()
        if hasattr(self, 'thread') and self.thread:
            self.thread.join()
