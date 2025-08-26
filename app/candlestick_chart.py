# app/candlestick_chart.py

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import ticker
from mplfinance.original_flavor import candlestick_ohlc
import numpy as np

class CandlestickChart:
    def __init__(self, base=None, cotizada=None, period='1mo', interval='1d'):
        self.base = base
        self.cotizada = cotizada
        self.period = period
        self.interval = interval
        self.data = None
        self.ax = None

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
        
        # Mostrar símbolo si está disponible, sino genérico
        if self.base and self.cotizada:
            ax.set_ylabel(f"{self.base}/{self.cotizada}")
        else:
            ax.set_ylabel("Precio")
            
        ax.grid(True)
        fig.autofmt_xdate()
        
        # Guardar referencia al axes
        self.ax = ax
        return fig, ax

    # --- Dibujar senales RL: ENTRENAMIENTO ---
    def dibujar_senales(self, signals):
        """
        Dibuja flechas de compra/venta sobre el gráfico.
        signals: array o Serie de 0=mantener, 1=comprar, 2=vender
        """
        if self.ax is None:
            raise ValueError("Debe crear la figura primero con crear_figura()")
        
        df_plot = self.data.reset_index()
        for i, signal in enumerate(signals):
            if signal == 1:  # comprar
                self.ax.annotate('↑', xy=(mdates.date2num(df_plot['DateTime'].iloc[i]),
                                           df_plot['Low'].iloc[i]*0.995),
                                 color='green', fontsize=12, ha='center')
            elif signal == 2:  # vender
                self.ax.annotate('↓', xy=(mdates.date2num(df_plot['DateTime'].iloc[i]),
                                           df_plot['High'].iloc[i]*1.005),
                                 color='red', fontsize=12, ha='center')