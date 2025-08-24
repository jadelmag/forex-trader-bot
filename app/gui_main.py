# app/gui_main.py

import tkinter as tk
from tkinter import ttk, messagebox
from .csv_manager import CSVManager
from .grafico_manager import GraficoManager
from .tooltip_zoom_pan import TooltipZoomPan
from .csv_loader_modal import CSVLoaderModal

class GUIPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot - CSV Data Viewer")
        self.root.geometry("1500x750")
        self.root.configure(bg="#F0F0F0")

        # ---------------- Inicializaciones ----------------
        self.csv_manager = CSVManager(root)
        self.grafico_manager = GraficoManager(frame=None)
        self.tooltip_zoom_pan = None
        self.df_actual = None

        # ---------------- Frames ----------------
        self.frame_controls = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_controls.pack(padx=20, pady=10, anchor="w")
        
        self.frame_grafico = tk.Frame(self.root, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(fill="both", expand=True, padx=20, pady=10)

        self.grafico_manager.frame = self.frame_grafico

        # ---------------- Widgets ----------------
        # Botones CSV / Procesados
        self.btn_cargar_csv = tk.Button(self.frame_controls, text="Cargar CSV", 
                                       command=self.cargar_csv, width=15, height=2)
        self.btn_cargar_csv.pack(side="left", padx=5)
        
        self.btn_cargar_procesados = tk.Button(self.frame_controls, text="Cargar datos procesados", 
                                              command=self.cargar_procesados, width=20, height=2)
        self.btn_cargar_procesados.pack(side="left", padx=5)
        
        self.btn_guardar_procesados = tk.Button(self.frame_controls, text="Guardar datos procesados", 
                                               command=self.guardar_procesados, state="disabled", 
                                               width=20, height=2)
        self.btn_guardar_procesados.pack(side="left", padx=5)

        # Botón Reset Zoom
        self.btn_reset_zoom = tk.Button(self.frame_controls, text="Reset Zoom", 
                                       command=self.reset_zoom, state="disabled", 
                                       width=15, height=2)
        self.btn_reset_zoom.pack(side="left", padx=5)

    # ---------------- Cargar CSV ----------------
    def cargar_csv(self):
        df = self.csv_manager.cargar_csv()
        if df is not None:
            CSVLoaderModal(self.root, df, callback=self._on_csv_cargado)

    def _on_csv_cargado(self, df_seleccion):
        self.df_actual = df_seleccion
        self._dibujar_grafico(df_seleccion)
        self.btn_guardar_procesados.config(state="normal")
        self.btn_reset_zoom.config(state="normal")

    # ---------------- Cargar datos procesados ----------------
    def cargar_procesados(self):
        df = self.csv_manager.cargar_procesados()
        if df is not None:
            self.df_actual = df
            self._dibujar_grafico(df)
            self.btn_guardar_procesados.config(state="normal")
            self.btn_reset_zoom.config(state="normal")

    # ---------------- Guardar datos procesados ----------------
    def guardar_procesados(self):
        self.csv_manager.df_cache = self.df_actual
        self.csv_manager.guardar_procesados()

    # ---------------- Dibujar gráfico ----------------
    def _dibujar_grafico(self, df):
        self.grafico_manager.dibujar_csv(df)
        self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

    # ---------------- Reset Zoom ----------------
    def reset_zoom(self):
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.reset_zoom()

    # ---------------- Limpiar Gráfico ----------------
    def limpiar_grafico(self):
        """Elimina los datos y oculta la gráfica por completo"""
        self.df_actual = None

        # Limpiar y destruir tooltip
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.cleanup()
        self.tooltip_zoom_pan = None

        # Limpiar la figura en GraficoManager
        if hasattr(self.grafico_manager, 'limpiar'):
            self.grafico_manager.limpiar()

        # Ocultar o destruir el canvas de Matplotlib
        if hasattr(self.grafico_manager, 'canvas') and self.grafico_manager.canvas:
            self.grafico_manager.canvas.get_tk_widget().pack_forget()  # Oculta el canvas
            # self.grafico_manager.canvas.get_tk_widget().destroy()  # Si quieres destruirlo completamente
            self.grafico_manager.canvas = None

    # ---------------- Run ----------------
    def run(self):
        self.root.mainloop()
