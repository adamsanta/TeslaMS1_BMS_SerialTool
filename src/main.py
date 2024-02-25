import tkinter as tk

from gui import (
    BMSMonitorApp,
)

if __name__ == "__main__":
    root = tk.Tk()
    app = BMSMonitorApp(root)
    root.mainloop()