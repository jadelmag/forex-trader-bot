# app/email_service.py

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from pathlib import Path
from datetime import datetime
import logging

from .config_app_modal import ConfigAppModal


class EmailService:
    """Servicio para envío automático de reportes por correo electrónico"""
    
    def __init__(self):
        self.config = ConfigAppModal.get_config()
        self.logger = logging.getLogger(__name__)
        
    def _get_smtp_config(self, email):
        """Obtener configuración SMTP basada en el proveedor de email"""
        email_lower = email.lower()
        
        if 'gmail.com' in email_lower:
            return {
                'smtp_server': 'smtp.gmail.com',
                'port': 587,
                'use_tls': True
            }
        elif 'outlook.com' in email_lower or 'hotmail.com' in email_lower:
            return {
                'smtp_server': 'smtp-mail.outlook.com',
                'port': 587,
                'use_tls': True
            }
        elif 'yahoo.com' in email_lower:
            return {
                'smtp_server': 'smtp.mail.yahoo.com',
                'port': 587,
                'use_tls': True
            }
        else:
            # Configuración genérica para otros proveedores
            return {
                'smtp_server': 'smtp.gmail.com',  # Por defecto Gmail
                'port': 587,
                'use_tls': True
            }
    
    def send_report_email(self, report_content, report_file_path=None):
        """
        Enviar reporte por correo electrónico
        
        Args:
            report_content (str): Contenido del reporte en texto
            report_file_path (str, optional): Ruta al archivo de reporte para adjuntar
            
        Returns:
            bool: True si el envío fue exitoso, False en caso contrario
        """
        try:
            # Verificar configuración
            if not self.config.get('email') or not self.config.get('password'):
                self.logger.error("Configuración de email incompleta")
                return False
            
            email_from = self.config['email']
            password = self.config['password']
            
            # Obtener configuración SMTP
            smtp_config = self._get_smtp_config(email_from)
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = email_from
            msg['To'] = email_from  # Enviar a sí mismo
            msg['Subject'] = f"Reporte Forex Trading Bot - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            # Cuerpo del mensaje
            body = f"""
Reporte Automático del Forex Trading Bot
========================================

Fecha y hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

{report_content}

---
Este es un reporte automático generado por el Forex Trading Bot.
Configurado para envío cada {self.config.get('report_hours', 0)} horas.
"""
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Adjuntar archivo si se proporciona
            if report_file_path and os.path.exists(report_file_path):
                try:
                    with open(report_file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    filename = os.path.basename(report_file_path)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
                except Exception as e:
                    self.logger.warning(f"No se pudo adjuntar el archivo: {e}")
            
            # Crear conexión SMTP
            context = ssl.create_default_context()
            
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['port']) as server:
                if smtp_config['use_tls']:
                    server.starttls(context=context)
                
                server.login(email_from, password)
                server.send_message(msg)
            
            self.logger.info(f"Reporte enviado exitosamente a {email_from}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            self.logger.error("Error de autenticación SMTP. Verifique email y contraseña.")
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"Error SMTP: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error inesperado al enviar email: {e}")
            return False
    
    def test_email_connection(self):
        """
        Probar la conexión de email sin enviar nada
        
        Returns:
            bool: True si la conexión es exitosa, False en caso contrario
        """
        try:
            if not self.config.get('email') or not self.config.get('password'):
                return False
            
            email_from = self.config['email']
            password = self.config['password']
            smtp_config = self._get_smtp_config(email_from)
            
            context = ssl.create_default_context()
            
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['port']) as server:
                if smtp_config['use_tls']:
                    server.starttls(context=context)
                server.login(email_from, password)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error al probar conexión de email: {e}")
            return False
    
    def is_email_configured(self):
        """
        Verificar si el email está configurado correctamente
        
        Returns:
            bool: True si está configurado, False en caso contrario
        """
        config = ConfigAppModal.get_config()
        return bool(config.get('email') and config.get('password') and config.get('report_hours', 0) > 0)
