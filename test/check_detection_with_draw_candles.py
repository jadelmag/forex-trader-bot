#!/usr/bin/env python3
# test/check_detection_with_draw_candles.py

"""
Test completo de detección de patrones con simulación CSV
Carga datos CSV y simula el flujo completo de trading con:
- 10 slots para estrategias forex
- 10 slots para candle strategies  
- Control de tipo de mercado
- Apertura de operaciones short y long
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading
from typing import Dict, List, Any

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports del proyecto
from strategies.strategies import ForexStrategies
from strategies.candle_strategies import CandleStrategies
from strategies.market_strategy_mapper import MarketStrategyMapper
from app.market_scene_detector import ForexMarketAnalyzer, MarketScenario
from patterns.candlestickpatterns import CandlestickPatterns

class SimpleSlotManager:
    """Gestor de slots simplificado para testing"""
    
    def __init__(self, max_forex_slots=10, max_candle_slots=10):
        self.max_forex_slots = max_forex_slots
        self.max_candle_slots = max_candle_slots
        self.forex_trades = {}
        self.candle_trades = {}
    
    def can_open_trade(self, trade_type):
        """Verifica si se puede abrir una operación del tipo especificado"""
        if trade_type == "FOREX":
            return len(self.forex_trades) < self.max_forex_slots
        else:
            return len(self.candle_trades) < self.max_candle_slots
    
    def open_trade(self, trade_id, trade_type):
        """Abre una operación y reserva el slot"""
        if not self.can_open_trade(trade_type):
            return False
        
        if trade_type == "FOREX":
            self.forex_trades[trade_id] = True
        else:
            self.candle_trades[trade_id] = True
        return True
    
    def close_trade(self, trade_id, trade_type):
        """Cierra una operación y libera el slot"""
        if trade_type == "FOREX" and trade_id in self.forex_trades:
            del self.forex_trades[trade_id]
        elif trade_type == "CANDLE" and trade_id in self.candle_trades:
            del self.candle_trades[trade_id]
    
    def get_used_slots(self, trade_type):
        """Obtiene el número de slots utilizados"""
        if trade_type == "FOREX":
            return len(self.forex_trades)
        else:
            return len(self.candle_trades)

class TradingTestSimulator:
    """Simulador de trading para testing completo"""
    
    def __init__(self):
        self.csv_file = "trading_view/trade_view_csv/EURUSDT_data.csv"
        self.symbol = "EURUSDT"
        
        # Componentes principales
        self.market_detector = ForexMarketAnalyzer()
        self.strategy_mapper = MarketStrategyMapper()
        self.candlestick_patterns = None  # Se inicializará cuando tengamos datos
        
        # Gestión de slots y riesgo
        self.slot_manager = SimpleSlotManager(
            max_forex_slots=10,
            max_candle_slots=10
        )
        
        # Configuración de riesgo simplificada para testing
        self.risk_config = {
            'max_risk_per_trade': 0.02,
            'stop_loss_atr_mult': 2.0,
            'take_profit_atr_mult': 4.0,
            'position_size': 1.0
        }
        
        # Datos y estado
        self.df = None
        self.current_market_scenario = MarketScenario.RANGING
        self.active_trades = {}
        self.trade_history = []
        self.processed_candles = 0
        
        # Estadísticas
        self.stats = {
            'total_signals': 0,
            'forex_signals': 0,
            'candle_signals': 0,
            'long_trades': 0,
            'short_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'market_scenarios': {}
        }
        
    def load_csv_data(self) -> bool:
        """Carga los datos del archivo CSV"""
        try:
            if not os.path.exists(self.csv_file):
                print(f"❌ Archivo CSV no encontrado: {self.csv_file}")
                return False
                
            self.df = pd.read_csv(self.csv_file)
            self.df['Date'] = pd.to_datetime(self.df['Date'])
            self.df.set_index('Date', inplace=True)
            self.df.sort_index(inplace=True)
            
            # Estandarizar nombres de columnas para compatibilidad con ForexMarketAnalyzer
            column_mapping = {
                'Open': 'open',
                'High': 'high', 
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }
            self.df.rename(columns=column_mapping, inplace=True)
            
            print(f"✅ Cargados {len(self.df)} registros desde {self.csv_file}")
            print(f"📊 Rango de fechas: {self.df.index[0]} a {self.df.index[-1]}")
            print(f"📈 Precio inicial: {self.df['close'].iloc[0]:.5f}")
            print(f"📈 Precio final: {self.df['close'].iloc[-1]:.5f}")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando CSV: {e}")
            return False
    
    def detect_market_scenario(self, df_window: pd.DataFrame) -> MarketScenario:
        """Detecta el escenario de mercado actual"""
        try:
            if len(df_window) < 20:  # Necesitamos al menos 20 velas
                return MarketScenario.RANGING
                
            analysis = self.market_detector.analyze_market(df_window)
            scenario = analysis.get('primary_scenario', MarketScenario.RANGING)
            
            # Actualizar estadísticas
            scenario_name = scenario.name
            if scenario_name not in self.stats['market_scenarios']:
                self.stats['market_scenarios'][scenario_name] = 0
            self.stats['market_scenarios'][scenario_name] += 1
            
            return scenario
            
        except Exception as e:
            print(f"⚠️ Error detectando escenario de mercado: {e}")
            return MarketScenario.SIDEWAYS
    
    def get_active_strategies(self, market_scenario: MarketScenario) -> Dict[str, Any]:
        """Obtiene las estrategias activas según el escenario de mercado"""
        try:
            # Estrategias de velas (candle patterns)
            candle_strategies = self.strategy_mapper.get_prioritized_strategies(
                market_scenario
            )
            
            # Estrategias forex (técnicas)
            forex_strategies = self.strategy_mapper.get_prioritized_forex_strategies(
                market_scenario
            )
            
            return {
                'candle': candle_strategies,
                'forex': forex_strategies
            }
            
        except Exception as e:
            print(f"⚠️ Error obteniendo estrategias activas: {e}")
            return {'candle': [], 'forex': []}
    
    def analyze_candle_patterns(self, df_window: pd.DataFrame) -> List[Dict]:
        """Analiza patrones de velas en la ventana actual"""
        signals = []
        
        try:
            if len(df_window) < 3:
                return signals
            
            # Inicializar CandlestickPatterns si no existe
            if self.candlestick_patterns is None:
                # Crear copia con nombres de columnas capitalizados para CandlestickPatterns
                df_candle = df_window.copy()
                df_candle.rename(columns={
                    'open': 'Open',
                    'high': 'High', 
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }, inplace=True)
                self.candlestick_patterns = CandlestickPatterns(df_candle)
            
            # Crear copia con nombres capitalizados para el análisis actual
            df_candle_current = df_window.copy()
            df_candle_current.rename(columns={
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            
            # Detectar patrones principales
            patterns_to_check = [
                'bullish_engulfing', 'bearish_engulfing',
                'hammer', 'hanging_man',
                'doji', 'spinning_top',
                'morning_star', 'evening_star',
                'three_white_soldiers', 'three_black_crows'
            ]
            
            for pattern in patterns_to_check:
                try:
                    if hasattr(self.candlestick_patterns, pattern):
                        result = getattr(self.candlestick_patterns, pattern)(df_candle_current)
                        
                        if result and len(result) > 0:
                            # Tomar la señal más reciente
                            latest_signal = result.iloc[-1] if hasattr(result, 'iloc') else result[-1]
                            
                            if latest_signal:
                                signal_type = 'LONG' if 'bullish' in pattern or pattern in ['hammer', 'morning_star', 'three_white_soldiers'] else 'SHORT'
                                
                                signals.append({
                                    'type': 'CANDLE',
                                    'strategy': pattern,
                                    'direction': signal_type,
                                    'timestamp': df_window.index[-1],
                                    'price': df_window['close'].iloc[-1],
                                    'confidence': 0.7,  # Confianza base para patrones
                                    'pattern_data': latest_signal
                                })
                                
                except Exception as e:
                    continue  # Continuar con el siguiente patrón
                    
        except Exception as e:
            print(f"⚠️ Error analizando patrones de velas: {e}")
            
        return signals
    
    def analyze_forex_strategies(self, df_window: pd.DataFrame) -> List[Dict]:
        """Analiza estrategias forex técnicas"""
        signals = []
        
        try:
            if len(df_window) < 50:  # Necesitamos suficientes datos para indicadores
                return signals
            
            # Crear copia con nombres de columnas capitalizados para ForexStrategies
            df_forex = df_window.copy()
            df_forex.rename(columns={
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            
            forex_analyzer = ForexStrategies(df_forex)
            
            # Estrategias a analizar
            strategies_to_check = [
                'sma_crossover', 'ema_crossover', 'rsi_oversold_oversold',
                'bollinger_squeeze', 'macd_divergence', 'stochastic_crossover',
                'williams_r_reversal', 'cci_reversal', 'momentum_breakout'
            ]
            
            for strategy in strategies_to_check:
                try:
                    if hasattr(forex_analyzer, strategy):
                        result = getattr(forex_analyzer, strategy)()
                        
                        if result and len(result) > 0:
                            # Tomar la señal más reciente
                            latest_signal = result.iloc[-1] if hasattr(result, 'iloc') else result[-1]
                            
                            if latest_signal and latest_signal != 0:
                                signal_type = 'LONG' if latest_signal > 0 else 'SHORT'
                                confidence = min(abs(latest_signal), 1.0)
                                
                                signals.append({
                                    'type': 'FOREX',
                                    'strategy': strategy,
                                    'direction': signal_type,
                                    'timestamp': df_window.index[-1],
                                    'price': df_window['close'].iloc[-1],
                                    'confidence': confidence,
                                    'signal_strength': latest_signal
                                })
                                
                except Exception as e:
                    continue  # Continuar con la siguiente estrategia
                    
        except Exception as e:
            print(f"⚠️ Error analizando estrategias forex: {e}")
            
        return signals
    
    def process_trading_signals(self, signals: List[Dict]) -> None:
        """Procesa las señales de trading y abre operaciones"""
        for signal in signals:
            try:
                # Verificar disponibilidad de slots
                slot_type = signal['type']
                
                if not self.slot_manager.can_open_trade(slot_type):
                    print(f"⚠️ No hay slots disponibles para {signal['type']}")
                    continue
                
                # Calcular tamaño de posición y riesgo (simplificado)
                current_price = signal['price']
                
                # Cálculo simplificado de SL/TP
                if signal['direction'] == 'LONG':
                    stop_loss = current_price * 0.98
                    take_profit = current_price * 1.02
                else:
                    stop_loss = current_price * 1.02
                    take_profit = current_price * 0.98
                
                risk_params = {
                    'position_size': self.risk_config['position_size'],
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
                
                # Crear la operación
                trade_id = f"{signal['type']}_{signal['strategy']}_{int(time.time())}"
                
                trade = {
                    'id': trade_id,
                    'type': signal['type'],
                    'strategy': signal['strategy'],
                    'direction': signal['direction'],
                    'entry_price': current_price,
                    'entry_time': signal['timestamp'],
                    'position_size': risk_params['position_size'],
                    'stop_loss': risk_params['stop_loss'],
                    'take_profit': risk_params['take_profit'],
                    'confidence': signal['confidence'],
                    'status': 'OPEN'
                }
                
                # Reservar slot
                if self.slot_manager.open_trade(trade_id, slot_type):
                    self.active_trades[trade_id] = trade
                    
                    # Actualizar estadísticas
                    self.stats['total_signals'] += 1
                    if signal['type'] == 'FOREX':
                        self.stats['forex_signals'] += 1
                    else:
                        self.stats['candle_signals'] += 1
                        
                    if signal['direction'] == 'LONG':
                        self.stats['long_trades'] += 1
                    else:
                        self.stats['short_trades'] += 1
                    
                    print(f"🔥 NUEVA OPERACIÓN: {signal['direction']} {signal['strategy']} @ {current_price:.5f}")
                    print(f"   💰 Tamaño: {risk_params.get('position_size', 1.0):.2f}")
                    print(f"   🛡️ SL: {risk_params.get('stop_loss', current_price * 0.98):.5f} | TP: {risk_params.get('take_profit', current_price * 1.02):.5f}")
                    
            except Exception as e:
                print(f"⚠️ Error procesando señal {signal['strategy']}: {e}")
    
    def check_trade_exits(self, current_data: pd.DataFrame) -> None:
        """Verifica si alguna operación debe cerrarse"""
        current_price = current_data['close'].iloc[-1]
        current_time = current_data.index[-1]
        
        trades_to_close = []
        
        for trade_id, trade in self.active_trades.items():
            try:
                should_close = False
                exit_reason = ""
                
                # Verificar Stop Loss
                if trade['direction'] == 'LONG' and current_price <= trade['stop_loss']:
                    should_close = True
                    exit_reason = "STOP_LOSS"
                elif trade['direction'] == 'SHORT' and current_price >= trade['stop_loss']:
                    should_close = True
                    exit_reason = "STOP_LOSS"
                
                # Verificar Take Profit
                elif trade['direction'] == 'LONG' and current_price >= trade['take_profit']:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
                elif trade['direction'] == 'SHORT' and current_price <= trade['take_profit']:
                    should_close = True
                    exit_reason = "TAKE_PROFIT"
                
                # Verificar tiempo máximo (opcional)
                time_diff = current_time - trade['entry_time']
                if time_diff > timedelta(hours=4):  # Máximo 4 horas
                    should_close = True
                    exit_reason = "TIME_EXIT"
                
                if should_close:
                    trades_to_close.append((trade_id, exit_reason, current_price, current_time))
                    
            except Exception as e:
                print(f"⚠️ Error verificando salida para {trade_id}: {e}")
        
        # Cerrar operaciones
        for trade_id, exit_reason, exit_price, exit_time in trades_to_close:
            self.close_trade(trade_id, exit_reason, exit_price, exit_time)
    
    def close_trade(self, trade_id: str, reason: str, exit_price: float, exit_time: datetime) -> None:
        """Cierra una operación y actualiza estadísticas"""
        try:
            trade = self.active_trades[trade_id]
            
            # Calcular P&L
            if trade['direction'] == 'LONG':
                pnl = (exit_price - trade['entry_price']) * trade['position_size']
            else:
                pnl = (trade['entry_price'] - exit_price) * trade['position_size']
            
            # Actualizar trade
            trade.update({
                'exit_price': exit_price,
                'exit_time': exit_time,
                'exit_reason': reason,
                'pnl': pnl,
                'status': 'CLOSED'
            })
            
            # Mover a historial
            self.trade_history.append(trade)
            
            # Liberar slot
            slot_type = trade['type']
            self.slot_manager.close_trade(trade_id, slot_type)
            
            # Remover de activas
            del self.active_trades[trade_id]
            
            # Actualizar estadísticas
            if pnl > 0:
                self.stats['successful_trades'] += 1
                status_icon = "✅"
            else:
                self.stats['failed_trades'] += 1
                status_icon = "❌"
            
            print(f"{status_icon} CERRADA: {trade['strategy']} | P&L: {pnl:.2f} | Razón: {reason}")
            
        except Exception as e:
            print(f"⚠️ Error cerrando operación {trade_id}: {e}")
    
    def simulate_trading(self, window_size: int = 50, step_size: int = 1) -> None:
        """Ejecuta la simulación completa de trading"""
        print("\n🚀 INICIANDO SIMULACIÓN DE TRADING")
        print("=" * 60)
        
        total_candles = len(self.df)
        
        for i in range(window_size, total_candles, step_size):
            try:
                # Ventana de datos actual
                df_window = self.df.iloc[max(0, i-window_size):i+1]
                current_candle = self.df.iloc[i:i+1]
                
                self.processed_candles += 1
                
                # Detectar escenario de mercado
                market_scenario = self.detect_market_scenario(df_window)
                if market_scenario != self.current_market_scenario:
                    self.current_market_scenario = market_scenario
                    print(f"\n📊 CAMBIO DE MERCADO: {market_scenario.name}")
                
                # Obtener estrategias activas
                active_strategies = self.get_active_strategies(market_scenario)
                
                # Analizar señales
                candle_signals = self.analyze_candle_patterns(df_window)
                forex_signals = self.analyze_forex_strategies(df_window)
                
                all_signals = candle_signals + forex_signals
                
                # Procesar señales de trading
                if all_signals:
                    print(f"\n🔍 Vela {self.processed_candles}/{total_candles} | {len(all_signals)} señales detectadas")
                    self.process_trading_signals(all_signals)
                
                # Verificar salidas de operaciones activas
                if self.active_trades:
                    self.check_trade_exits(current_candle)
                
                # Mostrar progreso cada 100 velas
                if self.processed_candles % 100 == 0:
                    self.print_progress_report()
                
                # Pequeña pausa para simular tiempo real (opcional)
                # time.sleep(0.01)
                
            except Exception as e:
                print(f"⚠️ Error en vela {i}: {e}")
                continue
        
        # Cerrar todas las operaciones abiertas al final
        self.close_all_remaining_trades()
        
        print("\n🏁 SIMULACIÓN COMPLETADA")
        self.print_final_report()
    
    def close_all_remaining_trades(self) -> None:
        """Cierra todas las operaciones que quedaron abiertas"""
        if not self.active_trades:
            return
            
        print(f"\n🔒 Cerrando {len(self.active_trades)} operaciones restantes...")
        
        final_price = self.df['close'].iloc[-1]
        final_time = self.df.index[-1]
        
        for trade_id in list(self.active_trades.keys()):
            self.close_trade(trade_id, "SIMULATION_END", final_price, final_time)
    
    def print_progress_report(self) -> None:
        """Imprime reporte de progreso"""
        active_count = len(self.active_trades)
        total_trades = len(self.trade_history) + active_count
        
        print(f"\n📈 PROGRESO - Vela {self.processed_candles}")
        print(f"   🎯 Operaciones totales: {total_trades}")
        print(f"   🔥 Activas: {active_count}")
        print(f"   📊 Mercado actual: {self.current_market_scenario.name}")
        print(f"   💹 Slots: Forex {self.slot_manager.get_used_slots('FOREX')}/10 | Candle {self.slot_manager.get_used_slots('CANDLE')}/10")
    
    def print_final_report(self) -> None:
        """Imprime el reporte final de la simulación"""
        print("\n" + "=" * 80)
        print("📊 REPORTE FINAL DE SIMULACIÓN")
        print("=" * 80)
        
        total_trades = len(self.trade_history)
        successful = self.stats['successful_trades']
        failed = self.stats['failed_trades']
        
        success_rate = (successful / total_trades * 100) if total_trades > 0 else 0
        
        # Calcular P&L total
        total_pnl = sum(trade.get('pnl', 0) for trade in self.trade_history)
        
        print(f"\n🎯 ESTADÍSTICAS GENERALES:")
        print(f"   📊 Velas procesadas: {self.processed_candles}")
        print(f"   🔥 Señales totales: {self.stats['total_signals']}")
        print(f"   📈 Operaciones ejecutadas: {total_trades}")
        print(f"   ✅ Exitosas: {successful} ({success_rate:.1f}%)")
        print(f"   ❌ Fallidas: {failed}")
        print(f"   💰 P&L Total: {total_pnl:.2f}")
        
        print(f"\n📊 DESGLOSE POR TIPO:")
        print(f"   🕯️ Señales Candle: {self.stats['candle_signals']}")
        print(f"   📈 Señales Forex: {self.stats['forex_signals']}")
        print(f"   📈 Operaciones Long: {self.stats['long_trades']}")
        print(f"   📉 Operaciones Short: {self.stats['short_trades']}")
        
        print(f"\n🌍 ESCENARIOS DE MERCADO:")
        for scenario, count in self.stats['market_scenarios'].items():
            percentage = (count / self.processed_candles * 100) if self.processed_candles > 0 else 0
            print(f"   {scenario}: {count} velas ({percentage:.1f}%)")
        
        # Top 5 estrategias más exitosas
        strategy_performance = {}
        for trade in self.trade_history:
            strategy = trade['strategy']
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {'total': 0, 'successful': 0, 'pnl': 0}
            
            strategy_performance[strategy]['total'] += 1
            strategy_performance[strategy]['pnl'] += trade.get('pnl', 0)
            if trade.get('pnl', 0) > 0:
                strategy_performance[strategy]['successful'] += 1
        
        if strategy_performance:
            print(f"\n🏆 TOP 5 ESTRATEGIAS (por P&L):")
            sorted_strategies = sorted(strategy_performance.items(), 
                                     key=lambda x: x[1]['pnl'], reverse=True)[:5]
            
            for i, (strategy, perf) in enumerate(sorted_strategies, 1):
                success_rate = (perf['successful'] / perf['total'] * 100) if perf['total'] > 0 else 0
                print(f"   {i}. {strategy}: {perf['pnl']:.2f} P&L | {success_rate:.1f}% éxito | {perf['total']} ops")
        
        print("\n" + "=" * 80)

def main():
    """Función principal del test"""
    print("🧪 TEST DE DETECCIÓN DE PATRONES CON SIMULACIÓN CSV")
    print("=" * 60)
    
    # Crear simulador
    simulator = TradingTestSimulator()
    
    # Cargar datos CSV
    if not simulator.load_csv_data():
        print("❌ No se pudieron cargar los datos CSV")
        return
    
    # Ejecutar simulación
    try:
        simulator.simulate_trading(window_size=50, step_size=1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Simulación interrumpida por el usuario")
        simulator.close_all_remaining_trades()
        simulator.print_final_report()
        
    except Exception as e:
        print(f"\n❌ Error durante la simulación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()