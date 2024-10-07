#!/usr/bin/env python

import sys
import textwrap
import tkinter as tk
from tkinter import ttk


def main():
    input_args = sys.argv[1:]
    label_text = textwrap.dedent(f"""
    This is a sample message to demonstrate a simple GUI application.

    Here are the arguments you supplied:

        {input_args}
    """)

    root = tk.Tk()
    frm = ttk.Frame(root, padding=10)
    frm.master.title("Qcrbox Quality (version: x.y.z)")
    frm.master.minsize(400, 200)
    frm.grid()
    ttk.Label(frm, text=label_text).grid(column=0, row=0)
    ttk.Button(frm, text="Quit", command=root.destroy).grid(column=0, row=1)
    root.mainloop()


if __name__ == "__main__":
    main()
