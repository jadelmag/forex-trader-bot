# strategies/strategies.py

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from enum import Enum

class ExitMethod(Enum):
    """Métodos de cierre disponibles"""
    SIGNAL_REVERSAL = 1      # Cierre por señal contraria (por defecto)
    PRICE_ACTION = 2         # Patrón de velas contrario
    MA_CROSSOVER = 3         # Cruce de medias contrario
    RSI_REVERSAL = 4         # RSI en zona de sobrecompra/sobreventa
    SUPPORT_RESISTANCE = 5   # Toque de soporte/resistencia
    TRAILING_STOP = 6        # Stop móvil con ATR
    TIME_EXIT = 7            # Salida por tiempo
    HYBRID = 8               # Combinación de métodos

@dataclass
class ExitConfig:
    """Configuración para órdenes de cierre"""
    method: ExitMethod = ExitMethod.SIGNAL_REVERSAL
    # Configuración específica para cada método
    price_action_pattern: str = 'engulfing'  # 'engulfing', 'doji', 'hammer', etc.
    ma_fast_period: int = 20
    ma_slow_period: int = 50
    rsi_period: int = 14
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    trailing_atr_mult: float = 2.0
    max_bars: int = 20  # Para TIME_EXIT
    hybrid_conditions: List[ExitMethod] = None

    def __post_init__(self):
        if self.hybrid_conditions is None:
            self.hybrid_conditions = [ExitMethod.RSI_REVERSAL, ExitMethod.MA_CROSSOVER]

