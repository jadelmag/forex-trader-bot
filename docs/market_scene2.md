1. MERCADO TENDENCIAL (TRENDING)

**Tendencia Alcista:**
- three_white_soldiers_strategy() - Fuerte continuación alcista
- bullish_engulfing_strategy() - Confirmación de tendencia
- marubozu_trend() - Impulso fuerte con filtro de tendencia

**Tendencia Bajista:**
- three_black_crows_strategy() - Fuerte continuación bajista
- bearish_engulfing_strategy() - Confirmación de tendencia
- marubozu_trend() - Impulso bajista con filtro

2. MERCADO LATERAL (RANGING)

**Rebotes en Soportes:**
- hammer_reversal_strategy() - Reversión alcista en soporte
- tweezer_bottom_strategy() - Doble fondo en soporte
- bullish_engulfing_strategy() - Engulfing alcista en soporte

**Rebotes en Resistencias:**
- hanging_man_strategy() - Reversión bajista en resistencia
- shooting_star_strategy() - Estrella fugaz en resistencia
- tweezer_top_strategy() - Doble techo en resistencia

3. MERCADO EN TRANSICIÓN

**Acumulación (Cambio a Alcista):**
- morning_star_strategy() - Fuerte reversión alcista
- hammer_reversal_strategy() - Martillo en fondo
- piercing_line_strategy() - Línea perforante

**Distribución (Cambio a Bajista):**
- evening_star_strategy() - Fuerte reversión bajista
- dark_cloud_cover_strategy() - Cubierta nubosa oscura
- bearish_engulfing_strategy() - Engulfing bajist

4. ALTA VOLATILIDAD (BREAKOUT)

- marubozu_trend() - Velas de impulso sin mechas
- bullish_engulfing_strategy() - Confirmación ruptura alcista
- bearish_engulfing_strategy() - Confirmación ruptura bajista

5. BAJA VOLATILIDAD (CONTRACCIÓN)

- doji_reversal_strategy() - Indecisión, posible cambio
- spinning_top_strategy() - Equilibrio, espera ruptura
- filter_with_trend() - Espera señal con filtro de tendencia

6. FALSAS RUPTURAS (FAKEOUTS)

- inverted_hammer_strategy() - Fakeout bajista fallido
- shooting_star_strategy() - Fakeout alcista fallido
- tweezer_top/bottom_strategy() - Reversión tras fakeout

🎯 ESTRATEGIAS COMBINADAS
- swing_trading() - Ideal para mercados con tendencia (Morning/Evening Star)
- scalping_reversal() - Para rangos y reversiones (Hammer + Engulfing)
- filter_with_trend() - Filtra señales con media de 50 periodos

⚖️ ESTRATEGIAS NEUTRALES
- doji_reversal_strategy() - Funciona en múltiples escenarios
- spinning_top_strategy() - Indecisión, requiere confirmación

📊 RESUMEN POR PATRÓN:

|   Patrón	              |  Mejor Escenario	    |   Señal
--------------------------|-------------------------|----------------
|   Hammer	              |  Lateral (Soporte)	|   Alcista
|   Engulfing Alcista	  | Transición/Ruptura	|   Alcista
|   Engulfing Bajista	  | Transición/Ruptura	|   Bajista
|   Morning Star	      | Transición (Acumulación)	|   Alcista
|   Evening Star	      | Transición (Distribución)	|   Bajista
|   3 White Soldiers	  | Tendencia Alcista	|   Alcista
|   3 Black Crows	      | Tendencia Bajista	|   Bajista
|   Marubozu	          | Tendencia/Ruptura	|   Según dirección
|   Doji	              | Baja Volatilidad	|   Neutral/Reversión

Recomendación: Usa filter_with_trend() como estrategia base y combina con estrategias específicas según el escenario detectado por tu analizador de mercado.