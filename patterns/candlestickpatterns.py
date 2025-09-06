# patterns/candlestickpatterns.py

import pandas as pd
import numpy as np

class CandlestickPatterns:
    def __init__(self, data, atr_period=14, trend_period=20, volatility_period=20):
        """
        data: DataFrame con columnas ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self._calculate_indicators(atr_period, trend_period, volatility_period)
    
    def _calculate_indicators(self, atr_period, trend_period, volatility_period):
        """Calcula indicadores técnicos necesarios"""
        df = self.data
        
        # Calcular True Range (TR) de manera vectorizada
        high_low = df['High'] - df['Low']
        high_close_prev = abs(df['High'] - df['Close'].shift(1))
        low_close_prev = abs(df['Low'] - df['Close'].shift(1))
        
        df['TR'] = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        df['ATR'] = df['TR'].rolling(atr_period).mean()
        
        # Tendencia
        df['SMA_20'] = df['Close'].rolling(trend_period).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Volatilidad
        df['Volatility'] = df['Close'].pct_change().rolling(volatility_period).std()
        
        # Volume analysis
        if 'Volume' in df.columns:
            df['Volume_MA'] = df['Volume'].rolling(20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        else:
            df['Volume_MA'] = 1.0
            df['Volume_Ratio'] = 1.0
        
        # Llenar NaN values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            df[col] = df[col].bfill().ffill()
        
        self.data = df

    def _get_pattern_confidence(self, pattern_type, current_idx):
        """Calcula la confianza del patrón (0.0 a 1.0)"""
        df = self.data
        
        if current_idx >= len(df):
            return 0.5
            
        confidence = 1.0
        
        # Volume confirmation
        if df['Volume_Ratio'].iloc[current_idx] < 0.8:
            confidence *= 0.7
        
        # Volatility adjustment
        current_volatility = df['Volatility'].iloc[current_idx]
        if current_volatility > df['Volatility'].rolling(50).mean().iloc[current_idx] * 1.5:
            confidence *= 0.6
        
        return max(0.1, min(1.0, confidence))

    # ---------------- Todos los métodos requeridos ----------------
    
    def doji(self, threshold=0.05):
        df = self.data.copy()
        body = abs(df['Close'] - df['Open'])
        total_range = df['High'] - df['Low']
        
        signals = []
        for i in range(len(df)):
            if total_range.iloc[i] > 0:
                body_ratio = body.iloc[i] / total_range.iloc[i]
                confidence = self._get_pattern_confidence('neutral', i)
                signal = confidence if body_ratio <= threshold else 0
            else:
                signal = 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def hammer(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            lower_shadow = min(df['Open'].iloc[i], df['Close'].iloc[i]) - df['Low'].iloc[i]
            upper_shadow = df['High'].iloc[i] - max(df['Open'].iloc[i], df['Close'].iloc[i])
            
            is_hammer = (lower_shadow >= 1.5 * body and upper_shadow <= body and body > 0)
            confidence = self._get_pattern_confidence('bullish', i)
            
            signal = confidence if is_hammer else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def hanging_man(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            lower_shadow = min(df['Open'].iloc[i], df['Close'].iloc[i]) - df['Low'].iloc[i]
            upper_shadow = df['High'].iloc[i] - max(df['Open'].iloc[i], df['Close'].iloc[i])
            
            is_pattern = (lower_shadow >= 1.5 * body and upper_shadow <= body and body > 0)
            confidence = self._get_pattern_confidence('bearish', i)
            
            signal = -confidence if is_pattern else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def shooting_star(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            upper_shadow = df['High'].iloc[i] - max(df['Open'].iloc[i], df['Close'].iloc[i])
            lower_shadow = min(df['Open'].iloc[i], df['Close'].iloc[i]) - df['Low'].iloc[i]
            
            is_pattern = (upper_shadow >= 2 * body and lower_shadow <= body)
            confidence = self._get_pattern_confidence('bearish', i)
            
            signal = -confidence if is_pattern else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def spinning_top(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            total_range = df['High'].iloc[i] - df['Low'].iloc[i]
            upper_shadow = df['High'].iloc[i] - max(df['Open'].iloc[i], df['Close'].iloc[i])
            lower_shadow = min(df['Open'].iloc[i], df['Close'].iloc[i]) - df['Low'].iloc[i]
            
            is_pattern = (body <= total_range * 0.3 and upper_shadow >= body and lower_shadow >= body)
            confidence = self._get_pattern_confidence('neutral', i)
            
            signal = confidence if is_pattern else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def inverted_hammer(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            upper_shadow = df['High'].iloc[i] - max(df['Open'].iloc[i], df['Close'].iloc[i])
            lower_shadow = min(df['Open'].iloc[i], df['Close'].iloc[i]) - df['Low'].iloc[i]
            
            is_pattern = (upper_shadow >= 2 * body and lower_shadow <= body)
            confidence = self._get_pattern_confidence('bullish', i)
            
            signal = confidence if is_pattern else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def marubozu(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
            total_range = df['High'].iloc[i] - df['Low'].iloc[i]
            upper_shadow = df['High'].iloc[i] - max(df['Open'].iloc[i], df['Close'].iloc[i])
            lower_shadow = min(df['Open'].iloc[i], df['Close'].iloc[i]) - df['Low'].iloc[i]
            
            is_marubozu = (body > total_range * 0.8 and upper_shadow <= body * 0.1 and lower_shadow <= body * 0.1)
            
            if is_marubozu:
                signal = 1 if df['Close'].iloc[i] > df['Open'].iloc[i] else -1
                confidence = self._get_pattern_confidence('trend', i)
                signal *= confidence
            else:
                signal = 0
                
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def bullish_engulfing(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 1:
                signals.append(0)
                continue
                
            current_bullish = df['Close'].iloc[i] > df['Open'].iloc[i]
            prev_bearish = df['Close'].iloc[i-1] < df['Open'].iloc[i-1]
            engulfing = (df['Open'].iloc[i] < df['Close'].iloc[i-1] and df['Close'].iloc[i] > df['Open'].iloc[i-1])
            
            confidence = self._get_pattern_confidence('bullish', i)
            signal = confidence if (current_bullish and prev_bearish and engulfing) else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def bearish_engulfing(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 1:
                signals.append(0)
                continue
                
            current_bearish = df['Close'].iloc[i] < df['Open'].iloc[i]
            prev_bullish = df['Close'].iloc[i-1] > df['Open'].iloc[i-1]
            engulfing = (df['Open'].iloc[i] > df['Close'].iloc[i-1] and df['Close'].iloc[i] < df['Open'].iloc[i-1])
            
            confidence = self._get_pattern_confidence('bearish', i)
            signal = -confidence if (current_bearish and prev_bullish and engulfing) else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def piercing_line(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 1:
                signals.append(0)
                continue
                
            prev_bearish = df['Close'].iloc[i-1] < df['Open'].iloc[i-1]
            current_bullish = df['Close'].iloc[i] > df['Open'].iloc[i]
            opens_below = df['Open'].iloc[i] < df['Close'].iloc[i-1]
            closes_above_mid = df['Close'].iloc[i] > (df['Open'].iloc[i-1] + df['Close'].iloc[i-1]) / 2
            
            confidence = self._get_pattern_confidence('bullish', i)
            signal = confidence if (prev_bearish and current_bullish and opens_below and closes_above_mid) else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def dark_cloud_cover(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 1:
                signals.append(0)
                continue
                
            prev_bullish = df['Close'].iloc[i-1] > df['Open'].iloc[i-1]
            current_bearish = df['Close'].iloc[i] < df['Open'].iloc[i]
            opens_above = df['Open'].iloc[i] > df['Close'].iloc[i-1]
            closes_below_mid = df['Close'].iloc[i] < (df['Open'].iloc[i-1] + df['Close'].iloc[i-1]) / 2
            
            confidence = self._get_pattern_confidence('bearish', i)
            signal = -confidence if (prev_bullish and current_bearish and opens_above and closes_below_mid) else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def morning_star(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 2:
                signals.append(0)
                continue
                
            first_bearish = df['Close'].iloc[i-2] < df['Open'].iloc[i-2]
            third_bullish = df['Close'].iloc[i] > df['Open'].iloc[i]
            middle_small = abs(df['Close'].iloc[i-1] - df['Open'].iloc[i-1]) < abs(df['Close'].iloc[i-2] - df['Open'].iloc[i-2]) / 2
            
            confidence = self._get_pattern_confidence('bullish', i)
            signal = confidence if (first_bearish and middle_small and third_bullish) else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def evening_star(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 2:
                signals.append(0)
                continue
                
            first_bullish = df['Close'].iloc[i-2] > df['Open'].iloc[i-2]
            third_bearish = df['Close'].iloc[i] < df['Open'].iloc[i]
            middle_small = abs(df['Close'].iloc[i-1] - df['Open'].iloc[i-1]) < abs(df['Close'].iloc[i-2] - df['Open'].iloc[i-2]) / 2
            
            confidence = self._get_pattern_confidence('bearish', i)
            signal = -confidence if (first_bullish and middle_small and third_bearish) else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def three_white_soldiers(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 2:
                signals.append(0)
                continue
                
            cond = (
                (df['Close'].iloc[i] > df['Open'].iloc[i]) &
                (df['Close'].iloc[i-1] > df['Open'].iloc[i-1]) &
                (df['Close'].iloc[i-2] > df['Open'].iloc[i-2]) &
                (df['Close'].iloc[i] > df['Close'].iloc[i-1]) &
                (df['Close'].iloc[i-1] > df['Close'].iloc[i-2])
            )
            
            confidence = self._get_pattern_confidence('bullish', i)
            signal = confidence if cond else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    def three_black_crows(self):
        df = self.data.copy()
        signals = []
        
        for i in range(len(df)):
            if i < 2:
                signals.append(0)
                continue
                
            cond = (
                (df['Close'].iloc[i] < df['Open'].iloc[i]) &
                (df['Close'].iloc[i-1] < df['Open'].iloc[i-1]) &
                (df['Close'].iloc[i-2] < df['Open'].iloc[i-2]) &
                (df['Close'].iloc[i] < df['Close'].iloc[i-1]) &
                (df['Close'].iloc[i-1] < df['Close'].iloc[i-2])
            )
            
            confidence = self._get_pattern_confidence('bearish', i)
            signal = -confidence if cond else 0
            signals.append(signal)
        
        df['Signal'] = signals
        return df

    # ---------------- Métodos de compatibilidad ----------------
    
    def detect_all_patterns(self):
        df = self.data.copy()
        pattern_methods = [
            'doji', 'hammer', 'hanging_man', 'shooting_star', 'spinning_top', 
            'inverted_hammer', 'marubozu', 'bullish_engulfing', 'bearish_engulfing',
            'piercing_line', 'dark_cloud_cover', 'morning_star', 'evening_star',
            'three_white_soldiers', 'three_black_crows'
        ]
        
        for method in pattern_methods:
            try:
                result_df = getattr(self, method)()
                df[method] = result_df['Signal']
            except Exception as e:
                print(f"Error calculando {method}: {e}")
                df[method] = 0
        
        return df

    def combined_signal_optimized(self):
        df = self.detect_all_patterns()
        
        # Señal combinada
        bullish_patterns = ['hammer', 'bullish_engulfing', 'piercing_line', 'morning_star', 'three_white_soldiers']
        bearish_patterns = ['hanging_man', 'bearish_engulfing', 'dark_cloud_cover', 'evening_star', 'three_black_crows']
        
        df['Bullish_Score'] = df[bullish_patterns].sum(axis=1)
        df['Bearish_Score'] = df[bearish_patterns].sum(axis=1)
        
        df['Final_Signal'] = 0
        df.loc[df['Bullish_Score'] > 0.5, 'Final_Signal'] = 1
        df.loc[df['Bearish_Score'] < -0.5, 'Final_Signal'] = -1
        
        return df

    def get_trading_signals(self, min_confidence=0.6, min_patterns=1):
        """Método simplificado para compatibilidad"""
        df = self.combined_signal_optimized()
        df['Trading_Signal'] = df['Final_Signal']
        return df