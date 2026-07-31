"""Reusable date and time controls for the desktop GUI."""

import calendar
from datetime import date

import customtkinter as ctk

from medicus_privacy.gui.theme import COLORS


TIME_SLOTS = tuple(
    f"{hour:02d}:{minute:02d}"
    for hour in range(7, 20)
    for minute in (0, 30)
    if not (hour == 19 and minute == 30)
)


class DateSelector(ctk.CTkFrame):
    def __init__(
        self,
        master,
        value=None,
        min_date=None,
        max_date=None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.min_date = min_date
        self.max_date = max_date
        self.value = value or min_date or date.today()
        if isinstance(self.value, str):
            self.value = date.fromisoformat(self.value)
        self.grid_columnconfigure(0, weight=1)
        self.button = ctk.CTkButton(
            self,
            text=self.value.isoformat(),
            anchor="w",
            height=38,
            command=self._open,
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=5,
        )
        self.button.grid(row=0, column=0, sticky="ew")

    def get(self):
        return self.value.isoformat()

    def set(self, value):
        self.value = date.fromisoformat(value) if isinstance(value, str) else value
        self.button.configure(text=self.value.isoformat())

    def _open(self):
        DatePickerDialog(
            self,
            self.value,
            self.set,
            self.min_date,
            self.max_date,
        )


class DatePickerDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        selected,
        on_select,
        min_date=None,
        max_date=None,
    ):
        super().__init__(master)
        self.selected = selected
        self.visible_year = selected.year
        self.visible_month = selected.month
        self.on_select = on_select
        self.min_date = min_date
        self.max_date = max_date
        self.title("Seleccionar fecha")
        self.geometry("390x410")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=18, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            header,
            text="<",
            width=38,
            command=lambda: self._move(-1),
        ).grid(row=0, column=0)
        self.month_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.month_label.grid(row=0, column=1)
        ctk.CTkButton(
            header,
            text=">",
            width=38,
            command=lambda: self._move(1),
        ).grid(row=0, column=2)

        self.calendar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.calendar_frame.grid(row=1, column=0, padx=18, pady=8, sticky="nsew")
        for column in range(7):
            self.calendar_frame.grid_columnconfigure(column, weight=1)
        self._render()

    def _move(self, offset):
        month = self.visible_month + offset
        year = self.visible_year
        if month < 1:
            month, year = 12, year - 1
        elif month > 12:
            month, year = 1, year + 1
        self.visible_month, self.visible_year = month, year
        self._render()

    def _render(self):
        for child in self.calendar_frame.winfo_children():
            child.destroy()
        month_names = (
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        )
        self.month_label.configure(
            text=f"{month_names[self.visible_month - 1]} {self.visible_year}"
        )
        for column, name in enumerate(("Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do")):
            ctk.CTkLabel(
                self.calendar_frame,
                text=name,
                text_color=COLORS["muted"],
            ).grid(row=0, column=column, pady=5)

        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(
            self.visible_year,
            self.visible_month,
        )
        for row_index, week in enumerate(weeks, start=1):
            for column, day in enumerate(week):
                if day == 0:
                    continue
                candidate = date(
                    self.visible_year,
                    self.visible_month,
                    day,
                )
                enabled = not (
                    (self.min_date and candidate < self.min_date)
                    or (self.max_date and candidate > self.max_date)
                )
                selected = candidate == self.selected
                ctk.CTkButton(
                    self.calendar_frame,
                    text=str(day),
                    width=40,
                    height=36,
                    state="normal" if enabled else "disabled",
                    command=lambda value=candidate: self._choose(value),
                    fg_color=COLORS["accent"] if selected else "transparent",
                    hover_color=COLORS["surface_alt"],
                    text_color="#FFFFFF" if selected else COLORS["text"],
                ).grid(row=row_index, column=column, padx=2, pady=2)

    def _choose(self, value):
        self.selected = value
        self.on_select(value)
        self.destroy()


def labeled_entry(master, row, label, value="", show=None):
    ctk.CTkLabel(master, text=label).grid(
        row=row,
        column=0,
        padx=4,
        pady=(10, 4),
        sticky="w",
    )
    entry = ctk.CTkEntry(master, height=38, show=show, corner_radius=5)
    entry.grid(row=row + 1, column=0, padx=4, sticky="ew")
    if value not in (None, ""):
        entry.insert(0, str(value))
    return entry
