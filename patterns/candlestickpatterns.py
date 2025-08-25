# patterns/candlestickpatterns.py

import pandas as pd
import numpy as np

class CandlestickPatterns:
    def __init__(self, data):
        """
        data: DataFrame con columnas ['Open', 'High', 'Low', 'Close']
        """
        self.data = data.copy()

    # ---------------- Single Candles ----------------
    def doji(self):
        df = self.data.copy()
        df['Signal'] = np.where(abs(df['Close'] - df['Open']) <= (df['High'] - df['Low'])*0.1, 0, 0)
        return df[['Open','High','Low','Close','Signal']]

    def hammer(self):
        df = self.data.copy()
        df['Signal'] = 0
        body = abs(df['Close'] - df['Open'])
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        df['Signal'] = np.where((lower_shadow >= 2*body) & (upper_shadow <= body), 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def hanging_man(self):
        df = self.hammer()
        df['Signal'] = np.where(df['Signal'] == 1, -1, 0)
        return df

    def shooting_star(self):
        df = self.data.copy()
        df['Signal'] = 0
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        df['Signal'] = np.where((upper_shadow >= 2*body) & (lower_shadow <= body), -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def spinning_top(self):
        df = self.data.copy()
        df['Signal'] = np.where(abs(df['Close'] - df['Open']) <= (df['High'] - df['Low'])*0.3, 0, 0)
        return df[['Open','High','Low','Close','Signal']]

    def inverted_hammer(self):
        df = self.data.copy()
        df['Signal'] = 0
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        df['Signal'] = np.where((upper_shadow >= 2*body) & (lower_shadow <= body), 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    # ---------------- Double Candles ----------------
    def bullish_engulfing(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'] > df['Open']) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Open'] < df['Close'].shift(1)) &
            (df['Close'] > df['Open'].shift(1)), 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def bearish_engulfing(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'] < df['Open']) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Open'] > df['Close'].shift(1)) &
            (df['Close'] < df['Open'].shift(1)), -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def piercing_line(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] > (df['Open'].shift(1) + df['Close'].shift(1))/2) &
            (df['Open'] < df['Close'].shift(1)), 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def dark_cloud_cover(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] < (df['Open'].shift(1) + df['Close'].shift(1))/2) &
            (df['Open'] > df['Close'].shift(1)), -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def tweezer_top(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['High'].shift(1).round(5) == df['High'].round(5)), -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def tweezer_bottom(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Low'].shift(1).round(5) == df['Low'].round(5)), 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    # ---------------- Triple Candles ----------------
    def morning_star(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) &
            (df['Close'] > df['Open'].shift(1)), 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def evening_star(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) &
            (df['Close'] < df['Open'].shift(1)), -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def three_white_soldiers(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] > df['Open']) &
            (df['Close'] > df['Close'].shift(1)) &
            (df['Close'].shift(1) > df['Close'].shift(2))
        )
        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def three_black_crows(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] < df['Open']) &
            (df['Close'] < df['Close'].shift(1)) &
            (df['Close'].shift(1) < df['Close'].shift(2))
        )
        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def three_inside_up(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] > df['Open'].shift(2))
        )
        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def three_inside_down(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] < df['Open'].shift(2))
        )
        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def rising_three_methods(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(4) < df['Open'].shift(4)) &
            (df['Close'].shift(3) < df['Open'].shift(3)) &
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] > df['Open'].shift(4))
        )
        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def falling_three_methods(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(4) > df['Open'].shift(4)) &
            (df['Close'].shift(3) > df['Open'].shift(3)) &
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] < df['Open'].shift(4))
        )
        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    # ---------------- Detect all patterns ----------------
    def detect_all_patterns(self):
        df = self.data.copy()
        pattern_functions = [
            'doji', 'hammer', 'hanging_man', 'shooting_star', 'spinning_top', 'inverted_hammer',
            'bullish_engulfing', 'bearish_engulfing', 'piercing_line', 'dark_cloud_cover',
            'tweezer_top', 'tweezer_bottom',
            'morning_star', 'evening_star', 'three_white_soldiers', 'three_black_crows',
            'three_inside_up', 'three_inside_down', 'rising_three_methods', 'falling_three_methods'
        ]
        for func_name in pattern_functions:
            func = getattr(self, func_name)
            df[func_name] = func()['Signal']
        return df

    # ---------------- Combined signal optimized ----------------
    def combined_signal_optimized(self):
        df = self.detect_all_patterns().copy()
        pattern_cols = df.columns.difference(['Open','High','Low','Close'])
        has_bull = (df[pattern_cols] == 1).any(axis=1)
        has_bear = (df[pattern_cols] == -1).any(axis=1)
        df['Final_Signal'] = 0
        df.loc[has_bull & ~has_bear, 'Final_Signal'] = 1
        df.loc[has_bear & ~has_bull, 'Final_Signal'] = -1
        return df

# # ---------------- Example usage ----------------
# if __name__ == "__main__":
#     # Simulated data
#     data = pd.DataFrame({
#         'Open': np.random.rand(100)*1.1,
#         'High': np.random.rand(100)*1.1,
#         'Low': np.random.rand(100)*1.1,
#         'Close': np.random.rand(100)*1.1
#     })

#     patterns = CandlestickPatterns(data)
    
#     # Detect all patterns
#     all_signals = patterns.detect_all_patterns()
#     print(all_signals.head())

#     # Get combined final signal
#     final_signals = patterns.combined_signal_optimized()
#     print(final_signals[['Open','High','Low','Close','Final_Signal']].head())
