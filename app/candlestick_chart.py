# app/candlestick_chart.py

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import ticker
from mplfinance.original_flavor import candlestick_ohlc

class CandlestickChart:
    def __init__(self, base=None, cotizada=None, period='1mo', interval='1d'):
        self.base = base
        self.cotizada = cotizada
        self.period = period
        self.interval = interval
        self.data = None

    @classmethod
    def from_dataframe(cls, df):
        """
        Crea una instancia de CandlestickChart a partir de un DataFrame.
        El DataFrame debe tener columnas: DateTime, Open, High, Low, Close, Volume
        """
        obj = cls()
        df = df.copy()
        if 'DateTime' in df.columns:
            df['DateTime'] = pd.to_datetime(df['DateTime'], format='%Y%m%d %H%M%S', errors='coerce')
            df.set_index('DateTime', inplace=True)
        obj.data = df
        return obj

    def obtener_datos(self):
        """Obtiene datos de yfinance si no hay CSV."""
        import yfinance as yf
        if not self.base or not self.cotizada:
            raise ValueError("Base y cotizada deben estar definidas para descargar datos.")
        ticker_str = f"{self.base}{self.cotizada}=X"
        df = yf.download(ticker_str, period=self.period, interval=self.interval)
        if df.empty:
            raise ValueError("No se pudieron obtener datos de Yahoo Finance")
        df.reset_index(inplace=True)
        df.rename(columns={'Date': 'DateTime', 'Open':'Open', 'High':'High',
                           'Low':'Low', 'Close':'Close', 'Volume':'Volume'}, inplace=True)
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df.set_index('DateTime', inplace=True)
        self.data = df

    def crear_figura(self, ax=None):
        """Dibuja la gráfica de velas."""
        if self.data is None or self.data.empty:
            raise ValueError("No hay datos para graficar.")

        df = self.data.copy()
        df_ohlc = df[['Open','High','Low','Close']].copy()
        df_ohlc.reset_index(inplace=True)
        df_ohlc['DateTime'] = df_ohlc['DateTime'].map(mdates.date2num)

        if ax is None:
            fig, ax = plt.subplots(figsize=(12,6))
        else:
            fig = ax.figure
            ax.clear()

        candlestick_ohlc(ax, df_ohlc.values, width=0.0008, colorup='green', colordown='red', alpha=0.8)

        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.set_ylabel(f"{self.base}/{self.cotizada}" if self.base and self.cotizada else "Precio")
        ax.grid(True)
        fig.autofmt_xdate()
        return fig, ax
