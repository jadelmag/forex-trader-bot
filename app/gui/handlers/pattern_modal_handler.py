# app/gui/handlers/pattern_modal_handler.py

class PatternModalHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        
    def abrir_modal_patrones(self):
        """Abre el modal de patrones"""
        if self.main_app.csv_handler.df_actual is not None:
            try:
                from app.gui.modals.patterns_modal import PatternsModal
                PatternsModal(
                    self.main_app.root, 
                    self.main_app.csv_handler.df_actual, 
                    self.main_app.grafico_manager, 
                    self.main_app, 
                    callback=self.main_app._on_patrones_aplicados
                )
            except Exception as e:
                self.log(f"Error abriendo modal de patrones: {str(e)}", color='red')
        else:
            from tkinter import messagebox
            messagebox.showwarning("Atención", "No hay datos cargados para aplicar patrones")
            
    def _on_patrones_aplicados(self, df_actualizado):
        """Callback cuando se aplican patrones"""
        try:
            # Actualizar el DataFrame actual
            self.main_app.csv_handler.df_actual = df_actualizado
            
            # Redibujar el gráfico
            if hasattr(self.main_app, 'grafico_manager'):
                self.main_app.grafico_manager.dibujar_csv(df_actualizado)
                
            self.log("Patrones aplicados correctamente", color='green')
        except Exception as e:
            self.log(f"Error aplicando patrones: {str(e)}", color='red')
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)
