# app/ai_trainer.py

import threading
import time
import random
import copy
import os
import json
from typing import Callable, Dict, List, Optional
import numpy as np
import pandas as pd

from strategies import ForexStrategies, CandleStrategies
from strategies.risk_manager import RiskManager, RiskManagerIntegration
from rl.rl_agent import RLTradingAgent


class AITrainer:
    """
    Ejecuta el entrenamiento de IA con aprendizaje por refuerzo.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        seleccion_fx: Dict[str, Dict],
        seleccion_patterns: List[str],
        seleccion_candle: List[str],
        max_orders: int,
        capital_inicial: float,
        use_winrate: bool,
        winrate_target: float,
        max_attempts: int = 0,
        seed: Optional[int] = None,
        save_best: bool = True,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_finish: Optional[Callable[[Dict], None]] = None,
    ):
        self.df = df
        self.seleccion_fx = seleccion_fx or {}
        self.seleccion_patterns = seleccion_patterns or []
        self.seleccion_candle = seleccion_candle or []
        self._current_fx = copy.deepcopy(self.seleccion_fx)
        self._current_patterns = list(self.seleccion_patterns)
        self._current_candle = list(self.seleccion_candle)
        self.max_orders = max_orders
        self.capital_inicial = capital_inicial
        self.use_winrate = use_winrate
        self.winrate_target = float(winrate_target or 0.0)
        self.max_attempts = int(max_attempts or 0)
        self.seed = seed
        self.save_best = bool(save_best)
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_finish = on_finish
        self._thread: Optional[threading.Thread] = None
        self._stop = False

        # Risk Manager
        self.risk_manager = RiskManager(max_operaciones_activas=self.max_orders, capital_inicial=self.capital_inicial)
        self.risk_integration = RiskManagerIntegration(self.risk_manager, None)

        # Estrategias auxiliares
        self.fx = ForexStrategies(self.df)
        self.candle = CandleStrategies(self.df)

        # Tracking del mejor resultado
        self._best_stats: Optional[Dict] = None
        self._best_fx: Dict[str, Dict] = copy.deepcopy(self._current_fx)
        self._best_patterns: List[str] = list(self._current_patterns)
        self._best_candle: List[str] = list(self._current_candle)
        self._best_model_path: Optional[str] = None

        # Agente RL
        self.rl_agent = None
        self._initialize_rl_agent()

        # Track de operaciones
        self.operaciones_track = []
        self.estadisticas_por_estrategia = {}
        self.mejor_configuracion = None

    def _initialize_rl_agent(self):
        """Inicializa el agente RL con las estrategias actuales"""
        self.rl_agent = RLTradingAgent(
            self.df,
            self._current_fx,
            self._current_candle,
            self._current_patterns,
            log_fn=lambda m: self._emit_log(m, 'cyan')
        )

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True

    def _emit_log(self, msg: str, color: str = "white"):
        if self.on_log:
            try:
                self.on_log(str(msg), color)
            except Exception:
                pass

    def _emit_progress(self, cur: int, total: int):
        if self.on_progress:
            try:
                self.on_progress(int(cur), int(total))
            except Exception:
                pass

    def _emit_finish(self, stats: Dict):
        if self.on_finish:
            try:
                self.on_finish(stats)
            except Exception:
                pass

    def _entrenar_modelo_rl(self, timesteps=5000):
        """Entrena el modelo RL con las estrategias actuales"""
        self._emit_log("🎯 INICIANDO ENTRENAMIENTO RL CON ESTRATEGIAS", 'green')
        self._emit_log(f"📊 Estrategias FX: {list(self._current_fx.keys())}", 'white')
        self._emit_log(f"📊 Estrategias Candle: {self._current_candle}", 'white')
        self._emit_log(f"📊 Patrones: {self._current_patterns}", 'white')
        params_list = [(k, f"riesgo={v['riesgo']:.3f}, rr={v['rr']:.2f}") for k, v in self._current_fx.items()]
        self._emit_log(f"⚙️  Parámetros: {params_list}", 'white')
        
        # Recrear entorno con estrategias actuales
        self.rl_agent.estrategias_fx = self._current_fx
        self.rl_agent.estrategias_candle = self._current_candle
        self.rl_agent.patrones = self._current_patterns
        self.rl_agent.env = self.rl_agent._create_env()
        
        # Entrenar modelo
        success = self.rl_agent.entrenar(timesteps=timesteps, progress_cb=lambda cur, total: self._emit_progress(cur, total))
        if success:
            self._emit_log("✅ ENTRENAMIENTO RL COMPLETADO", 'green')
        else:
            self._emit_log("❌ FALLO EN ENTRENAMIENTO RL", 'red')
        
        return success

    def _generate_signals_from_rl(self):
        """Genera señales usando el modelo RL entrenado"""
        self._emit_log("🔮 GENERANDO SEÑALES CON MODELO RL ENTRENADO", 'cyan')
        
        # Generar señales con el modelo RL
        signals = self.rl_agent.generar_senales()
        
        # Crear DataFrame con las señales
        df_signals = self.df.copy()
        df_signals['RL_Signal'] = signals
        
        # Añadir ATR para gestión de riesgo
        df_signals['ATR'] = (df_signals['High'] - df_signals['Low']).rolling(14).mean()
        df_signals['ATR'] = df_signals['ATR'].fillna(df_signals['ATR'].mean())
        
        return df_signals

    def _mutate_configs(self, last_winrate: float):
        """Ajusta parámetros y estrategias para el siguiente intento"""
        # Mutar estrategias forex
        for nombre, params in self._current_fx.items():
            riesgo = float(params.get('riesgo', 0.01))
            rr = float(params.get('rr', 2.0))
            
            # Guía por rendimiento
            if last_winrate < max(30.0, self.winrate_target * 0.6):
                riesgo *= 0.9  # bajar riesgo
                rr *= 1.05     # subir RR
            elif last_winrate < self.winrate_target:
                riesgo *= 0.95
                rr *= 1.02
            
            # Pequeñas mutaciones aleatorias
            riesgo *= random.uniform(0.9, 1.1)
            rr *= random.uniform(0.95, 1.1)
            
            # Limitar rangos razonables
            riesgo = min(max(riesgo, 0.001), 0.05)
            rr = min(max(rr, 1.0), 5.0)
            
            params['riesgo'] = riesgo
            params['rr'] = rr

        # Mutar estrategias candle
        base_candle = set(self.seleccion_candle)
        cur_candle = set(self._current_candle)
        if base_candle:
            if random.random() < 0.2 and len(cur_candle) > 0:
                cur_candle.remove(random.choice(list(cur_candle)))
            if random.random() < 0.3 and len(cur_candle) < len(base_candle):
                restantes = list(base_candle - cur_candle)
                if restantes:
                    cur_candle.add(random.choice(restantes))
        self._current_candle = list(cur_candle)

        # Mutar patrones
        base_patterns = set(self.seleccion_patterns)
        cur_set = set(self._current_patterns)
        if base_patterns:
            if random.random() < 0.25 and len(cur_set) > 0:
                cur_set.remove(random.choice(list(cur_set)))
            if random.random() < 0.35 and len(cur_set) < len(base_patterns):
                restantes = list(base_patterns - cur_set)
                if restantes:
                    cur_set.add(random.choice(restantes))
        self._current_patterns = list(cur_set)

        riesgos_list = [(k, f"{v['riesgo']:.3f}") for k, v in self._current_fx.items()]
        self._emit_log(f"🔄 Configuración mutada - Riesgos: {riesgos_list}", 'yellow')

    def _save_best_configuration(self, stats: Dict, attempt: int):
        """Guarda la mejor configuración encontrada"""
        if not self.save_best:
            return

        try:
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            ts = int(time.time())
            
            data = {
                'timestamp': ts,
                'attempt': attempt,
                'stats': stats,
                'fx': self._best_fx,
                'candle_strategies': self._best_candle,
                'patterns': self._best_patterns,
                'winrate_target': self.winrate_target,
                'max_attempts': self.max_attempts,
                'capital_inicial': self.capital_inicial,
                'max_orders': self.max_orders,
                'use_winrate': self.use_winrate,
            }
            
            out_path = os.path.join(logs_dir, f'best_config_{ts}.json')
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._emit_log(f"💾 Mejor configuración guardada en: {out_path}", 'cyan')
            
            # Guardar también el modelo RL si es el mejor
            if self.rl_agent and hasattr(self.rl_agent, 'guardar_modelo'):
                model_save_path = os.path.join(logs_dir, f'best_model_{ts}')
                self.rl_agent.model.save(model_save_path)
                self._emit_log(f"🤖 Mejor modelo guardado en: {model_save_path}.zip", 'cyan')
                
        except Exception as e:
            self._emit_log(f"❌ No se pudo guardar la mejor configuración: {e}", 'red')

    def _run(self):
        try:
            attempt = 1
            reached_winrate_target = False
            
            while not self._stop:
                # Respetar límite de intentos
                if self.max_attempts > 0 and attempt > self.max_attempts:
                    self._emit_log(f"⏹️ Máximo de intentos alcanzado: {self.max_attempts}. Finalizando.", 'yellow')
                    break

                # Semilla por intento
                if self.seed is not None:
                    try:
                        random.seed(self.seed + attempt - 1)
                        np.random.seed(self.seed + attempt - 1)
                        self._emit_log(f"🌱 Semilla para intento {attempt}: {self.seed + attempt - 1}", 'white')
                    except Exception:
                        pass

                # 1. ENTRENAR MODELO RL
                if not self._entrenar_modelo_rl(timesteps=3000):
                    self._emit_log("❌ Fallo en entrenamiento RL, saltando intento...", 'red')
                    attempt += 1
                    continue

                # 2. GENERAR SEÑALES
                df_work = self._generate_signals_from_rl()
                total_rows = len(df_work)

                self._emit_log(f"🚀 INICIO BACKTESTING (intento {attempt})", 'green')
                if self.use_winrate:
                    try:
                        fx_resumen = ", ".join([f"{k}(riesgo={v.get('riesgo',0.01):.3f}, rr={v.get('rr',2.0):.2f})" for k,v in self._current_fx.items()]) or "-"
                        candle_resumen = ", ".join(self._current_candle) or "-"
                        patt_resumen = ", ".join(self._current_patterns) or "-"
                        self._emit_log(f"🔧 Config actual -> FX: {fx_resumen}", 'white')
                        self._emit_log(f"🔧 Candle: {candle_resumen}", 'white')
                        self._emit_log(f"🔧 Patrones: {patt_resumen}", 'white')
                    except Exception:
                        pass

                self.risk_manager.reset()
                processed = 0
                closed_gains = 0
                closed_losses = 0
                dinero_ganado = 0.0
                dinero_perdido = 0.0

                # 3. EJECUTAR BACKTESTING
                for idx, row in df_work.iterrows():
                    if self._stop:
                        break
                    
                    processed += 1
                    self._emit_progress(processed, total_rows)

                    # Cierre de operaciones
                    operaciones_cerradas = self.risk_manager.verificar_cierre_operaciones(row['Close'], idx)
                    for op in operaciones_cerradas:
                        profit = 0.0
                        try:
                            if op.tipo == 'BUY':
                                profit = (op.precio_cierre - op.precio_apertura) * op.lote_size
                            else:
                                profit = (op.precio_apertura - op.precio_cierre) * op.lote_size
                        except Exception:
                            profit = 0.0
                            
                        if np.isnan(profit) or np.isinf(profit):
                            profit = 0.0
                            
                        color = 'green' if profit >= 0 else 'red'
                        if profit >= 0:
                            closed_gains += 1
                            dinero_ganado += profit
                        else:
                            closed_losses += 1
                            dinero_perdido += abs(profit)
                            
                        self._emit_log(f"🔒 CIERRE: {op} | Profit: ${profit:+.2f}", color)

                    # Apertura por señales RL
                    senal = row.get('RL_Signal')
                    if senal is not None and senal != 0 and not np.isnan(senal):
                        if not self.risk_manager.puede_abrir_operacion():
                            continue
                            
                        atr_value = row.get('ATR')
                        if np.isnan(atr_value) or atr_value <= 0:
                            atr_value = (df_work['High'] - df_work['Low']).mean() * 0.1
                            
                        operacion = self.risk_integration.procesar_senal(
                            senal=senal,
                            precio_actual=row['Close'],
                            timestamp=idx,
                            atr_value=atr_value,
                            rr_ratio=2.0,
                        )
                        
                        if operacion:
                            self._emit_log(f"🔓 APERTURA: {operacion} | Señal RL: {senal}", 'cyan')

                    # Verificar condición de WinRate
                    total_closed = closed_gains + closed_losses
                    if self.use_winrate and total_closed > 0:
                        winrate = (closed_gains / total_closed) * 100.0
                        if winrate >= self.winrate_target:
                            self._emit_log(f"🎯 WinRate objetivo alcanzado: {winrate:.1f}% >= {self.winrate_target:.1f}%", 'yellow')
                            reached_winrate_target = True
                            break

                    time.sleep(0.0)

                # Cierre final de operaciones
                if not reached_winrate_target:
                    try:
                        last_price = df_work['Close'].dropna().iloc[-1]
                        last_idx = df_work.dropna(subset=['Close']).index[-1]
                        for op in self.risk_manager.operaciones_activas[:]:
                            profit = op.cerrar(last_price, last_idx)
                            if np.isnan(profit) or np.isinf(profit):
                                profit = 0.0
                                
                            color = 'green' if profit >= 0 else 'red'
                            if profit >= 0:
                                closed_gains += 1
                                dinero_ganado += profit
                            else:
                                closed_losses += 1
                                dinero_perdido += abs(profit)
                                
                            self._emit_log(f"🔚 CIERRE FINAL: {op} | Profit: ${profit:+.2f}", color)
                    except Exception:
                        pass

                # Calcular estadísticas finales
                total_closed = closed_gains + closed_losses
                winrate = (closed_gains / total_closed * 100.0) if total_closed > 0 else 0.0
                beneficio_total = dinero_ganado - dinero_perdido
                
                stats = {
                    'capital_final': float(self.risk_manager.capital),
                    'beneficio_total': float(beneficio_total),
                    'operaciones_ganadas': int(closed_gains),
                    'operaciones_perdidas': int(closed_losses),
                    'operaciones_activas': int(self.risk_manager.get_operaciones_activas_count()),
                    'max_operaciones': int(self.risk_manager.max_operaciones_activas),
                    'dinero_ganado': float(dinero_ganado),
                    'dinero_perdido': float(dinero_perdido),
                    'fx_config': copy.deepcopy(self._current_fx),
                    'candle_config': copy.deepcopy(self._current_candle),
                    'patterns_config': copy.deepcopy(self._current_patterns),
                    'winrate': float(winrate),
                    'attempt': attempt,
                }

                # Actualizar mejor resultado
                def _is_better(a: Optional[Dict], b: Dict) -> bool:
                    if a is None:
                        return True
                    if self.use_winrate:
                        return b.get('winrate', 0.0) > a.get('winrate', 0.0)
                    else:
                        return b.get('beneficio_total', 0.0) > a.get('beneficio_total', 0.0)

                if _is_better(self._best_stats, stats):
                    self._best_stats = copy.deepcopy(stats)
                    self._best_fx = copy.deepcopy(self._current_fx)
                    self._best_candle = copy.deepcopy(self._current_candle)
                    self._best_patterns = copy.deepcopy(self._current_patterns)
                    self._save_best_configuration(stats, attempt)

                # Verificar si se alcanzó el objetivo
                if self.use_winrate and winrate >= self.winrate_target:
                    reached_winrate_target = True
                    self._emit_log(f"✅ OBJETIVO ALCANZADO en intento {attempt}", 'green')
                    break

                # Si no se alcanzó, mutar y reintentar
                if self.use_winrate:
                    self._emit_log(f"📉 WinRate final {winrate:.1f}% < objetivo {self.winrate_target:.1f}%. Ajustando estrategias y reintentando (intento {attempt+1}).", 'yellow')
                    self._mutate_configs(winrate)
                else:
                    self._emit_log(f"🔄 Finalizado intento {attempt}. Preparando siguiente intento...", 'white')

                attempt += 1
                time.sleep(0.1)

            # FINALIZACIÓN
            final_stats = self._best_stats or {
                'capital_final': float(self.risk_manager.capital),
                'beneficio_total': float(self.risk_manager.beneficio_total),
                'operaciones_ganadas': int(self.risk_manager.operaciones_ganadas),
                'operaciones_perdidas': int(self.risk_manager.operaciones_perdidas),
                'operaciones_activas': int(self.risk_manager.get_operaciones_activas_count()),
                'max_operaciones': int(self.risk_manager.max_operaciones_activas),
                'dinero_ganado': float(getattr(self.risk_manager, 'ganancia_ganadoras_total', 0.0)),
                'dinero_perdido': float(getattr(self.risk_manager, 'perdida_perdedoras_total', 0.0)),
                'fx_config': copy.deepcopy(self._current_fx),
                'winrate': 0.0,
                'attempt': attempt-1,
            }

            # Incluir mejor configuración si existe
            if self._best_stats:
                final_stats['best'] = {
                    'stats': self._best_stats,
                    'fx': copy.deepcopy(self._best_fx),
                    'candle': copy.deepcopy(self._best_candle),
                    'patterns': copy.deepcopy(self._best_patterns),
                }

            # Mensaje final
            if reached_winrate_target:
                self._emit_log(f"🎉 ENTRENAMIENTO FINALIZADO - OBJETIVO ALCANZADO", 'green')
            elif self.max_attempts > 0 and attempt > self.max_attempts:
                self._emit_log(f"⏹️ ENTRENAMIENTO FINALIZADO - MÁXIMO DE INTENTOS", 'yellow')
            else:
                self._emit_log(f"🏁 ENTRENAMIENTO FINALIZADO", 'green')

            self._emit_finish(final_stats)

        except Exception as e:
            self._emit_log(f"❌ Error en hilo de entrenamiento IA: {e}", 'red')
            self._emit_finish({'error': str(e)})