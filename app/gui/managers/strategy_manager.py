# app/gui/managers/strategy_manager.py
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from strategies import ForexStrategies, CandleStrategies
from strategies.strategy_utils import get_available_strategies, resolve_strategy_name
from patterns.candlestickpatterns import CandlestickPatterns

class StrategyManager:
    def __init__(self, main_app):
        self.main_app = main_app
        
        # Instancias de estrategias
        self._forex_strategies = None
        self._candle_strategies = None
        self._patterns_instance = None
        
        # Configuración de estrategias
        self.strategy_config = {
            'max_orders': 5,
            'risk_per_trade': 0.02,
            'rr_ratio': 2.0,
            'enable_forex': True,
            'enable_candle': True,
            'enable_patterns': True
        }
        
        # Resultados de estrategias aplicadas
        self.applied_strategies = {}
        self.strategy_results = {}
        
    def initialize_strategies(self, df: pd.DataFrame):
        """Inicializa las instancias de estrategias con el DataFrame"""
        if df is None or df.empty:
            return False
            
        try:
            # Verificar si ya están en caché
            cached_forex = self.main_app.cache_manager.get_forex_strategies()
            cached_candle = self.main_app.cache_manager.get_candle_strategies()
            cached_patterns = self.main_app.cache_manager.get_patterns()
            
            # Verificar si el DataFrame ha cambiado
            if self.main_app.cache_manager.is_df_cached(df):
                if cached_forex:
                    self._forex_strategies = cached_forex
                if cached_candle:
                    self._candle_strategies = cached_candle
                if cached_patterns:
                    self._patterns_instance = cached_patterns
            else:
                # Crear nuevas instancias
                self._forex_strategies = ForexStrategies(df)
                self._candle_strategies = CandleStrategies(df)
                self._patterns_instance = CandlestickPatterns(df)
                
                # Cachear las instancias
                self.main_app.cache_manager.cache_forex_strategies(self._forex_strategies)
                self.main_app.cache_manager.cache_candle_strategies(self._candle_strategies)
                self.main_app.cache_manager.cache_patterns(self._patterns_instance)
                
            return True
        except Exception as e:
            self.log(f"Error inicializando estrategias: {e}", color='red')
            return False
            
    def get_available_strategies(self) -> Dict[str, List[str]]:
        """Obtiene las estrategias disponibles por tipo"""
        try:
            fx_methods, candle_methods = get_available_strategies()
            
            # Obtener patrones disponibles
            pattern_methods = []
            if self._patterns_instance:
                pattern_methods = [
                    method for method in dir(self._patterns_instance)
                    if not method.startswith('_') and callable(getattr(self._patterns_instance, method))
                ]
            
            return {
                'forex': sorted(fx_methods),
                'candle': sorted(candle_methods),
                'patterns': sorted(pattern_methods)
            }
        except Exception as e:
            self.log(f"Error obteniendo estrategias disponibles: {e}", color='red')
            return {'forex': [], 'candle': [], 'patterns': []}
            
    def apply_strategy(self, strategy_name: str, strategy_type: str, params: Dict = None) -> Optional[pd.DataFrame]:
        """Aplica una estrategia específica"""
        if params is None:
            params = {}
            
        try:
            if strategy_type == 'forex' and self._forex_strategies:
                method_name = resolve_strategy_name(strategy_name, 'forex')
                method = getattr(self._forex_strategies, method_name, None)
                if callable(method):
                    risk_kwargs = {
                        'risk_per_trade': params.get('riesgo', self.strategy_config['risk_per_trade']),
                        'rr_ratio': params.get('rr', self.strategy_config['rr_ratio']),
                    }
                    return method(**risk_kwargs)
                    
            elif strategy_type == 'candle' and self._candle_strategies:
                method_name = resolve_strategy_name(strategy_name, 'candle')
                method = getattr(self._candle_strategies, method_name, None)
                if callable(method):
                    return method()
                    
            elif strategy_type == 'pattern' and self._patterns_instance:
                # Manejar namespace de patrones
                method_name = strategy_name.split("::", 1)[1] if strategy_name.startswith("pattern::") else strategy_name
                method = getattr(self._patterns_instance, method_name, None)
                if callable(method):
                    return method()
                    
        except Exception as e:
            self.log(f"Error aplicando estrategia {strategy_name}: {e}", color='red')
            
        return None
        
    def apply_multiple_strategies(self, strategies_config: Dict) -> pd.DataFrame:
        """Aplica múltiples estrategias y combina los resultados"""
        if not strategies_config:
            return None
            
        df_base = self.main_app.csv_handler.df_actual
        if df_base is None:
            return None
            
        df_result = df_base.copy()
        
        for strategy_name, config in strategies_config.items():
            strategy_type = config.get('tipo', 'forex')
            params = config.get('params', {})
            
            df_strategy = self.apply_strategy(strategy_name, strategy_type, params)
            
            if df_strategy is not None and 'Signal' in df_strategy.columns:
                # Agregar señales al DataFrame resultado
                col_name = f"{strategy_name}_Signal"
                df_result[col_name] = 0
                
                # Copiar señales no nulas
                signal_series = df_strategy['Signal']
                non_zero_signals = signal_series[signal_series != 0]
                df_result.loc[non_zero_signals.index, col_name] = non_zero_signals
                
                # Guardar resultado de la estrategia
                self.strategy_results[strategy_name] = {
                    'type': strategy_type,
                    'signals_count': len(non_zero_signals),
                    'buy_signals': len(non_zero_signals[non_zero_signals > 0]),
                    'sell_signals': len(non_zero_signals[non_zero_signals < 0]),
                    'config': config
                }
                
                self.log(f"Estrategia {strategy_name} aplicada: {len(non_zero_signals)} señales", color='cyan')
                
        self.applied_strategies = strategies_config
        return df_result
        
    def get_strategy_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de las estrategias aplicadas"""
        if not self.strategy_results:
            return {}
            
        total_signals = sum(result['signals_count'] for result in self.strategy_results.values())
        total_buy = sum(result['buy_signals'] for result in self.strategy_results.values())
        total_sell = sum(result['sell_signals'] for result in self.strategy_results.values())
        
        return {
            'total_strategies': len(self.strategy_results),
            'total_signals': total_signals,
            'total_buy_signals': total_buy,
            'total_sell_signals': total_sell,
            'strategies_by_type': self._group_strategies_by_type(),
            'individual_results': self.strategy_results.copy()
        }
        
    def _group_strategies_by_type(self) -> Dict[str, int]:
        """Agrupa las estrategias por tipo"""
        type_count = {}
        for result in self.strategy_results.values():
            strategy_type = result['type']
            type_count[strategy_type] = type_count.get(strategy_type, 0) + 1
        return type_count
        
    def clear_results(self):
        """Limpia los resultados de estrategias"""
        self.applied_strategies.clear()
        self.strategy_results.clear()
        
    def update_config(self, new_config: Dict):
        """Actualiza la configuración de estrategias"""
        self.strategy_config.update(new_config)
        
    def get_config(self) -> Dict:
        """Obtiene la configuración actual"""
        return self.strategy_config.copy()
        
    def validate_strategy_exists(self, strategy_name: str, strategy_type: str) -> bool:
        """Valida si una estrategia existe"""
        try:
            if strategy_type == 'forex' and self._forex_strategies:
                method_name = resolve_strategy_name(strategy_name, 'forex')
                return hasattr(self._forex_strategies, method_name)
            elif strategy_type == 'candle' and self._candle_strategies:
                method_name = resolve_strategy_name(strategy_name, 'candle')
                return hasattr(self._candle_strategies, method_name)
            elif strategy_type == 'pattern' and self._patterns_instance:
                method_name = strategy_name.split("::", 1)[1] if strategy_name.startswith("pattern::") else strategy_name
                return hasattr(self._patterns_instance, method_name)
        except Exception:
            pass
        return False
        
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)