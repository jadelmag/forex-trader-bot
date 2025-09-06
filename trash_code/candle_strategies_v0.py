# strategies/candle_strategies.py

import pandas as pd
import numpy as np
from patterns.candlestickpatterns import CandlestickPatterns
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ExitMethod(Enum):
    """Métodos de cierre para estrategias de velas"""
    SIGNAL_CHANGE = 1        # Cierre por cambio de señal
    STOP_LOSS = 2           # Stop Loss por ATR
    TAKE_PROFIT = 3         # Take Profit por ATR
    TRAILING_STOP = 4       # Stop móvil por ATR
    PATTERN_REVERSAL = 5    # Patrón de reversión contrario

@dataclass
class CandleExitConfig:
    """Configuración para cierres automáticos en estrategias de velas"""
    use_signal_change: bool = True
    use_stop_loss: bool = True
    use_take_profit: bool = True
    use_trailing_stop: bool = False
    use_pattern_reversal: bool = False
    
    # Parámetros de riesgo
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 3.0
    atr_trailing_multiplier: float = 2.0
    
    # Patrones de reversión para cierre
    bullish_reversal_patterns: list = None
    bearish_reversal_patterns: list = None
    
    def __post_init__(self):
        if self.bullish_reversal_patterns is None:
            self.bullish_reversal_patterns = ['hammer', 'bullish_engulfing', 'morning_star']
        if self.bearish_reversal_patterns is None:
            self.bearish_reversal_patterns = ['hanging_man', 'bearish_engulfing', 'evening_star']

