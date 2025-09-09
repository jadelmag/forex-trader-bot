# strategies/risk_manager_integration.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import queue
import concurrent.futures
import time
import json
import os
from typing import Dict, List, Optional, Callable, Union, Any
import logging
from collections import deque
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RiskManagerIntegration')

@dataclass
class RiskConfig:
    """Configuración de riesgo personalizable"""
    atr_period: int = 14
    default_risk_percent: float = 0.01  # 1%
    default_rr_ratio: float = 2.0
    atr_sl_multiplier: float = 2.0
    atr_tp_multiplier: float = 2.0
    atr_trailing_multiplier: float = 1.5
    max_strategies_per_candle: int = 3
    enable_trailing_stop: bool = False
    enable_sell_operations: bool = True
    worker_timeout: float = 0.5
    queue_maxsize: int = 2000
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RiskConfig':
        return cls(**data)

@dataclass
class WorkerMetrics:
    """Métricas de rendimiento de workers"""
    signals_processed: int = 0
    dataframes_processed: int = 0
    processing_time_total: float = 0.0
    errors_count: int = 0
    queue_full_count: int = 0
    last_reset: datetime = None
    
    def __post_init__(self):
        if self.last_reset is None:
            self.last_reset = datetime.now()
    
    def reset(self):
        self.signals_processed = 0
        self.dataframes_processed = 0
        self.processing_time_total = 0.0
        self.errors_count = 0
        self.queue_full_count = 0
        self.last_reset = datetime.now()
    
    def get_avg_processing_time(self) -> float:
        total_operations = self.signals_processed + self.dataframes_processed
        return self.processing_time_total / total_operations if total_operations > 0 else 0.0

