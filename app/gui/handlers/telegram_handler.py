# app/handlers/telegram_handler.py
import tkinter as tk
from tkinter import messagebox

class TelegramHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        
    def abrir_modal_telegram(self):
        """Abre el modal de configuración de Telegram"""
        try:
            from app.telegram_modal import TelegramModal
            TelegramModal(self.main_app.root, self.main_app)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)