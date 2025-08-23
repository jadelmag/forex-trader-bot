import tkinter as tk
from app.window import Window
from app.forex_pairs import ForexPairs

def main():
    root = tk.Tk()
    root.title("Forex Trader Bot")
    root.geometry("1500x750")  # tamaño amplio para gráficos
    
    # Inicializa la ventana principal con las monedas de Forex
    app = Window(root=root, monedas=ForexPairs.CURRENCIES)
    
    # Ejecuta la GUI
    app.run()

if __name__ == "__main__":
    main()