# patterns/candlestickpatterns.py

import pandas as pd
import numpy as np

DEFAULT_MIN_PATTERNS = 4

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
        # Precompute rolling mean for volatility once to avoid recomputation per pattern
        df['Volatility_Mean_50'] = df['Volatility'].rolling(50).mean()
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
        # Vectorized confidence per-candle. If a single index is given, return scalar; if a collection, return Series.
        try:
            vol_ratio = df['Volume_Ratio']
            vol_mean = df['Volatility_Mean_50']
            vol = df['Volatility']

            base = pd.Series(1.0, index=df.index)
            base = base.where(vol_ratio >= 0.8, base * 0.7)
            base = base.where(~(vol > vol_mean * 1.5), base * 0.6)
            # Clamp to [0.1, 1.0]
            base = base.clip(lower=0.1, upper=1.0)

            # If current_idx is an integer, return scalar for that row
            if isinstance(current_idx, (int, np.integer)):
                if current_idx >= len(df):
                    return 0.5
                return float(base.iloc[current_idx])

            # If current_idx is a scalar Timestamp, map to position
            if hasattr(current_idx, 'timestamp'):
                pos = df.index.get_loc(current_idx)
                return float(base.iloc[pos])

            # For Index/Series/array-like, return aligned Series
            if hasattr(current_idx, '__len__'):
                return base

            # Fallback
            return float(base.iloc[0])
        except Exception:
            # Robust fallback
            if isinstance(current_idx, (int, np.integer)):
                return 0.5
            return pd.Series(0.5, index=df.index)

    # ---------------- Señales anticipadas ----------------

    def _get_partial_signal(self, pattern_type, condition_mask, partial_factor=None, direction=1):
        df = self.data.copy()
        if partial_factor is None:
            partial_factor = self.partial_factor
        # Move towards High for bullish, towards Low for bearish
        partial_close_up = df['Open'] + (df['High'] - df['Open']) * partial_factor
        partial_close_down = df['Open'] - (df['Open'] - df['Low']) * partial_factor
        partial_close = np.where(direction == 1, partial_close_up, partial_close_down)

        partial_cond = condition_mask.copy()
        partial_cond = partial_cond & (
            ((direction == 1) & (partial_close > df['Open'])) |
            ((direction == -1) & (partial_close < df['Open']))
        )

        confidence = self._get_pattern_confidence(pattern_type, df.index) * 0.7
        # confidence can be Series (vectorized) or scalar; np.where handles both when aligned by index
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
        # Use pattern counts (how many patterns point >0 or <0) to avoid losing signals due to high confidence thresholds
        if min_patterns is None:
            min_patterns = self.config.get('min_patterns', DEFAULT_MIN_PATTERNS)
        df = self.detect_all_patterns()

        bullish_patterns = ['hammer', 'bullish_engulfing', 'piercing_line', 'morning_star', 'three_white_soldiers', 'tweezer_bottom', 'inverted_hammer']
        bearish_patterns = ['hanging_man', 'bearish_engulfing', 'dark_cloud_cover', 'evening_star', 'three_black_crows', 'tweezer_top', 'shooting_star']

        # Count signals rather than sum by confidence; a pattern contributes if its signal sign matches
        df['Bullish_Count'] = (df[bullish_patterns] > 0).sum(axis=1)
        df['Bearish_Count'] = (df[bearish_patterns] < 0).sum(axis=1)

        # Final signal resolution
        df['Final_Signal'] = 0
        df.loc[df['Bullish_Count'] >= min_patterns, 'Final_Signal'] = 1
        df.loc[df['Bearish_Count'] >= min_patterns, 'Final_Signal'] = -1

        # If both sides meet the threshold on the same candle, prefer the side with higher count; if equal, keep bearish precedence
        conflict_mask = (df['Bullish_Count'] >= min_patterns) & (df['Bearish_Count'] >= min_patterns)
        higher_bull = conflict_mask & (df['Bullish_Count'] > df['Bearish_Count'])
        higher_bear = conflict_mask & (df['Bearish_Count'] > df['Bullish_Count'])
        equal_counts = conflict_mask & (df['Bullish_Count'] == df['Bearish_Count'])
        df.loc[higher_bull, 'Final_Signal'] = 1
        df.loc[higher_bear, 'Final_Signal'] = -1
        # For equal counts, maintain previous precedence to bearish
        df.loc[equal_counts, 'Final_Signal'] = -1

        return df

    def get_trading_signals(self, min_confidence=None, min_patterns=None):
        if min_confidence is None:
            min_confidence = self.min_confidence
        if min_patterns is None:
            min_patterns = self.config.get('min_patterns', DEFAULT_MIN_PATTERNS)
        df = self.combined_signal_optimized(min_patterns=min_patterns, min_confidence=min_confidence)
        df['Trading_Signal'] = df['Final_Signal']
        return df