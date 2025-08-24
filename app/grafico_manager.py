# app/grafico_manager.py

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .candlestick_chart import CandlestickChart

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

    def dibujar_yfinance(self, base, cotizada, periodo, intervalo):
        self.grafico = CandlestickChart(base, cotizada, periodo=periodo, interval=intervalo)
        self.grafico.obtener_datos()
        self.fig, self.ax = self.grafico.crear_figura()
        self._dibujar_canvas()
        return self.fig, self.ax

    def _dibujar_canvas(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
