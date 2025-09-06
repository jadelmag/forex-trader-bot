# strategies/candle_strategies.py

import pandas as pd
import numpy as np
from patterns.candlestickpatterns import CandlestickPatterns

class CandleStrategies:
    def __init__(self, data):
        """
        data: DataFrame con columnas ['Open','High','Low','Close']
        """
        self.data = data.copy()
        
        # Asegurar que tenemos las columnas necesarias
        required_cols = ['Open', 'High', 'Low', 'Close']
        for col in required_cols:
            if col not in self.data.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada en los datos")
        
        # Agregar volumen dummy si no existe
        if 'Volume' not in self.data.columns:
            self.data['Volume'] = 1.0
            
        self.patterns = CandlestickPatterns(self.data)

    def _safe_join(self, main_df, new_df, new_columns):
        """Une dataframes de manera segura evitando superposición de columnas"""
        result_df = main_df.copy()
        for col in new_columns:
            if col in new_df.columns:
                # Renombrar columna temporalmente para evitar conflicto
                temp_col = f"temp_{col}"
                result_df[temp_col] = new_df[col]
                # Solo mantener si no existe ya
                if col not in result_df.columns:
                    result_df[col] = result_df[temp_col]
                result_df.drop(columns=[temp_col], inplace=True, errors='ignore')
        return result_df

    def _apply_exit_logic(self, df, strategy_name, config=None):
        """Versión simplificada para evitar errores"""
        # Implementación básica sin lógica compleja
        df['ExecSignal'] = df['Signal']
        df['Position'] = df['Signal']
        return df

    # ---------------- Estrategias corregidas ----------------
    
    def hammer_reversal_strategy(self, config=None):
        df = self.patterns.hammer()
        # Evitar join conflictivo - usar asignación directa
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        result_df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        result_df['Signal'] = np.where(
            (result_df['Signal'] > 0) & (self.data['Close'] < result_df['EMA20']), 
            result_df['Signal'], 0
        )
        return self._apply_exit_logic(result_df, 'hammer_reversal', config)

    def bullish_engulfing_strategy(self, config=None):
        df = self.patterns.bullish_engulfing()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'bullish_engulfing', config)

    def bearish_engulfing_strategy(self, config=None):
        df = self.patterns.bearish_engulfing()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'bearish_engulfing', config)

    def morning_star_strategy(self, config=None):
        df = self.patterns.morning_star()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'morning_star', config)

    def evening_star_strategy(self, config=None):
        df = self.patterns.evening_star()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'evening_star', config)

    def hanging_man_strategy(self, config=None):
        df = self.patterns.hanging_man()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'hanging_man', config)

    def three_white_soldiers_strategy(self, config=None):
        df = self.patterns.three_white_soldiers()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'three_white_soldiers', config)

    def three_black_crows_strategy(self, config=None):
        df = self.patterns.three_black_crows()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'three_black_crows', config)

    def doji_reversal_strategy(self, config=None):
        df = self.patterns.doji()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        result_df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        result_df['RSI'] = self.patterns.data['RSI']
        
        bullish_doji = (result_df['Signal'] > 0) & (self.data['Close'] <= result_df['EMA20'] * 1.01) & (result_df['RSI'] < 30)
        bearish_doji = (result_df['Signal'] > 0) & (self.data['Close'] >= result_df['EMA20'] * 0.99) & (result_df['RSI'] > 70)
        
        result_df['Signal'] = np.where(bullish_doji, 1, np.where(bearish_doji, -1, 0))
        return self._apply_exit_logic(result_df, 'doji_reversal', config)

    def marubozu_trend(self, config=None):
        df = self.patterns.marubozu()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        result_df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        
        bullish_marubozu = (result_df['Signal'] > 0) & (self.data['Close'] > result_df['EMA20'])
        bearish_marubozu = (result_df['Signal'] < 0) & (self.data['Close'] < result_df['EMA20'])
        
        result_df['Signal'] = np.where(bullish_marubozu, 1, np.where(bearish_marubozu, -1, 0))
        return self._apply_exit_logic(result_df, 'marubozu_trend', config)

    # ---------------- Métodos de compatibilidad ----------------
    
    def bearish_engulfing_reversal(self, config=None):
        return self.bearish_engulfing_strategy(config)
    
    def bullish_engulfing_reversal(self, config=None):
        return self.bullish_engulfing_strategy(config)
    
    def doji_indecision(self, config=None):
        return self.doji_reversal_strategy(config)
    
    def evening_star_swing(self, config=None):
        return self.evening_star_strategy(config)
    
    def hammer_reversal(self, config=None):
        return self.hammer_reversal_strategy(config)
    
    def hanging_man_reversal(self, config=None):
        return self.hanging_man_strategy(config)
    
    def morning_star_swing(self, config=None):
        return self.morning_star_strategy(config)
    
    def three_black_crows(self, config=None):
        return self.three_black_crows_strategy(config)
    
    def three_white_soldiers(self, config=None):
        return self.three_white_soldiers_strategy(config)

    # ---------------- Métodos simplificados ----------------
    
    def filter_with_trend(self, config=None):
        signals_df = self.patterns.get_trading_signals()
        result_df = self.data.copy()
        result_df['Signal'] = signals_df['Trading_Signal']
        result_df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        
        result_df['Signal'] = np.where(
            (result_df['Signal'] == 1) & (self.data['Close'] > result_df['EMA50']), 1,
            np.where((result_df['Signal'] == -1) & (self.data['Close'] < result_df['EMA50']), -1, 0)
        )
        return self._apply_exit_logic(result_df, 'filter_with_trend', config)

    def stop_loss_take_profit(self, config=None):
        signals_df = self.patterns.get_trading_signals()
        result_df = self.data.copy()
        result_df['Signal'] = signals_df['Trading_Signal']
        return self._apply_exit_logic(result_df, 'stop_loss_take_profit', config)

    def scalping_reversal(self, config=None):
        df_h = self.hammer_reversal_strategy(config)
        df_e = self.bullish_engulfing_strategy(config)
        
        result_df = self.data.copy()
        result_df['Signal'] = np.where(
            (df_h['Signal'] == 1) | (df_e['Signal'] == 1), 1, 0
        )
        return self._apply_exit_logic(result_df, 'scalping_reversal', config)

    def swing_trading(self, config=None):
        df_m = self.morning_star_strategy(config)
        df_e = self.evening_star_strategy(config)
        
        result_df = self.data.copy()
        result_df['Signal'] = np.where(
            df_m['Signal'] == 1, 1, np.where(df_e['Signal'] == -1, -1, 0)
        )
        return self._apply_exit_logic(result_df, 'swing_trading', config)