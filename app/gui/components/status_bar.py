# app/gui/components/status_bar.py
import tkinter as tk
from ..utils.constants import COLORS

class StatusBar:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # Variables de estado financiero CORREGIDAS
        self.capital_inicial = 0     # Capital inicial del usuario
        self.equidad_total = 0       # Capital inicial + ganancia neta + P&L flotante
        self.beneficios_totales = 0  # Total de operaciones ganadoras
        self.perdidas_totales = 0    # Total de operaciones perdedoras
        
        self._create_status_labels()
        
    def _create_status_labels(self):
        """Crea las etiquetas de estado financiero con lógica corregida"""
        # Capital inicial
        self.label_capital = tk.Label(
            self.parent_frame, 
            text=f"Capital inicial: ${self.capital_inicial:,.2f}", 
            fg="blue", 
            bg=COLORS['BACKGROUND']
        )
        self.label_capital.pack(side="left", padx=10)

        # Equidad total (capital + ganancia neta + P&L flotante)
        self.label_dinero = tk.Label(
            self.parent_frame, 
            text=f"Balance total: ${self.equidad_total:,.2f}", 
            fg="black", 
            bg=COLORS['BACKGROUND']
        )
        self.label_dinero.pack(side="left", padx=10)

        # Beneficios totales de operaciones ganadoras
        self.label_beneficios = tk.Label(
            self.parent_frame, 
            text=f"Beneficios: ${self.beneficios_totales:,.2f}", 
            fg="green", 
            bg=COLORS['BACKGROUND']
        )
        self.label_beneficios.pack(side="left", padx=10)

        # Pérdidas totales de operaciones perdedoras
        self.label_perdidas = tk.Label(
            self.parent_frame, 
            text=f"Pérdidas: ${self.perdidas_totales:,.2f}", 
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
        """DEPRECATED: Usar actualizar_valores_financieros() en su lugar"""
        # Mantener compatibilidad hacia atrás
        if dinero_ficticio is not None:
            # Si no hay capital inicial establecido, usar dinero_ficticio como base
            if self.capital_inicial == 0:
                self.capital_inicial = dinero_ficticio
                self.label_capital.config(text=f"Capital inicial: ${self.capital_inicial:,.2f}")
            
            self.equidad_total = dinero_ficticio
            self.label_dinero.config(text=f"Equidad: ${self.equidad_total:,.2f}")
            
        if beneficios is not None:
            self.beneficios_totales = beneficios
            self.label_beneficios.config(text=f"Beneficios: ${self.beneficios_totales:,.2f}")
            
        if perdidas is not None:
            self.perdidas_totales = perdidas
            self.label_perdidas.config(text=f"Pérdidas: ${self.perdidas_totales:,.2f}")
            
    def actualizar_dinero_visible(self, equity, cash):
        """DEPRECATED: Usar actualizar_valores_financieros() en su lugar"""
        self.equidad_total = equity
        # Si no hay capital inicial, usar cash como referencia
        if self.capital_inicial == 0:
            self.capital_inicial = cash
            self.label_capital.config(text=f"Capital inicial: ${self.capital_inicial:,.2f}")
        
        self.label_dinero.config(text=f"Equidad: ${equity:,.2f}")
        
    def actualizar_valores_financieros(self, capital_inicial, equidad_actual, beneficios_totales, perdidas_totales):
        """Método principal para actualizar todos los valores financieros de forma coherente"""
        self.capital_inicial = capital_inicial
        self.equidad_total = equidad_actual
        self.beneficios_totales = beneficios_totales
        self.perdidas_totales = perdidas_totales
        
        # Actualizar todos los labels
        self.label_capital.config(text=f"Capital inicial: ${self.capital_inicial:,.2f}")
        self.label_dinero.config(text=f"Equidad: ${self.equidad_total:,.2f}")
        self.label_beneficios.config(text=f"Beneficios: ${self.beneficios_totales:,.2f}")
        self.label_perdidas.config(text=f"Pérdidas: ${self.perdidas_totales:,.2f}")
        
    def actualizar_estado_simulacion(self, estado, color="gray"):
        """Actualiza el estado de la simulación"""
        self.label_sim_status.config(text=f"Estado: {estado}", fg=color)
        
    def actualizar_estado_streamer(self, conectado=False):
        """Actualiza el estado de conexión del streamer"""
        if conectado:
            self.label_sim_status.config(text="Estado: Conectado", fg="green")
        else:
            self.label_sim_status.config(text="Estado: Desconectado", fg="red")