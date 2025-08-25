# app/main.py

import tkinter as tk
from .window import Window

def main():
    """
    Función principal para iniciar la aplicación.
    """
    root = tk.Tk()
    root.title("CSV Data Viewer")
    root.geometry("1500x750")
    
    # Crear instancia de la ventana principal
    app = Window(root=root)
    
    # Ejecutar loop principal de Tkinter
    app.run()

if __name__ == "__main__":
    main()