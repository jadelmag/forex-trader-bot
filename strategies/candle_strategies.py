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
        """Envolvente alcista en tendencia bajista"""
        df = self.patterns.bullish_engulfing()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        df['Signal'] = np.where((df['Signal'] == 1) & 
                                (self.data['Close'] < df['EMA20']), 1, 0)
        return df

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
        df = self.patterns.bearish_engulfing()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        df['Signal'] = np.where((df['Signal'] == -1) & 
                                (self.data['Close'] > df['EMA20']), -1, 0)
        return df

    def evening_star_swing(self):
        df = self.patterns.evening_star()
        df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        df['Signal'] = np.where((df['Signal'] == -1) & 
                                (self.data['Close'] < df['EMA50']), -1, 0)
        return df

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
