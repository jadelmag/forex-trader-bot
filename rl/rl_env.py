# rl/rl_env.py

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from strategies import ForexStrategies, CandleStrategies
from patterns.candlestickpatterns import CandlestickPatterns

DEFAULT_WINDOW_SIZE = 1000

class TradingEnv(gym.Env):
    """
    Entorno RL para trading con objetivos específicos de aprendizaje:
    
    OBJETIVOS DE ENTRENAMIENTO:
    1. Aprender el timing óptimo para aplicar cada estrategia forex y maximizar beneficios
    2. Detectar patrones de vela para abrir operaciones BUY y SELL con máximo beneficio
    
    Observaciones: [OHLCV normalizados] + [señales de estrategias] + [contexto de mercado]
    Acciones: 0 = Mantener, 1 = Comprar, 2 = Vender
    
    El modelo aprenderá:
    - Cuándo aplicar cada estrategia forex para obtener mayor rentabilidad
    - Cómo detectar patrones de vela optimales para operaciones al alza y a la baja
    - Gestión automática de riesgo y número de operaciones simultáneas
    """

    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame,
        estrategias_fx: dict = None,
        estrategias_candle: list = None,
        candle_configs: dict = None,
        patrones: list = None,
        initial_balance: float = 10000,
        window_size: int = DEFAULT_WINDOW_SIZE,
    ):
        super(TradingEnv, self).__init__()

        self.df = df.reset_index(drop=True).copy()
        self.estrategias_fx = estrategias_fx or {}
        self.estrategias_candle = estrategias_candle or []
        self.candle_configs = candle_configs or {}
        self.patrones = patrones or []
        self.n_steps = len(self.df)
        self.current_step = 0
        self.window_size = window_size
        self.features_per_vela = 5  # OHLCV normalizado

        # Inicializar estrategias
        self.fx_strategies = ForexStrategies(self.df)
        self.candle_strategies = CandleStrategies(self.df)
        self.pattern_detector = CandlestickPatterns(self.df)

        # Balance inicial
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = 0
        self.entry_price = 0
        self.total_operations = 0
        self.winning_operations = 0
        
        # Métricas específicas para objetivos de aprendizaje
        self.forex_strategy_profits = {strategy: 0.0 for strategy in self.estrategias_fx.keys()}
        self.candle_pattern_profits = {pattern: 0.0 for pattern in self.estrategias_candle + self.patrones}
        self.strategy_timing_rewards = {strategy: [] for strategy in self.estrategias_fx.keys()}
        self.pattern_detection_rewards = {pattern: [] for pattern in self.estrategias_candle + self.patrones}
        
        # Tracking para aprendizaje de timing óptimo
        self.last_strategy_signals = {strategy: 0 for strategy in self.estrategias_fx.keys()}
        self.last_pattern_signals = {pattern: 0 for pattern in self.estrategias_candle + self.patrones}
        self.strategy_entry_steps = {}
        self.pattern_entry_steps = {}

        # Número total de señales
        self.num_strategy_signals = (
            len(self.estrategias_fx)
            + len(self.estrategias_candle)
            + len(self.patrones)
        )

        # Espacio de observación: ventana * OHLCV + señales
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.window_size * self.features_per_vela + self.num_strategy_signals,),
            dtype=np.float32,
        )

        # Espacio de acción: Mantener / Comprar / Vender
        self.action_space = spaces.Discrete(3)

    def _get_observation(self):
        # Determinar ventana de datos
        start = max(0, self.current_step - self.window_size + 1)
        end = self.current_step + 1
        df_window = self.df.iloc[start:end]

        # Construir matriz OHLCV normalizada
        obs_window = []
        for _, row in df_window.iterrows():
            obs_window.append([
                row["Open"] / row["Close"],
                row["High"] / row["Close"],
                row["Low"] / row["Close"],
                1.0,  # Close/Close = 1
                row["Volume"] / row["Close"] if row["Volume"] != 0 else 0
            ])
        obs_window = np.array(obs_window, dtype=np.float32).flatten()

        # Rellenar con ceros si la ventana es menor que window_size
        obs_size = self.window_size * self.features_per_vela
        if len(obs_window) < obs_size:
            obs_padded = np.zeros(obs_size, dtype=np.float32)
            obs_padded[-len(obs_window):] = obs_window
            obs_window = obs_padded

        obs = obs_window.tolist()

        # Agregar señales de estrategias FX (sin parámetros fijos - el IA los aprenderá)
        for estrategia, params in self.estrategias_fx.items():
            try:
                metodo = getattr(self.fx_strategies, estrategia)
                # El modelo RL aprenderá los parámetros óptimos de riesgo y RR
                df_res = metodo()
                signal = df_res.iloc[self.current_step]["Signal"] if self.current_step < len(df_res) else 0
                obs.append(float(signal))
            except Exception:
                obs.append(0.0)

        # Señales de estrategias Candle
        for estrategia in self.estrategias_candle:
            try:
                metodo = getattr(self.candle_strategies, estrategia)
                # Si hay configuración para esta estrategia, intentar pasarla
                cfg = self.candle_configs.get(estrategia)
                try:
                    if cfg is not None:
                        df_res = metodo(config=cfg)
                    else:
                        df_res = metodo()
                except TypeError:
                    df_res = metodo()
                signal = df_res.iloc[self.current_step]["Signal"] if self.current_step < len(df_res) else 0
                obs.append(float(signal))
            except Exception:
                obs.append(0.0)

        # Señales de patrones
        for patron in self.patrones:
            try:
                metodo = getattr(self.pattern_detector, patron)
                df_res = metodo()
                signal = df_res.iloc[self.current_step]["Signal"] if self.current_step < len(df_res) else 0
                obs.append(float(signal))
            except Exception:
                obs.append(0.0)

        return np.array(obs, dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        self.total_operations = 0
        self.winning_operations = 0
        
        # Reset métricas de aprendizaje
        self.forex_strategy_profits = {strategy: 0.0 for strategy in self.estrategias_fx.keys()}
        self.candle_pattern_profits = {pattern: 0.0 for pattern in self.estrategias_candle + self.patrones}
        self.strategy_timing_rewards = {strategy: [] for strategy in self.estrategias_fx.keys()}
        self.pattern_detection_rewards = {pattern: [] for pattern in self.estrategias_candle + self.patrones}
        self.last_strategy_signals = {strategy: 0 for strategy in self.estrategias_fx.keys()}
        self.last_pattern_signals = {pattern: 0 for pattern in self.estrategias_candle + self.patrones}
        self.strategy_entry_steps = {}
        self.pattern_entry_steps = {}
        
        return self._get_observation(), {}

    def step(self, action):
        done = False
        reward = 0
        profit = 0
        row = self.df.iloc[self.current_step]
        price = row["Close"]
        
        # Calcular reward basado en objetivos de aprendizaje
        timing_reward = self._calculate_timing_reward()
        pattern_detection_reward = self._calculate_pattern_detection_reward()

        # Acción
        if action == 1:  # Comprar
            if self.position == 0:
                self.position = 1
                self.entry_price = price
                self.total_operations += 1
                
                # Reward por timing óptimo de estrategias
                reward += timing_reward
                # Reward por detección correcta de patrones
                reward += pattern_detection_reward
                # Pequeña penalización por entrar (costo de transacción)
                reward -= 0.001
                
                # Registrar entrada para tracking de timing
                self._register_entry_timing()

        elif action == 2:  # Vender
            if self.position == 1:
                profit = price - self.entry_price
                base_reward = profit / self.entry_price if self.entry_price > 0 else 0
                
                # Reward mejorado basado en objetivos de aprendizaje
                strategy_bonus = self._calculate_strategy_success_bonus(profit)
                pattern_bonus = self._calculate_pattern_success_bonus(profit)
                
                reward = base_reward + strategy_bonus + pattern_bonus
                
                self.balance += profit
                if profit > 0:
                    self.winning_operations += 1
                    
                # Actualizar métricas de aprendizaje
                self._update_learning_metrics(profit)
                
                self.position = 0
                self.entry_price = 0

        # Avanzar paso
        self.current_step += 1
        if self.current_step >= self.n_steps - 1:
            done = True

        # Penalizar si queda posición abierta al final
        if done and self.position == 1:
            profit = price - self.entry_price
            base_reward = profit / self.entry_price if self.entry_price > 0 else 0
            reward = base_reward - 0.05  # Penalización por no cerrar
            self.balance += profit
            if profit > 0:
                self.winning_operations += 1
            self._update_learning_metrics(profit)
            self.position = 0

        obs = self._get_observation()
        info = {
            "balance": self.balance,
            "step": self.current_step,
            "position": self.position,
            "profit": profit,
            "total_operations": self.total_operations,
            "winning_operations": self.winning_operations,
            "winrate": (self.winning_operations / self.total_operations * 100) if self.total_operations > 0 else 0,
            "timing_reward": timing_reward,
            "pattern_reward": pattern_detection_reward,
            "forex_profits": self.forex_strategy_profits,
            "pattern_profits": self.candle_pattern_profits
        }

        return obs, reward, done, False, info

    def _calculate_timing_reward(self):
        """
        OBJETIVO 1: Calcular reward por timing óptimo de estrategias forex
        Premia cuando las señales de estrategias forex están alineadas positivamente
        """
        timing_reward = 0.0
        
        for estrategia, params in self.estrategias_fx.items():
            try:
                metodo = getattr(self.fx_strategies, estrategia)
                df_res = metodo()
                current_signal = df_res.iloc[self.current_step]["Signal"] if self.current_step < len(df_res) else 0
                
                # Reward por señal de compra fuerte
                if current_signal > 0:
                    timing_reward += current_signal * 0.1  # Reward proporcional a la fuerza de la señal
                    
                # Bonus por consistencia de señal
                prev_signal = self.last_strategy_signals.get(estrategia, 0)
                if current_signal > 0 and prev_signal > 0:
                    timing_reward += 0.05  # Bonus por señal consistente
                    
                self.last_strategy_signals[estrategia] = current_signal
                
            except Exception:
                pass
                
        return timing_reward
    
    def _calculate_pattern_detection_reward(self):
        """
        OBJETIVO 2: Calcular reward por detección correcta de patrones de vela
        Premia cuando los patrones indican oportunidades BUY/SELL óptimas
        """
        pattern_reward = 0.0
        
        # Reward por estrategias de velas
        for estrategia in self.estrategias_candle:
            try:
                metodo = getattr(self.candle_strategies, estrategia)
                cfg = self.candle_configs.get(estrategia)
                if cfg is not None:
                    df_res = metodo(config=cfg)
                else:
                    df_res = metodo()
                    
                current_signal = df_res.iloc[self.current_step]["Signal"] if self.current_step < len(df_res) else 0
                
                # Reward por detección de patrones alcistas
                if current_signal > 0:
                    pattern_reward += current_signal * 0.15
                    
                # Reward por detección de patrones bajistas (para SELL futuro)
                elif current_signal < 0:
                    pattern_reward += abs(current_signal) * 0.1
                    
                self.last_pattern_signals[estrategia] = current_signal
                
            except Exception:
                pass
        
        # Reward por patrones de velas clásicos
        for patron in self.patrones:
            try:
                metodo = getattr(self.pattern_detector, patron)
                df_res = metodo()
                current_signal = df_res.iloc[self.current_step]["Signal"] if self.current_step < len(df_res) else 0
                
                if current_signal != 0:
                    pattern_reward += abs(current_signal) * 0.12
                    
                self.last_pattern_signals[patron] = current_signal
                
            except Exception:
                pass
                
        return pattern_reward
    
    def _register_entry_timing(self):
        """
        Registra el momento de entrada para evaluar el timing de estrategias
        """
        # Registrar qué estrategias tenían señales positivas al entrar
        for estrategia, signal in self.last_strategy_signals.items():
            if signal > 0:
                self.strategy_entry_steps[estrategia] = self.current_step
                
        for pattern, signal in self.last_pattern_signals.items():
            if signal != 0:
                self.pattern_entry_steps[pattern] = self.current_step
    
    def _calculate_strategy_success_bonus(self, profit):
        """
        Calcula bonus basado en el éxito de las estrategias forex que predijeron la entrada
        """
        bonus = 0.0
        
        if profit > 0:  # Solo dar bonus si la operación fue exitosa
            for estrategia, entry_step in self.strategy_entry_steps.items():
                if entry_step is not None:
                    # Bonus por estrategia que predijo correctamente
                    bonus += 0.2
                    # Actualizar profits de la estrategia
                    self.forex_strategy_profits[estrategia] += profit
                    
        return bonus
    
    def _calculate_pattern_success_bonus(self, profit):
        """
        Calcula bonus basado en el éxito de los patrones que predijeron la entrada
        """
        bonus = 0.0
        
        if profit > 0:  # Solo dar bonus si la operación fue exitosa
            for pattern, entry_step in self.pattern_entry_steps.items():
                if entry_step is not None:
                    # Bonus por patrón que predijo correctamente
                    bonus += 0.15
                    # Actualizar profits del patrón
                    self.candle_pattern_profits[pattern] += profit
                    
        return bonus
    
    def _update_learning_metrics(self, profit):
        """
        Actualiza las métricas de aprendizaje después de cerrar una operación
        """
        # Actualizar rewards de timing para estrategias activas
        for estrategia, entry_step in self.strategy_entry_steps.items():
            if entry_step is not None:
                timing_reward = profit / self.entry_price if self.entry_price > 0 else 0
                self.strategy_timing_rewards[estrategia].append(timing_reward)
                
        # Actualizar rewards de detección para patrones activos
        for pattern, entry_step in self.pattern_entry_steps.items():
            if entry_step is not None:
                detection_reward = profit / self.entry_price if self.entry_price > 0 else 0
                self.pattern_detection_rewards[pattern].append(detection_reward)
                
        # Reset entry steps para próxima operación
        self.strategy_entry_steps = {}
        self.pattern_entry_steps = {}

    def render(self, mode="human"):
        winrate = (self.winning_operations / self.total_operations * 100) if self.total_operations > 0 else 0
        print(
            f"Step: {self.current_step}, Balance: {self.balance:.2f}, "
            f"Posición: {self.position}, Operaciones: {self.total_operations}, "
            f"WinRate: {winrate:.1f}%"
        )
        
        # Mostrar métricas de aprendizaje
        if self.forex_strategy_profits:
            print(f"Forex Strategy Profits: {self.forex_strategy_profits}")
        if self.candle_pattern_profits:
            print(f"Pattern Profits: {self.candle_pattern_profits}")
