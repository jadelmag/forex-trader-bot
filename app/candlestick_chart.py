import yfinance as yf
import mplfinance as mpf
import pandas as pd

class CandlestickChart:
    def __init__(self, base, cotizada, period="1d", interval="1m"):
        """
        base: moneda base (ej. "USD")
        cotizada: moneda cotizada (ej. "EUR")
        period: periodo de los datos (ej. "1d", "1mo")
        interval: intervalo de las velas (ej. "1m", "5m", "1h")
        """
        self.base = base.upper()
        self.cotizada = cotizada.upper()
        self.period = period
        self.interval = interval
        self.ticker_symbol = f"{self.base}{self.cotizada}=X"
        self.data = None
        self.ultima_fecha = None

    def obtener_datos(self):
        """
        Descarga datos desde Yahoo Finance y actualiza self.data.
        Solo añade nuevas velas para evitar parpadeo.
        """
        ticker = yf.Ticker(self.ticker_symbol)
        nueva_data = ticker.history(period=self.period, interval=self.interval)

        if nueva_data.empty:
            raise ValueError(f"No se encontraron datos para {self.ticker_symbol}")

        if self.data is None:
            self.data = nueva_data
            self.ultima_fecha = self.data.index[-1]
        else:
            # Solo añade nuevas filas
            ultima = self.data.index[-1]
            nuevas_filas = nueva_data.loc[nueva_data.index > ultima]
            if not nuevas_filas.empty:
                self.data = pd.concat([self.data, nuevas_filas])
                self.ultima_fecha = self.data.index[-1]

        return self.data

    def crear_figura(self, style="yahoo", mostrar_volumen=True):
        """
        Devuelve una figura mplfinance lista para incrustar en Tkinter.
        """
        if self.data is None:
            self.obtener_datos()

        fig, axlist = mpf.plot(
            self.data,
            type='candle',
            style=style,
            title=f"{self.base}/{self.cotizada} - Últimos {self.period}",
            ylabel="Precio",
            volume=mostrar_volumen,
            returnfig=True
        )
        return fig

    def actualizar_datos_incremental(self):
        """Actualiza los datos descargando solo nuevas filas"""
        print("actualizar_datos_incremental")
        
    def dibujar_incremental(self, ax):
        """Redibuja toda la gráfica con los datos actuales"""
        print("dibujar_incremental")
