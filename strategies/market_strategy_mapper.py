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
    Mapea estrategias de velas y forex según el escenario de mercado detectado.
    SIMPLIFICADO para trabajar con solo 3 tipos de mercado:
    - UPTREND (Mercado ascendente): Prioriza operaciones LONG
    - DOWNTREND (Mercado descendente): Prioriza operaciones SHORT
    - LATERAL (Mercado lateral): Permite tanto LONG como SHORT en soportes/resistencias
    """
    
    def __init__(self):
        """Inicializa el mapeador con las configuraciones de estrategias por escenario."""
        self.strategy_mappings = self._initialize_strategy_mappings()
        self.forex_mappings = self._initialize_forex_mappings()
    
    def _initialize_strategy_mappings(self) -> Dict[MarketScenario, Dict[str, StrategyPriority]]:
        """
        Inicializa el mapeo de estrategias de VELAS para 3 tipos de mercado.
        
        Returns:
            Diccionario con escenarios como claves y estrategias con prioridades como valores
        """
        return {
            # 1. MERCADO ASCENDENTE - Priorizar patrones alcistas
            MarketScenario.UPTREND: {
                # Alta prioridad - Patrones de continuación y reversión alcista
                'three_white_soldiers_strategy': StrategyPriority.HIGH,
                'bullish_engulfing_strategy': StrategyPriority.HIGH,
                'piercing_line_strategy': StrategyPriority.HIGH,
                'morning_star_strategy': StrategyPriority.HIGH,
                'hammer_reversal_strategy': StrategyPriority.HIGH,
                'inverted_hammer_strategy': StrategyPriority.HIGH,
                'tweezer_bottom_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - Patrones neutrales
                'doji_reversal_strategy': StrategyPriority.MEDIUM,
                'spinning_top_strategy': StrategyPriority.MEDIUM,
                'marubozu_trend': StrategyPriority.MEDIUM,
                
                # Baja prioridad - Patrones bajistas (para detectar posibles cambios)
                'bearish_engulfing_strategy': StrategyPriority.LOW,
                'dark_cloud_cover_strategy': StrategyPriority.LOW,
                'evening_star_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - Fuertemente contrarias a la tendencia
                'three_black_crows_strategy': StrategyPriority.DISABLED,
                'hanging_man_strategy': StrategyPriority.DISABLED,
                'shooting_star_strategy': StrategyPriority.DISABLED,
                'tweezer_top_strategy': StrategyPriority.DISABLED,
            },
            
            # 2. MERCADO DESCENDENTE - Priorizar patrones bajistas
            MarketScenario.DOWNTREND: {
                # Alta prioridad - Patrones de continuación y reversión bajista
                'three_black_crows_strategy': StrategyPriority.HIGH,
                'bearish_engulfing_strategy': StrategyPriority.HIGH,
                'dark_cloud_cover_strategy': StrategyPriority.HIGH,
                'evening_star_strategy': StrategyPriority.HIGH,
                'hanging_man_strategy': StrategyPriority.HIGH,
                'shooting_star_strategy': StrategyPriority.HIGH,
                'tweezer_top_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - Patrones neutrales
                'doji_reversal_strategy': StrategyPriority.MEDIUM,
                'spinning_top_strategy': StrategyPriority.MEDIUM,
                'marubozu_trend': StrategyPriority.MEDIUM,
                
                # Baja prioridad - Patrones alcistas (para detectar posibles cambios)
                'bullish_engulfing_strategy': StrategyPriority.LOW,
                'piercing_line_strategy': StrategyPriority.LOW,
                'morning_star_strategy': StrategyPriority.LOW,
                
                # Deshabilitadas - Fuertemente contrarias a la tendencia
                'three_white_soldiers_strategy': StrategyPriority.DISABLED,
                'hammer_reversal_strategy': StrategyPriority.DISABLED,
                'inverted_hammer_strategy': StrategyPriority.DISABLED,
                'tweezer_bottom_strategy': StrategyPriority.DISABLED,
            },
            
            # 3. MERCADO LATERAL - Todos los patrones de reversión activos
            MarketScenario.LATERAL: {
                # Alta prioridad - Patrones de reversión en ambas direcciones
                # Para LONG en soporte:
                'hammer_reversal_strategy': StrategyPriority.HIGH,
                'bullish_engulfing_strategy': StrategyPriority.HIGH,
                'tweezer_bottom_strategy': StrategyPriority.HIGH,
                'piercing_line_strategy': StrategyPriority.HIGH,
                'morning_star_strategy': StrategyPriority.HIGH,
                
                # Para SHORT en resistencia:
                'hanging_man_strategy': StrategyPriority.HIGH,
                'bearish_engulfing_strategy': StrategyPriority.HIGH,
                'shooting_star_strategy': StrategyPriority.HIGH,
                'tweezer_top_strategy': StrategyPriority.HIGH,
                'dark_cloud_cover_strategy': StrategyPriority.HIGH,
                'evening_star_strategy': StrategyPriority.HIGH,
                
                # Media prioridad - Indecisión y otros
                'doji_reversal_strategy': StrategyPriority.MEDIUM,
                'spinning_top_strategy': StrategyPriority.MEDIUM,
                'inverted_hammer_strategy': StrategyPriority.MEDIUM,
                
                # Baja prioridad - Patrones de continuación (menos útiles en rango)
                'three_white_soldiers_strategy': StrategyPriority.LOW,
                'three_black_crows_strategy': StrategyPriority.LOW,
                'marubozu_trend': StrategyPriority.LOW,
            }
        }

    def _initialize_forex_mappings(self) -> Dict[MarketScenario, Dict[str, StrategyPriority]]:
        """
        Inicializa prioridades para estrategias FOREX en 3 tipos de mercado.
        """
        return {
            # 1. MERCADO ASCENDENTE - Estrategias de tendencia y momentum alcista
            MarketScenario.UPTREND: {
                'trend_following': StrategyPriority.HIGH,
                'moving_average_crossover': StrategyPriority.HIGH,
                'ichimoku_cloud_strategy': StrategyPriority.HIGH,
                'breakout': StrategyPriority.HIGH,
                'macd_strategy': StrategyPriority.HIGH,
                
                'rsi_strategy': StrategyPriority.MEDIUM,
                'support_resistance_strategy': StrategyPriority.MEDIUM,
                'price_action_patterns': StrategyPriority.MEDIUM,
                
                'bollinger_bands_strategy': StrategyPriority.LOW,
                'stochastic_strategy': StrategyPriority.LOW,
                
                'range_trading_strategy': StrategyPriority.DISABLED,
            },

            # 2. MERCADO DESCENDENTE - Estrategias de tendencia y momentum bajista
            MarketScenario.DOWNTREND: {
                'trend_following': StrategyPriority.HIGH,
                'moving_average_crossover': StrategyPriority.HIGH,
                'ichimoku_cloud_strategy': StrategyPriority.HIGH,
                'breakout': StrategyPriority.HIGH,
                'macd_strategy': StrategyPriority.HIGH,
                
                'rsi_strategy': StrategyPriority.MEDIUM,
                'support_resistance_strategy': StrategyPriority.MEDIUM,
                'price_action_patterns': StrategyPriority.MEDIUM,
                
                'bollinger_bands_strategy': StrategyPriority.LOW,
                'stochastic_strategy': StrategyPriority.LOW,
                
                'range_trading_strategy': StrategyPriority.DISABLED,
            },

            # 3. MERCADO LATERAL - Estrategias de rango y reversión
            MarketScenario.LATERAL: {
                'range_trading_strategy': StrategyPriority.HIGH,
                'bollinger_bands_strategy': StrategyPriority.HIGH,
                'support_resistance_strategy': StrategyPriority.HIGH,
                'rsi_strategy': StrategyPriority.HIGH,
                'stochastic_strategy': StrategyPriority.HIGH,
                
                'price_action_patterns': StrategyPriority.MEDIUM,
                'mean_reversion_strategy': StrategyPriority.MEDIUM,
                'grid_trading_strategy': StrategyPriority.MEDIUM,
                
                'macd_strategy': StrategyPriority.LOW,
                'moving_average_crossover': StrategyPriority.LOW,
                
                'trend_following': StrategyPriority.DISABLED,
                'ichimoku_cloud_strategy': StrategyPriority.DISABLED,
                'breakout': StrategyPriority.DISABLED,
            }
        }

    def get_prioritized_forex_strategies(self, scenario: MarketScenario,
                                         available_strategies: List[str] = None) -> Dict[str, StrategyPriority]:
        """Obtiene prioridades para estrategias Forex por escenario (filtradas opcionalmente)."""
        # Si el escenario no existe, usar LATERAL como fallback
        if scenario not in self.forex_mappings:
            scenario = MarketScenario.LATERAL
            
        mapping = self.forex_mappings[scenario]
        
        if available_strategies:
            return {k: v for k, v in mapping.items() if k in available_strategies}
        return mapping.copy()

    def should_execute_forex_strategy(self, strategy_name: str, scenario: MarketScenario,
                                    signal_type: int) -> Tuple[bool, str]:
        """
        Reglas de ejecución para estrategias Forex.
        En el sistema simplificado:
        - UPTREND: Permite BUY (1), restringe SELL (-1)
        - DOWNTREND: Permite SELL (-1), restringe BUY (1)
        - LATERAL: Permite tanto BUY como SELL
        """
        if scenario not in self.forex_mappings:
            scenario = MarketScenario.LATERAL

        # Reglas simplificadas para 3 tipos de mercado
        rules = {
            # MERCADO ASCENDENTE
            MarketScenario.UPTREND: {
                'preferred_signal': 1,  # Preferir BUY
                'allowed_buy': True,    # Permitir compras
                'allowed_sell': False,  # Restringir ventas (solo para cerrar posiciones)
                'reason_buy': "Mercado ascendente - operaciones LONG priorizadas",
                'reason_sell_blocked': "Mercado ascendente - evitar operaciones SHORT nuevas",
            },

            # MERCADO DESCENDENTE
            MarketScenario.DOWNTREND: {
                'preferred_signal': -1,  # Preferir SELL
                'allowed_buy': False,    # Restringir compras (solo para cerrar posiciones)
                'allowed_sell': True,    # Permitir ventas
                'reason_buy_blocked': "Mercado descendente - evitar operaciones LONG nuevas",
                'reason_sell': "Mercado descendente - operaciones SHORT priorizadas",
            },

            # MERCADO LATERAL
            MarketScenario.LATERAL: {
                'preferred_signal': 0,   # No hay preferencia
                'allowed_buy': True,     # Permitir compras en soporte
                'allowed_sell': True,    # Permitir ventas en resistencia
                'reason_buy': "Mercado lateral - compras en zona de soporte",
                'reason_sell': "Mercado lateral - ventas en zona de resistencia",
            },
        }

        scenario_rules = rules.get(scenario, rules[MarketScenario.LATERAL])
        
        # Determinar si ejecutar según el tipo de señal
        if signal_type == 1:  # BUY
            allowed = scenario_rules.get('allowed_buy', True)
            reason = scenario_rules.get('reason_buy', 'Compra permitida') if allowed else scenario_rules.get('reason_buy_blocked', 'Compra no recomendada')
        elif signal_type == -1:  # SELL
            allowed = scenario_rules.get('allowed_sell', True)
            reason = scenario_rules.get('reason_sell', 'Venta permitida') if allowed else scenario_rules.get('reason_sell_blocked', 'Venta no recomendada')
        else:  # NEUTRAL (0)
            allowed = True
            reason = "Señal neutral - evaluación permitida"

        return allowed, reason

    def get_prioritized_strategies(self, scenario: MarketScenario, 
                                 available_strategies: List[str] = None) -> Dict[str, StrategyPriority]:
        """
        Obtiene las estrategias de VELAS priorizadas para un escenario específico.
        """
        if scenario not in self.strategy_mappings:
            scenario = MarketScenario.LATERAL
        
        scenario_strategies = self.strategy_mappings[scenario]
        
        if available_strategies:
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
        """
        descriptions = {
            MarketScenario.UPTREND: "Mercado ascendente - Priorizar operaciones LONG y patrones de continuación alcista",
            MarketScenario.DOWNTREND: "Mercado descendente - Priorizar operaciones SHORT y patrones de continuación bajista", 
            MarketScenario.LATERAL: "Mercado lateral - Operar reversiones: LONG en soportes, SHORT en resistencias",
        }
        return descriptions.get(scenario, "Mercado lateral - Operar en rangos")

    def should_execute_strategy(self, strategy_name: str, scenario: MarketScenario, 
                              signal_type: int) -> Tuple[bool, str]:
        """
        Determina si una estrategia de VELAS debe ejecutarse según el escenario y tipo de señal.
        Sistema simplificado para 3 tipos de mercado.
        """
        if scenario not in self.strategy_mappings:
            scenario = MarketScenario.LATERAL
        
        scenario_strategies = self.strategy_mappings[scenario]
        strategy_priority = scenario_strategies.get(strategy_name, StrategyPriority.DISABLED)
        
        # Si la estrategia está deshabilitada para este escenario, no ejecutar
        if strategy_priority == StrategyPriority.DISABLED:
            return False, f"Estrategia deshabilitada para {scenario.value}"
        
        # Reglas de ejecución simplificadas
        execution_rules = self._get_execution_rules(scenario, strategy_name, signal_type)
        should_execute = execution_rules['execute']
        reason = execution_rules['reason']
        
        return should_execute, reason
    
    def _get_execution_rules(self, scenario: MarketScenario, strategy_name: str, 
                           signal_type: int) -> Dict[str, any]:
        """
        Obtiene las reglas de ejecución para estrategias de VELAS.
        Simplificado para 3 tipos de mercado.
        """
        # Estrategias alcistas (generan señales BUY)
        bullish_strategies = [
            'three_white_soldiers_strategy', 'bullish_engulfing_strategy', 
            'piercing_line_strategy', 'hammer_reversal_strategy', 
            'morning_star_strategy', 'inverted_hammer_strategy',
            'tweezer_bottom_strategy'
        ]
        
        # Estrategias bajistas (generan señales SELL)
        bearish_strategies = [
            'three_black_crows_strategy', 'bearish_engulfing_strategy',
            'dark_cloud_cover_strategy', 'hanging_man_strategy',
            'shooting_star_strategy', 'evening_star_strategy',
            'tweezer_top_strategy'
        ]
        
        # Estrategias neutrales (pueden generar ambas señales)
        neutral_strategies = [
            'doji_reversal_strategy', 'spinning_top_strategy',
            'marubozu_trend'
        ]
        
        # Reglas por escenario
        rules = {
            MarketScenario.UPTREND: {
                'allow_bullish': True,    # Permitir estrategias alcistas
                'allow_bearish': False,   # Restringir estrategias bajistas (solo para cierre)
                'allow_neutral': True,    # Permitir estrategias neutrales
                'reason_bullish': "Mercado ascendente - patrón alcista confirmado",
                'reason_bearish_blocked': "Mercado ascendente - evitar nuevos SHORT",
                'reason_neutral': "Mercado ascendente - patrón neutral evaluado"
            },
            
            MarketScenario.DOWNTREND: {
                'allow_bullish': False,   # Restringir estrategias alcistas (solo para cierre)
                'allow_bearish': True,    # Permitir estrategias bajistas
                'allow_neutral': True,    # Permitir estrategias neutrales
                'reason_bullish_blocked': "Mercado descendente - evitar nuevos LONG",
                'reason_bearish': "Mercado descendente - patrón bajista confirmado",
                'reason_neutral': "Mercado descendente - patrón neutral evaluado"
            },
            
            MarketScenario.LATERAL: {
                'allow_bullish': True,    # Permitir todas las estrategias
                'allow_bearish': True,
                'allow_neutral': True,
                'reason_bullish': "Mercado lateral - patrón alcista en soporte",
                'reason_bearish': "Mercado lateral - patrón bajista en resistencia",
                'reason_neutral': "Mercado lateral - patrón de reversión detectado"
            }
        }
        
        scenario_rules = rules.get(scenario, rules[MarketScenario.LATERAL])
        
        # Determinar si la estrategia debe ejecutarse
        if strategy_name in bullish_strategies:
            allowed = scenario_rules['allow_bullish']
            reason = scenario_rules.get('reason_bullish', '') if allowed else scenario_rules.get('reason_bullish_blocked', '')
        elif strategy_name in bearish_strategies:
            allowed = scenario_rules['allow_bearish']
            reason = scenario_rules.get('reason_bearish', '') if allowed else scenario_rules.get('reason_bearish_blocked', '')
        else:  # neutral strategies
            allowed = scenario_rules['allow_neutral']
            reason = scenario_rules.get('reason_neutral', '')
        
        # Si es señal de cierre (contraria a la tendencia), permitir siempre
        if signal_type == 0 or (
            (scenario == MarketScenario.UPTREND and signal_type == -1) or
            (scenario == MarketScenario.DOWNTREND and signal_type == 1)
        ):
            # Permitir señales de cierre/neutralización
            allowed = True
            reason = f"Señal de gestión de posición permitida en {scenario.value}"
        
        return {
            'execute': allowed,
            'reason': reason
        }
    
    def get_priority_weight(self, strategy_name: str, scenario: MarketScenario) -> float:
        """
        Obtiene el peso de prioridad de una estrategia para un escenario.
        """
        if scenario not in self.strategy_mappings:
            scenario = MarketScenario.LATERAL
        
        priority = self.strategy_mappings[scenario].get(strategy_name, StrategyPriority.DISABLED)
        
        weight_map = {
            StrategyPriority.HIGH: 1.0,
            StrategyPriority.MEDIUM: 0.5,
            StrategyPriority.LOW: 0.2,
            StrategyPriority.DISABLED: 0.0
        }
        
        return weight_map.get(priority, 0.0)
