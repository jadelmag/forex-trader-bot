# app/market_scene_detector.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum

class MarketScenario(Enum):
    """Enumeración de los escenarios del mercado - SIMPLIFICADO A 3 TIPOS"""
    UPTREND = "Mercado ascendente"      # Tendencia alcista clara
    DOWNTREND = "Mercado descendente"   # Tendencia bajista clara
    LATERAL = "Mercado lateral"          # Mercado en rango o lateral

class ForexMarketAnalyzer:
    """
    Clase para detectar los principales escenarios del mercado Forex
    basados en el análisis de precios y patrones.
    SIMPLIFICADO para detectar solo 3 tipos de mercado.
    """
    
    def __init__(self, window_size: int = 5, atr_period: int = 14, 
                 volatility_threshold: float = 0.002, trend_strength: float = 0.001,
                 quick_detection: bool = True):
        """
        Inicializa el analizador de mercado.
        
        Args:
            window_size: Tamaño de ventana para análisis de tendencia (5 para detección rápida)
            atr_period: Período para el cálculo de ATR (Average True Range)
            volatility_threshold: Umbral para determinar alta/baja volatilidad (0.2% más realista para forex)
            trend_strength: Fuerza mínima requerida para considerar tendencia (0.1% es más realista para forex)
            quick_detection: Si True, permite detección con menos velas (mínimo 3)
        """
        self.window_size = window_size
        self.atr_period = atr_period
        self.volatility_threshold = volatility_threshold
        self.trend_strength = trend_strength
        self.quick_detection = quick_detection
        
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
    
    def detect_market_type(self, df: pd.DataFrame) -> Tuple[MarketScenario, float]:
        """
        Detecta el tipo de mercado: ascendente, descendente o lateral.
        MÉTODO PRINCIPAL SIMPLIFICADO.
        
        Returns:
            Tuple con (tipo_de_mercado, fuerza_de_la_señal)
        """
        recent_data = df.tail(self.window_size)
        
        if len(recent_data) < 3:
            return MarketScenario.LATERAL, 0.0
        
        # Calcular cambio porcentual total
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        
        # Análisis de máximos y mínimos
        highs = recent_data['high'].values
        lows = recent_data['low'].values
        
        # Contar tendencia de máximos y mínimos
        highs_increasing = 0
        lows_increasing = 0
        
        for i in range(1, len(highs)):
            if highs[i] > highs[i-1]:
                highs_increasing += 1
            if lows[i] > lows[i-1]:
                lows_increasing += 1
        
        # Porcentaje de velas con máximos/mínimos crecientes
        pct_highs_up = highs_increasing / (len(highs) - 1) if len(highs) > 1 else 0
        pct_lows_up = lows_increasing / (len(lows) - 1) if len(lows) > 1 else 0
        
        # Análisis de medias móviles
        sma_20_current = recent_data['sma_20'].iloc[-1] if 'sma_20' in recent_data.columns else recent_data['close'].iloc[-1]
        sma_50_current = recent_data['sma_50'].iloc[-1] if 'sma_50' in recent_data.columns else recent_data['close'].iloc[-1]
        price_above_sma = recent_data['close'].iloc[-1] > sma_20_current
        
        # Fuerza de tendencia basada en cambio de precio
        trend_strength = abs(price_change)
        
        # CRITERIOS SIMPLIFICADOS PARA 3 TIPOS DE MERCADO:
        
        # 1. MERCADO ASCENDENTE
        if (price_change > self.trend_strength and 
            (pct_highs_up > 0.5 or pct_lows_up > 0.5) and 
            price_above_sma):
            return MarketScenario.UPTREND, trend_strength
        
        # 2. MERCADO DESCENDENTE
        elif (price_change < -self.trend_strength and 
              (pct_highs_up < 0.5 or pct_lows_up < 0.5) and 
              not price_above_sma):
            return MarketScenario.DOWNTREND, trend_strength
        
        # 3. MERCADO LATERAL (por defecto si no hay tendencia clara)
        else:
            # Calcular rango para determinar la fuerza del mercado lateral
            price_range = recent_data['high'].max() - recent_data['low'].min()
            avg_price = recent_data['close'].mean()
            range_strength = 1.0 - (price_range / avg_price) if avg_price != 0 else 0.5
            return MarketScenario.LATERAL, range_strength
    
    def analyze_market(self, df: pd.DataFrame, 
                      support: Optional[float] = None, 
                      resistance: Optional[float] = None) -> Dict:
        """
        Analiza el mercado y detecta el tipo de mercado (simplificado a 3 tipos).
        
        Returns:
            Diccionario con el análisis del mercado
        """
        # Calcular indicadores
        df_with_indicators = self.calculate_indicators(df)
        
        # Detectar tipo de mercado (método simplificado)
        market_type, market_strength = self.detect_market_type(df_with_indicators)
        
        # Análisis adicional de volatilidad
        recent_data = df_with_indicators.tail(self.window_size)
        volatility = recent_data['atr'].mean() / recent_data['close'].mean() if recent_data['close'].mean() != 0 else 0
        
        # RSI para confirmar condiciones
        current_rsi = recent_data['rsi'].iloc[-1] if 'rsi' in recent_data.columns else 50
        
        # Resultado simplificado
        return {
            'primary_scenario': market_type,
            'market_type': market_type.value,
            'market_strength': market_strength,
            'volatility': volatility,
            'current_rsi': current_rsi,
            'indicators': df_with_indicators.iloc[-1:].to_dict('records')[0] if len(df_with_indicators) > 0 else {},
            # Mantener compatibilidad con código existente
            'trend': market_type if market_type != MarketScenario.LATERAL else MarketScenario.LATERAL,
            'trend_strength': market_strength if market_type != MarketScenario.LATERAL else 0.0,
            'ranging': MarketScenario.LATERAL if market_type == MarketScenario.LATERAL else None,
            'range_strength': market_strength if market_type == MarketScenario.LATERAL else 0.0,
        }
    
    # Métodos de compatibilidad (mantener por si otros módulos los usan)
    def detect_trend(self, df: pd.DataFrame) -> Tuple[MarketScenario, float]:
        """Método de compatibilidad - redirige a detect_market_type"""
        market_type, strength = self.detect_market_type(df)
        if market_type == MarketScenario.LATERAL:
            return MarketScenario.LATERAL, 0.0
        return market_type, strength
    
    def detect_ranging_market(self, df: pd.DataFrame) -> Tuple[MarketScenario, float]:
        """Método de compatibilidad - detecta solo mercado lateral"""
        market_type, strength = self.detect_market_type(df)
        if market_type == MarketScenario.LATERAL:
            return MarketScenario.LATERAL, strength
        return None, 0.0
    
    def detect_accumulation_distribution(self, df: pd.DataFrame) -> MarketScenario:
        """Método de compatibilidad - simplificado"""
        market_type, _ = self.detect_market_type(df)
        return market_type
    
    def detect_breakout(self, df: pd.DataFrame, support: float, resistance: float) -> MarketScenario:
        """Método de compatibilidad - simplificado"""
        market_type, _ = self.detect_market_type(df)
        # Un breakout sería un cambio de lateral a tendencia
        return market_type if market_type != MarketScenario.LATERAL else MarketScenario.LATERAL
    
    def detect_low_volatility(self, df: pd.DataFrame) -> Tuple[MarketScenario, float]:
        """Método de compatibilidad - simplificado"""
        # Baja volatilidad normalmente implica mercado lateral
        return self.detect_market_type(df)
    
    def detect_fake_breakout(self, df: pd.DataFrame, support: float, resistance: float) -> MarketScenario:
        """Método de compatibilidad - simplificado"""
        # Fake breakout sería volver a lateral después de intentar tendencia
        return MarketScenario.LATERAL
    
    def _determine_primary_scenario(self, *args, **kwargs) -> MarketScenario:
        """Método de compatibilidad - simplificado"""
        # Solo retorna uno de los 3 tipos de mercado
        for arg in args:
            if isinstance(arg, MarketScenario) and arg in [MarketScenario.UPTREND, MarketScenario.DOWNTREND, MarketScenario.LATERAL]:
                return arg
        return MarketScenario.LATERAL
