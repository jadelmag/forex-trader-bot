# app/ai_trainer.py

import threading
import time
import random
import copy
import os
import json
from typing import Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import queue

import numpy as np
import pandas as pd

from strategies import ForexStrategies, CandleStrategies
from strategies.risk_manager import RiskManager
from strategies.risk_manager_integration import RiskManagerIntegration, RiskConfig
from rl.rl_agent import RLTradingAgent
from ia.smart_order_analyzer import SmartOrderAnalyzer


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
        save_best: bool = True,
        timesteps_per_attempt: int = 3000,
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
        self.save_best = bool(save_best)
        # Timesteps por intento de entrenamiento del modelo RL
        try:
            self.timesteps_per_attempt = int(timesteps_per_attempt)
            if self.timesteps_per_attempt <= 0:
                self.timesteps_per_attempt = 3000
        except Exception:
            self.timesteps_per_attempt = 3000
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_finish = on_finish
        self._thread: Optional[threading.Thread] = None
        self._stop = False
        self._stopped_by_user = False

        # Risk Manager
        self.risk_manager = RiskManager(max_operaciones_activas=self.max_orders, capital_inicial=self.capital_inicial)
        self.risk_integration = RiskManagerIntegration(self.risk_manager, debug_mode=False)

        # Estrategias auxiliares
        self.fx = ForexStrategies(self.df)
        self.candle = CandleStrategies(self.df)
        
        # Analizador inteligente de órdenes
        self.smart_analyzer = SmartOrderAnalyzer(self.df, self._current_fx, self._current_candle)

        # Tracking del mejor resultado
        self._best_stats: Optional[Dict] = None
        self._best_fx: Dict[str, Dict] = copy.deepcopy(self._current_fx)
        self._best_patterns: List[str] = list(self._current_patterns)
        self._best_candle: List[str] = list(self._current_candle)
        self._best_model_path: Optional[str] = None

        # Límite por tipo de estrategia (solicitado: 10 forex, 10 candle)
        # Nota: el RiskManager limita el total (max_orders). Aquí imponemos reparto por tipo.
        try:
            self.max_forex_ops = 10
            self.max_candle_ops = 10
        except Exception:
            self.max_forex_ops = 10
            self.max_candle_ops = 10

        # --- Candle strategies configuration management ---
        # Maintain per-strategy CandleExitConfig-like dicts that we can optimize
        self._config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        os.makedirs(self._config_dir, exist_ok=True)
        self._current_candle_configs: Dict[str, Dict] = {}
        for name in self._current_candle:
            self._current_candle_configs[name] = self._load_candle_config(name)
        self._best_candle_configs: Dict[str, Dict] = {k: dict(v) for k, v in self._current_candle_configs.items()}

        # Agente RL
        self.rl_agent = None
        self._initialize_rl_agent()

        # Track de operaciones
        self.operaciones_track = []
        self.estadisticas_por_estrategia = {}
        self.mejor_configuracion = None
        
        # Thread pool para procesamiento paralelo
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="AITrainer")
        self._progress_queue = queue.Queue()
        self._batch_size = 50  # Procesar en batches para mejor rendimiento

    def _count_active_ops_by_type(self) -> Dict[str, int]:
        """Cuenta operaciones activas por tipo usando el prefijo de estrategia.
        Prefijos: AI_FOREX_, AI_CANDLE_ (cualquier otro cuenta como 'other').
        """
        counts = {"forex": 0, "candle": 0, "other": 0}
        try:
            for op in getattr(self.risk_manager, 'operaciones_activas', []) or []:
                name = getattr(op, 'estrategia', '')
                if isinstance(name, str):
                    if name.startswith('AI_FOREX_'):
                        counts["forex"] += 1
                    elif name.startswith('AI_CANDLE_'):
                        counts["candle"] += 1
                    else:
                        counts["other"] += 1
                else:
                    counts["other"] += 1
        except Exception:
            pass
        return counts

    def _initialize_rl_agent(self):
        """Inicializa el agente RL con las estrategias actuales"""
        self.rl_agent = RLTradingAgent(
            self.df,
            self._current_fx,
            self._current_candle,
            self._current_patterns,
            candle_configs=self._current_candle_configs,
            log_fn=lambda m: self._emit_log(m, 'cyan')
        )

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        # Señal de parada solicitada por el usuario
        self._stop = True
        self._stopped_by_user = True

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
        """Entrena el modelo RL con las estrategias actuales - OPTIMIZADO para no bloquear UI"""
        self._emit_log("🎯 INICIANDO ENTRENAMIENTO RL CON ESTRATEGIAS", 'green')
        self._emit_log(f"📊 Estrategias FX: {list(self._current_fx.keys())}", 'white')
        self._emit_log(f"📊 Estrategias Candle: {self._current_candle}", 'white')
        self._emit_log(f"📊 Patrones: {self._current_patterns}", 'white')
        params_list = [(k, f"riesgo={v.get('riesgo', 0.0):.3f}, rr={v.get('rr', 0.0):.2f}") for k, v in self._current_fx.items()]
        self._emit_log(f"⚙️  Parámetros: {params_list}", 'white')
        
        # Recrear entorno con estrategias y configuraciones actuales
        self.rl_agent.estrategias_fx = self._current_fx
        self.rl_agent.estrategias_candle = self._current_candle
        self.rl_agent.patrones = self._current_patterns
        self.rl_agent.candle_configs = self._current_candle_configs
        self.rl_agent.env = self.rl_agent._create_env()
        
        # Actualizar analizador inteligente
        self.smart_analyzer = SmartOrderAnalyzer(self.df, self._current_fx, self._current_candle)
        
        # Entrenar modelo con callbacks no bloqueantes
        def progress_callback(cur, total):
            # Usar queue para evitar bloqueo
            self._progress_queue.put((cur, total))
            # Procesar queue de forma no bloqueante
            try:
                while not self._progress_queue.empty():
                    c, t = self._progress_queue.get_nowait()
                    self._emit_progress(c, t)
                    # Yield al sistema para permitir que UI responda
                    if c % 100 == 0:
                        time.sleep(0.001)
            except queue.Empty:
                pass
        
        success = self.rl_agent.entrenar(timesteps=timesteps, progress_cb=progress_callback)
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
        
        # Guardar una copia rápida de las señales para inspección
        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            reports_dir = os.path.join(project_root, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            ts = int(time.time())
            out_csv = os.path.join(reports_dir, f"rl_signals_{ts}.csv")
            df_signals.to_csv(out_csv, index=False)
            self._emit_log(f"💾 Señales RL guardadas en: {out_csv}", 'cyan')
        except Exception as e:
            self._emit_log(f"⚠️ No se pudo guardar CSV de señales RL: {e}", 'yellow')
        
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

        # Mutar estrategias candle (selección de estrategias activas)
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

        # Mantener el dict de configs sincronizado con la selección actual
        # 1) Eliminar configs de estrategias ya no seleccionadas
        for k in list(self._current_candle_configs.keys()):
            if k not in self._current_candle:
                self._current_candle_configs.pop(k, None)
        # 2) Añadir configs por defecto para nuevas estrategias seleccionadas
        for k in self._current_candle:
            if k not in self._current_candle_configs:
                self._current_candle_configs[k] = self._load_candle_config(k)

        # Mutar parámetros de configuración Candle por estrategia
        for name, cfg in self._current_candle_configs.items():
            try:
                # Booleans: pequeñas probabilidades de toggle, guiadas por rendimiento
                def maybe_flip(val: bool, p: float) -> bool:
                    return (not val) if random.random() < p else val

                # Tasa base de mutación guiada por winrate (peor -> más mutación)
                base_p = 0.02 if last_winrate >= self.winrate_target else 0.08
                cfg['use_signal_change'] = maybe_flip(bool(cfg.get('use_signal_change', True)), base_p)
                cfg['use_stop_loss'] = maybe_flip(bool(cfg.get('use_stop_loss', True)), base_p)
                cfg['use_take_profit'] = maybe_flip(bool(cfg.get('use_take_profit', True)), base_p)
                cfg['use_trailing_stop'] = maybe_flip(bool(cfg.get('use_trailing_stop', False)), base_p)
                cfg['use_pattern_reversal'] = maybe_flip(bool(cfg.get('use_pattern_reversal', False)), base_p)

                # ATR multipliers: mutate within reasonable ranges
                def mutate_float(x: float, low: float, high: float, scale: float = 0.15) -> float:
                    x = float(x)
                    x *= random.uniform(1.0 - scale, 1.0 + scale)
                    return min(max(x, low), high)

                cfg['atr_sl_multiplier'] = mutate_float(cfg.get('atr_sl_multiplier', 1.5), 0.5, 5.0)
                cfg['atr_tp_multiplier'] = mutate_float(cfg.get('atr_tp_multiplier', 3.0), 0.5, 8.0)
                cfg['atr_trailing_multiplier'] = mutate_float(cfg.get('atr_trailing_multiplier', 2.0), 0.5, 6.0)

                # Pattern lists: keep as-is, optionally small mutation
                for key, defaults in (
                    ('bullish_reversal_patterns', ['hammer', 'bullish_engulfing', 'morning_star']),
                    ('bearish_reversal_patterns', ['hanging_man', 'bearish_engulfing', 'evening_star']),
                ):
                    arr = cfg.get(key)
                    if not isinstance(arr, list):
                        arr = list(defaults)
                    # 10% chance to swap one element with defaults
                    if random.random() < 0.1 and defaults:
                        idx = random.randrange(0, len(arr)) if arr else 0
                        pick = random.choice(defaults)
                        if idx < len(arr):
                            arr[idx] = pick
                        else:
                            arr.append(pick)
                    cfg[key] = arr
            except Exception:
                continue

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

        riesgos_list = [(k, f"{v.get('riesgo', 0.0):.3f}") for k, v in self._current_fx.items()]
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
                'candle_configs': self._best_candle_configs,
                'patterns': self._best_patterns,
                'winrate_target': self.winrate_target,
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
                
            # Persist per-strategy candle configs to config/*.json
            try:
                for strat, cfg in self._best_candle_configs.items():
                    path = self._primary_config_path(strat)
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(cfg, f, ensure_ascii=False, indent=2)
                self._emit_log(f"💾 Configs de Candle guardadas en {self._config_dir}", 'cyan')
            except Exception as ie:
                self._emit_log(f"⚠️ No se pudo guardar configs de Candle: {ie}", 'yellow')

            # Escribir siempre el reporte TXT final
            try:
                self._write_best_txt_report()
                self._emit_log(f"📝 Reporte final best_config_ia.txt generado", 'cyan')
            except Exception as re:
                self._emit_log(f"⚠️ No se pudo escribir el reporte final TXT: {re}", 'yellow')
            # Escribir siempre el reporte JSON final
            try:
                self._write_best_json_report()
                self._emit_log(f"📝 Reporte final best_config_ia.json generado", 'cyan')
            except Exception as re2:
                self._emit_log(f"⚠️ No se pudo escribir el reporte final JSON: {re2}", 'yellow')
                self._emit_log(f"⚠️ No se pudo escribir el reporte JSON: {re2}", 'yellow')

        except Exception as e:
            self._emit_log(f"❌ No se pudo guardar la mejor configuración: {e}", 'red')

    # ------------- Config helpers (Candle) -------------
    def _primary_config_path(self, strategy_name: str) -> str:
        """Primary filename for a candle strategy config: config/candle_<resolved>.json"""
        try:
            from strategies.strategy_utils import resolve_strategy_name
            resolved = resolve_strategy_name(strategy_name, 'candle')
        except Exception:
            resolved = strategy_name
        fname = f"candle_{resolved}.json"
        return os.path.join(self._config_dir, fname)

    def _all_config_paths(self, strategy_name: str) -> List[str]:
        paths = []
        try:
            from strategies.strategy_utils import resolve_strategy_name
            resolved = resolve_strategy_name(strategy_name, 'candle')
        except Exception:
            resolved = strategy_name
        paths.append(os.path.join(self._config_dir, f"candle_{strategy_name}.json"))
        paths.append(os.path.join(self._config_dir, f"candle_{resolved}.json"))
        return list(dict.fromkeys(paths))

    def _default_candle_config(self) -> Dict:
        return {
            'use_signal_change': True,
            'use_stop_loss': True,
            'use_take_profit': True,
            'use_trailing_stop': False,
            'use_pattern_reversal': False,
            'atr_sl_multiplier': 1.5,
            'atr_tp_multiplier': 3.0,
            'atr_trailing_multiplier': 2.0,
            'bullish_reversal_patterns': ['hammer', 'bullish_engulfing', 'morning_star'],
            'bearish_reversal_patterns': ['hanging_man', 'bearish_engulfing', 'evening_star'],
        }

    def _load_candle_config(self, strategy_name: str) -> Dict:
        # Load from any matching path, else default
        for p in self._all_config_paths(strategy_name):
            try:
                if os.path.isfile(p):
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            # merge with defaults to ensure keys
                            base = self._default_candle_config()
                            base.update({k: v for k, v in data.items() if k in base or True})
                            return base
            except Exception:
                continue
        return self._default_candle_config()

    def _write_best_txt_report(self):
        """Escribe reports/best_config_ia.txt con la mejor configuración y resumen de resultados."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        reports_dir = os.path.join(project_root, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        path = os.path.join(reports_dir, 'best_config_ia.txt')

        best = self._best_stats or {}
        fx_cfg = self._best_fx or {}
        candle_list = self._best_candle or []
        candle_cfgs = self._best_candle_configs or {}

        # Operaciones
        ganancias = float(best.get('dinero_ganado', 0.0)) if 'dinero_ganado' in best else 0.0
        perdidas = float(best.get('dinero_perdido', 0.0)) if 'dinero_perdido' in best else 0.0
        beneficio_total = float(best.get('beneficio_total', ganancias - perdidas))
        ops_gan = int(best.get('operaciones_ganadas', 0))
        ops_per = int(best.get('operaciones_perdidas', 0))
        winrate = float(best.get('winrate', 0.0))
        max_ops = int(best.get('max_operaciones', getattr(self.risk_manager, 'max_operaciones_activas', 0)))

        lines = []
        lines.append("=== MEJOR CONFIGURACIÓN IA ===")
        lines.append("")
        lines.append(f"Objetivo WinRate: {self.winrate_target:.2f}%  |  WinRate logrado: {winrate:.2f}%")
        lines.append(f"Capital inicial: ${self.capital_inicial:.2f}  |  Capital final: ${float(best.get('capital_final', 0.0)):.2f}")
        lines.append(f"Máx. operaciones simultáneas permitidas: {max_ops}")
        lines.append("")
        lines.append("-- Estrategias Forex --")
        if fx_cfg:
            for name, params in sorted(fx_cfg.items()):
                try:
                    riesgo_pct = float(params.get('riesgo', 0.0)) * 100.0
                    rr = float(params.get('rr', 0.0))
                except Exception:
                    riesgo_pct, rr = 0.0, 0.0
                lines.append(f"  * {name}: riesgo={riesgo_pct:.2f}%  rr={rr:.2f}")
        else:
            lines.append("  (ninguna)")
        lines.append("")
        lines.append("-- Candle Strategies --")
        if candle_list:
            for name in sorted(candle_list):
                cfg = candle_cfgs.get(name, {})
                lines.append(f"  * {name}:")
                for k in [
                    'use_signal_change','use_stop_loss','use_take_profit','use_trailing_stop','use_pattern_reversal',
                    'atr_sl_multiplier','atr_tp_multiplier','atr_trailing_multiplier',
                    'bullish_reversal_patterns','bearish_reversal_patterns']:
                    v = cfg.get(k, None)
                    lines.append(f"      - {k}: {v}")
        else:
            lines.append("  (ninguna)")
        lines.append("")
        lines.append("-- Resultados de Operaciones --")
        lines.append(f"  Operaciones ganadas: {ops_gan}  |  Dinero ganado: ${ganancias:.2f}")
        lines.append(f"  Operaciones perdidas: {ops_per}  |  Dinero perdido: -${perdidas:.2f}")
        lines.append(f"  Beneficio total: ${beneficio_total:.2f}")
        lines.append("")
        # Listado detallado de operaciones
        succ_ops = best.get('successful_operations', []) or []
        fail_ops = best.get('failed_operations', []) or []
        lines.append("-- Operaciones Ganadoras (detalle) --")
        if succ_ops:
            for op in succ_ops:
                estr = op.get('estrategia', '')
                amt = float(op.get('profit', 0.0))
                ts = op.get('timestamp', '')
                lines.append(f"  + [{ts}] {estr}: +${amt:.2f}")
        else:
            lines.append("  (ninguna)")
        lines.append("")
        lines.append("-- Operaciones Perdedoras (detalle) --")
        if fail_ops:
            for op in fail_ops:
                estr = op.get('estrategia', '')
                amt = float(op.get('loss', 0.0))
                ts = op.get('timestamp', '')
                lines.append(f"  - [{ts}] {estr}: -${amt:.2f}")
        else:
            lines.append("  (ninguna)")
        lines.append("")
        lines.append("Restricciones aplicadas:")
        lines.append("  - Máximo de operaciones simultáneas respetado por RiskManager")
        lines.append("  - Sin estrategias Forex duplicadas (clave única por estrategia)")
        lines.append("  - Máximo una apertura por vela (pipeline de RL/analizador abre 0/1 por paso)")

        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def _write_best_json_report(self):
        """Escribe reports/best_config_ia.json con la mejor configuración y resultados en formato estructurado."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        reports_dir = os.path.join(project_root, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        path = os.path.join(reports_dir, 'best_config_ia.json')

        best = self._best_stats or {}
        data = {
            'winrate_target': self.winrate_target,
            'capital_inicial': self.capital_inicial,
            'capital_final': best.get('capital_final'),
            'max_operaciones': best.get('max_operaciones', getattr(self.risk_manager, 'max_operaciones_activas', 0)),
            'winrate': best.get('winrate'),
            'beneficio_total': best.get('beneficio_total'),
            'dinero_ganado': best.get('dinero_ganado'),
            'dinero_perdido': best.get('dinero_perdido'),
            'operaciones_ganadas': best.get('operaciones_ganadas'),
            'operaciones_perdidas': best.get('operaciones_perdidas'),
            'estrategias_fx': self._best_fx or {},
            'candle_strategies': self._best_candle or [],
            'candle_configs': self._best_candle_configs or {},
            'successful_operations': best.get('successful_operations', []),
            'failed_operations': best.get('failed_operations', []),
            'restricciones': [
                'Máximo de operaciones simultáneas respetado por RiskManager',
                'Sin estrategias Forex duplicadas (clave única por estrategia)',
                'Máximo una apertura por vela (pipeline RL/analizador)'
            ]
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _run(self):
        try:
            attempt = 1
            reached_winrate_target = False
            
            while not self._stop:
                # (semilla aleatoria eliminada)

                # 1. ENTRENAR MODELO RL - Ya optimizado con callbacks no bloqueantes
                if not self._entrenar_modelo_rl(timesteps=self.timesteps_per_attempt):
                    self._emit_log("❌ Fallo en entrenamiento RL, saltando intento...", 'red')
                    attempt += 1
                    continue

                # 2. GENERAR SEÑALES
                df_work = self._generate_signals_from_rl()
                total_rows = len(df_work)

                # Reiniciar barra de progreso para la fase de backtesting
                self._emit_progress(0, total_rows)

                self._emit_log(f"🚀 INICIO BACKTESTING (intento {attempt})", 'green')
                # Mostrar reparto de límites por tipo
                try:
                    self._emit_log(f"🔒 Límite total RiskManager: {self.risk_manager.max_operaciones_activas}", 'white')
                    self._emit_log(f"🔢 Reparto por tipo -> Forex: {self.max_forex_ops} | Candle: {self.max_candle_ops}", 'white')
                except Exception:
                    pass
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
                successful_ops: List[Dict] = []
                failed_ops: List[Dict] = []

                # 3. EJECUTAR BACKTESTING CON ANÁLISIS INTELIGENTE - OPTIMIZADO
                # Flag para no spamear el log de stop
                stop_log_emitted = False
                
                # Procesar en batches para mejor rendimiento y no bloquear UI
                batch_counter = 0
                for idx, row in df_work.iterrows():
                    if self._stop:
                        if not stop_log_emitted:
                            self._emit_log("🛑 Señal de parada recibida. Deteniendo backtesting de forma segura...", 'yellow')
                            stop_log_emitted = True
                        break
                    
                    processed += 1
                    batch_counter += 1
                    
                    # Actualizar progreso y yield al sistema cada N filas
                    if batch_counter >= self._batch_size:
                        self._emit_progress(processed, total_rows)
                        # Yield al thread principal para permitir que UI responda
                        time.sleep(0.001)
                        batch_counter = 0
                    elif processed % 10 == 0:
                        # Actualización más frecuente pero sin sleep
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
                            try:
                                successful_ops.append({
                                    'estrategia': getattr(op, 'estrategia', ''),
                                    'profit': float(profit),
                                    'timestamp': idx
                                })
                            except Exception:
                                pass
                        else:
                            closed_losses += 1
                            dinero_perdido += abs(profit)
                            try:
                                failed_ops.append({
                                    'estrategia': getattr(op, 'estrategia', ''),
                                    'loss': float(abs(profit)),
                                    'timestamp': idx
                                })
                            except Exception:
                                pass
                            
                        self._emit_log(f"🔒 CIERRE {op.estrategia}: {op} | Profit: ${profit:+.2f}", color)

                    # Análisis inteligente para apertura de órdenes
                    senal = row.get('RL_Signal')
                    if senal is not None and senal != 0 and not np.isnan(senal):
                        if not self.risk_manager.puede_abrir_operacion():
                            continue

                        # ANÁLISIS INTELIGENTE DE LA VELA
                        analysis = self.smart_analyzer.analyze_candle_for_buy_opportunity(idx, row['Close'])

                        if analysis['should_buy']:
                            atr_value = row.get('ATR')
                            if np.isnan(atr_value) or atr_value <= 0:
                                atr_value = (df_work['High'] - df_work['Low']).mean() * 0.1

                            # Usar estrategia recomendada por el análisis inteligente
                            strategy_name = analysis['recommended_strategy']
                            strategy_type = analysis.get('strategy_type', 'rl')

                            # Resolver tipo cuando venga 'rl' o valores inesperados
                            stype = str(strategy_type).lower() if strategy_type is not None else 'rl'
                            if stype not in ('forex', 'candle'):
                                if strategy_name in self._current_fx:
                                    stype = 'forex'
                                elif strategy_name in self._current_candle:
                                    stype = 'candle'
                                else:
                                    stype = 'forex'  # fallback razonable

                            # Enforzar límites por tipo (10/10)
                            type_counts = self._count_active_ops_by_type()
                            if stype == 'forex' and type_counts.get('forex', 0) >= self.max_forex_ops:
                                self._emit_log(f"⛔ Límite Forex alcanzado ({type_counts.get('forex',0)}/{self.max_forex_ops}). Saltando apertura.", 'yellow')
                                continue
                            if stype == 'candle' and type_counts.get('candle', 0) >= self.max_candle_ops:
                                self._emit_log(f"⛔ Límite Candle alcanzado ({type_counts.get('candle',0)}/{self.max_candle_ops}). Saltando apertura.", 'yellow')
                                continue

                            # Determinar parámetros según tipo de estrategia
                            if stype == 'forex' and strategy_name in self._current_fx:
                                rr_ratio = self._current_fx[strategy_name].get('rr', 2.0)
                                riesgo = self._current_fx[strategy_name].get('riesgo', 0.01)
                            else:
                                rr_ratio = 2.0
                                riesgo = 0.01

                            operacion = self.risk_integration.procesar_senal(
                                senal=senal,
                                precio_actual=row['Close'],
                                timestamp=idx,
                                atr_value=atr_value,
                                rr_ratio=rr_ratio,
                                estrategia=(f"AI_{'FOREX' if stype=='forex' else 'CANDLE'}_{strategy_name}" if strategy_name else f"AI_{'FOREX' if stype=='forex' else 'CANDLE'}")
                            )
                            
                            if operacion:
                                confidence = analysis['confidence_score']
                                patterns = ', '.join(analysis['pattern_signals'][:2])  # Mostrar máximo 2 patrones
                                self._emit_log(f"🧠 APERTURA INTELIGENTE: {operacion}", 'cyan')
                                self._emit_log(f"   └─ Estrategia: {strategy_name} | Confianza: {confidence:.2f} | Patrones: {patterns}", 'white')
                                self._emit_log(f"   └─ Razón: {analysis['reason'][:100]}...", 'white')
                        else:
                            # Log de por qué no se abrió la operación
                            self._emit_log(f"⚠️ SEÑAL RL RECHAZADA en vela {idx}: {analysis['reason'][:80]}...", 'yellow')

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
                                try:
                                    successful_ops.append({
                                        'estrategia': getattr(op, 'estrategia', ''),
                                        'profit': float(profit),
                                        'timestamp': last_idx
                                    })
                                except Exception:
                                    pass
                            else:
                                closed_losses += 1
                                dinero_perdido += abs(profit)
                                try:
                                    failed_ops.append({
                                        'estrategia': getattr(op, 'estrategia', ''),
                                        'loss': float(abs(profit)),
                                        'timestamp': last_idx
                                    })
                                except Exception:
                                    pass
                                
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
                    'successful_operations': successful_ops,
                    'failed_operations': failed_ops,
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

            # Mensaje final diferenciado
            if self._stopped_by_user:
                self._emit_log("🛑 ENTRENAMIENTO DETENIDO POR EL USUARIO (finalizado el apagado)", 'yellow')
            else:
                if reached_winrate_target:
                    self._emit_log(f"🎉 ENTRENAMIENTO FINALIZADO - OBJETIVO ALCANZADO", 'green')
                else:
                    self._emit_log(f"🏁 ENTRENAMIENTO FINALIZADO", 'green')

            # Escribir siempre el reporte TXT final
            try:
                self._write_best_txt_report()
                self._emit_log(f"📝 Reporte final best_config_ia.txt generado", 'cyan')
            except Exception as re:
                self._emit_log(f"⚠️ No se pudo escribir el reporte final TXT: {re}", 'yellow')

            self._emit_finish(final_stats)

        except Exception as e:
            self._emit_log(f"❌ Error en hilo de entrenamiento IA: {e}", 'red')
            self._emit_finish({'error': str(e)})