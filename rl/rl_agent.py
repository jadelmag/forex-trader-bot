# rl/rl_agent.py

import os
import numpy as np
from typing import Callable, Optional
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from rl.rl_env import TradingEnv


class RLTradingAgent:
    def __init__(self, df, model_dir="models_rl", model_name="ppo_trading", log_fn: Optional[Callable[[str], None]] = None):
        """
        df: DataFrame de velas OHLC
        model_dir: carpeta donde se guardan los modelos
        model_name: nombre base del modelo
        """
        self.df = df
        self.model_dir = model_dir
        self.model_name = model_name
        self.env = DummyVecEnv([lambda: TradingEnv(self.df)])
        self.model = None
        self._log_fn = log_fn

        # Crear carpeta de modelos si no existe
        os.makedirs(self.model_dir, exist_ok=True)

    def entrenar(self, timesteps=10_000, progress_cb: Optional[Callable[[int, int], None]] = None):
        """
        Entrena el modelo PPO y lo guarda en disco.
        """
        if self.model is None:
            # verbose=0 para evitar spam por stdout; dirigiremos mensajes al log_fn
            self.model = PPO("MlpPolicy", self.env, verbose=0)
        self._log(f"Entrenando por {timesteps} pasos...")

        # Callback de progreso
        callback = None
        if progress_cb is not None:
            outer_progress_cb = progress_cb

            class _ProgressCB(BaseCallback):
                def __init__(self, total_steps: int):
                    super().__init__()
                    self.total_steps = total_steps

                def _on_step(self) -> bool:
                    try:
                        # self.num_timesteps es provisto por BaseCallback
                        outer_progress_cb(int(self.num_timesteps), int(self.total_steps))
                    except Exception:
                        pass
                    return True

            callback = _ProgressCB(timesteps)

        self.model.learn(total_timesteps=timesteps, callback=callback)
        self.guardar_modelo()
        self._log("Entrenamiento finalizado y modelo guardado.")

    def guardar_modelo(self):
        """Guarda el modelo entrenado en la carpeta especificada."""
        if self.model:
            save_path = os.path.join(self.model_dir, self.model_name)
            self.model.save(save_path)
            self._log(f"Modelo guardado en {save_path}")

    def cargar_modelo(self):
        """Carga el modelo entrenado desde disco."""
        load_path = os.path.join(self.model_dir, self.model_name)
        if os.path.exists(load_path + ".zip"):
            self.model = PPO.load(load_path, env=self.env)
            self._log(f"Modelo cargado desde {load_path}")
            return True
        self._log("No se encontró un modelo previo, entrene primero.")
        return False

    def generar_senales(self):
        """
        Ejecuta el modelo sobre el dataset y devuelve señales de trading.
        0 = mantener, 1 = comprar, 2 = vender
        """
        if self.model is None:
            self._log("Debe entrenar o cargar un modelo primero.")
            return []

        obs = self.env.reset()
        done = False
        señales = []
        i = 0

        while not done and i < len(self.df) - 1:
            action, _ = self.model.predict(obs, deterministic=True)
            señales.append(int(action))
            obs, _, done, _ = self.env.step(action)
            i += 1

        return señales

    # ---------------- Utilidades ----------------
    def _log(self, msg: str):
        if self._log_fn is not None:
            try:
                self._log_fn(str(msg))
                return
            except Exception:
                pass
        # fallback
        print(str(msg))
