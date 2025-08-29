# strategies/strategies.py

import pandas as pd
import numpy as np

class ForexStrategies:
    """
    Estrategias de trading con gestión de riesgo integrada.
    Requiere DataFrame con columnas: ['Open','High','Low','Close'].
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
        out['ExecSignal'] = out['Signal'].shift(exec_lag).fillna(0)
        out['Position'] = self._position_from_signal(out['ExecSignal'])
        return out

    def _apply_risk_management(self, df: pd.DataFrame, 
                               account_size=10000, risk_per_trade=0.01,
                               atr_period=14, atr_mult=2, rr_ratio=2):
        """
        Calcula StopLoss, TakeProfit y PositionSize según ATR y % de riesgo.
        """
        df = df.copy()
        df['ATR'] = (df['High'] - df['Low']).rolling(atr_period).mean()

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
        df['PositionSize'] = np.where(df['Signal'] != 0,
                                      risk_amount / (df['ATR']*atr_mult),
                                      0)
        return df

    # ------- ADX Helper -------
    def _calculate_adx(self, period=14):
        """Calcula ADX, DI+ y DI-"""
        df = self.data.copy()
        
        # Calcular True Range
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        
        # Calcular Directional Movement
        df['DMplus'] = np.where(
            (df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']),
            np.maximum(df['High'] - df['High'].shift(1), 0),
            0
        )
        
        df['DMminus'] = np.where(
            (df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)),
            np.maximum(df['Low'].shift(1) - df['Low'], 0),
            0
        )
        
        # Suavizar con media móvil
        df['TR_smooth'] = df['TR'].rolling(period).mean()
        df['DMplus_smooth'] = df['DMplus'].rolling(period).mean()
        df['DMminus_smooth'] = df['DMminus'].rolling(period).mean()
        
        # Calcular DI+ y DI-
        df['DIplus'] = (df['DMplus_smooth'] / df['TR_smooth']) * 100
        df['DIminus'] = (df['DMminus_smooth'] / df['TR_smooth']) * 100
        
        # Calcular DX y ADX
        df['DX'] = (abs(df['DIplus'] - df['DIminus']) / (df['DIplus'] + df['DIminus'])) * 100
        df['ADX'] = df['DX'].rolling(period).mean()
        
        return df[['DIplus', 'DIminus', 'ADX']]

    # ---------------- ADX Strategy ----------------
    def adx_strategy(self, adx_period=14, adx_threshold=25, exec_lag=1, **risk_kwargs):
        """
        Estrategia basada en ADX y Direccional Movement Index.
        
        Señales:
        - COMPRA: DI+ > DI- y ADX > threshold (tendencia alcista fuerte)
        - VENTA: DI- > DI+ y ADX > threshold (tendencia bajista fuerte)
        """
        df = self.data.copy()
        
        # Calcular indicadores ADX
        adx_data = self._calculate_adx(adx_period)
        df = pd.concat([df, adx_data], axis=1)
        
        # Generar señales
        df['Signal'] = 0
        
        # Señal de compra: DI+ cruza por encima de DI- con ADX fuerte
        buy_condition = (df['DIplus'] > df['DIminus']) & (df['ADX'] > adx_threshold)
        df.loc[buy_condition, 'Signal'] = 1
        
        # Señal de venta: DI- cruza por encima de DI+ con ADX fuerte
        sell_condition = (df['DIminus'] > df['DIplus']) & (df['ADX'] > adx_threshold)
        df.loc[sell_condition, 'Signal'] = -1
        
        # Aplicar gestión de riesgo
        df = self._apply_risk_management(df, **risk_kwargs)
        
        return self._attach_execution(df[['Close', 'DIplus', 'DIminus', 'ADX',
                                         'Signal', 'StopLoss', 'TakeProfit', 'PositionSize']], exec_lag)

    # ---------------- Trend Following ----------------
    def trend_following(self, short_window=20, long_window=50, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        df['EMA_short'] = df['Close'].ewm(span=short_window, adjust=False).mean()
        df['EMA_long']  = df['Close'].ewm(span=long_window, adjust=False).mean()

        cond = df['EMA_short'] > df['EMA_long']
        
        # Usar numpy para manejar los NaN de manera más eficiente
        cond_shifted = cond.shift(1)
        cond_shifted_filled = cond_shifted.where(cond_shifted.notna(), False)
        
        cross_up = cond & (~cond_shifted_filled)
        cross_dn = (~cond) & cond_shifted_filled

        df['Signal'] = 0
        df.loc[cross_up, 'Signal'] = 1
        df.loc[cross_dn, 'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','EMA_short','EMA_long',
                                        'Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)   

    # ---------------- Breakout ----------------
    def breakout(self, window=20, exec_lag=1, **risk_kwargs):
        df = self.data.copy()
        df['High_Max'] = df['High'].rolling(window).max().shift(1)
        df['Low_Min']  = df['Low'].rolling(window).min().shift(1)

        df['Signal'] = 0
        df.loc[df['Close'] > df['High_Max'], 'Signal'] = 1
        df.loc[df['Close'] < df['Low_Min'],  'Signal'] = -1

        df = self._apply_risk_management(df, **risk_kwargs)
        return self._attach_execution(df[['Close','High_Max','Low_Min',
                                          'Signal','StopLoss','TakeProfit','PositionSize']], exec_lag)

    # ---------------- RSI ----------------
    def rsi_strategy(self, period=14, overbought=70, oversold=30, exec_lag=1, **risk_kwargs):
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