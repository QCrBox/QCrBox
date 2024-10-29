#!/usr/bin/env python

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk


def add_labels(frame, input_args):
    try:
        input_filepath = Path(input_args[0])
        input_filename = input_filepath.name
        ttk.Label(frame, text=f"Input file specified: {input_filename!r}\n", justify=tk.LEFT).pack(fill=tk.X)
        if not input_filepath.exists():
            ttk.Label(frame, text=f"Error: input file {input_filename!r} does not exist", justify=tk.LEFT).pack(
                fill=tk.X
            )
    except IndexError:
        ttk.Label(frame, text="No input file specified.").pack()


def main():
    root = tk.Tk()
    root.title("Dummy GUI Application")
    root.minsize(400, 0)
    frame = ttk.Frame(root, padding=10)
    frame.grid()

    input_args = sys.argv[1:]
    add_labels(frame, input_args)

    ttk.Button(frame, text="Quit", command=root.destroy).pack(pady=(20, 10))

    root.mainloop()


if __name__ == "__main__":
    main()
