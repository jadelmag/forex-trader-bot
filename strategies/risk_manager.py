# strategies/risk_manager_integration.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import queue
import concurrent.futures
import time
from typing import Dict, List, Optional, Callable, Union
import logging
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RiskManagerIntegration')

# ---------------- Clase Operacion ----------------
class Operacion:
    """Clase para representar una operación de trading - Mismos nombres que original"""
    
    def __init__(self, id_operacion, tipo, precio_apertura, timestamp,
                 stop_loss, take_profit, lote_size, estrategia: Optional[str] = None):
        # Mismos parámetros que la versión original
        self.id = id_operacion
        self.tipo = tipo  # 'BUY' o 'SELL'
        self.precio_apertura = precio_apertura
        self.precio_cierre = None
        self.timestamp_apertura = timestamp
        self.timestamp_cierre = None
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.lote_size = lote_size
        self.estado = 'ACTIVA'  # 'ACTIVA', 'CERRADA', 'CANCELADA'
        self.resultado = None  # 'GANANCIA', 'PERDIDA', None
        self.riesgo_reservado = 0.0
        self.estrategia = estrategia
        self.valor_posicion = 0.0

    def cerrar(self, precio_cierre, timestamp):
        """Cierra la operación y calcula el resultado - Mismo método que original"""
        self.precio_cierre = precio_cierre
        self.timestamp_cierre = timestamp
        self.estado = 'CERRADA'

        # Misma lógica de cálculo que original
        if (np.isnan(self.precio_apertura) or np.isnan(precio_cierre) or
            np.isnan(self.lote_size) or self.lote_size <= 0):
            self.resultado = 'PERDIDA'
            return 0.0

        if self.tipo == 'BUY':
            profit = (precio_cierre - self.precio_apertura) * self.lote_size
        else:
            profit = (self.precio_apertura - precio_cierre) * self.lote_size

        if np.isnan(profit) or np.isinf(profit):
            profit = 0.0

        self.resultado = 'GANANCIA' if profit >= 0 else 'PERDIDA'
        return profit

    def __str__(self):
        return f"Operacion {self.id} [{self.tipo}] {self.estado} @ {self.precio_apertura:.5f}"

