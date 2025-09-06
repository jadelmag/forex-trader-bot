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
        # Doji: body is very small relative to total range
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        df['Signal'] = np.where(
            (body <= total_range * 0.1) & (total_range > 0), 1, 0)
        return df

    def hammer(self):
        df = self.data.copy()
        df['Signal'] = 0
        body = abs(df['Close'] - df['Open'])
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        df['Signal'] = np.where((lower_shadow >= 2*body) & (upper_shadow <= body), 1, 0)
        return df

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
        return df

    def spinning_top(self):
        df = self.data.copy()
        # Spinning top: small body with long shadows on both sides
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        df['Signal'] = np.where(
            (body <= total_range * 0.3) & 
            (upper_shadow >= body) & 
            (lower_shadow >= body) & 
            (total_range > 0), 1, 0)
        return df

    def inverted_hammer(self):
        df = self.data.copy()
        df['Signal'] = 0
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        df['Signal'] = np.where((upper_shadow >= 2*body) & (lower_shadow <= body), 1, 0)
        return df

    def marubozu(self):
        """Marubozu pattern: candle with very small or no shadows"""
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        
        # Marubozu: both shadows are very small relative to body
        df['Signal'] = np.where(
            (body > total_range * 0.8) & 
            (upper_shadow <= body * 0.1) & 
            (lower_shadow <= body * 0.1) & 
            (total_range > 0), 
            np.where(df['Close'] > df['Open'], 1, -1), 0)
        return df

    # ---------------- Double Candles ----------------
    def bullish_engulfing(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'] > df['Open']) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Open'] < df['Close'].shift(1)) &
            (df['Close'] > df['Open'].shift(1)), 1, 0)
        return df

    def bearish_engulfing(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'] < df['Open']) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Open'] > df['Close'].shift(1)) &
            (df['Close'] < df['Open'].shift(1)), -1, 0)
        return df

    def piercing_line(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(1) < df['Open'].shift(1)) &  # Previous candle bearish
            (df['Close'] > df['Open']) &  # Current candle bullish
            (df['Open'] < df['Close'].shift(1)) &  # Opens below previous close
            (df['Close'] > (df['Open'].shift(1) + df['Close'].shift(1))/2), 1, 0)  # Closes above midpoint
        return df

    def dark_cloud_cover(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(1) > df['Open'].shift(1)) &  # Previous candle bullish
            (df['Close'] < df['Open']) &  # Current candle bearish
            (df['Open'] > df['Close'].shift(1)) &  # Opens above previous close
            (df['Close'] < (df['Open'].shift(1) + df['Close'].shift(1))/2), -1, 0)  # Closes below midpoint
        return df

    def tweezer_top(self):
        df = self.data.copy()
        # Tweezer top: two candles with similar highs after uptrend
        similar_highs = abs(df['High'] - df['High'].shift(1)) <= (df['High'] + df['High'].shift(1)) * 0.001
        uptrend = df['Close'].shift(2) < df['Close'].shift(1)  # Simple uptrend check
        df['Signal'] = np.where(
            similar_highs & uptrend, -1, 0)
        return df

    def tweezer_bottom(self):
        df = self.data.copy()
        # Tweezer bottom: two candles with similar lows after downtrend
        similar_lows = abs(df['Low'] - df['Low'].shift(1)) <= (df['Low'] + df['Low'].shift(1)) * 0.001
        downtrend = df['Close'].shift(2) > df['Close'].shift(1)  # Simple downtrend check
        df['Signal'] = np.where(
            similar_lows & downtrend, 1, 0)
        return df

    # ---------------- Triple Candles ----------------
    def morning_star(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(2) < df['Open'].shift(2)) &  # First candle bearish
            (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) &  # Middle candle small
            (df['Close'] > df['Open']) &  # Current candle bullish
            (df['Close'] > df['Open'].shift(1)), 1, 0)  # Closes above middle candle open
        return df

    def evening_star(self):
        df = self.data.copy()
        df['Signal'] = np.where(
            (df['Close'].shift(2) > df['Open'].shift(2)) &  # First candle bullish
            (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) &  # Middle candle small
            (df['Close'] < df['Open']) &  # Current candle bearish
            (df['Close'] < df['Open'].shift(1)), -1, 0)  # Closes below middle candle open
        return df

    def three_white_soldiers(self):
        df = self.data.copy()

        # Condiciones base: 3 velas consecutivas alcistas
        cond_bullish = (
            (df['Close'] > df['Open']) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'].shift(2) > df['Open'].shift(2))
        )

        # Cada vela cierra más alto que la anterior
        cond_higher_closes = (
            (df['Close'] > df['Close'].shift(1)) &
            (df['Close'].shift(1) > df['Close'].shift(2))
        )

        # Aperturas dentro del cuerpo de la vela anterior (no gap grande)
        cond_open_within_body = (
            (df['Open'] < df['Close'].shift(1)) &
            (df['Open'] > df['Open'].shift(1))
        )

        # Cuerpos relativamente grandes (evitar dojis)
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()  # promedio de 20 velas
        cond_large_body = (
            (body > 0.5 * avg_body) &
            (body.shift(1) > 0.5 * avg_body.shift(1)) &
            (body.shift(2) > 0.5 * avg_body.shift(2))
        )

        # Cierres cerca del máximo (poca mecha superior)
        upper_shadow = df['High'] - df['Close']
        cond_strong_close = (
            (upper_shadow < (body * 0.3)) &
            (upper_shadow.shift(1) < (body.shift(1) * 0.3)) &
            (upper_shadow.shift(2) < (body.shift(2) * 0.3))
        )

        # Condición de tendencia previa bajista (opcional pero recomendable)
        prev_trend = df['Close'].shift(3).rolling(5).mean()
        cond_prev_downtrend = df['Close'].shift(3) < prev_trend

        # Combinar todas las condiciones
        cond = (
            cond_bullish &
            cond_higher_closes &
            cond_open_within_body &
            cond_large_body &
            cond_strong_close &
            cond_prev_downtrend
        )

        df['Signal'] = np.where(cond, 1, 0)
        return df

    def three_black_crows(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) < df['Open'].shift(2)) &  # First candle bearish
            (df['Close'].shift(1) < df['Open'].shift(1)) &  # Second candle bearish
            (df['Close'] < df['Open']) &  # Third candle bearish
            (df['Close'] < df['Close'].shift(1)) &  # Each closes lower
            (df['Close'].shift(1) < df['Close'].shift(2))
        )
        df['Signal'] = np.where(cond, -1, 0)
        return df

    def three_inside_up(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) < df['Open'].shift(2)) &  # First candle bearish
            (df['Close'].shift(1) > df['Open'].shift(1)) &  # Second candle bullish
            (df['Open'].shift(1) > df['Close'].shift(2)) &  # Second opens above first close
            (df['Close'].shift(1) < df['Open'].shift(2)) &  # Second closes below first open (inside)
            (df['Close'] > df['Open']) &  # Third candle bullish
            (df['Close'] > df['Close'].shift(1))  # Third closes higher than second
        )
        df['Signal'] = np.where(cond, 1, 0)
        return df

    def three_inside_down(self):
        df = self.data.copy()
        cond = (
            (df['Close'].shift(2) > df['Open'].shift(2)) &  # First candle bullish
            (df['Close'].shift(1) < df['Open'].shift(1)) &  # Second candle bearish
            (df['Open'].shift(1) < df['Close'].shift(2)) &  # Second opens below first close
            (df['Close'].shift(1) > df['Open'].shift(2)) &  # Second closes above first open (inside)
            (df['Close'] < df['Open']) &  # Third candle bearish
            (df['Close'] < df['Close'].shift(1))  # Third closes lower than second
        )
        df['Signal'] = np.where(cond, -1, 0)
        return df

    def rising_three_methods(self):
        df = self.data.copy()
        # Rising three methods: long bullish + 3 small bearish + long bullish
        cond = (
            (df['Close'].shift(4) > df['Open'].shift(4)) &  # First: long bullish
            (df['Close'].shift(3) < df['Open'].shift(3)) &  # Second: small bearish
            (df['Close'].shift(2) < df['Open'].shift(2)) &  # Third: small bearish
            (df['Close'].shift(1) < df['Open'].shift(1)) &  # Fourth: small bearish
            (df['Close'] > df['Open']) &  # Fifth: bullish
            # Small candles stay within first candle's range
            (df['High'].shift(3) < df['High'].shift(4)) &
            (df['High'].shift(2) < df['High'].shift(4)) &
            (df['High'].shift(1) < df['High'].shift(4)) &
            (df['Low'].shift(3) > df['Low'].shift(4)) &
            (df['Low'].shift(2) > df['Low'].shift(4)) &
            (df['Low'].shift(1) > df['Low'].shift(4)) &
            # Final candle closes above first candle's high
            (df['Close'] > df['High'].shift(4))
        )
        df['Signal'] = np.where(cond, 1, 0)
        return df

    def falling_three_methods(self):
        df = self.data.copy()
        # Falling three methods: long bearish + 3 small bullish + long bearish
        cond = (
            (df['Close'].shift(4) < df['Open'].shift(4)) &  # First: long bearish
            (df['Close'].shift(3) > df['Open'].shift(3)) &  # Second: small bullish
            (df['Close'].shift(2) > df['Open'].shift(2)) &  # Third: small bullish
            (df['Close'].shift(1) > df['Open'].shift(1)) &  # Fourth: small bullish
            (df['Close'] < df['Open']) &  # Fifth: bearish
            # Small candles stay within first candle's range
            (df['High'].shift(3) < df['High'].shift(4)) &
            (df['High'].shift(2) < df['High'].shift(4)) &
            (df['High'].shift(1) < df['High'].shift(4)) &
            (df['Low'].shift(3) > df['Low'].shift(4)) &
            (df['Low'].shift(2) > df['Low'].shift(4)) &
            (df['Low'].shift(1) > df['Low'].shift(4)) &
            # Final candle closes below first candle's low
            (df['Close'] < df['Low'].shift(4))
        )
        df['Signal'] = np.where(cond, -1, 0)
        return df

    # ---------------- Detect all patterns ----------------
    def detect_all_patterns(self):
        df = self.data.copy()
        pattern_functions = [
            'doji', 'hammer', 'hanging_man', 'shooting_star', 'spinning_top', 'inverted_hammer', 'marubozu',
            'bullish_engulfing', 'bearish_engulfing', 'piercing_line', 'dark_cloud_cover',
            'tweezer_top', 'tweezer_bottom', 'morning_star', 'evening_star',
            'three_white_soldiers', 'three_black_crows', 'three_inside_up', 'three_inside_down',
            'rising_three_methods', 'falling_three_methods'
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

