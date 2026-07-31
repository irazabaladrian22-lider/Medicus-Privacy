"""Administrative patient registry without clinical content."""

from datetime import date, timedelta
from tkinter import messagebox, ttk

import customtkinter as ctk

from medicus_privacy.gui.theme import COLORS
from medicus_privacy.gui.widgets import DateSelector, labeled_entry
from medicus_privacy.modules.catalogs import SEX_OPTIONS
from medicus_privacy.modules.patients import PatientService


class PatientsFrame(ctk.CTkFrame):
    def __init__(self, master, session):
        super().__init__(master, fg_color=COLORS["window"], corner_radius=0)
        self.session = session
        self.service = PatientService(session.username, session.role)
        self.patients = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build()
        self.refresh()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=28, pady=(24, 12), sticky="ew")
        ctk.CTkLabel(
            header,
            text="Pacientes",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Datos administrativos; el contenido clinico no es visible aqui",
            text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(3, 0))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, padx=28, pady=(0, 12), sticky="ew")
        bar.grid_columnconfigure(2, weight=1)
        ctk.CTkButton(
            bar,
            text="Nuevo paciente",
            command=lambda: PatientDialog(self, self._create),
        ).grid(row=0, column=0, padx=(0, 8))
        self.edit_button = ctk.CTkButton(
            bar,
            text="Editar",
            width=90,
            state="disabled",
            command=self._edit,
        )
        self.edit_button.grid(row=0, column=1)
        self.search = ctk.CTkEntry(
            bar,
            width=260,
            placeholder_text="Nombre o cedula",
        )
        self.search.grid(row=0, column=3, sticky="e")
        self.search.bind("<KeyRelease>", lambda _event: self.refresh())

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
        columns = ("cedula", "name", "age", "sex", "nationality", "status")
        self.table = ttk.Treeview(
            host,
            columns=columns,
            show="headings",
            style="Medicus.Treeview",
        )
        labels = {
            "cedula": "Cedula",
            "name": "Paciente",
            "age": "Edad",
            "sex": "Sexo",
            "nationality": "Nacionalidad",
            "status": "Datos",
        }
        for column in columns:
            self.table.heading(column, text=labels[column])
            self.table.column(column, width=140)
        self.table.column("name", width=240)
        scrollbar = ttk.Scrollbar(
            host,
            command=self.table.yview,
            style="Medicus.Vertical.TScrollbar",
        )
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.bind("<<TreeviewSelect>>", self._selected)
        self.table.bind("<Double-1>", lambda _event: self._edit())

    def refresh(self):
        patients = self.service.listar_pacientes(self.search.get())
        self.patients = {str(item["id"]): item for item in patients}
        self.table.delete(*self.table.get_children())
        for patient_id, patient in self.patients.items():
            self.table.insert(
                "",
                "end",
                iid=patient_id,
                values=(
                    patient["cedula"],
                    patient["nombre_completo"],
                    patient["edad"] if patient["edad"] is not None else "-",
                    patient["sexo"],
                    patient["nacionalidad"] or "-",
                    "Completo" if patient["datos_completos"] else "Por completar",
                ),
            )
        self._selected()

    def _selected(self, _event=None):
        self.edit_button.configure(
            state="normal" if self.table.selection() else "disabled"
        )

    def selected_patient(self):
        selected = self.table.selection()
        return self.patients.get(selected[0]) if selected else None

    def _create(self, values):
        success, message, _patient_id = self.service.registrar_paciente(**values)
        self._result(success, message)
        if success:
            self.refresh()
        return success

    def _edit(self):
        patient = self.selected_patient()
        if patient:
            PatientDialog(self, self._update, patient)

    def _update(self, values):
        patient_id = values.pop("patient_id")
        success, message = self.service.actualizar_paciente(
            patient_id,
            **values,
        )
        self._result(success, message)
        if success:
            self.refresh()
        return success

    def _result(self, success, message):
        method = messagebox.showinfo if success else messagebox.showerror
        method(
            "Operacion completada" if success else "No se pudo completar",
            message,
            parent=self,
        )


class PatientDialog(ctk.CTkToplevel):
    def __init__(self, master, on_submit, patient=None):
        super().__init__(master)
        self.patient = patient
        self.on_submit = on_submit
        self.title("Editar paciente" if patient else "Nuevo paciente")
        self.geometry("560x700")
        self.minsize(500, 560)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text="Datos del paciente",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=4, pady=(0, 8), sticky="w")
        self.cedula = labeled_entry(
            body, 1, "Cedula", patient["cedula"] if patient else ""
        )
        self.names = labeled_entry(
            body, 3, "Nombres", patient["nombres"] if patient else ""
        )
        self.surnames = labeled_entry(
            body, 5, "Apellidos", patient["apellidos"] if patient else ""
        )
        ctk.CTkLabel(body, text="Fecha de nacimiento").grid(
            row=7,
            column=0,
            padx=4,
            pady=(10, 4),
            sticky="w",
        )
        birth = (
            patient["fecha_nacimiento"]
            if patient and patient["fecha_nacimiento"]
            else date(2000, 1, 1)
        )
        self.birth = DateSelector(
            body,
            value=birth,
            max_date=date.today() - timedelta(days=1),
        )
        self.birth.grid(row=8, column=0, padx=4, sticky="ew")
        ctk.CTkLabel(body, text="Sexo").grid(
            row=9,
            column=0,
            padx=4,
            pady=(10, 4),
            sticky="w",
        )
        self.sex = ctk.CTkOptionMenu(body, values=list(SEX_OPTIONS))
        self.sex.grid(row=10, column=0, padx=4, sticky="ew")
        if patient:
            self.sex.set(patient["sexo"])
        self.nationality = labeled_entry(
            body,
            11,
            "Nacionalidad",
            patient["nacionalidad"] if patient else "",
        )
        self.address = labeled_entry(
            body,
            13,
            "Direccion",
            patient["direccion"] if patient else "",
        )
        self.error = ctk.CTkLabel(
            body,
            text="",
            text_color=COLORS["danger"],
            wraplength=450,
        )
        self.error.grid(row=15, column=0, padx=4, pady=12, sticky="w")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, padx=24, pady=(4, 20), sticky="e")
        ctk.CTkButton(
            footer,
            text="Cerrar",
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

    def _submit(self):
        values = {
            "cedula": self.cedula.get(),
            "nombres": self.names.get(),
            "apellidos": self.surnames.get(),
            "fecha_nacimiento": self.birth.get(),
            "sexo": self.sex.get(),
            "nacionalidad": self.nationality.get(),
            "direccion": self.address.get(),
        }
        if self.patient:
            values["patient_id"] = self.patient["id"]
        if self.on_submit(values):
            self.destroy()
        else:
            self.error.configure(text="Revise los datos obligatorios.")
