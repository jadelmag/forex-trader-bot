import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd


class TradingEnv(gym.Env):
    """
    Entorno RL para trading con velas OHLC.
    Observaciones: [Open, High, Low, Close, Volumen normalizados]
    Acciones: 0 = Mantener, 1 = Comprar, 2 = Vender
    """

    metadata = {"render.modes": ["human"]}

    def __init__(self, df: pd.DataFrame, initial_balance: float = 10000):
        super(TradingEnv, self).__init__()

        # Guardar dataset
        self.df = df.reset_index(drop=True).copy()
        self.n_steps = len(self.df)
        self.current_step = 0

        # Balance inicial
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = 0  # 0 = sin posición, >0 = comprado
        self.entry_price = 0

        # Espacio de observación: OHLCV normalizados
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32
        )

        # Espacio de acción: Mantener / Comprar / Vender
        self.action_space = spaces.Discrete(3)

    def _get_observation(self):
        row = self.df.iloc[self.current_step]
        obs = np.array(
            [
                row["Open"],
                row["High"],
                row["Low"],
                row["Close"],
                row["Volume"],
            ],
            dtype=np.float32,
        )

        # Normalización (opcional: aquí solo escalamos por precio Close)
        obs = obs / row["Close"]
        return obs

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        return self._get_observation(), {}

    def step(self, action):
        done = False
        reward = 0

        row = self.df.iloc[self.current_step]
        price = row["Close"]

        # Acción
        if action == 1:  # Comprar
            if self.position == 0:
                self.position = 1
                self.entry_price = price

        elif action == 2:  # Vender
            if self.position == 1:
                reward = price - self.entry_price
                self.balance += reward
                self.position = 0
                self.entry_price = 0

        # Avanzamos paso
        self.current_step += 1
        if self.current_step >= self.n_steps - 1:
            done = True

        # Penalizar si se queda con posición abierta al final
        if done and self.position == 1:
            reward -= abs(price - self.entry_price)
            self.position = 0

        obs = self._get_observation()
        info = {"balance": self.balance}
        return obs, reward, done, False, info

    def render(self, mode="human"):
        print(
            f"Step: {self.current_step}, Balance: {self.balance:.2f}, Posición: {self.position}"
        )
