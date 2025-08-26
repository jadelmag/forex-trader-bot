# trading_rl_agent.py

import gym
from gym import spaces
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

class ForexTradingEnv(gym.Env):
    """
    Entorno de Reinforcement Learning para trading de Forex basado en velas.
    Observación: ventana de N velas
    Acción: 0 = mantener, 1 = comprar, 2 = vender
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, df: pd.DataFrame, window_size=20, initial_balance=10000):
        super().__init__()
        self.df = df.reset_index()
        self.window_size = window_size
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = 0  # 1 = comprado, -1 = vendido
        self.current_step = window_size
        self.total_steps = len(df)
        self.action_space = spaces.Discrete(3)  # mantener, comprar, vender
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(window_size, 5), dtype=np.float32
        )
    
    def reset(self):
        self.balance = self.initial_balance
        self.position = 0
        self.current_step = self.window_size
        return self._get_observation()
    
    def _get_observation(self):
        obs = self.df.iloc[self.current_step-self.window_size:self.current_step][['Open','High','Low','Close','Volume']].values
        return obs.astype(np.float32)
    
    def step(self, action):
        done = False
        reward = 0
        price = self.df['Close'].iloc[self.current_step]

        # Lógica simple de recompensas
        if action == 1:  # comprar
            if self.position == 0:
                self.position = 1
                self.entry_price = price
        elif action == 2:  # vender
            if self.position == 0:
                self.position = -1
                self.entry_price = price
        # Cierre de posición opuesta
        if self.position == 1 and action == 2:
            reward = price - self.entry_price
            self.balance += reward
            self.position = -1
            self.entry_price = price
        elif self.position == -1 and action == 1:
            reward = self.entry_price - price
            self.balance += reward
            self.position = 1
            self.entry_price = price
        
        self.current_step += 1
        if self.current_step >= self.total_steps:
            done = True
            # cerrar posición final
            if self.position == 1:
                reward += self.df['Close'].iloc[-1] - self.entry_price
            elif self.position == -1:
                reward += self.entry_price - self.df['Close'].iloc[-1]
            self.balance += reward

        return self._get_observation(), reward, done, {}
    
    def render(self, mode='human'):
        print(f'Step: {self.current_step}, Balance: {self.balance:.2f}, Position: {self.position}')


class ForexRLAgent:
    """
    Clase wrapper para entrenar y predecir señales de compra/venta
    """
    def __init__(self, df: pd.DataFrame, window_size=20, initial_balance=10000):
        self.env = ForexTradingEnv(df, window_size, initial_balance)
        self.model = PPO('MlpPolicy', self.env, verbose=1)
        self.df = df
        self.window_size = window_size
    
    def entrenar(self, total_timesteps=100000):
        """
        Entrena el agente con el entorno de velas
        """
        self.model.learn(total_timesteps=total_timesteps)
    
    def generar_senales(self):
        """
        Devuelve un array con las señales del agente sobre el dataframe:
        0 = mantener, 1 = comprar, 2 = vender
        """
        obs = self.env.reset()
        senales = []
        done = False
        while not done:
            action, _states = self.model.predict(obs, deterministic=True)
            senales.append(action)
            obs, _, done, _ = self.env.step(action)
        return np.array(senales)
