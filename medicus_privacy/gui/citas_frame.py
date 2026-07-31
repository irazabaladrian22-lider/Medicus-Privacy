"""Role-aware appointment workspace with guided date and patient controls."""

from datetime import date, timedelta
from tkinter import messagebox, ttk

import customtkinter as ctk

from medicus_privacy.gui.theme import COLORS
from medicus_privacy.gui.widgets import (
    TIME_SLOTS,
    DateSelector,
    labeled_entry,
)
from medicus_privacy.modules.catalogs import SEX_OPTIONS, SPECIALTIES
from medicus_privacy.modules.citas import CitasService
from medicus_privacy.modules.directory import DirectoryService
from medicus_privacy.modules.patients import PatientService
from medicus_privacy.modules.roles import ADMIN, ESTUDIANTE, MEDICO, RECEPCIONISTA


class CitasFrame(ctk.CTkFrame):
    def __init__(self, master, session):
        super().__init__(master, fg_color=COLORS["window"], corner_radius=0)
        self.session = session
        self.service = CitasService(session.username, session.role)
        self.appointments = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build()
        self.refresh()

    def _build(self):
        title = "Citas asignadas" if self.session.role in (MEDICO, ESTUDIANTE) else "Citas"
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=28, pady=(24, 12), sticky="ew")
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Agenda hospitalaria por paciente y especialidad",
            text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(3, 0))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, padx=28, pady=(0, 12), sticky="ew")
        bar.grid_columnconfigure(3, weight=1)
        if self.session.role in (ADMIN, RECEPCIONISTA, MEDICO):
            ctk.CTkButton(
                bar,
                text="Nueva cita",
                command=self.open_new,
            ).grid(row=0, column=0, padx=(0, 8))
            self.cancel_button = ctk.CTkButton(
                bar,
                text="Cancelar cita",
                state="disabled",
                command=self.cancel,
                fg_color=COLORS["danger"],
                hover_color=COLORS["danger_hover"],
            )
            self.cancel_button.grid(row=0, column=1, padx=(0, 8))
        else:
            self.cancel_button = None
        ctk.CTkButton(
            bar,
            text="Refrescar",
            width=90,
            command=self.refresh,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        ).grid(row=0, column=2)
        self.search = ctk.CTkEntry(
            bar,
            width=270,
            placeholder_text="Paciente, cedula o especialidad",
        )
        self.search.grid(row=0, column=4, sticky="e")
        self.search.bind("<KeyRelease>", lambda _event: self._render())

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
        columns = (
            "id",
            "date",
            "time",
            "patient",
            "cedula",
            "specialty",
            "doctor",
            "student",
            "status",
        )
        self.table = ttk.Treeview(
            host,
            columns=columns,
            show="headings",
            style="Medicus.Treeview",
        )
        headings = {
            "id": "ID",
            "date": "Fecha",
            "time": "Hora",
            "patient": "Paciente",
            "cedula": "Cedula",
            "specialty": "Especialidad",
            "doctor": "Medico",
            "student": "Estudiante",
            "status": "Estado",
        }
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=110, minwidth=70)
        self.table.column("id", width=50)
        self.table.column("patient", width=190)
        self.table.column("specialty", width=180)
        scrollbar = ttk.Scrollbar(
            host,
            command=self.table.yview,
            style="Medicus.Vertical.TScrollbar",
        )
        horizontal = ttk.Scrollbar(
            host,
            orient="horizontal",
            command=self.table.xview,
        )
        self.table.configure(
            yscrollcommand=scrollbar.set,
            xscrollcommand=horizontal.set,
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.bind("<<TreeviewSelect>>", self._selection_changed)

    def refresh(self):
        self.appointments = {
            str(item["id"]): item for item in self.service.obtener_citas()
        }
        self._render()

    def _render(self):
        query = self.search.get().strip().casefold()
        self.table.delete(*self.table.get_children())
        for appointment_id, item in self.appointments.items():
            searchable = " ".join(str(value) for value in item.values()).casefold()
            if query and query not in searchable:
                continue
            self.table.insert(
                "",
                "end",
                iid=appointment_id,
                values=(
                    item["id"],
                    item["fecha"],
                    item["hora"],
                    item["paciente"],
                    item["cedula"],
                    item["especialidad"],
                    item["medico"],
                    item["estudiante"] or "-",
                    item["estado"],
                ),
            )
        self._selection_changed()

    def selected(self):
        selected = self.table.selection()
        return self.appointments.get(selected[0]) if selected else None

    def _selection_changed(self, _event=None):
        if self.cancel_button is not None:
            item = self.selected()
            self.cancel_button.configure(
                state=(
                    "normal"
                    if item and item["estado"] == "Programada"
                    else "disabled"
                )
            )

    def open_new(self):
        NewAppointmentDialog(self, self.session, self._schedule)

    def _schedule(
        self,
        doctor,
        patient_id,
        selected_date,
        selected_time,
        specialty,
        student,
    ):
        success, message = self.service.agendar_cita(
            doctor,
            patient_id,
            selected_date,
            selected_time,
            specialty,
            student,
        )
        self._result(success, message)
        if success:
            self.refresh()
        return success

    def cancel(self):
        item = self.selected()
        if not item:
            return
        if not messagebox.askyesno(
            "Cancelar cita",
            f"¿Desea cancelar la cita {item['id']} de {item['paciente']}?",
            parent=self,
        ):
            return
        success, message = self.service.cancelar_cita(item["id"])
        self._result(success, message)
        if success:
            self.refresh()

    def _result(self, success, message):
        method = messagebox.showinfo if success else messagebox.showerror
        method(
            "Operacion completada" if success else "No se pudo completar",
            message,
            parent=self,
        )


class NewAppointmentDialog(ctk.CTkToplevel):
    def __init__(self, master, session, on_submit, preset_patient=None):
        super().__init__(master)
        self.session = session
        self.on_submit = on_submit
        self.patient_service = PatientService(session.username, session.role)
        self.directory = DirectoryService(session.role)
        self.patient = preset_patient
        self.doctor_map = {}
        self.student_map = {"Sin estudiante": None}
        self.title("Agendar cita")
        self.geometry("650x760")
        self.minsize(560, 600)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text="Nueva cita",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=4, pady=(0, 8), sticky="w")

        ctk.CTkLabel(body, text="Especialidad").grid(
            row=1, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.specialty = ctk.CTkOptionMenu(
            body,
            values=list(SPECIALTIES),
            command=self._specialty_changed,
        )
        self.specialty.grid(row=2, column=0, padx=4, sticky="ew")

        ctk.CTkLabel(body, text="Medico").grid(
            row=3, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.doctor = ctk.CTkComboBox(body, values=["Sin medicos"], state="readonly")
        self.doctor.grid(row=4, column=0, padx=4, sticky="ew")

        ctk.CTkLabel(body, text="Estudiante asignado (opcional)").grid(
            row=5, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.student = ctk.CTkComboBox(
            body,
            values=["Sin estudiante"],
            state="readonly",
        )
        self.student.grid(row=6, column=0, padx=4, sticky="ew")
        if session.role == MEDICO:
            self.student.configure(state="disabled")

        patient_bar = ctk.CTkFrame(body, fg_color="transparent")
        patient_bar.grid(row=7, column=0, padx=4, pady=(14, 0), sticky="ew")
        patient_bar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(patient_bar, text="Cedula del paciente").grid(
            row=0, column=0, columnspan=2, pady=(0, 4), sticky="w"
        )
        self.cedula = ctk.CTkEntry(patient_bar, height=38)
        self.cedula.grid(row=1, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(
            patient_bar,
            text="Buscar",
            width=86,
            command=self._find_patient,
        ).grid(row=1, column=1)

        self.patient_status = ctk.CTkLabel(
            body,
            text="Si no existe, complete los datos siguientes.",
            text_color=COLORS["muted"],
        )
        self.patient_status.grid(row=8, column=0, padx=4, pady=(6, 0), sticky="w")
        self.names = labeled_entry(body, 9, "Nombres")
        self.surnames = labeled_entry(body, 11, "Apellidos")
        ctk.CTkLabel(body, text="Fecha de nacimiento").grid(
            row=13, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.birth = DateSelector(
            body,
            value=date(2000, 1, 1),
            max_date=date.today() - timedelta(days=1),
        )
        self.birth.grid(row=14, column=0, padx=4, sticky="ew")
        ctk.CTkLabel(body, text="Sexo").grid(
            row=15, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.sex = ctk.CTkOptionMenu(body, values=list(SEX_OPTIONS))
        self.sex.grid(row=16, column=0, padx=4, sticky="ew")
        ctk.CTkLabel(body, text="Fecha de la cita").grid(
            row=17, column=0, padx=4, pady=(14, 4), sticky="w"
        )
        self.appointment_date = DateSelector(
            body,
            value=date.today() + timedelta(days=1),
            min_date=date.today(),
        )
        self.appointment_date.grid(row=18, column=0, padx=4, sticky="ew")
        ctk.CTkLabel(body, text="Hora").grid(
            row=19, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.time = ctk.CTkOptionMenu(body, values=list(TIME_SLOTS))
        self.time.set("09:00")
        self.time.grid(row=20, column=0, padx=4, sticky="ew")
        self.error = ctk.CTkLabel(
            body,
            text="",
            text_color=COLORS["danger"],
            wraplength=520,
        )
        self.error.grid(row=21, column=0, padx=4, pady=14, sticky="w")

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
            text="Agendar",
            width=100,
            command=self._submit,
        ).grid(row=0, column=1)
        if session.role == MEDICO:
            own_profile = next(
                (
                    item
                    for item in self.directory.listar_medicos()
                    if item["username"] == session.username
                ),
                None,
            )
            if own_profile:
                self.specialty.set(own_profile["especialidad"])
                self.specialty.configure(state="disabled")
        self._specialty_changed(self.specialty.get())
        if preset_patient:
            self._populate_patient(preset_patient)

    @staticmethod
    def _display(user):
        return f"{user['nombre_completo']} ({user['username']})"

    def _specialty_changed(self, specialty):
        doctors = self.directory.listar_medicos(specialty)
        if self.session.role == MEDICO:
            doctors = [
                item for item in doctors if item["username"] == self.session.username
            ]
        self.doctor_map = {self._display(item): item["username"] for item in doctors}
        doctor_values = list(self.doctor_map) or ["Sin medicos disponibles"]
        self.doctor.configure(values=doctor_values)
        self.doctor.set(doctor_values[0])

        students = self.directory.listar_estudiantes(specialty)
        self.student_map = {"Sin estudiante": None}
        self.student_map.update(
            {self._display(item): item["username"] for item in students}
        )
        self.student.configure(values=list(self.student_map))
        self.student.set("Sin estudiante")

    def _find_patient(self):
        patient = self.patient_service.buscar_por_cedula(self.cedula.get())
        if not patient:
            self.patient = None
            self.patient_status.configure(
                text="Paciente nuevo: complete nombres, apellidos, nacimiento y sexo.",
                text_color=COLORS["warning"],
            )
            return
        self._populate_patient(patient)

    def _populate_patient(self, patient):
        self.patient = patient
        for entry, value in (
            (self.cedula, patient["cedula"]),
            (self.names, patient["nombres"]),
            (self.surnames, patient["apellidos"]),
        ):
            entry.delete(0, "end")
            entry.insert(0, value)
        if patient.get("fecha_nacimiento"):
            self.birth.set(patient["fecha_nacimiento"])
        self.sex.set(patient["sexo"])
        self.patient_status.configure(
            text=f"Paciente encontrado: {patient['nombre_completo']}",
            text_color=COLORS["accent"],
        )

    def _resolve_patient(self):
        found = self.patient_service.buscar_por_cedula(self.cedula.get())
        if found and found["datos_completos"]:
            return found["id"]
        values = {
            "cedula": self.cedula.get(),
            "nombres": self.names.get(),
            "apellidos": self.surnames.get(),
            "fecha_nacimiento": self.birth.get(),
            "sexo": self.sex.get(),
        }
        if found:
            success, message = self.patient_service.actualizar_paciente(
                found["id"],
                **values,
            )
            if not success:
                self.error.configure(text=message)
                return None
            return found["id"]
        success, message, patient_id = self.patient_service.registrar_paciente(
            **values
        )
        if not success:
            self.error.configure(text=message)
            return None
        return patient_id

    def _submit(self):
        doctor = self.doctor_map.get(self.doctor.get())
        if not doctor:
            self.error.configure(text="No hay un medico valido para la especialidad.")
            return
        patient_id = self._resolve_patient()
        if not patient_id:
            return
        student = self.student_map.get(self.student.get())
        success = self.on_submit(
            doctor,
            patient_id,
            self.appointment_date.get(),
            self.time.get(),
            self.specialty.get(),
            student,
        )
        if success:
            self.destroy()


DecryptDialog = None
