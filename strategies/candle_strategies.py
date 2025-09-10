# strategies/candle_strategies.py

import pandas as pd
import numpy as np
from dataclasses import dataclass
from patterns.candlestickpatterns import CandlestickPatterns


@dataclass
class CandleExitConfig:
    """Configuración para cierres automáticos en estrategias de velas."""
    use_signal_change: bool = True
    use_stop_loss: bool = True
    use_take_profit: bool = True
    use_trailing_stop: bool = False
    use_pattern_reversal: bool = False

    # Parámetros de riesgo
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 3.0
    atr_trailing_multiplier: float = 2.0

    # Listas de patrones (reservadas para futuras extensiones)
    bullish_reversal_patterns: list | None = None
    bearish_reversal_patterns: list | None = None

    def __post_init__(self):
        if self.bullish_reversal_patterns is None:
            self.bullish_reversal_patterns = ['hammer', 'bullish_engulfing', 'morning_star']
        if self.bearish_reversal_patterns is None:
            self.bearish_reversal_patterns = ['hanging_man', 'bearish_engulfing', 'evening_star']


class CandleStrategies:
    def __init__(self, data, config=None):
        """
        data: DataFrame con columnas ['Open','High','Low','Close']
        config: Diccionario opcional con configuración para CandlestickPatterns
        """
        self.data = data.copy()
        self.config = config or {}
        
        # Asegurar que tenemos las columnas necesarias
        required_cols = ['Open', 'High', 'Low', 'Close']
        for col in required_cols:
            if col not in self.data.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada en los datos")
        
        # Agregar volumen dummy si no existe
        if 'Volume' not in self.data.columns:
            self.data['Volume'] = 1.0
            
        # Pasar configuración a CandlestickPatterns
        self.patterns = CandlestickPatterns(self.data, config=self.config)

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
        """Aplica cierres explícitos (SL/TP, trailing, cambio de señal) y devuelve estructura completa.

        Requiere columna 'Signal' en df y devuelve las columnas:
        - ExecSignal (-1/0/1), Position (-1/0/1), StopLoss, TakeProfit, ExitReason
        """
        # Config por defecto
        if config is None or not isinstance(config, CandleExitConfig):
            # Si viene un dict desde el modal, convertir a CandleExitConfig
            if isinstance(config, dict):
                try:
                    config = CandleExitConfig(**config)
                except TypeError:
                    config = CandleExitConfig()
            else:
                config = CandleExitConfig()

        df = df.copy()

        # Asegurar ATR
        if 'ATR' not in df.columns:
            df['ATR'] = (df['High'] - df['Low']).rolling(14, min_periods=1).mean()

        # Inicializar columnas de salida
        df['ExecSignal'] = 0
        df['Position'] = 0
        df['StopLoss'] = np.nan
        df['TakeProfit'] = np.nan
        df['ExitReason'] = ''

        position = 0
        entry_price = 0.0
        stop_loss = np.nan
        take_profit = np.nan
        trailing_stop = np.nan

        for i in range(len(df)):
            current_signal = int(df.iloc[i]['Signal']) if not pd.isna(df.iloc[i]['Signal']) else 0
            current_price = float(df.iloc[i]['Close'])
            current_high = float(df.iloc[i]['High'])
            current_low = float(df.iloc[i]['Low'])
            current_atr = float(df.iloc[i]['ATR']) if not pd.isna(df.iloc[i]['ATR']) else 0.0

            # Si hay posición abierta, evaluar posibles cierres
            if position != 0:
                exit_signal = 0
                exit_reason = ''

                # 1) Stop Loss
                if config.use_stop_loss:
                    if (position == 1 and current_low <= stop_loss) or (position == -1 and current_high >= stop_loss):
                        exit_signal = -position
                        exit_reason = 'STOP_LOSS'

                # 2) Take Profit
                if exit_signal == 0 and config.use_take_profit:
                    if (position == 1 and current_high >= take_profit) or (position == -1 and current_low <= take_profit):
                        exit_signal = -position
                        exit_reason = 'TAKE_PROFIT'

                # 3) Trailing Stop
                if exit_signal == 0 and config.use_trailing_stop and current_atr > 0:
                    if position == 1:
                        new_trailing = current_price - (current_atr * config.atr_trailing_multiplier)
                        if np.isnan(trailing_stop) or new_trailing > trailing_stop:
                            trailing_stop = new_trailing
                        if current_low <= trailing_stop:
                            exit_signal = -1
                            exit_reason = 'TRAILING_STOP'
                    else:  # position == -1
                        new_trailing = current_price + (current_atr * config.atr_trailing_multiplier)
                        if np.isnan(trailing_stop) or new_trailing < trailing_stop:
                            trailing_stop = new_trailing
                        if current_high >= trailing_stop:
                            exit_signal = 1
                            exit_reason = 'TRAILING_STOP'

                # 4) Cambio de señal
                if exit_signal == 0 and config.use_signal_change:
                    if (position == 1 and current_signal == -1) or (position == -1 and current_signal == 1):
                        exit_signal = -position
                        exit_reason = 'SIGNAL_CHANGE'

                if exit_signal != 0:
                    df.iloc[i, df.columns.get_loc('ExecSignal')] = exit_signal
                    df.iloc[i, df.columns.get_loc('ExitReason')] = exit_reason
                    position = 0
                    entry_price = 0.0
                    stop_loss = np.nan
                    take_profit = np.nan
                    trailing_stop = np.nan

            # Entradas: si no hay posición y existe señal
            if position == 0 and current_signal != 0:
                df.iloc[i, df.columns.get_loc('ExecSignal')] = current_signal
                position = current_signal
                entry_price = current_price

                # Calcular SL/TP
                if current_atr <= 0:
                    # Fallback si ATR es 0: usar rango de la vela
                    current_atr = max(current_high - current_low, 1e-6)
                if position == 1:
                    stop_loss = entry_price - (current_atr * config.atr_sl_multiplier)
                    take_profit = entry_price + (current_atr * config.atr_tp_multiplier)
                    trailing_stop = entry_price - (current_atr * config.atr_trailing_multiplier) if config.use_trailing_stop else np.nan
                else:
                    stop_loss = entry_price + (current_atr * config.atr_sl_multiplier)
                    take_profit = entry_price - (current_atr * config.atr_tp_multiplier)
                    trailing_stop = entry_price + (current_atr * config.atr_trailing_multiplier) if config.use_trailing_stop else np.nan

                df.iloc[i, df.columns.get_loc('StopLoss')] = stop_loss
                df.iloc[i, df.columns.get_loc('TakeProfit')] = take_profit

            # Actualizar posición persistente
            df.iloc[i, df.columns.get_loc('Position')] = position

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

    # ---------------- Nuevos metodos -----------------------

    def shooting_star_strategy(self, config=None):
        df = self.patterns.shooting_star()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'shooting_star', config)

    def spinning_top_strategy(self, config=None):
        df = self.patterns.spinning_top()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'spinning_top', config)

    def inverted_hammer_strategy(self, config=None):
        df = self.patterns.inverted_hammer()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'inverted_hammer', config)

    def piercing_line_strategy(self, config=None):
        df = self.patterns.piercing_line()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'piercing_line', config)

    def dark_cloud_cover_strategy(self, config=None):
        df = self.patterns.dark_cloud_cover()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'dark_cloud_cover', config)

    def tweezer_top_strategy(self, config=None):
        df = self.patterns.tweezer_top()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'tweezer_top', config)

    def tweezer_bottom_strategy(self, config=None):
        df = self.patterns.tweezer_bottom()
        result_df = self.data.copy()
        result_df['Signal'] = df['Signal']
        return self._apply_exit_logic(result_df, 'tweezer_bottom', config)

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