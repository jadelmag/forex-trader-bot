# ia/candle_strategy_optimizer.py

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import random
from dataclasses import dataclass
from patterns.candlestickpatterns import CandlestickPatterns
from strategies.candle_strategies import CandleStrategies
import json
import os

@dataclass
class OptimizationResult:
    """Resultado de una optimización de parámetros"""
    parameters: Dict[str, Any]
    win_rate: float
    total_profit: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit_per_trade: float
    max_drawdown: float
    fitness_score: float

class CandleStrategyOptimizer:
    """Optimizador de parámetros para estrategias de velas usando algoritmos genéticos"""
    
    def __init__(self, data: pd.DataFrame, strategy_name: str, param_ranges: Dict[str, Any]):
        self.data = data
        self.strategy_name = strategy_name
        self.param_ranges = param_ranges
        self.population_size = 50
        self.generations = 30
        self.mutation_rate = 0.1
        self.crossover_rate = 0.8
        self.elite_size = 5
        
    def generate_random_parameters(self) -> Dict[str, Any]:
        """Genera parámetros aleatorios dentro de los rangos especificados"""
        params = {}
        for param_name, param_range in self.param_ranges.items():
            if isinstance(param_range, tuple) and len(param_range) == 2:
                # Rango numérico
                min_val, max_val = param_range
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = random.randint(min_val, max_val)
                else:
                    params[param_name] = random.uniform(min_val, max_val)
            elif isinstance(param_range, list):
                # Lista de opciones
                params[param_name] = random.choice(param_range)
        return params
    
    def evaluate_parameters(self, params: Dict[str, Any]) -> OptimizationResult:
        """Evalúa un conjunto de parámetros y retorna métricas de rendimiento"""
        try:
            # Separar parámetros de detección y de salida
            detection_params = {k: v for k, v in params.items() 
                              if k not in ['use_signal_change', 'use_stop_loss', 'use_take_profit', 
                                         'use_trailing_stop', 'use_pattern_reversal', 'atr_sl_multiplier', 
                                         'atr_tp_multiplier', 'atr_trailing_multiplier']}
            
            exit_params = {k: v for k, v in params.items() 
                          if k in ['use_signal_change', 'use_stop_loss', 'use_take_profit', 
                                 'use_trailing_stop', 'use_pattern_reversal', 'atr_sl_multiplier', 
                                 'atr_tp_multiplier', 'atr_trailing_multiplier']}
            
            # Crear instancia de CandlestickPatterns con parámetros optimizados
            patterns = CandlestickPatterns(self.data, config=detection_params)
            
            # Crear instancia de CandleStrategies
            candle_strategies = CandleStrategies(patterns)
            
            # Ejecutar la estrategia específica
            if hasattr(candle_strategies, self.strategy_name):
                strategy_method = getattr(candle_strategies, self.strategy_name)
                signals_df = strategy_method()
            else:
                # Fallback: usar detección de patrones directa
                signals_df = patterns.detect_all_patterns()
            
            # Simular trades con parámetros de salida
            trades = self._simulate_trades(signals_df, exit_params)
            
            # Calcular métricas
            if not trades:
                return OptimizationResult(
                    parameters=params,
                    win_rate=0.0,
                    total_profit=0.0,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    avg_profit_per_trade=0.0,
                    max_drawdown=0.0,
                    fitness_score=0.0
                )
            
            winning_trades = sum(1 for trade in trades if trade['profit'] > 0)
            losing_trades = len(trades) - winning_trades
            total_profit = sum(trade['profit'] for trade in trades)
            win_rate = winning_trades / len(trades) if trades else 0.0
            avg_profit = total_profit / len(trades) if trades else 0.0
            
            # Calcular drawdown máximo
            cumulative_profits = np.cumsum([trade['profit'] for trade in trades])
            running_max = np.maximum.accumulate(cumulative_profits)
            drawdowns = running_max - cumulative_profits
            max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
            
            # Calcular fitness score (combinación de win rate y profit)
            fitness_score = self._calculate_fitness(win_rate, total_profit, len(trades), max_drawdown)
            
            return OptimizationResult(
                parameters=params,
                win_rate=win_rate,
                total_profit=total_profit,
                total_trades=len(trades),
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                avg_profit_per_trade=avg_profit,
                max_drawdown=max_drawdown,
                fitness_score=fitness_score
            )
            
        except Exception as e:
            print(f"Error evaluando parámetros: {e}")
            return OptimizationResult(
                parameters=params,
                win_rate=0.0,
                total_profit=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_profit_per_trade=0.0,
                max_drawdown=0.0,
                fitness_score=0.0
            )
    
    def _simulate_trades(self, signals_df: pd.DataFrame, exit_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simula trades basado en señales y parámetros de salida"""
        trades = []
        
        # Parámetros por defecto
        use_stop_loss = exit_params.get('use_stop_loss', True)
        use_take_profit = exit_params.get('use_take_profit', True)
        use_trailing_stop = exit_params.get('use_trailing_stop', False)
        atr_sl_multiplier = exit_params.get('atr_sl_multiplier', 1.5)
        atr_tp_multiplier = exit_params.get('atr_tp_multiplier', 3.0)
        atr_trailing_multiplier = exit_params.get('atr_trailing_multiplier', 2.0)
        
        # Buscar señales de trading
        signal_column = 'Trading_Signal' if 'Trading_Signal' in signals_df.columns else 'Signal'
        if signal_column not in signals_df.columns:
            return trades
        
        open_positions = []
        
        for i in range(len(signals_df)):
            current_row = signals_df.iloc[i]
            
            # Procesar posiciones abiertas
            positions_to_close = []
            for pos_idx, position in enumerate(open_positions):
                exit_info = self._check_exit_conditions(
                    position, current_row, i, signals_df, 
                    use_stop_loss, use_take_profit, use_trailing_stop,
                    atr_sl_multiplier, atr_tp_multiplier, atr_trailing_multiplier
                )
                
                if exit_info['should_exit']:
                    profit = self._calculate_profit(position, current_row, exit_info['exit_price'])
                    trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': exit_info['exit_price'],
                        'direction': position['direction'],
                        'profit': profit,
                        'entry_time': position['entry_time'],
                        'exit_time': i,
                        'exit_reason': exit_info['reason']
                    })
                    positions_to_close.append(pos_idx)
            
            # Cerrar posiciones
            for pos_idx in reversed(positions_to_close):
                open_positions.pop(pos_idx)
            
            # Abrir nuevas posiciones
            signal = current_row.get(signal_column, 0)
            if signal != 0 and len(open_positions) < 5:  # Máximo 5 posiciones simultáneas
                position = {
                    'entry_price': current_row['Close'],
                    'direction': 1 if signal > 0 else -1,
                    'entry_time': i,
                    'atr': current_row.get('ATR', current_row['Close'] * 0.01),  # Fallback ATR
                    'highest_profit': 0.0
                }
                open_positions.append(position)
        
        # Cerrar posiciones restantes al final
        if open_positions:
            final_row = signals_df.iloc[-1]
            for position in open_positions:
                profit = self._calculate_profit(position, final_row, final_row['Close'])
                trades.append({
                    'entry_price': position['entry_price'],
                    'exit_price': final_row['Close'],
                    'direction': position['direction'],
                    'profit': profit,
                    'entry_time': position['entry_time'],
                    'exit_time': len(signals_df) - 1,
                    'exit_reason': 'end_of_data'
                })
        
        return trades
    
    def _check_exit_conditions(self, position: Dict[str, Any], current_row: pd.Series, 
                              current_idx: int, signals_df: pd.DataFrame,
                              use_stop_loss: bool, use_take_profit: bool, use_trailing_stop: bool,
                              atr_sl_multiplier: float, atr_tp_multiplier: float, 
                              atr_trailing_multiplier: float) -> Dict[str, Any]:
        """Verifica condiciones de salida para una posición"""
        
        current_price = current_row['Close']
        entry_price = position['entry_price']
        direction = position['direction']
        atr = position['atr']
        
        # Calcular profit actual
        current_profit = self._calculate_profit(position, current_row, current_price)
        
        # Actualizar highest_profit para trailing stop
        if current_profit > position['highest_profit']:
            position['highest_profit'] = current_profit
        
        # Stop Loss
        if use_stop_loss:
            sl_distance = atr * atr_sl_multiplier
            if direction == 1:  # Long
                sl_price = entry_price - sl_distance
                if current_price <= sl_price:
                    return {'should_exit': True, 'exit_price': sl_price, 'reason': 'stop_loss'}
            else:  # Short
                sl_price = entry_price + sl_distance
                if current_price >= sl_price:
                    return {'should_exit': True, 'exit_price': sl_price, 'reason': 'stop_loss'}
        
        # Take Profit
        if use_take_profit:
            tp_distance = atr * atr_tp_multiplier
            if direction == 1:  # Long
                tp_price = entry_price + tp_distance
                if current_price >= tp_price:
                    return {'should_exit': True, 'exit_price': tp_price, 'reason': 'take_profit'}
            else:  # Short
                tp_price = entry_price - tp_distance
                if current_price <= tp_price:
                    return {'should_exit': True, 'exit_price': tp_price, 'reason': 'take_profit'}
        
        # Trailing Stop
        if use_trailing_stop and position['highest_profit'] > 0:
            trailing_distance = atr * atr_trailing_multiplier
            max_profit_price = entry_price + (position['highest_profit'] * direction)
            
            if direction == 1:  # Long
                trailing_sl = max_profit_price - trailing_distance
                if current_price <= trailing_sl:
                    return {'should_exit': True, 'exit_price': trailing_sl, 'reason': 'trailing_stop'}
            else:  # Short
                trailing_sl = max_profit_price + trailing_distance
                if current_price >= trailing_sl:
                    return {'should_exit': True, 'exit_price': trailing_sl, 'reason': 'trailing_stop'}
        
        return {'should_exit': False, 'exit_price': current_price, 'reason': 'none'}
    
    def _calculate_profit(self, position: Dict[str, Any], current_row: pd.Series, exit_price: float) -> float:
        """Calcula el profit de una posición"""
        entry_price = position['entry_price']
        direction = position['direction']
        
        if direction == 1:  # Long
            return (exit_price - entry_price) / entry_price
        else:  # Short
            return (entry_price - exit_price) / entry_price
    
    def _calculate_fitness(self, win_rate: float, total_profit: float, total_trades: int, max_drawdown: float) -> float:
        """Calcula el fitness score combinando múltiples métricas"""
        if total_trades == 0:
            return 0.0
        
        # Componentes del fitness
        win_rate_component = win_rate * 100  # 0-100
        profit_component = total_profit * 100  # Convertir a porcentaje
        trade_frequency_component = min(total_trades / 100, 1.0) * 20  # Bonus por actividad
        drawdown_penalty = max_drawdown * 50  # Penalizar drawdown alto
        
        # Fitness final (mayor es mejor)
        fitness = (
            win_rate_component * 0.4 +  # 40% peso al win rate
            profit_component * 0.4 +    # 40% peso al profit total
            trade_frequency_component * 0.1 -  # 10% bonus por actividad
            drawdown_penalty * 0.1      # 10% penalización por drawdown
        )
        
        return max(0.0, fitness)
    
    def optimize(self, progress_callback=None) -> OptimizationResult:
        """Ejecuta la optimización usando algoritmo genético"""
        print(f"Iniciando optimización para {self.strategy_name}...")
        
        # Generar población inicial
        population = []
        for _ in range(self.population_size):
            params = self.generate_random_parameters()
            result = self.evaluate_parameters(params)
            population.append(result)
        
        best_result = max(population, key=lambda x: x.fitness_score)
        
        for generation in range(self.generations):
            if progress_callback:
                progress = (generation / self.generations) * 100
                progress_callback(progress, f"Generación {generation + 1}/{self.generations}")
            
            # Selección por torneo
            new_population = []
            
            # Mantener elite
            population.sort(key=lambda x: x.fitness_score, reverse=True)
            for i in range(self.elite_size):
                new_population.append(population[i])
            
            # Generar nueva población
            while len(new_population) < self.population_size:
                parent1 = self._tournament_selection(population)
                parent2 = self._tournament_selection(population)
                
                if random.random() < self.crossover_rate:
                    child_params = self._crossover(parent1.parameters, parent2.parameters)
                else:
                    child_params = parent1.parameters.copy()
                
                if random.random() < self.mutation_rate:
                    child_params = self._mutate(child_params)
                
                child_result = self.evaluate_parameters(child_params)
                new_population.append(child_result)
            
            population = new_population
            current_best = max(population, key=lambda x: x.fitness_score)
            
            if current_best.fitness_score > best_result.fitness_score:
                best_result = current_best
                print(f"Generación {generation + 1}: Nuevo mejor fitness = {best_result.fitness_score:.2f}, "
                      f"Win Rate = {best_result.win_rate:.2%}, Profit = {best_result.total_profit:.2%}")
        
        if progress_callback:
            progress_callback(100, "Optimización completada")
        
        print(f"Optimización completada. Mejor fitness: {best_result.fitness_score:.2f}")
        return best_result
    
    def _tournament_selection(self, population: List[OptimizationResult], tournament_size: int = 3) -> OptimizationResult:
        """Selección por torneo"""
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=lambda x: x.fitness_score)
    
    def _crossover(self, parent1_params: Dict[str, Any], parent2_params: Dict[str, Any]) -> Dict[str, Any]:
        """Cruzamiento de parámetros"""
        child_params = {}
        for param_name in parent1_params:
            if random.random() < 0.5:
                child_params[param_name] = parent1_params[param_name]
            else:
                child_params[param_name] = parent2_params[param_name]
        return child_params
    
    def _mutate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mutación de parámetros"""
        mutated_params = params.copy()
        
        # Seleccionar parámetro aleatorio para mutar
        param_to_mutate = random.choice(list(params.keys()))
        param_range = self.param_ranges[param_to_mutate]
        
        if isinstance(param_range, tuple) and len(param_range) == 2:
            min_val, max_val = param_range
            if isinstance(min_val, int) and isinstance(max_val, int):
                mutated_params[param_to_mutate] = random.randint(min_val, max_val)
            else:
                # Mutación gaussiana
                current_val = params[param_to_mutate]
                std_dev = (max_val - min_val) * 0.1  # 10% del rango
                new_val = np.random.normal(current_val, std_dev)
                mutated_params[param_to_mutate] = np.clip(new_val, min_val, max_val)
        elif isinstance(param_range, list):
            mutated_params[param_to_mutate] = random.choice(param_range)
        
        return mutated_params
    
    def save_best_config(self, result: OptimizationResult, filepath: str):
        """Guarda la mejor configuración encontrada"""
        config = {
            'strategy_name': self.strategy_name,
            'best_parameters': result.parameters,
            'performance_metrics': {
                'win_rate': result.win_rate,
                'total_profit': result.total_profit,
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'avg_profit_per_trade': result.avg_profit_per_trade,
                'max_drawdown': result.max_drawdown,
                'fitness_score': result.fitness_score
            }
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Configuración guardada en: {filepath}")
