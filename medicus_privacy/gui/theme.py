"""Visual tokens and ttk configuration shared by the desktop UI."""

from tkinter import ttk

import customtkinter as ctk


COLORS = {
    "window": ("#F3F5F7", "#111418"),
    "surface": ("#FFFFFF", "#1A1F24"),
    "surface_alt": ("#E8ECEF", "#242A30"),
    "border": ("#CDD4D9", "#353D44"),
    "text": ("#152026", "#F1F4F5"),
    "muted": ("#5F6B73", "#A9B2B8"),
    "accent": ("#176B5B", "#35A98C"),
    "accent_hover": ("#125548", "#2C8E76"),
    "danger": ("#B23B3B", "#D95C5C"),
    "danger_hover": ("#922F2F", "#BB4848"),
    "warning": ("#9A640C", "#D7A43B"),
}


def configure_treeview_style(root):
    dark = ctk.get_appearance_mode() == "Dark"
    background = "#1A1F24" if dark else "#FFFFFF"
    foreground = "#F1F4F5" if dark else "#152026"
    heading = "#242A30" if dark else "#E8ECEF"
    heading_active = "#30383F" if dark else "#DCE2E6"
    border = "#353D44" if dark else "#CDD4D9"
    muted = "#A9B2B8" if dark else "#5F6B73"

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Medicus.Treeview",
        background=background,
        foreground=foreground,
        fieldbackground=background,
        bordercolor=border,
        borderwidth=0,
        rowheight=34,
        font=("Segoe UI", 10),
    )
    style.map(
        "Medicus.Treeview",
        background=[("selected", "#176B5B")],
        foreground=[("selected", "#FFFFFF")],
    )
    style.configure(
        "Medicus.Treeview.Heading",
        background=heading,
        foreground=foreground,
        bordercolor=border,
        borderwidth=1,
        relief="flat",
        font=("Segoe UI Semibold", 10),
        padding=(8, 8),
    )
    style.map(
        "Medicus.Treeview.Heading",
        background=[("active", heading_active)],
    )
    style.configure(
        "Medicus.Vertical.TScrollbar",
        background=border,
        troughcolor=background,
        bordercolor=background,
        arrowcolor=muted,
    )
