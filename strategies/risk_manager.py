# strategies/risk_manager.py

import pandas as pd
import numpy as np
from datetime import datetime
import threading
import queue
import time
from typing import List, Dict, Any, Optional, Union

# Importar sistema de reports
try:
    from app.reports import trading_reports
except ImportError:
    trading_reports = None

# ---------------- Clase Operacion ----------------
class Operacion:
    """Clase para representar una operación de trading (optimizada)"""
    
    __slots__ = [
        'id', 'tipo', 'precio_apertura', 'precio_cierre', 'timestamp_apertura',
        'timestamp_cierre', 'stop_loss', 'take_profit', 'lote_size', 'estado',
        'resultado', 'riesgo_reservado', 'estrategia', 'valor_posicion', 'report_index'
    ]
    
    def __init__(self, id_operacion, tipo, precio_apertura, timestamp,
                 stop_loss, take_profit, lote_size, estrategia: Optional[str] = None):
        self.id = id_operacion
        self.tipo = tipo  # 'BUY' o 'SELL'
        self.precio_apertura = float(precio_apertura)
        self.precio_cierre = None
        self.timestamp_apertura = timestamp
        self.timestamp_cierre = None
        self.stop_loss = float(stop_loss)
        self.take_profit = float(take_profit)
        self.lote_size = float(lote_size)
        self.estado = 'ACTIVA'  # 'ACTIVA', 'CERRADA', 'CANCELADA'
        self.resultado = None  # 'GANANCIA', 'PERDIDA', None
        self.riesgo_reservado = 0.0
        self.estrategia = estrategia
        self.valor_posicion = 0.0
        self.report_index = None

    def cerrar(self, precio_cierre, timestamp):
        """Cierra la operación y calcula el resultado (optimizado)"""
        self.precio_cierre = float(precio_cierre)
        self.timestamp_cierre = timestamp
        self.estado = 'CERRADA'

        # Validaciones rápidas
        if (np.isnan(self.precio_apertura) or np.isnan(self.precio_cierre) or
            np.isnan(self.lote_size) or self.lote_size <= 0):
            self.resultado = 'PERDIDA'
            return 0.0

        # Cálculo optimizado de profit
        if self.tipo == 'BUY':
            profit = (self.precio_cierre - self.precio_apertura) * self.lote_size
        else:
            profit = (self.precio_apertura - self.precio_cierre) * self.lote_size

        # Validación de resultados numéricos
        if np.isnan(profit) or np.isinf(profit):
            profit = 0.0

        self.resultado = 'GANANCIA' if profit >= 0 else 'PERDIDA'
        return profit

    def __str__(self):
        return f"Operacion {self.id} [{self.tipo}] {self.estado} @ {self.precio_apertura:.5f}"

