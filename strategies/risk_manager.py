# strategies/risk_manager.py

import pandas as pd
import numpy as np
from datetime import datetime

class Operacion:
    """Clase para representar una operación de trading"""
    def __init__(self, id_operacion, tipo, precio_apertura, timestamp, stop_loss, take_profit, lote_size):
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

    def cerrar(self, precio_cierre, timestamp):
        """Cierra la operación y calcula el resultado"""
        self.precio_cierre = precio_cierre
        self.timestamp_cierre = timestamp
        self.estado = 'CERRADA'
        
        # Validar que los precios sean números válidos
        if (np.isnan(self.precio_apertura) or np.isnan(precio_cierre) or 
            np.isnan(self.lote_size) or self.lote_size <= 0):
            self.resultado = 'PERDIDA'
            return 0.0
        
        if self.tipo == 'BUY':
            profit = (precio_cierre - self.precio_apertura) * self.lote_size
        else:  # SELL
            profit = (self.precio_apertura - precio_cierre) * self.lote_size
            
        # Validar que el profit sea un número válido
        if np.isnan(profit) or np.isinf(profit):
            profit = 0.0
            
        self.resultado = 'GANANCIA' if profit >= 0 else 'PERDIDA'
        return profit

    def __str__(self):
        return f"Operacion {self.id} [{self.tipo}] {self.estado} @ {self.precio_apertura:.5f}"

class RiskManager:
    """Gestiona la apertura y cierre de operaciones con límite máximo"""
    
    def __init__(self, capital_inicial=10000, max_operaciones_activas=5):
        self.capital = capital_inicial
        self.max_operaciones_activas = max_operaciones_activas
        self.operaciones_activas = []
        self.operaciones_cerradas = []
        self.contador_operaciones = 0
        self.beneficio_total = 0
        self.operaciones_ganadas = 0
        self.operaciones_perdidas = 0
        
    def puede_abrir_operacion(self):
        """Verifica si se puede abrir una nueva operación"""
        operaciones_activas = len([op for op in self.operaciones_activas if op.estado == 'ACTIVA'])
        return operaciones_activas < self.max_operaciones_activas
    
    def get_operaciones_activas_count(self):
        """Retorna el número de operaciones activas"""
        return len([op for op in self.operaciones_activas if op.estado == 'ACTIVA'])
    
    def get_slots_disponibles(self):
        """Retorna el número de slots disponibles para nuevas operaciones"""
        return self.max_operaciones_activas - self.get_operaciones_activas_count()
    
    def abrir_operacion(self, tipo, precio, timestamp, stop_loss, take_profit, riesgo_por_operacion=0.01):
        """
        Abre una nueva operación si hay slots disponibles
        """
        if not self.puede_abrir_operacion():
            return None
            
        # Calcular tamaño de lote basado en el riesgo
        if tipo == 'BUY':
            riesgo_por_pip = abs(precio - stop_loss)
        else:  # SELL
            riesgo_por_pip = abs(stop_loss - precio)
            
        # Evitar división por cero y valores inválidos
        if riesgo_por_pip <= 0 or np.isnan(riesgo_por_pip) or np.isinf(riesgo_por_pip):
            return None
            
        riesgo_dinero = self.capital * riesgo_por_operacion
        lote_size = riesgo_dinero / riesgo_por_pip
        
        # Validar que el lote_size sea un número válido
        if np.isnan(lote_size) or np.isinf(lote_size) or lote_size <= 0:
            return None
        
        # Crear nueva operación
        self.contador_operaciones += 1
        operacion = Operacion(
            id_operacion=self.contador_operaciones,
            tipo=tipo,
            precio_apertura=precio,
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lote_size=lote_size
        )
        
        self.operaciones_activas.append(operacion)
        return operacion

    def verificar_cierre_operaciones(self, precio_actual, timestamp):
        """
        Verifica si alguna operación activa debe cerrarse por SL o TP
        
        Returns:
            Lista de operaciones cerradas
        """
        operaciones_cerradas = []
        
        for operacion in self.operaciones_activas:
            if operacion.estado != 'ACTIVA':
                continue
                
            debe_cerrar = False
            precio_cierre = None
            
            if operacion.tipo == 'BUY':
                # Check Take Profit
                if precio_actual >= operacion.take_profit:
                    debe_cerrar = True
                    precio_cierre = operacion.take_profit
                # Check Stop Loss
                elif precio_actual <= operacion.stop_loss:
                    debe_cerrar = True
                    precio_cierre = operacion.stop_loss
                    
            else:  # SELL
                # Check Take Profit
                if precio_actual <= operacion.take_profit:
                    debe_cerrar = True
                    precio_cierre = operacion.take_profit
                # Check Stop Loss
                elif precio_actual >= operacion.stop_loss:
                    debe_cerrar = True
                    precio_cierre = operacion.stop_loss
            
            if debe_cerrar and precio_cierre is not None:
                profit = operacion.cerrar(precio_cierre, timestamp)
                self.capital += profit
                self.beneficio_total += profit
                
                if profit >= 0:
                    self.operaciones_ganadas += 1
                else:
                    self.operaciones_perdidas += 1
                
                operaciones_cerradas.append(operacion)
                self.operaciones_cerradas.append(operacion)
        
        # Remover operaciones cerradas de la lista activa
        self.operaciones_activas = [op for op in self.operaciones_activas if op.estado == 'ACTIVA']
        
        return operaciones_cerradas
    
    def cerrar_operacion_manual(self, id_operacion, precio_cierre, timestamp):
        """Cierra manualmente una operación específica"""
        for operacion in self.operaciones_activas:
            if operacion.id == id_operacion and operacion.estado == 'ACTIVA':
                profit = operacion.cerrar(precio_cierre, timestamp)
                self.capital += profit
                self.beneficio_total += profit
                
                if profit >= 0:
                    self.operaciones_ganadas += 1
                else:
                    self.operaciones_perdidas += 1
                
                self.operaciones_cerradas.append(operacion)
                self.operaciones_activas.remove(operacion)
                return operacion, profit
        
        return None, 0
    
    def get_estadisticas(self):
        """Retorna estadísticas del risk manager"""
        total_operaciones = self.operaciones_ganadas + self.operaciones_perdidas
        win_rate = (self.operaciones_ganadas / total_operaciones * 100) if total_operaciones > 0 else 0
        
        return {
            'capital_actual': self.capital,
            'beneficio_total': self.beneficio_total,
            'operaciones_activas': self.get_operaciones_activas_count(),
            'operaciones_ganadas': self.operaciones_ganadas,
            'operaciones_perdidas': self.operaciones_perdidas,
            'win_rate': win_rate,
            'slots_disponibles': self.get_slots_disponibles(),
            'max_operaciones': self.max_operaciones_activas
        }
    
    def reset(self):
        """Reinicia el risk manager"""
        self.operaciones_activas = []
        self.operaciones_cerradas = []
        self.contador_operaciones = 0
        self.beneficio_total = 0
        self.operaciones_ganadas = 0
        self.operaciones_perdidas = 0