# ---------------- Clase RiskManager ----------------
class RiskManager:
    """Gestiona la apertura y cierre de operaciones con límite máximo - Mismos nombres"""
    
    def __init__(self, capital_inicial=10000, max_operaciones_activas=5, debug_mode=False):
        # Mismos parámetros que original
        self.capital_inicial = capital_inicial
        self.capital = capital_inicial
        self.max_operaciones_activas = max_operaciones_activas
        self.debug_mode = debug_mode
        
        # Mismas estructuras de datos que original
        self.operaciones_activas = []
        self.operaciones_cerradas = []
        self.contador_operaciones = 0
        self.beneficio_total = 0
        self.operaciones_ganadas = 0
        self.operaciones_perdidas = 0
        self.ganancia_ganadoras_total = 0.0
        self.perdida_perdedoras_total = 0.0
        self.last_error = None
        self.estrategias_buy_activa_notificadas = set()
        self.ultima_vela_buy = None
        self.ultima_vela_mensaje_buy_duplicada = None
        
        # Sistema de seguimiento de estrategias por vela
        self.estrategias_por_vela = {}  # {timestamp: [estrategia1, estrategia2, ...]}
        self.max_estrategias_por_vela = 3

    # ---------- Mismos métodos de estado que original ----------
    def puede_abrir_operacion(self):
        """Mismo método que original"""
        if self.max_operaciones_activas is None or self.max_operaciones_activas <= 0:
            return True
        return len([op for op in self.operaciones_activas if op.estado == 'ACTIVA']) < self.max_operaciones_activas

    def get_operaciones_activas_count(self):
        """Mismo método que original"""
        return len([op for op in self.operaciones_activas if op.estado == 'ACTIVA'])

    def get_slots_disponibles(self):
        """Mismo método que original"""
        if self.max_operaciones_activas is None or self.max_operaciones_activas <= 0:
            return 1_000_000_000
        return self.max_operaciones_activas - self.get_operaciones_activas_count()
    
    def _puede_aplicar_estrategia_en_vela(self, timestamp, estrategia):
        """Verifica si se puede aplicar una estrategia en una vela específica"""
        # Convertir timestamp a string para usar como clave
        timestamp_key = str(timestamp)
        
        # Obtener estrategias ya aplicadas en esta vela
        estrategias_en_vela = self.estrategias_por_vela.get(timestamp_key, [])
        
        # Verificar si ya se aplicó esta estrategia en esta vela
        if estrategia in estrategias_en_vela:
            self.last_error = f"La estrategia '{estrategia}' ya fue aplicada en esta vela"
            return False
        
        # Verificar si ya se alcanzó el máximo de estrategias por vela
        if len(estrategias_en_vela) >= self.max_estrategias_por_vela:
            self.last_error = f"Máximo de {self.max_estrategias_por_vela} estrategias por vela alcanzado"
            return False
        
        return True
    
    def _registrar_estrategia_en_vela(self, timestamp, estrategia):
        """Registra que una estrategia fue aplicada en una vela específica"""
        if estrategia is None:
            return
        
        timestamp_key = str(timestamp)
        if timestamp_key not in self.estrategias_por_vela:
            self.estrategias_por_vela[timestamp_key] = []
        
        if estrategia not in self.estrategias_por_vela[timestamp_key]:
            self.estrategias_por_vela[timestamp_key].append(estrategia)

    def abrir_operacion(self, tipo, precio, timestamp, stop_loss, take_profit, riesgo_por_operacion=0.01, estrategia: Optional[str] = None):
        """Mismo método que original - mismos parámetros"""
        if not self.puede_abrir_operacion():
            self.last_error = "Sin slots disponibles para abrir nueva operación"
            return None

        # Verificar límites de estrategias por vela
        if estrategia is not None:
            if not self._puede_aplicar_estrategia_en_vela(timestamp, estrategia):
                return None

        # Restricciones de unicidad por estrategia (misma lógica)
        if estrategia is not None:
            for op in self.operaciones_activas:
                if op.estado == 'ACTIVA' and op.estrategia == estrategia:
                    if estrategia not in self.estrategias_buy_activa_notificadas:
                        self.last_error = f"Ya existe operación ACTIVA para la estrategia '{estrategia}'"
                        self.estrategias_buy_activa_notificadas.add(estrategia)
                    return None

        # Cálculo de lote (misma lógica)
        if tipo == 'BUY':
            riesgo_por_pip = abs(precio - stop_loss)
        else:
            riesgo_por_pip = abs(stop_loss - precio)

        if riesgo_por_pip <= 0:
            if self.debug_mode:
                self.last_error = "Parámetros de riesgo inválidos (riesgo_por_pip <= 0)"
            return None

        if self.capital < 100:
            self.last_error = f"Capital insuficiente: ${self.capital:,.2f}"
            return None

        riesgo_dinero = self.capital * riesgo_por_operacion
        lote_size = riesgo_dinero / riesgo_por_pip
        if lote_size <= 0:
            if self.debug_mode:
                self.last_error = "Tamaño de lote inválido"
            return None

        # Crear operación (misma lógica)
        self.contador_operaciones += 1
        operacion = Operacion(
            id_operacion=self.contador_operaciones,
            tipo=tipo,
            precio_apertura=precio,
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lote_size=lote_size,
            estrategia=estrategia
        )
        operacion.riesgo_reservado = float(riesgo_dinero)

        if tipo == 'BUY':
            operacion.valor_posicion = float(precio) * float(lote_size)
            self.capital -= riesgo_dinero
            self.ultima_vela_buy = timestamp

        # Registrar la estrategia en esta vela
        self._registrar_estrategia_en_vela(timestamp, estrategia)
        
        self.operaciones_activas.append(operacion)
        self.last_error = None
        
        return operacion

    def verificar_cierre_operaciones(self, precio_actual, timestamp):
        """Mismo método que original"""
        operaciones_cerradas = []
        for operacion in self.operaciones_activas:
            if operacion.estado != 'ACTIVA':
                continue

            precio_cierre = None
            if operacion.tipo == 'BUY':
                if precio_actual >= operacion.take_profit:
                    precio_cierre = operacion.take_profit
                elif precio_actual <= operacion.stop_loss:
                    precio_cierre = operacion.stop_loss
            else:
                if precio_actual <= operacion.take_profit:
                    precio_cierre = operacion.take_profit
                elif precio_actual >= operacion.stop_loss:
                    precio_cierre = operacion.stop_loss

            if precio_cierre is not None:
                profit = operacion.cerrar(precio_cierre, timestamp)
                if operacion.tipo == 'BUY':
                    self.capital += operacion.riesgo_reservado + profit
                else:
                    self.capital += profit
                self.beneficio_total += profit

                if profit >= 0:
                    self.operaciones_ganadas += 1
                    self.ganancia_ganadoras_total += profit
                else:
                    self.operaciones_perdidas += 1
                    self.perdida_perdedoras_total += profit

                if operacion.tipo == 'BUY' and operacion.estrategia:
                    self.estrategias_buy_activa_notificadas.discard(operacion.estrategia)

                operaciones_cerradas.append(operacion)
                self.operaciones_cerradas.append(operacion)

        self.operaciones_activas = [op for op in self.operaciones_activas if op.estado == 'ACTIVA']
        return operaciones_cerradas

    def cerrar_operacion_por_estrategia(self, estrategia_nombre, precio_cierre, timestamp, motivo="EXIT_SIGNAL"):
        """Mismo método que original"""
        operaciones_cerradas = []
        for operacion in self.operaciones_activas[:]:
            if operacion.estado == 'ACTIVA' and operacion.estrategia == estrategia_nombre:
                profit = operacion.cerrar(precio_cierre, timestamp)
                if operacion.tipo == 'BUY':
                    self.capital += operacion.riesgo_reservado + profit
                else:
                    self.capital += profit

                self.beneficio_total += profit
                if profit >= 0:
                    self.operaciones_ganadas += 1
                    self.ganancia_ganadoras_total += profit
                else:
                    self.operaciones_perdidas += 1
                    self.perdida_perdedoras_total += profit

                if operacion.tipo == 'BUY' and operacion.estrategia:
                    self.estrategias_buy_activa_notificadas.discard(operacion.estrategia)

                operacion.motivo_cierre = motivo
                operaciones_cerradas.append(operacion)
                self.operaciones_cerradas.append(operacion)
                self.operaciones_activas.remove(operacion)
        return operaciones_cerradas

    def cerrar_operacion_manual(self, id_operacion, precio_cierre, timestamp):
        """Mismo método que original"""
        for operacion in self.operaciones_activas:
            if operacion.id == id_operacion and operacion.estado == 'ACTIVA':
                profit = operacion.cerrar(precio_cierre, timestamp)
                if operacion.tipo == 'BUY':
                    self.capital += operacion.riesgo_reservado + profit
                else:
                    self.capital += profit
                self.beneficio_total += profit

                if profit >= 0:
                    self.operaciones_ganadas += 1
                    self.ganancia_ganadoras_total += profit
                else:
                    self.operaciones_perdidas += 1
                    self.perdida_perdedoras_total += profit

                if operacion.tipo == 'BUY' and operacion.estrategia:
                    self.estrategias_buy_activa_notificadas.discard(operacion.estrategia)

                self.operaciones_cerradas.append(operacion)
                self.operaciones_activas.remove(operacion)
                return operacion, profit
        return None, 0

    # ---------- Mismos métodos de estadísticas que original ----------
    def get_estadisticas(self):
        """Mismo método que original"""
        total_operaciones = self.operaciones_ganadas + self.operaciones_perdidas
        win_rate = (self.operaciones_ganadas / total_operaciones * 100) if total_operaciones > 0 else 0
        return {
            'capital_final': self.capital,
            'beneficio_total': self.beneficio_total,
            'operaciones_activas': self.get_operaciones_activas_count(),
            'operaciones_ganadas': self.operaciones_ganadas,
            'operaciones_perdidas': self.operaciones_perdidas,
            'win_rate': win_rate,
            'slots_utilizados': self.get_operaciones_activas_count(),
            'max_slots': self.max_operaciones_activas,
            'ganancia_ganadoras_total': self.ganancia_ganadoras_total,
            'perdida_perdedoras_total': self.perdida_perdedoras_total
        }

    def obtener_estadisticas(self):
        """Mismo método que original"""
        return self.get_estadisticas()

    def reset(self):
        """Mismo método que original"""
        self.capital = self.capital_inicial
        self.operaciones_activas = []
        self.operaciones_cerradas = []
        self.contador_operaciones = 0
        self.beneficio_total = 0
        self.operaciones_ganadas = 0
        self.operaciones_perdidas = 0
        self.ganancia_ganadoras_total = 0.0
        self.perdida_perdedoras_total = 0.0
        self.estrategias_buy_activa_notificadas.clear()
        self.ultima_vela_buy = None
        self.ultima_vela_mensaje_buy_duplicada = None
        self.estrategias_por_vela.clear()