# ---------------- Clase RiskManager ----------------
class RiskManager:
    """Gestiona la apertura y cierre de operaciones con límite máximo (optimizado)"""
    
    def __init__(self, capital_inicial=10000, max_operaciones_activas=5, debug_mode=False):
        self.capital_inicial = float(capital_inicial)
        self.capital = float(capital_inicial)
        self.max_operaciones_activas = max_operaciones_activas
        self.operaciones_activas = []  # Usar array numpy para mejor performance?
        self.operaciones_cerradas = []
        self.contador_operaciones = 0
        self.beneficio_total = 0.0
        self.operaciones_ganadas = 0
        self.operaciones_perdidas = 0
        self.ganancia_ganadoras_total = 0.0
        self.perdida_perdedoras_total = 0.0
        self.last_error = None
        self.debug_mode = debug_mode
        self.estrategias_buy_activa_notificadas = set()
        self.ultima_vela_buy = None
        self.ultima_vela_mensaje_buy_duplicada = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Cache para estadísticas
        self._estadisticas_cache = None
        self._estadisticas_timestamp = 0
        self._cache_timeout = 1.0  # 1 segundo de cache

    # ---------- Funciones de estado (optimizadas) ----------
    def puede_abrir_operacion(self):
        """Verificación rápida de slots disponibles"""
        with self._lock:
            if self.max_operaciones_activas <= 0:
                return True
            return len(self.operaciones_activas) < self.max_operaciones_activas

    def get_operaciones_activas_count(self):
        """Conteo rápido de operaciones activas"""
        with self._lock:
            return len(self.operaciones_activas)

    def get_slots_disponibles(self):
        """Slots disponibles con caché"""
        with self._lock:
            if self.max_operaciones_activas <= 0:
                return 1_000_000
            return self.max_operaciones_activas - len(self.operaciones_activas)

    # ---------- Abrir operación (optimizada) ----------
    def abrir_operacion(self, tipo, precio, timestamp, stop_loss, take_profit,
                        riesgo_por_operacion=0.01, estrategia: Optional[str] = None):
        """Apertura de operación optimizada con validaciones rápidas"""
        with self._lock:
            if not self.puede_abrir_operacion():
                self.last_error = "Sin slots disponibles para abrir nueva operación"
                return None

            # Restricciones de unicidad por vela (optimizado)
            if tipo == 'BUY':
                if self.ultima_vela_buy == timestamp:
                    if self.ultima_vela_mensaje_buy_duplicada != timestamp:
                        self.last_error = "Ya se abrió una operación BUY en esta vela"
                        self.ultima_vela_mensaje_buy_duplicada = timestamp
                    return None

            # Restricciones de unicidad por estrategia (optimizado)
            if estrategia is not None:
                for op in self.operaciones_activas:
                    if op.estado == 'ACTIVA' and op.estrategia == estrategia:
                        if estrategia not in self.estrategias_buy_activa_notificadas:
                            self.last_error = f"Ya existe operación ACTIVA para la estrategia '{estrategia}'"
                            self.estrategias_buy_activa_notificadas.add(estrategia)
                        return None

            # Cálculos de riesgo optimizados
            precio_f = float(precio)
            stop_loss_f = float(stop_loss)
            take_profit_f = float(take_profit)
            
            if tipo == 'BUY':
                riesgo_por_pip = abs(precio_f - stop_loss_f)
            else:
                riesgo_por_pip = abs(stop_loss_f - precio_f)

            if riesgo_por_pip <= 1e-10:  # Evitar división por cero
                if self.debug_mode:
                    self.last_error = "Parámetros de riesgo inválidos (riesgo_por_pip <= 0)"
                return None

            if self.capital < 100:
                self.last_error = f"Capital insuficiente: ${self.capital:,.2f}"
                return None

            # Cálculo de lote size optimizado
            riesgo_dinero = self.capital * float(riesgo_por_operacion)
            lote_size = riesgo_dinero / riesgo_por_pip
            
            if lote_size <= 1e-10:
                if self.debug_mode:
                    self.last_error = "Tamaño de lote inválido"
                return None

            # Crear operación
            self.contador_operaciones += 1
            operacion = Operacion(
                id_operacion=self.contador_operaciones,
                tipo=tipo,
                precio_apertura=precio_f,
                timestamp=timestamp,
                stop_loss=stop_loss_f,
                take_profit=take_profit_f,
                lote_size=lote_size,
                estrategia=estrategia
            )
            operacion.riesgo_reservado = float(riesgo_dinero)

            # Actualizar capital
            if tipo == 'BUY':
                operacion.valor_posicion = precio_f * lote_size
                self.capital -= riesgo_dinero
                self.ultima_vela_buy = timestamp

            self.operaciones_activas.append(operacion)
            self.last_error = None
            self._estadisticas_cache = None  # Invalidar cache
            
            # Registrar apertura (async para no bloquear)
            if trading_reports is not None:
                operation_type = "COMPRA" if tipo == "BUY" else "VENTA"
                # Ejecutar en thread separado para no bloquear
                threading.Thread(
                    target=self._registrar_apertura_reporte,
                    args=(operacion, operation_type, estrategia, precio_f, take_profit_f, stop_loss_f, timestamp),
                    daemon=True
                ).start()
            
            return operacion

    def _registrar_apertura_reporte(self, operacion, operation_type, estrategia, precio, take_profit, stop_loss, timestamp):
        """Registra apertura en reportes de forma asíncrona"""
        try:
            operacion.report_index = trading_reports.add_operation_open(
                strategy_name=estrategia or "Sin estrategia",
                operation_type=operation_type,
                price=precio,
                take_profit=take_profit,
                stop_loss=stop_loss,
                timestamp=timestamp
            )
        except Exception as e:
            if self.debug_mode:
                print(f"Error registrando apertura en reporte: {e}")

    # ---------- Cerrar operaciones (optimizado) ----------
    def verificar_cierre_operaciones(self, precio_actual, timestamp):
        """Verificación optimizada de cierres por SL/TP"""
        operaciones_cerradas = []
        precio_actual_f = float(precio_actual)
        
        with self._lock:
            # Filtrar solo operaciones activas una vez
            ops_activas = [op for op in self.operaciones_activas if op.estado == 'ACTIVA']
            
            for operacion in ops_activas:
                precio_cierre = None
                
                # Verificación optimizada de condiciones de cierre
                if operacion.tipo == 'BUY':
                    if precio_actual_f >= operacion.take_profit:
                        precio_cierre = operacion.take_profit
                    elif precio_actual_f <= operacion.stop_loss:
                        precio_cierre = operacion.stop_loss
                else:
                    if precio_actual_f <= operacion.take_profit:
                        precio_cierre = operacion.take_profit
                    elif precio_actual_f >= operacion.stop_loss:
                        precio_cierre = operacion.stop_loss

                if precio_cierre is not None:
                    profit = operacion.cerrar(precio_cierre, timestamp)
                    
                    # Actualizar capital y estadísticas
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

                    # Limpiar estrategias activas
                    if operacion.tipo == 'BUY' and operacion.estrategia:
                        self.estrategias_buy_activa_notificadas.discard(operacion.estrategia)

                    # Registrar cierre async
                    if trading_reports is not None and hasattr(operacion, 'report_index'):
                        close_reason = "TAKE PROFIT" if precio_cierre == operacion.take_profit else "STOP LOSS"
                        threading.Thread(
                            target=self._registrar_cierre_reporte,
                            args=(operacion, precio_cierre, close_reason, profit, timestamp),
                            daemon=True
                        ).start()

                    operaciones_cerradas.append(operacion)
                    self.operaciones_cerradas.append(operacion)

            # Actualizar lista de operaciones activas
            self.operaciones_activas = [op for op in self.operaciones_activas if op.estado == 'ACTIVA']
            self._estadisticas_cache = None  # Invalidar cache
            
        return operaciones_cerradas

    def _registrar_cierre_reporte(self, operacion, precio_cierre, close_reason, profit, timestamp):
        """Registra cierre en reportes de forma asíncrona"""
        try:
            trading_reports.add_operation_close(
                operation_index=operacion.report_index,
                close_price=precio_cierre,
                close_reason=close_reason,
                profit_loss=profit,
                timestamp=timestamp
            )
        except Exception as e:
            if self.debug_mode:
                print(f"Error registrando cierre en reporte: {e}")

    def cerrar_operacion_por_estrategia(self, estrategia_nombre, precio_cierre, timestamp, motivo="EXIT_SIGNAL"):
        """Cierre por estrategia optimizado"""
        operaciones_cerradas = []
        precio_cierre_f = float(precio_cierre)
        
        with self._lock:
            ops_a_cerrar = [op for op in self.operaciones_activas 
                           if op.estado == 'ACTIVA' and op.estrategia == estrategia_nombre]
            
            for operacion in ops_a_cerrar:
                profit = operacion.cerrar(precio_cierre_f, timestamp)
                
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

                # Registrar cierre async
                if trading_reports is not None and hasattr(operacion, 'report_index'):
                    threading.Thread(
                        target=self._registrar_cierre_estrategia_reporte,
                        args=(operacion, precio_cierre_f, motivo, profit, timestamp),
                        daemon=True
                    ).start()

                operacion.motivo_cierre = motivo
                operaciones_cerradas.append(operacion)
                self.operaciones_cerradas.append(operacion)
                self.operaciones_activas.remove(operacion)
                
            self._estadisticas_cache = None  # Invalidar cache
            
        return operaciones_cerradas

    def _registrar_cierre_estrategia_reporte(self, operacion, precio_cierre, motivo, profit, timestamp):
        """Registra cierre por estrategia en reportes de forma asíncrona"""
        try:
            trading_reports.add_operation_close(
                operation_index=operacion.report_index,
                close_price=precio_cierre,
                close_reason=f"CIERRE POR ESTRATEGIA ({motivo})",
                profit_loss=profit,
                timestamp=timestamp
            )
        except Exception as e:
            if self.debug_mode:
                print(f"Error registrando cierre por estrategia: {e}")

    def cerrar_operacion_manual(self, id_operacion, precio_cierre, timestamp):
        """Cierre manual optimizado"""
        with self._lock:
            for operacion in self.operaciones_activas:
                if operacion.id == id_operacion and operacion.estado == 'ACTIVA':
                    profit = operacion.cerrar(float(precio_cierre), timestamp)
                    
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

                    # Registrar cierre manual async
                    if trading_reports is not None and hasattr(operacion, 'report_index'):
                        threading.Thread(
                            target=self._registrar_cierre_manual_reporte,
                            args=(operacion, precio_cierre, profit, timestamp),
                            daemon=True
                        ).start()

                    self.operaciones_cerradas.append(operacion)
                    self.operaciones_activas.remove(operacion)
                    self._estadisticas_cache = None  # Invalidar cache
                    
                    return operacion, profit
                    
            return None, 0

    def _registrar_cierre_manual_reporte(self, operacion, precio_cierre, profit, timestamp):
        """Registra cierre manual en reportes de forma asíncrona"""
        try:
            trading_reports.add_operation_close(
                operation_index=operacion.report_index,
                close_price=precio_cierre,
                close_reason="CIERRE MANUAL",
                profit_loss=profit,
                timestamp=timestamp
            )
        except Exception as e:
            if self.debug_mode:
                print(f"Error registrando cierre manual: {e}")

    # ---------- Estadísticas (con cache) ----------
    def get_estadisticas(self):
        """Estadísticas con cache para mejor performance"""
        current_time = time.time()
        
        # Devolver cache si es válida
        if (self._estadisticas_cache is not None and 
            current_time - self._estadisticas_timestamp < self._cache_timeout):
            return self._estadisticas_cache
            
        with self._lock:
            total_operaciones = self.operaciones_ganadas + self.operaciones_perdidas
            win_rate = (self.operaciones_ganadas / total_operaciones * 100) if total_operaciones > 0 else 0
            
            stats = {
                'capital_final': self.capital,
                'beneficio_total': self.beneficio_total,
                'operaciones_activas': len(self.operaciones_activas),
                'operaciones_ganadas': self.operaciones_ganadas,
                'operaciones_perdidas': self.operaciones_perdidas,
                'win_rate': win_rate,
                'slots_utilizados': len(self.operaciones_activas),
                'max_slots': self.max_operaciones_activas,
                'ganancia_ganadoras_total': self.ganancia_ganadoras_total,
                'perdida_perdedoras_total': self.perdida_perdedoras_total
            }
            
            self._estadisticas_cache = stats
            self._estadisticas_timestamp = current_time
            
            return stats

    def obtener_estadisticas(self):
        """Alias para compatibilidad"""
        return self.get_estadisticas()

    def reset(self):
        """Reset optimizado"""
        with self._lock:
            self.capital = self.capital_inicial
            self.operaciones_activas = []
            self.operaciones_cerradas = []
            self.contador_operaciones = 0
            self.beneficio_total = 0.0
            self.operaciones_ganadas = 0
            self.operaciones_perdidas = 0
            self.ganancia_ganadoras_total = 0.0
            self.perdida_perdedoras_total = 0.0
            self.estrategias_buy_activa_notificadas.clear()
            self.ultima_vela_buy = None
            self.ultima_vela_mensaje_buy_duplicada = None
            self._estadisticas_cache = None

