# app/gui/components/status_bar.py
import tkinter as tk
from ..utils.constants import COLORS

class StatusBar:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # Variables de estado financiero
        self.dinero_ficticio = 0
        self.beneficios = 0
        self.perdidas = 0
        
        self._create_status_labels()
        
    def _create_status_labels(self):
        """Crea las etiquetas de estado financiero"""
        # Equity (dinero visible: capital - riesgo reservado + PnL flotante)
        self.label_dinero = tk.Label(
            self.parent_frame, 
            text=f"Equidad: ${self.dinero_ficticio:,.2f}", 
            fg="black", 
            bg=COLORS['BACKGROUND']
        )
        self.label_dinero.pack(side="left", padx=10)

        # Cash (capital - riesgo reservado)
        self.label_cash = tk.Label(
            self.parent_frame, 
            text=f"Dinero: ${self.dinero_ficticio:,.2f}", 
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

        # Etiqueta de tipo de mercado
        self.label_market_type = tk.Label(
            self.parent_frame, 
            text="Tipo de mercado: Indeterminado", 
            fg="black", 
            bg=COLORS['BACKGROUND']
        )
        self.label_market_type.pack(side="left", padx=12)
        
        # Etiqueta de estado de conexión del streamer
        self.label_streamer_status = tk.Label(
            self.parent_frame,
            text="Streamer: Desconectado",
            fg="red",
            bg=COLORS['BACKGROUND']
        )
        self.label_streamer_status.pack(side="left", padx=12)
        
    def actualizar_labels(self, dinero_ficticio=None, beneficios=None, perdidas=None):
        """Actualiza las etiquetas de estado financiero"""
        if dinero_ficticio is not None:
            self.dinero_ficticio = dinero_ficticio
            self.label_dinero.config(text=f"Equidad: ${self.dinero_ficticio:,.2f}")
            self.label_cash.config(text=f"Dinero: ${self.dinero_ficticio:,.2f}")
            
        if beneficios is not None:
            self.beneficios = beneficios
            self.label_beneficios.config(text=f"Beneficios: ${self.beneficios:,.2f}")
            
        if perdidas is not None:
            self.perdidas = perdidas
            self.label_perdidas.config(text=f"Pérdidas: ${self.perdidas:,.2f}")
            
    def actualizar_dinero_visible(self, equity, cash):
        """Actualiza el dinero visible en tiempo real"""
        self.dinero_ficticio = equity
        self.label_dinero.config(text=f"Equidad: {equity:,.2f}$")
        self.label_cash.config(text=f"Dinero: {cash:,.2f}$")
        
    def actualizar_estado_simulacion(self, estado, color="gray"):
        """Actualiza el estado de la simulación"""
        self.label_sim_status.config(text=f"Estado: {estado}", fg=color)
        
    def actualizar_estado_streamer(self, conectado=False):
        """Actualiza el estado de conexión del streamer"""
        if conectado:
            self.label_streamer_status.config(text="Streamer: Conectado", fg="green")
        else:
            self.label_streamer_status.config(text="Streamer: Desconectado", fg="red")
            
    def actualizar_tipo_mercado(self, tipo_mercado="Indeterminado"):
        """Actualiza el tipo de mercado detectado"""
        self.label_market_type.config(text=f"Tipo de mercado: {tipo_mercado}", fg="black")