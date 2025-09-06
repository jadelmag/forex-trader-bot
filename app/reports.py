# reports.py - Sistema de generación de informes para el bot de trading

import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class TradingReports:
    def __init__(self):
        self.operations = []  # Lista de todas las operaciones
        self.report_folder = 'reports'
        self.capital_inicial = 0
        self.estrategias_seleccionadas = []
        self.max_operaciones_simultaneas = 0
        
        # Asegurar que existe la carpeta reports
        self._ensure_reports_folder()
    
    def _ensure_reports_folder(self):
        """Crea la carpeta reports si no existe"""
        if not os.path.exists(self.report_folder):
            os.makedirs(self.report_folder)
            print(f"Carpeta '{self.report_folder}' creada")
    
    def set_simulation_config(self, capital_inicial: float, estrategias: List[str], max_operaciones: int):
        """Configura los parámetros iniciales de la simulación"""
        self.capital_inicial = capital_inicial
        self.estrategias_seleccionadas = estrategias.copy()
        self.max_operaciones_simultaneas = max_operaciones
    
    def add_operation_open(self, strategy_name: str, operation_type: str, price: float, 
                          take_profit: float, stop_loss: float, timestamp: Optional[datetime] = None):
        """Registra una operación de apertura"""
        if timestamp is None:
            timestamp = datetime.now()
        
        operation = {
            'type': 'OPEN',
            'strategy': strategy_name,
            'operation_type': operation_type,  # 'COMPRA' o 'VENTA'
            'price': price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'timestamp': timestamp,
            'status': 'OPEN'
        }
        
        self.operations.append(operation)
        return len(self.operations) - 1  # Retorna el índice para referencia
    
    def add_operation_close(self, operation_index: int, close_price: float, 
                           close_reason: str, profit_loss: float, timestamp: Optional[datetime] = None):
        """Registra el cierre de una operación"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if 0 <= operation_index < len(self.operations):
            # Actualizar la operación original
            self.operations[operation_index]['status'] = 'CLOSED'
            self.operations[operation_index]['close_price'] = close_price
            self.operations[operation_index]['close_reason'] = close_reason
            self.operations[operation_index]['profit_loss'] = profit_loss
            self.operations[operation_index]['close_timestamp'] = timestamp
            
            # Agregar entrada de cierre
            close_operation = {
                'type': 'CLOSE',
                'strategy': self.operations[operation_index]['strategy'],
                'operation_type': self.operations[operation_index]['operation_type'],
                'price': close_price,
                'reason': close_reason,
                'profit_loss': profit_loss,
                'timestamp': timestamp,
                'original_index': operation_index
            }
            
            self.operations.append(close_operation)
    
    def generate_report(self, filename: Optional[str] = None) -> str:
        """Genera un informe completo y lo guarda en un archivo TXT"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_report_{timestamp}.txt"
        
        filepath = os.path.join(self.report_folder, filename)
        
        # Generar contenido del informe
        report_content = self._generate_report_content()
        
        # Guardar archivo
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"Informe generado exitosamente: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error generando informe: {e}")
            return ""
    
    def _generate_report_content(self) -> str:
        """Genera el contenido del informe"""
        lines = []
        lines.append("=" * 60)
        lines.append("INFORME DE TRADING")
        lines.append("=" * 60)
        lines.append(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Sección de operaciones
        lines.append("OPERACIONES REALIZADAS:")
        lines.append("-" * 40)
        
        operation_pairs = self._group_operations()
        
        for pair in operation_pairs:
            open_op = pair['open']
            close_op = pair.get('close')
            
            # Operación de apertura
            timestamp_str = open_op['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            lines.append(f"Orden de {open_op['operation_type']} abierta {open_op['strategy']}: "
                        f"{open_op['price']:.5f} (TP: {open_op['take_profit']:.5f}, "
                        f"SL: {open_op['stop_loss']:.5f}) - {timestamp_str}")
            
            # Operación de cierre (si existe)
            if close_op:
                close_timestamp_str = close_op['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                profit_symbol = "+" if close_op['profit_loss'] >= 0 else ""
                lines.append(f"Orden de {close_op['operation_type']} cerrada {close_op['strategy']}: "
                            f"{close_op['price']:.5f} - {close_op['reason']} "
                            f"({profit_symbol}{close_op['profit_loss']:.2f}€) - {close_timestamp_str}")
            
            lines.append("")  # Línea en blanco entre operaciones
        
        # Separador
        lines.append("-" * 60)
        lines.append("")
        
        # Resumen estadístico
        lines.extend(self._generate_summary())
        
        return "\n".join(lines)
    
    def _group_operations(self) -> List[Dict]:
        """Agrupa las operaciones de apertura con sus respectivos cierres"""
        operation_pairs = []
        open_operations = {}
        
        for i, op in enumerate(self.operations):
            if op['type'] == 'OPEN':
                open_operations[i] = op
                operation_pairs.append({'open': op, 'close': None})
            elif op['type'] == 'CLOSE':
                original_index = op.get('original_index')
                if original_index is not None:
                    # Encontrar el par correspondiente
                    for pair in operation_pairs:
                        if pair['open'] == self.operations[original_index]:
                            pair['close'] = op
                            break
        
        return operation_pairs
    
    def _generate_summary(self) -> List[str]:
        """Genera el resumen estadístico"""
        lines = []
        lines.append("RESUMEN GENERAL:")
        lines.append("=" * 40)
        
        # Calcular estadísticas
        stats = self._calculate_statistics()
        
        lines.append(f"Capital inicial: {self.capital_inicial:.2f}€")
        lines.append(f"Estrategias seleccionadas: {', '.join(self.estrategias_seleccionadas)}")
        lines.append(f"Máximo de operaciones simultáneas: {self.max_operaciones_simultaneas}")
        lines.append(f"Capital final: {stats['capital_final']:.2f}€")
        lines.append(f"Beneficio total: {stats['beneficio_total']:+.2f}€")
        lines.append(f"Operaciones ganadas: {stats['operaciones_ganadas']} [{stats['dinero_ganado']:+.2f}€]")
        lines.append(f"Operaciones perdidas: {stats['operaciones_perdidas']} [{stats['dinero_perdido']:+.2f}€]")
        lines.append(f"Win Rate: {stats['win_rate']:.1f}%")
        
        return lines
    
    def _calculate_statistics(self) -> Dict[str, float]:
        """Calcula las estadísticas del trading"""
        closed_operations = [op for op in self.operations if op['type'] == 'CLOSE']
        
        total_profit = sum(op['profit_loss'] for op in closed_operations)
        winning_ops = [op for op in closed_operations if op['profit_loss'] > 0]
        losing_ops = [op for op in closed_operations if op['profit_loss'] < 0]
        
        money_won = sum(op['profit_loss'] for op in winning_ops)
        money_lost = sum(op['profit_loss'] for op in losing_ops)
        
        total_operations = len(closed_operations)
        win_rate = (len(winning_ops) / total_operations * 100) if total_operations > 0 else 0
        
        return {
            'capital_final': self.capital_inicial + total_profit,
            'beneficio_total': total_profit,
            'operaciones_ganadas': len(winning_ops),
            'operaciones_perdidas': len(losing_ops),
            'dinero_ganado': money_won,
            'dinero_perdido': money_lost,
            'win_rate': win_rate
        }
    
    def clear_operations(self):
        """Limpia todas las operaciones registradas"""
        self.operations.clear()
    
    def get_operations_count(self) -> int:
        """Retorna el número total de operaciones registradas"""
        return len(self.operations)
    
    def get_open_operations_count(self) -> int:
        """Retorna el número de operaciones abiertas"""
        return len([op for op in self.operations if op['type'] == 'OPEN' and op['status'] == 'OPEN'])


# Instancia global para uso en toda la aplicación
trading_reports = TradingReports()


# Funciones de conveniencia para uso fácil
def set_simulation_config(capital_inicial: float, estrategias: List[str], max_operaciones: int):
    """Configura los parámetros de la simulación"""
    trading_reports.set_simulation_config(capital_inicial, estrategias, max_operaciones)


def register_operation_open(strategy_name: str, operation_type: str, price: float, 
                           take_profit: float, stop_loss: float) -> int:
    """Registra una operación de apertura"""
    return trading_reports.add_operation_open(strategy_name, operation_type, price, 
                                            take_profit, stop_loss)


def register_operation_close(operation_index: int, close_price: float, 
                           close_reason: str, profit_loss: float):
    """Registra el cierre de una operación"""
    trading_reports.add_operation_close(operation_index, close_price, close_reason, profit_loss)


def generate_trading_report(filename: Optional[str] = None) -> str:
    """Genera y guarda un informe de trading"""
    return trading_reports.generate_report(filename)


def clear_all_operations():
    """Limpia todas las operaciones"""
    trading_reports.clear_operations()


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar simulación
    set_simulation_config(1000.0, ["Ichimoku Cloud Strategy", "RSI Strategy"], 5)
    
    # Registrar algunas operaciones de ejemplo
    op1 = register_operation_open("Ichimoku Cloud Strategy", "COMPRA", 1.17060, 1.17106, 1.17037)
    register_operation_close(op1, 1.17080, "TAKE PROFIT", 20.0)
    
    op2 = register_operation_open("RSI Strategy", "VENTA", 1.17100, 1.17050, 1.17130)
    register_operation_close(op2, 1.17120, "STOP LOSS", -20.0)
    
    # Generar informe
    report_path = generate_trading_report()
    print(f"Informe generado en: {report_path}")
