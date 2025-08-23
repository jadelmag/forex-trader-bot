import pandas as pd
import numpy as np

class ForexBacktester:
    def __init__(self, data, initial_balance=10000):
        """
        data: DataFrame con columnas ['Open', 'High', 'Low', 'Close']
        initial_balance: saldo inicial para el backtest
        """
        self.data = data.copy()
        self.initial_balance = initial_balance
    
    # ---------------- Trend Following ----------------
    def trend_following(self, short_window=20, long_window=50):
        df = self.data.copy()
        df['EMA_short'] = df['Close'].ewm(span=short_window, adjust=False).mean()
        df['EMA_long'] = df['Close'].ewm(span=long_window, adjust=False).mean()
        df['Signal'] = 0
        df['Signal'][short_window:] = np.where(df['EMA_short'][short_window:] > df['EMA_long'][short_window:], 1, -1)
        return df
    
    # ---------------- Breakout Strategy ----------------
    def breakout(self, window=20):
        df = self.data.copy()
        df['High_Max'] = df['High'].rolling(window=window).max()
        df['Low_Min'] = df['Low'].rolling(window=window).min()
        df['Signal'] = 0
        df['Signal'] = np.where(df['Close'] > df['High_Max'].shift(1), 1,
                                np.where(df['Close'] < df['Low_Min'].shift(1), -1, 0))
        return df
    
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
        return df
    
    # ---------------- Backtesting genérico ----------------
    def backtest(self, df):
        balance = self.initial_balance
        position = 0  # 1 = comprado, -1 = vendido
        for i in range(1, len(df)):
            signal = df['Signal'].iloc[i]
            price = df['Close'].iloc[i]
            
            # Abrir posición
            if signal == 1 and position <= 0:
                position = 1
                entry_price = price
            elif signal == -1 and position >= 0:
                position = -1
                entry_price = price
            
            # Cerrar posición y calcular ganancias
            if (position == 1 and signal == -1) or (position == -1 and signal == 1):
                balance += (price - entry_price) * position * 1000  # tamaño de lote simulado
                position = signal
                entry_price = price
        # Cerrar última posición
        if position != 0:
            balance += (df['Close'].iloc[-1] - entry_price) * position * 1000
        return balance

    # ---------------- Comparar estrategias ----------------
    def compare_strategies(self):
        results = {}
        for strategy in [self.trend_following, self.breakout, self.rsi_strategy]:
            df_signal = strategy()
            final_balance = self.backtest(df_signal)
            results[strategy.__name__] = final_balance
        return results

# # ---------------- EJEMPLO DE USO ----------------
# data = pd.DataFrame({
#     'Open': np.random.rand(100) * 1.1,
#     'High': np.random.rand(100) * 1.1,
#     'Low': np.random.rand(100) * 1.1,
#     'Close': np.random.rand(100) * 1.1
# })

# forex_bt = ForexBacktester(data)
# comparison = forex_bt.compare_strategies()
# print("Resultado final por estrategia:", comparison)
