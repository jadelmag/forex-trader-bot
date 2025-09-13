# app/candle_strategies_modal.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import inspect
from strategies.candle_strategies import CandleStrategies

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

class CandleStrategiesModal(tk.Toplevel):
    def __init__(self, master, df, gui_principal, callback=None):
        super().__init__(master)
        self.df = df
        self.gui_principal = gui_principal
        self.callback = callback
        
        self.title("Estrategias de velas")
        self.geometry("450x600")
        self.resizable(True, True)
        self.grab_set()
        
        # Variables para checkboxes
        self.strategy_vars = {}
        
        # Obtener todas las estrategias disponibles
        self.available_strategies = self._get_available_strategies()
        
        self._create_widgets()
        self.center_window()

    def _get_available_strategies(self):
        """Obtiene todas las estrategias disponibles de CandleStrategies"""
        strategies = []
        
        # Crear una instancia temporal para inspeccionar métodos
        temp_instance = CandleStrategies(self.df)
        
        # Obtener todos los métodos que no empiecen con _ y sean callable
        for name in dir(temp_instance):
            if not name.startswith('_') and name not in ['data', 'patterns', 'add_indicators']:
                method = getattr(temp_instance, name)
                if callable(method):
                    # Verificar que el método tenga el parámetro config (indicativo de estrategia)
                    try:
                        sig = inspect.signature(method)
                        if 'config' in sig.parameters:
                            strategies.append(name)
                    except:
                        # Si no se puede inspeccionar, asumir que es una estrategia
                        strategies.append(name)
        
        return sorted(strategies)

    def _create_widgets(self):
        """Crear todos los widgets del modal"""
        
        # Título principal
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = ttk.Label(title_frame, text="Estrategias de velas", 
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(anchor="center")
        
        # Botones de seleccionar/deseleccionar todos
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        btn_select_all = ttk.Button(buttons_frame, text="Seleccionar todos", 
                                   command=self._select_all)
        btn_select_all.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        btn_deselect_all = ttk.Button(buttons_frame, text="Deseleccionar todos", 
                                     command=self._deselect_all)
        btn_deselect_all.pack(side="right", padx=(10, 0), expand=True, fill="x")
        
        # Frame scrollable para las estrategias
        scroll_frame = ScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Crear checkboxes para cada estrategia
        for strategy in self.available_strategies:
            var = tk.IntVar(value=1)  # Seleccionadas por defecto
            self.strategy_vars[strategy] = var
            
            # Formatear nombre de la estrategia para mostrar
            display_name = strategy.replace("_", " ").title()
            
            chk = ttk.Checkbutton(
                scroll_frame.scrollable_frame,
                text=display_name,
                variable=var
            )
            chk.pack(fill="x", anchor="w", pady=2, padx=10)
        
        # Barra de progreso
        self.progress_frame = ttk.Frame(self)
        self.progress_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal", 
                                       mode="determinate")
        self.progress.pack(fill="x")
        
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor="w", pady=(2, 0))
        
        # Inicialmente ocultar la barra de progreso
        self.progress_frame.pack_forget()
        
        # Botones de acción
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        self.btn_cancel = ttk.Button(action_frame, text="Cancelar", 
                                    command=self.destroy)
        self.btn_cancel.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        self.btn_accept = ttk.Button(action_frame, text="Aceptar", 
                                    command=self.on_accept)
        self.btn_accept.pack(side="right", padx=(10, 0), expand=True, fill="x")

    def center_window(self):
        """Centrar el modal en el contenedor padre"""
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

    def _select_all(self):
        """Seleccionar todas las estrategias"""
        for var in self.strategy_vars.values():
            var.set(1)

    def _deselect_all(self):
        """Deseleccionar todas las estrategias"""
        for var in self.strategy_vars.values():
            var.set(0)

    def on_accept(self):
        """Manejar el botón Aceptar"""
        # Obtener estrategias seleccionadas
        selected_strategies = [strategy for strategy, var in self.strategy_vars.items() 
                              if var.get() == 1]
        
        if not selected_strategies:
            messagebox.showwarning("Atención", "Seleccione al menos una estrategia")
            return
        
        # Usar valor por defecto para operaciones
        max_operations = 5
        
        # Mostrar barra de progreso
        self.progress_frame.pack(fill="x", padx=20, pady=(10, 0))
        self.progress.config(maximum=100, value=0)
        self.progress_label.config(text="Iniciando simulación...")
        
        # Deshabilitar botones
        self.btn_accept.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        
        # Ejecutar simulación en hilo separado
        thread = threading.Thread(target=self._run_simulation, 
                                 args=(selected_strategies,))
        thread.daemon = True
        thread.start()

    def _run_simulation(self, selected_strategies):
        """Ejecutar la simulación de estrategias de velas"""
        try:
            # Llamar al método de simulación en gui_principal
            if hasattr(self.gui_principal, 'simular_estrategias_velas'):
                self.gui_principal.simular_estrategias_velas(
                    selected_strategies, 0,
                    progress_callback=self._update_progress
                )
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Error", "Método de simulación no encontrado"))
                
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(
                "Error", f"Error durante la simulación: {str(e)}"))
        finally:
            # Cerrar modal
            self.after(0, self.destroy)

    def _update_progress(self, value, text=""):
        """Actualizar la barra de progreso desde el hilo de simulación"""
        def update():
            self.progress['value'] = value
            if text:
                self.progress_label.config(text=f"{text} ({value:.1f}%)")
            else:
                self.progress_label.config(text=f"{value:.1f}%")
            self.update_idletasks()
        
        self.after(0, update)