# app/window.py

import tkinter as tk
from .gui_main import GUIPrincipal 

class Window:
    def __init__(self, root):
        self.root = root
        self.gui = GUIPrincipal(root)

    def run(self):
        self.gui.run()