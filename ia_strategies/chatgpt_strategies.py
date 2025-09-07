import pandas as pd
import numpy as np

class CandleScalping:
    def __init__(self):
        """
        Clase para estrategias scalping basadas en velas.
        take_profit: objetivo de beneficio por trade (en la misma unidad del precio, p.ej. $ o €)
        stop_loss: pérdida máxima por trade (misma unidad)
        """
        self.take_profit = 2.0
        self.stop_loss = 1.0

    # === Patrones de velas ===
    def bullish_engulfing(self, df):
        condition = (
            (df['Close'].shift(1) < df['Open'].shift(1)) &  # vela anterior bajista
            (df['Close'] > df['Open']) &                    # vela actual alcista
            (df['Close'] > df['Open'].shift(1)) &           # cierra por encima de apertura anterior
            (df['Open'] < df['Close'].shift(1))             # abre debajo del cierre anterior
        )
        return condition

    def bearish_engulfing(self, df):
        condition = (
            (df['Close'].shift(1) > df['Open'].shift(1)) &  # vela anterior alcista
            (df['Close'] < df['Open']) &                    # vela actual bajista
            (df['Close'] < df['Open'].shift(1)) &           # cierra por debajo de apertura anterior
            (df['Open'] > df['Close'].shift(1))             # abre por encima del cierre anterior
        )
        return condition

    def hammer(self, df):
        body = abs(df['Close'] - df['Open'])
        lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
        condition = (lower_shadow > 2 * body) & (upper_shadow < body)
        return condition

    def shooting_star(self, df):
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
        lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
        condition = (upper_shadow > 2 * body) & (lower_shadow < body)
        return condition