class CandleStrategies:
    def __init__(self, data):
        """
        data: DataFrame con columnas ['Open','High','Low','Close']
        """
        self.data = data.copy()
        self.patterns = CandlestickPatterns(self.data)

    def add_indicators(self):
        """Agrega indicadores básicos"""
        df = self.data.copy()
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        return df

    def _apply_exit_logic(self, df, strategy_name, config=None):
        """
        Aplica lógica de cierre automático a cualquier estrategia
        Convierte Signal en ExecSignal y Position con cierres explícitos
        """
        if config is None:
            config = CandleExitConfig()
        
        # Agregar ATR si no existe
        if 'ATR' not in df.columns:
            df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        
        # Inicializar columnas
        df['ExecSignal'] = 0
        df['Position'] = 0
        df['StopLoss'] = np.nan
        df['TakeProfit'] = np.nan
        df['ExitReason'] = ''
        
        position = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        trailing_stop = 0
        
        for i in range(len(df)):
            current_signal = df.iloc[i]['Signal']
            current_price = df.iloc[i]['Close']
            current_high = df.iloc[i]['High']
            current_low = df.iloc[i]['Low']
            current_atr = df.iloc[i]['ATR']
            
            # Verificar cierres si hay posición abierta
            if position != 0:
                exit_signal = 0
                exit_reason = ''
                
                # 1. Stop Loss
                if config.use_stop_loss:
                    if (position == 1 and current_low <= stop_loss) or \
                       (position == -1 and current_high >= stop_loss):
                        exit_signal = -position
                        exit_reason = 'STOP_LOSS'
                
                # 2. Take Profit
                if config.use_take_profit and exit_signal == 0:
                    if (position == 1 and current_high >= take_profit) or \
                       (position == -1 and current_low <= take_profit):
                        exit_signal = -position
                        exit_reason = 'TAKE_PROFIT'
                
                # 3. Trailing Stop
                if config.use_trailing_stop and exit_signal == 0:
                    if position == 1:
                        new_trailing = current_price - (current_atr * config.atr_trailing_multiplier)
                        if new_trailing > trailing_stop:
                            trailing_stop = new_trailing
                        if current_low <= trailing_stop:
                            exit_signal = -1
                            exit_reason = 'TRAILING_STOP'
                    elif position == -1:
                        new_trailing = current_price + (current_atr * config.atr_trailing_multiplier)
                        if new_trailing < trailing_stop:
                            trailing_stop = new_trailing
                        if current_high >= trailing_stop:
                            exit_signal = 1
                            exit_reason = 'TRAILING_STOP'
                
                # 4. Cambio de señal
                if config.use_signal_change and exit_signal == 0:
                    if (position == 1 and current_signal == -1) or \
                       (position == -1 and current_signal == 1):
                        exit_signal = -position
                        exit_reason = 'SIGNAL_CHANGE'
                
                # Aplicar cierre
                if exit_signal != 0:
                    df.iloc[i, df.columns.get_loc('ExecSignal')] = exit_signal
                    df.iloc[i, df.columns.get_loc('ExitReason')] = exit_reason
                    position = 0
                    entry_price = 0
                    stop_loss = 0
                    take_profit = 0
                    trailing_stop = 0
            
            # Verificar nuevas entradas
            if position == 0 and current_signal != 0:
                df.iloc[i, df.columns.get_loc('ExecSignal')] = current_signal
                position = current_signal
                entry_price = current_price
                
                # Calcular niveles
                if position == 1:  # Long
                    stop_loss = entry_price - (current_atr * config.atr_sl_multiplier)
                    take_profit = entry_price + (current_atr * config.atr_tp_multiplier)
                    if config.use_trailing_stop:
                        trailing_stop = entry_price - (current_atr * config.atr_trailing_multiplier)
                else:  # Short
                    stop_loss = entry_price + (current_atr * config.atr_sl_multiplier)
                    take_profit = entry_price - (current_atr * config.atr_tp_multiplier)
                    if config.use_trailing_stop:
                        trailing_stop = entry_price + (current_atr * config.atr_trailing_multiplier)
                
                df.iloc[i, df.columns.get_loc('StopLoss')] = stop_loss
                df.iloc[i, df.columns.get_loc('TakeProfit')] = take_profit
            
            # Actualizar posición actual
            df.iloc[i, df.columns.get_loc('Position')] = position
        
        return df

    # ---------------- Estrategias con cierres explícitos ----------------
    
    def hammer_reversal_strategy(self, config=None):
        """Martillo en tendencia bajista con cierres automáticos"""
        df = self.patterns.hammer()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        df['Signal'] = np.where((df['Signal'] == 1) & 
                                (self.data['Close'] < df['EMA20']), 1, 0)
        return self._apply_exit_logic(df, 'hammer_reversal', config)

    def bullish_engulfing_strategy(self, config=None):
        """Envolvente alcista con cierres automáticos"""
        df = self.data.copy()
        
        # Lógica del patrón optimizada
        cond_bearish_prev = df['Close'].shift(1) < df['Open'].shift(1)
        cond_bullish_curr = df['Close'] > df['Open']
        cond_engulfing = (
            (df['Open'] < df['Close'].shift(1)) &
            (df['Close'] > df['Open'].shift(1))
        )
        
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()
        cond_large_body = body > 0.7 * avg_body
        
        upper_shadow = df['High'] - df['Close']
        cond_strong_close = upper_shadow < (body * 0.3)
        
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_downtrend = df['Close'].shift(2) < df['EMA20'].shift(2)
        
        cond = (
            cond_bearish_prev & cond_bullish_curr & cond_engulfing &
            cond_large_body & cond_strong_close & cond_prev_downtrend
        )
        
        df['Signal'] = np.where(cond, 1, 0)
        return self._apply_exit_logic(df, 'bullish_engulfing', config)

    def bearish_engulfing_strategy(self, config=None):
        """Envolvente bajista con cierres automáticos"""
        df = self.data.copy()
        
        df['Body'] = (df['Close'] - df['Open']).abs()
        avg_body = df['Body'].rolling(20).mean()
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        
        cond_prev_bullish = df['Close'].shift(1) > df['Open'].shift(1)
        cond_curr_bearish = df['Close'] < df['Open']
        cond_engulfing = (
            (df['Open'] > df['Close'].shift(1)) &
            (df['Close'] < df['Open'].shift(1))
        )
        
        cond_large_body = df['Body'] > 0.7 * avg_body
        cond_strong_close = upper_shadow < (df['Body'] * 0.3)
        
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_uptrend = df['Close'].shift(2) > df['EMA20'].shift(2)
        
        cond = (
            cond_prev_bullish & cond_curr_bearish & cond_engulfing &
            cond_large_body & cond_strong_close & cond_prev_uptrend
        )
        
        df['Signal'] = np.where(cond, -1, 0)
        return self._apply_exit_logic(df, 'bearish_engulfing', config)

    def morning_star_strategy(self, config=None):
        """Morning Star con cierres automáticos"""
        df = self.patterns.morning_star()
        df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        df['Signal'] = np.where((df['Signal'] == 1) & 
                                (self.data['Close'] > df['EMA50']), 1, 0)
        return self._apply_exit_logic(df, 'morning_star', config)

    def evening_star_strategy(self, config=None):
        """Evening Star con cierres automáticos"""
        df = self.patterns.evening_star()
        df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        df['Signal'] = np.where((df['Signal'] == -1) & 
                                (self.data['Close'] < df['EMA50']), -1, 0)
        return self._apply_exit_logic(df, 'evening_star', config)

    def hanging_man_strategy(self, config=None):
        """Hanging Man con cierres automáticos"""
        df = self.patterns.hanging_man()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        df['Signal'] = np.where((df['Signal'] == -1) & 
                                (self.data['Close'] > df['EMA20']), -1, 0)
        return self._apply_exit_logic(df, 'hanging_man', config)

    def three_white_soldiers_strategy(self, config=None):
        """Three White Soldiers con cierres automáticos"""
        df = self.patterns.three_white_soldiers()
        return self._apply_exit_logic(df, 'three_white_soldiers', config)

    def three_black_crows_strategy(self, config=None):
        """Three Black Crows con cierres automáticos"""
        df = self.patterns.three_black_crows()
        return self._apply_exit_logic(df, 'three_black_crows', config)

    def doji_reversal_strategy(self, config=None):
        """Doji en niveles clave con cierres automáticos"""
        df = self.patterns.doji()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        
        # Doji alcista en soporte (EMA20)
        bullish_doji = (df['Signal'] == 1) & (df['Close'] <= df['EMA20'] * 1.002)
        # Doji bajista en resistencia (EMA20)  
        bearish_doji = (df['Signal'] == 1) & (df['Close'] >= df['EMA20'] * 0.998)
        
        df['Signal'] = np.where(bullish_doji, 1, 
                       np.where(bearish_doji, -1, 0))
        return self._apply_exit_logic(df, 'doji_reversal', config)

    # ---------------- Estrategias combinadas ----------------
    
    def scalping_reversal_strategy(self, config=None):
        """Scalping con múltiples patrones de reversión"""
        df_h = self.hammer_reversal_strategy(config)
        df_e = self.bullish_engulfing_strategy(config)
        
        df = self.data.copy()
        df['Signal'] = np.where((df_h['Signal'] == 1) | (df_e['Signal'] == 1), 1, 0)
        return self._apply_exit_logic(df, 'scalping_reversal', config)

    def swing_trading_strategy(self, config=None):
        """Swing con morning/evening star"""
        df_m = self.morning_star_strategy(config)
        df_e = self.evening_star_strategy(config)
        
        df = self.data.copy()
        df['Signal'] = np.where(df_m['Signal'] == 1, 1, 
                       np.where(df_e['Signal'] == -1, -1, 0))
        return self._apply_exit_logic(df, 'swing_trading', config)

    def multi_pattern_strategy(self, config=None):
        """Estrategia con múltiples patrones filtrados por tendencia"""
        df = self.patterns.combined_signal_optimized()
        df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        
        # Filtrar señales por tendencia
        df['Signal'] = np.where((df['Final_Signal'] == 1) & (df['Close'] > df['EMA50']), 1,
                       np.where((df['Final_Signal'] == -1) & (df['Close'] < df['EMA50']), -1, 0))
        
        return self._apply_exit_logic(df, 'multi_pattern', config)

    # ---------------- Estrategias especializadas ----------------
    
    def aggressive_reversal_strategy(self, config=None):
        """Estrategia agresiva con trailing stop"""
        if config is None:
            config = CandleExitConfig(
                use_trailing_stop=True,
                atr_sl_multiplier=1.0,
                atr_tp_multiplier=2.0,
                atr_trailing_multiplier=1.5
            )
        
        df = self.patterns.combined_signal_optimized()
        df['Signal'] = df['Final_Signal']
        return self._apply_exit_logic(df, 'aggressive_reversal', config)

    def conservative_swing_strategy(self, config=None):
        """Estrategia conservadora con stops amplios"""
        if config is None:
            config = CandleExitConfig(
                use_trailing_stop=False,
                atr_sl_multiplier=2.5,
                atr_tp_multiplier=4.0
            )
        
        df_m = self.morning_star_strategy()
        df_e = self.evening_star_strategy()
        df_soldiers = self.three_white_soldiers_strategy()
        df_crows = self.three_black_crows_strategy()
        
        df = self.data.copy()
        df['Signal'] = np.where(
            (df_m['Signal'] == 1) | (df_soldiers['Signal'] == 1), 1,
            np.where((df_e['Signal'] == -1) | (df_crows['Signal'] == -1), -1, 0)
        )
        
        return self._apply_exit_logic(df, 'conservative_swing', config)

    # ---------------- Missing strategy methods ----------------
    
    def bearish_engulfing_reversal(self, config=None):
        """Bearish engulfing reversal strategy"""
        return self.bearish_engulfing_strategy(config)
    
    def bullish_engulfing_reversal(self, config=None):
        """Bullish engulfing reversal strategy"""
        return self.bullish_engulfing_strategy(config)
    
    def doji_indecision(self, config=None):
        """Doji indecision strategy"""
        return self.doji_reversal_strategy(config)
    
    def evening_star_swing(self, config=None):
        """Evening star swing strategy"""
        return self.evening_star_strategy(config)
    
    def filter_with_trend(self, config=None):
        """Filter signals with trend"""
        return self.multi_pattern_strategy(config)
    
    def hammer_reversal(self, config=None):
        """Hammer reversal strategy"""
        return self.hammer_reversal_strategy(config)
    
    def hanging_man_reversal(self, config=None):
        """Hanging man reversal strategy"""
        return self.hanging_man_strategy(config)
    
    def marubozu_trend(self, config=None):
        """Marubozu trend following strategy"""
        df = self.patterns.marubozu()
        df['EMA20'] = self.data['Close'].ewm(span=20).mean()
        
        # Marubozu alcista en tendencia alcista
        bullish_marubozu = (df['Signal'] == 1) & (df['Close'] > df['EMA20'])
        # Marubozu bajista en tendencia bajista
        bearish_marubozu = (df['Signal'] == -1) & (df['Close'] < df['EMA20'])
        
        df['Signal'] = np.where(bullish_marubozu, 1, 
                       np.where(bearish_marubozu, -1, 0))
        return self._apply_exit_logic(df, 'marubozu_trend', config)
    
    def morning_star_swing(self, config=None):
        """Morning star swing strategy"""
        return self.morning_star_strategy(config)
    
    def scalping_reversal(self, config=None):
        """Scalping reversal strategy"""
        return self.scalping_reversal_strategy(config)
    
    def stop_loss_take_profit(self, config=None):
        """Strategy focused on SL/TP management"""
        if config is None:
            config = CandleExitConfig(
                use_stop_loss=True,
                use_take_profit=True,
                atr_sl_multiplier=1.5,
                atr_tp_multiplier=3.0
            )
        
        # Use combined patterns for entries
        df = self.patterns.combined_signal_optimized()
        df['Signal'] = df['Final_Signal']
        return self._apply_exit_logic(df, 'stop_loss_take_profit', config)
    
    def swing_trading(self, config=None):
        """Swing trading strategy"""
        return self.swing_trading_strategy(config)
    
    def three_black_crows(self, config=None):
        """Three black crows strategy"""
        return self.three_black_crows_strategy(config)
    
    def three_white_soldiers(self, config=None):
        """Three white soldiers strategy"""
        return self.three_white_soldiers_strategy(config)
