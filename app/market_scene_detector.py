# app/scene_detector.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum

class MarketScenario(Enum):
    """Enumeración de los escenarios del mercado"""
    UPTREND = "Tendencia alcista"
    DOWNTREND = "Tendencia bajista"
    RANGING = "Mercado lateral/rango"
    ACCUMULATION = "Fase de acumulación"
    DISTRIBUTION = "Fase de distribución"
    BREAKOUT = "Ruptura de alta volatilidad"
    LOW_VOLATILITY = "Baja volatilidad/contracción"
    FAKE_BREAKOUT = "Falsa ruptura"
    UNCLEAR = "Escenario no claro"

class ForexMarketAnalyzer:
    """
    Clase para detectar los principales escenarios del mercado Forex
    basados en el análisis de precios y patrones.
    """
    
    def __init__(self, window_size: int = 20, atr_period: int = 14, 
                 volatility_threshold: float = 0.005, trend_strength: float = 0.3):
        """
        Inicializa el analizador de mercado.
        
        Args:
            window_size: Tamaño de ventana para análisis de tendencia
            atr_period: Período para el cálculo de ATR (Average True Range)
            volatility_threshold: Umbral para determinar alta/baja volatilidad
            trend_strength: Fuerza mínima requerida para considerar tendencia
        """
        self.window_size = window_size
        self.atr_period = atr_period
        self.volatility_threshold = volatility_threshold
        self.trend_strength = trend_strength
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos necesarios para el análisis SIN TA-Lib.
        
        Args:
            df: DataFrame con columnas 'high', 'low', 'close'
            
        Returns:
            DataFrame con indicadores añadidos
        """
        df = df.copy()
        
        # ATR para volatilidad (cálculo manual)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=self.atr_period).mean()
        
        # Medias móviles para tendencia
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI para momentum (cálculo manual)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bandas de Bollinger para rangos (cálculo manual)
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Cálculo de máximos y mínimos locales
        df['local_max'] = (df['high'] == df['high'].rolling(window=5, center=True).max())
        df['local_min'] = (df['low'] == df['low'].rolling(window=5, center=True).min())
        
        # Limpiar valores NaN
        df = df.fillna(method='bfill').fillna(method='ffill')
        
        return df
    
    def detect_trend(self, df: pd.DataFrame) -> Tuple[MarketScenario, float]:
        """
        Detecta si el mercado está en tendencia alcista o bajista.
        """
        recent_data = df.tail(self.window_size)
        
        # Análisis de máximos y mínimos
        highs = recent_data['high'].values
        lows = recent_data['low'].values
        
        # Detectar secuencia de máximos y mínimos
        max_increasing = len(highs) > 1 and all(highs[i] > highs[i-1] for i in range(1, len(highs)))
        min_increasing = len(lows) > 1 and all(lows[i] > lows[i-1] for i in range(1, len(lows)))
        max_decreasing = len(highs) > 1 and all(highs[i] < highs[i-1] for i in range(1, len(highs)))
        min_decreasing = len(lows) > 1 and all(lows[i] < lows[i-1] for i in range(1, len(lows)))
        
        # Fuerza de tendencia basada en pendiente de medias móviles
        sma_20_slope = (recent_data['sma_20'].iloc[-1] - recent_data['sma_20'].iloc[0]) / recent_data['sma_20'].iloc[0] if recent_data['sma_20'].iloc[0] != 0 else 0
        trend_strength = abs(sma_20_slope)
        
        if max_increasing and min_increasing and trend_strength > self.trend_strength:
            return MarketScenario.UPTREND, trend_strength
        elif max_decreasing and min_decreasing and trend_strength > self.trend_strength:
            return MarketScenario.DOWNTREND, trend_strength
        
        return MarketScenario.UNCLEAR, trend_strength
    
    def detect_ranging_market(self, df: pd.DataFrame) -> Tuple[MarketScenario, float]:
        """
        Detecta si el mercado está en fase lateral/rango.
        """
        recent_data = df.tail(self.window_size)
        
        # Calcular volatilidad relativa
        price_range = recent_data['high'].max() - recent_data['low'].min()
        avg_price = recent_data['close'].mean()
        volatility = price_range / avg_price if avg_price != 0 else 0
        
        # Porcentaje de tiempo dentro de las bandas de Bollinger
        in_bb_percentage = ((recent_data['close'] >= recent_data['bb_lower']) & 
                           (recent_data['close'] <= recent_data['bb_upper'])).mean()
        
        if volatility < self.volatility_threshold and in_bb_percentage > 0.8:
            return MarketScenario.RANGING, 1 - volatility
        
        return MarketScenario.UNCLEAR, volatility
    
    def detect_accumulation_distribution(self, df: pd.DataFrame) -> MarketScenario:
        """
        Detecta fases de acumulación o distribución.
        """
        recent_data = df.tail(30)
        
        # Análisis de precio
        price_change = recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]
        volatility = recent_data['atr'].mean() / recent_data['close'].mean() if recent_data['close'].mean() != 0 else 0
        
        # Patrones típicos de acumulación/distribución
        if (abs(price_change) < volatility * 2 and 
            self.detect_ranging_market(df)[0] == MarketScenario.RANGING):
            
            # Análisis de RSI
            avg_rsi = recent_data['rsi'].mean()
            
            if avg_rsi > 55:
                return MarketScenario.DISTRIBUTION
            elif avg_rsi < 45:
                return MarketScenario.ACCUMULATION
        
        return MarketScenario.UNCLEAR
    
    def detect_breakout(self, df: pd.DataFrame, support: float, resistance: float) -> MarketScenario:
        """
        Detecta rupturas de soportes/resistencias.
        """
        recent_data = df.tail(10)
        current_close = recent_data['close'].iloc[-1]
        current_high = recent_data['high'].iloc[-1]
        current_low = recent_data['low'].iloc[-1]
        
        # Volatilidad actual
        current_volatility = recent_data['atr'].iloc[-1] / recent_data['close'].iloc[-1] if recent_data['close'].iloc[-1] != 0 else 0
        
        # Detectar rupturas
        if current_high > resistance and current_volatility > self.volatility_threshold * 2:
            return MarketScenario.BREAKOUT
        elif current_low < support and current_volatility > self.volatility_threshold * 2:
            return MarketScenario.BREAKOUT
        
        return MarketScenario.UNCLEAR
    
    def detect_low_volatility(self, df: pd.DataFrame) -> Tuple[MarketScenario, float]:
        """
        Detecta periodos de baja volatilidad.
        """
        recent_data = df.tail(self.window_size)
        
        # Calcular volatilidad promedio
        avg_volatility = recent_data['atr'].mean() / recent_data['close'].mean() if recent_data['close'].mean() != 0 else 0
        
        if avg_volatility < self.volatility_threshold / 2:
            return MarketScenario.LOW_VOLATILITY, avg_volatility
        
        return MarketScenario.UNCLEAR, avg_volatility
    
    def detect_fake_breakout(self, df: pd.DataFrame, support: float, resistance: float) -> MarketScenario:
        """
        Detecta falsas rupturas.
        """
        recent_data = df.tail(15)
        
        for i in range(5, len(recent_data)):
            if i >= len(recent_data):
                continue
                
            window = recent_data.iloc[i-5:i]
            current_candle = recent_data.iloc[i]
            
            # Ruptura previa seguida de reversión
            if (window['high'].max() > resistance and 
                current_candle['close'] < resistance and
                abs(current_candle['close'] - resistance) / resistance > 0.001):
                return MarketScenario.FAKE_BREAKOUT
            
            if (window['low'].min() < support and 
                current_candle['close'] > support and
                abs(current_candle['close'] - support) / support > 0.001):
                return MarketScenario.FAKE_BREAKOUT
        
        return MarketScenario.UNCLEAR
    
    def analyze_market(self, df: pd.DataFrame, 
                      support: Optional[float] = None, 
                      resistance: Optional[float] = None) -> Dict:
        """
        Analiza el mercado y detecta todos los escenarios posibles.
        """
        # Calcular indicadores
        df_with_indicators = self.calculate_indicators(df)
        
        # Detectar escenarios
        trend_scenario, trend_strength = self.detect_trend(df_with_indicators)
        ranging_scenario, range_strength = self.detect_ranging_market(df_with_indicators)
        acc_dist_scenario = self.detect_accumulation_distribution(df_with_indicators)
        low_vol_scenario, volatility = self.detect_low_volatility(df_with_indicators)
        
        # Detectar rupturas y falsas rupturas si se proporcionan niveles
        breakout_scenario = MarketScenario.UNCLEAR
        fakeout_scenario = MarketScenario.UNCLEAR
        
        if support is not None and resistance is not None:
            breakout_scenario = self.detect_breakout(df_with_indicators, support, resistance)
            fakeout_scenario = self.detect_fake_breakout(df_with_indicators, support, resistance)
        
        # Determinar escenario principal
        primary_scenario = self._determine_primary_scenario(
            trend_scenario, ranging_scenario, acc_dist_scenario,
            breakout_scenario, low_vol_scenario, fakeout_scenario,
            trend_strength, range_strength
        )
        
        return {
            'primary_scenario': primary_scenario,
            'trend': trend_scenario,
            'trend_strength': trend_strength,
            'ranging': ranging_scenario,
            'range_strength': range_strength,
            'accumulation_distribution': acc_dist_scenario,
            'breakout': breakout_scenario,
            'low_volatility': low_vol_scenario,
            'volatility_level': volatility,
            'fake_breakout': fakeout_scenario,
            'indicators': df_with_indicators.iloc[-1:].to_dict('records')[0] if len(df_with_indicators) > 0 else {}
        }
    
    def _determine_primary_scenario(self, *scenarios) -> MarketScenario:
        """
        Determina el escenario principal basado en la prioridad y fuerza.
        """
        priority_order = [
            MarketScenario.BREAKOUT,
            MarketScenario.UPTREND,
            MarketScenario.DOWNTREND,
            MarketScenario.FAKE_BREAKOUT,
            MarketScenario.RANGING,
            MarketScenario.ACCUMULATION,
            MarketScenario.DISTRIBUTION,
            MarketScenario.LOW_VOLATILITY
        ]
        
        for scenario in priority_order:
            if scenario in scenarios:
                return scenario
        
        return MarketScenario.UNCLEAR

