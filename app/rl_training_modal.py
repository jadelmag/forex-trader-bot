# app/rl_training_modal.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re


class RLTrainingModal(tk.Toplevel):
    """
    Modal para configurar y ejecutar el entrenamiento de RL.
    - Título: "Entrenamiento de modelo"
    - Barra de progreso (determinada con progreso real)
    - Campo de iteraciones (entero > 0, por defecto 50000)
    - Botón Cancelar: cierra el modal
    - Botón Crear: inicia el entrenamiento llamando a start_training(iteraciones, on_complete)
    """

    def __init__(self, parent, start_training_callback):
        super().__init__(parent)
        self.parent = parent
        self.title("Creación de modelo")
        self.resizable(False, False)
        self.grab_set()  # Modal

        self._start_training_cb = start_training_callback
        self._training_thread = None

        # Contenido
        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        # Título
        ttk.Label(container, text="Creación de modelo", font=("Arial", 12, "bold")).pack(anchor="w")

        # Iteraciones
        it_frame = ttk.Frame(container)
        it_frame.pack(fill="x", pady=(12, 8))
        ttk.Label(it_frame, text="Iteraciones:").pack(side="left")
        self.iter_var = tk.StringVar(value="50000")
        vcmd_int = (self.register(self._validate_positive_int), '%P')
        self.entry_iter = ttk.Entry(it_frame, textvariable=self.iter_var, width=10,
                                    validate='key', validatecommand=vcmd_int)
        self.entry_iter.pack(side="left", padx=(8, 0))
        # Actualizar estado del botón Crear al cambiar el valor
        self.iter_var.trace_add('write', lambda *args: self._update_create_state())

        # Progreso
        prog_frame = ttk.Frame(container)
        prog_frame.pack(fill="x", pady=(8, 8))
        self.progress_label = ttk.Label(prog_frame, text="")
        self.progress = ttk.Progressbar(prog_frame, mode='determinate', length=280)
        # Nota: no empacamos la barra todavía hasta que comience el entrenamiento

        # Botones
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill="x", pady=(8, 0))
        self.btn_cancel = ttk.Button(btn_frame, text="Cancelar", command=self._on_cancel)
        self.btn_cancel.pack(side="right", padx=(8, 0))
        self.btn_create = ttk.Button(btn_frame, text="Crear", command=self._on_create)
        self.btn_create.pack(side="right")

        # Centrar ventana respecto al padre
        self._center()
        # Establecer estado inicial del botón Crear
        self._update_create_state()

    def _center(self):
        self.update_idletasks()
        if self.parent is not None:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 3
            self.geometry(f"{w}x{h}+{x}+{y}")

    def _validate_positive_int(self, P: str) -> bool:
        if P == "":
            return True
        if not re.fullmatch(r"\d+", P or ""):
            return False
        try:
            return int(P) > 0
        except ValueError:
            return False

    def _update_create_state(self):
        """Habilita/Deshabilita el botón Crear según el valor de iteraciones."""
        txt = (self.iter_var.get() or "").strip()
        valid = txt.isdigit() and int(txt) > 0
        try:
            self.btn_create.config(state='normal' if valid else 'disabled')
        except Exception:
            pass

    def _on_cancel(self):
        # No intentamos cancelar el hilo si está corriendo; solo cerramos el modal
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_create(self):
        # Validar iteraciones
        txt = self.iter_var.get().strip()
        if not txt or not txt.isdigit() or int(txt) <= 0:
            messagebox.showerror("Error", "Introduzca un número entero mayor que 0 para las iteraciones")
            return
        iters = int(txt)

        # Deshabilitar acciones y comenzar progreso real
        self.btn_create.config(state='disabled')
        self.btn_cancel.config(state='disabled')
        self.entry_iter.config(state='disabled')
        # Bloquear cierre de la ventana mientras entrena
        try:
            self.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception:
            pass
        # Mostrar la barra ahora y configurar máximos
        try:
            # Primero el texto, luego la barra, para que el layout sea claro
            self.progress_label.pack(anchor="w")
            self.progress.pack(fill="x")
        except Exception:
            pass
        try:
            self.progress.configure(maximum=iters, value=0)
        except Exception:
            pass

        def on_complete(success=True, error_msg=None):
            # Llamado en el hilo de entrenamiento; reinyectar al hilo de UI
            def _done_ui():
                # Rehabilitar cierre y controles (si decides no cerrar automáticamente)
                try:
                    self.protocol("WM_DELETE_WINDOW", self._on_cancel)
                except Exception:
                    pass
                if success:
                    # Forzar 100% visual
                    try:
                        total = int(self.progress.cget('maximum')) if str(self.progress.cget('maximum')).isdigit() else None
                        if total:
                            self.progress['value'] = total
                            self.progress_label.config(text=f"{total} / {total} (100%)")
                    except Exception:
                        pass
                    # Mantener botones deshabilitados y cerrar tras breve pausa
                    self.after(800, self._on_cancel)
                else:
                    messagebox.showerror("RL", error_msg or "Error en el entrenamiento")
                    # En error, permitir reintento
                    self.btn_create.config(state='normal')
                    self.btn_cancel.config(state='normal')
                    self.entry_iter.config(state='normal')
            try:
                self.after(0, _done_ui)
            except Exception:
                pass

        # Progreso (pasos actuales, total)
        def on_progress(current:int, total:int):
            try:
                self.after(0, lambda: self._update_progress(current, total))
            except Exception:
                pass

        # Lanzar entrenamiento en segundo plano usando el callback entregado por el padre
        def _run_training():
            try:
                # Pasamos callback de progreso para barra determinada
                self._start_training_cb(iters, on_complete, on_progress)
            except Exception as e:
                on_complete(success=False, error_msg=str(e))

        self._training_thread = threading.Thread(target=_run_training, daemon=True)
        self._training_thread.start()

    def _update_progress(self, current:int, total:int):
        try:
            # Asegurar máximo correcto y no retroceder
            if total > 0:
                self.progress.configure(maximum=total)
            self.progress['value'] = max(0, min(current, total if total > 0 else current))
            # Actualizar etiqueta con porcentaje y conteo
            if total and total > 0:
                pct = int((max(0, min(current, total)) / total) * 100)
                self.progress_label.config(text=f"{current} / {total} ({pct}%)")
            else:
                self.progress_label.config(text=f"{current}")
        except Exception:
            pass
