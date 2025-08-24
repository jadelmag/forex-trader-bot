# app/window.py

import tkinter as tk
from .gui_main import GUIPrincipal
from .forex_pairs import ForexPairs

class Window:
    def __init__(self, root, monedas=None):
        self.root = root
        self.monedas = monedas or ForexPairs.CURRENCIES
        # Instanciamos GUIPrincipal dentro de Window
        self.gui = GUIPrincipal(root)

    def run(self):
        self.gui.run()
