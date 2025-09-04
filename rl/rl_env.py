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
    Entorno RL para trading con estrategias y ventana dinámica de velas.
    Observaciones: [OHLCV normalizados] + [señales de estrategias] para las últimas `window_size` velas.
    Acciones: 0 = Mantener, 1 = Comprar, 2 = Vender
    """

    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame,
        estrategias_fx: dict = None,
        estrategias_candle: list = None,
        patrones: list = None,
        initial_balance: float = 10000,
        window_size: int = DEFAULT_WINDOW_SIZE,
    ):
        super(TradingEnv, self).__init__()

        self.df = df.reset_index(drop=True).copy()
        self.estrategias_fx = estrategias_fx or {}
        self.estrategias_candle = estrategias_candle or []
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

        # Agregar señales de estrategias FX
        for estrategia, params in self.estrategias_fx.items():
            try:
                metodo = getattr(self.fx_strategies, estrategia)
                risk_kwargs = {
                    "risk_per_trade": params.get("riesgo", 0.01),
                    "rr_ratio": params.get("rr", 2.0),
                }
                df_res = metodo(**risk_kwargs)
                signal = df_res.iloc[self.current_step]["Signal"] if self.current_step < len(df_res) else 0
                obs.append(float(signal))
            except Exception:
                obs.append(0.0)

        # Señales de estrategias Candle
        for estrategia in self.estrategias_candle:
            try:
                metodo = getattr(self.candle_strategies, estrategia)
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
        return self._get_observation(), {}

    def step(self, action):
        done = False
        reward = 0
        profit = 0
        row = self.df.iloc[self.current_step]
        price = row["Close"]

        # Acción
        if action == 1:  # Comprar
            if self.position == 0:
                self.position = 1
                self.entry_price = price
                self.total_operations += 1
                reward = -0.001  # penalización por entrar

        elif action == 2:  # Vender
            if self.position == 1:
                profit = price - self.entry_price
                reward = profit / self.entry_price
                self.balance += profit
                if profit > 0:
                    self.winning_operations += 1
                self.position = 0
                self.entry_price = 0

        # Avanzar paso
        self.current_step += 1
        if self.current_step >= self.n_steps - 1:
            done = True

        # Penalizar si queda posición abierta al final
        if done and self.position == 1:
            profit = price - self.entry_price
            reward = profit / self.entry_price - 0.05
            self.balance += profit
            if profit > 0:
                self.winning_operations += 1
            self.position = 0

        obs = self._get_observation()
        info = {
            "balance": self.balance,
            "step": self.current_step,
            "position": self.position,
            "profit": profit,
            "total_operations": self.total_operations,
            "winning_operations": self.winning_operations,
            "winrate": (self.winning_operations / self.total_operations * 100) if self.total_operations > 0 else 0
        }

        return obs, reward, done, False, info

    def render(self, mode="human"):
        winrate = (self.winning_operations / self.total_operations * 100) if self.total_operations > 0 else 0
        print(
            f"Step: {self.current_step}, Balance: {self.balance:.2f}, "
            f"Posición: {self.position}, Operaciones: {self.total_operations}, "
            f"WinRate: {winrate:.1f}%"
        )
