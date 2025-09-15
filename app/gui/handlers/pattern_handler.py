# app/handlers/pattern_handler.py
import tkinter as tk
from tkinter import messagebox

class PatternHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        
    def abrir_modal_patrones(self):
        """Abre el modal de patrones"""
        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
            
        try:
            from app.patterns_modal import PatternsModal
            PatternsModal(
                self.main_app.root,
                self.main_app.csv_handler.df_actual,
                self.main_app.grafico_manager,
                self.main_app
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")
            
    def abrir_modal_candle_strategies(self):
        """Abre el modal de estrategias de velas"""
        if self.main_app.csv_handler.df_actual is None:
            messagebox.showwarning("Atención", "Cargue primero un CSV o datos procesados")
            return
            
        try:
            from app.candle_strategies_modal import CandleStrategiesModal
            CandleStrategiesModal(
                self.main_app.root,
                self.main_app.csv_handler.df_actual,
                self.main_app.grafico_manager,
                self.main_app
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)