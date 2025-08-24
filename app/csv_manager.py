# app/csv_manager.py

import pandas as pd
import os
import pickle
import tkinter as tk
from tkinter import filedialog, messagebox

class CSVManager:
    def __init__(self, root):
        self.root = root
        self.df_cache = None
        # Definir la ruta base del proyecto
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def cargar_csv(self):
        # Empezar desde la carpeta csv/ del proyecto
        initial_dir = os.path.join(self.base_dir, 'csv')
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("CSV Files", "*.csv")]
        )
        if not filepath:
            return None

        try:
            df = pd.read_csv(filepath, sep=';', header=None,
                             names=['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['DateTime'] = pd.to_datetime(df['DateTime'], format='%Y%m%d %H%M%S')
            df.set_index('DateTime', inplace=True)
            self.df_cache = df
            return df
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el CSV: {str(e)}")
            return None

    def guardar_procesados(self, filename=None):
        if self.df_cache is None:
            messagebox.showwarning("Atención", "No hay datos para guardar.")
            return

        # Usar la carpeta processed/ del proyecto
        folder = os.path.join(self.base_dir, 'processed')
        os.makedirs(folder, exist_ok=True)

        if not filename:
            # Sugerir nombre basado en el rango de fechas
            if not self.df_cache.empty:
                start_date = self.df_cache.index[0].strftime('%Y%m%d')
                end_date = self.df_cache.index[-1].strftime('%Y%m%d')
                default_name = f"processed_data_{start_date}_{end_date}.pkl"
            else:
                default_name = "processed_data.pkl"
                
            filename = filedialog.asksaveasfilename(
                initialdir=folder,
                initialfile=default_name,
                defaultextension=".pkl",
                filetypes=[("Pickle Files", "*.pkl")]
            )

        if not filename:
            return

        try:
            # Asegurar que se guarda en la carpeta processed/
            if not filename.startswith(folder):
                filename = os.path.join(folder, os.path.basename(filename))
            
            with open(filename, 'wb') as f:
                pickle.dump(self.df_cache, f)
            messagebox.showinfo("Éxito", f"Datos guardados en {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar los datos: {str(e)}")

    def cargar_procesados(self):
        # Usar la carpeta processed/ del proyecto
        folder = os.path.join(self.base_dir, 'processed')
        os.makedirs(folder, exist_ok=True)

        filepath = filedialog.askopenfilename(
            initialdir=folder,
            filetypes=[("Pickle Files", "*.pkl")]
        )
        
        if not filepath:
            return None

        try:
            with open(filepath, 'rb') as f:
                df = pickle.load(f)
            self.df_cache = df
            return df
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo: {str(e)}")
            return None

    def obtener_ruta_processed(self):
        """Devuelve la ruta absoluta a la carpeta processed/"""
        return os.path.join(self.base_dir, 'processed')

    def listar_archivos_procesados(self):
        """Lista todos los archivos .pkl en la carpeta processed/"""
        folder = self.obtener_ruta_processed()
        if os.path.exists(folder):
            return [f for f in os.listdir(folder) if f.endswith('.pkl')]
        return []