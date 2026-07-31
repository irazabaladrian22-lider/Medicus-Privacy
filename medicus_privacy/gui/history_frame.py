"""Clinical history workspace for doctors and assigned trainees."""

from tkinter import messagebox, ttk

import customtkinter as ctk

from medicus_privacy.gui.theme import COLORS
from medicus_privacy.gui.widgets import labeled_entry
from medicus_privacy.modules.citas import CitasService
from medicus_privacy.modules.clinical import ClinicalHistoryService
from medicus_privacy.modules.roles import MEDICO


class HistoryFrame(ctk.CTkFrame):
    def __init__(self, master, session):
        super().__init__(master, fg_color=COLORS["window"], corner_radius=0)
        self.session = session
        self.service = ClinicalHistoryService(session.username, session.role)
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
            text="Historias clinicas",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        subtitle = (
            "Pacientes atendidos; consulta de solo lectura"
            if self.session.role != MEDICO
            else "Evoluciones cifradas y continuidad del tratamiento"
        )
        ctk.CTkLabel(
            header,
            text=subtitle,
            text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(3, 0))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, padx=28, pady=(0, 12), sticky="ew")
        bar.grid_columnconfigure(2, weight=1)
        self.open_button = ctk.CTkButton(
            bar,
            text="Abrir historia",
            state="disabled",
            command=self.open_history,
        )
        self.open_button.grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            bar,
            text="Refrescar",
            width=90,
            command=self.refresh,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        ).grid(row=0, column=1)
        self.search = ctk.CTkEntry(
            bar,
            width=270,
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
        columns = ("cedula", "patient", "age", "sex")
        self.table = ttk.Treeview(
            host,
            columns=columns,
            show="headings",
            style="Medicus.Treeview",
        )
        for column, label in (
            ("cedula", "Cedula"),
            ("patient", "Paciente"),
            ("age", "Edad"),
            ("sex", "Sexo"),
        ):
            self.table.heading(column, text=label)
            self.table.column(column, width=170)
        self.table.column("patient", width=300)
        scrollbar = ttk.Scrollbar(
            host,
            command=self.table.yview,
            style="Medicus.Vertical.TScrollbar",
        )
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.bind("<<TreeviewSelect>>", self._selection)
        self.table.bind("<Double-1>", lambda _event: self.open_history())

    def refresh(self):
        patients = self.service.listar_historias(self.search.get())
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
                ),
            )
        self._selection()

    def _selection(self, _event=None):
        self.open_button.configure(
            state="normal" if self.table.selection() else "disabled"
        )

    def selected_patient(self):
        selected = self.table.selection()
        return self.patients.get(selected[0]) if selected else None

    def open_history(self):
        patient = self.selected_patient()
        if patient:
            HistoryDetailDialog(self, self.session, self.service, patient)


