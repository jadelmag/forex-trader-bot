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

        # DEBUG: Log detallado para valores anormales
        if abs(profit) > 50:  # Si el P&L es mayor a 50€, logear detalles
            try:
                import logging
                logger = logging.getLogger('RiskManager')
                logger.warning(f"P&L ANORMAL DETECTADO:")
                logger.warning(f"  Operación ID: {self.id}")
                logger.warning(f"  Tipo: {self.tipo}")
                logger.warning(f"  Precio apertura: {self.precio_apertura:.5f}")
                logger.warning(f"  Precio actual: {precio_actual:.5f}")
                logger.warning(f"  Diferencia: {abs(precio_actual - self.precio_apertura):.5f}")
                logger.warning(f"  Lote size: {self.lote_size:.2f}")
                logger.warning(f"  P&L calculado: {profit:.5f}")
                logger.warning(f"  Estrategia: {getattr(self, 'estrategia', 'N/A')}")
            except Exception:
                pass

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
        self.max_estrategias_por_vela = 20  # Aumentado para permitir más estrategias por vela
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

    def _get_capital_limit(self):
        """Obtiene el límite de capital desde la configuración"""
        try:
            from pathlib import Path
            import json
            
            config_dir = Path(__file__).parent.parent / "config"
            config_file = config_dir / "app_config.json"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return float(config.get('capital_limit', 100))
            else:
                return 100.0  # Valor por defecto
        except Exception:
            return 100.0  # Valor por defecto en caso de error

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
            
            # Contar cuántas veces se ha aplicado esta estrategia en esta vela
            veces_aplicada = estrategias_en_vela.count(estrategia)
            
            # Permitir hasta 3 aplicaciones de la misma estrategia por vela
            if veces_aplicada >= 3:
                self.last_error = f"La estrategia '{estrategia}' ya fue aplicada {veces_aplicada} veces en esta vela (máximo: 3)"
                return False
            
            # Sin límite máximo de estrategias por vela - comentado para permitir ilimitadas
            # if len(estrategias_en_vela) >= self.max_estrategias_por_vela:
            #     self.last_error = f"Máximo de {self.max_estrategias_por_vela} estrategias por vela alcanzado"
            #     return False
            
            return True
    
    def _registrar_estrategia_en_vela(self, timestamp, estrategia):
        """Registra que una estrategia fue aplicada en una vela específica"""
        if estrategia is None:
            return
        
        with self._estrategias_lock:
            timestamp_key = str(timestamp)
            if timestamp_key not in self.estrategias_por_vela:
                self.estrategias_por_vela[timestamp_key] = []
            
            # Permitir múltiples aplicaciones de la misma estrategia
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

        # Validar tipo de operación
        if tipo not in ['BUY', 'SELL']:
            if self.debug_mode:
                self.last_error = f"Tipo de operación inválido: {tipo}"
            return False

        # Validar capital mínimo (configurable)
        capital_limit = self._get_capital_limit()
        if self.capital < capital_limit:
            self.last_error = f"Capital insuficiente: ${self.capital:,.2f} (mínimo: ${capital_limit:,.2f})"
            return False

        return True

    def _calcular_lote_size(self, tipo, precio, stop_loss, riesgo_por_operacion, position_size=None):
        """Método centralizado para calcular tamaño de lote"""
        # Si ya tenemos PositionSize calculado por la estrategia, usarlo directamente
        if position_size is not None and position_size > 0:
            return float(position_size), None
        
        # Fallback: cálculo tradicional con límites para forex
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

        # CORRECCIÓN CRÍTICA: Calcular lote size correcto para forex
        riesgo_dinero = self.capital * riesgo_por_operacion
        
        # NUEVA FÓRMULA CORREGIDA para Forex:
        # 1. Convertir la diferencia de precio a pips (multiplicar por 10,000 para pares con 4 decimales)
        # Para EURUSD: diferencia 0.00047 = 4.7 pips
        pips_de_riesgo = riesgo_por_pip * 10000  # Conversión a pips
        
        # 2. Calcular el valor por pip necesario
        # Si queremos arriesgar 8.32€ en 4.7 pips: valor_por_pip = 8.32 / 4.7 = 1.77€ por pip
        valor_por_pip_necesario = riesgo_dinero / pips_de_riesgo if pips_de_riesgo > 0 else 0
        
        # 3. Calcular el tamaño del lote
        # En Forex, para EURUSD: 1 micro lote (1,000 unidades) = 0.10€ por pip
        # Por tanto: lote_size = valor_por_pip_necesario / 0.0001 (valor de 1 unidad por pip)
        # Simplificado: lote_size = valor_por_pip_necesario * 10000
        lote_size = valor_por_pip_necesario * 10000
        
        # LÍMITES AJUSTADOS para forex: entre 100 y 50,000 unidades
        min_lote_forex = 100     # Mínimo 100 unidades (0.001 lotes estándar)
        max_lote_forex = 50000   # Máximo 50,000 unidades (0.5 lotes estándar)
        
        # Aplicar límites
        if lote_size < min_lote_forex:
            lote_size = min_lote_forex
            if self.debug_mode:
                logger.warning(f"Lote size aumentado a mínimo {min_lote_forex} unidades")
        elif lote_size > max_lote_forex:
            lote_size = max_lote_forex
            if self.debug_mode:
                logger.warning(f"Lote size limitado a máximo {max_lote_forex} unidades")
        
        if lote_size <= 0:
            if self.debug_mode:
                return None, "Lote size calculado <= 0"
            return None, "Lote size inválido"

        # DEBUG: Log detallado del cálculo
        if self.debug_mode:
            logger.info(f"CÁLCULO LOTE SIZE CORREGIDO:")
            logger.info(f"  Capital: {self.capital:.2f}€")
            logger.info(f"  Riesgo %: {riesgo_por_operacion*100:.1f}%")
            logger.info(f"  Riesgo €: {riesgo_dinero:.2f}€")
            logger.info(f"  Precio: {precio:.5f}")
            logger.info(f"  Stop Loss: {stop_loss:.5f}")
            logger.info(f"  Diferencia precio: {riesgo_por_pip:.5f}")
            logger.info(f"  Pips de riesgo: {pips_de_riesgo:.2f}")
            logger.info(f"  Valor por pip necesario: {valor_por_pip_necesario:.4f}€")
            logger.info(f"  Lote size final: {lote_size:.0f} unidades")
            logger.info(f"  Valor real por pip: {lote_size * 0.0001:.4f}€")
            logger.info(f"  Pérdida máxima esperada: {pips_de_riesgo * lote_size * 0.0001:.2f}€")

        return float(lote_size), None

    def _cerrar_operacion_comun(self, operacion, precio_cierre, timestamp, motivo="AUTO_CLOSE"):
        """Método centralizado para cerrar operaciones - Sistema Forex completo"""
        inicio_tiempo = time.time()
        
        profit = operacion.cerrar(precio_cierre, timestamp)
        
        # AUDITORÍA: Registrar evento de cierre
        try:
            import json
            import time as time_module
            audit_entry = {
                "ts": time_module.time(),
                "iso": timestamp.isoformat() + "Z" if hasattr(timestamp, 'isoformat') else f"{timestamp}Z",
                "type": "forex" if not operacion.estrategia.startswith('candle_') else "candle",
                "event": "closed",
                "strategy": operacion.estrategia.replace('forex_', '').replace('candle_', ''),
                "signal": 1 if operacion.tipo == "BUY" else -1,
                "entry_price": float(operacion.precio_apertura),
                "exit_price": float(precio_cierre),
                "profit": float(profit),
                "reason": motivo,
                "risk_percent": 1.0,
                "scenario": getattr(self, 'current_scenario', None)
            }
            
            # Escribir a archivo de auditoría
            from datetime import datetime
            audit_file = f"app/logs/audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry) + '\n')
        except Exception:
            pass
        
        # Log de cierre de operación
        profit_text = f"+{profit:.5f}" if profit >= 0 else f"{profit:.5f}"
        color = "green" if profit >= 0 else "red"
        
        # Importar logger si está disponible
        try:
            from app.gui.handlers.simulation_handler import SimulationHandler
            if hasattr(SimulationHandler, '_current_instance') and SimulationHandler._current_instance:
                handler = SimulationHandler._current_instance
                handler.log(f"🔴 Cierre {operacion.estrategia} {operacion.tipo} @ {precio_cierre:.5f} | P&L: {profit_text} | {motivo}", color)
        except Exception:
            pass
        
        # SISTEMA FOREX CORREGIDO: Gestión precisa de capital
        # El capital ya incluye el riesgo reservado cuando se abre la operación
        # Solo necesitamos aplicar el P&L real de la operación
        
        # CORREGIDO: Devolver el riesgo reservado y aplicar el P&L neto
        self.capital += operacion.riesgo_reservado + profit
        
        # Actualizar estadísticas globales
        self.beneficio_total += profit
        if profit >= 0:
            self.operaciones_ganadas += 1
            self.ganancia_ganadoras_total += profit
        else:
            self.operaciones_perdidas += 1
            self.perdida_perdedoras_total += abs(profit)

        # Actualizar GUI con sistema de beneficios/pérdidas acumuladas (SIN LOG DUPLICADO)
        try:
            from app.gui.handlers.simulation_handler import SimulationHandler
            if hasattr(SimulationHandler, '_current_instance') and SimulationHandler._current_instance:
                handler = SimulationHandler._current_instance
                if hasattr(handler.main_app, 'strategy_handler'):
                    strategy_handler = handler.main_app.strategy_handler
                    
                    # Actualizar dinero ficticio con el nuevo balance
                    strategy_handler.dinero_ficticio = self.capital
                    
                    # Actualizar beneficios y pérdidas ACUMULADAS
                    if profit >= 0:
                        # Sumar a beneficios acumulados
                        if not hasattr(strategy_handler, 'beneficios'):
                            strategy_handler.beneficios = 0.0
                        strategy_handler.beneficios += profit
                    else:
                        # Sumar a pérdidas acumuladas (valor absoluto)
                        if not hasattr(strategy_handler, 'perdidas'):
                            strategy_handler.perdidas = 0.0
                        strategy_handler.perdidas += abs(profit)
                    
                    # Actualizar labels en tiempo real SIN logging adicional
                    strategy_handler.actualizar_labels()
        except Exception:
            pass

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

    def abrir_operacion(self, tipo, precio, timestamp, stop_loss, take_profit, 
                       riesgo_por_operacion=0.01, estrategia=None, position_size=None):
        """
        Abre una nueva operación BUY o SELL
        
        NOTA: Este método es usado SOLO para BACKTESTING con datos PKL/CSV.
        Para trading en tiempo real con Binance, las operaciones se manejan
        a través de risk_manager_integration.py usando el método process_signal().
        """
        with self._main_lock:
            try:
                inicio_tiempo = time.time()
                
                # Validar parámetros
                if not self._validar_parametros_operacion(tipo, precio, stop_loss, (timestamp, estrategia)):
                    return None
                
                # Calcular lote size (usar position_size si está disponible)
                lote_size, error = self._calcular_lote_size(tipo, precio, stop_loss, riesgo_por_operacion, position_size)
                if error:
                    self.last_error = error
                    return None
                
                # DEBUG: Log lote_size para verificar valores
                if self.debug_mode or lote_size > 15000:  # Log si es muy alto
                    logger.info(f"APERTURA - Lote size calculado: {lote_size:.2f}")
                    if position_size:
                        logger.info(f"  Usando PositionSize de estrategia: {position_size}")
                    else:
                        logger.info(f"  Calculado con fallback: riesgo={riesgo_por_operacion*self.capital:.2f} / pip_risk={abs(precio-stop_loss):.5f}")
                    if lote_size > 15000:
                        logger.warning(f"  ⚠️ LOTE_SIZE MUY ALTO: {lote_size:.2f} - Puede causar P&L extremo")
                
                # Reservar capital según tipo
                riesgo_dinero = self.capital * riesgo_por_operacion
                self.capital -= riesgo_dinero
                
                # Crear operación
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
                
                # Guardar riesgo reservado
                operacion.riesgo_reservado = riesgo_dinero
                
                # Añadir a operaciones activas
                self.operaciones_activas.append(operacion)
                self._invalidar_cache()
                
                # Actualizar labels de dinero cuando se abre operación
                try:
                    from app.gui.handlers.simulation_handler import SimulationHandler
                    if hasattr(SimulationHandler, '_current_instance') and SimulationHandler._current_instance:
                        handler = SimulationHandler._current_instance
                        if hasattr(handler.main_app, 'strategy_handler'):
                            strategy_handler = handler.main_app.strategy_handler
                            
                            # Actualizar dinero ficticio con el capital después de reservar riesgo
                            strategy_handler.dinero_ficticio = self.capital
                            
                            # Actualizar labels
                            strategy_handler.actualizar_labels()
                except Exception:
                    pass
                
                # Registrar estrategia si aplica
                if estrategia:
                    self._registrar_estrategia_en_vela(timestamp, estrategia)
                
                # Métricas de rendimiento
                tiempo_apertura = time.time() - inicio_tiempo
                self.performance_metrics['operaciones_abiertas'] += 1
                
                if hasattr(self, '_tiempos_operacion'):
                    self._tiempos_operacion.append(tiempo_apertura)
                    if len(self._tiempos_operacion) > 100:
                        self._tiempos_operacion = self._tiempos_operacion[-100:]
                    self.performance_metrics['tiempo_promedio_apertura'] = sum(self._tiempos_operacion) / len(self._tiempos_operacion)
                else:
                    self._tiempos_operacion = [tiempo_apertura]
                    self.performance_metrics['tiempo_promedio_apertura'] = tiempo_apertura
                
                return operacion
                
            except Exception as e:
                self.performance_metrics['errores_thread_safety'] += 1
                logger.error(f"Error abriendo operación: {e}")
                return None

    def verificar_cierre_operaciones(self, precio_actual, timestamp):
        """
        Verifica y cierra operaciones con lógica inteligente:
        1. Cierre inmediato si profit > 0 (cualquier ganancia)
        2. Cierre si pérdida está muy cerca de 0 (breakeven)
        3. Cierre tradicional por SL/TP
        """
        operaciones_cerradas = []
        
        with self._main_lock:
            try:
                # Usar copia de la lista para modificación segura
                for operacion in self.operaciones_activas[:]:
                    if operacion.estado != 'ACTIVA':
                        continue
                    
                    cierre_requerido = False
                    motivo_cierre = None
                    precio_cierre = precio_actual
                    
                    # LÓGICA INTELIGENTE: Calcular profit actual
                    profit_actual = operacion.calcular_profit(precio_actual)
                    
                    # CONDICIÓN 1: Cerrar si alcanzamos 50% del objetivo TP
                    if profit_actual > 0:
                        # Calcular profit objetivo
                        if operacion.tipo == 'BUY':
                            profit_objetivo = (operacion.take_profit - operacion.precio_apertura) * operacion.lote_size
                        else:  # SELL
                            profit_objetivo = (operacion.precio_apertura - operacion.take_profit) * operacion.lote_size
                        
                        # Solo cerrar si alcanzamos al menos 50% del objetivo
                        if profit_actual >= profit_objetivo * 0.5:
                            cierre_requerido = True
                            motivo_cierre = "PROFIT_PARCIAL_50%"
                    
                    # CONDICIÓN 2: Cerrar si pérdida está muy cerca de 0 (breakeven)
                    elif profit_actual < 0:
                        # Umbral de breakeven: 0.1% del capital o 0.0001 mínimo
                        umbral_breakeven = max(self.capital * 0.001, 0.0001)
                        
                        if abs(profit_actual) <= umbral_breakeven:
                            cierre_requerido = True
                            motivo_cierre = "BREAKEVEN"
                    
                    # CONDICIÓN 3: Lógica tradicional de SL/TP (solo si no se activaron las anteriores)
                    if not cierre_requerido:
                        if operacion.tipo == 'BUY':
                            if precio_actual >= operacion.take_profit:
                                cierre_requerido = True
                                motivo_cierre = "TAKE_PROFIT"
                                precio_cierre = operacion.take_profit
                            elif precio_actual <= operacion.stop_loss:
                                cierre_requerido = True
                                motivo_cierre = "STOP_LOSS"
                                precio_cierre = operacion.stop_loss
                        
                        elif operacion.tipo == 'SELL':
                            if precio_actual <= operacion.take_profit:
                                cierre_requerido = True
                                motivo_cierre = "TAKE_PROFIT"
                                precio_cierre = operacion.take_profit
                            elif precio_actual >= operacion.stop_loss:
                                cierre_requerido = True
                                motivo_cierre = "STOP_LOSS"
                                precio_cierre = operacion.stop_loss
                    
                    # Ejecutar cierre si es necesario
                    if cierre_requerido:
                        # Usar método centralizado para evitar duplicación
                        self._cerrar_operacion_comun(operacion, precio_cierre, timestamp, motivo_cierre)
                        operaciones_cerradas.append(operacion)
                        self.operaciones_cerradas.append(operacion)
                        self.operaciones_activas.remove(operacion)  # Eliminación correcta
                        self._invalidar_cache()
                
                return operaciones_cerradas
                
            except Exception as e:
                self.performance_metrics['errores_thread_safety'] += 1
                logger.error(f"Error en verificar_cierre_operaciones: {e}")
                return []

    def verificar_trailing_stops(self, precio_actual, timestamp, atr_value=None):
        """Verifica y ejecuta trailing stops para operaciones BUY y SELL"""
        operaciones_cerradas = []
        
        try:
            with self._main_lock:
                for operacion in self.operaciones_activas[:]:
                    if not hasattr(operacion, 'trailing_stop_enabled') or not operacion.trailing_stop_enabled:
                        continue
                    
                    if operacion.estado != 'ACTIVA':
                        continue
                    
                    # Obtener multiplicador de trailing (por defecto 1.5)
                    trailing_mult = getattr(operacion, 'trailing_multiplier', 1.5)
                    
                    if operacion.tipo == 'BUY':
                        # Actualizar precio más alto alcanzado
                        if not hasattr(operacion, 'highest_price'):
                            operacion.highest_price = operacion.precio_apertura
                        
                        if precio_actual > operacion.highest_price:
                            operacion.highest_price = precio_actual
                            
                            # Calcular nuevo stop loss usando ATR o estimación
                            if atr_value and atr_value > 0:
                                new_stop = operacion.highest_price - (atr_value * trailing_mult)
                            else:
                                # Estimación basada en movimiento del precio
                                price_movement = operacion.highest_price - operacion.precio_apertura
                                estimated_atr = max(price_movement * 0.1, 0.0001)
                                new_stop = operacion.highest_price - (estimated_atr * trailing_mult)
                            
                            # Solo actualizar si el nuevo stop es mayor (más favorable)
                            operacion.stop_loss = max(operacion.stop_loss, new_stop)
                        
                        # Verificar si se debe cerrar por trailing stop
                        if precio_actual <= operacion.stop_loss:
                            operacion_cerrada = self._cerrar_operacion_comun(
                                operacion, precio_actual, timestamp, "TRAILING_STOP"
                            )
                            if operacion_cerrada:
                                operaciones_cerradas.append(operacion_cerrada)
                    
                    elif operacion.tipo == 'SELL':
                        # Actualizar precio más bajo alcanzado
                        if not hasattr(operacion, 'lowest_price'):
                            operacion.lowest_price = operacion.precio_apertura
                        
                        if precio_actual < operacion.lowest_price:
                            operacion.lowest_price = precio_actual
                            
                            # Calcular nuevo stop loss usando ATR o estimación
                            if atr_value and atr_value > 0:
                                new_stop = operacion.lowest_price + (atr_value * trailing_mult)
                            else:
                                # Estimación basada en movimiento del precio
                                price_movement = operacion.precio_apertura - operacion.lowest_price
                                estimated_atr = max(price_movement * 0.1, 0.0001)
                                new_stop = operacion.lowest_price + (estimated_atr * trailing_mult)
                            
                            # Solo actualizar si el nuevo stop es menor (más favorable)
                            operacion.stop_loss = min(operacion.stop_loss, new_stop)
                        
                        # Verificar si se debe cerrar por trailing stop
                        if precio_actual >= operacion.stop_loss:
                            operacion_cerrada = self._cerrar_operacion_comun(
                                operacion, precio_actual, timestamp, "TRAILING_STOP"
                            )
                            if operacion_cerrada:
                                operaciones_cerradas.append(operacion_cerrada)
                    
        except Exception as e:
            self._thread_errors += 1
            print(f"❌ Error verificando trailing stops: {e}")
        
        return operaciones_cerradas

    def corregir_lote_sizes_activos(self):
        """Corrige lote_sizes extremos en operaciones activas existentes"""
        operaciones_corregidas = 0
        
        with self._main_lock:
            for operacion in self.operaciones_activas:
                if operacion.estado == 'ACTIVA' and operacion.lote_size > 15000:
                    lote_size_original = operacion.lote_size
                    
                    # Aplicar límite máximo
                    operacion.lote_size = min(operacion.lote_size, 10000)
                    
                    operaciones_corregidas += 1
                    logger.warning(f"CORRECCIÓN: Operación {operacion.id} - Lote size {lote_size_original:.2f} → {operacion.lote_size:.2f}")
        
        if operaciones_corregidas > 0:
            logger.info(f"✅ Corregidas {operaciones_corregidas} operaciones con lote_size extremo")
        
        return operaciones_corregidas

    def get_performance_metrics(self) -> dict:
        """Obtiene métricas de rendimiento del RiskManager"""
        with self._main_lock:
            return {
                'operaciones_totales': len(self.operaciones_cerradas) + len(self.operaciones_activas),
                'operaciones_activas': len(self.operaciones_activas),
                'operaciones_cerradas': len(self.operaciones_cerradas),
                'operaciones_ganadas': self.operaciones_ganadas,
                'operaciones_perdidas': self.operaciones_perdidas,
                'beneficio_total': self.beneficio_total,
                'capital_actual': self.capital,
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'cleanup_operations': self._cleanup_count,
                'avg_operation_time': np.mean(self._operation_times) if self._operation_times else 0,
                'thread_errors': self._thread_errors,
                'estrategias_por_vela_count': len(self.estrategias_por_vela)
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