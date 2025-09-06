# strategies/risk_manager_integration.py

import pandas as pd
import numpy as np
from datetime import datetime

# ---------------- Clase Operacion ----------------
class Operacion:
    """Clase para representar una operación de trading"""
    def __init__(self, id_operacion, tipo, precio_apertura, timestamp,
                 stop_loss, take_profit, lote_size, estrategia: str | None = None):
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
        """Cierra la operación y calcula el resultado"""
        self.precio_cierre = precio_cierre
        self.timestamp_cierre = timestamp
        self.estado = 'CERRADA'

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
    """Gestiona la apertura y cierre de operaciones con límite máximo"""
    def __init__(self, capital_inicial=10000, max_operaciones_activas=5, debug_mode=False):
        self.capital_inicial = capital_inicial
        self.capital = capital_inicial
        self.max_operaciones_activas = max_operaciones_activas
        self.operaciones_activas = []
        self.operaciones_cerradas = []
        self.contador_operaciones = 0
        self.beneficio_total = 0
        self.operaciones_ganadas = 0
        self.operaciones_perdidas = 0
        self.ganancia_ganadoras_total = 0.0
        self.perdida_perdedoras_total = 0.0
        self.last_error: str | None = None
        self.debug_mode = debug_mode
        self.estrategias_buy_activa_notificadas = set()
        self.ultima_vela_buy = None
        self.ultima_vela_mensaje_buy_duplicada = None

    # ---------- Funciones de estado ----------
    def puede_abrir_operacion(self):
        if self.max_operaciones_activas is None or self.max_operaciones_activas <= 0:
            return True
        return len([op for op in self.operaciones_activas if op.estado == 'ACTIVA']) < self.max_operaciones_activas

    def get_operaciones_activas_count(self):
        return len([op for op in self.operaciones_activas if op.estado == 'ACTIVA'])

    def get_slots_disponibles(self):
        if self.max_operaciones_activas is None or self.max_operaciones_activas <= 0:
            return 1_000_000_000
        return self.max_operaciones_activas - self.get_operaciones_activas_count()

    # ---------- Abrir operación ----------
    def abrir_operacion(self, tipo, precio, timestamp, stop_loss, take_profit,
                        riesgo_por_operacion=0.01, estrategia: str | None = None):
        if not self.puede_abrir_operacion():
            self.last_error = "Sin slots disponibles para abrir nueva operación"
            return None

        # Restricciones de unicidad por vela
        if tipo == 'BUY' and self.ultima_vela_buy == timestamp:
            if self.ultima_vela_mensaje_buy_duplicada != timestamp:
                self.last_error = "Ya se abrió una operación BUY en esta vela"
                self.ultima_vela_mensaje_buy_duplicada = timestamp
            return None

        # Restricciones de unicidad por estrategia
        if estrategia is not None:
            for op in self.operaciones_activas:
                if op.estado == 'ACTIVA' and op.estrategia == estrategia:
                    if estrategia not in self.estrategias_buy_activa_notificadas:
                        self.last_error = f"Ya existe operación ACTIVA para la estrategia '{estrategia}'"
                        self.estrategias_buy_activa_notificadas.add(estrategia)
                    return None

        # Calcular lote según riesgo
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

        self.operaciones_activas.append(operacion)
        self.last_error = None
        return operacion

    # ---------- Cerrar operaciones ----------
    def verificar_cierre_operaciones(self, precio_actual, timestamp):
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

    # ---------- Estadísticas ----------
    def get_estadisticas(self):
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
        return self.get_estadisticas()

    def reset(self):
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

# ---------------- Clase RiskManagerIntegration ----------------
class RiskManagerIntegration:
    """Integra RiskManager con señales de estrategia"""
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    def procesar_senal(self, senal, precio_actual, timestamp, atr_value, rr_ratio=2, estrategia_nombre=None):
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
        resultados = []

        for idx, row in df.iterrows():
            # Verificar cierre por SL/TP
            operaciones_cerradas_sltp = self.risk_manager.verificar_cierre_operaciones(row['Close'], idx)
            for op in operaciones_cerradas_sltp:
                resultados.append({'timestamp': idx, 'tipo': 'CIERRE_SL_TP', 'operacion': op, 'precio': row['Close'], 'resultado': op.resultado})

            # Procesar señales
            if 'Signal' in row and row['Signal'] != 0:
                atr_value = row.get('ATR', max(row['High'] - row['Low'], 0.0001))
                resultado_senal = self.procesar_senal(
                    senal=row['Signal'],
                    precio_actual=row['Close'],
                    timestamp=idx,
                    atr_value=atr_value,
                    rr_ratio=rr_ratio,
                    estrategia_nombre=estrategia_nombre
                )
                if resultado_senal is not None:
                    if row['Signal'] == 1 and hasattr(resultado_senal, 'id'):
                        resultados.append({'timestamp': idx, 'tipo': 'APERTURA', 'operacion': resultado_senal, 'precio': row['Close']})
                    elif row['Signal'] == -1 and isinstance(resultado_senal, list):
                        for op in resultado_senal:
                            resultados.append({'timestamp': idx, 'tipo': 'CIERRE_ESTRATEGIA', 'operacion': op, 'precio': row['Close'], 'resultado': op.resultado})
        return resultados
