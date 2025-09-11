# ia/smart_order_analyzer.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from patterns.candlestickpatterns import CandlestickPatterns
from strategies import ForexStrategies, CandleStrategies


class SmartOrderAnalyzer:
    """
    Analizador inteligente que evalúa si vale la pena abrir órdenes de compra
    basándose en patrones de velas y estrategias forex.
    
    Reglas:
    - No estrategias forex repetidas
    - No múltiples estrategias en la misma vela
    - Análisis de patrones de velas para decisiones rentables
    - Análisis de estrategias forex para puntos de entrada óptimos
    """
    
    def __init__(self, df: pd.DataFrame, estrategias_fx: Dict, estrategias_candle: List):
        self.df = df.copy()
        self.estrategias_fx = estrategias_fx or {}
        self.estrategias_candle = estrategias_candle or []
        
        # Inicializar clases de análisis
        self.candlestick_patterns = CandlestickPatterns(self.df)
        self.forex_strategies = ForexStrategies(self.df)
        self.candle_strategies = CandleStrategies(self.df)
        
        # Tracking para evitar repeticiones
        self.executed_fx_strategies: Set[str] = set()
        self.last_candle_index: Optional[int] = None
        self.strategies_used_on_candle: Set[str] = set()
        
        # Cache de análisis de patrones
        self.pattern_cache: Dict[int, Dict] = {}
        
        # Configuración de filtros
        self.min_pattern_strength = 0.6  # Mínima fuerza del patrón (0-1)
        self.min_forex_confidence = 0.7  # Mínima confianza de estrategia forex
        
    def reset_tracking(self):
        """Reinicia el tracking de estrategias ejecutadas"""
        self.executed_fx_strategies.clear()
        self.last_candle_index = None
        self.strategies_used_on_candle.clear()
        self.pattern_cache.clear()
        
    def analyze_candle_for_buy_opportunity(self, candle_index, current_price: float) -> Dict:
        """
        Analiza una vela específica para determinar si es una buena oportunidad de compra.
        
        Args:
            candle_index: Puede ser int (posición) o Timestamp (índice del DataFrame)
            current_price: Precio actual
        
        Returns:
            Dict con información del análisis:
            {
                'should_buy': bool,
                'recommended_strategy': str,
                'pattern_signals': List[str],
                'forex_signals': List[str],
                'confidence_score': float,
                'reason': str
            }
        """
        # Convertir candle_index a posición numérica si es necesario
        try:
            if isinstance(candle_index, (pd.Timestamp, str)):
                # Si es Timestamp o string, encontrar la posición numérica
                numeric_index = self.df.index.get_loc(candle_index)
            else:
                # Si ya es numérico, usarlo directamente
                numeric_index = int(candle_index)
        except (KeyError, ValueError, TypeError):
            return self._create_analysis_result(False, None, [], [], 0.0, "Índice de vela inválido")
            
        # Verificar si es una nueva vela
        if numeric_index != self.last_candle_index:
            self.last_candle_index = numeric_index
            self.strategies_used_on_candle.clear()
            
        # Obtener datos de la vela actual y anteriores
        if numeric_index < 20:  # Necesitamos al menos 20 velas para análisis completo
            return self._create_analysis_result(False, None, [], [], 0.0, "Datos insuficientes para análisis")
            
        # Análizar patrones de velas
        pattern_analysis = self._analyze_candlestick_patterns(numeric_index)
        
        # Analizar estrategias forex
        forex_analysis = self._analyze_forex_strategies(numeric_index, current_price)
        
        # Analizar estrategias de velas
        candle_strategy_analysis = self._analyze_candle_strategies(numeric_index)
        
        # Combinar análisis y tomar decisión
        decision = self._make_buy_decision(pattern_analysis, forex_analysis, candle_strategy_analysis)
        
        return decision
        
    def _analyze_candlestick_patterns(self, candle_index: int) -> Dict:
        """Analiza patrones de velas japonesas en el índice dado"""
        if candle_index in self.pattern_cache:
            return self.pattern_cache[candle_index]
            
        bullish_patterns = []
        bearish_patterns = []
        pattern_strengths = {}
        
        # Lista de patrones bullish a verificar
        bullish_pattern_methods = [
            'hammer', 'inverted_hammer', 'bullish_engulfing', 'piercing_line',
            'morning_star', 'three_white_soldiers', 'tweezer_bottom',
            'three_inside_up', 'rising_three_methods'
        ]
        
        # Lista de patrones bearish a verificar
        bearish_pattern_methods = [
            'shooting_star', 'hanging_man', 'bearish_engulfing', 'dark_cloud_cover',
            'evening_star', 'three_black_crows', 'tweezer_top',
            'three_inside_down', 'falling_three_methods'
        ]
        
        # Verificar patrones bullish
        for pattern_name in bullish_pattern_methods:
            if hasattr(self.candlestick_patterns, pattern_name):
                try:
                    pattern_method = getattr(self.candlestick_patterns, pattern_name)
                    result = pattern_method(candle_index)
                    if result > 0:
                        strength = min(result / 100.0, 1.0)  # Normalizar a 0-1
                        if strength >= self.min_pattern_strength:
                            bullish_patterns.append(pattern_name)
                            pattern_strengths[pattern_name] = strength
                except Exception:
                    continue
                    
        # Verificar patrones bearish
        for pattern_name in bearish_pattern_methods:
            if hasattr(self.candlestick_patterns, pattern_name):
                try:
                    pattern_method = getattr(self.candlestick_patterns, pattern_name)
                    result = pattern_method(candle_index)
                    if result > 0:
                        strength = min(result / 100.0, 1.0)
                        if strength >= self.min_pattern_strength:
                            bearish_patterns.append(pattern_name)
                            pattern_strengths[pattern_name] = strength
                except Exception:
                    continue
        
        analysis = {
            'bullish_patterns': bullish_patterns,
            'bearish_patterns': bearish_patterns,
            'pattern_strengths': pattern_strengths,
            'net_bullish_score': len(bullish_patterns) - len(bearish_patterns),
            'max_bullish_strength': max([pattern_strengths.get(p, 0) for p in bullish_patterns], default=0),
            'max_bearish_strength': max([pattern_strengths.get(p, 0) for p in bearish_patterns], default=0)
        }
        
        self.pattern_cache[candle_index] = analysis
        return analysis
        
    def _analyze_forex_strategies(self, candle_index: int, current_price: float) -> Dict:
        """Analiza estrategias forex disponibles"""
        available_strategies = []
        strategy_signals = {}
        
        for strategy_name, params in self.estrategias_fx.items():
            # Verificar si la estrategia ya fue ejecutada
            if strategy_name in self.executed_fx_strategies:
                continue
                
            # Verificar si la estrategia ya fue usada en esta vela
            if strategy_name in self.strategies_used_on_candle:
                continue
                
            # Evaluar la estrategia
            if hasattr(self.forex_strategies, strategy_name):
                try:
                    strategy_method = getattr(self.forex_strategies, strategy_name)
                    
                    # Crear subset de datos hasta el índice actual
                    subset_df = self.df.iloc[:candle_index+1].copy()
                    
                    # Aplicar estrategia
                    result_df = strategy_method(
                        subset_df,
                        riesgo_por_operacion=params.get('riesgo', 0.01),
                        rr_ratio=params.get('rr', 2.0)
                    )
                    
                    # Verificar señal en la última fila
                    if not result_df.empty:
                        last_signal = result_df['Signal'].iloc[-1]
                        if last_signal == 1:  # Señal de compra
                            confidence = self._calculate_forex_confidence(result_df, strategy_name)
                            if confidence >= self.min_forex_confidence:
                                available_strategies.append(strategy_name)
                                strategy_signals[strategy_name] = {
                                    'signal': last_signal,
                                    'confidence': confidence,
                                    'params': params
                                }
                except Exception:
                    continue
                    
        return {
            'available_strategies': available_strategies,
            'strategy_signals': strategy_signals,
            'best_strategy': max(available_strategies, 
                               key=lambda s: strategy_signals[s]['confidence'], 
                               default=None) if available_strategies else None
        }
        
    def _analyze_candle_strategies(self, candle_index: int) -> Dict:
        """Analiza estrategias de velas disponibles"""
        available_strategies = []
        strategy_signals = {}
        
        for strategy_name in self.estrategias_candle:
            # Verificar si la estrategia ya fue usada en esta vela
            strategy_key = f"candle_{strategy_name}"
            if strategy_key in self.strategies_used_on_candle:
                continue
                
            # Evaluar la estrategia
            if hasattr(self.candle_strategies, strategy_name):
                try:
                    strategy_method = getattr(self.candle_strategies, strategy_name)
                    
                    # Crear subset de datos hasta el índice actual
                    subset_df = self.df.iloc[:candle_index+1].copy()
                    
                    # Aplicar estrategia
                    result_df = strategy_method(subset_df)
                    
                    # Verificar señal en la última fila
                    if not result_df.empty and 'ExecSignal' in result_df.columns:
                        last_signal = result_df['ExecSignal'].iloc[-1]
                        if last_signal == 1:  # Señal de compra
                            confidence = self._calculate_candle_confidence(result_df, strategy_name)
                            available_strategies.append(strategy_name)
                            strategy_signals[strategy_name] = {
                                'signal': last_signal,
                                'confidence': confidence
                            }
                except Exception:
                    continue
                    
        return {
            'available_strategies': available_strategies,
            'strategy_signals': strategy_signals,
            'best_strategy': max(available_strategies,
                               key=lambda s: strategy_signals[s]['confidence'],
                               default=None) if available_strategies else None
        }
        
    def _calculate_forex_confidence(self, result_df: pd.DataFrame, strategy_name: str) -> float:
        """Calcula la confianza de una estrategia forex"""
        try:
            # Factores para calcular confianza
            factors = []
            
            # Factor 1: Consistencia de señales recientes
            recent_signals = result_df['Signal'].tail(5)
            signal_consistency = (recent_signals == 1).sum() / len(recent_signals)
            factors.append(signal_consistency * 0.3)
            
            # Factor 2: Volatilidad (menor volatilidad = mayor confianza para compra)
            if 'ATR' in result_df.columns:
                current_atr = result_df['ATR'].iloc[-1]
                avg_atr = result_df['ATR'].tail(20).mean()
                volatility_factor = max(0, 1 - (current_atr / avg_atr - 1))
                factors.append(volatility_factor * 0.2)
            
            # Factor 3: Tendencia general (RSI si está disponible)
            if 'RSI' in result_df.columns:
                current_rsi = result_df['RSI'].iloc[-1]
                # RSI entre 30-70 es favorable para compra
                if 30 <= current_rsi <= 70:
                    rsi_factor = 1 - abs(current_rsi - 50) / 50
                    factors.append(rsi_factor * 0.2)
            
            # Factor 4: Momentum de precio
            price_momentum = (result_df['Close'].iloc[-1] / result_df['Close'].iloc[-5] - 1)
            momentum_factor = max(0, min(1, price_momentum * 10 + 0.5))
            factors.append(momentum_factor * 0.3)
            
            return min(1.0, sum(factors))
            
        except Exception:
            return 0.5  # Confianza neutral por defecto
            
    def _calculate_candle_confidence(self, result_df: pd.DataFrame, strategy_name: str) -> float:
        """Calcula la confianza de una estrategia de velas"""
        try:
            # Factores específicos para estrategias de velas
            factors = []
            
            # Factor 1: Fuerza de la señal actual
            if 'ExecSignal' in result_df.columns:
                signal_strength = abs(result_df['ExecSignal'].iloc[-1])
                factors.append(signal_strength * 0.4)
            
            # Factor 2: Posición relativa en el rango
            current_close = result_df['Close'].iloc[-1]
            recent_high = result_df['High'].tail(10).max()
            recent_low = result_df['Low'].tail(10).min()
            
            if recent_high != recent_low:
                position_factor = (current_close - recent_low) / (recent_high - recent_low)
                # Favorece posiciones no extremas
                position_factor = 1 - abs(position_factor - 0.5) * 2
                factors.append(position_factor * 0.3)
            
            # Factor 3: Volumen relativo (si está disponible)
            if 'Volume' in result_df.columns:
                current_volume = result_df['Volume'].iloc[-1]
                avg_volume = result_df['Volume'].tail(20).mean()
                volume_factor = min(1, current_volume / avg_volume)
                factors.append(volume_factor * 0.3)
            
            return min(1.0, sum(factors))
            
        except Exception:
            return 0.6  # Confianza ligeramente favorable por defecto
            
    def _make_buy_decision(self, pattern_analysis: Dict, forex_analysis: Dict, candle_analysis: Dict) -> Dict:
        """Toma la decisión final de compra basada en todos los análisis"""
        
        # Calcular score total
        total_score = 0.0
        reasons = []
        recommended_strategy = None
        strategy_type = None
        
        # Score de patrones de velas (30% del peso)
        pattern_score = 0.0
        if pattern_analysis['net_bullish_score'] > 0:
            pattern_score = pattern_analysis['max_bullish_strength'] * 0.3
            total_score += pattern_score
            reasons.append(f"Patrones bullish detectados: {pattern_analysis['bullish_patterns']}")
        elif pattern_analysis['net_bullish_score'] < 0:
            # Penalizar patrones bearish
            total_score -= pattern_analysis['max_bearish_strength'] * 0.2
            reasons.append(f"Patrones bearish detectados: {pattern_analysis['bearish_patterns']}")
            
        # Score de estrategias forex (40% del peso)
        forex_score = 0.0
        if forex_analysis['best_strategy']:
            best_fx = forex_analysis['best_strategy']
            forex_confidence = forex_analysis['strategy_signals'][best_fx]['confidence']
            forex_score = forex_confidence * 0.4
            total_score += forex_score
            recommended_strategy = best_fx
            strategy_type = 'forex'
            reasons.append(f"Estrategia forex {best_fx} con confianza {forex_confidence:.2f}")
            
        # Score de estrategias de velas (30% del peso)
        candle_score = 0.0
        if candle_analysis['best_strategy']:
            best_candle = candle_analysis['best_strategy']
            candle_confidence = candle_analysis['strategy_signals'][best_candle]['confidence']
            candle_score = candle_confidence * 0.3
            
            # Si no hay estrategia forex recomendada, usar estrategia de velas
            if not recommended_strategy or candle_confidence > forex_analysis['strategy_signals'].get(recommended_strategy, {}).get('confidence', 0):
                total_score += candle_score
                recommended_strategy = best_candle
                strategy_type = 'candle'
                reasons.append(f"Estrategia de velas {best_candle} con confianza {candle_confidence:.2f}")
            else:
                total_score += candle_score * 0.5  # Peso reducido si ya hay forex
                reasons.append(f"Estrategia de velas {best_candle} como soporte")
        
        # Decisión final
        should_buy = total_score >= 0.5 and recommended_strategy is not None
        
        if should_buy and recommended_strategy:
            # Marcar estrategia como usada
            if strategy_type == 'forex':
                self.executed_fx_strategies.add(recommended_strategy)
                self.strategies_used_on_candle.add(recommended_strategy)
            else:
                self.strategies_used_on_candle.add(f"candle_{recommended_strategy}")
        
        return self._create_analysis_result(
            should_buy=should_buy,
            recommended_strategy=recommended_strategy,
            pattern_signals=pattern_analysis['bullish_patterns'],
            forex_signals=list(forex_analysis['available_strategies']),
            confidence_score=total_score,
            reason="; ".join(reasons) if reasons else "Análisis completado",
            strategy_type=strategy_type
        )
        
    def _create_analysis_result(self, should_buy: bool, recommended_strategy: Optional[str], 
                              pattern_signals: List[str], forex_signals: List[str], 
                              confidence_score: float, reason: str, strategy_type: str = None) -> Dict:
        """Crea el resultado del análisis en formato estándar"""
        return {
            'should_buy': should_buy,
            'recommended_strategy': recommended_strategy,
            'strategy_type': strategy_type,
            'pattern_signals': pattern_signals,
            'forex_signals': forex_signals,
            'confidence_score': confidence_score,
            'reason': reason,
            'timestamp': pd.Timestamp.now()
        }
        
    def get_execution_stats(self) -> Dict:
        """Retorna estadísticas de ejecución"""
        return {
            'executed_fx_strategies': list(self.executed_fx_strategies),
            'total_fx_executed': len(self.executed_fx_strategies),
            'available_fx_strategies': list(self.estrategias_fx.keys()),
            'available_candle_strategies': self.estrategias_candle,
            'cache_size': len(self.pattern_cache)
        }
