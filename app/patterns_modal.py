# app/patterns_modal.py

import tkinter as tk
from tkinter import ttk
from patterns.candlestickpatterns import CandlestickPatterns  # paquete externo

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
    def __init__(self, parent, df, grafico_manager, callback=None):
        super().__init__(parent)
        self.master = parent
        self.df = df
        self.grafico_manager = grafico_manager
        self.callback = callback

        self.title("Seleccionar patrones")
        self.geometry("350x450")
        self.resizable(True, True)
        self.grab_set()  # Modal

        # Definir categorías de patrones
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
        self.other_patterns = []  # Otros patrones si existen

        self.vars = {}

        # Scrollable frame
        scroll_frame = ScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Función para agregar secciones
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

        # Agregar todas las secciones
        add_section("----- Patrones de una vela -----", self.one_candle_patterns)
        add_section("----- Patrones de dos velas -----", self.two_candle_patterns)
        add_section("----- Patrones de tres velas -----", self.three_candle_patterns)
        add_section("----- Otros patrones -----", self.other_patterns)

        # Botones en fila compacta
        frame_buttons = ttk.Frame(self)
        frame_buttons.pack(pady=10, fill="x")
        ttk.Button(frame_buttons, text="Cancelar", command=self.destroy).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(frame_buttons, text="Aceptar", command=self.aplicar_patrones).pack(side="left", padx=5, expand=True, fill="x")

        # Centrar el modal sobre la ventana padre
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()

        if self.master:
            parent_x = self.master.winfo_rootx()
            parent_y = self.master.winfo_rooty()
            parent_w = self.master.winfo_width()
            parent_h = self.master.winfo_height()
        else:
            parent_x = 0
            parent_y = 0
            parent_w = self.winfo_screenwidth()
            parent_h = self.winfo_screenheight()

        x = parent_x + (parent_w // 2) - (w // 2)
        y = parent_y + (parent_h // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def aplicar_patrones(self):
        patterns = CandlestickPatterns(self.df)
        selected_patterns = [p for p, var in self.vars.items() if var.get() == 1]

        df_patrones = self.df.copy()
        for pattern_name in selected_patterns:
            df_patrones[pattern_name] = patterns.__getattribute__(pattern_name)()['Signal']

        pattern_cols = df_patrones.columns.difference(['Open','High','Low','Close'])
        has_bull = (df_patrones[pattern_cols] == 1).any(axis=1)
        has_bear = (df_patrones[pattern_cols] == -1).any(axis=1)
        df_patrones['Final_Signal'] = 0
        df_patrones.loc[has_bull & ~has_bear, 'Final_Signal'] = 1
        df_patrones.loc[has_bear & ~has_bull, 'Final_Signal'] = -1

        if self.grafico_manager:
            self.grafico_manager.dibujar_csv(df_patrones)
        if self.callback:
            self.callback(df_patrones)

        self.destroy()
