# strategies/risk_manager.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Optional
import logging
import warnings
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

        # Cálculo de lote mejorado para BUY y SELL
        if tipo == 'BUY':
            riesgo_por_pip = abs(precio - stop_loss)
        elif tipo == 'SELL':
            riesgo_por_pip = abs(stop_loss - precio)
        else:
            if self.debug_mode:
                self.last_error = f"Tipo de operación inválido: {tipo}"
            return None

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
        return operaciones_cerradas

    def cerrar_operacion_por_estrategia(self, estrategia_nombre, precio_cierre, timestamp, motivo="EXIT_SIGNAL"):
        """Mismo método que original"""
        operaciones_cerradas = []
        for operacion in self.operaciones_activas[:]:
            if operacion.estado == 'ACTIVA' and operacion.estrategia == estrategia_nombre:
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

                if operacion.estrategia:
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
        self.last_error = None