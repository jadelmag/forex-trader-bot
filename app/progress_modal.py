# app/progress_modal.py

import tkinter as tk
from tkinter import ttk

def centrar_ventana(top, parent):
    """Centrar una ventana 'top' sobre su ventana padre 'parent'"""
    top.update_idletasks()
    w_top = top.winfo_width()
    h_top = top.winfo_height()
    
    w_parent = parent.winfo_width()
    h_parent = parent.winfo_height()
    x_parent = parent.winfo_rootx()
    y_parent = parent.winfo_rooty()
    
    x = x_parent + (w_parent - w_top) // 2
    y = y_parent + (h_parent - h_top) // 2
    top.geometry(f"+{x}+{y}")


class ProgressModal:
    def __init__(self, parent, total_items):
        self.parent = parent
        self.top = tk.Toplevel(parent)
        self.top.title("Cargando elementos")
        self.top.geometry("450x150")
        self.top.grab_set()
        self.top.resizable(False, False)

        self.total_items = total_items
        self.cancelled = False
        self.value = 0

        # Etiqueta de descripción
        self.label_desc = tk.Label(self.top, text="Cargando todos los elementos...")
        self.label_desc.pack(pady=(10, 5))

        # Barra de progreso
        self.progress = ttk.Progressbar(self.top, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)
        self.progress['maximum'] = total_items

        # Etiqueta de porcentaje
        self.label_percent = tk.Label(self.top, text=f"0% (0/{total_items})")
        self.label_percent.pack(pady=(5, 10))

        # Botón cancelar
        self.btn_cancel = tk.Button(self.top, text="Cancelar", command=self.cancelar)
        self.btn_cancel.pack(pady=5)

        # Centrar sobre la ventana principal
        centrar_ventana(self.top, parent)

    def actualizar(self):
        """Actualizar barra de progreso y porcentaje"""
        if self.cancelled or not self.top.winfo_exists():
            return  # No actualizar si la ventana fue cerrada

        try:
            self.value += 1
            if self.value > self.total_items:
                self.value = self.total_items
            self.progress['value'] = self.value
            porcentaje = int((self.value / self.total_items) * 100)
            self.label_percent.config(text=f"{porcentaje}% ({self.value}/{self.total_items})")
            self.top.update_idletasks()
        except tk.TclError:
            # La ventana fue destruida mientras se actualizaba
            pass

    def cancelar(self):
        """Cancelar la carga"""
        self.cancelled = True
        self.top.destroy()
