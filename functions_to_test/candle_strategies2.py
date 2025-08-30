# strategies/candle_strategies.py

import pandas as pd
import numpy as np
from patterns.candlestickpatterns import CandlestickPatterns

class CandleStrategies:
    def __init__(self, data):
        """
        data: DataFrame con columnas ['Open','High','Low','Close']
        """
        self.data = data.copy()
        self.patterns = CandlestickPatterns(self.data)

    # ---------------- Utils ----------------
    def add_indicators(self):
        """Agrega indicadores de tendencia y volatilidad básicos"""
        df = self.data.copy()
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        return df

    # ---------------- Estrategias de reversión alcista ----------------
    def hammer_reversal(self):
        """Martillo en tendencia bajista"""
        df = self.patterns.hammer()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        df['Signal'] = np.where((df['Signal'] == 1) & 
                                (self.data['Close'] < df['EMA20']), 1, 0)
        return df

    def bullish_engulfing_reversal(self):
        """Envolvente alcista tras tendencia bajista (optimizado)"""
        df = self.data.copy()

        # Condiciones para envolvente alcista
        cond_bearish_prev = df['Close'].shift(1) < df['Open'].shift(1)  # vela anterior bajista
        cond_bullish_curr = df['Close'] > df['Open']                    # vela actual alcista

        # Cuerpo de la vela actual envuelve completamente al cuerpo de la anterior
        cond_engulfing = (
            (df['Open'] < df['Close'].shift(1)) &   # abre debajo del cierre previo
            (df['Close'] > df['Open'].shift(1))     # cierra por encima de la apertura previa
        )

        # Cuerpo relativamente grande comparado con promedio de 20 velas
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()
        cond_large_body = body > 0.7 * avg_body

        # Cierre cerca del máximo (fuerza compradora)
        upper_shadow = df['High'] - df['Close']
        cond_strong_close = upper_shadow < (body * 0.3)

        # Tendencia bajista previa (precio debajo de media móvil)
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_downtrend = df['Close'].shift(2) < df['EMA20'].shift(2)

        # Señal final
        cond = (
            cond_bearish_prev &
            cond_bullish_curr &
            cond_engulfing &
            cond_large_body &
            cond_strong_close &
            cond_prev_downtrend
        )

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open', 'High', 'Low', 'Close', 'EMA20', 'Signal']]

    def morning_star_swing(self):
        """Estrella de la mañana como señal swing (confirmada con 2 velas)"""
        df = self.patterns.morning_star()
        df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        df['Signal'] = np.where((df['Signal'] == 1) & 
                                (self.data['Close'] > df['EMA50']), 1, 0)
        return df

    # ---------------- Estrategias de reversión bajista ----------------
    def hanging_man_reversal(self):
        df = self.patterns.hanging_man()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        df['Signal'] = np.where((df['Signal'] == -1) & 
                                (self.data['Close'] > df['EMA20']), -1, 0)
        return df

    def bearish_engulfing_reversal(self):
        """Patrón Bearish Engulfing optimizado (reversión bajista)"""
        df = self.data.copy()

        # --- Cálculo de cuerpo y sombras ---
        df['Body'] = (df['Close'] - df['Open']).abs()
        avg_body = df['Body'].rolling(20).mean()
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)

        # --- Condiciones básicas del patrón ---
        cond_prev_bullish = df['Close'].shift(1) > df['Open'].shift(1)   # vela anterior alcista
        cond_curr_bearish = df['Close'] < df['Open']                     # vela actual bajista

        # La vela bajista envuelve completamente a la alcista previa
        cond_engulfing = (
            (df['Open'] > df['Close'].shift(1)) &  # abre por encima del cierre anterior
            (df['Close'] < df['Open'].shift(1))    # cierra por debajo de la apertura anterior
        )

        # Cuerpo relativamente grande
        cond_large_body = df['Body'] > 0.7 * avg_body

        # Cierre fuerte (cerca del mínimo de la vela actual)
        cond_strong_close = upper_shadow < (df['Body'] * 0.3)

        # Tendencia previa alcista
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_uptrend = df['Close'].shift(2) > df['EMA20'].shift(2)

        # Señal final
        cond = (
            cond_prev_bullish &
            cond_curr_bearish &
            cond_engulfing &
            cond_large_body &
            cond_strong_close &
            cond_prev_uptrend
        )

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA20','Signal']]
    
    def evening_star_swing(self):
        """Patrón Evening Star optimizado con confirmación de tendencia alcista previa"""
        df = self.data.copy()

        # Calcular cuerpos y sombras
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        upper_shadow = df['High'] - df[['Close', 'Open']].max(axis=1)
        lower_shadow = df[['Close', 'Open']].min(axis=1) - df['Low']

        # Condiciones del patrón
        cond_first_bullish = (df['Close'].shift(2) > df['Open'].shift(2)) & (body.shift(2) > 0.7 * avg_body.shift(2))
        cond_second_small = body.shift(1) < 0.5 * avg_body.shift(1)  # vela débil / indecisión
        cond_third_bearish = (df['Close'] < df['Open']) & (body > 0.7 * avg_body)

        # Confirmación: la tercera vela cierra al menos debajo de la mitad de la primera
        cond_close_below_mid = df['Close'] < ((df['Open'].shift(2) + df['Close'].shift(2)) / 2)

        # Cierre fuerte (cerca del mínimo de la vela actual)
        cond_strong_close = (lower_shadow < body * 0.3)

        # Tendencia previa alcista (precio por encima de EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(3) > df['EMA50'].shift(3)

        # Señal final
        cond = (
            cond_first_bullish &
            cond_second_small &
            cond_third_bearish &
            cond_close_below_mid &
            cond_strong_close &
            cond_prev_uptrend
        )

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open', 'High', 'Low', 'Close', 'EMA50', 'Signal']]

    # ---------------- Estrategias de indecisión / continuación ----------------
    def doji_indecision(self):
        df = self.patterns.doji()
        df['Signal'] = np.where(df['Signal'] == 0, 0, 0)  # neutro
        return df

    def marubozu_trend(self):
        df = self.data.copy()
        df['Body'] = abs(df['Close'] - df['Open'])
        df['UpperShadow'] = df['High'] - df[['Open','Close']].max(axis=1)
        df['LowerShadow'] = df[['Open','Close']].min(axis=1) - df['Low']
        df['Signal'] = 0
        df.loc[(df['Body'] > df['UpperShadow']*3) & (df['Body'] > df['LowerShadow']*3) & (df['Close'] > df['Open']), 'Signal'] = 1
        df.loc[(df['Body'] > df['UpperShadow']*3) & (df['Body'] > df['LowerShadow']*3) & (df['Close'] < df['Open']), 'Signal'] = -1
        return df[['Open','High','Low','Close','Signal']]

    # ---------------- Estrategias de múltiples velas ----------------
    def three_white_soldiers(self):
        df = self.patterns.three_white_soldiers()
        return df

    def three_black_crows(self):
        df = self.patterns.three_black_crows()
        return df

    # ---------------- Estrategias de trading ----------------
    def scalping_reversal(self):
        """Scalping con hammer + engulfing en soportes"""
        df_h = self.hammer_reversal()
        df_e = self.bullish_engulfing_reversal()
        df = self.data.copy()
        df['Signal'] = np.where((df_h['Signal'] == 1) | (df_e['Signal'] == 1), 1, 0)
        return df

    def swing_trading(self):
        """Swing con morning/evening star"""
        df_m = self.morning_star_swing()
        df_e = self.evening_star_swing()
        df = self.data.copy()
        df['Signal'] = np.where(df_m['Signal'] == 1, 1, 
                         np.where(df_e['Signal'] == -1, -1, 0))
        return df

    def filter_with_trend(self):
        """Filtro combinado con EMA50"""
        df = self.patterns.combined_signal_optimized()
        df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        df['Final_Signal'] = np.where((df['Final_Signal'] == 1) & (df['Close'] > df['EMA50']), 1,
                               np.where((df['Final_Signal'] == -1) & (df['Close'] < df['EMA50']), -1, 0))
        return df

    def stop_loss_take_profit(self, rr_ratio=2):
        """Calcula niveles SL y TP con ATR"""
        df = self.add_indicators()
        df['Signal'] = self.patterns.combined_signal_optimized()['Final_Signal']
        df['StopLoss'] = np.where(df['Signal'] == 1, df['Close'] - df['ATR'], 
                           np.where(df['Signal'] == -1, df['Close'] + df['ATR'], np.nan))
        df['TakeProfit'] = np.where(df['Signal'] == 1, df['Close'] + df['ATR']*rr_ratio,
                             np.where(df['Signal'] == -1, df['Close'] - df['ATR']*rr_ratio, np.nan))
        return df[['Open','High','Low','Close','Signal','StopLoss','TakeProfit']]
