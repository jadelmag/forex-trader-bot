# app/csv_loader_modal.py

import tkinter as tk
from tkinter import ttk
import threading
import time

from .progress_modal import ProgressModal, centrar_ventana


class CSVLoaderModal(tk.Toplevel):
    def __init__(self, parent, df, callback):
        super().__init__(parent)
        self.parent = parent
        self.df = df
        self.callback = callback
        self.title("Seleccionar filas a cargar")
        self.geometry("300x150")
        self.resizable(False, False)
        self.grab_set()  # Modal

        # Centrar sobre ventana principal
        centrar_ventana(self, parent)

        tk.Label(self, text=f"Total de elementos: {len(df)}").grid(row=0, column=0, columnspan=2, pady=10)

        # Variables de control
        self.var_cargar_todo = tk.IntVar(value=1)
        self.var_cargar_n = tk.IntVar(value=0)

        # Checkbutton "Cargar todo"
        self.chk_todo = tk.Checkbutton(self, text="Cargar todo el fichero", variable=self.var_cargar_todo,
                                       command=self._toggle_checks)
        self.chk_todo.grid(row=1, column=0, columnspan=2, sticky="w", padx=20)

        # Checkbutton "Cargar número de filas" + Entry
        self.chk_n = tk.Checkbutton(self, text="Cargar número de filas:", variable=self.var_cargar_n,
                                    command=self._toggle_checks)
        self.chk_n.grid(row=2, column=0, sticky="w", padx=20)
        self.entry_n = tk.Entry(self, width=6)
        self.entry_n.grid(row=2, column=1, sticky="w")
        self.entry_n.bind("<KeyRelease>", lambda e: self._actualizar_boton())

        # Botones Cancelar y Aceptar
        self.btn_cancelar = tk.Button(self, text="Cancelar", command=self.destroy)
        self.btn_cancelar.grid(row=3, column=0, pady=20, padx=10, sticky="e")
        self.btn_aceptar = tk.Button(self, text="Aceptar", command=self._aceptar)
        self.btn_aceptar.grid(row=3, column=1, pady=20, padx=10, sticky="w")

        self._actualizar_boton()  # Inicializa el estado del botón

    def _toggle_checks(self):
        # Al seleccionar uno, el otro se deselecciona
        if self.var_cargar_todo.get():
            self.var_cargar_n.set(0)
        elif self.var_cargar_n.get():
            self.var_cargar_todo.set(0)
        self._actualizar_boton()

    def _actualizar_boton(self):
        if self.var_cargar_todo.get():
            self.btn_aceptar.config(state="normal")
        elif self.var_cargar_n.get():
            try:
                n = int(self.entry_n.get())
                self.btn_aceptar.config(state="normal" if n > 0 else "disabled")
            except ValueError:
                self.btn_aceptar.config(state="disabled")
        else:
            self.btn_aceptar.config(state="disabled")

    def _aceptar(self):
        # Determinar filas a cargar
        if self.var_cargar_todo.get():
            df_seleccion = self.df
        else:
            n = int(self.entry_n.get())
            df_seleccion = self.df.head(n)

        # Cerrar modal original
        self.destroy()

        # Crear modal de progreso
        progress_modal = ProgressModal(self.parent, len(df_seleccion))

        def cargar_elementos():
            for idx, row in df_seleccion.iterrows():
                if progress_modal.cancelled:
                    break
                # Simula procesamiento de cada fila (reemplazar con tu lógica real)
                time.sleep(0.05)
                # Actualiza barra en hilo principal
                self.parent.after(0, progress_modal.actualizar)

            # Llamar callback al terminar si no se canceló
            if not progress_modal.cancelled:
                self.parent.after(0, lambda: self.callback(df_seleccion))

        # Ejecutar la carga en hilo separado
        threading.Thread(target=cargar_elementos, daemon=True).start()
