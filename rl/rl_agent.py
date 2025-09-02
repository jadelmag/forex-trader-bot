# rl/rl_agent.py

import os
import numpy as np
from typing import Callable, Optional, Dict, List
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from rl.rl_env import TradingEnv


class RLTradingAgent:
    def __init__(self, df, estrategias_fx: Dict, estrategias_candle: List, 
                 patrones: List, model_dir="models_rl", model_name="ppo_trading", 
                 log_fn: Optional[Callable[[str], None]] = None):
        """
        df: DataFrame de velas OHLC
        estrategias_fx: Dict con estrategias forex y parámetros
        estrategias_candle: Lista de estrategias de velas
        patrones: Lista de patrones de velas
        """
        self.df = df
        self.estrategias_fx = estrategias_fx or {}
        self.estrategias_candle = estrategias_candle or []
        self.patrones = patrones or []
        self.model_dir = model_dir
        self.model_name = model_name
        self._log_fn = log_fn
        self.model = None

        # Crear entorno con estrategias
        self.env = self._create_env()

        # Crear carpeta de modelos si no existe
        os.makedirs(self.model_dir, exist_ok=True)

    def _create_env(self):
        """Crea el entorno con las estrategias seleccionadas"""
        return DummyVecEnv([lambda: TradingEnv(
            self.df, 
            self.estrategias_fx,
            self.estrategias_candle,
            self.patrones
        )])

    def entrenar(self, timesteps=10000, progress_cb: Optional[Callable[[int, int], None]] = None):
        """
        Entrena el modelo PPO con las estrategias seleccionadas.
        """
        if self.model is None:
            self.model = PPO("MlpPolicy", self.env, verbose=0, 
                           learning_rate=0.0003, n_steps=2048, batch_size=64,
                           tensorboard_log="./tensorboard_logs/")
        
        self._log(f"🧠 ENTRENANDO MODELO RL con {timesteps} pasos...")
        self._log(f"📊 Estrategias FX: {list(self.estrategias_fx.keys())}")
        self._log(f"📊 Estrategias Candle: {self.estrategias_candle}")
        self._log(f"📊 Patrones: {self.patrones}")
        self._log(f"⚙️  Parámetros Riesgo/RR: {[(k, v['riesgo'], v['rr']) for k, v in self.estrategias_fx.items()]}")

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
                        outer_progress_cb(int(self.num_timesteps), int(self.total_steps))
                    except Exception:
                        pass
                    return True

            callback = _ProgressCB(timesteps)

        # Entrenar el modelo
        try:
            self.model.learn(total_timesteps=timesteps, callback=callback, reset_num_timesteps=False)
            self.guardar_modelo()
            self._log("✅ ENTRENAMIENTO RL COMPLETADO Y MODELO GUARDADO")
            return True
        except Exception as e:
            self._log(f"❌ ERROR en entrenamiento: {e}")
            return False

    def guardar_modelo(self):
        """Guarda el modelo entrenado en la carpeta especificada."""
        if self.model:
            save_path = os.path.join(self.model_dir, self.model_name)
            self.model.save(save_path)
            self._log(f"💾 Modelo guardado en {save_path}.zip")

    def cargar_modelo(self):
        """Carga el modelo entrenado desde disco."""
        load_path = os.path.join(self.model_dir, self.model_name)
        if os.path.exists(load_path + ".zip"):
            try:
                self.model = PPO.load(load_path, env=self.env)
                self._log(f"📂 Modelo cargado desde {load_path}")
                # Validar compatibilidad básica de espacios de observación
                try:
                    cur_dim = int(self.env.observation_space.shape[0]) if hasattr(self.env, 'observation_space') else None
                    # En DummyVecEnv, observation_space está envs[0].observation_space
                    if cur_dim is None and hasattr(self.env, 'envs') and self.env.envs:
                        cur_dim = int(getattr(self.env.envs[0], 'observation_space').shape[0])
                    model_dim = int(getattr(self.model, 'observation_space').shape[0]) if hasattr(self.model, 'observation_space') else None
                    if cur_dim is not None and model_dim is not None and cur_dim != model_dim:
                        self._log(f"⚠️ El espacio de observación actual ({cur_dim}) no coincide con el del modelo cargado ({model_dim}). Se entrenará un modelo nuevo.")
                        self.model = None
                        return False
                except Exception:
                    pass
                return True
            except Exception as e:
                # Manejar incompatibilidades (e.g., espacios de observación distintos)
                self._log(f"⚠️ No se pudo cargar el modelo existente debido a incompatibilidad: {e}. Se entrenará un modelo nuevo.")
                self.model = None
                return False
        self._log("⚠️ No se encontró un modelo previo, entrene primero.")
        return False

    def generar_senales(self):
        """
        Ejecuta el modelo sobre el dataset y devuelve señales de trading.
        0 = mantener, 1 = comprar, 2 = vender
        """
        if self.model is None:
            self._log("❌ Debe entrenar o cargar un modelo primero.")
            return []

        obs = self.env.reset()
        signals = []
        n = len(self.df)

        self._log(f"🔮 GENERANDO SEÑALES para {n} datos...")

        for i in range(n):
            action, _ = self.model.predict(obs, deterministic=True)
            try:
                act_scalar = int(action if np.isscalar(action) else action[0])
            except Exception:
                act_scalar = 0
            signals.append(act_scalar)

            try:
                step_action = [act_scalar]
                obs, rewards, dones, infos = self.env.step(step_action)
            except Exception:
                obs, rewards, dones, infos = self.env.step(act_scalar)

            try:
                done_flag = bool(dones[0]) if hasattr(dones, '__len__') else bool(dones)
            except Exception:
                done_flag = bool(dones)

            if done_flag and i < n - 1:
                signals.extend([0] * (n - len(signals)))
                break

        if len(signals) < n:
            signals.extend([0] * (n - len(signals)))
        elif len(signals) > n:
            signals = signals[:n]

        # Estadísticas de las señales
        compras = signals.count(1)
        ventas = signals.count(2)
        mantener = signals.count(0)
        self._log(f"📈 Señales generadas: COMPRAS={compras}, VENTAS={ventas}, MANTENER={mantener}")

        return signals

    def evaluar_rendimiento(self, signals):
        """Evalúa el rendimiento del modelo con las señales generadas"""
        if not signals:
            return {"error": "No hay señales para evaluar"}
        
        # Simular operaciones basadas en señales
        balance = 10000
        position = 0
        entry_price = 0
        operaciones = []
        ganancias_totales = 0
        operaciones_ganadas = 0
        operaciones_totales = 0

        for i, signal in enumerate(signals):
            if i >= len(self.df):
                break
                
            current_price = self.df.iloc[i]['Close']
            
            # Cerrar posición si existe y señal es contraria
            if position != 0 and signal != position:
                profit = (current_price - entry_price) if position == 1 else (entry_price - current_price)
                balance += profit
                ganancias_totales += profit
                operaciones_totales += 1
                if profit > 0:
                    operaciones_ganadas += 1
                
                operaciones.append({
                    'tipo': 'Cierre',
                    'precio': current_price,
                    'profit': profit,
                    'balance': balance,
                    'step': i
                })
                position = 0
                entry_price = 0
            
            # Abrir nueva posición
            if position == 0 and signal != 0:
                position = signal
                entry_price = current_price
                operaciones.append({
                    'tipo': 'Apertura',
                    'senal': signal,
                    'precio': entry_price,
                    'balance': balance,
                    'step': i
                })
        
        # Cerrar posición final si existe
        if position != 0 and len(self.df) > 0:
            current_price = self.df.iloc[-1]['Close']
            profit = (current_price - entry_price) if position == 1 else (entry_price - current_price)
            balance += profit
            ganancias_totales += profit
            operaciones_totales += 1
            if profit > 0:
                operaciones_ganadas += 1
            
            operaciones.append({
                'tipo': 'Cierre Final',
                'precio': current_price,
                'profit': profit,
                'balance': balance,
                'step': len(self.df) - 1
            })

        winrate = (operaciones_ganadas / operaciones_totales * 100) if operaciones_totales > 0 else 0
        
        return {
            'balance_final': balance,
            'ganancia_total': ganancias_totales,
            'operaciones_totales': operaciones_totales,
            'operaciones_ganadas': operaciones_ganadas,
            'operaciones_perdidas': operaciones_totales - operaciones_ganadas,
            'winrate': winrate,
            'operaciones': operaciones
        }

    def _log(self, msg: str):
        if self._log_fn is not None:
            try:
                self._log_fn(str(msg))
            except Exception:
                pass
        print(str(msg))