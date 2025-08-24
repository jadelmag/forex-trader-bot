# app/gui_main.py

import tkinter as tk
from tkinter import ttk, messagebox
from .csv_manager import CSVManager
from .grafico_manager import GraficoManager
from .yfinance_manager import YFinanceManager
from .tooltip_zoom_pan import TooltipZoomPan
from .forex_pairs import ForexPairs
from .csv_loader_modal import CSVLoaderModal

class GUIPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot - Forex Market")
        self.root.geometry("1500x750")
        self.root.configure(bg="#F0F0F0")

        # ---------------- Inicializaciones ----------------
        self.monedas = ForexPairs.CURRENCIES
        self.csv_manager = CSVManager(root)
        self.grafico_manager = GraficoManager(frame=None)
        self.yfinance_manager = YFinanceManager()
        self.tooltip_zoom_pan = None
        self.df_actual = None

        # ---------------- Frames ----------------
        self.frame_main = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_main.pack(padx=20, pady=20, anchor="w")
        self.frame_grafico = tk.Frame(self.root, bg="#FFFFFF", relief="sunken", bd=1)
        self.frame_grafico.pack(fill="both", expand=True, padx=20, pady=10)
        self.frame_trading = tk.Frame(self.root, bg="#F0F0F0")
        self.frame_trading.pack(fill="x", pady=5, padx=20, anchor="e")

        self.grafico_manager.frame = self.frame_grafico

        # ---------------- Widgets ----------------
        tk.Label(self.frame_main, text="Moneda Base:", bg="#F0F0F0").grid(row=0, column=0, sticky="w")
        self.combo1 = ttk.Combobox(self.frame_main, values=self.monedas, state="readonly", width=12)
        self.combo1.grid(row=1, column=0, padx=5)
        self.combo1.bind("<<ComboboxSelected>>", self.on_seleccion)

        tk.Label(self.frame_main, text="Moneda Cotizada:", bg="#F0F0F0").grid(row=0, column=1, sticky="w")
        self.combo2 = ttk.Combobox(self.frame_main, values=self.monedas, state="readonly", width=12)
        self.combo2.grid(row=1, column=1, padx=5)
        self.combo2.bind("<<ComboboxSelected>>", self.on_seleccion)

        # Botones Confirmar / Clear
        self.btn_confirmar = tk.Button(self.frame_main, text="Confirmar", state="disabled", command=self.confirmar)
        self.btn_confirmar.grid(row=1, column=2, padx=5)
        self.btn_clear_confirmar = tk.Button(self.frame_main, text="Clear", state="disabled", command=self.clear_confirmar)
        self.btn_clear_confirmar.grid(row=1, column=3, padx=5)

        # Botones CSV / Procesados
        self.btn_cargar_csv = tk.Button(self.frame_main, text="Cargar CSV", command=self.cargar_csv)
        self.btn_cargar_csv.grid(row=1, column=4, padx=5)
        self.btn_cargar_procesados = tk.Button(self.frame_main, text="Cargar datos procesados", command=self.cargar_procesados)
        self.btn_cargar_procesados.grid(row=1, column=5, padx=5)
        self.btn_guardar_procesados = tk.Button(self.frame_main, text="Guardar datos procesados", command=self.guardar_procesados, state="disabled")
        self.btn_guardar_procesados.grid(row=1, column=6, padx=5)

        # Botón YFinance
        self.btn_yfinance = tk.Button(self.frame_main, text="Cargar YFinance", command=self.cargar_yfinance)
        self.btn_yfinance.grid(row=1, column=7, padx=5)

        # Botón Reset Zoom (NUEVO)
        self.btn_reset_zoom = tk.Button(self.frame_main, text="Reset Zoom", command=self.reset_zoom, state="disabled")
        self.btn_reset_zoom.grid(row=1, column=8, padx=5)

    # ---------------- Funciones Combobox ----------------
    def actualizar_segundo(self):
        seleccion1 = self.combo1.get()
        opciones2 = [m for m in self.monedas if m != seleccion1]
        self.combo2['values'] = opciones2
        if self.combo2.get() == seleccion1:
            self.combo2.set('')

    def on_seleccion(self, event):
        self.actualizar_segundo()
        if self.combo1.get() and self.combo2.get():
            self.btn_confirmar.config(state="normal")
            self.btn_cargar_csv.config(state="disabled")
        else:
            self.btn_confirmar.config(state="disabled")
            self.btn_cargar_csv.config(state="normal")

    # ---------------- Confirmar ----------------
    def confirmar(self):
        self.btn_confirmar.config(state="disabled")
        self.btn_clear_confirmar.config(state="normal")
        self.combo1.config(state="disabled")
        self.combo2.config(state="disabled")

    def clear_confirmar(self):
        self.combo1.set(""); self.combo2.set("")
        self.combo1.config(state="readonly"); self.combo2.config(state="readonly")
        self.btn_confirmar.config(state="disabled"); self.btn_clear_confirmar.config(state="disabled")
        self.btn_cargar_csv.config(state="normal")

    # ---------------- Cargar CSV ----------------
    def cargar_csv(self):
        df = self.csv_manager.cargar_csv()
        if df is not None:
            CSVLoaderModal(self.root, df, callback=self._on_csv_cargado)

    def _on_csv_cargado(self, df_seleccion):
        self.df_actual = df_seleccion
        self._dibujar_grafico(df_seleccion)
        self.btn_guardar_procesados.config(state="normal")
        self.btn_reset_zoom.config(state="normal")  # Habilitar reset zoom

    # ---------------- Cargar datos procesados ----------------
    def cargar_procesados(self):
        df = self.csv_manager.cargar_procesados()
        if df is not None:
            self.df_actual = df
            self._dibujar_grafico(df)
            self.btn_guardar_procesados.config(state="normal")
            self.btn_reset_zoom.config(state="normal")  # Habilitar reset zoom

    # ---------------- Guardar datos procesados ----------------
    def guardar_procesados(self):
        self.csv_manager.df_cache = self.df_actual
        self.csv_manager.guardar_procesados()

    # ---------------- Cargar YFinance ----------------
    def cargar_yfinance(self):
        base = self.combo1.get()
        cotizada = self.combo2.get()
        if not base or not cotizada:
            messagebox.showwarning("Atención", "Selecciona ambas monedas para YFinance")
            return
        self.df_actual = self.yfinance_manager.obtener_datos(base, cotizada, "1mo", "1d")
        self._dibujar_grafico(self.df_actual)
        self.btn_reset_zoom.config(state="normal")  # Habilitar reset zoom

    # ---------------- Dibujar gráfico ----------------
    def _dibujar_grafico(self, df):
        self.grafico_manager.dibujar_csv(df)
        self.tooltip_zoom_pan = TooltipZoomPan(self.root, self.grafico_manager.canvas, self.grafico_manager.grafico)

    # ---------------- Reset Zoom (NUEVO) ----------------
    def reset_zoom(self):
        """Restaura el zoom inicial del gráfico"""
        if self.tooltip_zoom_pan:
            self.tooltip_zoom_pan.reset_zoom()

    # ---------------- Run ----------------
    def run(self):
        self.root.mainloop()