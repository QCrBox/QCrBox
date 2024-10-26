#!/usr/bin/env python

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk


def main():
    root = tk.Tk()
    root.title("Dummy GUI Application")
    root.minsize(400, 200)
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    try:
        input_filepath = Path(sys.argv[1])
        input_filename = input_filepath.name
        ttk.Label(frm, text=f"Input file specified: {input_filename!r}\n", justify=tk.LEFT).pack(fill=tk.X)
        if not input_filepath.exists():
            ttk.Label(frm, text=f"Error: input file {input_filename!r} does not exist", justify=tk.LEFT).pack(fill=tk.X)
    except IndexError:
        ttk.Label(frm, text="No input file specified.").pack()

    ttk.Label(frm, text="").pack()
    ttk.Button(frm, text="Quit", command=root.destroy).pack()
    root.mainloop()


if __name__ == "__main__":
    main()
