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
        self.patterns = CandlestickPatterns(self.data)

    # ---------------- Utils ----------------
    def add_indicators(self):
        """Agrega indicadores de tendencia y volatilidad básicos optimizados"""
        df = self.data.copy()

        # --- EMAs ---
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

        # --- True Range y ATR 14 ---
        df['PrevClose'] = df['Close'].shift(1)
        df['TR'] = df[['High', 'PrevClose']].max(axis=1) - df[['Low', 'PrevClose']].min(axis=1)
        df['ATR'] = df['TR'].rolling(14).mean()

        # Limpiar columna temporal
        df.drop(columns=['PrevClose', 'TR'], inplace=True)

        return df

    # ---------------- Estrategias de reversión alcista ----------------
    def hammer_reversal(self):
        """Patrón Hammer optimizado (reversión alcista)"""
        df = self.data.copy()

        # Calcular cuerpo y sombras
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['UpperShadow'] = df['High'] - df[['Open','Close']].max(axis=1)
        df['LowerShadow'] = df[['Open','Close']].min(axis=1) - df['Low']
        avg_body = df['Body'].rolling(20).mean()

        # Condiciones de Hammer
        cond_small_body = df['Body'] < 1.2 * avg_body        # cuerpo pequeño
        cond_long_lower_shadow = df['LowerShadow'] >= 2 * df['Body']
        cond_small_upper_shadow = df['UpperShadow'] <= 0.2 * df['Body']

        # Tendencia previa bajista (precio por debajo de EMA20)
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_downtrend = df['Close'].shift(1) < df['EMA20'].shift(1)

        # Confirmación opcional: siguiente vela alcista
        cond_confirmation = df['Close'].shift(-1) > df['Open'].shift(-1)

        # Señal final
        cond = cond_small_body & cond_long_lower_shadow & cond_small_upper_shadow & cond_prev_downtrend & cond_confirmation

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','EMA20','Signal']]

    def bullish_engulfing_reversal(self):
        """Envolvente alcista tras tendencia bajista (optimizado)"""
        df = self.data.copy()

        # Condiciones para envolvente alcista
        cond_bearish_prev = df['Close'].shift(1) < df['Open'].shift(1)  # vela anterior bajista
        cond_bullish_curr = df['Close'] > df['Open']                    # vela actual alcista

        # Cuerpo de la vela actual envuelve completamente al cuerpo de la anterior
        cond_engulfing = (
            (df['Open'] < df['Close'].shift(1)) &   # abre debajo del cierre previo
            (df['Close'] > df['Open'].shift(1))     # cierra por encima de la apertura previa
        )

        # Cuerpo relativamente grande comparado con promedio de 20 velas
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()
        cond_large_body = body > 0.7 * avg_body

        # Cierre cerca del máximo (fuerza compradora)
        upper_shadow = df['High'] - df['Close']
        cond_strong_close = upper_shadow < (body * 0.3)

        # Tendencia bajista previa (precio debajo de media móvil)
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_downtrend = df['Close'].shift(2) < df['EMA20'].shift(2)

        # Señal final
        cond = (
            cond_bearish_prev &
            cond_bullish_curr &
            cond_engulfing &
            cond_large_body &
            cond_strong_close &
            cond_prev_downtrend
        )

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open', 'High', 'Low', 'Close', 'EMA20', 'Signal']]

    def morning_star_swing(self):
        """Patrón Morning Star optimizado (reversión alcista)"""
        df = self.data.copy()

        # Cuerpo y sombras
        df['Body'] = (df['Close'] - df['Open']).abs()
        avg_body = df['Body'].rolling(20).mean()
        upper_shadow = df['High'] - df['Close']
        lower_shadow = df['Open'] - df['Low']

        # Primera vela: bajista fuerte
        cond_first_bearish = (df['Close'].shift(2) < df['Open'].shift(2)) & (df['Body'].shift(2) > 0.7 * avg_body.shift(2))

        # Segunda vela: pequeña, indecisión
        cond_second_small = df['Body'].shift(1) < 0.5 * avg_body.shift(1)

        # Tercera vela: alcista fuerte
        cond_third_bullish = (df['Close'] > df['Open']) & (df['Body'] > 0.7 * avg_body)

        # Cierre de la tercera por encima de la mitad de la primera
        cond_close_above_mid = df['Close'] > ((df['Open'].shift(2) + df['Close'].shift(2)) / 2)

        # Tendencia previa bajista (confirmación)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'].shift(3) < df['EMA50'].shift(3)

        # Señal final
        cond = cond_first_bearish & cond_second_small & cond_third_bullish & cond_close_above_mid & cond_prev_downtrend

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    # ---------------- Estrategias de reversión bajista ----------------
    def hanging_man_reversal(self):
        """Patrón Hanging Man optimizado para detección de reversión bajista"""
        df = self.data.copy()

        # Medidas de la vela
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['UpperShadow'] = df['High'] - df[['Open','Close']].max(axis=1)
        df['LowerShadow'] = df[['Open','Close']].min(axis=1) - df['Low']
        avg_body = df['Body'].rolling(20).mean()

        # Condiciones del Hanging Man
        cond_small_body = df['Body'] < 1.2 * avg_body  # cuerpo no demasiado grande
        cond_long_lower_shadow = df['LowerShadow'] >= 2 * df['Body']
        cond_small_upper_shadow = df['UpperShadow'] <= 0.2 * df['Body']

        # Tendencia previa alcista (precio por encima de EMA20)
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_uptrend = df['Close'].shift(1) > df['EMA20'].shift(1)

        # Confirmación opcional: siguiente vela bajista
        cond_confirmation = df['Close'].shift(-1) < df['Open'].shift(-1)

        # Señal final
        cond = cond_small_body & cond_long_lower_shadow & cond_small_upper_shadow & cond_prev_uptrend & cond_confirmation

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA20','Signal']]

    def bearish_engulfing_reversal(self):
        """Patrón Bearish Engulfing optimizado (reversión bajista)"""
        df = self.data.copy()

        # --- Cálculo de cuerpo y sombras ---
        df['Body'] = (df['Close'] - df['Open']).abs()
        avg_body = df['Body'].rolling(20).mean()
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)

        # --- Condiciones básicas del patrón ---
        cond_prev_bullish = df['Close'].shift(1) > df['Open'].shift(1)   # vela anterior alcista
        cond_curr_bearish = df['Close'] < df['Open']                     # vela actual bajista

        # La vela bajista envuelve completamente a la alcista previa
        cond_engulfing = (
            (df['Open'] > df['Close'].shift(1)) &  # abre por encima del cierre anterior
            (df['Close'] < df['Open'].shift(1))    # cierra por debajo de la apertura anterior
        )

        # Cuerpo relativamente grande
        cond_large_body = df['Body'] > 0.7 * avg_body

        # Cierre fuerte (cerca del mínimo de la vela actual)
        cond_strong_close = upper_shadow < (df['Body'] * 0.3)

        # Tendencia previa alcista
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        cond_prev_uptrend = df['Close'].shift(2) > df['EMA20'].shift(2)

        # Señal final
        cond = (
            cond_prev_bullish &
            cond_curr_bearish &
            cond_engulfing &
            cond_large_body &
            cond_strong_close &
            cond_prev_uptrend
        )

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA20','Signal']]

    def evening_star_swing(self):
        """Patrón Evening Star optimizado con confirmación de tendencia alcista previa"""
        df = self.data.copy()

        # Calcular cuerpos y sombras
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        upper_shadow = df['High'] - df[['Close', 'Open']].max(axis=1)
        lower_shadow = df[['Close', 'Open']].min(axis=1) - df['Low']

        # Condiciones del patrón
        cond_first_bullish = (df['Close'].shift(2) > df['Open'].shift(2)) & (body.shift(2) > 0.7 * avg_body.shift(2))
        cond_second_small = body.shift(1) < 0.5 * avg_body.shift(1)  # vela débil / indecisión
        cond_third_bearish = (df['Close'] < df['Open']) & (body > 0.7 * avg_body)

        # Confirmación: la tercera vela cierra al menos debajo de la mitad de la primera
        cond_close_below_mid = df['Close'] < ((df['Open'].shift(2) + df['Close'].shift(2)) / 2)

        # Cierre fuerte (cerca del mínimo de la vela actual)
        cond_strong_close = (lower_shadow < body * 0.3)

        # Tendencia previa alcista (precio por encima de EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(3) > df['EMA50'].shift(3)

        # Señal final
        cond = (
            cond_first_bullish &
            cond_second_small &
            cond_third_bearish &
            cond_close_below_mid &
            cond_strong_close &
            cond_prev_uptrend
        )

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open', 'High', 'Low', 'Close', 'EMA50', 'Signal']]

    # ---------------- Estrategias de indecisión / continuación ----------------
    def doji_indecision(self):
        """Detección optimizada de velas Doji e indecisión"""
        df = self.data.copy()

        # Medidas básicas
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['Range'] = df['High'] - df['Low']
        df['UpperShadow'] = df['High'] - df[['Open','Close']].max(axis=1)
        df['LowerShadow'] = df[['Open','Close']].min(axis=1) - df['Low']

        # Promedio de cuerpos para referencia
        avg_body = df['Body'].rolling(20).mean()

        # --- Condición base de Doji ---
        cond_doji = df['Body'] <= (0.1 * df['Range'])  # cuerpo muy pequeño
        df['DojiType'] = "Doji"

        # --- Clasificación de tipos de doji ---
        df.loc[cond_doji & (df['UpperShadow'] > 2 * df['LowerShadow']), 'DojiType'] = "Gravestone Doji"
        df.loc[cond_doji & (df['LowerShadow'] > 2 * df['UpperShadow']), 'DojiType'] = "Dragonfly Doji"
        df.loc[cond_doji & (df['UpperShadow'] > 0.4 * df['Range']) & (df['LowerShadow'] > 0.4 * df['Range']), 'DojiType'] = "Long-Legged Doji"

        # Señal neutra por defecto
        df['Signal'] = 0

        # --- Opcional: marcar riesgo de reversión ---
        # Si el doji aparece tras fuerte tendencia alcista → riesgo bajista
        cond_bear_risk = cond_doji & (df['Close'].shift(3) > df['Open'].shift(3)) & (df['Close'] > df['Open'].rolling(5).mean())
        # Si aparece tras fuerte tendencia bajista → riesgo alcista
        cond_bull_risk = cond_doji & (df['Close'].shift(3) < df['Open'].shift(3)) & (df['Close'] < df['Close'].rolling(5).mean())

        df.loc[cond_bear_risk, 'Signal'] = -2
        df.loc[cond_bull_risk, 'Signal'] = 2

        return df[['Open','High','Low','Close','DojiType','Signal']]

    def marubozu_trend(self):
        """Detección optimizada de velas Marubozu (alcista/bajista)"""
        df = self.data.copy()

        # Cuerpo y sombras
        df['Body'] = (df['Close'] - df['Open']).abs()
        df['UpperShadow'] = df['High'] - df[['Open','Close']].max(axis=1)
        df['LowerShadow'] = df[['Open','Close']].min(axis=1) - df['Low']

        # Tamaño promedio de los cuerpos para referencia
        avg_body = df['Body'].rolling(20).mean()

        # Señal inicial
        df['Signal'] = 0

        # Marubozu alcista
        cond_bull = (
            (df['Close'] > df['Open']) &
            (df['Body'] > 1.2 * avg_body) &  # cuerpo mayor al promedio
            (df['UpperShadow'] < df['Body'] * 0.1) &  # sombra superior < 10%
            (df['LowerShadow'] < df['Body'] * 0.1)   # sombra inferior < 10%
        )

        # Marubozu bajista
        cond_bear = (
            (df['Close'] < df['Open']) &
            (df['Body'] > 1.2 * avg_body) &
            (df['UpperShadow'] < df['Body'] * 0.1) &
            (df['LowerShadow'] < df['Body'] * 0.1)
        )

        df.loc[cond_bull, 'Signal'] = 1
        df.loc[cond_bear, 'Signal'] = -1

        return df[['Open','High','Low','Close','Signal']]

    # ---------------- Estrategias de múltiples velas ----------------
    def three_white_soldiers(self):
        df = self.patterns.three_white_soldiers()
        return df

    def three_black_crows(self):
        df = self.patterns.three_black_crows()
        return df

    # ---------------- Estrategias de trading ----------------
    def scalping_reversal(self):
        """Scalping con Hammer + Bullish Engulfing optimizado sobre soportes"""
        df_h = self.hammer_reversal()
        df_e = self.bullish_engulfing_reversal()
        df = self.data.copy()

        # Identificar soporte simple: mínimo de las últimas 10 velas
        df['Support'] = df['Low'].rolling(10).min()

        # Solo marcar señal si se encuentra cerca del soporte
        cond_h = (df_h['Signal'] == 1) & (df['Close'] <= df['Support'] * 1.01)
        cond_e = (df_e['Signal'] == 1) & (df['Close'] <= df['Support'] * 1.01)

        # Señal final
        df['Signal'] = np.where(cond_h | cond_e, 1, 0)

        # Limpiar columna de soporte temporal
        df.drop(columns=['Support'], inplace=True)

        return df[['Open','High','Low','Close','Signal']]

    def swing_trading(self):
        """Swing trading con Morning Star y Evening Star optimizado"""
        df_m = self.morning_star_swing()
        df_e = self.evening_star_swing()
        df = self.data.copy()

        # Señal alcista si Morning Star detectada
        cond_m = df_m['Signal'] == 1

        # Señal bajista si Evening Star detectada
        cond_e = df_e['Signal'] == -1

        # Señal final
        df['Signal'] = np.where(cond_m, 1, np.where(cond_e, -1, 0))

        # Mantener solo columnas relevantes
        return df[['Open','High','Low','Close','Signal']]

    def filter_with_trend(self):
        """Filtro combinado con EMA50 optimizado"""
        df = self.patterns.combined_signal_optimized()
        
        # Calcular EMA50 solo si no existe
        if 'EMA50' not in df.columns:
            df['EMA50'] = self.data['Close'].ewm(span=50, adjust=False).mean()
        
        # Filtro de tendencia: mantener señal solo si coincide con EMA50
        cond_long = (df['Final_Signal'] == 1) & (df['Close'] > df['EMA50'])
        cond_short = (df['Final_Signal'] == -1) & (df['Close'] < df['EMA50'])

        df['Final_Signal'] = np.where(cond_long, 1, np.where(cond_short, -1, 0))

        # Mantener solo columnas esenciales
        return df[['Open','High','Low','Close','EMA50','Final_Signal']]

    def stop_loss_take_profit(self, rr_ratio=2):
        """Calcula niveles SL y TP usando ATR y señal combinada optimizada"""
        # Agregar indicadores
        df = self.add_indicators()

        # Obtener señal combinada
        signals = self.patterns.combined_signal_optimized()
        if 'Final_Signal' not in signals.columns:
            raise ValueError("El DataFrame de señales debe contener 'Final_Signal'")
        df['Signal'] = signals['Final_Signal']

        # Validar ATR
        if 'ATR' not in df.columns:
            raise ValueError("El DataFrame debe contener 'ATR' para calcular SL/TP")

        # Calcular Stop Loss
        df['StopLoss'] = np.where(
            df['Signal'] == 1, df['Close'] - df['ATR'],
            np.where(df['Signal'] == -1, df['Close'] + df['ATR'], np.nan)
        )

        # Calcular Take Profit
        df['TakeProfit'] = np.where(
            df['Signal'] == 1, df['Close'] + df['ATR'] * rr_ratio,
            np.where(df['Signal'] == -1, df['Close'] - df['ATR'] * rr_ratio, np.nan)
        )

        # Mantener columnas relevantes
        return df[['Open','High','Low','Close','Signal','StopLoss','TakeProfit']]