class ForexStrategies:
    """
    Estrategias de trading con gestión de riesgo integrada y órdenes explícitas de cierre.
    Requiere DataFrame con columnas: ['Open','High','Low','Close'].
    """

    def __init__(self, data: pd.DataFrame):
        # Crear copia para evitar modificar el DataFrame original
        df = data.copy()
        
        # Mapeo de columnas lowercase a uppercase para compatibilidad
        column_mapping = {
            'open': 'Open',
            'high': 'High', 
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        # Renombrar columnas si están en lowercase
        columns_to_rename = {col: column_mapping[col] for col in df.columns if col in column_mapping}
        if columns_to_rename:
            df.rename(columns=columns_to_rename, inplace=True)
        
        # Verificar que las columnas requeridas estén presentes
        required = {'Open', 'High', 'Low', 'Close'}
        if not required.issubset(df.columns):
            raise ValueError(f"Faltan columnas: {sorted(required - set(df.columns))}")
        
        self.data = df.sort_index().copy()

    # ------- helpers -------
    @staticmethod
    def _position_from_signal(signal: pd.Series) -> pd.Series:
        """Convierte señales discretas (1, -1, 0) en posición mantenida."""
        return signal.replace(0, np.nan).ffill().fillna(0)

    def _attach_execution(self, df: pd.DataFrame, exec_lag: int = 1) -> pd.DataFrame:
        """Agrega ExecSignal y Position (posición mantenida)."""
        out = df.copy()
        out['ExecSignal'] = out['Signal'].shift(exec_lag, fill_value=0)
        out['Position'] = self._position_from_signal(out['ExecSignal'])
        return out

    def _apply_risk_management(self, df: pd.DataFrame,
                               account_size=10000, risk_per_trade=0.01,
                               atr_period=14, atr_mult=2, rr_ratio=2):
        """Calcula StopLoss, TakeProfit y PositionSize según ATR y % de riesgo."""
        df = df.copy()
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs()
        tr3 = (df['Low'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs()
        df['TR'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['ATR'] = df['TR'].rolling(atr_period).mean()

        df['StopLoss'] = np.where(df['Signal'] == 1,
                                  df['Close'] - df['ATR']*atr_mult,
                                  np.where(df['Signal'] == -1,
                                           df['Close'] + df['ATR']*atr_mult, np.nan))

        df['TakeProfit'] = np.where(df['Signal'] == 1,
                                    df['Close'] + df['ATR']*atr_mult*rr_ratio,
                                    np.where(df['Signal'] == -1,
                                             df['Close'] - df['ATR']*atr_mult*rr_ratio, np.nan))

        risk_amount = account_size * risk_per_trade
        pip_value_proxy = df['ATR'] * atr_mult
        df['PositionSize'] = np.where(df['Signal'] != 0,
                                      np.where(pip_value_proxy > 0, risk_amount / pip_value_proxy, 0),
                                      0)
        return df

    # ------- indicators -------
    @staticmethod
    def _ema(s: pd.Series, span: int):
        return s.ewm(span=span, adjust=False).mean()

    @staticmethod
    def _sma(s: pd.Series, window: int):
        return s.rolling(window).mean()

    def _rsi(self, period=14):
        close = self.data['Close']
        delta = close.diff()
        gain = (delta.clip(lower=0)).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _macd(self, fast=12, slow=26, signal=9):
        ema_fast = self._ema(self.data['Close'], fast)
        ema_slow = self._ema(self.data['Close'], slow)
        macd = ema_fast - ema_slow
        sig = macd.ewm(span=signal, adjust=False).mean()
        hist = macd - sig
        return macd, sig, hist

    def _bollinger(self, window=20, num_std=2.0):
        ma = self._sma(self.data['Close'], window)
        std = self.data['Close'].rolling(window).std()
        upper = ma + num_std * std
        lower = ma - num_std * std
        return ma, upper, lower, std

    def _stochastic(self, k=14, d=3):
        low_min = self.data['Low'].rolling(k).min()
        high_max = self.data['High'].rolling(k).max()
        k_fast = 100 * (self.data['Close'] - low_min) / (high_max - low_min)
        d_slow = k_fast.rolling(d).mean()
        return k_fast, d_slow

    # ------- ADX Helper -------
    def _calculate_adx(self, period=14):
        """Calcula ADX, DI+ y DI-"""
        df = self.data.copy()

        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum((df['High'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs(), 
                      (df['Low'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs())
        )

        up_move = df['High'] - df['High'].shift(1)
        down_move = df['Low'].shift(1) - df['Low']
        df['DMplus'] = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        df['DMminus'] = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        df['TR_smooth'] = df['TR'].rolling(period).mean()
        df['DMplus_smooth'] = df['DMplus'].rolling(period).mean()
        df['DMminus_smooth'] = df['DMminus'].rolling(period).mean()

        df['DIplus'] = (df['DMplus_smooth'] / df['TR_smooth']) * 100
        df['DIminus'] = (df['DMminus_smooth'] / df['TR_smooth']) * 100
        df['DX'] = (np.abs(df['DIplus'] - df['DIminus']) / (df['DIplus'] + df['DIminus'])) * 100
        df['ADX'] = df['DX'].rolling(period).mean()

        return df[['DIplus', 'DIminus', 'ADX']]

    # ------- Métodos de cierre explícitos -------
    def _generate_exit_signals(self, df: pd.DataFrame, exit_config: ExitConfig) -> pd.Series:
        """Genera señales de cierre basadas en la configuración"""
        exit_signal = pd.Series(0, index=df.index)
        
        if exit_config.method == ExitMethod.SIGNAL_REVERSAL:
            # Cierre por señal contraria (ya implementado por defecto)
            pass
            
        elif exit_config.method == ExitMethod.PRICE_ACTION:
            # Patrones de velas contrarios
            exit_signal = self._price_action_exit(df, exit_config)
            
        elif exit_config.method == ExitMethod.MA_CROSSOVER:
            # Cruce de medias contrario
            exit_signal = self._ma_crossover_exit(df, exit_config)
            
        elif exit_config.method == ExitMethod.RSI_REVERSAL:
            # RSI en zona contraria
            exit_signal = self._rsi_exit(df, exit_config)
            
        elif exit_config.method == ExitMethod.SUPPORT_RESISTANCE:
            # Toque de soporte/resistencia
            exit_signal = self._support_resistance_exit(df, exit_config)
            
        elif exit_config.method == ExitMethod.TRAILING_STOP:
            # Stop móvil (se implementa en el backtest, no aquí)
            pass
            
        elif exit_config.method == ExitMethod.TIME_EXIT:
            # Salida por tiempo
            exit_signal = self._time_exit(df, exit_config)
            
        elif exit_config.method == ExitMethod.HYBRID:
            # Combinación de métodos
            exit_signal = self._hybrid_exit(df, exit_config)
            
        return exit_signal

    def _price_action_exit(self, df: pd.DataFrame, config: ExitConfig) -> pd.Series:
        """Señales de cierre por patrones de velas"""
        exit_signal = pd.Series(0, index=df.index)
        o, c, h, l = df['Open'], df['Close'], df['High'], df['Low']
        
        if config.price_action_pattern == 'engulfing':
            # Engulfing contrario
            prev_o, prev_c = o.shift(1), c.shift(1)
            bearish_engulfing = (prev_c > prev_o) & (c < o) & (o >= prev_c) & (c <= prev_o)
            bullish_engulfing = (prev_c < prev_o) & (c > o) & (c >= prev_o) & (o <= prev_c)
            
            # Cerrar largos con engulfing bajista, cortos con alcista
            exit_signal = np.where(bearish_engulfing, -1, np.where(bullish_engulfing, 1, 0))
            
        elif config.price_action_pattern == 'doji':
            # Doji como señal de indecisión
            doji = abs(c - o) / (h - l + 1e-9) < 0.1  # Cuerpo pequeño relativo al rango
            exit_signal = doji.astype(int)  # Cerrar ambas direcciones
            
        return exit_signal

    def _ma_crossover_exit(self, df: pd.DataFrame, config: ExitConfig) -> pd.Series:
        """Cierre por cruce de medias contrario"""
        ema_fast = self._ema(df['Close'], config.ma_fast_period)
        ema_slow = self._ema(df['Close'], config.ma_slow_period)
        
        # Cruzamiento contrario
        cross_down = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))
        cross_up = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
        
        exit_signal = np.where(cross_down, -1, np.where(cross_up, 1, 0))
        return exit_signal

    def _rsi_exit(self, df: pd.DataFrame, config: ExitConfig) -> pd.Series:
        """Cierre por RSI en zona contraria"""
        rsi = self._rsi(config.rsi_period)
        
        # Cerrar largos cuando RSI > overbought, cortos cuando RSI < oversold
        exit_long = rsi > config.rsi_overbought
        exit_short = rsi < config.rsi_oversold
        
        exit_signal = np.where(exit_long, -1, np.where(exit_short, 1, 0))
        return exit_signal

    def _support_resistance_exit(self, df: pd.DataFrame, config: ExitConfig) -> pd.Series:
        """Cierre por toque de soporte/resistencia"""
        # Usar pivots de soporte/resistencia
        lookback = 20
        pivot_high = (df['High'] == df['High'].rolling(lookback, center=True).max())
        pivot_low = (df['Low'] == df['Low'].rolling(lookback, center=True).min())
        
        resistance = df['High'].where(pivot_high).ffill()
        support = df['Low'].where(pivot_low).ffill()
        
        # Cerrar largos en resistencia, cortos en soporte
        touch_resistance = df['Close'] >= resistance * 0.995
        touch_support = df['Close'] <= support * 1.005
        
        exit_signal = np.where(touch_resistance, -1, np.where(touch_support, 1, 0))
        return exit_signal

    def _time_exit(self, df: pd.DataFrame, config: ExitConfig) -> pd.Series:
        """Salida después de N barras"""
        # Esta se implementa mejor en el backtest, pero aquí marcamos
        exit_signal = pd.Series(0, index=df.index)
        return exit_signal

    def _hybrid_exit(self, df: pd.DataFrame, config: ExitConfig) -> pd.Series:
        """Combinación de métodos de cierre"""
        exit_signals = []
        for method in config.hybrid_conditions:
            temp_config = ExitConfig(method=method)
            exit_sig = self._generate_exit_signals(df, temp_config)
            exit_signals.append(exit_sig)
        
        # Cerrar si cualquier condición se cumple
        hybrid_signal = pd.Series(0, index=df.index)
        for sig in exit_signals:
            hybrid_signal = np.where(sig != 0, sig, hybrid_signal)
            
        return hybrid_signal

    # ------- Estrategias actualizadas con órdenes de cierre -------

    # ---------------- ADX Strategy ----------------
    def adx_strategy(self, adx_period=14, adx_threshold=25, exec_lag=1, 
                    exit_config: ExitConfig = None, **risk_kwargs):
        """ADX strategy con órdenes de cierre explícitas"""
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.RSI_REVERSAL)
        
        df = self.data.copy()
        adx_data = self._calculate_adx(adx_period)
        df = pd.concat([df, adx_data], axis=1)

        df['Signal'] = 0
        buy_condition = (df['DIplus'] > df['DIminus']) & (df['ADX'] > adx_threshold)
        sell_condition = (df['DIminus'] > df['DIplus']) & (df['ADX'] > adx_threshold)
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1

        # Generar señales de cierre
        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        
        df = self._apply_risk_management(df, **risk_kwargs)
        result = self._attach_execution(df[['Close', 'DIplus', 'DIminus', 'ADX',
                                          'Signal', 'ExitSignal', 'StopLoss', 
                                          'TakeProfit', 'PositionSize']], exec_lag)
        return result

    # ---------------- Trend Following (EMA crossover) ----------------
    def trend_following(self, short_window=20, long_window=50, exec_lag=1,
                       exit_config: ExitConfig = None, **risk_kwargs):
        """Trend following con órdenes de cierre"""
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.MA_CROSSOVER,
                                   ma_fast_period=short_window,
                                   ma_slow_period=long_window)
        
        df = self.data.copy()
        df['EMA_short'] = self._ema(df['Close'], short_window)
        df['EMA_long'] = self._ema(df['Close'], long_window)

        cond = df['EMA_short'] > df['EMA_long']
        cond_shifted = cond.shift(1, fill_value=False)
        cross_up = cond & (~cond_shifted)
        cross_dn = (~cond) & cond_shifted

        df['Signal'] = 0
        df.loc[cross_up, 'Signal'] = 1
        df.loc[cross_dn, 'Signal'] = -1

        # Señales de cierre
        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','EMA_short','EMA_long',
                                          'Signal','ExitSignal','StopLoss',
                                          'TakeProfit','PositionSize']], exec_lag)

    # ---------------- Breakout (HH/LL) ----------------
    def breakout(self, window=20, exec_lag=1, exit_config: ExitConfig = None, **risk_kwargs):
        """Breakout strategy con órdenes de cierre"""
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.SUPPORT_RESISTANCE)
        
        df = self.data.copy()
        df['High_Max'] = df['High'].rolling(window).max().shift(1)
        df['Low_Min'] = df['Low'].rolling(window).min().shift(1)

        df['Signal'] = 0
        df.loc[df['Close'] > df['High_Max'], 'Signal'] = 1
        df.loc[df['Close'] < df['Low_Min'], 'Signal'] = -1

        # Señales de cierre
        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','High_Max','Low_Min',
                                          'Signal','ExitSignal','StopLoss',
                                          'TakeProfit','PositionSize']], exec_lag)

    # ---------------- RSI Strategy ----------------
    def rsi_strategy(self, period=14, overbought=70, oversold=30, exec_lag=1,
                    exit_config: ExitConfig = None, **risk_kwargs):
        """RSI strategy con órdenes de cierre"""
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.RSI_REVERSAL,
                                   rsi_period=period,
                                   rsi_overbought=overbought,
                                   rsi_oversold=oversold)
        
        df = self.data.copy()
        df['RSI'] = self._rsi(period)
        df['Signal'] = 0
        df.loc[df['RSI'] < oversold, 'Signal'] = 1
        df.loc[df['RSI'] > overbought, 'Signal'] = -1

        # Señales de cierre
        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','RSI','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # ================== ESTRATEGIAS ADICIONALES ACTUALIZADAS ==================

    # 1) Moving Average Crossover (SMA)
    def moving_average_crossover(self, short=20, long=50, exec_lag=1, 
                               exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.MA_CROSSOVER,
                                   ma_fast_period=short,
                                   ma_slow_period=long)
        
        df = self.data.copy()
        df['SMA_short'] = self._sma(df['Close'], short)
        df['SMA_long'] = self._sma(df['Close'], long)
        cond = df['SMA_short'] > df['SMA_long']
        cond_shifted = cond.shift(1, fill_value=False)
        cross_up = cond & (~cond_shifted)
        cross_dn = (~cond) & cond_shifted
        df['Signal'] = 0
        df.loc[cross_up, 'Signal'] = 1
        df.loc[cross_dn, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','SMA_short','SMA_long','Signal',
                                         'ExitSignal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 2) MACD strategy
    def macd_strategy(self, fast=12, slow=26, signal=9, exec_lag=1,
                     exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.MA_CROSSOVER)
        
        df = self.data.copy()
        macd, sig, hist = self._macd(fast, slow, signal)
        df['MACD'] = macd
        df['MACD_signal'] = sig
        df['MACD_hist'] = hist
        df['Signal'] = 0
        cross_up = (df['MACD'] > df['MACD_signal']) & (df['MACD'].shift(1) <= df['MACD_signal'].shift(1))
        cross_dn = (df['MACD'] < df['MACD_signal']) & (df['MACD'].shift(1) >= df['MACD_signal'].shift(1))
        df.loc[cross_up, 'Signal'] = 1
        df.loc[cross_dn, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','MACD','MACD_signal','MACD_hist',
                                         'Signal','ExitSignal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 3) Bollinger Bands strategy
    def bollinger_bands_strategy(self, window=20, num_std=2.0, exec_lag=1,
                                exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.RSI_REVERSAL)
        
        df = self.data.copy()
        ma, upper, lower, std = self._bollinger(window, num_std)
        df['BB_MA'] = ma
        df['BB_upper'] = upper
        df['BB_lower'] = lower
        df['BB_width'] = (upper - lower) / ma
        df['Signal'] = 0
        df.loc[df['Close'] < df['BB_lower'], 'Signal'] = 1
        df.loc[df['Close'] > df['BB_upper'], 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','BB_MA','BB_upper','BB_lower','BB_width',
                                         'Signal','ExitSignal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 4) Stochastic Oscillator strategy
    def stochastic_strategy(self, k=14, d=3, overbought=80, oversold=20, exec_lag=1,
                           exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.RSI_REVERSAL)
        
        df = self.data.copy()
        k_fast, d_slow = self._stochastic(k, d)
        df['%K'] = k_fast
        df['%D'] = d_slow
        df['Signal'] = 0
        long_cond = (df['%K'] < oversold) & (df['%K'] > df['%D']) & (df['%K'].shift(1) <= df['%D'].shift(1))
        short_cond = (df['%K'] > overbought) & (df['%K'] < df['%D']) & (df['%K'].shift(1) >= df['%D'].shift(1))
        df.loc[long_cond, 'Signal'] = 1
        df.loc[short_cond, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','%K','%D','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 5) Ichimoku Cloud strategy
    def ichimoku_cloud_strategy(self, conv=9, base=26, span_b=52, exec_lag=1,
                               exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.MA_CROSSOVER)
        
        df = self.data.copy()
        high = df['High']; low = df['Low']; close = df['Close']
        tenkan_sen = (high.rolling(conv).max() + low.rolling(conv).min()) / 2
        kijun_sen = (high.rolling(base).max() + low.rolling(base).min()) / 2
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(base)
        senkou_span_b = ((high.rolling(span_b).max() + low.rolling(span_b).min()) / 2).shift(base)
        chikou_span = close.shift(-base)

        df['Tenkan'] = tenkan_sen
        df['Kijun'] = kijun_sen
        df['SpanA'] = senkou_span_a
        df['SpanB'] = senkou_span_b
        df['Chikou'] = chikou_span

        df['Signal'] = 0
        bull = (close > df[['SpanA','SpanB']].max(axis=1)) & (tenkan_sen > kijun_sen)
        bear = (close < df[['SpanA','SpanB']].min(axis=1)) & (tenkan_sen < kijun_sen)
        df.loc[bull, 'Signal'] = 1
        df.loc[bear, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','Tenkan','Kijun','SpanA','SpanB',
                                         'Signal','ExitSignal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 6) Support & Resistance strategy
    def support_resistance_strategy(self, lookback=5, exec_lag=1,
                                  exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.SUPPORT_RESISTANCE)
        
        df = self.data.copy()
        df['PivotHigh'] = (df['High'] == df['High'].rolling(lookback, center=True).max()).astype(int)
        df['PivotLow'] = (df['Low'] == df['Low'].rolling(lookback, center=True).min()).astype(int)
        df['Res'] = df['High'].where(df['PivotHigh'] == 1).ffill()
        df['Sup'] = df['Low'].where(df['PivotLow'] == 1).ffill()
        df['Signal'] = 0
        buy = (df['Close'] > df['Sup']) & (df['Low'] <= df['Sup']*1.001)
        sell = (df['Close'] < df['Res']) & (df['High'] >= df['Res']*0.999)
        df.loc[buy, 'Signal'] = 1
        df.loc[sell, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Open','High','Low','Close','Sup','Res','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 7) Price Action Patterns (engulfing)
    def price_action_patterns(self, exec_lag=1, exit_config: ExitConfig = None, **risk_kwargs):
        """Price action con órdenes de cierre"""
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.PRICE_ACTION,
                                   price_action_pattern='engulfing')
        
        df = self.data.copy()
        o,c = df['Open'], df['Close']
        prev_o, prev_c = o.shift(1), c.shift(1)
        
        bull = (prev_c < prev_o) & (c > o) & (c >= prev_o) & (o <= prev_c)
        bear = (prev_c > prev_o) & (c < o) & (o >= prev_c) & (c <= prev_o)
        
        df['Signal'] = 0
        df.loc[bull, 'Signal'] = 1
        df.loc[bear, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Open','Close','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 8) Supply & Demand Zones
    def supply_demand_zones(self, lookback=2, touch_tolerance=0.0015, exec_lag=1,
                           exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.SUPPORT_RESISTANCE)
        
        df = self.data.copy()
        high = df['High']; low = df['Low']
        is_fractal_high = (high.shift(2) < high.shift(1)) & (high.shift(1) < high) & (high.shift(-1) < high) & (high.shift(-2) < high)
        is_fractal_low = (low.shift(2) > low.shift(1)) & (low.shift(1) > low) & (low.shift(-1) > low) & (low.shift(-2) > low)
        df['Supply'] = high.where(is_fractal_high).ffill()
        df['Demand'] = low.where(is_fractal_low).ffill()

        df['Signal'] = 0
        touch_dem = (df['Low'] <= df['Demand'] * (1 + touch_tolerance))
        touch_sup = (df['High'] >= df['Supply'] * (1 - touch_tolerance))
        buy = touch_dem & (df['Close'] > df['Open'])
        sell = touch_sup & (df['Close'] < df['Open'])
        df.loc[buy, 'Signal'] = 1
        df.loc[sell, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','Supply','Demand','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 9) Trendline strategy
    def trendline_strategy(self, window=50, exec_lag=1,
                         exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.MA_CROSSOVER)
        
        df = self.data.copy()
        df['RegLine'] = self._sma(df['Close'], window)
        df['Dev'] = (df['Close'] - df['RegLine'])
        df['Signal'] = 0
        cross_up = (df['Close'] > df['RegLine']) & (df['Close'].shift(1) <= df['RegLine'].shift(1))
        cross_dn = (df['Close'] < df['RegLine']) & (df['Close'].shift(1) >= df['RegLine'].shift(1))
        df.loc[cross_up, 'Signal'] = 1
        df.loc[cross_dn, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','RegLine','Dev','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 10) 1-Minute Scalping strategy
    def scalping_1m_strategy(self, ema_fast=8, ema_slow=21, rsi_period=7, rsi_buy=45, rsi_sell=55, 
                           exec_lag=1, exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.TIME_EXIT, max_bars=10)
        
        df = self.data.copy()
        df['EMA_fast'] = self._ema(df['Close'], ema_fast)
        df['EMA_slow'] = self._ema(df['Close'], ema_slow)
        df['RSI'] = self._rsi(rsi_period)
        df['Signal'] = 0
        long_cond = (df['EMA_fast'] > df['EMA_slow']) & (df['RSI'] > rsi_buy)
        short_cond = (df['EMA_fast'] < df['EMA_slow']) & (df['RSI'] < rsi_sell)
        df.loc[long_cond, 'Signal'] = 1
        df.loc[short_cond, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, atr_period=7, atr_mult=1.5, **risk_kwargs)
        return self._attach_execution(df[['Close','EMA_fast','EMA_slow','RSI','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 11) News Trading strategy
    def news_trading_strategy(self, pre_window=20, spike_mult=1.8, exec_lag=1,
                            events_mask: pd.Series | None = None, 
                            exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.TRAILING_STOP, trailing_atr_mult=2.0)
        
        df = self.data.copy()
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1)).abs()
        tr3 = (df['Low'] - df['Close'].shift(1)).abs()
        df['TR'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['ATR_pre'] = df['TR'].rolling(pre_window).mean()
        df['Spike'] = df['TR'] > (spike_mult * df['ATR_pre'])
        momentum_up = df['Close'] > df['Open']
        momentum_dn = df['Close'] < df['Open']
        df['Signal'] = 0
        mask = events_mask.reindex(df.index).fillna(False) if events_mask is not None else df['Spike']
        df.loc[mask & momentum_up, 'Signal'] = 1
        df.loc[mask & momentum_dn, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, atr_period=max(10, pre_window), atr_mult=2.5, **risk_kwargs)
        return self._attach_execution(df[['Close','ATR_pre','Spike','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 12) Range trading
    def range_trading_strategy(self, window=20, bw_thresh=0.04, exec_lag=1,
                             exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.RSI_REVERSAL)
        
        df = self.data.copy()
        ma, upper, lower, std = self._bollinger(window, 2)
        bw = (upper - lower) / ma
        df['BB_MA'] = ma
        df['BB_upper'] = upper
        df['BB_lower'] = lower
        df['BB_bw'] = bw
        df['Signal'] = 0
        cond_low_bw = bw < bw_thresh
        buy = cond_low_bw & (df['Close'] <= lower)
        sell = cond_low_bw & (df['Close'] >= upper)
        df.loc[buy, 'Signal'] = 1
        df.loc[sell, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','BB_MA','BB_upper','BB_lower','BB_bw',
                                         'Signal','ExitSignal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 13) Carry Trade
    def carry_trade_strategy(self, rate_diff: pd.Series, threshold=0.25, exec_lag=1,
                           exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.MA_CROSSOVER)
        
        if rate_diff is None:
            raise ValueError('Se requiere "rate_diff" (pd.Series) para carry_trade_strategy')
        
        df = self.data.copy()
        df['RateDiff'] = rate_diff.reindex(df.index).astype(float)
        df['Signal'] = 0
        df.loc[df['RateDiff'] > threshold, 'Signal'] = 1
        df.loc[df['RateDiff'] < -threshold, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, atr_mult=3, **risk_kwargs)
        return self._attach_execution(df[['Close','RateDiff','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 14) Hedging strategy
    def hedging_overlay(self, base_signal: pd.Series, atr_period=14, vol_pctl=0.8, exec_lag=1,
                       exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.SIGNAL_REVERSAL)
        
        if base_signal is None:
            raise ValueError('Se requiere "base_signal" (pd.Series) para hedging_overlay')
        
        df = self.data.copy()
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1)).abs()
        tr3 = (df['Low'] - df['Close'].shift(1)).abs()
        df['TR'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['ATR'] = df['TR'].rolling(atr_period).mean()
        thr = df['ATR'].quantile(vol_pctl)
        df['VolHigh'] = df['ATR'] >= thr
        df['Signal'] = base_signal.reindex(df.index).fillna(0)
        df.loc[df['VolHigh'], 'Signal'] = 0

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','ATR','VolHigh','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 15) Grid Trading
    def grid_trading_strategy(self, step_pct=0.005, exec_lag=1,
                            exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.MA_CROSSOVER)
        
        df = self.data.copy()
        df['Anchor'] = self._sma(df['Close'], 100)
        df['Signal'] = 0
        dist = (df['Close'] - df['Anchor']) / df['Anchor']
        df.loc[dist <= -step_pct, 'Signal'] = 1
        df.loc[dist >= step_pct, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, atr_mult=1.8, **risk_kwargs)
        return self._attach_execution(df[['Close','Anchor','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 16) Mean Reversion (z-score)
    def mean_reversion_strategy(self, window=50, z=2.0, exec_lag=1,
                              exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.RSI_REVERSAL)
        
        df = self.data.copy()
        ma = self._sma(df['Close'], window)
        std = df['Close'].rolling(window).std()
        zscore = (df['Close'] - ma) / std
        df['MR_MA'] = ma
        df['MR_z'] = zscore
        df['Signal'] = 0
        df.loc[zscore <= -z, 'Signal'] = 1
        df.loc[zscore >= z, 'Signal'] = -1

        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','MR_MA','MR_z','Signal','ExitSignal',
                                         'StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 17) Martingale overlay
    def martingale_overlay(self, base_signal: pd.Series, max_mult=4, exec_lag=1,
                          exit_config: ExitConfig = None, **risk_kwargs):
        if exit_config is None:
            exit_config = ExitConfig(method=ExitMethod.SIGNAL_REVERSAL)
        
        if base_signal is None:
            raise ValueError('Se requiere "base_signal" (pd.Series) para martingale_overlay')
        
        df = self.data.copy()
        sig = base_signal.reindex(df.index).fillna(0)
        ret = df['Close'].pct_change().fillna(0)
        lose = (sig.shift(1) * ret) < 0
        streak = lose.groupby((lose != lose.shift()).cumsum()).cumsum().fillna(0)
        streak = streak.where(lose, 0)
        mult = (2 ** streak).clip(upper=max_mult)

        df['Signal'] = sig
        df['ExitSignal'] = self._generate_exit_signals(df, exit_config)
        df = self._apply_risk_management(df, **risk_kwargs)
        df['PositionSize'] = (df['PositionSize'] * mult).fillna(0)
        return self._attach_execution(df[['Close','Signal','ExitSignal','StopLoss',
                                         'TakeProfit','PositionSize']], exec_lag)