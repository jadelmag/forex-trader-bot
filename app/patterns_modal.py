# app/patterns_modal.py

import tkinter as tk
from tkinter import ttk
from patterns.candlestickpatterns import CandlestickPatterns
import threading
import pandas as pd

class ScrollableFrame(ttk.Frame):
    """Frame con scroll vertical confiable"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        canvas = tk.Canvas(self, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self.window_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self.window_id, width=e.width)
        )

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Scroll con rueda del mouse
        self.scrollable_frame.bind(
            "<Enter>",
            lambda e: canvas.bind_all(
                "<MouseWheel>",
                lambda ev: canvas.yview_scroll(int(-1*(ev.delta/120)), "units")
            )
        )
        self.scrollable_frame.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

class PatternsModal(tk.Toplevel):
    def __init__(self, master, df, grafico_manager, gui_principal, callback=None):
        super().__init__(master)
        self.df = df
        self.grafico_manager = grafico_manager
        self.gui_principal = gui_principal
        self.callback = callback
        self.selected_patterns = []

        self.title("Seleccionar patrones")
        self.geometry("350x450")
        self.resizable(True, True)
        self.grab_set()

        self.one_candle_patterns = [
            'doji', 'hammer', 'hanging_man', 'shooting_star', 'spinning_top', 'inverted_hammer'
        ]
        self.two_candle_patterns = [
            'bullish_engulfing', 'bearish_engulfing', 'piercing_line', 'dark_cloud_cover',
            'tweezer_top', 'tweezer_bottom'
        ]
        self.three_candle_patterns = [
            'morning_star', 'evening_star', 'three_white_soldiers', 'three_black_crows',
            'three_inside_up', 'three_inside_down', 'rising_three_methods', 'falling_three_methods'
        ]
        self.other_patterns = []

        self.vars = {}

        scroll_frame = ScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def add_section(title, patterns_list):
            lbl = ttk.Label(scroll_frame.scrollable_frame, text=title, font=("Segoe UI", 10, "bold"))
            lbl.pack(anchor="w", pady=(10,2))
            for pattern in patterns_list:
                var = tk.IntVar(value=1)
                chk = ttk.Checkbutton(
                    scroll_frame.scrollable_frame,
                    text=pattern.replace("_"," ").title(),
                    variable=var
                )
                chk.pack(fill="x", anchor="w", pady=1)
                self.vars[pattern] = var

        add_section("----- Patrones de una vela -----", self.one_candle_patterns)
        add_section("----- Patrones de dos velas -----", self.two_candle_patterns)
        add_section("----- Patrones de tres velas -----", self.three_candle_patterns)
        add_section("----- Otros patrones -----", self.other_patterns)

        # Barra de progreso y estado
        self.frame_progress = ttk.Frame(self)
        self.frame_progress.pack(padx=10, pady=(5, 0), fill="x")
        self.progress = ttk.Progressbar(self.frame_progress, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")
        self.lbl_progress = ttk.Label(self.frame_progress, text="")
        self.lbl_progress.pack(anchor="w", pady=(2, 8))

        frame_buttons = ttk.Frame(self)
        frame_buttons.pack(pady=10, fill="x")
        self.btn_cancel = ttk.Button(frame_buttons, text="Cancelar", command=self.destroy)
        self.btn_cancel.pack(side="left", padx=5, expand=True, fill="x")
        self.btn_accept = ttk.Button(frame_buttons, text="Aceptar", command=self.on_accept)
        self.btn_accept.pack(side="left", padx=5, expand=True, fill="x")

        self.center_window()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        parent_x = self.master.winfo_rootx() if self.master else 0
        parent_y = self.master.winfo_rooty() if self.master else 0
        parent_w = self.master.winfo_width() if self.master else self.winfo_screenwidth()
        parent_h = self.master.winfo_height() if self.master else self.winfo_screenheight()
        x = parent_x + (parent_w // 2) - (w // 2)
        y = parent_y + (parent_h // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def on_accept(self):
        # Determinar selección y preparar progreso
        self.selected_patterns = [p for p, var in self.vars.items() if var.get() == 1]
        if not self.selected_patterns:
            self.lbl_progress.config(text="Seleccione al menos un patrón")
            return
        self.progress.config(maximum=len(self.selected_patterns), value=0)
        self.lbl_progress.config(text=f"Procesando 0/{len(self.selected_patterns)} patrones...")
        # Deshabilitar aceptar mientras procesa
        self.btn_accept.state(["disabled"])
        # Ejecutar procesamiento en thread para no bloquear GUI
        thread = threading.Thread(target=self.aplicar_patrones_thread)
        thread.start()

    def aplicar_patrones_thread(self):
        patterns = CandlestickPatterns(self.df)
        selected_patterns = self.selected_patterns

        df_patrones = self.df.copy()
        encontrados_totales = 0
        for pattern_name in selected_patterns:
            df_patrones[pattern_name] = patterns.__getattribute__(pattern_name)()['Signal']
            # contar coincidencias del patrón actual
            encontrados_patron = (df_patrones[pattern_name] != 0).sum()
            encontrados_totales += int(encontrados_patron)
            # actualizar progreso en el hilo de UI
            idx_actual = selected_patterns.index(pattern_name) + 1
            self.after(0, lambda i=idx_actual, total=len(selected_patterns), p=pattern_name, found=encontrados_totales: (
                self.progress.config(value=i),
                self.lbl_progress.config(text=f"Procesando {i}/{total} patrones... | Coincidencias: {found}")
            ))

        pattern_cols = df_patrones.columns.difference(['Open','High','Low','Close'])
        has_bull = (df_patrones[pattern_cols] == 1).any(axis=1)
        has_bear = (df_patrones[pattern_cols] == -1).any(axis=1)
        df_patrones['Final_Signal'] = 0
        df_patrones.loc[has_bull & ~has_bear, 'Final_Signal'] = 1
        df_patrones.loc[has_bear & ~has_bull, 'Final_Signal'] = -1

        # Actualizar GUI usando after
        self.after(0, lambda: self.actualizar_grafico_log(df_patrones, selected_patterns))

    def actualizar_grafico_log(self, df_patrones, patterns_list):
        if self.grafico_manager:
            self.grafico_manager.dibujar_csv(df_patrones)
        if self.callback:
            self.callback(df_patrones)

        if self.gui_principal is not None:
            for pattern_name in patterns_list:
                for i, row in df_patrones.iterrows():
                    if row[pattern_name] != 0:
                        fecha = row.name if isinstance(row.name, pd.Timestamp) else pd.to_datetime(row.name)
                        fecha_str = fecha.strftime("%d/%m/%Y")
                        color = "gray"
                        if row["Close"] > row["Open"]:
                            color = "green"
                        elif row["Close"] < row["Open"]:
                            color = "red"
                        mensaje = f"Patrón: {pattern_name} | Fecha: {fecha_str} | Open: {row['Open']:.5f} | Close: {row['Close']:.5f}"
                        self.gui_principal.log(mensaje, color=color)

        # Completar progreso y re-habilitar por si el modal no se cerrara aún
        try:
            self.progress.config(value=self.progress.cget('maximum'))
            self.lbl_progress.config(text=self.lbl_progress.cget('text') + " | Completado")
            self.btn_accept.state(["!disabled"])
        except Exception:
            pass

        self.destroy()
