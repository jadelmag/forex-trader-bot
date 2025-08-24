import pandas as pd
import os
import pickle
import tkinter as tk
from tkinter import filedialog, messagebox

class CSVManager:
    def __init__(self, root):
        self.root = root
        self.df_cache = None

    def cargar_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files","*.csv")])
        if not filepath: return

        df = pd.read_csv(filepath, sep=';', header=None,
                         names=['DateTime','Open','High','Low','Close','Volume'])
        df['DateTime'] = pd.to_datetime(df['DateTime'], format='%Y%m%d %H%M%S')
        df.set_index('DateTime', inplace=True)
        self.df_cache = df
        return df

    def guardar_procesados(self, filename=None):
        if self.df_cache is None:
            messagebox.showwarning("Atención", "No hay datos para guardar.")
            return
        folder = os.path.join(os.getcwd(), 'processed')
        os.makedirs(folder, exist_ok=True)
        if not filename:
            filename = filedialog.asksaveasfilename(initialdir=folder, defaultextension=".pkl",
                                                    filetypes=[("Pickle Files","*.pkl")])
        if not filename: return
        with open(filename, 'wb') as f:
            pickle.dump(self.df_cache, f)
        messagebox.showinfo("Éxito", f"Datos guardados en {filename}")

    def cargar_procesados(self):
        folder = os.path.join(os.getcwd(), 'processed')
        os.makedirs(folder, exist_ok=True)
        filepath = filedialog.askopenfilename(initialdir=folder, filetypes=[("Pickle Files","*.pkl")])
        if not filepath: return
        with open(filepath, 'rb') as f:
            df = pickle.load(f)
        self.df_cache = df
        return df
