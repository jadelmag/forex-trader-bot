# strategies/risk_manager.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
from typing import Dict, List, Optional
import logging
import warnings
from collections import defaultdict
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RiskManager')

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

        # Calcular profit usando método centralizado
        profit = self.calcular_profit(precio_cierre)
        self.resultado = 'GANANCIA' if profit >= 0 else 'PERDIDA'
        return profit

    def calcular_profit(self, precio_actual):
        """Método centralizado para calcular profit/loss de una operación"""
        # Validaciones básicas
        if (np.isnan(self.precio_apertura) or np.isnan(precio_actual) or
            np.isnan(self.lote_size) or self.lote_size <= 0):
            return 0.0

        # Cálculo según tipo de operación
        if self.tipo == 'BUY':
            profit = (precio_actual - self.precio_apertura) * self.lote_size
        elif self.tipo == 'SELL':
            profit = (self.precio_apertura - precio_actual) * self.lote_size
        else:
            return 0.0

        # Validar resultado
        if np.isnan(profit) or np.isinf(profit):
            profit = 0.0

        return profit

    def __str__(self):
        return f"Operacion {self.id} [{self.tipo}] {self.estado} @ {self.precio_apertura:.5f}"

# ---------------- Clase RiskManager ----------------
class RiskManager:
    """Gestiona la apertura y cierre de operaciones con límite máximo - Optimizado"""
    
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
        
        # Sistema de seguimiento de estrategias por vela con limpieza automática
        self.estrategias_por_vela = {}  # {timestamp: [estrategia1, estrategia2, ...]}
        self.max_estrategias_por_vela = 3
        self.max_velas_historial = 1000  # Límite para evitar memory leaks
        self.ultima_limpieza = time.time()
        self.intervalo_limpieza = 300  # 5 minutos
        
        # Cache para operaciones activas (optimización de rendimiento)
        self._operaciones_activas_count = 0
        self._cache_dirty = True
        
        # Thread safety completo para todas las estructuras compartidas
        self._main_lock = threading.RLock()  # Lock principal para operaciones críticas
        self._estrategias_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        
        # Sistema de métricas de rendimiento
        self.performance_metrics = {
            'operaciones_abiertas': 0,
            'operaciones_cerradas_total': 0,
            'tiempo_promedio_apertura': 0.0,
            'tiempo_promedio_cierre': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'limpiezas_realizadas': 0,
            'errores_thread_safety': 0
        }
        self._tiempos_operacion = []

    # ---------- Métodos optimizados con cache ----------
    def _actualizar_cache_operaciones_activas(self):
        """Actualiza el cache de operaciones activas"""
        with self._cache_lock:
            if self._cache_dirty:
                self._operaciones_activas_count = len([op for op in self.operaciones_activas if op.estado == 'ACTIVA'])
                self._cache_dirty = False
                self.performance_metrics['cache_misses'] += 1
            else:
                self.performance_metrics['cache_hits'] += 1

    def _invalidar_cache(self):
        """Marca el cache como sucio"""
        with self._cache_lock:
            self._cache_dirty = True

    def puede_abrir_operacion(self):
        """Optimizado con cache"""
        if self.max_operaciones_activas is None or self.max_operaciones_activas <= 0:
            return True
        self._actualizar_cache_operaciones_activas()
        return self._operaciones_activas_count < self.max_operaciones_activas

    def get_operaciones_activas_count(self):
        """Optimizado con cache"""
        self._actualizar_cache_operaciones_activas()
        return self._operaciones_activas_count

    def get_slots_disponibles(self):
        """Optimizado con cache"""
        if self.max_operaciones_activas is None or self.max_operaciones_activas <= 0:
            return 1_000_000_000
        return self.max_operaciones_activas - self.get_operaciones_activas_count()
    
    def _puede_aplicar_estrategia_en_vela(self, timestamp, estrategia):
        """Verifica si se puede aplicar una estrategia en una vela específica"""
        with self._estrategias_lock:
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
        
        with self._estrategias_lock:
            timestamp_key = str(timestamp)
            if timestamp_key not in self.estrategias_por_vela:
                self.estrategias_por_vela[timestamp_key] = []
            
            if estrategia not in self.estrategias_por_vela[timestamp_key]:
                self.estrategias_por_vela[timestamp_key].append(estrategia)
            
            # Limpieza automática para evitar memory leaks
            self._limpiar_estrategias_antiguas()

    def _limpiar_estrategias_antiguas(self):
        """Sistema de limpieza automática para estrategias_por_vela"""
        tiempo_actual = time.time()
        
        # Solo limpiar cada cierto intervalo
        if tiempo_actual - self.ultima_limpieza < self.intervalo_limpieza:
            return
        
        # Si hay demasiadas velas, eliminar las más antiguas
        if len(self.estrategias_por_vela) > self.max_velas_historial:
            # Ordenar por timestamp y mantener solo las más recientes
            timestamps_ordenados = sorted(self.estrategias_por_vela.keys())
            velas_a_eliminar = len(timestamps_ordenados) - self.max_velas_historial
            
            for i in range(velas_a_eliminar):
                del self.estrategias_por_vela[timestamps_ordenados[i]]
            
            self.performance_metrics['limpiezas_realizadas'] += 1
            logger.info(f"Limpieza automática: eliminadas {velas_a_eliminar} velas antiguas")
        
        self.ultima_limpieza = tiempo_actual

    def _validar_parametros_operacion(self, tipo, precio, stop_loss, estrategia):
        """Método centralizado para validar parámetros de operación"""
        # Validar disponibilidad de slots
        if not self.puede_abrir_operacion():
            self.last_error = "Sin slots disponibles para abrir nueva operación"
            return False

        # Validar límites de estrategias por vela
        if estrategia is not None:
            if not self._puede_aplicar_estrategia_en_vela(estrategia[1], estrategia[0]):  # (timestamp, estrategia)
                return False

        # Validar unicidad por estrategia
        if estrategia is not None:
            for op in self.operaciones_activas:
                if op.estado == 'ACTIVA' and op.estrategia == estrategia[0]:
                    if estrategia[0] not in self.estrategias_buy_activa_notificadas:
                        self.last_error = f"Ya existe operación ACTIVA para la estrategia '{estrategia[0]}'"
                        self.estrategias_buy_activa_notificadas.add(estrategia[0])
                    return False

        # Validar tipo de operación
        if tipo not in ['BUY', 'SELL']:
            if self.debug_mode:
                self.last_error = f"Tipo de operación inválido: {tipo}"
            return False

        # Validar capital mínimo
        if self.capital < 100:
            self.last_error = f"Capital insuficiente: ${self.capital:,.2f}"
            return False

        return True

    def _calcular_lote_size(self, tipo, precio, stop_loss, riesgo_por_operacion):
        """Método centralizado para calcular tamaño de lote"""
        if tipo == 'BUY':
            riesgo_por_pip = abs(precio - stop_loss)
        elif tipo == 'SELL':
            riesgo_por_pip = abs(stop_loss - precio)
        else:
            return None, "Tipo de operación inválido"

        if riesgo_por_pip <= 0:
            if self.debug_mode:
                return None, "Parámetros de riesgo inválidos (riesgo_por_pip <= 0)"
            return None, "Riesgo por pip inválido"

        riesgo_dinero = self.capital * riesgo_por_operacion
        lote_size = riesgo_dinero / riesgo_por_pip
        
        if lote_size <= 0:
            if self.debug_mode:
                return None, "Tamaño de lote inválido"
            return None, "Lote size inválido"

        return lote_size, riesgo_dinero

    def abrir_operacion(self, tipo, precio, timestamp, stop_loss, take_profit, riesgo_por_operacion=0.01, estrategia: Optional[str] = None):
        """Optimizado con thread safety y métricas"""
        inicio_tiempo = time.time()
        
        with self._main_lock:
            try:
                # Validar parámetros usando método centralizado
                if not self._validar_parametros_operacion(tipo, precio, stop_loss, (estrategia, timestamp) if estrategia else None):
                    return None

                # Calcular lote usando método centralizado
                lote_size, riesgo_dinero = self._calcular_lote_size(tipo, precio, stop_loss, riesgo_por_operacion)
                if lote_size is None:
                    self.last_error = riesgo_dinero  # riesgo_dinero contiene el mensaje de error
                    return None

                # Crear operación con soporte completo BUY/SELL
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

                # Gestión de capital para ambos tipos de operación
                if tipo == 'BUY':
                    operacion.valor_posicion = float(precio) * float(lote_size)
                    self.capital -= riesgo_dinero
                    self.ultima_vela_buy = timestamp
                elif tipo == 'SELL':
                    operacion.valor_posicion = float(precio) * float(lote_size)
                    self.capital -= riesgo_dinero  # También reservar capital para SELL

                self.operaciones_activas.append(operacion)
                self._invalidar_cache()  # Invalidar cache después de agregar operación
                self.last_error = None
                
                # CORRECCIÓN: Registrar la estrategia SOLO después de confirmar éxito
                # Esto evita que se marque como "aplicada" si la operación falla
                self._registrar_estrategia_en_vela(timestamp, estrategia)
                
                # Métricas de rendimiento
                tiempo_operacion = time.time() - inicio_tiempo
                self._tiempos_operacion.append(tiempo_operacion)
                self.performance_metrics['operaciones_abiertas'] += 1
                
                # Mantener solo los últimos 100 tiempos para el promedio
                if len(self._tiempos_operacion) > 100:
                    self._tiempos_operacion = self._tiempos_operacion[-100:]
                
                self.performance_metrics['tiempo_promedio_apertura'] = sum(self._tiempos_operacion) / len(self._tiempos_operacion)
                
                return operacion
                
            except Exception as e:
                self.performance_metrics['errores_thread_safety'] += 1
                logger.error(f"Error en abrir_operacion: {e}")
                self.last_error = f"Error interno: {str(e)}"
                return None

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
                elif operacion.tipo == 'SELL':
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

                if operacion.estrategia:
                    self.estrategias_buy_activa_notificadas.discard(operacion.estrategia)

                operaciones_cerradas.append(operacion)
                self.operaciones_cerradas.append(operacion)

        self.operaciones_activas = [op for op in self.operaciones_activas if op.estado == 'ACTIVA']
        self._invalidar_cache()
        return operaciones_cerradas

    def _cerrar_operacion_comun(self, operacion, precio_cierre, timestamp, motivo="AUTO_CLOSE"):
        """Método centralizado para cerrar operaciones - elimina duplicación"""
        inicio_tiempo = time.time()
        
        profit = operacion.cerrar(precio_cierre, timestamp)
        
        # Gestión de capital unificada
        if operacion.tipo in ['BUY', 'SELL']:
            self.capital += operacion.riesgo_reservado + profit
        else:
            self.capital += profit
        
        # Actualizar estadísticas
        self.beneficio_total += profit
        if profit >= 0:
            self.operaciones_ganadas += 1
            self.ganancia_ganadoras_total += profit
        else:
            self.operaciones_perdidas += 1
            self.perdida_perdedoras_total += profit

        # Limpiar notificaciones de estrategia
        if operacion.estrategia:
            self.estrategias_buy_activa_notificadas.discard(operacion.estrategia)

        # Agregar motivo de cierre si no existe
        if not hasattr(operacion, 'motivo_cierre'):
            operacion.motivo_cierre = motivo
        
        # Métricas de rendimiento
        tiempo_cierre = time.time() - inicio_tiempo
        self.performance_metrics['operaciones_cerradas_total'] += 1
        
        # Actualizar tiempo promedio de cierre
        if hasattr(self, '_tiempos_cierre'):
            self._tiempos_cierre.append(tiempo_cierre)
            if len(self._tiempos_cierre) > 100:
                self._tiempos_cierre = self._tiempos_cierre[-100:]
            self.performance_metrics['tiempo_promedio_cierre'] = sum(self._tiempos_cierre) / len(self._tiempos_cierre)
        else:
            self._tiempos_cierre = [tiempo_cierre]
            self.performance_metrics['tiempo_promedio_cierre'] = tiempo_cierre
        
        return profit

    def cerrar_operacion_por_estrategia(self, estrategia_nombre, precio_cierre, timestamp, motivo="EXIT_SIGNAL"):
        """Optimizado con thread safety y método centralizado"""
        with self._main_lock:
            try:
                operaciones_cerradas = []
                for operacion in self.operaciones_activas[:]:
                    if operacion.estado == 'ACTIVA' and operacion.estrategia == estrategia_nombre:
                        self._cerrar_operacion_comun(operacion, precio_cierre, timestamp, motivo)
                        operaciones_cerradas.append(operacion)
                        self.operaciones_cerradas.append(operacion)
                        self.operaciones_activas.remove(operacion)
                
                self._invalidar_cache()
                return operaciones_cerradas
                
            except Exception as e:
                self.performance_metrics['errores_thread_safety'] += 1
                logger.error(f"Error en cerrar_operacion_por_estrategia: {e}")
                return []

    def cerrar_operacion_manual(self, id_operacion, precio_cierre, timestamp):
        """Optimizado con thread safety y método centralizado"""
        with self._main_lock:
            try:
                for operacion in self.operaciones_activas:
                    if operacion.id == id_operacion and operacion.estado == 'ACTIVA':
                        profit = self._cerrar_operacion_comun(operacion, precio_cierre, timestamp, "MANUAL")
                        self.operaciones_cerradas.append(operacion)
                        self.operaciones_activas.remove(operacion)
                        self._invalidar_cache()
                        return operacion, profit
                return None, 0
                
            except Exception as e:
                self.performance_metrics['errores_thread_safety'] += 1
                logger.error(f"Error en cerrar_operacion_manual: {e}")
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

    def get_performance_metrics(self):
        """Obtiene métricas de rendimiento del RiskManager"""
        return {
            **self.performance_metrics,
            'operaciones_activas_actuales': self.get_operaciones_activas_count(),
            'velas_en_historial': len(self.estrategias_por_vela),
            'cache_hit_rate': (self.performance_metrics['cache_hits'] / 
                             max(1, self.performance_metrics['cache_hits'] + self.performance_metrics['cache_misses'])) * 100
        }

    def reset(self):
        """Optimizado con thread safety y limpieza completa"""
        with self._main_lock:
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
            self.last_error = None
            
            # Reset de cache y métricas
            self._invalidar_cache()
            self._tiempos_operacion = []
            if hasattr(self, '_tiempos_cierre'):
                self._tiempos_cierre = []
            
            # Reset de métricas de rendimiento
            self.performance_metrics = {
                'operaciones_abiertas': 0,
                'operaciones_cerradas_total': 0,
                'tiempo_promedio_apertura': 0.0,
                'tiempo_promedio_cierre': 0.0,
                'cache_hits': 0,
                'cache_misses': 0,
                'limpiezas_realizadas': 0,
                'errores_thread_safety': 0
            }
            
            self.ultima_limpieza = time.time()