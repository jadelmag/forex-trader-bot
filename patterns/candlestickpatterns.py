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
        'bullish_engulfing': 2, 
        'bearish_engulfing': 2, 
        'piercing_line': 2, 
        'dark_cloud_cover': 2,
        'tweezer_top': 2, 
        'tweezer_bottom': 2,
        'morning_star': 3, 
        'evening_star': 3, 
        'three_white_soldiers': 3, 
        'three_black_crows': 3
    }

    @classmethod
    def get_patterns_by_candle_count(cls):
        """Agrupa patrones por número de velas que utilizan."""
        groups = {1: [], 2: [], 3: [], 'other': []}
        
        for pattern, count in cls.PATTERN_CANDLE_COUNTS.items():
            if count in groups:
                groups[count].append(pattern)
            else:
                groups['other'].append(pattern)
        
        return groups

    def __init__(self, data, atr_period=14, trend_period=20, volatility_period=20, config=None):
        self.data = data.copy()
        
        # Aplicar configuración personalizada si se proporciona
        self.config = config or {}
        
        # Parámetros configurables con valores por defecto
        self.atr_period = self.config.get('atr_period', atr_period)
        self.trend_period = self.config.get('trend_period', trend_period)
        self.volatility_period = self.config.get('volatility_period', volatility_period)
        
        # Parámetros específicos de patrones
        self.doji_threshold = self.config.get('doji_threshold', 0.05)
        self.tweezer_tolerance = self.config.get('tweezer_tolerance', 0.001)
        self.min_confidence = self.config.get('min_confidence', 0.6)
        self.partial_factor = self.config.get('partial_factor', 0.5)
        self.hammer_body_ratio = self.config.get('hammer_body_ratio', 1.5)
        self.shooting_star_ratio = self.config.get('shooting_star_ratio', 2.0)
        self.spinning_top_ratio = self.config.get('spinning_top_ratio', 0.3)
        self.marubozu_ratio = self.config.get('marubozu_ratio', 0.8)
        
        self._calculate_indicators(self.atr_period, self.trend_period, self.volatility_period)

    # ---------------- Indicadores ----------------

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
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            df[col] = df[col].bfill().ffill()
        self.data = df

    def _get_pattern_confidence(self, pattern_type, current_idx):
        df = self.data
        # Si current_idx es un array/series, usar el primer elemento
        if hasattr(current_idx, '__len__') and len(current_idx) > 0:
            idx = 0  # Usar el primer índice para calcular confianza general
        elif isinstance(current_idx, (int, np.integer)):
            idx = current_idx
        else:
            idx = 0
            
        if idx >= len(df):
            return 0.5
        confidence = 1.0
        if df['Volume_Ratio'].iloc[idx] < 0.8:
            confidence *= 0.7
        current_volatility = df['Volatility'].iloc[idx]
        if current_volatility > df['Volatility'].rolling(50).mean().iloc[idx] * 1.5:
            confidence *= 0.6
        return max(0.1, min(1.0, confidence))

    # ---------------- Señales anticipadas ----------------

    def _get_partial_signal(self, pattern_type, condition_mask, partial_factor=None, direction=1):
        df = self.data.copy()
        if partial_factor is None:
            partial_factor = self.partial_factor
        partial_close = df['Open'] + (df['High'] - df['Open']) * partial_factor
        partial_cond = condition_mask.copy()
        partial_cond = partial_cond & ((direction == 1) & (partial_close > df['Open']) |
                                       (direction == -1) & (partial_close < df['Open']))
        confidence = self._get_pattern_confidence(pattern_type, df.index) * 0.7
        signal = np.where(partial_cond, confidence * direction, 0)
        return signal

    # ---------------- Patrones de 1 vela ----------------

    def doji(self, threshold=None):
        if threshold is None:
            threshold = self.doji_threshold
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        cond = body / total_range <= threshold
        df['Signal'] = self._get_partial_signal('neutral', cond, direction=1)
        return df

    def hammer(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        cond = (lower_shadow >= self.hammer_body_ratio*body) & (upper_shadow <= body) & (body > 0)
        df['Signal'] = self._get_partial_signal('bullish', cond, direction=1)
        return df

    def hanging_man(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        cond = (lower_shadow >= self.hammer_body_ratio*body) & (upper_shadow <= body) & (body > 0)
        df['Signal'] = self._get_partial_signal('bearish', cond, direction=-1)
        return df

    def shooting_star(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        cond = (upper_shadow >= self.shooting_star_ratio*body) & (lower_shadow <= body)
        df['Signal'] = self._get_partial_signal('bearish', cond, direction=-1)
        return df

    def spinning_top(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        cond = (body <= total_range*self.spinning_top_ratio) & (upper_shadow >= body) & (lower_shadow >= body)
        df['Signal'] = self._get_partial_signal('neutral', cond, direction=1)
        return df

    def inverted_hammer(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        cond = (upper_shadow >= self.shooting_star_ratio*body) & (lower_shadow <= body)
        df['Signal'] = self._get_partial_signal('bullish', cond, direction=1)
        return df

    def marubozu(self):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        cond = (body > total_range*self.marubozu_ratio) & (upper_shadow <= body*0.1) & (lower_shadow <= body*0.1)
        df['Signal'] = self._get_partial_signal('trend', cond, direction=np.sign(df['Close'] - df['Open']))
        return df

    # ---------------- Patrones de 2 velas ----------------

    def bullish_engulfing(self):
        df = self.data.copy()
        cond = (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & \
               (df['Open'] < df['Close'].shift(1)) & (df['Close'] > df['Open'].shift(1))
        df['Signal'] = self._get_partial_signal('bullish', cond, direction=1)
        return df

    def bearish_engulfing(self):
        df = self.data.copy()
        cond = (df['Close'] < df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1)) & \
               (df['Open'] > df['Close'].shift(1)) & (df['Close'] < df['Open'].shift(1))
        df['Signal'] = self._get_partial_signal('bearish', cond, direction=-1)
        return df

    def piercing_line(self):
        df = self.data.copy()
        cond = (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & \
               (df['Open'] < df['Close'].shift(1)) & (df['Close'] > (df['Open'].shift(1) + df['Close'].shift(1))/2)
        df['Signal'] = self._get_partial_signal('bullish', cond, direction=1)
        return df

    def dark_cloud_cover(self):
        df = self.data.copy()
        cond = (df['Close'] < df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1)) & \
               (df['Open'] > df['Close'].shift(1)) & (df['Close'] < (df['Open'].shift(1) + df['Close'].shift(1))/2)
        df['Signal'] = self._get_partial_signal('bearish', cond, direction=-1)
        return df

    def morning_star(self):
        df = self.data.copy()
        cond = (df['Close'].shift(2) < df['Open'].shift(2)) & \
               (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) & \
               (df['Close'] > df['Open'])
        df['Signal'] = self._get_partial_signal('bullish', cond, direction=1)
        return df

    def evening_star(self):
        df = self.data.copy()
        cond = (df['Close'].shift(2) > df['Open'].shift(2)) & \
               (abs(df['Close'].shift(1) - df['Open'].shift(1)) < abs(df['Close'].shift(2) - df['Open'].shift(2))/2) & \
               (df['Close'] < df['Open'])
        df['Signal'] = self._get_partial_signal('bearish', cond, direction=-1)
        return df

    def tweezer_top(self, tolerance=None):
        if tolerance is None:
            tolerance = self.tweezer_tolerance
        df = self.data.copy()
        cond = (df['Close'] < df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1)) & \
               (abs(df['High'] - df['High'].shift(1)) <= df['High'] * tolerance)
        df['Signal'] = self._get_partial_signal('bearish', cond, direction=-1)
        return df

    def tweezer_bottom(self, tolerance=None):
        if tolerance is None:
            tolerance = self.tweezer_tolerance
        df = self.data.copy()
        cond = (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & \
               (abs(df['Low'] - df['Low'].shift(1)) <= df['Low'] * tolerance)
        df['Signal'] = self._get_partial_signal('bullish', cond, direction=1)
        return df

    # ---------------- Patrones de 3 velas ----------------

    def three_white_soldiers(self):
        df = self.data.copy()
        cond = (df['Close'] > df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1)) & \
               (df['Close'].shift(2) > df['Open'].shift(2)) & (df['Close'] > df['Close'].shift(1)) & (df['Close'].shift(1) > df['Close'].shift(2))
        df['Signal'] = self._get_partial_signal('bullish', cond, direction=1)
        return df

    def three_black_crows(self):
        df = self.data.copy()
        cond = (df['Close'] < df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & \
               (df['Close'].shift(2) < df['Open'].shift(2)) & (df['Close'] < df['Close'].shift(1)) & (df['Close'].shift(1) < df['Close'].shift(2))
        df['Signal'] = self._get_partial_signal('bearish', cond, direction=-1)
        return df

    # ---------------- Señales combinadas ----------------

    def detect_all_patterns(self):
        df = self.data.copy()
        pattern_methods = list(self.PATTERN_CANDLE_COUNTS.keys())
        for method in pattern_methods:
            try:
                result_df = getattr(self, method)()
                df[method] = result_df['Signal']
            except Exception as e:
                print(f"Error calculando {method}: {e}")
                df[method] = 0
        return df

    def combined_signal_optimized(self, min_patterns=None, min_confidence=None):
        if min_patterns is None:
            min_patterns = self.config.get('min_patterns', 1)
        if min_confidence is None:
            min_confidence = self.min_confidence
        df = self.detect_all_patterns()
        bullish_patterns = ['hammer', 'bullish_engulfing', 'piercing_line', 'morning_star', 'three_white_soldiers', 'tweezer_bottom']
        bearish_patterns = ['hanging_man', 'bearish_engulfing', 'dark_cloud_cover', 'evening_star', 'three_black_crows', 'tweezer_top']
        df['Bullish_Score'] = df[bullish_patterns].apply(lambda row: sum(val for val in row if val >= min_confidence), axis=1)
        df['Bearish_Score'] = df[bearish_patterns].apply(lambda row: sum(val for val in row if val <= -min_confidence), axis=1)
        df['Final_Signal'] = 0
        df.loc[df['Bullish_Score'] >= min_patterns, 'Final_Signal'] = 1
        df.loc[df['Bearish_Score'] >= min_patterns, 'Final_Signal'] = -1
        return df

    def get_trading_signals(self, min_confidence=None, min_patterns=None):
        if min_confidence is None:
            min_confidence = self.min_confidence
        if min_patterns is None:
            min_patterns = self.config.get('min_patterns', 1)
        df = self.combined_signal_optimized(min_patterns=min_patterns, min_confidence=min_confidence)
        df['Trading_Signal'] = df['Final_Signal']
        return df