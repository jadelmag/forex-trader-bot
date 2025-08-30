# patterns/candlestickpatterns.py

import pandas as pd
import numpy as np

class CandlestickPatterns:
    def __init__(self, data):
        """
        data: DataFrame con columnas ['Open', 'High', 'Low', 'Close']
        """
        self.data = data.copy()

    # ---------------- Single Candles ----------------
    def doji(self, tol=0.1):
        """Detección optimizada de Doji (indecisión del mercado)"""
        df = self.data.copy()

        # Cuerpo y rango
        body = abs(df['Close'] - df['Open'])
        candle_range = df['High'] - df['Low']

        # Condición: cuerpo muy pequeño relativo al rango de la vela
        cond_doji = body <= candle_range * tol

        # Señal neutral (0) para indecisión
        df['Signal'] = np.where(cond_doji, 0, 0)

        return df[['Open','High','Low','Close','Signal']]

    def hammer(self):
        """Detección optimizada de Hammer (reversión alcista potencial)"""
        df = self.data.copy()

        # Cuerpo y sombras
        body = (df['Close'] - df['Open']).abs()
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)

        # Tendencia bajista previa (EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_downtrend = df['Close'] < df['EMA50']

        # Señal: cuerpo pequeño, sombra inferior al menos el doble del cuerpo, sombra superior pequeña y tendencia bajista
        cond_hammer = (lower_shadow >= 2 * body) & (upper_shadow <= body) & cond_downtrend

        df['Signal'] = np.where(cond_hammer, 1, 0)

        return df[['Open','High','Low','Close','EMA50','Signal']]

    def hanging_man(self):
        """Hanging Man optimizado (reversión bajista)"""
        df = self.hammer().copy()  # Reusar la detección de Hammer

        # Tendencia previa alcista (EMA50)
        df['EMA50'] = self.data['Close'].ewm(span=50).mean()
        cond_prev_uptrend = self.data['Close'] > df['EMA50']

        # Señal final: convertir Hammer en Hanging Man solo si hay tendencia alcista
        df['Signal'] = np.where((df['Signal'] == 1) & cond_prev_uptrend, -1, 0)

        return df

    def shooting_star(self):
        """Shooting Star optimizado (reversión bajista)"""
        df = self.data.copy()

        # Cuerpo y sombras
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']

        # Tendencia previa alcista (EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'] > df['EMA50']

        # Señal: sombra superior >= 2*body y sombra inferior <= body y tendencia alcista
        cond_signal = (upper_shadow >= 2*body) & (lower_shadow <= body) & cond_prev_uptrend

        df['Signal'] = np.where(cond_signal, -1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def spinning_top(self):
        """Spinning Top optimizado (indecisión del mercado)"""
        df = self.data.copy()

        # Cuerpo y rango
        body = abs(df['Close'] - df['Open'])
        range_ = df['High'] - df['Low']

        # Condición: cuerpo pequeño relativo al rango total de la vela
        cond_spinning = body <= range_ * 0.3

        # Asignar señal 0 (neutral) para indecisión
        df['Signal'] = np.where(cond_spinning, 0, 0)

        return df[['Open','High','Low','Close','Signal']]

    def inverted_hammer(self):
        """Inverted Hammer optimizado (reversión alcista potencial)"""
        df = self.data.copy()

        # Cuerpo y sombras
        body = abs(df['Close'] - df['Open'])
        upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
        lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']

        # Tendencia previa bajista (EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'] < df['EMA50']

        # Señal: sombra superior >= 2*body y sombra inferior <= body y tendencia bajista
        cond_signal = (upper_shadow >= 2*body) & (lower_shadow <= body) & cond_prev_downtrend

        df['Signal'] = np.where(cond_signal, 1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    # ---------------- Double Candles ----------------
    def bullish_engulfing(self):
        """Bullish Engulfing optimizado (reversión alcista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: bajista fuerte
        cond_first_bear = (df['Close'].shift(1) < df['Open'].shift(1)) & (body.shift(1) > 0.7 * avg_body.shift(1))

        # Segunda vela: alcista que envuelve la primera
        cond_second_bull = (df['Close'] > df['Open']) & \
                        (df['Open'] < df['Close'].shift(1)) & \
                        (df['Close'] > df['Open'].shift(1)) & \
                        (body > 0.7 * avg_body)

        # Tendencia previa bajista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'].shift(2) < df['EMA50'].shift(2)

        # Señal final
        cond = cond_first_bear & cond_second_bull & cond_prev_downtrend

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def bearish_engulfing(self):
        """Bearish Engulfing optimizado (reversión bajista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: alcista fuerte
        cond_first_bull = (df['Close'].shift(1) > df['Open'].shift(1)) & (body.shift(1) > 0.7 * avg_body.shift(1))

        # Segunda vela: bajista que envuelve la primera
        cond_second_bear = (df['Close'] < df['Open']) & \
                        (df['Open'] > df['Close'].shift(1)) & \
                        (df['Close'] < df['Open'].shift(1)) & \
                        (body > 0.7 * avg_body)

        # Tendencia previa alcista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(2) > df['EMA50'].shift(2)

        # Señal final
        cond = cond_first_bull & cond_second_bear & cond_prev_uptrend

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def piercing_line(self):
        """Piercing Line optimizado (reversión alcista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: bajista fuerte
        cond_first_bear = (df['Close'].shift(1) < df['Open'].shift(1)) & (body.shift(1) > 0.7 * avg_body.shift(1))

        # Segunda vela: abre por debajo del cierre anterior y cierra por encima de la mitad del cuerpo de la primera
        half_first_body = (df['Open'].shift(1) + df['Close'].shift(1)) / 2
        cond_second_bull = (df['Open'] < df['Close'].shift(1)) & (df['Close'] > half_first_body) & (df['Close'] > df['Open'])

        # Tendencia previa bajista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'].shift(2) < df['EMA50'].shift(2)

        # Señal final
        cond = cond_first_bear & cond_second_bull & cond_prev_downtrend

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def dark_cloud_cover(self):
        """Dark Cloud Cover optimizado (reversión bajista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: alcista fuerte
        cond_first_bull = (df['Close'].shift(1) > df['Open'].shift(1)) & (body.shift(1) > 0.7 * avg_body.shift(1))

        # Segunda vela: abre por encima del cierre anterior y cierra por debajo de la mitad de la primera
        half_first_body = (df['Open'].shift(1) + df['Close'].shift(1)) / 2
        cond_second_bear = (df['Open'] > df['Close'].shift(1)) & (df['Close'] < half_first_body) & (df['Close'] < df['Open'])

        # Tendencia previa alcista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(2) > df['EMA50'].shift(2)

        # Señal final
        cond = cond_first_bull & cond_second_bear & cond_prev_uptrend

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def tweezer_top(self, tol=0.001):
        """Tweezer Top optimizado (reversión bajista)"""
        df = self.data.copy()

        # Tendencia previa alcista (EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(1) > df['EMA50'].shift(1)

        # Comparar máximos consecutivos con tolerancia relativa
        cond_tweezer = (abs(df['High'] - df['High'].shift(1)) / df['High'].shift(1) <= tol)

        # Señal final solo si hay tendencia alcista previa
        df['Signal'] = np.where(cond_tweezer & cond_prev_uptrend, -1, 0)

        return df[['Open','High','Low','Close','EMA50','Signal']]

    def tweezer_bottom(self, tol=0.001):
        """Tweezer Bottom optimizado (reversión alcista)"""
        df = self.data.copy()

        # Tendencia previa bajista (EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'].shift(1) < df['EMA50'].shift(1)

        # Comparar mínimos consecutivos con tolerancia relativa
        cond_tweezer = (abs(df['Low'] - df['Low'].shift(1)) / df['Low'].shift(1) <= tol)

        # Señal final solo si hay tendencia bajista previa
        df['Signal'] = np.where(cond_tweezer & cond_prev_downtrend, 1, 0)

        return df[['Open','High','Low','Close','EMA50','Signal']]

    # ---------------- Triple Candles ----------------
    def morning_star(self):
        """Morning Star optimizado (reversión alcista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: bajista fuerte
        cond_first_bear = (df['Close'].shift(2) < df['Open'].shift(2)) & (body.shift(2) > 0.7 * avg_body.shift(2))

        # Segunda vela: pequeña, indecisa
        cond_second_small = (body.shift(1) < 0.5 * body.shift(2))

        # Tercera vela: alcista cerrando por encima del cuerpo de la segunda y mitad de la primera
        half_first_body = (df['Open'].shift(2) + df['Close'].shift(2)) / 2
        cond_third_bull = (df['Close'] > df['Open'].shift(1)) & (df['Close'] > half_first_body) & (df['Close'] > df['Open'])

        # Tendencia previa bajista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'].shift(3) < df['EMA50'].shift(3)

        # Señal final
        cond = cond_first_bear & cond_second_small & cond_third_bull & cond_prev_downtrend

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def evening_star(self):
        """Evening Star optimizado (reversión bajista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: alcista fuerte
        cond_first_bull = (df['Close'].shift(2) > df['Open'].shift(2)) & (body.shift(2) > 0.7 * avg_body.shift(2))

        # Segunda vela: pequeña, indecisa
        cond_second_small = (body.shift(1) < 0.5 * body.shift(2))

        # Tercera vela: bajista cerrando por debajo del cuerpo de la segunda y mitad de la primera
        half_first_body = (df['Open'].shift(2) + df['Close'].shift(2)) / 2
        cond_third_bear = (df['Close'] < df['Open'].shift(1)) & (df['Close'] < half_first_body) & (df['Close'] < df['Open'])

        # Tendencia previa alcista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(3) > df['EMA50'].shift(3)

        # Señal final
        cond = cond_first_bull & cond_second_small & cond_third_bear & cond_prev_uptrend

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def three_white_soldiers(self):
        df = self.data.copy()

        # Condiciones base: 3 velas consecutivas alcistas
        cond_bullish = (
            (df['Close'] > df['Open']) &
            (df['Close'].shift(1) > df['Open'].shift(1)) &
            (df['Close'].shift(2) > df['Open'].shift(2))
        )

        # Cada vela cierra más alto que la anterior
        cond_higher_closes = (
            (df['Close'] > df['Close'].shift(1)) &
            (df['Close'].shift(1) > df['Close'].shift(2))
        )

        # Aperturas dentro del cuerpo de la vela anterior (no gap grande)
        cond_open_within_body = (
            (df['Open'] < df['Close'].shift(1)) &
            (df['Open'] > df['Open'].shift(1))
        )

        # Cuerpos relativamente grandes (evitar dojis)
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()  # promedio de 20 velas
        cond_large_body = (
            (body > 0.5 * avg_body) &
            (body.shift(1) > 0.5 * avg_body.shift(1)) &
            (body.shift(2) > 0.5 * avg_body.shift(2))
        )

        # Cierres cerca del máximo (poca mecha superior)
        upper_shadow = df['High'] - df['Close']
        cond_strong_close = (
            (upper_shadow < (body * 0.3)) &
            (upper_shadow.shift(1) < (body.shift(1) * 0.3)) &
            (upper_shadow.shift(2) < (body.shift(2) * 0.3))
        )

        # Condición de tendencia previa bajista (opcional pero recomendable)
        prev_trend = df['Close'].shift(3).rolling(5).mean()
        cond_prev_downtrend = df['Close'].shift(3) < prev_trend

        # Combinar todas las condiciones
        cond = (
            cond_bullish &
            cond_higher_closes &
            cond_open_within_body &
            cond_large_body &
            cond_strong_close &
            cond_prev_downtrend
        )

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open', 'High', 'Low', 'Close', 'Signal']]

    def three_black_crows(self):
        """Patrón Three Black Crows optimizado"""
        df = self.data.copy()

        # --- Calcular cuerpo y sombras ---
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()
        lower_shadow = df[['Close', 'Open']].min(axis=1) - df['Low']

        # --- Condiciones principales ---
        cond_bearish = (
            (df['Close'] < df['Open']) &
            (df['Close'].shift(1) < df['Open'].shift(1)) &
            (df['Close'].shift(2) < df['Open'].shift(2))
        )

        cond_lower_closes = (
            (df['Close'] < df['Close'].shift(1)) &
            (df['Close'].shift(1) < df['Close'].shift(2))
        )

        # Apertura dentro del cuerpo de la vela anterior (no gaps raros)
        cond_open_within_body = (
            (df['Open'] < df['Close'].shift(1)) &
            (df['Open'] > df['Open'].shift(1))
        )

        # Cuerpos grandes (evita dojis)
        cond_large_body = (
            (body > 0.5 * avg_body) &
            (body.shift(1) > 0.5 * avg_body.shift(1)) &
            (body.shift(2) > 0.5 * avg_body.shift(2))
        )

        # Cierre fuerte (cerca del mínimo, poca mecha inferior)
        cond_strong_close = (
            (lower_shadow < body * 0.3) &
            (lower_shadow.shift(1) < body.shift(1) * 0.3) &
            (lower_shadow.shift(2) < body.shift(2) * 0.3)
        )

        # Tendencia previa alcista (confirmación de reversión)
        prev_trend = df['Close'].shift(3).rolling(5).mean()
        cond_prev_uptrend = df['Close'].shift(3) > prev_trend

        # --- Señal final ---
        cond = (
            cond_bearish &
            cond_lower_closes &
            cond_open_within_body &
            cond_large_body &
            cond_strong_close &
            cond_prev_uptrend
        )

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','Signal']]

    def three_inside_up(self):
        """Three Inside Up optimizado (reversión alcista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: bajista fuerte
        cond_first_bear = (df['Close'].shift(2) < df['Open'].shift(2)) & (body.shift(2) > 0.7 * avg_body.shift(2))

        # Segunda vela: alcista dentro del cuerpo de la primera
        cond_second_inside = (df['Close'].shift(1) > df['Open'].shift(1)) & \
                            (df['Close'].shift(1) < df['Open'].shift(2)) & \
                            (df['Open'].shift(1) > df['Close'].shift(2))

        # Tercera vela: alcista cerrando por encima del cierre de la primera
        cond_third_bull = (df['Close'] > df['Close'].shift(2)) & (df['Close'] > df['Open']) & (body > 0.7 * avg_body)

        # Tendencia previa bajista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'].shift(3) < df['EMA50'].shift(3)

        # Señal final
        cond = cond_first_bear & cond_second_inside & cond_third_bull & cond_prev_downtrend

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def three_inside_down(self):
        """Three Inside Down optimizado (reversión bajista)"""
        df = self.data.copy()

        # Cuerpo y promedio
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: alcista fuerte
        cond_first_bull = (df['Close'].shift(2) > df['Open'].shift(2)) & (body.shift(2) > 0.7 * avg_body.shift(2))

        # Segunda vela: bajista dentro del cuerpo de la primera
        cond_second_inside = (df['Close'].shift(1) < df['Open'].shift(1)) & \
                            (df['Close'].shift(1) > df['Open'].shift(2)) & \
                            (df['Open'].shift(1) < df['Close'].shift(2))

        # Tercera vela: bajista cerrando por debajo del cierre de la primera
        cond_third_bear = (df['Close'] < df['Close'].shift(2)) & (df['Close'] < df['Open']) & (body > 0.7 * avg_body)

        # Tendencia previa alcista
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(3) > df['EMA50'].shift(3)

        # Señal final
        cond = cond_first_bull & cond_second_inside & cond_third_bear & cond_prev_uptrend

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def rising_three_methods(self):
        """Rising Three Methods optimizado (continuación alcista)"""
        df = self.data.copy()

        # Cuerpo y rango de velas
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: fuerte alcista
        cond_first_bull = (df['Close'].shift(4) > df['Open'].shift(4)) & (body.shift(4) > 0.7 * avg_body.shift(4))

        # Tres velas internas: bajistas pequeñas dentro del rango de la primera
        cond_middle_bear = (
            (df['Close'].shift(3) < df['Open'].shift(3)) & (body.shift(3) < 0.5 * avg_body.shift(3)) &
            (df['Close'].shift(2) < df['Open'].shift(2)) & (body.shift(2) < 0.5 * avg_body.shift(2)) &
            (df['Close'].shift(1) < df['Open'].shift(1)) & (body.shift(1) < 0.5 * avg_body.shift(1)) &
            (df['Low'].shift(3) > df['Open'].shift(4)) & (df['Low'].shift(2) > df['Open'].shift(4)) & (df['Low'].shift(1) > df['Open'].shift(4))
        )

        # Última vela: fuerte alcista cerrando por encima de la primera
        cond_last_bull = (df['Close'] > df['Close'].shift(4)) & (df['Close'] > df['Open']) & (body > 0.7 * avg_body)

        # Tendencia previa alcista (opcional, usando EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_uptrend = df['Close'].shift(5) > df['EMA50'].shift(5)

        # Señal final
        cond = cond_first_bull & cond_middle_bear & cond_last_bull & cond_prev_uptrend

        df['Signal'] = np.where(cond, 1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    def falling_three_methods(self):
        """Falling Three Methods optimizado (continuación bajista)"""
        df = self.data.copy()

        # Cuerpo y rango de velas
        body = (df['Close'] - df['Open']).abs()
        avg_body = body.rolling(20).mean()

        # Primera vela: fuerte bajista
        cond_first_bear = (df['Close'].shift(4) < df['Open'].shift(4)) & (body.shift(4) > 0.7 * avg_body.shift(4))

        # Tres velas internas: alcistas pequeñas dentro del rango de la primera
        cond_middle_bull = (
            (df['Close'].shift(3) > df['Open'].shift(3)) & (body.shift(3) < 0.5 * avg_body.shift(3)) &
            (df['Close'].shift(2) > df['Open'].shift(2)) & (body.shift(2) < 0.5 * avg_body.shift(2)) &
            (df['Close'].shift(1) > df['Open'].shift(1)) & (body.shift(1) < 0.5 * avg_body.shift(1)) &
            (df['High'].shift(3) < df['Open'].shift(4)) & (df['High'].shift(2) < df['Open'].shift(4)) & (df['High'].shift(1) < df['Open'].shift(4))
        )

        # Última vela: fuerte bajista cerrando debajo de la primera
        cond_last_bear = (df['Close'] < df['Close'].shift(4)) & (df['Close'] < df['Open']) & (body > 0.7 * avg_body)

        # Tendencia previa bajista (opcional, usando EMA50)
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        cond_prev_downtrend = df['Close'].shift(5) < df['EMA50'].shift(5)

        # Señal final
        cond = cond_first_bear & cond_middle_bull & cond_last_bear & cond_prev_downtrend

        df['Signal'] = np.where(cond, -1, 0)
        return df[['Open','High','Low','Close','EMA50','Signal']]

    # ---------------- Detect all patterns ----------------
    def detect_all_patterns(self):
        df = self.data.copy()
        pattern_functions = [
            'doji', 'hammer', 'hanging_man', 'shooting_star', 'spinning_top', 'inverted_hammer',
            'bullish_engulfing', 'bearish_engulfing', 'piercing_line', 'dark_cloud_cover',
            'tweezer_top', 'tweezer_bottom',
            'morning_star', 'evening_star', 'three_white_soldiers', 'three_black_crows',
            'three_inside_up', 'three_inside_down', 'rising_three_methods', 'falling_three_methods'
        ]
        for func_name in pattern_functions:
            func = getattr(self, func_name)
            df[func_name] = func()['Signal']
        return df

    # ---------------- Combined signal optimized ----------------
    def combined_signal_optimized(self):
        """Combina todas las señales de patrones en una señal final optimizada"""
        df = self.detect_all_patterns().copy()

        # Filtrar solo columnas de patrones (excluyendo OHLC y otras)
        pattern_cols = df.columns.difference(['Open','High','Low','Close'])
        if pattern_cols.empty:
            raise ValueError("No se detectaron columnas de patrones para combinar")

        # Detectar señales alcistas y bajistas
        has_bull = (df[pattern_cols] == 1).any(axis=1)
        has_bear = (df[pattern_cols] == -1).any(axis=1)

        # Inicializar Final_Signal
        df['Final_Signal'] = 0

        # Asignar señales según combinaciones
        df.loc[has_bull & ~has_bear, 'Final_Signal'] = 1
        df.loc[has_bear & ~has_bull, 'Final_Signal'] = -1
        # Si hay conflicto (ambos), deja 0

        return df