# Ejemplo de uso integrado con las estrategias
class RiskManagerIntegration:
    """Integración del Risk Manager con las estrategias existentes"""
    
    def __init__(self, risk_manager, estrategias):
        self.risk_manager = risk_manager
        self.estrategias = estrategias
        self.senales_pendientes = []

    def procesar_senal(self, senal, precio_actual, timestamp, atr_value, rr_ratio=2):
        """
        Procesa una señal de trading y abre operación si es posible
        """
        if senal == 0 or not self.risk_manager.puede_abrir_operacion():
            return None
        
        tipo = 'BUY' if senal == 1 else 'SELL'
        
        # Validar que atr_value sea un número válido
        if np.isnan(atr_value) or np.isinf(atr_value) or atr_value <= 0:
            # Usar un valor por defecto si ATR no es válido
            atr_value = (precio_actual * 0.001)  # 0.1% del precio como fallback
        
        # Calcular SL y TP basado en ATR
        if tipo == 'BUY':
            stop_loss = precio_actual - (atr_value * 2)  # 2x ATR
            take_profit = precio_actual + (atr_value * 2 * rr_ratio)
        else:  # SELL
            stop_loss = precio_actual + (atr_value * 2)
            take_profit = precio_actual - (atr_value * 2 * rr_ratio)
        
        # Validar que SL y TP sean válidos
        if (np.isnan(stop_loss) or np.isinf(stop_loss) or 
            np.isnan(take_profit) or np.isinf(take_profit)):
            return None
        
        return self.risk_manager.abrir_operacion(
            tipo=tipo,
            precio=precio_actual,
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            riesgo_por_operacion=0.01  # 1% de riesgo por operación
        )    

    def procesar_dataframe(self, df, atr_period=14, rr_ratio=2):
        """
        Procesa un dataframe completo con señales de trading
        """
        resultados = []
        
        for idx, row in df.iterrows():
            # Verificar cierre de operaciones existentes
            operaciones_cerradas = self.risk_manager.verificar_cierre_operaciones(
                row['Close'], idx
            )
            
            # Procesar nueva señal si existe
            if 'Signal' in row and row['Signal'] != 0 and self.risk_manager.puede_abrir_operacion():
                operacion = self.procesar_senal(
                    senal=row['Signal'],
                    precio_actual=row['Close'],
                    timestamp=idx,
                    atr_value=row.get('ATR', (row['High'] - row['Low']).rolling(atr_period).mean().iloc[-1]),
                    rr_ratio=rr_ratio
                )
                
                if operacion:
                    resultados.append({
                        'timestamp': idx,
                        'tipo': 'APERTURA',
                        'operacion': operacion,
                        'precio': row['Close']
                    })
            
            # Registrar operaciones cerradas
            for op in operaciones_cerradas:
                resultados.append({
                    'timestamp': idx,
                    'tipo': 'CIERRE',
                    'operacion': op,
                    'precio': row['Close'],
                    'resultado': op.resultado
                })
        
        return resultados