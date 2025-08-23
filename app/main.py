# app/main.py

import tkinter as tk
from app import Window, ForexPairs

def main():
    """
    Función principal para iniciar la aplicación.
    """
    root = tk.Tk()
    root.title("Forex Trader Bot")
    root.geometry("1500x750")  # tamaño amplio para que quepa el gráfico
    
    # Crear instancia de la ventana principal
    app = Window(root=root, monedas=ForexPairs.CURRENCIES)
    
    # Ejecutar loop principal de Tkinter
    app.run()

# Esto permite ejecutar con python app/main.py
if __name__ == "__main__":
    main()