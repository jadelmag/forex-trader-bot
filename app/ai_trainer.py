# app/ai_trainer.py

import threading
import time
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
    - Detiene por iteraciones o por WinRate objetivo.
    - Emite logs y notificaciones mediante callbacks seguros para la UI.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        seleccion_fx: Dict[str, Dict],
        seleccion_patterns: List[str],
        max_orders: int,
        capital_inicial: float,
        use_iterations: bool,
        iterations: int,
        use_winrate: bool,
        winrate_target: float,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_finish: Optional[Callable[[Dict], None]] = None,
    ):
        self.df = df
        self.seleccion_fx = seleccion_fx or {}
        self.seleccion_patterns = seleccion_patterns or []
        self.max_orders = max_orders
        self.capital_inicial = capital_inicial
        self.use_iterations = use_iterations
        self.iterations = max(1, int(iterations or 1))
        self.use_winrate = use_winrate
        self.winrate_target = float(winrate_target or 0.0)
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

    def _generate_signals_df(self) -> pd.DataFrame:
        df_new = self.df.copy()
        # Estrategias Forex
        for nombre, params in self.seleccion_fx.items():
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
        for nombre in self.seleccion_patterns:
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

    def _run(self):
        try:
            self._emit_log("INICIO ENTRENAMIENTO IA (hilo en segundo plano)", 'green')
            self.risk_manager.reset()
            df_work = self._generate_signals_df()

            total_rows = len(df_work)
            processed = 0
            closed_gains = 0
            closed_losses = 0

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

                # Condición de parada por iteraciones (procesadas)
                if self.use_iterations and processed >= self.iterations:
                    self._emit_log("Parada por iteraciones alcanzadas.", 'yellow')
                    break

                # Condición por WinRate
                total_closed = closed_gains + closed_losses
                if self.use_winrate and total_closed > 0:
                    winrate = (closed_gains / total_closed) * 100.0
                    if winrate >= self.winrate_target:
                        self._emit_log(f"Parada por WinRate objetivo alcanzado: {winrate:.1f}% >= {self.winrate_target:.1f}%", 'yellow')
                        break

                # Pequeña espera para no saturar CPU y permitir UI
                time.sleep(0.0)

            # Cierre final de operaciones restantes al último precio válido
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
            }

            self._emit_log("ENTRENAMIENTO IA FINALIZADO", 'green')
            self._emit_finish(stats)
        except Exception as e:
            self._emit_log(f"Error en hilo de entrenamiento IA: {e}", 'red')
            self._emit_finish({'error': str(e)})
