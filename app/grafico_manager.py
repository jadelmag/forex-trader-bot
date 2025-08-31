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
        # Artistas (anotaciones/flechas) añadidos por señales RL para poder limpiarlos
        self._rl_artists = []

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
        # Limpiar flechas anteriores de forma segura
        try:
            if hasattr(self, '_rl_artists') and self._rl_artists:
                # eliminar cada artista previo (Text/Line2D/Collection, etc.)
                for art in list(self._rl_artists):
                    try:
                        art.remove()
                    except Exception:
                        pass
                self._rl_artists.clear()
        except Exception:
            pass

        for i, signal in enumerate(signals):
            if signal == 1:  # Compra
                txt = self.ax.annotate(
                    "▲",
                    xy=(i, df['Low'].iloc[i] * 0.9995),
                    xytext=(0, 0),
                    textcoords="offset points",
                    color="green",
                    fontsize=12,
                    ha="center",
                    va="bottom"
                )
                try:
                    setattr(txt, 'es_flecha_rl', True)
                    self._rl_artists.append(txt)
                except Exception:
                    pass
            elif signal == 2:  # Venta
                txt = self.ax.annotate(
                    "▼",
                    xy=(i, df['High'].iloc[i] * 1.0005),
                    xytext=(0, 0),
                    textcoords="offset points",
                    color="red",
                    fontsize=12,
                    ha="center",
                    va="top"
                )
                try:
                    setattr(txt, 'es_flecha_rl', True)
                    self._rl_artists.append(txt)
                except Exception:
                    pass

        self.canvas.draw_idle()

    def set_candles_opacity(self, alpha: float):
        """Actualiza la opacidad de las velas y redibuja el canvas."""
        if not self.grafico:
            return
        try:
            self.grafico.set_candles_alpha(alpha)
            if self.canvas:
                self.canvas.draw_idle()
        except Exception:
            pass
