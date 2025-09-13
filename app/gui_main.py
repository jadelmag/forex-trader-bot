# app/gui_main.py

import sys
import tkinter as tk
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Importar la clase principal refactorizada
from app.gui.main_window import GUIPrincipal

def main():
    """Función principal de la aplicación"""
    try:
        # Crear la ventana principal
        root = tk.Tk()
        
        # Crear la aplicación usando la estructura modular
        app = GUIPrincipal(root)
        
        # Configurar el protocolo de cierre
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        # Iniciar el loop principal
        app.run()
        
    except Exception as e:
        print(f"Error iniciando la aplicación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