# ---------------- Clase RiskManagerIntegration ----------------
class RiskManagerIntegration:
    """Integra RiskManager con señales de estrategia (optimizado)"""
    
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager
        self._procesamiento_activo = False
        self._cola_senales = queue.Queue(maxsize=1000)
        self._procesar_thread = None
        self._detener_procesamiento = False

    def iniciar_procesamiento_async(self):
        """Inicia el procesamiento asíncrono de señales"""
        if self._procesar_thread is None or not self._procesar_thread.is_alive():
            self._detener_procesamiento = False
            self._procesar_thread = threading.Thread(target=self._procesar_senales_worker, daemon=True)
            self._procesar_thread.start()

    def detener_procesamiento(self):
        """Detiene el procesamiento asíncrono"""
        self._detener_procesamiento = True
        if self._procesar_thread and self._procesar_thread.is_alive():
            self._procesar_thread.join(timeout=2.0)

    def _procesar_senales_worker(self):
        """Worker para procesamiento asíncrono de señales"""
        while not self._detener_procesamiento:
            try:
                # Procesar hasta 100 señales por ciclo para no bloquear
                for _ in range(min(100, self._cola_senales.qsize())):
                    if self._detener_procesamiento:
                        return
                        
                    try:
                        senal_data = self._cola_senales.get_nowait()
                        self._procesar_senal_interna(**senal_data)
                        self._cola_senales.task_done()
                    except queue.Empty:
                        break
                
                time.sleep(0.01)  # Pequeña pausa para no saturar CPU
            except Exception as e:
                if self.risk_manager.debug_mode:
                    print(f"Error en procesamiento de señales: {e}")

    def procesar_senal(self, senal, precio_actual, timestamp, atr_value, rr_ratio=2, 
                       estrategia_nombre=None, stop_loss_override=None, take_profit_override=None):
        """Añade señal a la cola de procesamiento (no bloqueante)"""
        if self._detener_procesamiento:
            return None
            
        senal_data = {
            'senal': senal,
            'precio_actual': precio_actual,
            'timestamp': timestamp,
            'atr_value': atr_value,
            'rr_ratio': rr_ratio,
            'estrategia_nombre': estrategia_nombre,
            'stop_loss_override': stop_loss_override,
            'take_profit_override': take_profit_override
        }
        
        try:
            self._cola_senales.put_nowait(senal_data)
            return "SENAL_ENCOLADA"
        except queue.Full:
            if self.risk_manager.debug_mode:
                print("Cola de señales llena, descartando señal")
            return None

    def _procesar_senal_interna(self, senal, precio_actual, timestamp, atr_value, rr_ratio=2, 
                               estrategia_nombre=None, stop_loss_override=None, take_profit_override=None):
        """Procesamiento interno de señales"""
        if senal == 0:
            return None

        # Señal de salida (-1)
        if senal == -1 and estrategia_nombre is not None:
            return self.risk_manager.cerrar_operacion_por_estrategia(
                estrategia_nombre, precio_actual, timestamp, motivo="EXIT_SIGNAL"
            )

        # Señal de entrada (1)
        if senal == 1 and self.risk_manager.puede_abrir_operacion():
            tipo = 'BUY'
            # Usar niveles provenientes de CandleStrategies si están disponibles
            if stop_loss_override is not None and take_profit_override is not None:
                stop_loss = float(stop_loss_override)
                take_profit = float(take_profit_override)
            else:
                stop_loss = precio_actual - (atr_value * 2)
                take_profit = precio_actual + (atr_value * 2 * rr_ratio)
                
            return self.risk_manager.abrir_operacion(
                tipo=tipo,
                precio=precio_actual,
                timestamp=timestamp,
                stop_loss=stop_loss,
                take_profit=take_profit,
                riesgo_por_operacion=0.01,
                estrategia=estrategia_nombre
            )
        return None

    def procesar_dataframe(self, df: pd.DataFrame, atr_period=14, rr_ratio=2, estrategia_nombre=None):
        """Procesamiento optimizado de dataframe"""
        resultados = []
        
        # Pre-calcular ATR si no existe
        if 'ATR' not in df.columns:
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['ATR'] = true_range.rolling(window=atr_period).mean()
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            # Verificar cierre por SL/TP
            operaciones_cerradas_sltp = self.risk_manager.verificar_cierre_operaciones(row['Close'], idx)
            for op in operaciones_cerradas_sltp:
                resultados.append({
                    'timestamp': idx, 
                    'tipo': 'CIERRE_SL_TP', 
                    'operacion': op, 
                    'precio': row['Close'], 
                    'resultado': op.resultado
                })

            # Procesar señales (optimizado)
            signal_value = 0
            if 'ExecSignal' in df.columns and not pd.isna(row.get('ExecSignal', np.nan)):
                signal_value = int(row['ExecSignal'])
            elif 'Signal' in df.columns and not pd.isna(row.get('Signal', np.nan)):
                signal_value = int(row['Signal'])

            if signal_value != 0:
                atr_value = row.get('ATR', max(row['High'] - row['Low'], 0.0001))
                stop_loss_override = row.get('StopLoss', None) if 'StopLoss' in df.columns else None
                take_profit_override = row.get('TakeProfit', None) if 'TakeProfit' in df.columns else None

                resultado_senal = self._procesar_senal_interna(
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

    def __del__(self):
        """Destructor para limpieza"""
        self.detener_procesamiento()