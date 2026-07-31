"""Administrator workspace for user profiles and access state."""

from tkinter import messagebox, ttk

import customtkinter as ctk

from medicus_privacy.gui.theme import COLORS
from medicus_privacy.gui.widgets import labeled_entry
from medicus_privacy.modules.admin import AdminService
from medicus_privacy.modules.catalogs import SPECIALTIES
from medicus_privacy.modules.roles import (
    ESTUDIANTE,
    MEDICO,
    ROLES_PERMITIDOS,
)


class AdminFrame(ctk.CTkFrame):
    def __init__(self, master, session):
        super().__init__(master, fg_color=COLORS["window"], corner_radius=0)
        self.session = session
        self.service = AdminService(session.role)
        self.users = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_toolbar()
        self._build_table()
        self.refresh()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=28, pady=(24, 12), sticky="ew")
        ctk.CTkLabel(
            header,
            text="Usuarios",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Acceso, perfil profesional y estado de cuentas",
            text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(3, 0))

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, padx=28, pady=(0, 12), sticky="ew")
        bar.grid_columnconfigure(4, weight=1)
        ctk.CTkButton(
            bar,
            text="Nuevo usuario",
            width=116,
            command=lambda: UserDialog(self, self._create),
        ).grid(row=0, column=0, padx=(0, 8))
        self.edit_button = ctk.CTkButton(
            bar,
            text="Editar",
            width=86,
            state="disabled",
            command=self._open_edit,
        )
        self.edit_button.grid(row=0, column=1, padx=4)
        self.status_button = ctk.CTkButton(
            bar,
            text="Desactivar",
            width=100,
            state="disabled",
            command=self._toggle_status,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
        )
        self.status_button.grid(row=0, column=2, padx=4)
        self.show_inactive = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            bar,
            text="Incluir inactivos",
            variable=self.show_inactive,
            command=self.refresh,
        ).grid(row=0, column=3, padx=12)
        self.search = ctk.CTkEntry(
            bar,
            width=240,
            placeholder_text="Filtrar usuarios",
        )
        self.search.grid(row=0, column=5, sticky="e")
        self.search.bind("<KeyRelease>", lambda _event: self._render())

    def _build_table(self):
        host = ctk.CTkFrame(
            self,
            fg_color=COLORS["surface"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
        )
        host.grid(row=2, column=0, padx=28, pady=(0, 24), sticky="nsew")
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(0, weight=1)
        columns = ("username", "name", "role", "specialty", "status")
        self.table = ttk.Treeview(
            host,
            columns=columns,
            show="headings",
            style="Medicus.Treeview",
        )
        headings = {
            "username": "Usuario",
            "name": "Nombre",
            "role": "Rol",
            "specialty": "Especialidad",
            "status": "Estado",
        }
        widths = {
            "username": 130,
            "name": 220,
            "role": 120,
            "specialty": 210,
            "status": 90,
        }
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], minwidth=80)
        scrollbar = ttk.Scrollbar(
            host,
            orient="vertical",
            command=self.table.yview,
            style="Medicus.Vertical.TScrollbar",
        )
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.bind("<<TreeviewSelect>>", self._selection_changed)

    def refresh(self):
        self.users = {
            user["username"]: user
            for user in self.service.listar_usuarios(self.show_inactive.get())
        }
        self._render()

    def _render(self):
        query = self.search.get().strip().casefold()
        self.table.delete(*self.table.get_children())
        for user in self.users.values():
            searchable = " ".join(
                str(user.get(key) or "")
                for key in ("username", "nombre_completo", "rol", "especialidad")
            ).casefold()
            if query and query not in searchable:
                continue
            self.table.insert(
                "",
                "end",
                iid=user["username"],
                values=(
                    user["username"],
                    user["nombre_completo"],
                    user["rol"],
                    user["especialidad"] or "-",
                    "Activo" if user["activo"] else "Inactivo",
                ),
            )
        self._selection_changed()

    def selected_user(self):
        selected = self.table.selection()
        return self.users.get(selected[0]) if selected else None

    def _selection_changed(self, _event=None):
        user = self.selected_user()
        state = "normal" if user else "disabled"
        self.edit_button.configure(state=state)
        self.status_button.configure(
            state=state,
            text="Desactivar" if not user or user["activo"] else "Activar",
            fg_color=(
                COLORS["danger"]
                if not user or user["activo"]
                else COLORS["accent"]
            ),
        )

    def _create(self, values):
        success, message = self.service.crear_usuario(
            values["username"],
            values["password"],
            values["role"],
            values["name"],
            values["specialty"],
        )
        self._result(success, message)
        if success:
            self.refresh()
        return success

    def _open_edit(self):
        user = self.selected_user()
        if user:
            UserDialog(self, self._edit, user)

    def _edit(self, values):
        success, message = self.service.actualizar_usuario(
            values["username"],
            values["name"],
            values["role"],
            values["specialty"],
        )
        self._result(success, message)
        if success:
            self.refresh()
        return success

    def _toggle_status(self):
        user = self.selected_user()
        if not user:
            return
        action = "desactivar" if user["activo"] else "activar"
        if not messagebox.askyesno(
            "Confirmar",
            f"¿Desea {action} a '{user['username']}'?",
            parent=self,
        ):
            return
        result = (
            self.service.eliminar_usuario(user["username"])
            if user["activo"]
            else self.service.activar_usuario(user["username"])
        )
        self._result(*result)
        if result[0]:
            self.refresh()

    def _result(self, success, message):
        method = messagebox.showinfo if success else messagebox.showerror
        method(
            "Operacion completada" if success else "No se pudo completar",
            message,
            parent=self,
        )


