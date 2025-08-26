# app/grafico_manager.py

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .candlestick_chart import CandlestickChart
import numpy as np

class GraficoManager:
    def __init__(self, frame):
        self.frame = frame
        self.canvas = None
        self.grafico = None
        self.fig = None
        self.ax = None

    def dibujar_csv(self, df):
        self.grafico = CandlestickChart.from_dataframe(df)
        self.fig, self.ax = self.grafico.crear_figura()
        self._dibujar_canvas()
        return self.fig, self.ax

    def _dibujar_canvas(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def limpiar(self):
        """Limpia la figura y el canvas"""
        if hasattr(self, 'grafico') and self.grafico:
            if hasattr(self.grafico, 'ax') and self.grafico.ax:
                self.grafico.ax.clear()
            if hasattr(self.grafico, 'fig') and self.grafico.fig:
                self.grafico.fig.clf()
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.draw_idle()

    def dibujar_senales_rl(self, signals):
        """
        Dibuja flechas de compra/venta sobre la gráfica de velas
        signals: lista de 0=mantener, 1=comprar, 2=vender
        """
        if self.grafico is None or self.ax is None:
            return
        df = self.grafico.data.reset_index()
        # Limpiar flechas anteriores
        self.ax.collections = [c for c in self.ax.collections if not hasattr(c, 'es_flecha_rl')]
        self.ax.lines = [l for l in self.ax.lines if not hasattr(l, 'es_flecha_rl')]

        for i, signal in enumerate(signals):
            if signal == 1:  # Compra
                self.ax.annotate(
                    "▲",
                    xy=(i, df['Low'].iloc[i] * 0.9995),
                    xytext=(0, 0),
                    textcoords="offset points",
                    color="green",
                    fontsize=12,
                    ha="center",
                    va="bottom"
                )
            elif signal == 2:  # Venta
                self.ax.annotate(
                    "▼",
                    xy=(i, df['High'].iloc[i] * 1.0005),
                    xytext=(0, 0),
                    textcoords="offset points",
                    color="red",
                    fontsize=12,
                    ha="center",
                    va="top"
                )

        self.canvas.draw_idle()
