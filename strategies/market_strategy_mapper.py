# strategies/market_strategy_mapper.py

from enum import Enum
from typing import Dict, List, Tuple
from app.market_scene_detector import MarketScenario

class StrategyPriority(Enum):
    """Niveles de prioridad para estrategias"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    DISABLED = 4

class MarketStrategyMapper:
    """
    Mapea estrategias de velas según el escenario de mercado detectado.
    Proporciona priorización y filtrado de estrategias basado en condiciones de mercado.
    """
    
    def __init__(self):
        """Inicializa el mapeador con las configuraciones de estrategias por escenario."""
        self.strategy_mappings = self._initialize_strategy_mappings()
    
    def _initialize_strategy_mappings(self) -> Dict[MarketScenario, Dict[str, StrategyPriority]]:
        """
        Inicializa el mapeo completo de estrategias por escenario de mercado.
        
        Returns:
            Diccionario con escenarios como claves y estrategias con prioridades como valores
        """
        return {
            # 1. MERCADO TENDENCIAL ALCISTA
            MarketScenario.UPTREND: {
                # Alta prioridad - continuación alcista
                'three_white_soldiers_strategy': StrategyPriority.HIGH,
                'bullish_engulfing_strategy': StrategyPriority.HIGH,
                'piercing_line_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - patrones de apoyo
                'hammer_reversal_strategy': StrategyPriority.MEDIUM,
                'morning_star_strategy': StrategyPriority.MEDIUM,
                'inverted_hammer_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - neutrales
                'doji_reversal_strategy': StrategyPriority.LOW,
                'spinning_top_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - contrarias a tendencia
                'three_black_crows_strategy': StrategyPriority.DISABLED,
                'bearish_engulfing_strategy': StrategyPriority.DISABLED,
                'dark_cloud_cover_strategy': StrategyPriority.DISABLED,
                'hanging_man_strategy': StrategyPriority.DISABLED,
                'shooting_star_strategy': StrategyPriority.DISABLED,
                'evening_star_strategy': StrategyPriority.DISABLED,
                'tweezer_top_strategy': StrategyPriority.DISABLED,
            },
            
            # 2. MERCADO TENDENCIAL BAJISTA
            MarketScenario.DOWNTREND: {
                # Alta prioridad - continuación bajista
                'three_black_crows_strategy': StrategyPriority.HIGH,
                'bearish_engulfing_strategy': StrategyPriority.HIGH,
                'dark_cloud_cover_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - patrones de apoyo
                'hanging_man_strategy': StrategyPriority.MEDIUM,
                'shooting_star_strategy': StrategyPriority.MEDIUM,
                'evening_star_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - neutrales
                'doji_reversal_strategy': StrategyPriority.LOW,
                'spinning_top_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - contrarias a tendencia
                'three_white_soldiers_strategy': StrategyPriority.DISABLED,
                'bullish_engulfing_strategy': StrategyPriority.DISABLED,
                'piercing_line_strategy': StrategyPriority.DISABLED,
                'hammer_reversal_strategy': StrategyPriority.DISABLED,
                'morning_star_strategy': StrategyPriority.DISABLED,
                'inverted_hammer_strategy': StrategyPriority.DISABLED,
                'tweezer_bottom_strategy': StrategyPriority.DISABLED,
            },
            
            # 3. MERCADO LATERAL (RANGO)
            MarketScenario.RANGING: {
                # Alta prioridad - reversión en soporte/resistencia
                'hammer_reversal_strategy': StrategyPriority.HIGH,
                'tweezer_bottom_strategy': StrategyPriority.HIGH,
                'bullish_engulfing_strategy': StrategyPriority.HIGH,
                'hanging_man_strategy': StrategyPriority.HIGH,
                'shooting_star_strategy': StrategyPriority.HIGH,
                'tweezer_top_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - patrones de reversión
                'bearish_engulfing_strategy': StrategyPriority.MEDIUM,
                'piercing_line_strategy': StrategyPriority.MEDIUM,
                'dark_cloud_cover_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - indecisión
                'doji_reversal_strategy': StrategyPriority.LOW,
                'spinning_top_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - patrones de continuación
                'three_white_soldiers_strategy': StrategyPriority.DISABLED,
                'three_black_crows_strategy': StrategyPriority.DISABLED,
            },
            
            # 4. FASE DE ACUMULACIÓN (fondo)
            MarketScenario.ACCUMULATION: {
                # Alta prioridad - reversión alcista fuerte
                'morning_star_strategy': StrategyPriority.HIGH,
                'hammer_reversal_strategy': StrategyPriority.HIGH,
                'bullish_engulfing_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - patrones de apoyo
                'piercing_line_strategy': StrategyPriority.MEDIUM,
                'tweezer_bottom_strategy': StrategyPriority.MEDIUM,
                'inverted_hammer_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - indecisión
                'doji_reversal_strategy': StrategyPriority.LOW,
                'spinning_top_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - bajistas
                'evening_star_strategy': StrategyPriority.DISABLED,
                'hanging_man_strategy': StrategyPriority.DISABLED,
                'bearish_engulfing_strategy': StrategyPriority.DISABLED,
                'three_black_crows_strategy': StrategyPriority.DISABLED,
                'shooting_star_strategy': StrategyPriority.DISABLED,
                'dark_cloud_cover_strategy': StrategyPriority.DISABLED,
                'tweezer_top_strategy': StrategyPriority.DISABLED,
            },
            
            # 5. FASE DE DISTRIBUCIÓN (techo)
            MarketScenario.DISTRIBUTION: {
                # Alta prioridad - reversión bajista fuerte
                'evening_star_strategy': StrategyPriority.HIGH,
                'hanging_man_strategy': StrategyPriority.HIGH,
                'bearish_engulfing_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - patrones de apoyo
                'dark_cloud_cover_strategy': StrategyPriority.MEDIUM,
                'tweezer_top_strategy': StrategyPriority.MEDIUM,
                'shooting_star_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - indecisión
                'doji_reversal_strategy': StrategyPriority.LOW,
                'spinning_top_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - alcistas
                'morning_star_strategy': StrategyPriority.DISABLED,
                'hammer_reversal_strategy': StrategyPriority.DISABLED,
                'bullish_engulfing_strategy': StrategyPriority.DISABLED,
                'three_white_soldiers_strategy': StrategyPriority.DISABLED,
                'piercing_line_strategy': StrategyPriority.DISABLED,
                'inverted_hammer_strategy': StrategyPriority.DISABLED,
                'tweezer_bottom_strategy': StrategyPriority.DISABLED,
            },
            
            # 6. ALTA VOLATILIDAD (RUPTURA)
            MarketScenario.BREAKOUT: {
                # Alta prioridad - impulso fuerte
                'marubozu_strategy': StrategyPriority.HIGH,  # Si existe
                'bullish_engulfing_strategy': StrategyPriority.HIGH,
                'bearish_engulfing_strategy': StrategyPriority.HIGH,
                'three_white_soldiers_strategy': StrategyPriority.HIGH,
                'three_black_crows_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - confirmación
                'hammer_reversal_strategy': StrategyPriority.MEDIUM,
                'hanging_man_strategy': StrategyPriority.MEDIUM,
                'piercing_line_strategy': StrategyPriority.MEDIUM,
                'dark_cloud_cover_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - otros
                'morning_star_strategy': StrategyPriority.LOW,
                'evening_star_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - indecisión
                'doji_reversal_strategy': StrategyPriority.DISABLED,
                'spinning_top_strategy': StrategyPriority.DISABLED,
            },
            
            # 7. BAJA VOLATILIDAD (CONTRACCIÓN)
            MarketScenario.LOW_VOLATILITY: {
                # Alta prioridad - indecisión
                'doji_reversal_strategy': StrategyPriority.HIGH,
                'spinning_top_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - patrones sutiles
                'tweezer_top_strategy': StrategyPriority.MEDIUM,
                'tweezer_bottom_strategy': StrategyPriority.MEDIUM,
                'inverted_hammer_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - otros patrones
                'hammer_reversal_strategy': StrategyPriority.LOW,
                'hanging_man_strategy': StrategyPriority.LOW,
                'bullish_engulfing_strategy': StrategyPriority.LOW,
                'bearish_engulfing_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - patrones de impulso
                'three_white_soldiers_strategy': StrategyPriority.DISABLED,
                'three_black_crows_strategy': StrategyPriority.DISABLED,
                'morning_star_strategy': StrategyPriority.DISABLED,
                'evening_star_strategy': StrategyPriority.DISABLED,
            },
            
            # 8. FALSAS RUPTURAS (FAKEOUTS)
            MarketScenario.FAKE_BREAKOUT: {
                # Alta prioridad - reversión tras fakeout
                'inverted_hammer_strategy': StrategyPriority.HIGH,
                'shooting_star_strategy': StrategyPriority.HIGH,
                'bullish_engulfing_strategy': StrategyPriority.HIGH,
                'bearish_engulfing_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - patrones de reversión
                'hammer_reversal_strategy': StrategyPriority.MEDIUM,
                'hanging_man_strategy': StrategyPriority.MEDIUM,
                'tweezer_top_strategy': StrategyPriority.MEDIUM,
                'tweezer_bottom_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - otros
                'piercing_line_strategy': StrategyPriority.LOW,
                'dark_cloud_cover_strategy': StrategyPriority.LOW,
                'doji_reversal_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - continuación
                'three_white_soldiers_strategy': StrategyPriority.DISABLED,
                'three_black_crows_strategy': StrategyPriority.DISABLED,
            },
            
            # 9. ESCENARIO NO CLARO
            MarketScenario.UNCLEAR: {
                # Todas las estrategias con prioridad media para análisis completo
                'hammer_reversal_strategy': StrategyPriority.MEDIUM,
                'bullish_engulfing_strategy': StrategyPriority.MEDIUM,
                'bearish_engulfing_strategy': StrategyPriority.MEDIUM,
                'morning_star_strategy': StrategyPriority.MEDIUM,
                'evening_star_strategy': StrategyPriority.MEDIUM,
                'hanging_man_strategy': StrategyPriority.MEDIUM,
                'three_white_soldiers_strategy': StrategyPriority.MEDIUM,
                'three_black_crows_strategy': StrategyPriority.MEDIUM,
                'doji_reversal_strategy': StrategyPriority.MEDIUM,
                'shooting_star_strategy': StrategyPriority.MEDIUM,
                'spinning_top_strategy': StrategyPriority.MEDIUM,
                'inverted_hammer_strategy': StrategyPriority.MEDIUM,
                'piercing_line_strategy': StrategyPriority.MEDIUM,
                'dark_cloud_cover_strategy': StrategyPriority.MEDIUM,
                'tweezer_top_strategy': StrategyPriority.MEDIUM,
                'tweezer_bottom_strategy': StrategyPriority.MEDIUM,
            }
        }
    
    def get_prioritized_strategies(self, scenario: MarketScenario, 
                                 available_strategies: List[str] = None) -> Dict[str, StrategyPriority]:
        """
        Obtiene las estrategias priorizadas para un escenario específico.
        
        Args:
            scenario: Escenario de mercado detectado
            available_strategies: Lista de estrategias disponibles (opcional)
            
        Returns:
            Diccionario con estrategias y sus prioridades
        """
        if scenario not in self.strategy_mappings:
            scenario = MarketScenario.UNCLEAR
        
        scenario_strategies = self.strategy_mappings[scenario]
        
        if available_strategies:
            # Filtrar solo las estrategias disponibles
            filtered_strategies = {
                strategy: priority 
                for strategy, priority in scenario_strategies.items()
                if strategy in available_strategies
            }
            return filtered_strategies
        
        return scenario_strategies.copy()
    
    def filter_strategies_by_priority(self, strategies: Dict[str, StrategyPriority], 
                                    min_priority: StrategyPriority = StrategyPriority.MEDIUM) -> List[str]:
        """
        Filtra estrategias por nivel mínimo de prioridad.
        
        Args:
            strategies: Diccionario de estrategias con prioridades
            min_priority: Prioridad mínima requerida
            
        Returns:
            Lista de nombres de estrategias que cumplen el criterio
        """
        return [
            strategy for strategy, priority in strategies.items()
            if priority.value <= min_priority.value
        ]
    
    def get_strategy_recommendations(self, scenario: MarketScenario, 
                                   available_strategies: List[str] = None,
                                   max_strategies: int = None) -> Tuple[List[str], List[str], List[str]]:
        """
        Obtiene recomendaciones de estrategias categorizadas por prioridad.
        
        Args:
            scenario: Escenario de mercado
            available_strategies: Estrategias disponibles
            max_strategies: Número máximo de estrategias por categoría
            
        Returns:
            Tupla con (high_priority, medium_priority, low_priority) listas de estrategias
        """
        prioritized = self.get_prioritized_strategies(scenario, available_strategies)
        
        high_priority = self.filter_strategies_by_priority(prioritized, StrategyPriority.HIGH)
        medium_priority = [s for s, p in prioritized.items() if p == StrategyPriority.MEDIUM]
        low_priority = [s for s, p in prioritized.items() if p == StrategyPriority.LOW]
        
        if max_strategies:
            high_priority = high_priority[:max_strategies]
            medium_priority = medium_priority[:max_strategies]
            low_priority = low_priority[:max_strategies]
        
        return high_priority, medium_priority, low_priority
    
    def get_scenario_description(self, scenario: MarketScenario) -> str:
        """
        Obtiene una descripción del escenario de mercado.
        
        Args:
            scenario: Escenario de mercado
            
        Returns:
            Descripción textual del escenario
        """
        descriptions = {
            MarketScenario.UPTREND: "Mercado en tendencia alcista - Priorizar patrones de continuación alcista",
            MarketScenario.DOWNTREND: "Mercado en tendencia bajista - Priorizar patrones de continuación bajista", 
            MarketScenario.RANGING: "Mercado lateral - Priorizar patrones de reversión en soportes/resistencias",
            MarketScenario.ACCUMULATION: "Fase de acumulación - Priorizar patrones de reversión alcista",
            MarketScenario.DISTRIBUTION: "Fase de distribución - Priorizar patrones de reversión bajista",
            MarketScenario.BREAKOUT: "Ruptura de alta volatilidad - Priorizar patrones de impulso",
            MarketScenario.LOW_VOLATILITY: "Baja volatilidad - Priorizar patrones de indecisión",
            MarketScenario.FAKE_BREAKOUT: "Falsa ruptura - Priorizar patrones de reversión",
            MarketScenario.UNCLEAR: "Escenario no claro - Usar todas las estrategias disponibles"
        }
        return descriptions.get(scenario, "Escenario desconocido")

    def should_execute_strategy(self, strategy_name: str, scenario: MarketScenario, 
                              signal_type: int) -> Tuple[bool, str]:
        """
        Determina si una estrategia debe ejecutarse según el escenario de mercado y tipo de señal.
        
        Args:
            strategy_name: Nombre de la estrategia
            scenario: Escenario de mercado actual
            signal_type: Tipo de señal (1=BUY, -1=SELL, 0=NEUTRAL)
            
        Returns:
            Tupla (should_execute: bool, reason: str)
        """
        if scenario not in self.strategy_mappings:
            scenario = MarketScenario.UNCLEAR
        
        scenario_strategies = self.strategy_mappings[scenario]
        strategy_priority = scenario_strategies.get(strategy_name, StrategyPriority.DISABLED)
        
        # Si la estrategia está deshabilitada para este escenario, no ejecutar
        if strategy_priority == StrategyPriority.DISABLED:
            return False, f"Estrategia deshabilitada para escenario {scenario.value}"
        
        # Lógica específica por escenario y tipo de señal
        execution_rules = self._get_execution_rules(scenario, strategy_name, signal_type)
        should_execute = execution_rules['execute']
        reason = execution_rules['reason']
        
        return should_execute, reason
    
    def _get_execution_rules(self, scenario: MarketScenario, strategy_name: str, 
                           signal_type: int) -> Dict[str, any]:
        """
        Obtiene las reglas de ejecución específicas por escenario.
        
        Args:
            scenario: Escenario de mercado
            strategy_name: Nombre de la estrategia
            signal_type: Tipo de señal (1=BUY, -1=SELL)
            
        Returns:
            Diccionario con 'execute' (bool) y 'reason' (str)
        """
        # Reglas por escenario
        rules = {
            MarketScenario.UPTREND: {
                'preferred_signal': 1,  # Preferir BUY
                'allowed_strategies_buy': [
                    'three_white_soldiers_strategy', 'bullish_engulfing_strategy', 
                    'piercing_line_strategy', 'hammer_reversal_strategy', 
                    'morning_star_strategy', 'inverted_hammer_strategy'
                ],
                'allowed_strategies_sell': [],  # No SELL en tendencia alcista
                'reason_buy': "Tendencia alcista - priorizar operaciones de compra",
                'reason_sell_blocked': "Tendencia alcista - operaciones de venta bloqueadas"
            },
            
            MarketScenario.DOWNTREND: {
                'preferred_signal': -1,  # Preferir SELL
                'allowed_strategies_buy': [],  # No BUY en tendencia bajista
                'allowed_strategies_sell': [
                    'three_black_crows_strategy', 'bearish_engulfing_strategy',
                    'dark_cloud_cover_strategy', 'hanging_man_strategy',
                    'shooting_star_strategy', 'evening_star_strategy'
                ],
                'reason_buy_blocked': "Tendencia bajista - operaciones de compra bloqueadas",
                'reason_sell': "Tendencia bajista - priorizar operaciones de venta"
            },
            
            MarketScenario.RANGING: {
                'preferred_signal': 0,  # Ambos permitidos
                'allowed_strategies_buy': [
                    'hammer_reversal_strategy', 'tweezer_bottom_strategy', 
                    'bullish_engulfing_strategy', 'piercing_line_strategy'
                ],
                'allowed_strategies_sell': [
                    'hanging_man_strategy', 'shooting_star_strategy',
                    'tweezer_top_strategy', 'bearish_engulfing_strategy', 
                    'dark_cloud_cover_strategy'
                ],
                'reason_buy': "Mercado lateral - compra en soporte",
                'reason_sell': "Mercado lateral - venta en resistencia"
            },
            
            MarketScenario.ACCUMULATION: {
                'preferred_signal': 1,  # Preferir BUY
                'allowed_strategies_buy': [
                    'morning_star_strategy', 'hammer_reversal_strategy',
                    'bullish_engulfing_strategy', 'piercing_line_strategy',
                    'tweezer_bottom_strategy', 'inverted_hammer_strategy'
                ],
                'allowed_strategies_sell': [],  # Evitar SELL en acumulación
                'reason_buy': "Fase de acumulación - priorizar compras en fondo",
                'reason_sell_blocked': "Fase de acumulación - evitar ventas"
            },
            
            MarketScenario.DISTRIBUTION: {
                'preferred_signal': -1,  # Preferir SELL
                'allowed_strategies_buy': [],  # Evitar BUY en distribución
                'allowed_strategies_sell': [
                    'evening_star_strategy', 'hanging_man_strategy',
                    'bearish_engulfing_strategy', 'dark_cloud_cover_strategy',
                    'tweezer_top_strategy', 'shooting_star_strategy'
                ],
                'reason_buy_blocked': "Fase de distribución - evitar compras",
                'reason_sell': "Fase de distribución - priorizar ventas en techo"
            },
            
            MarketScenario.BREAKOUT: {
                'preferred_signal': 0,  # Ambos permitidos según dirección
                'allowed_strategies_buy': [
                    'bullish_engulfing_strategy', 'three_white_soldiers_strategy',
                    'hammer_reversal_strategy', 'piercing_line_strategy'
                ],
                'allowed_strategies_sell': [
                    'bearish_engulfing_strategy', 'three_black_crows_strategy',
                    'hanging_man_strategy', 'dark_cloud_cover_strategy'
                ],
                'reason_buy': "Ruptura alcista - seguir impulso de compra",
                'reason_sell': "Ruptura bajista - seguir impulso de venta"
            },
            
            MarketScenario.LOW_VOLATILITY: {
                'preferred_signal': 0,  # Señales sutiles
                'allowed_strategies_buy': [
                    'doji_reversal_strategy', 'spinning_top_strategy',
                    'tweezer_bottom_strategy', 'hammer_reversal_strategy'
                ],
                'allowed_strategies_sell': [
                    'doji_reversal_strategy', 'spinning_top_strategy',
                    'tweezer_top_strategy', 'hanging_man_strategy'
                ],
                'reason_buy': "Baja volatilidad - señales sutiles de compra",
                'reason_sell': "Baja volatilidad - señales sutiles de venta"
            },
            
            MarketScenario.FAKE_BREAKOUT: {
                'preferred_signal': 0,  # Reversión según contexto
                'allowed_strategies_buy': [
                    'inverted_hammer_strategy', 'bullish_engulfing_strategy',
                    'hammer_reversal_strategy', 'tweezer_bottom_strategy'
                ],
                'allowed_strategies_sell': [
                    'shooting_star_strategy', 'bearish_engulfing_strategy',
                    'hanging_man_strategy', 'tweezer_top_strategy'
                ],
                'reason_buy': "Falsa ruptura - reversión alcista",
                'reason_sell': "Falsa ruptura - reversión bajista"
            }
        }
        
        # Obtener reglas para el escenario (usar UNCLEAR como fallback)
        scenario_rules = rules.get(scenario, rules.get(MarketScenario.UNCLEAR, {
            'preferred_signal': 0,
            'allowed_strategies_buy': [strategy_name],
            'allowed_strategies_sell': [strategy_name],
            'reason_buy': "Escenario no claro - permitir operación",
            'reason_sell': "Escenario no claro - permitir operación"
        }))
        
        # Determinar si ejecutar según tipo de señal
        if signal_type == 1:  # BUY
            allowed = strategy_name in scenario_rules.get('allowed_strategies_buy', [])
            reason = scenario_rules.get('reason_buy', 'Operación de compra permitida') if allowed else scenario_rules.get('reason_buy_blocked', 'Operación de compra no recomendada para este escenario')
        elif signal_type == -1:  # SELL
            allowed = strategy_name in scenario_rules.get('allowed_strategies_sell', [])
            reason = scenario_rules.get('reason_sell', 'Operación de venta permitida') if allowed else scenario_rules.get('reason_sell_blocked', 'Operación de venta no recomendada para este escenario')
        else:  # NEUTRAL o desconocido
            allowed = True
            reason = "Señal neutral - permitir evaluación"
        
        return {
            'execute': allowed,
            'reason': reason
        }
    
    def get_priority_weight(self, strategy_name: str, scenario: MarketScenario) -> float:
        """
        Obtiene el peso de prioridad de una estrategia para un escenario.
        
        Args:
            strategy_name: Nombre de la estrategia
            scenario: Escenario de mercado
            
        Returns:
            Peso de prioridad (1.0=alta, 0.5=media, 0.2=baja, 0.0=deshabilitada)
        """
        if scenario not in self.strategy_mappings:
            scenario = MarketScenario.UNCLEAR
        
        priority = self.strategy_mappings[scenario].get(strategy_name, StrategyPriority.DISABLED)
        
        weight_map = {
            StrategyPriority.HIGH: 1.0,
            StrategyPriority.MEDIUM: 0.5,
            StrategyPriority.LOW: 0.2,
            StrategyPriority.DISABLED: 0.0
        }
        
        return weight_map.get(priority, 0.0)
