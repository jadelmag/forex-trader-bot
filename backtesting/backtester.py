# backtesting/backtester.py

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
        
        # Use .iloc for positional indexing
        ema_short = df['EMA_short'].iloc[short_window:].values
        ema_long = df['EMA_long'].iloc[short_window:].values
        df.iloc[short_window:, df.columns.get_loc('Signal')] = np.where(
            ema_short > ema_long, 1, -1
        )
        return df

    # ---------------- Breakout Strategy ----------------
    def breakout(self, window=20):
        df = self.data.copy()
        df['High_Max'] = df['High'].rolling(window=window).max()
        df['Low_Min'] = df['Low'].rolling(window=window).min()
        df['Signal'] = 0
        # Fixed chained assignment
        condition_high = df['Close'] > df['High_Max'].shift(1)
        condition_low = df['Close'] < df['Low_Min'].shift(1)
        df.loc[:, 'Signal'] = np.select(
            [condition_high, condition_low],
            [1, -1],
            default=0
        )
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
        # Fixed chained assignment
        conditions = [
            df['RSI'] > overbought,
            df['RSI'] < oversold
        ]
        choices = [-1, 1]
        df.loc[:, 'Signal'] = np.select(conditions, choices, default=0)
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

    def backtest_with_events(self, df):
        """Igual que backtest(), pero devuelve también los eventos de compra/venta.
        Retorna: (balance_final, events)
        events: lista de dicts { 'type': 'BUY'|'SELL', 'time': index, 'price': float }
        """
        balance = self.initial_balance
        position = 0
        entry_price = None
        events = []
        for i in range(1, len(df)):
            signal = df['Signal'].iloc[i]
            price = df['Close'].iloc[i]
            time = df.index[i] if hasattr(df, 'index') else i

            # Abrir posición
            if signal == 1 and position <= 0:
                position = 1
                entry_price = price
                events.append({'type': 'BUY', 'time': time, 'price': float(price)})
            elif signal == -1 and position >= 0:
                position = -1
                entry_price = price
                events.append({'type': 'SELL', 'time': time, 'price': float(price)})

            # Cerrar posición y calcular ganancias al cambio de señal opuesta
            if (position == 1 and signal == -1) or (position == -1 and signal == 1):
                balance += (price - entry_price) * position * 1000
                # posición cambia a la nueva señal (ya hecho arriba)

        # Cerrar última posición al final del dataset
        if position != 0 and entry_price is not None:
            last_price = df['Close'].iloc[-1]
            balance += (last_price - entry_price) * position * 1000
        return balance, events

    # ---------------- Comparar estrategias ----------------
    def compare_strategies(self):
        results = {}
        for strategy in [self.trend_following, self.breakout, self.rsi_strategy]:
            df_signal = strategy()
            final_balance = self.backtest(df_signal)
            results[strategy.__name__] = final_balance
        return results
