# app/candlestick_chart.py

import yfinance as yf
import mplfinance as mpf
import pandas as pd
from app.forex_pairs import ForexPairs

class CandlestickChart:
    def __init__(self, base, cotizada, period="1mo", interval="1d"):
        self.base = base.upper()
        self.cotizada = cotizada.upper()
        self.period = period
        self.interval = interval

        # Seleccionar ticker válido
        self.ticker_symbol, self.invertido = ForexPairs.ticker_valido(self.base, self.cotizada)

        self.data = None
        self.ultima_fecha = None

    def obtener_datos(self):
        ticker = yf.Ticker(self.ticker_symbol)
        nueva_data = ticker.history(period=self.period, interval=self.interval)

        if nueva_data.empty:
            raise ValueError(f"No se encontraron datos para {self.base}/{self.cotizada}")

        if self.invertido:
            # Invertir precios si el ticker estaba invertido
            nueva_data = nueva_data.rename(columns={"Open":"Open_tmp","High":"High_tmp","Low":"Low_tmp","Close":"Close_tmp"})
            nueva_data["Open"] = 1 / nueva_data["Close_tmp"]
            nueva_data["High"] = 1 / nueva_data["Low_tmp"]
            nueva_data["Low"] = 1 / nueva_data["High_tmp"]
            nueva_data["Close"] = 1 / nueva_data["Open_tmp"]
            nueva_data.drop(columns=["Open_tmp","High_tmp","Low_tmp","Close_tmp"], inplace=True)

        self.data = nueva_data
        self.ultima_fecha = self.data.index[-1]
        return self.data

    def crear_figura(self, style="yahoo", mostrar_volumen=True):
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
