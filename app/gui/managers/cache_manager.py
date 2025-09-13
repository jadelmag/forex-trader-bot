# app/gui/managers/cache_manager.py
import hashlib
import pandas as pd
import numpy as np
from typing import Optional, Any, Dict

class CacheManager:
    def __init__(self):
        # Cache para instancias pesadas (evitar recreación constante)
        self._forex_strategies_cache = None
        self._candle_strategies_cache = None
        self._patterns_cache = None
        self._last_df_hash = None
        
        # ATR precalculado (evitar recálculos repetitivos)
        self._cached_atr = None
        self._atr_last_update = None
        
        # Cache general para datos
        self._data_cache: Dict[str, Any] = {}
        
    def get_df_hash(self, df: pd.DataFrame) -> str:
        """Calcula un hash único para un DataFrame"""
        try:
            if df is None or df.empty:
                return ""
            # Usar una muestra del DataFrame para el hash
            sample_data = str(df.head().to_string()) + str(df.tail().to_string()) + str(len(df))
            return hashlib.md5(sample_data.encode()).hexdigest()
        except Exception:
            return ""
            
    def is_df_cached(self, df: pd.DataFrame) -> bool:
        """Verifica si el DataFrame ya está en caché"""
        current_hash = self.get_df_hash(df)
        return current_hash == self._last_df_hash and current_hash != ""
        
    def update_df_cache(self, df: pd.DataFrame):
        """Actualiza el hash del DataFrame en caché"""
        self._last_df_hash = self.get_df_hash(df)
        
    def _get_cached_atr(self, df: pd.DataFrame, last_candle: pd.Series) -> float:
        """Obtiene ATR precalculado o lo calcula una sola vez por vela"""
        try:
            import time
            import numpy as np
            current_time = time.time()
            # Recalcular ATR solo si han pasado más de 1 segundo o es la primera vez
            if (self._cached_atr is None or 
                self._atr_last_update is None or 
                current_time - self._atr_last_update > 1.0):
                
                try:
                    atr_series = (df['High'] - df['Low']).rolling(14).mean()
                    atr_value = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else float((df['High'] - df['Low']).mean())
                except Exception:
                    try:
                        high_low_range = (df['High'] - df['Low']).tail(20).mean()
                        atr_value = float(high_low_range) if not np.isnan(high_low_range) else float(last_candle['Close']) * 0.002
                    except Exception:
                        atr_value = float(last_candle['Close']) * 0.002
                
                self._cached_atr = atr_value
                self._atr_last_update = current_time
            
            return self._cached_atr
        except Exception:
            return float(last_candle['Close']) * 0.002
    
    def _get_cached_forex_strategies(self, df: pd.DataFrame):
        """Obtiene instancia cacheada de ForexStrategies o la crea"""
        try:
            # Calcular hash del DataFrame para detectar cambios
            df_hash = hash(str(df.shape) + str(df.iloc[-1].to_dict()) if not df.empty else "empty")
            
            if (self._forex_strategies_cache is None or 
                self._last_df_hash != df_hash):
                from strategies import ForexStrategies
                self._forex_strategies_cache = ForexStrategies(df)
                self._last_df_hash = df_hash
            
            return self._forex_strategies_cache
        except Exception:
            from strategies import ForexStrategies
            return ForexStrategies(df)
    
    def _get_cached_candle_strategies(self, df: pd.DataFrame):
        """Obtiene instancia cacheada de CandleStrategies o la crea"""
        try:
            df_hash = hash(str(df.shape) + str(df.iloc[-1].to_dict()) if not df.empty else "empty")
            
            if (self._candle_strategies_cache is None or 
                self._last_df_hash != df_hash):
                from strategies.candle_strategies import CandleStrategies
                self._candle_strategies_cache = CandleStrategies(df)
                self._last_df_hash = df_hash
            
            return self._candle_strategies_cache
        except Exception:
            from strategies.candle_strategies import CandleStrategies
            return CandleStrategies(df)
    
    def _get_cached_patterns(self, df: pd.DataFrame):
        """Obtiene instancia cacheada de CandlestickPatterns o la crea"""
        try:
            df_hash = hash(str(df.shape) + str(df.iloc[-1].to_dict()) if not df.empty else "empty")
            
            if (self._patterns_cache is None or 
                self._last_df_hash != df_hash):
                from patterns.candlestickpatterns import CandlestickPatterns
                self._patterns_cache = CandlestickPatterns(df)
                self._last_df_hash = df_hash
            
            return self._patterns_cache
        except Exception:
            from patterns.candlestickpatterns import CandlestickPatterns
            return CandlestickPatterns(df)
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self, 'main_app') and hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)
        else:
            print(f"[{color}] {message}")
        
    def get_forex_strategies(self):
        """Obtiene instancia cacheada de ForexStrategies"""
        return self._forex_strategies_cache
        
    def cache_forex_strategies(self, strategies_instance):
        """Cachea instancia de ForexStrategies"""
        self._forex_strategies_cache = strategies_instance
        
    def get_candle_strategies(self):
        """Obtiene instancia cacheada de CandleStrategies"""
        return self._candle_strategies_cache
        
    def cache_candle_strategies(self, strategies_instance):
        """Cachea instancia de CandleStrategies"""
        self._candle_strategies_cache = strategies_instance
        
    def get_patterns(self):
        """Obtiene instancia cacheada de Patterns"""
        return self._patterns_cache
        
    def cache_patterns(self, patterns_instance):
        """Cachea instancia de Patterns"""
        self._patterns_cache = patterns_instance
        
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Obtiene datos del caché general"""
        return self._data_cache.get(key)
        
    def cache_data(self, key: str, data: Any):
        """Cachea datos en el caché general"""
        self._data_cache[key] = data
        
    def clear_cache(self):
        """Limpia todo el caché"""
        self._forex_strategies_cache = None
        self._candle_strategies_cache = None
        self._patterns_cache = None
        self._last_df_hash = None
        self._cached_atr = None
        self._atr_last_update = None
        self._data_cache.clear()
        
    def clear_strategies_cache(self):
        """Limpia solo el caché de estrategias"""
        self._forex_strategies_cache = None
        self._candle_strategies_cache = None
        self._patterns_cache = None
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        return {
            'forex_strategies_cached': self._forex_strategies_cache is not None,
            'candle_strategies_cached': self._candle_strategies_cache is not None,
            'patterns_cached': self._patterns_cache is not None,
            'atr_cached': self._cached_atr is not None,
            'df_hash': self._last_df_hash,
            'data_cache_size': len(self._data_cache)
        }