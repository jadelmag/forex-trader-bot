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

class AITrainer:
    """
    Ejecuta el flujo de "entrenamiento" de IA en un hilo de fondo para no bloquear la UI.
    - Aplica estrategias/patrones seleccionados para generar señales.
    - Usa RiskManager para abrir/cerrar operaciones hasta max_orders.
    - Detiene por WinRate objetivo (si se especifica).
    - Emite logs y notificaciones mediante callbacks seguros para la UI.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        seleccion_fx: Dict[str, Dict],
        seleccion_patterns: List[str],
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
        # Configuración base y actual (para aprendizaje entre intentos)
        self.seleccion_fx = seleccion_fx or {}
        self.seleccion_patterns = seleccion_patterns or []
        self._current_fx: Dict[str, Dict] = copy.deepcopy(self.seleccion_fx)
        self._current_patterns: List[str] = list(self.seleccion_patterns)
        self.max_orders = max_orders
        self.capital_inicial = capital_inicial
        self.use_winrate = use_winrate
        self.winrate_target = float(winrate_target or 0.0)
        self.max_attempts = int(max_attempts or 0)  # 0 = ilimitado
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

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True

    # ---------------- Internals ----------------
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

    def _generate_signals_df_from(self, seleccion_fx: Dict[str, Dict], seleccion_patterns: List[str]) -> pd.DataFrame:
        df_new = self.df.copy()
        # Estrategias Forex
        for nombre, params in (seleccion_fx or {}).items():
            try:
                metodo = getattr(self.fx, nombre, None)
                if not callable(metodo):
                    self._emit_log(f"Estrategia Forex no encontrada: {nombre}", 'red')
                    continue
                risk_kwargs = {
                    'risk_per_trade': params.get('riesgo', 0.01),
                    'rr_ratio': params.get('rr', 2.0),
                }
                df_res = metodo(**risk_kwargs)
                if isinstance(df_res, pd.DataFrame) and 'Signal' in df_res.columns:
                    col_name = f"{nombre}_Signal"
                    df_new[col_name] = df_res['Signal']
            except Exception as e:
                self._emit_log(f"Error aplicando estrategia {nombre}: {e}", 'red')

        # Patrones de velas (como columnas de señal también si existen)
        for nombre in (seleccion_patterns or []):
            try:
                metodo = getattr(self.candle, nombre, None)
                if not callable(metodo):
                    self._emit_log(f"Patrón no encontrado: {nombre}", 'red')
                    continue
                df_res = metodo()
                if isinstance(df_res, pd.DataFrame) and 'Signal' in df_res.columns:
                    col_name = f"{nombre}_Signal"
                    df_new[col_name] = df_res['Signal']
            except Exception as e:
                self._emit_log(f"Error aplicando patrón {nombre}: {e}", 'red')

        # ATR aproximado para SL/TP
        df_new['ATR'] = (df_new['High'] - df_new['Low']).rolling(14).mean()
        if df_new['ATR'].isna().all():
            df_new['ATR'] = (df_new['High'] - df_new['Low']).mean() * 0.1
        else:
            df_new['ATR'] = df_new['ATR'].fillna(df_new['ATR'].mean())
        return df_new

    def _mutate_configs(self, last_winrate: float):
        """Ajusta ligeramente los parámetros actuales para el siguiente intento.
        Heurística simple:
        - Reducir riesgo si el winrate es bajo.
        - Aumentar rr_ratio gradualmente.
        - Mutaciones aleatorias suaves para explorar.
        - Togglear patrones con pequeña probabilidad.
        """
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

        # Mutar patrones: con baja probabilidad, añadir/eliminar alguno de la lista base
        # Mantener siempre como subconjunto de los patrones base iniciales para evitar nombres inválidos
        base_patterns = set(self.seleccion_patterns)
        cur_set = set(self._current_patterns)
        # Toggle aleatorio
        if base_patterns:
            if random.random() < 0.25 and len(cur_set) > 0:
                cur_set.remove(random.choice(list(cur_set)))
            if random.random() < 0.35 and len(cur_set) < len(base_patterns):
                restantes = list(base_patterns - cur_set)
                if restantes:
                    cur_set.add(random.choice(restantes))
        self._current_patterns = list(cur_set)

    def _run(self):
        try:
            attempt = 1
            while not self._stop:
                # Respetar límite de intentos (si aplica)
                if self.max_attempts > 0 and attempt > self.max_attempts:
                    self._emit_log(f"Máximo de intentos alcanzado: {self.max_attempts}. Finalizando.", 'yellow')
                    final_stats = self._best_stats or {
                        'capital_final': float(self.risk_manager.capital),
                        'beneficio_total': float(self.risk_manager.beneficio_total),
                        'operaciones_ganadas': int(self.risk_manager.operaciones_ganadas),
                        'operaciones_perdidas': int(self.risk_manager.operaciones_perdidas),
                        'operaciones_activas': int(self.risk_manager.get_operaciones_activas_count()),
                        'max_operaciones': int(self.risk_manager.max_operaciones_activas),
                        'winrate': 0.0,
                        'attempt': attempt-1,
                    }
                    # Incluir mejor configuración si existe
                    if self._best_stats:
                        final_stats['best'] = {
                            'stats': self._best_stats,
                            'fx': copy.deepcopy(self._best_fx),
                            'patterns': list(self._best_patterns),
                        }
                    self._emit_finish(final_stats)
                    return

                # Semilla por intento (reproducible y variación leve entre intentos)
                if self.seed is not None:
                    try:
                        random.seed(self.seed + attempt - 1)
                        np.random.seed(self.seed + attempt - 1)
                        self._emit_log(f"Semilla establecida para intento {attempt}: {self.seed + attempt - 1}", 'white')
                    except Exception:
                        pass
                # Generar señales con la config ACTUAL
                df_work = self._generate_signals_df_from(self._current_fx, self._current_patterns)
                total_rows = len(df_work)

                self._emit_log(f"INICIO ENTRENAMIENTO IA (intento {attempt})", 'green')
                if self.use_winrate:
                    # Log de configuración actual (resumen)
                    try:
                        fx_resumen = ", ".join([f"{k}(riesgo={v.get('riesgo',0.01):.3f}, rr={v.get('rr',2.0):.2f})" for k,v in self._current_fx.items()]) or "-"
                        patt_resumen = ", ".join(self._current_patterns) or "-"
                        self._emit_log(f"Config actual -> FX: {fx_resumen}", 'white')
                        self._emit_log(f"Patrones: {patt_resumen}", 'white')
                    except Exception:
                        pass
                self.risk_manager.reset()

                processed = 0
                closed_gains = 0
                closed_losses = 0
                reached_winrate_target = False

                for idx, row in df_work.iterrows():
                    if self._stop:
                        break
                    # progreso
                    processed += 1
                    self._emit_progress(processed, total_rows)

                    # Cierre de operaciones por SL/TP
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
                        else:
                            closed_losses += 1
                        self._emit_log(f"CIERRE: {op} | Profit: ${profit:+.2f}", color)

                    # Aperturas por nuevas señales (todas las columnas *_Signal)
                    for col in [c for c in df_work.columns if c.endswith('_Signal')]:
                        senal = row.get(col)
                        if senal is None or senal == 0 or np.isnan(senal):
                            continue
                        if not self.risk_manager.puede_abrir_operacion():
                            break
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
                            self._emit_log(f"APERTURA: {operacion} | Fuente: {col.replace('_Signal','')}", 'cyan')

                    # Condición por WinRate
                    total_closed = closed_gains + closed_losses
                    if self.use_winrate and total_closed > 0:
                        winrate = (closed_gains / total_closed) * 100.0
                        if winrate >= self.winrate_target:
                            self._emit_log(f"Parada por WinRate objetivo alcanzado: {winrate:.1f}% >= {self.winrate_target:.1f}%", 'yellow')
                            reached_winrate_target = True
                            break

                    # Pequeña espera para no saturar CPU y permitir UI
                    time.sleep(0.0)

                # Cierre final de operaciones restantes al último precio válido
                # Nota: si se alcanzó el WinRate objetivo, NO forzamos el cierre,
                # para que el winrate final refleje el momento del objetivo.
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
                            else:
                                closed_losses += 1
                            self._emit_log(f"CIERRE FINAL: {op} | Profit: ${profit:+.2f}", color)
                    except Exception:
                        pass

                total_closed = closed_gains + closed_losses
                winrate = (closed_gains / total_closed * 100.0) if total_closed > 0 else 0.0
                stats = {
                    'capital_final': float(self.risk_manager.capital),
                    'beneficio_total': float(self.risk_manager.beneficio_total),
                    'operaciones_ganadas': int(self.risk_manager.operaciones_ganadas),
                    'operaciones_perdidas': int(self.risk_manager.operaciones_perdidas),
                    'operaciones_activas': int(self.risk_manager.get_operaciones_activas_count()),
                    'max_operaciones': int(self.risk_manager.max_operaciones_activas),
                    'winrate': float(winrate),
                    'attempt': attempt,
                }

                # Actualizar mejor resultado
                def _is_better(a: Optional[Dict], b: Dict) -> bool:
                    if a is None:
                        return True
                    # Priorizar winrate, luego beneficio_total
                    if b.get('winrate', 0.0) > a.get('winrate', 0.0):
                        return True
                    if b.get('winrate', 0.0) == a.get('winrate', 0.0) and b.get('beneficio_total', 0.0) > a.get('beneficio_total', 0.0):
                        return True
                    return False

                if _is_better(self._best_stats, stats):
                    self._best_stats = copy.deepcopy(stats)
                    self._best_fx = copy.deepcopy(self._current_fx)
                    self._best_patterns = list(self._current_patterns)
                    # Guardar mejor configuración si corresponde
                    if self.save_best:
                        try:
                            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                            os.makedirs(logs_dir, exist_ok=True)
                            ts = int(time.time())
                            data = {
                                'timestamp': ts,
                                'attempt': attempt,
                                'stats': self._best_stats,
                                'fx': self._best_fx,
                                'patterns': self._best_patterns,
                            }
                            out_path = os.path.join(logs_dir, f'best_config_{ts}.json')
                            with open(out_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            self._emit_log(f"Mejor configuración actual guardada en: {out_path}", 'cyan')
                        except Exception as e:
                            self._emit_log(f"No se pudo guardar la mejor configuración: {e}", 'red')

                # Si no se usa winrate como objetivo, finaliza normal
                if not self.use_winrate:
                    self._emit_log("ENTRENAMIENTO IA FINALIZADO", 'green')
                    if self._best_stats:
                        stats['best'] = {
                            'stats': self._best_stats,
                            'fx': copy.deepcopy(self._best_fx),
                            'patterns': list(self._best_patterns),
                        }
                    self._emit_finish(stats)
                    return

                # Si se alcanzó el objetivo de winrate, finaliza
                if reached_winrate_target:
                    self._emit_log("ENTRENAMIENTO IA FINALIZADO (objetivo winrate alcanzado)", 'green')
                    if self._best_stats:
                        stats['best'] = {
                            'stats': self._best_stats,
                            'fx': copy.deepcopy(self._best_fx),
                            'patterns': list(self._best_patterns),
                        }
                    self._emit_finish(stats)
                    return

                # Si no se alcanzó el objetivo, APRENDER y reintentar
                self._emit_log(f"WinRate final {winrate:.1f}% < objetivo {self.winrate_target:.1f}%. Ajustando estrategias y reintentando (intento {attempt+1}).", 'yellow')
                try:
                    self._mutate_configs(winrate)
                except Exception:
                    pass
                attempt += 1
                # pequeña pausa para permitir refresco UI
                time.sleep(0.05)

            # Si se pidió parar externamente
            self._emit_log("ENTRENAMIENTO IA DETENIDO POR USUARIO", 'yellow')
            self._emit_finish({'error': 'detenido'})
        except Exception as e:
            self._emit_log(f"Error en hilo de entrenamiento IA: {e}", 'red')
            self._emit_finish({'error': str(e)})