class RiskManagerIntegration:
    """Integra RiskManager con señales de estrategia - Versión Mejorada"""
    
    def __init__(self, risk_manager, config: Optional[RiskConfig] = None, debug_mode=False):
        self.risk_manager = risk_manager
        self.config = config or RiskConfig()
        self.debug_mode = debug_mode
        
        # Thread safety
        self._lock = threading.RLock()
        self._state_lock = threading.RLock()
        
        # Sistema de colas para procesamiento paralelo
        self.signal_queue = queue.Queue(maxsize=self.config.queue_maxsize)
        self.dataframe_queue = queue.Queue(maxsize=100)
        
        # Thread pools optimizados
        self.signal_workers = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix='SignalWorker'
        )
        self.dataframe_workers = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix='DataFrameWorker'
        )
        
        # Flags de control
        self._running = True
        self._processing_threads = []
        self._shutdown_event = threading.Event()
        
        # Métricas de rendimiento
        self.metrics = WorkerMetrics()
        
        # Estado persistente (opcional)
        self._state_file = None
        self._enable_persistence = False
        
        # Iniciar workers
        self._start_workers()
        
        logger.info(f"RiskManagerIntegration mejorado iniciado con config: {self.config}")

    def enable_persistence(self, state_file: str):
        """Habilita persistencia de estado"""
        self._state_file = state_file
        self._enable_persistence = True
        self._load_state()

    def _save_state(self):
        """Guarda el estado actual"""
        if not self._enable_persistence or not self._state_file:
            return
        
        try:
            state = {
                'metrics': asdict(self.metrics),
                'config': self.config.to_dict(),
                'timestamp': datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            with open(self._state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")

    def _load_state(self):
        """Carga el estado guardado"""
        if not self._enable_persistence or not self._state_file or not os.path.exists(self._state_file):
            return
        
        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Cargar métricas
            if 'metrics' in state:
                metrics_data = state['metrics']
                if 'last_reset' in metrics_data:
                    metrics_data['last_reset'] = datetime.fromisoformat(metrics_data['last_reset'])
                self.metrics = WorkerMetrics(**metrics_data)
                
            logger.info("Estado cargado exitosamente")
            
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")

    def _start_workers(self):
        """Inicia todos los workers de procesamiento"""
        # Worker de procesamiento de señales
        for i in range(2):
            thread = threading.Thread(
                target=self._signal_processing_worker, 
                daemon=False,  # No daemon para shutdown graceful
                name=f"SignalProcessor-{i}"
            )
            thread.start()
            self._processing_threads.append(thread)
        
        # Worker de procesamiento de dataframes
        thread = threading.Thread(
            target=self._dataframe_processing_worker, 
            daemon=False,
            name="DataFrameProcessor"
        )
        thread.start()
        self._processing_threads.append(thread)

    def _signal_processing_worker(self):
        """Worker para procesamiento de señales individuales"""
        while self._running and not self._shutdown_event.is_set():
            try:
                signal_data = self.signal_queue.get(timeout=self.config.worker_timeout)
                
                start_time = time.time()
                self._process_single_signal(signal_data)
                processing_time = time.time() - start_time
                
                with self._lock:
                    self.metrics.signals_processed += 1
                    self.metrics.processing_time_total += processing_time
                
                self.signal_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                with self._lock:
                    self.metrics.errors_count += 1
                logger.error(f"Error en signal processing worker: {e}")

    def _dataframe_processing_worker(self):
        """Worker para procesamiento de dataframes completos"""
        while self._running and not self._shutdown_event.is_set():
            try:
                df_data = self.dataframe_queue.get(timeout=self.config.worker_timeout)
                
                start_time = time.time()
                self._process_dataframe_batch(df_data)
                processing_time = time.time() - start_time
                
                with self._lock:
                    self.metrics.dataframes_processed += 1
                    self.metrics.processing_time_total += processing_time
                
                self.dataframe_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                with self._lock:
                    self.metrics.errors_count += 1
                logger.error(f"Error en dataframe processing worker: {e}")

    def procesar_senal(self, senal, precio_actual, timestamp, atr_value=None, 
                       rr_ratio=None, estrategia_nombre=None, stop_loss_override=None, 
                       take_profit_override=None, sync_mode=False, risk_percent=None,
                       candle_config=None):
        """Procesa una señal de trading con configuraciones personalizables"""
        if not self._running:
            return None

        # Usar configuraciones personalizadas o defaults
        final_rr_ratio = rr_ratio or self.config.default_rr_ratio
        final_risk_percent = risk_percent or self.config.default_risk_percent
        
        # Aplicar configuración de candle strategy si está disponible
        atr_sl_mult = self.config.atr_sl_multiplier
        atr_tp_mult = self.config.atr_tp_multiplier
        
        if candle_config:
            atr_sl_mult = candle_config.get('atr_sl_multiplier', atr_sl_mult)
            atr_tp_mult = candle_config.get('atr_tp_multiplier', atr_tp_mult)

        signal_data = {
            'senal': senal,
            'precio_actual': float(precio_actual),
            'timestamp': timestamp,
            'atr_value': float(atr_value) if atr_value else None,
            'rr_ratio': float(final_rr_ratio),
            'risk_percent': float(final_risk_percent),
            'estrategia_nombre': estrategia_nombre,
            'stop_loss_override': float(stop_loss_override) if stop_loss_override else None,
            'take_profit_override': float(take_profit_override) if take_profit_override else None,
            'atr_sl_multiplier': atr_sl_mult,
            'atr_tp_multiplier': atr_tp_mult,
            'candle_config': candle_config
        }

        # Si se solicita modo síncrono (para GUI), procesar inmediatamente
        if sync_mode:
            return self._process_single_signal(signal_data)

        try:
            self.signal_queue.put_nowait(signal_data)
            return "SENAL_ENCOLADA"
        except queue.Full:
            with self._lock:
                self.metrics.queue_full_count += 1
            if self.debug_mode:
                logger.warning("Cola de señales llena")
            return None

    def _process_single_signal(self, signal_data: Dict):
        """Procesa una señal individual con configuraciones personalizadas y soporte completo BUY/SELL"""
        try:
            senal = signal_data['senal']
            precio_actual = signal_data['precio_actual']
            timestamp = signal_data['timestamp']
            atr_value = signal_data['atr_value']
            rr_ratio = signal_data['rr_ratio']
            risk_percent = signal_data['risk_percent']
            estrategia_nombre = signal_data['estrategia_nombre']
            stop_loss_override = signal_data['stop_loss_override']
            take_profit_override = signal_data['take_profit_override']
            atr_sl_multiplier = signal_data['atr_sl_multiplier']
            atr_tp_multiplier = signal_data['atr_tp_multiplier']
            candle_config = signal_data.get('candle_config', {})

            # Determinar tipo de operación basado en la señal
            if senal == 1:
                tipo = 'BUY'
            elif senal == -1:
                # Cerrar operaciones existentes por señal de salida
                return self.risk_manager.cerrar_operacion_por_estrategia(
                    estrategia_nombre, precio_actual, timestamp, "EXIT_SIGNAL"
                )
            else:
                return None

            # Calcular SL y TP
            if stop_loss_override is not None and take_profit_override is not None:
                stop_loss = stop_loss_override
                take_profit = take_profit_override
            else:
                if tipo == 'BUY':
                    stop_loss = precio_actual - (atr_value * atr_sl_multiplier)
                    take_profit = precio_actual + (atr_value * atr_tp_multiplier)
                elif tipo == 'SELL':
                    stop_loss = precio_actual + (atr_value * atr_sl_multiplier)
                    take_profit = precio_actual - (atr_value * atr_tp_multiplier)

            # Validar niveles calculados
            if tipo == 'BUY' and (stop_loss >= precio_actual or take_profit <= precio_actual):
                logger.error(f"Niveles inválidos para BUY: Precio={precio_actual}, SL={stop_loss}, TP={take_profit}")
                self.metrics.errors_count += 1
                return None
            elif tipo == 'SELL' and (stop_loss <= precio_actual or take_profit >= precio_actual):
                logger.error(f"Niveles inválidos para SELL: Precio={precio_actual}, SL={stop_loss}, TP={take_profit}")
                self.metrics.errors_count += 1
                return None

            # Crear operación usando RiskManager
            operacion = self.risk_manager.abrir_operacion(
                tipo=tipo,
                precio=precio_actual,
                timestamp=timestamp,
                stop_loss=stop_loss,
                take_profit=take_profit,
                riesgo_por_operacion=risk_percent / 100.0,
                estrategia=estrategia_nombre
            )

            if operacion:
                # Aplicar trailing stop si está configurado
                trailing_enabled = candle_config.get('trailing_stop_enabled', False)
                if trailing_enabled:
                    operacion.trailing_stop_enabled = True
                    operacion.trailing_stop_distance = atr_value * candle_config.get('trailing_stop_atr_multiplier', 2.0)
                    if self.debug_mode:
                        logger.info(f"Trailing stop configurado para operación {operacion.id_operacion}")

                self.metrics.signals_processed += 1
                logger.info(f"Señal {tipo} procesada: {estrategia_nombre} - Precio: {precio_actual}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
            else:
                self.metrics.errors_count += 1
                error_msg = self.risk_manager.last_error or "Error desconocido"
                logger.warning(f"Error procesando señal {tipo} {estrategia_nombre}: {error_msg}")

            return operacion

        except Exception as e:
            self.metrics.errors_count += 1
            logger.error(f"Error en _process_single_signal: {str(e)}")
            return None

    def procesar_dataframe(self, df: pd.DataFrame, atr_period=None, rr_ratio=None, 
                          estrategia_nombre=None, risk_percent=None, candle_config=None):
        """Procesa un dataframe completo con configuraciones personalizables"""
        if not self._running:
            return []

        # Usar configuraciones personalizadas o defaults
        final_atr_period = atr_period or self.config.atr_period
        final_rr_ratio = rr_ratio or self.config.default_rr_ratio
        final_risk_percent = risk_percent or self.config.default_risk_percent

        # Preparar datos para procesamiento batch
        df_data = {
            'df': df.copy(),
            'atr_period': final_atr_period,
            'rr_ratio': final_rr_ratio,
            'risk_percent': final_risk_percent,
            'estrategia_nombre': estrategia_nombre,
            'candle_config': candle_config
        }

        try:
            self.dataframe_queue.put_nowait(df_data)
            return [{'status': 'DATAFRAME_ENCOLADO'}]
        except queue.Full:
            with self._lock:
                self.metrics.queue_full_count += 1
            if self.debug_mode:
                logger.warning("Cola de dataframes llena")
            return [{'status': 'COLA_LLENA'}]

    def _process_dataframe_batch(self, df_data: Dict):
        """Procesa un dataframe completo con configuraciones personalizadas"""
        try:
            df = df_data['df']
            atr_period = df_data['atr_period']
            rr_ratio = df_data['rr_ratio']
            risk_percent = df_data['risk_percent']
            estrategia_nombre = df_data['estrategia_nombre']
            candle_config = df_data.get('candle_config')
            
            resultados = []

            # Calcular ATR si no existe
            if 'ATR' not in df.columns:
                high = df['High'].astype(float)
                low = df['Low'].astype(float)
                close = df['Close'].astype(float)
                
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = np.maximum(np.maximum(tr1, tr2), tr3)
                
                df['ATR'] = tr.rolling(window=atr_period).mean()

            # Procesar cada fila del dataframe
            for idx, row in df.iterrows():
                # Verificar cierre por SL/TP
                operaciones_cerradas = self.risk_manager.verificar_cierre_operaciones(row['Close'], idx)
                
                # Verificar trailing stops
                if self.config.enable_trailing_stop:
                    trailing_cerradas = self._check_trailing_stops(row['Close'], idx)
                    operaciones_cerradas.extend(trailing_cerradas)
                
                for op in operaciones_cerradas:
                    resultados.append({
                        'timestamp': idx, 
                        'tipo': 'CIERRE_SL_TP', 
                        'operacion': op, 
                        'precio': row['Close'], 
                        'resultado': op.resultado
                    })

                # Procesar señales del dataframe
                signal_value = 0
                if 'ExecSignal' in df.columns and not pd.isna(row.get('ExecSignal', np.nan)):
                    signal_value = int(row['ExecSignal'])
                elif 'Signal' in df.columns and not pd.isna(row.get('Signal', np.nan)):
                    signal_value = int(row['Signal'])

                if signal_value != 0:
                    atr_value = row.get('ATR', max(row['High'] - row['Low'], 0.0001))
                    
                    stop_loss_override = None
                    take_profit_override = None
                    if 'StopLoss' in df.columns and not pd.isna(row.get('StopLoss', np.nan)):
                        stop_loss_override = row['StopLoss']
                    if 'TakeProfit' in df.columns and not pd.isna(row.get('TakeProfit', np.nan)):
                        take_profit_override = row['TakeProfit']

                    # Procesar señal individual con configuraciones
                    resultado_senal = self.procesar_senal(
                        senal=signal_value,
                        precio_actual=row['Close'],
                        timestamp=idx,
                        atr_value=atr_value,
                        rr_ratio=rr_ratio,
                        risk_percent=risk_percent,
                        estrategia_nombre=estrategia_nombre,
                        stop_loss_override=stop_loss_override,
                        take_profit_override=take_profit_override,
                        candle_config=candle_config,
                        sync_mode=True  # Procesamiento síncrono en batch
                    )
                    
                    if resultado_senal is not None:
                        if signal_value == 1 and hasattr(resultado_senal, 'id'):
                            resultados.append({
                                'timestamp': idx, 
                                'tipo': 'APERTURA', 
                                'operacion': resultado_senal, 
                                'precio': row['Close']
                            })
                        elif signal_value == -1 and isinstance(resultado_senal, list):
                            for op in resultado_senal:
                                resultados.append({
                                    'timestamp': idx, 
                                    'tipo': 'CIERRE_ESTRATEGIA', 
                                    'operacion': op, 
                                    'precio': row['Close'], 
                                    'resultado': op.resultado
                                })

            return resultados

        except Exception as e:
            logger.error(f"Error procesando dataframe: {e}")
            return []

    def _check_trailing_stops(self, precio_actual, timestamp):
        """Verifica y ejecuta trailing stops"""
        operaciones_cerradas = []
        
        try:
            with self._state_lock:
                for operacion in self.risk_manager.operaciones_activas[:]:
                    if not hasattr(operacion, 'trailing_stop_enabled') or not operacion.trailing_stop_enabled:
                        continue
                    
                    if operacion.estado != 'ACTIVA':
                        continue
                    
                    if operacion.tipo == 'BUY':
                        # Actualizar precio más alto
                        if precio_actual > operacion.highest_price:
                            operacion.highest_price = precio_actual
                            # Actualizar stop loss
                            atr_value = (operacion.highest_price - operacion.precio_apertura) * 0.1  # Estimación
                            new_stop = operacion.highest_price - (atr_value * operacion.trailing_multiplier)
                            operacion.stop_loss = max(operacion.stop_loss, new_stop)
                        
                        # Verificar si se debe cerrar
                        if precio_actual <= operacion.stop_loss:
                            profit = operacion.cerrar(operacion.stop_loss, timestamp)
                            self.risk_manager.capital += operacion.riesgo_reservado + profit
                            self.risk_manager.beneficio_total += profit
                            
                            if profit >= 0:
                                self.risk_manager.operaciones_ganadas += 1
                                self.risk_manager.ganancia_ganadoras_total += profit
                            else:
                                self.risk_manager.operaciones_perdidas += 1
                                self.risk_manager.perdida_perdedoras_total += profit
                            
                            operaciones_cerradas.append(operacion)
                            self.risk_manager.operaciones_cerradas.append(operacion)
                            self.risk_manager.operaciones_activas.remove(operacion)
                    
                    # Lógica similar para SELL (cuando se implemente completamente)
                    
        except Exception as e:
            logger.error(f"Error verificando trailing stops: {e}")
        
        return operaciones_cerradas

    def get_metrics(self) -> Dict:
        """Obtiene métricas de rendimiento"""
        with self._lock:
            return {
                'signals_processed': self.metrics.signals_processed,
                'dataframes_processed': self.metrics.dataframes_processed,
                'avg_processing_time': self.metrics.get_avg_processing_time(),
                'errors_count': self.metrics.errors_count,
                'queue_full_count': self.metrics.queue_full_count,
                'uptime_seconds': (datetime.now() - self.metrics.last_reset).total_seconds(),
                'queue_sizes': {
                    'signals': self.signal_queue.qsize(),
                    'dataframes': self.dataframe_queue.qsize()
                }
            }

    def reset_metrics(self):
        """Reinicia las métricas"""
        with self._lock:
            self.metrics.reset()

    def update_config(self, new_config: RiskConfig):
        """Actualiza la configuración en tiempo real"""
        with self._lock:
            self.config = new_config
            logger.info(f"Configuración actualizada: {self.config}")

    def stop(self):
        """Detiene todos los workers de manera satisfactoria"""
        logger.info("Iniciando shutdown satisfactoriamente...")
        
        self._running = False
        self._shutdown_event.set()
        
        # Esperar a que las colas se procesen
        try:
            self.signal_queue.join()
            self.dataframe_queue.join()
        except Exception as e:
            logger.warning(f"Error esperando colas: {e}")
        
        # Esperar a que los threads terminen
        for thread in self._processing_threads:
            thread.join(timeout=2.0)
            if thread.is_alive():
                logger.warning(f"Thread {thread.name} no terminó satisfactoriamente")
        
        # Shutdown de executors
        self.signal_workers.shutdown(wait=True)
        self.dataframe_workers.shutdown(wait=True)
        
        # Guardar estado final
        if self._enable_persistence:
            self._save_state()
        
        logger.info("RiskManagerIntegration detenido satisfactoriamente")

    def __del__(self):
        """Destructor para limpieza"""
        if hasattr(self, '_running') and self._running:
            self.stop()
