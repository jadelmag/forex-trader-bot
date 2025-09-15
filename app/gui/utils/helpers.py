# app/gui/utils/helpers.py
import tkinter as tk
from tkinter import ttk
import os
from pathlib import Path

def setup_styles():
    """Configura los estilos de la aplicación"""
    style = ttk.Style()
    style.configure('TButton', padding=2, font=('Segoe UI', 9))
    style.configure('Small.TButton', padding=1, font=('Segoe UI', 8))
    
    # Estilo exclusivo para el scrollbar de logs
    style.configure(
        "Logs.Vertical.TScrollbar",
        troughcolor="#EFEFEF",
        background="#B5B5B5",
        bordercolor="#EFEFEF",
        lightcolor="#EFEFEF",
        darkcolor="#EFEFEF",
        arrowcolor="#7A7A7A",
    )
    style.map(
        "Logs.Vertical.TScrollbar",
        background=[("active", "#A0A0A0"), ("pressed", "#8C8C8C")],
    )

def load_icon(root):
    """Carga el icono de la aplicación"""
    try:
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'icon.png')
        if os.path.exists(icon_path):
            icon = tk.PhotoImage(file=icon_path)
            root.iconphoto(False, icon)
    except Exception as e:
        print(f"Error al cargar el icono: {e}")

def format_currency(amount):
    """Formatea una cantidad como moneda"""
    return f"${amount:,.2f}"

def safe_float_conversion(value, default=0.0):
    """Convierte un valor a float de forma segura"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def validate_positive_number(value):
    """Valida que un valor sea un número positivo"""
    try:
        num = float(value)
        return num > 0
    except (ValueError, TypeError):
        return False