from .candlestick_chart import CandlestickChart

class YFinanceManager:
    def __init__(self):
        self.grafico = None

    def obtener_datos(self, base, cotizada, periodo, intervalo):
        self.grafico = CandlestickChart(base, cotizada, periodo=periodo, interval=intervalo)
        self.grafico.obtener_datos()
        return self.grafico.data
