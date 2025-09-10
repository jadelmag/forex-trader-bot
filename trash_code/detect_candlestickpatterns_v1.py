# patterns/candlestickpatterns.py

import pandas as pd
import numpy as np

class CandlestickPatterns:
    PATTERN_CANDLE_COUNTS = {
        'doji': 1,
        'hammer': 1,
        'hanging_man': 1,
        'shooting_star': 1,
        'spinning_top': 1,
        'inverted_hammer': 1,
        'marubozu': 1,
        'bullish_engulfing': 2,
        'bearish_engulfing': 2,
        'piercing_line': 2,
        'dark_cloud_cover': 2,
        'tweezer_top': 2,
        'tweezer_bottom': 2,
        'morning_star': 3,
        'evening_star': 3,
        'three_white_soldiers': 3,
        'three_black_crows': 3,
    }

    def __init__(self, data, atr_period=14, trend_period=20, volatility_period=20):
        self.data = data.copy()
        self._calculate_indicators(atr_period, trend_period, volatility_period)

    def _calculate_indicators(self, atr_period, trend_period, volatility_period):
        df = self.data
        high_low = df['High'] - df['Low']
        high_close_prev = abs(df['High'] - df['Close'].shift(1))
        low_close_prev = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        df['ATR'] = df['TR'].ewm(span=atr_period, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(trend_period).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['Volatility'] = df['Close'].pct_change().rolling(volatility_period).std()
        if 'Volume' in df.columns:
            df['Volume_MA'] = df['Volume'].rolling(20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        else:
            df['Volume_MA'] = 1.0
            df['Volume_Ratio'] = 1.0
        self.data = df

    def _get_pattern_confidence(self, pattern_type, idx):
        df = self.data
        if idx >= len(df):
            return 0.5
        confidence = 1.0
        if df['Volume_Ratio'].iloc[idx] < 0.8:
            confidence *= 0.8
        current_vol = df['Volatility'].iloc[idx]
        if current_vol > df['Volatility'].rolling(50).mean().iloc[idx] * 1.5:
            confidence *= 0.7
        if pattern_type == 'bullish':
            confidence *= 1.0
        elif pattern_type == 'bearish':
            confidence *= 1.0
        elif pattern_type == 'neutral':
            confidence *= 0.9
        return max(0.1, min(1.0, confidence))

    # -------------------- PATRONES PARA SEÑALES PARCIALES --------------------

    def doji(self, threshold=0.05):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(total_range > 0, np.clip((threshold - body/total_range)*self._get_pattern_confidence('neutral', df.index), 0, 1), 0)
        return df

    def hammer(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        # MODIFICAR AQUÍ para evaluar la vela mientras se forma
        df['Signal'] = np.where((lower_shadow >= 1.5*body) & (upper_shadow <= body) & (body>0), self._get_pattern_confidence('bullish', df.index), 0)
        return df

    def hanging_man(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where((lower_shadow >= 1.5*body) & (upper_shadow <= body) & (body>0), -self._get_pattern_confidence('bearish', df.index), 0)
        return df

    def shooting_star(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        df['Signal'] = np.where((upper_shadow >= 2*body) & (lower_shadow <= body), -self._get_pattern_confidence('bearish', df.index), 0)
        return df

    def spinning_top(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where((body <= total_range*0.3) & (upper_shadow >= body) & (lower_shadow >= body), self._get_pattern_confidence('neutral', df.index), 0)
        return df

    def inverted_hammer(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where((upper_shadow >= 2*body) & (lower_shadow <= body), self._get_pattern_confidence('bullish', df.index), 0)
        return df

    def marubozu(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        is_marubozu = (body > 0.8*(upper_shadow + lower_shadow + body)) & (upper_shadow <= 0.1*body) & (lower_shadow <= 0.1*body)
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(is_marubozu, np.sign(df['Close'] - df['Open'])*self._get_pattern_confidence('trend', df.index), 0)
        return df

    def bullish_engulfing(self):
        df = self.data.copy()
        prev_close = df['Close'].shift(1)
        prev_open = df['Open'].shift(1)
        current_bullish = df['Close'] > df['Open']
        prev_bearish = prev_close < prev_open
        engulfing = (df['Open'] < prev_close) & (df['Close'] > prev_open)
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(current_bullish & prev_bearish & engulfing, self._get_pattern_confidence('bullish', df.index), 0)
        return df

    def bearish_engulfing(self):
        df = self.data.copy()
        prev_close = df['Close'].shift(1)
        prev_open = df['Open'].shift(1)
        current_bearish = df['Close'] < df['Open']
        prev_bullish = prev_close > prev_open
        engulfing = (df['Open'] > prev_close) & (df['Close'] < prev_open)
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(current_bearish & prev_bullish & engulfing, -self._get_pattern_confidence('bearish', df.index), 0)
        return df

    def piercing_line(self):
        df = self.data.copy()
        prev_close = df['Close'].shift(1)
        prev_open = df['Open'].shift(1)
        current_bullish = df['Close'] > df['Open']
        opens_below = df['Open'] < prev_close
        closes_above_mid = df['Close'] > (prev_open + prev_close)/2
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(prev_close < prev_open & current_bullish & opens_below & closes_above_mid, self._get_pattern_confidence('bullish', df.index), 0)
        return df

    def dark_cloud_cover(self):
        df = self.data.copy()
        prev_close = df['Close'].shift(1)
        prev_open = df['Open'].shift(1)
        current_bearish = df['Close'] < df['Open']
        opens_above = df['Open'] > prev_close
        closes_below_mid = df['Close'] < (prev_open + prev_close)/2
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(prev_close > prev_open & current_bearish & opens_above & closes_below_mid, -self._get_pattern_confidence('bearish', df.index), 0)
        return df

    def morning_star(self):
        df = self.data.copy()
        first_bearish = df['Close'].shift(2) < df['Open'].shift(2)
        third_bullish = df['Close'] > df['Open']
        middle_small = abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2
        df['Signal'] = np.where(first_bearish & middle_small & third_bullish, self._get_pattern_confidence('bullish', df.index), 0)
        return df

    def evening_star(self):
        df = self.data.copy()
        first_bullish = df['Close'].shift(2) > df['Open'].shift(2)
        third_bearish = df['Close'] < df['Open']
        middle_small = abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(first_bullish & middle_small & third_bearish, -self._get_pattern_confidence('bearish', df.index), 0)
        return df

    def three_white_soldiers(self):
        df = self.data.copy()
        cond = (df['Close'] > df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1)) & (df['Close'].shift(2) > df['Open'].shift(2))
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(cond & (df['Close'] > df['Close'].shift(1)) & (df['Close'].shift(1) > df['Close'].shift(2)), self._get_pattern_confidence('bullish', df.index), 0)
        return df

    def three_black_crows(self):
        df = self.data.copy()
        cond = (df['Close'] < df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'].shift(2) < df['Open'].shift(2))
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where(cond & (df['Close'] < df['Close'].shift(1)) & (df['Close'].shift(1) < df['Close'].shift(2)), -self._get_pattern_confidence('bearish', df.index), 0)
        return df

    def tweezer_top(self, tolerance=0.001):
        df = self.data.copy()
        tops_aligned = abs(df['High'] - df['High'].shift(1)) <= df['High']*tolerance
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where((df['Close'] < df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1)) & tops_aligned, -self._get_pattern_confidence('bearish', df.index), 0)
        return df

    def tweezer_bottom(self, tolerance=0.001):
        df = self.data.copy()
        bottoms_aligned = abs(df['Low'] - df['Low'].shift(1)) <= df['Low']*tolerance
        # MODIFICAR AQUÍ para detectar antes de cierre usando Close parcial
        df['Signal'] = np.where((df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & bottoms_aligned, self._get_pattern_confidence('bullish', df.index), 0)
        return df

    # -------------------- MÉTODOS DE COMBINACIÓN --------------------

    def detect_all_patterns(self):
        df = self.data.copy()
        for method in self.PATTERN_CANDLE_COUNTS.keys():
            if hasattr(self, method):
                try:
                    df[method] = getattr(self, method)()['Signal']
                except Exception as e:
                    print(f"Error calculando {method}: {e}")
                    df[method] = 0
        return df

    def combined_signal_optimized(self, min_patterns=1, min_confidence=0.6):
        df = self.detect_all_patterns()
        
        bullish_patterns = ['hammer', 'bullish_engulfing', 'piercing_line', 'morning_star', 'three_white_soldiers', 'tweezer_bottom']
        bearish_patterns = ['hanging_man', 'bearish_engulfing', 'dark_cloud_cover', 'evening_star', 'three_black_crows', 'tweezer_top']
        
        # Sumar señales ponderadas
        df['Bullish_Score'] = df[bullish_patterns].apply(lambda row: sum(val for val in row if val >= min_confidence), axis=1)
        df['Bearish_Score'] = df[bearish_patterns].apply(lambda row: sum(val for val in row if val <= -min_confidence), axis=1)
        
        # Generar señal final si hay suficientes patrones
        df['Final_Signal'] = 0
        df.loc[df['Bullish_Score'] >= min_patterns, 'Final_Signal'] = 1
        df.loc[df['Bearish_Score'] >= min_patterns, 'Final_Signal'] = -1
        
        return df

    def get_trading_signals(self, min_confidence=0.6, min_patterns=1):
        df = self.combined_signal_optimized(min_patterns=min_patterns, min_confidence=min_confidence)
        df['Trading_Signal'] = df['Final_Signal']
        return df
