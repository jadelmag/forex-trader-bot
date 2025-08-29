# app/strategies_modal.py

import tkinter as tk
from tkinter import ttk

class EstrategiasModal(tk.Toplevel):
    def __init__(self, parent, estrategias_fx, estrategias_candle, callback):
        super().__init__(parent)
        self.parent = parent
        self.callback = callback
        self.title("Seleccionar Estrategias")
        self.resizable(False, False)
        self.grab_set()  # modal

        # Calcular altura basada en el número total de estrategias
        total_estrategias = len(estrategias_fx) + len(estrategias_candle)
        h = 120 + 40 * total_estrategias  # altura aumentada para los nuevos checkboxes

        # Centrar ventana sobre el padre
        self.update_idletasks()
        w = 500
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Frame principal con scrollbar
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Canvas y scrollbar para estrategias
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Diccionario de controles
        self.controls = {}

        # ---------------- SECCIÓN FOREX STRATEGIES ----------------
        if estrategias_fx:
            lbl_fx = tk.Label(scrollable_frame, text="Forex Strategies", 
                             font=("Arial", 10, "bold"), anchor="w")
            lbl_fx.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

            # Encabezado para Forex Strategies
            tk.Label(scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=1, column=0, padx=5)
            tk.Label(scrollable_frame, text="% Riesgo", width=10).grid(row=1, column=1, padx=5)
            tk.Label(scrollable_frame, text="RR Ratio", width=10).grid(row=1, column=2, padx=5)

            # Estrategias Forex con parámetros
            for idx, nombre in enumerate(estrategias_fx, start=2):
                var_check = tk.IntVar()
                chk = tk.Checkbutton(scrollable_frame, text=nombre, variable=var_check, 
                                    anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)

                var_riesgo = tk.StringVar(value="1.0")  # % por defecto
                entry_riesgo = tk.Entry(scrollable_frame, textvariable=var_riesgo, width=8)
                entry_riesgo.grid(row=idx, column=1, padx=5)

                var_rr = tk.StringVar(value="2")  # ratio por defecto
                entry_rr = tk.Entry(scrollable_frame, textvariable=var_rr, width=8)
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
            
            lbl_candle = tk.Label(scrollable_frame, text="Candle Strategies", 
                                 font=("Arial", 10, "bold"), anchor="w")
            lbl_candle.grid(row=start_row, column=0, columnspan=3, sticky="w", pady=(20, 10))

            # Encabezado para Candle Strategies (sin parámetros de riesgo)
            tk.Label(scrollable_frame, text="Estrategia", width=20, anchor="w").grid(row=start_row+1, column=0, padx=5)
            tk.Label(scrollable_frame, text="Sin parámetros", width=20).grid(row=start_row+1, column=1, columnspan=2, padx=5)

            # Estrategias Candle (sin parámetros de riesgo)
            for idx, nombre in enumerate(estrategias_candle, start=start_row+2):
                var_check = tk.IntVar()
                chk = tk.Checkbutton(scrollable_frame, text=nombre, variable=var_check, 
                                    anchor="w", width=20)
                chk.grid(row=idx, column=0, sticky="w", padx=5, pady=2)

                # Espacio vacío para alinear con las forex strategies
                tk.Label(scrollable_frame, text="").grid(row=idx, column=1, padx=5)
                tk.Label(scrollable_frame, text="").grid(row=idx, column=2, padx=5)

                self.controls[nombre] = {
                    "selected": var_check,
                    "tipo": "candle"
                }

        # ---------------- CHECKBOXES DE OPCIONES ----------------
        # Calcular la fila donde colocar los checkboxes
        options_row = start_row + len(estrategias_candle) + 2 if estrategias_candle else len(estrategias_fx) + 2
        
        # Checkbox para mostrar detección de patrones
        self.var_mostrar_deteccion = tk.IntVar(value=1)  # Habilitado por defecto
        chk_deteccion = tk.Checkbutton(
            scrollable_frame, 
            text="Mostrar detección de patrones", 
            variable=self.var_mostrar_deteccion,
            anchor="w"
        )
        chk_deteccion.grid(row=options_row, column=0, columnspan=3, sticky="w", padx=5, pady=(20, 5))
        
        # Checkbox para mostrar simulación
        self.var_mostrar_simulacion = tk.IntVar(value=1)  # Habilitado por defecto
        chk_simulacion = tk.Checkbutton(
            scrollable_frame, 
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