# app/gui/components/status_bar.py
import tkinter as tk
from ..utils.constants import COLORS

class StatusBar:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # Variables de estado financiero SEPARADAS
        self.dinero_disponible = 0  # Capital disponible (sin riesgo reservado)
        self.equidad_total = 0      # Capital + P&L flotante de operaciones abiertas
        self.beneficios = 0
        self.perdidas = 0
        
        self._create_status_labels()
        
    def _create_status_labels(self):
        """Crea las etiquetas de estado financiero"""
        # Equity (capital + P&L flotante de operaciones abiertas)
        self.label_dinero = tk.Label(
            self.parent_frame, 
            text=f"Equidad: ${self.equidad_total:,.2f}", 
            fg="black", 
            bg=COLORS['BACKGROUND']
        )
        self.label_dinero.pack(side="left", padx=10)

        # Cash (capital disponible - riesgo reservado)
        self.label_cash = tk.Label(
            self.parent_frame, 
            text=f"Dinero: ${self.dinero_disponible:,.2f}", 
            fg="black", 
            bg=COLORS['BACKGROUND']
        )
        self.label_cash.pack(side="left", padx=10)

        self.label_beneficios = tk.Label(
            self.parent_frame, 
            text=f"Beneficios: ${self.beneficios:,.2f}", 
            fg="green", 
            bg=COLORS['BACKGROUND']
        )
        self.label_beneficios.pack(side="left", padx=10)

        self.label_perdidas = tk.Label(
            self.parent_frame, 
            text=f"Pérdidas: ${self.perdidas:,.2f}", 
            fg="red", 
            bg=COLORS['BACKGROUND']
        )
        self.label_perdidas.pack(side="left", padx=10)

        # Etiqueta de estado de simulación
        self.label_sim_status = tk.Label(
            self.parent_frame, 
            text="Estado: Inactivo", 
            fg="gray", 
            bg=COLORS['BACKGROUND']
        )
        self.label_sim_status.pack(side="left", padx=12)
        
    def actualizar_labels(self, dinero_ficticio=None, beneficios=None, perdidas=None):
        """DEPRECATED: Usar actualizar_dinero_visible() en su lugar"""
        # Mantener compatibilidad hacia atrás
        if dinero_ficticio is not None:
            self.dinero_disponible = dinero_ficticio
            self.equidad_total = dinero_ficticio  # Fallback temporal
            self.label_dinero.config(text=f"Equidad: ${self.equidad_total:,.2f}")
            self.label_cash.config(text=f"Dinero: ${self.dinero_disponible:,.2f}")
            
        if beneficios is not None:
            self.beneficios = beneficios
            self.label_beneficios.config(text=f"Beneficios: ${self.beneficios:,.2f}")
            
        if perdidas is not None:
            self.perdidas = perdidas
            self.label_perdidas.config(text=f"Pérdidas: ${self.perdidas:,.2f}")
            
    def actualizar_dinero_visible(self, equity, cash):
        """Actualiza dinero y equidad por separado correctamente"""
        self.equidad_total = equity
        self.dinero_disponible = cash
        self.label_dinero.config(text=f"Equidad: {equity:,.2f}$")
        self.label_cash.config(text=f"Dinero: {cash:,.2f}$")
        
    def actualizar_estado_simulacion(self, estado, color="gray"):
        """Actualiza el estado de la simulación"""
        self.label_sim_status.config(text=f"Estado: {estado}", fg=color)
        
    def actualizar_estado_streamer(self, conectado=False):
        """Actualiza el estado de conexión del streamer"""
        if conectado:
            self.label_sim_status.config(text="Estado: Conectado", fg="green")
        else:
            self.label_sim_status.config(text="Estado: Desconectado", fg="red")