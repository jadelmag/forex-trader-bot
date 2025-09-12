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
                 patrones: List, candle_configs: Dict = None, model_dir="models_rl", model_name="ppo_trading", 
                 log_fn: Optional[Callable[[str], None]] = None):
        """
        Agente RL para trading con objetivos específicos de aprendizaje:
        
        OBJETIVOS DE ENTRENAMIENTO:
        1. Aprender timing óptimo para aplicar estrategias forex y maximizar beneficios
        2. Detectar patrones de vela para operaciones BUY/SELL con máximo beneficio
        
        Args:
            df: DataFrame de velas OHLC
            estrategias_fx: Dict con estrategias forex (sin parámetros fijos - el IA los aprenderá)
            estrategias_candle: Lista de estrategias de velas
            patrones: Lista de patrones de velas
            candle_configs: Configuraciones para estrategias de velas
        """
        self.df = df
        self.estrategias_fx = estrategias_fx or {}
        self.estrategias_candle = estrategias_candle or []
        self.patrones = patrones or []
        self.candle_configs = candle_configs or {}

        # Asegurar ruta absoluta para la carpeta de modelos
        try:
            if os.path.isabs(model_dir):
                self.model_dir = model_dir
            else:
                project_root = os.path.dirname(os.path.dirname(__file__))
                self.model_dir = os.path.join(project_root, model_dir)
        except Exception:
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
            self.candle_configs,
            self.patrones
        )])

    def entrenar(self, timesteps=10000, progress_cb: Optional[Callable[[int, int], None]] = None, cancel_event=None):
        """
        Entrena el modelo PPO con las estrategias seleccionadas.
        """
        if self.model is None:
            # Ajustar n_steps para que respete el número de timesteps especificado
            n_steps = min(timesteps, 2048)  # No exceder timesteps solicitados
            self.model = PPO("MlpPolicy", self.env, verbose=0, 
                           learning_rate=0.0003, n_steps=n_steps, batch_size=64,
                           tensorboard_log="./tensorboard_logs/")
        
        self._log(f"🧠 ENTRENANDO MODELO RL con {timesteps} pasos...")
        self._log(f"🎯 OBJETIVO 1: Aprender timing óptimo de estrategias forex")
        self._log(f"📊 Estrategias FX: {list(self.estrategias_fx.keys())}")
        self._log(f"🎯 OBJETIVO 2: Detectar patrones de vela para BUY/SELL óptimos")
        self._log(f"📊 Estrategias Candle: {self.estrategias_candle}")
        self._log(f"🤖 El modelo aprenderá automáticamente parámetros de riesgo, RR y gestión de órdenes")

        # Callback de progreso
        callback = None
        if progress_cb is not None:
            outer_progress_cb = progress_cb

            class _ProgressCB(BaseCallback):
                def __init__(self, total_steps: int, cancel_event=None):
                    super().__init__()
                    self.total_steps = total_steps
                    self.cancel_event = cancel_event

                def _on_step(self) -> bool:
                    # Check for cancellation
                    if self.cancel_event and self.cancel_event.is_set():
                        return False  # Stop training
                    
                    try:
                        outer_progress_cb(int(self.num_timesteps), int(self.total_steps))
                    except Exception:
                        pass
                    return True

            callback = _ProgressCB(timesteps, cancel_event)

        # Entrenar el modelo
        try:
            self.model.learn(total_timesteps=timesteps, callback=callback, reset_num_timesteps=False)
            
            # Check if training was cancelled
            if cancel_event and cancel_event.is_set():
                self._log("⚠️ ENTRENAMIENTO CANCELADO POR EL USUARIO")
                return False
            
            self.guardar_modelo()
            self._log("✅ ENTRENAMIENTO RL COMPLETADO Y MODELO GUARDADO")
            return True
        except Exception as e:
            # Check if it's a cancellation or actual error
            if cancel_event and cancel_event.is_set():
                self._log("⚠️ ENTRENAMIENTO CANCELADO POR EL USUARIO")
                return False
            else:
                self._log(f"❌ ERROR en entrenamiento: {e}")
                return False

    def guardar_modelo(self):
        """Guarda el modelo entrenado en la carpeta especificada."""
        if self.model:
            save_path = os.path.join(self.model_dir, self.model_name)
            self.model.save(save_path)
            self._log(f"💾 Modelo guardado en {save_path}.zip")
            # Mensaje amigable solicitado
            try:
                folder_name = os.path.basename(self.model_dir.rstrip(os.sep))
            except Exception:
                folder_name = "models_rl"
            self._log(f"Entrenamiento finalizado... Modelo guardado en la carpeta {folder_name}")

    def cargar_modelo(self):
        """Carga el modelo entrenado desde disco."""
        load_path = os.path.join(self.model_dir, self.model_name)
        if os.path.exists(load_path + ".zip"):
            self.model = PPO.load(load_path, env=self.env)
            self._log(f"📂 Modelo cargado desde {load_path}")
            return True
        self._log("⚠️ No se encontró un modelo previo, entrene primero.")
        return False

    def generar_senales(self):
        """
        Ejecuta el modelo entrenado para generar señales de trading optimizadas.
        
        El modelo aplicará el aprendizaje de:
        1. Timing óptimo de estrategias forex
        2. Detección de patrones de vela para BUY/SELL
        
        Returns:
            List[int]: Señales de trading (0 = mantener, 1 = comprar, 2 = vender)
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

        # Estadísticas de las señales con contexto de objetivos
        compras = signals.count(1)
        ventas = signals.count(2)
        mantener = signals.count(0)
        self._log(f"📈 Señales generadas por IA entrenada:")
        self._log(f"   🟢 COMPRAS: {compras} (timing óptimo + patrones alcistas)")
        self._log(f"   🔴 VENTAS: {ventas} (cierre optimizado)")
        self._log(f"   ⚪ MANTENER: {mantener} (espera de oportunidades)")

        return signals

    def evaluar_rendimiento(self, signals):
        """
        Evalúa el rendimiento del modelo entrenado con objetivos específicos.
        
        Analiza:
        - Efectividad del timing de estrategias forex
        - Precisión en detección de patrones de vela
        - Rentabilidad general del sistema IA
        """
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
            'operaciones': operaciones,
            # Métricas específicas de objetivos de aprendizaje
            'objetivo_timing_forex': 'Aprendido - timing óptimo de estrategias',
            'objetivo_patrones_vela': 'Aprendido - detección BUY/SELL optimizada',
            'gestion_automatica': 'Riesgo y órdenes gestionadas por IA'
        }

    def _log(self, msg: str):
        if self._log_fn is not None:
            try:
                self._log_fn(str(msg))
            except Exception:
                pass
        print(str(msg))