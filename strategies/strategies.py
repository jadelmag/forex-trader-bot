# app/strategies.py

import pandas as pd
import numpy as np

class ForexStrategies:
    def __init__(self, data):
        """
        data: DataFrame con columnas ['Open', 'High', 'Low', 'Close']
        """
        self.data = data.copy()
    
    # ---------------- Trend Following ----------------
    def trend_following(self, short_window=20, long_window=50):
        df = self.data.copy()
        df['EMA_short'] = df['Close'].ewm(span=short_window, adjust=False).mean()
        df['EMA_long'] = df['Close'].ewm(span=long_window, adjust=False).mean()
        
        df['Signal'] = 0
        df['Signal'][short_window:] = np.where(df['EMA_short'][short_window:] > df['EMA_long'][short_window:], 1, -1)
        return df[['Close', 'EMA_short', 'EMA_long', 'Signal']]
    
    # ---------------- Breakout Strategy ----------------
    def breakout(self, window=20):
        df = self.data.copy()
        df['High_Max'] = df['High'].rolling(window=window).max()
        df['Low_Min'] = df['Low'].rolling(window=window).min()
        
        df['Signal'] = 0
        df['Signal'] = np.where(df['Close'] > df['High_Max'].shift(1), 1, 
                                np.where(df['Close'] < df['Low_Min'].shift(1), -1, 0))
        return df[['Close', 'High_Max', 'Low_Min', 'Signal']]
    
    # ---------------- RSI Strategy ----------------
    def rsi_strategy(self, period=14, overbought=70, oversold=30):
        df = self.data.copy()
        delta = df['Close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(window=period).mean()
        avg_loss = pd.Series(loss).rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['Signal'] = 0
        df['Signal'] = np.where(df['RSI'] > overbought, -1, np.where(df['RSI'] < oversold, 1, 0))
        return df[['Close', 'RSI', 'Signal']]
