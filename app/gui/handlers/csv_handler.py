# app/gui/handlers/csv_handler.py
import tkinter as tk
from tkinter import messagebox, filedialog
import pandas as pd
import pickle
import os

class CSVHandler:
    def __init__(self, main_app):
        self.main_app = main_app
        self.df_actual = None
        
    def cargar_csv(self):
        """Carga un archivo CSV"""
        try:
            from tkinter import filedialog
            import pandas as pd
            
            # Abrir diálogo para seleccionar archivo CSV
            archivo = filedialog.askopenfilename(
                title="Seleccionar archivo CSV",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if archivo:
                # Cargar CSV
                df = pd.read_csv(archivo)
                
                # Usar el modal para seleccionar filas
                from app.csv_loader_modal import CSVLoaderModal
                
                def _on_loaded(df_seleccion):
                    self._on_csv_cargado(df_seleccion)
                
                CSVLoaderModal(self.main_app.root, df, _on_loaded)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar CSV: {str(e)}")
            self.log(f"Error cargando CSV: {str(e)}", color='red')
        return False
        
    def cargar_procesados(self):
        """Abre el nuevo modal para cargar datos procesados (Parquet/PKL) con opciones de rango."""
        try:
            def _on_loaded(df):
                try:
                    # Reutilizamos la misma ruta de pintado y habilitación de botones
                    self._on_csv_cargado(df)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo cargar los datos: {e}")

            from app.processed_loader_modal import ProcessedDataModal
            ProcessedDataModal(self.main_app.root, on_loaded_df=_on_loaded)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")
        
    def guardar_procesados(self):
        """Guarda los datos actuales como archivo PKL"""
        if hasattr(self.main_app, 'csv_manager'):
            self.main_app.csv_manager.df_cache = self.df_actual
            self.main_app.csv_manager.guardar_procesados()
        else:
            if self.df_actual is None:
                messagebox.showwarning("Atención", "No hay datos para guardar")
                return
                
            try:
                archivo = filedialog.asksaveasfilename(
                    title="Guardar datos procesados",
                    defaultextension=".pkl",
                    filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
                )
                if archivo:
                    with open(archivo, 'wb') as f:
                        pickle.dump(self.df_actual, f)
                    self.log(f"Datos guardados: {os.path.basename(archivo)}", color='green')
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar datos: {str(e)}")
                self.log(f"Error guardando datos: {str(e)}", color='red')
            
    def abrir_modal_csv_a_pkl(self):
        """Abre el modal para convertir un CSV en un archivo PKL."""
        try:
            from app.csv_to_pkl_modal import CSVToPKLModal
            CSVToPKLModal(self.main_app.root)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el modal: {e}")
    
    def _on_csv_cargado(self, df_seleccion):
        """Callback cuando se carga un CSV exitosamente"""
        self.df_actual = df_seleccion
        self.main_app.df_actual = df_seleccion
        
        # Dibujar gráfico
        if hasattr(self.main_app, 'grafico_manager'):
            self.main_app.grafico_manager.dibujar_csv(df_seleccion)
        
        # Fijar altura del log una vez
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel._fix_log_height_once()
        
        # Actualizar estados de botones
        try:
            if hasattr(self.main_app, 'menu_bar'):
                self.main_app.menu_bar._update_btn_aplicar_patrones()
                self.main_app.menu_bar._update_btn_cargar_estrategias()
                self.main_app.menu_bar.update_buttons_state()
        except Exception:
            pass
            
    def log(self, message, color="white"):
        """Envía mensaje al log panel"""
        if hasattr(self.main_app, 'log_panel'):
            self.main_app.log_panel.log(message, color)