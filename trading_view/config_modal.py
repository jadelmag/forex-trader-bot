import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any

class CandleStreamerConfigModal:
    def __init__(
        self,
        parent,
        symbols: list[str],
        on_connect: Callable[[Dict[str, Any]], None],
        initial_values: Optional[Dict[str, Any]] = None
    ):
        self.parent = parent
        self.on_connect = on_connect
        
        # Configuración de la ventana modal
        self.window = tk.Toplevel(parent)
        self.window.title("Configuración de CandleStreamer")
        self.window.geometry("300x280")
        self.window.resizable(False, False)
        self.window.grab_set()  # Hace que la ventana sea modal
        
        # Frame principal
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Variables para los controles
        self.interval_var = tk.StringVar(value=initial_values.get("interval", "1m") if initial_values else "1m")
        self.max_candles_var = tk.StringVar(value=str(initial_values.get("max_plot", 500)) if initial_values else "500")
        self.symbol_var = tk.StringVar(value=initial_values.get("symbol", "") if initial_values and "symbol" in initial_values else (symbols[0] if symbols else ""))
        self.initial_money_var = tk.StringVar(value=str(initial_values.get("initial_money", "1000")) if initial_values else "1000")
        self.visible_candles_var = tk.StringVar(value=str(initial_values.get("visible_candles", 5)) if initial_values else "5")
        
        # Estilo
        style = ttk.Style()
        style.configure('TButton', padding=2, font=('Segoe UI', 9))
        style.configure('Small.TButton', padding=1, font=('Segoe UI', 8))
        style.configure("TLabel", padding=2)
        
        # Controles del formulario
        ttk.Label(main_frame, text="Intervalo:").grid(row=0, column=0, sticky="w", pady=5)
        interval_combo = ttk.Combobox(
            main_frame,
            textvariable=self.interval_var,
            values=["1s", "5s", "10s", "20s", "30s", "40s", "50s", "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m", "10m"],
            state="readonly",
            width=10
        )
        interval_combo.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        
        ttk.Label(main_frame, text="Máximo de velas:").grid(row=1, column=0, sticky="w", pady=5)
        max_candles_combo = ttk.Combobox(
            main_frame,
            textvariable=self.max_candles_var,
            values=["100", "200", "300", "400", "500", "700", "1000", "1500", "2000"],
            state="readonly",
            width=10
        )
        max_candles_combo.grid(row=1, column=1, sticky="w", pady=5, padx=5)
        
        ttk.Label(main_frame, text="Moneda:").grid(row=2, column=0, sticky="w", pady=5)
        self.symbol_combo = ttk.Combobox(
            main_frame,
            textvariable=self.symbol_var,
            values=symbols,
            state="readonly",
            width=15
        )
        self.symbol_combo.grid(row=2, column=1, sticky="w", pady=5, padx=5)
        
        # Campo para el dinero inicial
        ttk.Label(main_frame, text="Dinero inicial:").grid(row=3, column=0, sticky="w", pady=5)
        initial_money_entry = ttk.Entry(
            main_frame,
            textvariable=self.initial_money_var,
            width=15
        )
        initial_money_entry.grid(row=3, column=1, sticky="w", pady=5, padx=5)
        
        # Campo para velas visibles
        ttk.Label(main_frame, text="Velas iniciales:").grid(row=4, column=0, sticky="w", pady=5)
        visible_candles_combo = ttk.Combobox(
            main_frame,
            textvariable=self.visible_candles_var,
            values=["5", "6", "7", "8", "9", "10"],
            state="readonly",
            width=10
        )
        visible_candles_combo.grid(row=4, column=1, sticky="w", pady=5, padx=5)
        
        # Frame para los botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        # Botón Cancelar
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancelar",
            command=self._on_cancel,
            style='Small.TButton'
        )
        cancel_btn.pack(side=tk.LEFT, padx=2)
        
        # Botón Aceptar
        connect_btn = ttk.Button(
            button_frame,
            text="Aceptar",
            command=self._on_connect,
            style='Small.TButton'
        )
        connect_btn.pack(side=tk.LEFT, padx=2)
        
        # Centrar la ventana
        self._center_window()
    
    def _center_window(self):
        """Centra la ventana respecto a la ventana padre"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        
        # Obtener posición y dimensiones de la ventana padre
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calcular posición para centrar respecto al padre
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        
        # Asegurar que la ventana no se salga de la pantalla
        x = max(0, min(x, self.window.winfo_screenwidth() - width))
        y = max(0, min(y, self.window.winfo_screenheight() - height))
        
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def _on_connect(self):
        """Maneja el evento de clic en el botón Conectar"""
        try:
            initial_money = float(self.initial_money_var.get())
            if initial_money <= 0:
                messagebox.showerror("Error", "El dinero inicial debe ser un número positivo")
                return
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese un valor numérico válido para el dinero inicial")
            return
            
        try:
            visible_candles = int(self.visible_candles_var.get())
            if visible_candles <= 0:
                messagebox.showerror("Error", "Las velas visibles deben ser un número positivo")
                return
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese un valor numérico válido para las velas visibles")
            return
            
        config = {
            "interval": self.interval_var.get(),
            "max_plot": int(self.max_candles_var.get()),
            "symbol": self.symbol_var.get(),
            "initial_money": initial_money,
            "visible_candles": visible_candles
        }
        self.on_connect(config)
        self.window.destroy()
    
    def _on_cancel(self):
        """Maneja el evento de clic en el botón Cancelar"""
        self.window.destroy()