class HistoryDetailDialog(ctk.CTkToplevel):
    def __init__(self, master, session, service, patient):
        super().__init__(master)
        self.host = master
        self.session = session
        self.service = service
        self.patient = patient
        self.title("Historia clinica")
        self.geometry("820x720")
        self.minsize(680, 560)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="ew")
        ctk.CTkLabel(
            header,
            text=patient["nombre_completo"],
            font=ctk.CTkFont(size=21, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=f"{patient['cedula']} | {patient['edad']} anos | {patient['sexo']}",
            text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(3, 0))

        self.body = ctk.CTkScrollableFrame(self)
        self.body.grid(row=1, column=0, padx=24, pady=8, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, padx=24, pady=(8, 20), sticky="e")
        if session.role == MEDICO:
            ctk.CTkButton(
                footer,
                text="Proxima consulta",
                command=self._followup,
                fg_color=COLORS["surface_alt"],
                text_color=COLORS["text"],
            ).grid(row=0, column=0, padx=(0, 8))
            ctk.CTkButton(
                footer,
                text="Agregar diagnostico y tratamiento",
                command=self._add_evolution,
            ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            footer,
            text="Cerrar",
            width=90,
            command=self.destroy,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        ).grid(row=0, column=2)
        self.refresh()

    def refresh(self):
        for child in self.body.winfo_children():
            child.destroy()
        success, message, history = self.service.obtener_historia(self.patient["id"])
        if not success:
            ctk.CTkLabel(
                self.body,
                text=message,
                text_color=COLORS["danger"],
            ).grid(row=0, column=0, padx=12, pady=20, sticky="w")
            return
        evolutions = history["evoluciones"]
        if not evolutions:
            ctk.CTkLabel(
                self.body,
                text="Todavia no hay evoluciones clinicas registradas.",
                text_color=COLORS["muted"],
            ).grid(row=0, column=0, padx=12, pady=20, sticky="w")
            return
        for row, evolution in enumerate(evolutions):
            panel = ctk.CTkFrame(
                self.body,
                fg_color=COLORS["surface"],
                border_width=1,
                border_color=COLORS["border"],
                corner_radius=6,
            )
            panel.grid(row=row, column=0, padx=4, pady=6, sticky="ew")
            panel.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                panel,
                text=(
                    f"{evolution['fecha_consulta']} | "
                    f"{evolution['especialidad']} | {evolution['medico']}"
                ),
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")
            ctk.CTkLabel(
                panel,
                text=(
                    f"Altura: {evolution['altura_cm']:.1f} cm   "
                    f"Peso: {evolution['peso_kg']:.1f} kg"
                ),
                text_color=COLORS["muted"],
            ).grid(row=1, column=0, padx=14, sticky="w")
            ctk.CTkLabel(
                panel,
                text=f"Diagnostico\n{evolution['diagnostico']}",
                justify="left",
                anchor="w",
                wraplength=700,
            ).grid(row=2, column=0, padx=14, pady=(10, 4), sticky="ew")
            ctk.CTkLabel(
                panel,
                text=f"Conducta / Tratamiento\n{evolution['tratamiento']}",
                justify="left",
                anchor="w",
                wraplength=700,
            ).grid(row=3, column=0, padx=14, pady=(4, 14), sticky="ew")

    def _add_evolution(self):
        appointments = self.service.citas_pendientes(self.patient["id"])
        if not appointments:
            messagebox.showwarning(
                "Sin citas pendientes",
                "Agende una consulta antes de registrar una evolucion.",
                parent=self,
            )
            return
        EvolutionDialog(self, self.service, self.patient, appointments, self.refresh)

    def _followup(self):
        from medicus_privacy.gui.citas_frame import NewAppointmentDialog

        appointment_service = CitasService(
            self.session.username,
            self.session.role,
        )

        def submit(doctor, patient_id, selected_date, selected_time, specialty, student):
            success, message = appointment_service.agendar_cita(
                doctor,
                patient_id,
                selected_date,
                selected_time,
                specialty,
                student,
            )
            method = messagebox.showinfo if success else messagebox.showerror
            method(
                "Operacion completada" if success else "No se pudo completar",
                message,
                parent=self,
            )
            return success

        NewAppointmentDialog(self, self.session, submit, self.patient)


class EvolutionDialog(ctk.CTkToplevel):
    def __init__(self, master, service, patient, appointments, on_saved):
        super().__init__(master)
        self.service = service
        self.patient = patient
        self.on_saved = on_saved
        self.appointment_map = {
            f"{item['fecha']} {item['hora']} | {item['especialidad']}": item["id"]
            for item in appointments
        }
        self.title("Nueva evolucion")
        self.geometry("620x680")
        self.minsize(520, 560)
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            body,
            text="Diagnostico y tratamiento",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=4, pady=(0, 8), sticky="w")
        ctk.CTkLabel(body, text="Consulta").grid(
            row=1, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.appointment = ctk.CTkOptionMenu(
            body,
            values=list(self.appointment_map),
        )
        self.appointment.grid(row=2, column=0, padx=4, sticky="ew")
        self.height = labeled_entry(body, 3, "Altura (cm)")
        self.weight = labeled_entry(body, 5, "Peso (kg)")
        ctk.CTkLabel(body, text="Diagnostico").grid(
            row=7, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.diagnosis = ctk.CTkTextbox(body, height=120)
        self.diagnosis.grid(row=8, column=0, padx=4, sticky="ew")
        ctk.CTkLabel(body, text="Conducta y/o tratamiento").grid(
            row=9, column=0, padx=4, pady=(10, 4), sticky="w"
        )
        self.treatment = ctk.CTkTextbox(body, height=140)
        self.treatment.grid(row=10, column=0, padx=4, sticky="ew")
        self.error = ctk.CTkLabel(
            body,
            text="",
            text_color=COLORS["danger"],
            wraplength=500,
        )
        self.error.grid(row=11, column=0, padx=4, pady=12, sticky="w")

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

    def _submit(self):
        success, message = self.service.agregar_evolucion(
            self.patient["id"],
            self.appointment_map[self.appointment.get()],
            self.height.get(),
            self.weight.get(),
            self.diagnosis.get("1.0", "end").strip(),
            self.treatment.get("1.0", "end").strip(),
        )
        if not success:
            self.error.configure(text=message)
            return
        messagebox.showinfo("Evolucion guardada", message, parent=self)
        self.on_saved()
        self.destroy()
