"""Login view."""

import customtkinter as ctk

from medicus_privacy.gui.theme import COLORS


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login):
        super().__init__(master, fg_color=COLORS["window"], corner_radius=0)
        self.on_login = on_login
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel = ctk.CTkFrame(
            self,
            width=420,
            height=500,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
        )
        panel.grid(row=0, column=0, padx=24, pady=24)
        panel.grid_propagate(False)
        panel.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkLabel(
            panel,
            text="Medicus-Privacy",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
        )
        brand.grid(row=0, column=0, padx=48, pady=(52, 4), sticky="w")

        subtitle = ctk.CTkLabel(
            panel,
            text="Acceso al sistema clinico",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        subtitle.grid(row=1, column=0, padx=48, pady=(0, 32), sticky="w")

        ctk.CTkLabel(
            panel,
            text="Usuario",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=2, column=0, padx=48, pady=(0, 6), sticky="w")

        self.username_entry = ctk.CTkEntry(
            panel,
            width=324,
            height=42,
            placeholder_text="Ingrese su usuario",
            corner_radius=6,
            border_color=COLORS["border"],
        )
        self.username_entry.grid(row=3, column=0, padx=48, sticky="ew")

        ctk.CTkLabel(
            panel,
            text="Contrasena",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=4, column=0, padx=48, pady=(20, 6), sticky="w")

        self.password_entry = ctk.CTkEntry(
            panel,
            width=324,
            height=42,
            placeholder_text="Ingrese su contrasena",
            show="*",
            corner_radius=6,
            border_color=COLORS["border"],
        )
        self.password_entry.grid(row=5, column=0, padx=48, sticky="ew")

        self.show_password = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            panel,
            text="Mostrar contrasena",
            variable=self.show_password,
            command=self._toggle_password,
            text_color=COLORS["muted"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=4,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=6, column=0, padx=48, pady=(12, 0), sticky="w")

        self.error_label = ctk.CTkLabel(
            panel,
            text="",
            text_color=COLORS["danger"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            wraplength=324,
            justify="left",
        )
        self.error_label.grid(row=7, column=0, padx=48, pady=(12, 0), sticky="w")

        self.login_button = ctk.CTkButton(
            panel,
            text="Ingresar",
            height=42,
            command=self._submit,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.login_button.grid(
            row=8,
            column=0,
            padx=48,
            pady=(18, 48),
            sticky="ew",
        )

        self.username_entry.bind("<Return>", lambda _event: self._submit())
        self.password_entry.bind("<Return>", lambda _event: self._submit())
        self.after(100, self.username_entry.focus_set)

    def _toggle_password(self):
        self.password_entry.configure(show="" if self.show_password.get() else "*")

    def _submit(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            self.set_error("Ingrese usuario y contrasena.")
            return
        self.set_busy(True)
        self.on_login(username, password)

    def set_error(self, message):
        self.error_label.configure(text=message)

    def set_busy(self, busy):
        self.login_button.configure(
            state="disabled" if busy else "normal",
            text="Verificando..." if busy else "Ingresar",
        )
        if not busy:
            self.password_entry.delete(0, "end")
            self.password_entry.focus_set()