# ---------------- Clase RiskManagerIntegration ----------------
class RiskManagerIntegration:
    """Integra RiskManager con señales de estrategia - Versión Optimizada"""
    
    def __init__(self, risk_manager, debug_mode=False):
        self.risk_manager = risk_manager
        self.debug_mode = debug_mode
        
        # Sistema de colas para procesamiento paralelo
        self.signal_queue = queue.Queue(maxsize=2000)
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
        
        # Iniciar workers
        self._start_workers()
        
        logger.info("RiskManagerIntegration optimizado iniciado")

    def _start_workers(self):
        """Inicia todos los workers de procesamiento"""
        # Worker de procesamiento de señales
        for i in range(2):
            thread = threading.Thread(target=self._signal_processing_worker, daemon=True, name=f"SignalProcessor-{i}")
            thread.start()
            self._processing_threads.append(thread)
        
        # Worker de procesamiento de dataframes
        thread = threading.Thread(target=self._dataframe_processing_worker, daemon=True, name="DataFrameProcessor")
        thread.start()
        self._processing_threads.append(thread)

    def _signal_processing_worker(self):
        """Worker para procesamiento de señales individuales"""
        while self._running:
            try:
                signal_data = self.signal_queue.get(timeout=0.1)
                self._process_single_signal(signal_data)
                self.signal_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error en signal processing worker: {e}")

    def _dataframe_processing_worker(self):
        """Worker para procesamiento de dataframes completos"""
        while self._running:
            try:
                df_data = self.dataframe_queue.get(timeout=0.1)
                self._process_dataframe_batch(df_data)
                self.dataframe_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error en dataframe processing worker: {e}")

    def procesar_senal(self, senal, precio_actual, timestamp, atr_value, rr_ratio=2, estrategia_nombre=None,
                       stop_loss_override=None, take_profit_override=None, sync_mode=False):
        """Procesa una señal de trading de manera asíncrona o síncrona - Mismo nombre que original"""
        if not self._running:
            return None

        signal_data = {
            'senal': senal,
            'precio_actual': float(precio_actual),
            'timestamp': timestamp,
            'atr_value': float(atr_value),
            'rr_ratio': float(rr_ratio),
            'estrategia_nombre': estrategia_nombre,
            'stop_loss_override': float(stop_loss_override) if stop_loss_override else None,
            'take_profit_override': float(take_profit_override) if take_profit_override else None
        }

        # Si se solicita modo síncrono (para GUI), procesar inmediatamente
        if sync_mode:
            return self._process_single_signal(signal_data)

        try:
            self.signal_queue.put_nowait(signal_data)
            return "SENAL_ENCOLADA"
        except queue.Full:
            if self.debug_mode:
                logger.warning("Cola de señales llena")
            return None

    def _process_single_signal(self, signal_data: Dict):
        """Procesa una señal individual de manera optimizada"""
        try:
            senal = signal_data['senal']
            precio_actual = signal_data['precio_actual']
            timestamp = signal_data['timestamp']
            atr_value = signal_data['atr_value']
            rr_ratio = signal_data['rr_ratio']
            estrategia_nombre = signal_data['estrategia_nombre']
            stop_loss_override = signal_data['stop_loss_override']
            take_profit_override = signal_data['take_profit_override']

            # Señal de salida (-1) - Misma lógica que original
            if senal == -1 and estrategia_nombre is not None:
                operaciones_cerradas = self.risk_manager.cerrar_operacion_por_estrategia(
                    estrategia_nombre, precio_actual, timestamp, motivo="EXIT_SIGNAL"
                )
                return operaciones_cerradas

            # Señal de entrada (1) - Misma lógica que original
            if senal == 1 and self.risk_manager.puede_abrir_operacion():
                tipo = 'BUY'
                
                # Usar niveles override si están disponibles
                if stop_loss_override is not None and take_profit_override is not None:
                    stop_loss = stop_loss_override
                    take_profit = take_profit_override
                else:
                    stop_loss = precio_actual - (atr_value * 2)
                    take_profit = precio_actual + (atr_value * 2 * rr_ratio)
                
                # Abrir operación usando el risk manager
                operacion = self.risk_manager.abrir_operacion(
                    tipo=tipo,
                    precio=precio_actual,
                    timestamp=timestamp,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    riesgo_por_operacion=0.01,
                    estrategia=estrategia_nombre
                )
                
                return operacion
                
            return None

        except Exception as e:
            logger.error(f"Error procesando señal individual: {e}")
            return None

    def procesar_dataframe(self, df: pd.DataFrame, atr_period=14, rr_ratio=2, estrategia_nombre=None):
        """Procesa un dataframe completo de manera asíncrona - Mismo nombre que original"""
        if not self._running:
            return []

        # Preparar datos para procesamiento batch
        df_data = {
            'df': df.copy(),
            'atr_period': atr_period,
            'rr_ratio': rr_ratio,
            'estrategia_nombre': estrategia_nombre
        }

        try:
            self.dataframe_queue.put_nowait(df_data)
            return [{'status': 'DATAFRAME_ENCOLADO'}]
        except queue.Full:
            if self.debug_mode:
                logger.warning("Cola de señales llena")
            return [{'status': 'COLA_LLENA'}]

    def _process_dataframe_batch(self, df_data: Dict):
        """Procesa un dataframe completo de manera optimizada"""
        try:
            df = df_data['df']
            atr_period = df_data['atr_period']
            rr_ratio = df_data['rr_ratio']
            estrategia_nombre = df_data['estrategia_nombre']
            
            resultados = []

            # Calcular ATR si no existe - Misma lógica que original
            if 'ATR' not in df.columns:
                high = df['High'].astype(float)
                low = df['Low'].astype(float)
                close = df['Close'].astype(float)
                
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = np.maximum(np.maximum(tr1, tr2), tr3)
                
                df['ATR'] = tr.rolling(window=atr_period).mean()

            # Procesar cada fila del dataframe - Misma lógica que original
            for idx, row in df.iterrows():
                # Verificar cierre por SL/TP (usando risk manager)
                operaciones_cerradas = self.risk_manager.verificar_cierre_operaciones(row['Close'], idx)
                
                for op in operaciones_cerradas:
                    resultados.append({
                        'timestamp': idx, 
                        'tipo': 'CIERRE_SL_TP', 
                        'operacion': op, 
                        'precio': row['Close'], 
                        'resultado': op.resultado
                    })

                # Procesar señales del dataframe - Misma lógica que original
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

                    # Procesar señal individual
                    resultado_senal = self.procesar_senal(
                        senal=signal_value,
                        precio_actual=row['Close'],
                        timestamp=idx,
                        atr_value=atr_value,
                        rr_ratio=rr_ratio,
                        estrategia_nombre=estrategia_nombre,
                        stop_loss_override=stop_loss_override,
                        take_profit_override=take_profit_override
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

    def stop(self):
        """Detiene todos los workers - Nuevo método para limpieza"""
        self._running = False
        
        # Esperar a que las colas se procesen
        time.sleep(0.2)
        
        # Shutdown de executors
        self.signal_workers.shutdown(wait=False)
        self.dataframe_workers.shutdown(wait=False)
        
        logger.info("RiskManagerIntegration detenido")

    # Métodos de compatibilidad para mantener la misma interfaz
    def __del__(self):
        """Destructor para limpieza"""
        self.stop()


        """Destructor para limpieza"""
        self.detener_procesamiento()