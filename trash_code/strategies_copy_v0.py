# strategies/strategies.py

import pandas as pd
import numpy as np
from dataclasses import dataclass


class ForexStrategies:
    """
    Estrategias de trading con gestión de riesgo integrada.
    Requiere DataFrame con columnas: ['Open','High','Low','Close'].
    Las funciones devuelven un DataFrame con columnas clave:
    - Signal: señal discreta (1 = largo, -1 = corto, 0 = neutral)
    - ExecSignal: señal ejecutada con retraso (exec_lag)
    - Position: posición mantenida (hold)
    - StopLoss, TakeProfit, PositionSize: gestión de riesgo basada en ATR

    Nota: Algunas estrategias "fundamentales" (carry/news/hedging) necesitan
    series adicionales (p.ej., diferenciales de tipos, eventos, o señal base).
    """

    def __init__(self, data: pd.DataFrame):
        required = {'Open', 'High', 'Low', 'Close'}
        if not required.issubset(data.columns):
            raise ValueError(f"Faltan columnas: {sorted(required - set(data.columns))}")
        self.data = data.sort_index().copy()

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
        """
        Calcula StopLoss, TakeProfit y PositionSize según ATR y % de riesgo.
        """
        df = df.copy()
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs()
        tr3 = (df['Low'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs()
        df['TR'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['ATR'] = df['TR'].rolling(atr_period).mean()

        # StopLoss y TakeProfit según dirección
        df['StopLoss'] = np.where(df['Signal'] == 1,
                                  df['Close'] - df['ATR']*atr_mult,
                                  np.where(df['Signal'] == -1,
                                           df['Close'] + df['ATR']*atr_mult, np.nan))

        df['TakeProfit'] = np.where(df['Signal'] == 1,
                                    df['Close'] + df['ATR']*atr_mult*rr_ratio,
                                    np.where(df['Signal'] == -1,
                                             df['Close'] - df['ATR']*atr_mult*rr_ratio, np.nan))

        # Tamaño de posición
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
            np.maximum((df['High'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs(), (df['Low'] - df['Close'].shift(1, fill_value=df['Close'].iloc[0])).abs())
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

    # ---------------- ADX Strategy ----------------
    def adx_strategy(self, adx_period=14, adx_threshold=25, exec_lag=1, **risk_kwargs):
        """
        Señales:
        - COMPRA: DI+ > DI- y ADX > threshold (tendencia alcista fuerte)
        - VENTA: DI- > DI+ y ADX > threshold (tendencia bajista fuerte)
        """
        df = self.data.copy()
        adx_data = self._calculate_adx(adx_period)
        df = pd.concat([df, adx_data], axis=1)

        df['Signal'] = 0
        buy_condition = (df['DIplus'] > df['DIminus']) & (df['ADX'] > adx_threshold)
        sell_condition = (df['DIminus'] > df['DIplus']) & (df['ADX'] > adx_threshold)
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close', 'DIplus', 'DIminus', 'ADX',
                                          'Signal', 'StopLoss', 'TakeProfit', 'PositionSize']], exec_lag)

    # ---------------- Trend Following (EMA crossover) ----------------
    def trend_following(self, short_window=20, long_window=50, exec_lag=1, **risk_kwargs):
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

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','EMA_short','EMA_long',
                                          'Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # ---------------- Breakout (HH/LL) ----------------
    def breakout(self, window=20, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        df['High_Max'] = df['High'].rolling(window).max().shift(1)
        df['Low_Min'] = df['Low'].rolling(window).min().shift(1)

        df['Signal'] = 0
        df.loc[df['Close'] > df['High_Max'], 'Signal'] = 1
        df.loc[df['Close'] < df['Low_Min'], 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','High_Max','Low_Min',
                                          'Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # ---------------- RSI ----------------
    def rsi_strategy(self, period=14, overbought=70, oversold=30, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        df['RSI'] = self._rsi(period)
        df['Signal'] = 0
        # Señales contrarias (mean-revert):
        df.loc[df['RSI'] < oversold, 'Signal'] = 1
        df.loc[df['RSI'] > overbought, 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','RSI','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # ================== 17 estrategias adicionales ==================
    # 1) Moving Average Crossover (SMA)
    def moving_average_crossover(self, short=20, long=50, exec_lag=1, **risk_kwargs):
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
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','SMA_short','SMA_long','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 2) MACD strategy
    def macd_strategy(self, fast=12, slow=26, signal=9, exec_lag=1, **risk_kwargs):
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
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','MACD','MACD_signal','MACD_hist','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 3) Bollinger Bands strategy
    def bollinger_bands_strategy(self, window=20, num_std=2.0, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        ma, upper, lower, std = self._bollinger(window, num_std)
        df['BB_MA'] = ma
        df['BB_upper'] = upper
        df['BB_lower'] = lower
        df['BB_width'] = (upper - lower) / ma
        df['Signal'] = 0
        # mean reversion
        df.loc[df['Close'] < df['BB_lower'], 'Signal'] = 1
        df.loc[df['Close'] > df['BB_upper'], 'Signal'] = -1
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','BB_MA','BB_upper','BB_lower','BB_width','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 4) Stochastic Oscillator strategy
    def stochastic_strategy(self, k=14, d=3, overbought=80, oversold=20, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        k_fast, d_slow = self._stochastic(k, d)
        df['%K'] = k_fast
        df['%D'] = d_slow
        df['Signal'] = 0
        long_cond = (df['%K'] < oversold) & (df['%K'] > df['%D']) & (df['%K'].shift(1) <= df['%D'].shift(1))
        short_cond = (df['%K'] > overbought) & (df['%K'] < df['%D']) & (df['%K'].shift(1) >= df['%D'].shift(1))
        df.loc[long_cond, 'Signal'] = 1
        df.loc[short_cond, 'Signal'] = -1
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','%K','%D','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 5) Ichimoku Cloud strategy (básica)
    def ichimoku_cloud_strategy(self, conv=9, base=26, span_b=52, exec_lag=1, **risk_kwargs):
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
        # Señal alcista cuando precio por encima de la nube y Tenkan > Kijun
        bull = (close > df[['SpanA','SpanB']].max(axis=1)) & (tenkan_sen > kijun_sen)
        bear = (close < df[['SpanA','SpanB']].min(axis=1)) & (tenkan_sen < kijun_sen)
        df.loc[bull, 'Signal'] = 1
        df.loc[bear, 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','Tenkan','Kijun','SpanA','SpanB','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 6) Support & Resistance strategy (pivots simples)
    def support_resistance_strategy(self, lookback=5, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        # pivotes locales
        df['PivotHigh'] = (df['High'] == df['High'].rolling(lookback, center=True).max()).astype(int)
        df['PivotLow'] = (df['Low'] == df['Low'].rolling(lookback, center=True).min()).astype(int)
        # niveles recientes
        df['Res'] = df['High'].where(df['PivotHigh'] == 1).ffill()
        df['Sup'] = df['Low'].where(df['PivotLow'] == 1).ffill()
        df['Signal'] = 0
        # rebote
        buy = (df['Close'] > df['Sup']) & (df['Low'] <= df['Sup']*1.001)
        sell = (df['Close'] < df['Res']) & (df['High'] >= df['Res']*0.999)
        df.loc[buy, 'Signal'] = 1
        df.loc[sell, 'Signal'] = -1
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','Sup','Res','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 7) Price Action Patterns (engulfing)
    def price_action_patterns(self, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        o,c = df['Open'], df['Close']
        prev_o, prev_c = o.shift(1), c.shift(1)
        # Engulfing alcista: vela roja previa y cuerpo actual cubre cuerpo previo
        bull = (prev_c < prev_o) & (c > o) & (c >= prev_o) & (o <= prev_c)
        # Engulfing bajista
        bear = (prev_c > prev_o) & (c < o) & (o >= prev_c) & (c <= prev_o)
        df['Signal'] = 0
        df.loc[bull, 'Signal'] = 1
        df.loc[bear, 'Signal'] = -1
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Open','Close','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 8) Supply & Demand Zones (fractales simples)
    def supply_demand_zones(self, lookback=2, touch_tolerance=0.0015, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        # fractales de Bill Williams (simplificado)
        high = df['High']; low = df['Low']
        is_fractal_high = (high.shift(2) < high.shift(1)) & (high.shift(1) < high) & (high.shift(-1) < high) & (high.shift(-2) < high)
        is_fractal_low = (low.shift(2) > low.shift(1)) & (low.shift(1) > low) & (low.shift(-1) > low) & (low.shift(-2) > low)
        df['Supply'] = high.where(is_fractal_high).ffill()
        df['Demand'] = low.where(is_fractal_low).ffill()

        df['Signal'] = 0
        # Señal cuando el precio "toca" la zona y gira (aprox: cierre alejado del toque)
        touch_dem = (df['Low'] <= df['Demand'] * (1 + touch_tolerance))
        touch_sup = (df['High'] >= df['Supply'] * (1 - touch_tolerance))
        # giro: cierre en contra del toque
        buy = touch_dem & (df['Close'] > df['Open'])
        sell = touch_sup & (df['Close'] < df['Open'])
        df.loc[buy, 'Signal'] = 1
        df.loc[sell, 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','Supply','Demand','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 9) Trendline strategy (regresión lineal rolling y ruptura)
    def trendline_strategy(self, window=50, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        # línea de tendencia aproximada con SMA + desviación
        df['RegLine'] = self._sma(df['Close'], window)
        df['Dev'] = (df['Close'] - df['RegLine'])
        df['Signal'] = 0
        # ruptura alcista: cierre cruza de abajo a arriba la línea
        cross_up = (df['Close'] > df['RegLine']) & (df['Close'].shift(1) <= df['RegLine'].shift(1))
        cross_dn = (df['Close'] < df['RegLine']) & (df['Close'].shift(1) >= df['RegLine'].shift(1))
        df.loc[cross_up, 'Signal'] = 1
        df.loc[cross_dn, 'Signal'] = -1
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','RegLine','Dev','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 10) 1-Minute Scalping strategy (ventanas cortas)
    def scalping_1m_strategy(self, ema_fast=8, ema_slow=21, rsi_period=7, rsi_buy=45, rsi_sell=55, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        df['EMA_fast'] = self._ema(df['Close'], ema_fast)
        df['EMA_slow'] = self._ema(df['Close'], ema_slow)
        df['RSI'] = self._rsi(rsi_period)
        df['Signal'] = 0
        long_cond = (df['EMA_fast'] > df['EMA_slow']) & (df['RSI'] > rsi_buy)
        short_cond = (df['EMA_fast'] < df['EMA_slow']) & (df['RSI'] < rsi_sell)
        df.loc[long_cond, 'Signal'] = 1
        df.loc[short_cond, 'Signal'] = -1
        df = self._apply_risk_management(df, atr_period=7, atr_mult=1.5, **risk_kwargs)
        return self._attach_execution(df[['Close','EMA_fast','EMA_slow','RSI','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 11) News Trading strategy (ruptura por volatilidad)
    def news_trading_strategy(self, pre_window=20, spike_mult=1.8, exec_lag=1, events_mask: pd.Series | None = None, **risk_kwargs):
        """
        Si se proporciona events_mask (booleano indexado por fecha), se filtran
        señales SOLO en eventos. Si no, se usa un proxy de picos de volatilidad.
        """
        df = self.data.copy()
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1)).abs()
        tr3 = (df['Low'] - df['Close'].shift(1)).abs()
        df['TR'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['ATR_pre'] = df['TR'].rolling(pre_window).mean()
        df['Spike'] = df['TR'] > (spike_mult * df['ATR_pre'])
        # breakout direccional por cierre vs apertura
        momentum_up = df['Close'] > df['Open']
        momentum_dn = df['Close'] < df['Open']
        df['Signal'] = 0
        mask = events_mask.reindex(df.index).fillna(False) if events_mask is not None else df['Spike']
        df.loc[mask & momentum_up, 'Signal'] = 1
        df.loc[mask & momentum_dn, 'Signal'] = -1
        df = self._apply_risk_management(df, atr_period=max(10, pre_window), atr_mult=2.5, **risk_kwargs)
        return self._attach_execution(df[['Close','ATR_pre','Spike','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 12) Range trading (bandwidth baja -> mean reversion)
    def range_trading_strategy(self, window=20, bw_thresh=0.04, exec_lag=1, **risk_kwargs):
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
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','BB_MA','BB_upper','BB_lower','BB_bw','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 13) Carry Trade (requiere diferencial de tipos)
    def carry_trade_strategy(self, rate_diff: pd.Series, threshold=0.25, exec_lag=1, **risk_kwargs):
        """
        rate_diff: Serie del diferencial de tipos (país base - cotizada) en % anual.
        threshold: umbral de preferencia para abrir carry (en %).
        Señal larga si rate_diff > threshold, corta si < -threshold.
        """
        if rate_diff is None:
            raise ValueError('Se requiere "rate_diff" (pd.Series) para carry_trade_strategy')
        df = self.data.copy()
        df['RateDiff'] = rate_diff.reindex(df.index).astype(float)
        df['Signal'] = 0
        df.loc[df['RateDiff'] > threshold, 'Signal'] = 1
        df.loc[df['RateDiff'] < -threshold, 'Signal'] = -1
        df = self._apply_risk_management(df, atr_mult=3, **risk_kwargs)
        return self._attach_execution(df[['Close','RateDiff','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 14) Hedging strategy (overlay que desactiva en alta volatilidad)
    def hedging_overlay(self, base_signal: pd.Series, atr_period=14, vol_pctl=0.8, exec_lag=1, **risk_kwargs):
        """
        base_signal: Serie de señales (-1,0,1) de otra estrategia.
        Reduce/neutraliza posición cuando la volatilidad (ATR) está en percentil alto.
        """
        if base_signal is None:
            raise ValueError('Se requiere "base_signal" (pd.Series) para hedging_overlay')
        df = self.data.copy()
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1)).abs()
        tr3 = (df['Low'] - df['Close'].shift(1)).abs()
        df['TR'] = np.maximum(tr1, np.maximum(tr2, tr3))
        df['ATR'] = df['TR'].rolling(atr_period).mean()
        # umbral por percentil
        thr = df['ATR'].quantile(vol_pctl)
        df['VolHigh'] = df['ATR'] >= thr
        df['Signal'] = base_signal.reindex(df.index).fillna(0)
        # cobertura parcial: señal a 0 cuando volatilidad alta
        df.loc[df['VolHigh'], 'Signal'] = 0
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','ATR','VolHigh','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 15) Grid Trading
    def grid_trading_strategy(self, step_pct=0.005, exec_lag=1, **risk_kwargs):
        """
        Coloca señales de compra por debajo y venta por encima de un precio de referencia
        en escalones (grid). Aquí usamos un "ancla" dinámica: SMA(100).
        """
        df = self.data.copy()
        df['Anchor'] = self._sma(df['Close'], 100)
        df['Signal'] = 0
        # distancia en escalones
        dist = (df['Close'] - df['Anchor']) / df['Anchor']
        # Si muy por debajo -> comprar; muy por encima -> vender
        df.loc[dist <= -step_pct, 'Signal'] = 1
        df.loc[dist >= step_pct, 'Signal'] = -1
        df = self._apply_risk_management(df, atr_mult=1.8, **risk_kwargs)
        return self._attach_execution(df[['Close','Anchor','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 16) Mean Reversion (z-score)
    def mean_reversion_strategy(self, window=50, z=2.0, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        ma = self._sma(df['Close'], window)
        std = df['Close'].rolling(window).std()
        zscore = (df['Close'] - ma) / std
        df['MR_MA'] = ma
        df['MR_z'] = zscore
        df['Signal'] = 0
        df.loc[zscore <= -z, 'Signal'] = 1
        df.loc[zscore >= z, 'Signal'] = -1
        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','MR_MA','MR_z','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # 17) Martingale overlay (multiplica tamaño tras rachas de pérdida)
    def martingale_overlay(self, base_signal: pd.Series, max_mult=4, exec_lag=1, **risk_kwargs):
        """
        base_signal: Serie (-1,0,1) de una estrategia. Aumenta PositionSize tras
        pérdidas consecutivas (simple, basado en retorno siguiente barra).
        Seguridad: tope en max_mult.
        """
        if base_signal is None:
            raise ValueError('Se requiere "base_signal" (pd.Series) para martingale_overlay')
        df = self.data.copy()
        sig = base_signal.reindex(df.index).fillna(0)
        ret = df['Close'].pct_change().fillna(0)
        # pérdida si la señal previa va en contra del retorno de la barra actual
        lose = (sig.shift(1) * ret) < 0
        streak = lose.groupby((lose != lose.shift()).cumsum()).cumsum().fillna(0)
        streak = streak.where(lose, 0)
        mult = (2 ** streak).clip(upper=max_mult)

        df['Signal'] = sig
        df = self._apply_risk_management(df, **risk_kwargs)
        # aplicar multiplicador al tamaño
        df['PositionSize'] = (df['PositionSize'] * mult).fillna(0)
        return self._attach_execution(df[['Close','Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

        df = self.data.copy()
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))

        buy  = (df['RSI'] < oversold)  & (df['RSI'].shift(1) >= oversold)
        sell = (df['RSI'] > overbought) & (df['RSI'].shift(1) <= overbought)

        df['Signal'] = 0
        df.loc[buy, 'Signal']  = 1
        df.loc[sell, 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','RSI',
                                          'Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)