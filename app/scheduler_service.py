# app/scheduler_service.py

import threading
import time
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json

from .config_app_modal import ConfigAppModal
from .email_service import EmailService
from .report_generator import ReportGenerator


class SchedulerService:
    """Servicio de programación automática para envío de reportes por correo"""
    
    def __init__(self, risk_manager=None):
        self.risk_manager = risk_manager
        self.email_service = EmailService()
        self.report_generator = ReportGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Control del hilo
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        
        # Archivo para guardar el último envío
        self.state_file = Path(__file__).parent.parent / "config" / "scheduler_state.json"
        self.state_file.parent.mkdir(exist_ok=True)
        
        # Cargar estado anterior
        self.last_report_time = self._load_last_report_time()
    
    def start(self):
        """Iniciar el servicio de programación"""
        if self._running:
            self.logger.warning("El scheduler ya está ejecutándose")
            return
        
        config = ConfigAppModal.get_config()
        report_hours = config.get('report_hours', 0)
        
        if report_hours <= 0:
            self.logger.info("Envío automático de reportes desactivado (report_hours = 0)")
            return
        
        if not config.get('email') or not config.get('password'):
            self.logger.warning("Configuración de email incompleta. No se puede iniciar el scheduler.")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        
        self.logger.info(f"Scheduler iniciado. Reportes cada {report_hours} horas.")
    
    def stop(self):
        """Detener el servicio de programación"""
        if not self._running:
            return
        
        self.logger.info("Deteniendo scheduler...")
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self.logger.info("Scheduler detenido")
    
    def _scheduler_loop(self):
        """Bucle principal del scheduler"""
        while self._running and not self._stop_event.is_set():
            try:
                # Verificar si es hora de enviar reporte
                if self._should_send_report():
                    self._send_scheduled_report()
                
                # Esperar 60 segundos antes de la siguiente verificación
                if self._stop_event.wait(60):
                    break
                    
            except Exception as e:
                self.logger.error(f"Error en scheduler loop: {e}")
                # Esperar un poco más en caso de error
                if self._stop_event.wait(300):  # 5 minutos
                    break
    
    def _should_send_report(self):
        """Verificar si es hora de enviar un reporte"""
        config = ConfigAppModal.get_config()
        report_hours = config.get('report_hours', 0)
        
        if report_hours <= 0:
            return False
        
        now = datetime.now()
        
        # Si nunca se ha enviado un reporte, enviar uno ahora
        if self.last_report_time is None:
            return True
        
        # Calcular tiempo transcurrido
        time_diff = now - self.last_report_time
        required_interval = timedelta(hours=report_hours)
        
        return time_diff >= required_interval
    
    def _send_scheduled_report(self):
        """Enviar reporte programado"""
        try:
            self.logger.info("Generando reporte programado...")
            
            # Generar reporte
            report_content, report_file = self.report_generator.generate_trading_report(
                risk_manager=self.risk_manager
            )
            
            if report_content is None:
                self.logger.error("Error al generar contenido del reporte")
                return
            
            # Enviar por email
            success = self.email_service.send_report_email(report_content, report_file)
            
            if success:
                # Actualizar tiempo del último envío
                self.last_report_time = datetime.now()
                self._save_last_report_time()
                self.logger.info("Reporte enviado exitosamente")
            else:
                self.logger.error("Error al enviar reporte por email")
                
        except Exception as e:
            self.logger.error(f"Error al enviar reporte programado: {e}")
    
    def _load_last_report_time(self):
        """Cargar el tiempo del último reporte enviado"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    timestamp_str = data.get('last_report_time')
                    if timestamp_str:
                        return datetime.fromisoformat(timestamp_str)
            return None
        except Exception as e:
            self.logger.error(f"Error al cargar estado del scheduler: {e}")
            return None
    
    def _save_last_report_time(self):
        """Guardar el tiempo del último reporte enviado"""
        try:
            data = {
                'last_report_time': self.last_report_time.isoformat() if self.last_report_time else None,
                'updated': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Error al guardar estado del scheduler: {e}")
    
    def force_send_report(self):
        """Forzar el envío inmediato de un reporte (para pruebas)"""
        try:
            self.logger.info("Forzando envío de reporte...")
            self._send_scheduled_report()
            return True
        except Exception as e:
            self.logger.error(f"Error al forzar envío de reporte: {e}")
            return False
    
    def get_status(self):
        """Obtener estado actual del scheduler"""
        config = ConfigAppModal.get_config()
        report_hours = config.get('report_hours', 0)
        
        status = {
            'running': self._running,
            'configured': report_hours > 0 and bool(config.get('email')),
            'report_hours': report_hours,
            'last_report_time': self.last_report_time.isoformat() if self.last_report_time else None,
            'next_report_due': None
        }
        
        # Calcular próximo reporte
        if self.last_report_time and report_hours > 0:
            next_report = self.last_report_time + timedelta(hours=report_hours)
            status['next_report_due'] = next_report.isoformat()
            
            # Tiempo restante
            now = datetime.now()
            if next_report > now:
                time_remaining = next_report - now
                hours_remaining = time_remaining.total_seconds() / 3600
                status['hours_until_next'] = round(hours_remaining, 1)
            else:
                status['hours_until_next'] = 0
        
        return status
    
    def update_risk_manager(self, risk_manager):
        """Actualizar la referencia al risk manager"""
        self.risk_manager = risk_manager
        self.logger.info("Risk manager actualizado en scheduler")
    
    def restart_if_config_changed(self):
        """Reiniciar el scheduler si la configuración cambió"""
        config = ConfigAppModal.get_config()
        report_hours = config.get('report_hours', 0)
        email_configured = bool(config.get('email') and config.get('password'))
        
        should_be_running = report_hours > 0 and email_configured
        
        if should_be_running and not self._running:
            self.start()
        elif not should_be_running and self._running:
            self.stop()
        elif self._running:
            # Si está corriendo pero la configuración cambió, reiniciar
            self.stop()
            time.sleep(1)  # Pequeña pausa
            self.start()


# Instancia global del scheduler
_scheduler_instance = None

def get_scheduler_instance(risk_manager=None):
    """Obtener la instancia global del scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService(risk_manager)
    elif risk_manager is not None:
        _scheduler_instance.update_risk_manager(risk_manager)
    return _scheduler_instance
