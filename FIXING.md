## Detección (lógica de patrones)
En patterns/candlestickpatterns.py, clase CandlestickPatterns.

- Cada patrón está implementado como un método que devuelve un DataFrame con la columna Signal. Ejemplos:
    - CandlestickPatterns.doji() (detección Doji) — donde tienes el cursor. Calcula body_ratio y coloca un Signal ponderado por confianza.

    - hammer(), hanging_man(), shooting_star(), spinning_top(), inverted_hammer(), marubozu(), bullish_engulfing(), bearish_engulfing(), piercing_line(), dark_cloud_cover(), morning_star(), evening_star(), three_white_soldiers(), three_black_crows(), tweezer_top(), tweezer_bottom(), inverted_hammer(), marubozu(), bullish_engulfing(), bearish_engulfing(), piercing_line(), dark_cloud_cover(), morning_star(), evening_star(), three_white_soldiers(), three_black_crows(), tweezer_top(), tweezer_bottom(), dark_cloud_cover(), morning_star(), evening_star(), three_white_soldiers(), three_black_crows(), tweezer_top(), tweezer_bottom(), dark_cloud_cover(), morning_star(), evening_star(), three_white_soldiers(), three_black_crows(), tweezer_top(), tweezer_bottom().

    - Métodos agregados:
        - detect_all_patterns() calcula todas las series de Signal y las añade al DF.
        - combined_signal_optimized() combina patrones alcistas/bajistas en Final_Signal.
        - get_trading_signals() expone un Trading_Signal de compatibilidad.

    - Indicadores previos (ATR, RSI, SMA, Volatility, etc.) se calculan en _calculate_indicators() y la confianza por vela en _get_pattern_confidence().

## Invocación (dónde se llaman en estrategias)

- En strategies/candle_strategies.py, clase CandleStrategies.

    - En init se instancia self.patterns = CandlestickPatterns(self.data).
    - Cada estrategia de velas utiliza un patrón y coloca su Signal, luego aplica salidas explícitas con _apply_exit_logic() para generar ExecSignal, Position, StopLoss, TakeProfit, ExitReason.

        - Ejemplos:
            - hammer_reversal_strategy() llama self.patterns.hammer() y filtra con EMA20.
            - bullish_engulfing_strategy() llama self.patterns.bullish_engulfing().
            - doji_reversal_strategy() llama self.patterns.doji() y reinterpreta a 1/-1 con EMA/RSI.
            - También: shooting_star_strategy(), spinning_top_strategy(), inverted_hammer_strategy(), piercing_line_strategy(), dark_cloud_cover_strategy(), tweezer_top_strategy(), tweezer_bottom_strategy(), etc.

## Invocación (GUI y simulaciones)

- En app/gui_main.py se crea CandlestickPatterns en varios puntos para precálculo o validación durante simulación:

    - Al ejecutar patrones desde selección de “pattern” en el flujo de estrategias:
        - Cerca de donde se arma la lista dinámica de métodos:
            - patterns_instance = CandlestickPatterns(self.df_actual) y getattr(patterns_instance, metodo_name) para ejecutar y tomar ['Signal'] (aprox. líneas 667–672).
    - En la precalculación de confirmaciones por patrones:
        - patterns = CandlestickPatterns(self.df_actual) → 
        - df_patterns = patterns.combined_signal_optimized() y se guarda self._pattern_signals alineado al índice (aprox. líneas 1451–1456).
    - En otro bloque de simulación donde se aplican patrones con límite por vela:
        - patterns = CandlestickPatterns(df) → df_patterns = patterns.combined_signal_optimized() (aprox. líneas 1979–1983).
    - También para loguear patrones seleccionados:
        - patterns = CandlestickPatterns(self.df_actual) y luego patterns.__getattribute__(p)()['Signal'] (aprox. líneas 1076–1082).

## Resumen corto

- La detección por vela está definida en patterns/candlestickpatterns.py  dentro de los métodos de CandlestickPatterns (cada uno calcula Signal).

- Las estrategias que consumen estos patrones y generan señales ejecutables con SL/TP están en strategies/candle_strategies.py (clase CandleStrategies).

- La GUI y las simulaciones invocan la detección (y combinaciones) en app/gui_main.py creando instancias de CandlestickPatterns sobre el DataFrame activo (self.df_actual o df) y usando combined_signal_optimized() o métodos individuales.