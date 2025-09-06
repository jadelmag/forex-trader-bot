# app/report_generator.py

import os
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging


class ReportGenerator:
    """Generador de reportes automáticos para el Forex Trading Bot"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.reports_dir = Path(__file__).parent.parent / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def generate_trading_report(self, risk_manager=None, operations_data=None):
        """
        Generar reporte completo de trading
        
        Args:
            risk_manager: Instancia del RiskManager para obtener datos actuales
            operations_data: Datos adicionales de operaciones (opcional)
            
        Returns:
            tuple: (report_content, report_file_path)
        """
        try:
            timestamp = datetime.now()
            report_content = self._build_report_content(risk_manager, operations_data, timestamp)
            report_file_path = self._save_report_to_file(report_content, timestamp)
            
            return report_content, report_file_path
            
        except Exception as e:
            self.logger.error(f"Error al generar reporte: {e}")
            return None, None
    
    def _build_report_content(self, risk_manager, operations_data, timestamp):
        """Construir el contenido del reporte"""
        
        # Información básica
        report_lines = [
            "REPORTE FOREX TRADING BOT",
            "=" * 50,
            f"Fecha: {timestamp.strftime('%d/%m/%Y')}",
            f"Hora: {timestamp.strftime('%H:%M:%S')}",
            "",
        ]
        
        # Estado del capital y operaciones
        if risk_manager:
            capital_actual = getattr(risk_manager, 'capital_actual', 0)
            capital_inicial = getattr(risk_manager, 'capital_inicial', 0)
            operaciones_abiertas = getattr(risk_manager, 'operaciones_abiertas', [])
            
            profit_loss = capital_actual - capital_inicial
            profit_percentage = (profit_loss / capital_inicial * 100) if capital_inicial > 0 else 0
            
            report_lines.extend([
                "ESTADO DEL CAPITAL:",
                "-" * 20,
                f"Capital inicial: ${capital_inicial:,.2f}",
                f"Capital actual: ${capital_actual:,.2f}",
                f"P&L Total: ${profit_loss:,.2f} ({profit_percentage:+.2f}%)",
                f"Operaciones abiertas: {len(operaciones_abiertas)}",
                "",
            ])
            
            # Detalles de operaciones abiertas
            if operaciones_abiertas:
                report_lines.extend([
                    "OPERACIONES ABIERTAS:",
                    "-" * 20,
                ])
                
                for i, op in enumerate(operaciones_abiertas, 1):
                    tipo = op.get('tipo', 'N/A')
                    estrategia = op.get('estrategia', 'N/A')
                    precio_entrada = op.get('precio_entrada', 0)
                    lot_size = op.get('lot_size', 0)
                    timestamp_op = op.get('timestamp', 'N/A')
                    
                    report_lines.extend([
                        f"{i}. {tipo} - {estrategia}",
                        f"   Precio entrada: {precio_entrada}",
                        f"   Lot size: {lot_size:,.0f}",
                        f"   Tiempo: {timestamp_op}",
                        "",
                    ])
            else:
                report_lines.extend([
                    "OPERACIONES ABIERTAS:",
                    "-" * 20,
                    "No hay operaciones abiertas actualmente.",
                    "",
                ])
        
        # Estadísticas de archivos de reporte recientes
        recent_reports = self._get_recent_reports_stats()
        if recent_reports:
            report_lines.extend([
                "ESTADÍSTICAS RECIENTES:",
                "-" * 25,
            ])
            report_lines.extend(recent_reports)
            report_lines.append("")
        
        # Información del sistema
        report_lines.extend([
            "INFORMACIÓN DEL SISTEMA:",
            "-" * 28,
            f"Versión: Forex Trading Bot v1.0",
            f"Reporte generado automáticamente",
            f"Próximo reporte programado según configuración",
            "",
        ])
        
        # Estado de conexiones (si hay datos disponibles)
        if operations_data and 'connection_status' in operations_data:
            status = operations_data['connection_status']
            report_lines.extend([
                "ESTADO DE CONEXIONES:",
                "-" * 22,
                f"Binance WebSocket: {'✓ Conectado' if status.get('binance', False) else '✗ Desconectado'}",
                f"Datos en tiempo real: {'✓ Activo' if status.get('realtime', False) else '✗ Inactivo'}",
                "",
            ])
        
        return "\n".join(report_lines)
    
    def _save_report_to_file(self, content, timestamp):
        """Guardar reporte en archivo"""
        try:
            filename = f"trading_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
            file_path = self.reports_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Reporte guardado en: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Error al guardar reporte: {e}")
            return None
    
    def _get_recent_reports_stats(self):
        """Obtener estadísticas de reportes recientes"""
        try:
            # Buscar archivos de reporte de los últimos 7 días
            cutoff_date = datetime.now() - timedelta(days=7)
            recent_files = []
            
            for file_path in self.reports_dir.glob("trading_report_*.txt"):
                try:
                    # Extraer fecha del nombre del archivo
                    date_str = file_path.stem.split('_')[2] + file_path.stem.split('_')[3]
                    file_date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    
                    if file_date >= cutoff_date:
                        recent_files.append((file_date, file_path))
                except:
                    continue
            
            if not recent_files:
                return ["No hay reportes recientes disponibles."]
            
            # Ordenar por fecha
            recent_files.sort(key=lambda x: x[0], reverse=True)
            
            stats = [
                f"Reportes generados (últimos 7 días): {len(recent_files)}",
                f"Último reporte: {recent_files[0][0].strftime('%d/%m/%Y %H:%M')}",
            ]
            
            if len(recent_files) > 1:
                stats.append(f"Reporte anterior: {recent_files[1][0].strftime('%d/%m/%Y %H:%M')}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error al obtener estadísticas de reportes: {e}")
            return ["Error al cargar estadísticas de reportes."]
    
    def generate_summary_report(self, period_hours=24):
        """
        Generar reporte resumen de un período específico
        
        Args:
            period_hours (int): Horas hacia atrás para el resumen
            
        Returns:
            str: Contenido del reporte resumen
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=period_hours)
            
            summary_lines = [
                f"RESUMEN DE {period_hours} HORAS",
                "=" * 30,
                f"Período: {cutoff_time.strftime('%d/%m/%Y %H:%M')} - {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                "",
            ]
            
            # Buscar reportes en el período
            period_reports = []
            for file_path in self.reports_dir.glob("trading_report_*.txt"):
                try:
                    date_str = file_path.stem.split('_')[2] + file_path.stem.split('_')[3]
                    file_date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    
                    if file_date >= cutoff_time:
                        period_reports.append(file_date)
                except:
                    continue
            
            summary_lines.extend([
                f"Reportes generados en el período: {len(period_reports)}",
                f"Frecuencia promedio: {period_hours/max(len(period_reports), 1):.1f} horas entre reportes",
                "",
                "Este es un resumen automático del sistema de reportes.",
            ])
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            self.logger.error(f"Error al generar reporte resumen: {e}")
            return "Error al generar reporte resumen."
    
    def cleanup_old_reports(self, days_to_keep=30):
        """
        Limpiar reportes antiguos
        
        Args:
            days_to_keep (int): Días de reportes a mantener
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0
            
            for file_path in self.reports_dir.glob("trading_report_*.txt"):
                try:
                    date_str = file_path.stem.split('_')[2] + file_path.stem.split('_')[3]
                    file_date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    
                    if file_date < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1
                except:
                    continue
            
            if deleted_count > 0:
                self.logger.info(f"Eliminados {deleted_count} reportes antiguos")
            
        except Exception as e:
            self.logger.error(f"Error al limpiar reportes antiguos: {e}")
