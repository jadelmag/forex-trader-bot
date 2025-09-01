# app/strategies_modal.py

import tkinter as tk
from tkinter import ttk

class EstrategiasModal(tk.Toplevel):
    def __init__(self, parent, estrategias_fx, estrategias_candle, callback, patrones_list=None):
        super().__init__(parent)
        self.parent = parent
        self.callback = callback
        self.title("Seleccionar Estrategias")
        self.resizable(False, False)
        self.grab_set()  # modal

        # Altura fija de la zona de estrategias (scrollable)
        list_area_height = 400

        # Centrar ventana sobre el padre
        self.update_idletasks()
        w = 500
        # Altura total del modal: área de lista (400) + controles inferiores
        h_total = 500
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h_total) // 2
        self.geometry(f"{w}x{h_total}+{x}+{y}")

        # Frame principal con scrollbar
        main_frame = tk.Frame(self)
        main_frame.pack(fill="x", expand=False, padx=10, pady=10)
        # Fijar altura visible de la lista a 400 y evitar que se expanda
        main_frame.configure(height=list_area_height)
        main_frame.pack_propagate(False)

        # Canvas y scrollbar para estrategias
        self.canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            main_frame,
            orient="vertical",
            style="Logs.Vertical.TScrollbar",
            command=self.canvas.yview,
        )
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        # Activar/desactivar scroll con rueda al entrar/salir
        self.scrollable_frame.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.scrollable_frame.bind("<Leave>", lambda e: self._unbind_mousewheel())

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set, height=list_area_height)

        # Pack canvas y scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Diccionario de controles
        self.controls = {}

        # ---------------- SECCIÓN FOREX STRATEGIES ----------------
        if estrategias_fx:
            lbl_fx = tk.Label(self.scrollable_frame, text="Forex Strategies", 
                             font=("Arial", 10, "bold"), anchor="w")
            lbl_fx.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

            # Encabezado para Forex Strategies
            tk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=1, column=0, padx=5)
            tk.Label(self.scrollable_frame, text="% Riesgo", width=10).grid(row=1, column=1, padx=5)
            tk.Label(self.scrollable_frame, text="RR Ratio", width=10).grid(row=1, column=2, padx=5)

            # Estrategias Forex con parámetros
            for idx, nombre in enumerate(estrategias_fx, start=2):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                chk = tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check, 
                                    anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)

                var_riesgo = tk.StringVar(value="1.0")  # % por defecto
                entry_riesgo = tk.Entry(self.scrollable_frame, textvariable=var_riesgo, width=8)
                entry_riesgo.grid(row=idx, column=1, padx=5)

                var_rr = tk.StringVar(value="2")  # ratio por defecto
                entry_rr = tk.Entry(self.scrollable_frame, textvariable=var_rr, width=8)
                entry_rr.grid(row=idx, column=2, padx=5)

                self.controls[nombre] = {
                    "selected": var_check,
                    "riesgo": var_riesgo,
                    "rr": var_rr,
                    "tipo": "forex"
                }

        # ---------------- SECCIÓN CANDLE STRATEGIES ----------------
        if estrategias_candle:
            start_row = len(estrategias_fx) + 3 if estrategias_fx else 0
            
            lbl_candle = tk.Label(self.scrollable_frame, text="Candle Strategies", 
                                 font=("Arial", 10, "bold"), anchor="w")
            lbl_candle.grid(row=start_row, column=0, columnspan=3, sticky="w", pady=(20, 10))

            # Encabezado para Candle Strategies (sin parámetros de riesgo)
            tk.Label(self.scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=start_row+1, column=0, padx=5)
            tk.Label(self.scrollable_frame, text="Sin parámetros", width=20).grid(row=start_row+1, column=1, columnspan=2, padx=5)

            # Estrategias Candle (sin parámetros de riesgo)
            for idx, nombre in enumerate(estrategias_candle, start=start_row+2):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                chk = tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check, 
                                    anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)

                # Espacio vacío para alinear con las forex strategies
                tk.Label(self.scrollable_frame, text="").grid(row=idx, column=1, padx=5)
                tk.Label(self.scrollable_frame, text="").grid(row=idx, column=2, padx=5)

                self.controls[nombre] = {
                    "selected": var_check,
                    "tipo": "candle"
                }

        # ---------------- SECCIÓN CANDLESTICK PATTERNS ----------------
        if patrones_list:
            start_row_patterns = (
                (len(estrategias_fx) + 3 if estrategias_fx else 0) +
                (len(estrategias_candle) + 2 if estrategias_candle else 0) + 2
            )

            lbl_patterns = tk.Label(self.scrollable_frame, text="Candlestick Patterns", 
                                    font=("Arial", 10, "bold"), anchor="w")
            lbl_patterns.grid(row=start_row_patterns, column=0, columnspan=3, sticky="w", pady=(20, 10))

            tk.Label(self.scrollable_frame, text="Patrón", width=20, anchor="w").grid(row=start_row_patterns+1, column=0, padx=5)
            tk.Label(self.scrollable_frame, text="Sin parámetros", width=20).grid(row=start_row_patterns+1, column=1, columnspan=2, padx=5)

            for idx, nombre in enumerate(sorted(patrones_list), start=start_row_patterns+2):
                var_check = tk.IntVar()
                display_name = nombre.replace('_', ' ').capitalize()
                chk = tk.Checkbutton(self.scrollable_frame, text=display_name, variable=var_check, 
                                    anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)
                tk.Label(self.scrollable_frame, text="").grid(row=idx, column=1, padx=5)
                tk.Label(self.scrollable_frame, text="").grid(row=idx, column=2, padx=5)

                self.controls[nombre] = {
                    "selected": var_check,
                    "tipo": "pattern"
                }

        # ---------------- CHECKBOXES DE OPCIONES ----------------
        # Calcular la fila donde colocar los checkboxes
        base_row = 0
        if estrategias_fx:
            base_row = max(base_row, 2 + len(estrategias_fx))
        if estrategias_candle:
            base_row = max(base_row, (len(estrategias_fx) + 3 if estrategias_fx else 0) + 2 + len(estrategias_candle))
        if patrones_list:
            base_row = max(base_row, (
                (len(estrategias_fx) + 3 if estrategias_fx else 0) +
                (len(estrategias_candle) + 2 if estrategias_candle else 0) +
                2 + len(patrones_list)
            ))
        options_row = base_row + 2
        
        # Checkbox para mostrar detección de patrones
        self.var_mostrar_deteccion = tk.IntVar(value=1)  # Habilitado por defecto
        chk_deteccion = tk.Checkbutton(
            self.scrollable_frame, 
            text="Mostrar detección de patrones", 
            variable=self.var_mostrar_deteccion,
            anchor="w"
        )
        chk_deteccion.grid(row=options_row, column=0, columnspan=3, sticky="w", padx=5, pady=(20, 5))
        
        # Checkbox para mostrar simulación
        self.var_mostrar_simulacion = tk.IntVar(value=1)  # Habilitado por defecto
        chk_simulacion = tk.Checkbutton(
            self.scrollable_frame, 
            text="Mostrar simulación con Risk Manager", 
            variable=self.var_mostrar_simulacion,
            anchor="w"
        )
        chk_simulacion.grid(row=options_row + 1, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        # ---------------- CAMPO MAX ORDENES ----------------
        frame_max = tk.Frame(self)
        frame_max.pack(pady=5)
        tk.Label(frame_max, text="Número máximo de órdenes:").pack(side="left", padx=5)
        self.max_orders_var = tk.StringVar(value="5")
        self.entry_max_orders = tk.Entry(frame_max, textvariable=self.max_orders_var, width=5)
        self.entry_max_orders.pack(side="left")

        # Botones Cancelar y Aceptar
        frame_btn = tk.Frame(self)
        frame_btn.pack(pady=10)
        btn_cancelar = tk.Button(frame_btn, text="Cancelar", command=self.destroy)
        btn_cancelar.pack(side="left", padx=10)
        btn_aceptar = tk.Button(frame_btn, text="Aceptar", command=self._aceptar)
        btn_aceptar.pack(side="left", padx=10)

    def _aceptar(self):
        seleccion = {}
        for nombre, ctrl in self.controls.items():
            if ctrl["selected"].get():
                if ctrl["tipo"] == "forex":
                    # Para Forex Strategies: incluir parámetros de riesgo
                    try:
                        riesgo = float(ctrl["riesgo"].get()) / 100  # convertir % a fracción
                        rr = float(ctrl["rr"].get())
                    except ValueError:
                        continue
                    seleccion[nombre] = {"riesgo": riesgo, "rr": rr, "tipo": "forex"}
                else:
                    # Para Candle Strategies: solo marcar como seleccionada
                    seleccion[nombre] = {"tipo": "candle"}

        # Añadir max_orders y opciones de visualización al resultado
        try:
            max_orders = int(self.max_orders_var.get())
        except ValueError:
            max_orders = 5  # valor por defecto en caso de error

        opciones = {
            "mostrar_deteccion": bool(self.var_mostrar_deteccion.get()),
            "mostrar_simulacion": bool(self.var_mostrar_simulacion.get())
        }

        self.destroy()
        if self.callback:
            self.callback(seleccion, max_orders, opciones)

    # --- Mouse wheel support for scrolling ---
    def _bind_mousewheel(self):
        try:
            # Windows and MacOS
            self.bind_all("<MouseWheel>", self._on_mousewheel)
            # Linux (X11)
            self.bind_all("<Button-4>", self._on_mousewheel)
            self.bind_all("<Button-5>", self._on_mousewheel)
        except Exception:
            pass

    def _unbind_mousewheel(self):
        try:
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")
        except Exception:
            pass

    def _on_mousewheel(self, event):
        try:
            if getattr(event, 'num', None) == 4 or getattr(event, 'delta', 0) > 0:
                self.canvas.yview_scroll(-1, "units")
            elif getattr(event, 'num', None) == 5 or getattr(event, 'delta', 0) < 0:
                self.canvas.yview_scroll(1, "units")
        except Exception:
            pass