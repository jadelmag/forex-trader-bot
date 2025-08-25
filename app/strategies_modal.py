# app/strategies_modal.py

import tkinter as tk
from tkinter import ttk

class EstrategiasModal(tk.Toplevel):
    def __init__(self, parent, estrategias, callback):
        super().__init__(parent)
        self.parent = parent
        self.callback = callback  # función a ejecutar con las estrategias seleccionadas
        self.title("Seleccionar Estrategias")
        self.resizable(False, False)
        self.grab_set()  # modal

        # Centrar ventana sobre el padre
        self.update_idletasks()
        w = 300
        h = 50 + 30 * len(estrategias)
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Variables de control
        self.vars = {}
        for idx, nombre in enumerate(estrategias):
            var = tk.IntVar()
            chk = tk.Checkbutton(self, text=nombre, variable=var)
            chk.pack(anchor="w", padx=20)
            self.vars[nombre] = var

        # Botones Cancelar y Aceptar
        frame_btn = tk.Frame(self)
        frame_btn.pack(pady=10)
        btn_cancelar = tk.Button(frame_btn, text="Cancelar", command=self.destroy)
        btn_cancelar.pack(side="left", padx=10)
        btn_aceptar = tk.Button(frame_btn, text="Aceptar", command=self._aceptar)
        btn_aceptar.pack(side="left", padx=10)

    def _aceptar(self):
        seleccionadas = [name for name, var in self.vars.items() if var.get()]
        self.destroy()
        if self.callback:
            self.callback(seleccionadas)