class UserDialog(ctk.CTkToplevel):
    def __init__(self, master, on_submit, user=None):
        super().__init__(master)
        self.on_submit = on_submit
        self.user = user
        self.title("Editar usuario" if user else "Nuevo usuario")
        self.geometry("500x640")
        self.minsize(460, 520)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text="Editar perfil" if user else "Registrar usuario",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=4, pady=(0, 8), sticky="w")
        self.username = labeled_entry(
            body,
            1,
            "Usuario",
            user["username"] if user else "",
        )
        if user:
            self.username.configure(state="disabled")
        self.name = labeled_entry(
            body,
            3,
            "Nombre completo",
            user["nombre_completo"] if user else "",
        )
        self.password = None
        next_row = 5
        if not user:
            self.password = labeled_entry(
                body,
                next_row,
                "Contrasena temporal",
                show="*",
            )
            next_row += 2
        ctk.CTkLabel(body, text="Rol").grid(
            row=next_row,
            column=0,
            padx=4,
            pady=(10, 4),
            sticky="w",
        )
        self.role = ctk.CTkOptionMenu(
            body,
            values=list(ROLES_PERMITIDOS),
            command=self._role_changed,
        )
        self.role.grid(row=next_row + 1, column=0, padx=4, sticky="ew")
        if user:
            self.role.set(user["rol"])
        ctk.CTkLabel(body, text="Especialidad").grid(
            row=next_row + 2,
            column=0,
            padx=4,
            pady=(10, 4),
            sticky="w",
        )
        self.specialty = ctk.CTkOptionMenu(body, values=list(SPECIALTIES))
        self.specialty.grid(
            row=next_row + 3,
            column=0,
            padx=4,
            sticky="ew",
        )
        if user and user["especialidad"]:
            self.specialty.set(user["especialidad"])
        self.error = ctk.CTkLabel(
            body,
            text="",
            text_color=COLORS["danger"],
            wraplength=410,
        )
        self.error.grid(
            row=next_row + 4,
            column=0,
            padx=4,
            pady=12,
            sticky="w",
        )
        self._role_changed(self.role.get())

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, padx=24, pady=(4, 20), sticky="e")
        ctk.CTkButton(
            footer,
            text="Cancelar",
            width=90,
            command=self.destroy,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            footer,
            text="Guardar",
            width=100,
            command=self._submit,
        ).grid(row=0, column=1)

    def _role_changed(self, role):
        state = "normal" if role in (MEDICO, ESTUDIANTE) else "disabled"
        self.specialty.configure(state=state)

    def _submit(self):
        values = {
            "username": self.user["username"] if self.user else self.username.get(),
            "name": self.name.get(),
            "password": self.password.get() if self.password else None,
            "role": self.role.get(),
            "specialty": self.specialty.get(),
        }
        if self.on_submit(values):
            self.destroy()
        else:
            self.error.configure(text="Revise los datos del perfil.")


NewUserDialog = UserDialog
