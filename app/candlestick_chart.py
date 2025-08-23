# app/candlestick_chart.py
# app/candlestick_chart.py
import yfinance as yf
import mplfinance as mpf
import pandas as pd
from app.forex_pairs import ForexPairs

class CandlestickChart:
    def __init__(self, base=None, cotizada=None, period="1mo", interval="1d", data=None):
        """
        base, cotizada: usados para yfinance
        data: DataFrame opcional para usar datos de CSV u otra fuente
        """
        self.base = base.upper() if base else None
        self.cotizada = cotizada.upper() if cotizada else None
        self.period = period
        self.interval = interval
        self.data = data
        self.ultima_fecha = None

        if base and cotizada:
            self.ticker_symbol, self.invertido = ForexPairs.ticker_valido(self.base, self.cotizada)
        else:
            self.ticker_symbol, self.invertido = None, False

    def obtener_datos(self):
        """
        Descarga datos desde Yahoo Finance si no hay DataFrame ya cargado.
        """
        if self.data is not None:
            return self.data

        if not self.ticker_symbol:
            raise ValueError("No se proporcionó ticker ni datos")

        try:
            ticker = yf.Ticker(self.ticker_symbol)
            nueva_data = ticker.history(period=self.period, interval=self.interval)
        except Exception as e:
            if "429" in str(e):
                raise RuntimeError("Acceso limitado (429) a Yahoo Finance") from e
            else:
                raise

        if nueva_data.empty:
            raise ValueError(f"No se encontraron datos para {self.base}/{self.cotizada}")

        if self.invertido:
            nueva_data = nueva_data.rename(columns={"Open":"Open_tmp","High":"High_tmp","Low":"Low_tmp","Close":"Close_tmp"})
            nueva_data["Open"] = 1 / nueva_data["Close_tmp"]
            nueva_data["High"] = 1 / nueva_data["Low_tmp"]
            nueva_data["Low"] = 1 / nueva_data["High_tmp"]
            nueva_data["Close"] = 1 / nueva_data["Open_tmp"]
            nueva_data.drop(columns=["Open_tmp","High_tmp","Low_tmp","Close_tmp"], inplace=True)

        self.data = nueva_data
        self.ultima_fecha = self.data.index[-1]
        return self.data

    @classmethod
    def from_dataframe(cls, df):
        """
        Crea un CandlestickChart a partir de un DataFrame ya cargado (CSV u otra fuente).
        """
        df = df.copy()
        # Normalizar nombres de columnas a los que usa mplfinance
        df.rename(columns={
            'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'
        }, inplace=True)
        return cls(data=df)

    def crear_figura(self, ax=None, style="yahoo", mostrar_volumen=True):
        if self.data is None:
            self.obtener_datos()

        if ax is None:
            fig, axlist = mpf.plot(
            self.data,
            type='candle',
            style=style,
            title=f"{self.base}/{self.cotizada}" if self.base and self.cotizada else "Datos CSV",
            ylabel="Precio",
            volume=mostrar_volumen,
            returnfig=True
        )
        else:
            fig, axlist = mpf.plot(
            self.data,
            type='candle',
            style=style,
            title=f"{self.base}/{self.cotizada}" if self.base and self.cotizada else "Datos CSV",
            ylabel="Precio",
            volume=mostrar_volumen,
            returnfig=True,
            ax=ax
        )

        return fig

