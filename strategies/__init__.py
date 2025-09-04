# strategies/__init__.py

from .strategies import ForexStrategies
from .candle_strategies import CandleStrategies  # Si existe
from .risk_manager import RiskManager, RiskManagerIntegration, Operacion
from .strategy_utils import get_available_strategies

__all__ = [
    'ForexStrategies', 
    'CandleStrategies', 
    'RiskManager', 
    'RiskManagerIntegration', 
    'Operacion',
    'get_available_strategies'
]