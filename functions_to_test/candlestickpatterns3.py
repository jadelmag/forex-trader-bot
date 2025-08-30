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
    def doji_pattern(self):
        df = self.data.copy()
        df['Doji_Signal'] = np.where(abs(df['Close'] - df['Open']) <= (df['High'] - df['Low'])*0.1, 0, 0)
        return df[['Open','High','Low','Close','Doji_Signal']]

    def hammer_pattern(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        df['Hammer_Signal'] = np.where((lower_shadow >= 2*body) & (upper_shadow <= body), 1, 0)
        return df[['Open','High','Low','Close','Hammer_Signal']]

    def hanging_man_pattern(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        df['Hanging_Man_Signal'] = np.where((lower_shadow >= 2*body) & (upper_shadow <= body), -1, 0)
        return df[['Open','High','Low','Close','Hanging_Man_Signal']]

    def shooting_star_pattern(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        df['Shooting_Star_Signal'] = np.where((upper_shadow >= 2*body) & (lower_shadow <= body), -1, 0)
        return df[['Open','High','Low','Close','Shooting_Star_Signal']]

    def spinning_top_pattern(self):
        df = self.data.copy()
        df['Spinning_Top_Signal'] = np.where(abs(df['Close'] - df['Open']) <= (df['High'] - df['Low'])*0.3, 0, 0)
        return df[['Open','High','Low','Close','Spinning_Top_Signal']]

    def inverted_hammer_pattern(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        df['Inverted_Hammer_Signal'] = np.where((upper_shadow >= 2*body) & (lower_shadow <= body), 1, 0)
        return df[['Open','High','Low','Close','Inverted_Hammer_Signal']]

    # ---------------- Double Candles ----------------
    def bullish_engulfing_pattern(self):
        df = self.data.copy()
        df['Bullish_Engulfing_Signal'] = np.where(
            (df['Close'] > df['Open']) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Open'] < df['Close'].shift(1)) &
            (df['Close'] > df['Open'].shift(1)), 1, 0)
        return df[['Open','High','Low','Close','Bullish_Engulfing_Signal']]

    def bearish_engulfing_pattern(self):
        df = self.data.copy()
        df['Bearish_Engulfing_Signal'] = np.where(
            (df['Close'] < df['Open']) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Open'] > df['Close'].shift(1)) &
            (df['Close'] < df['Open'].shift(1)), -1, 0)
        return df[['Open','High','Low','Close','Bearish_Engulfing_Signal']]

    def piercing_line_pattern(self):
        df = self.data.copy()
        df['Piercing_Line_Signal'] = np.where(
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] > (df['Open'].shift(1) + df['Close'].shift(1))/2) &
            (df['Open'] < df['Close'].shift(1)), 1, 0)
        return df[['Open','High','Low','Close','Piercing_Line_Signal']]

    def dark_cloud_cover_pattern(self):
        df = self.data.copy()
        df['Dark_Cloud_Cover_Signal'] = np.where(
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] < (df['Open'].shift(1) + df['Close'].shift(1))/2) &
            (df['Open'] > df['Close'].shift(1)), -1, 0)
        return df[['Open','High','Low','Close','Dark_Cloud_Cover_Signal']]

    def tweezer_top_pattern(self):
        df = self.data.copy()
        df['Tweezer_Top_Signal'] = np.where(
            (df['High'].shift(1).round(5) == df['High'].round(5)), -1, 0)
        return df[['Open','High','Low','Close','Tweezer_Top_Signal']]

    def tweezer_bottom_pattern(self):
        df = self.data.copy()
        df['Tweezer_Bottom_Signal'] = np.where(
            (df['Low'].shift(1).round(5) == df['Low'].round(5)), 1, 0)
        return df[['Open','High','Low','Close','Tweezer_Bottom_Signal']]

    # ---------------- Triple Candles ----------------
    def morning_star_pattern(self):
        df = self.data.copy()
        df['Morning_Star_Signal'] = np.where(
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) &
            (df['Close'] > df['Open'].shift(1)), 1, 0)
        return df[['Open','High','Low','Close','Morning_Star_Signal']]

    def evening_star_pattern(self):
        df = self.data.copy()
        df['Evening_Star_Signal'] = np.where(
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) &
            (df['Close'] < df['Open'].shift(1)), -1, 0)
        return df[['Open','High','Low','Close','Evening_Star_Signal']]

    def three_white_soldiers_pattern(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] > df['Open']) &
            (df['Close'] > df['Close'].shift(1)) &
            (df['Close'].shift(1) > df['Close'].shift(2))
        )
        df['Three_White_Soldiers_Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','Three_White_Soldiers_Signal']]

    def three_black_crows_pattern(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] < df['Open']) &
            (df['Close'] < df['Close'].shift(1)) &
            (df['Close'].shift(1) < df['Close'].shift(2))
        )
        df['Three_Black_Crows_Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','Three_Black_Crows_Signal']]

    def three_inside_up_pattern(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] > df['Open'].shift(2))
        )
        df['Three_Inside_Up_Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','Three_Inside_Up_Signal']]

    def three_inside_down_pattern(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] < df['Open'].shift(2))
        )
        df['Three_Inside_Down_Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','Three_Inside_Down_Signal']]

    def rising_three_methods_pattern(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(4) < df['Open'].shift(4)) &
            (df['Close'].shift(3) < df['Open'].shift(3)) &
            (df['Close'].shift(2) < df['Open'].shift(2)) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'] > df['Open'].shift(4))
        )
        df['Rising_Three_Methods_Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','Rising_Three_Methods_Signal']]

    def falling_three_methods_pattern(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(4) > df['Open'].shift(4)) &
            (df['Close'].shift(3) > df['Open'].shift(3)) &
            (df['Close'].shift(2) > df['Open'].shift(2)) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'] < df['Open'].shift(4))
        )
        df['Falling_Three_Methods_Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','Falling_Three_Methods_Signal']]

    # ---------------- Detect all patterns ----------------
    def detect_all_patterns(self):
        df = self.data.copy()
        pattern_functions = [
            'doji_pattern', 'hammer_pattern', 'hanging_man_pattern', 'shooting_star_pattern', 
            'spinning_top_pattern', 'inverted_hammer_pattern',
            'bullish_engulfing_pattern', 'bearish_engulfing_pattern', 'piercing_line_pattern', 
            'dark_cloud_cover_pattern', 'tweezer_top_pattern', 'tweezer_bottom_pattern',
            'morning_star_pattern', 'evening_star_pattern', 'three_white_soldiers_pattern', 
            'three_black_crows_pattern', 'three_inside_up_pattern', 'three_inside_down_pattern', 
            'rising_three_methods_pattern', 'falling_three_methods_pattern'
        ]
        
        for func_name in pattern_functions:
            func = getattr(self, func_name)
            result_df = func()
            signal_col = [col for col in result_df.columns if col.endswith('_Signal')][0]
            df[signal_col] = result_df[signal_col]
        
        return df

    # ---------------- Combined signal optimized ----------------
    def combined_signal_optimized(self):
        df = self.detect_all_patterns().copy()
        pattern_cols = [col for col in df.columns if col.endswith('_Signal')]
        
        has_bull = (df[pattern_cols] == 1).any(axis=1)
        has_bear = (df[pattern_cols] == -1).any(axis=1)
        
        df['Final_Signal'] = 0
        df.loc[has_bull & ~has_bear, 'Final_Signal'] = 1
        df.loc[has_bear & ~has_bull, 'Final_Signal'] = -1
        
        return df

    # ---------------- Get pattern names for reference ----------------
    def get_pattern_names(self):
        """Retorna lista de todos los nombres de patrones disponibles"""
        return [
            'Doji', 'Hammer', 'Hanging_Man', 'Shooting_Star', 'Spinning_Top', 'Inverted_Hammer',
            'Bullish_Engulfing', 'Bearish_Engulfing', 'Piercing_Line', 'Dark_Cloud_Cover',
            'Tweezer_Top', 'Tweezer_Bottom', 'Morning_Star', 'Evening_Star', 
            'Three_White_Soldiers', 'Three_Black_Crows', 'Three_Inside_Up', 'Three_Inside_Down',
            'Rising_Three_Methods', 'Falling_Three_Methods'
        ]