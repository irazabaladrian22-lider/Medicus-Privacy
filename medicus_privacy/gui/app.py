"""Desktop application coordinator for Medicus-Privacy."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import customtkinter as ctk


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from medicus_privacy.gui.admin_frame import AdminFrame
from medicus_privacy.gui.citas_frame import CitasFrame
from medicus_privacy.gui.history_frame import HistoryFrame
from medicus_privacy.gui.login_frame import LoginFrame
from medicus_privacy.gui.patients_frame import PatientsFrame
from medicus_privacy.gui.session import UserSession
from medicus_privacy.gui.theme import COLORS, configure_treeview_style
from medicus_privacy.modules.auth import AuthService
from medicus_privacy.modules.roles import ADMIN, ESTUDIANTE, MEDICO, RECEPCIONISTA


APP_NAME = "Medicus-Privacy"
APP_VERSION = "3.0.0"
MAX_LOGIN_ATTEMPTS = 3
LOCK_SECONDS = 15


def navigation_for_role(role):
    navigation = {
        ADMIN: (
            ("Usuarios", "users"),
            ("Citas", "appointments"),
            ("Pacientes", "patients"),
        ),
        RECEPCIONISTA: (
            ("Citas", "appointments"),
            ("Pacientes", "patients"),
        ),
        MEDICO: (
            ("Citas", "appointments"),
            ("Historias clinicas", "histories"),
        ),
        ESTUDIANTE: (
            ("Citas", "appointments"),
            ("Historias clinicas", "histories"),
        ),
    }
    return navigation.get(role, ())


def setup_audit_logger():
    logger = logging.getLogger("Medicus-Privacy.GUI")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "medicus_audit.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger


class MedicusPrivacyApp(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=COLORS["window"])
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1240x780")
        self.minsize(1024, 680)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.auth_service = AuthService()
        self.audit = setup_audit_logger()
        self.session = None
        self.login_attempts = 0
        self.lock_remaining = 0
        self.current_view = None
        self.nav_buttons = {}
        configure_treeview_style(self)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.show_login()

    def clear_root(self):
        for child in self.winfo_children():
            child.destroy()

    def show_login(self):
        self.clear_root()
        self.session = None
        self.current_view = None
        self.nav_buttons = {}
        self.login_frame = LoginFrame(self, self.handle_login)
        self.login_frame.grid(row=0, column=0, sticky="nsew")

    def handle_login(self, username, password):
        self.after(50, lambda: self._authenticate(username, password))

    def _authenticate(self, username, password):
        success, role, user_data = self.auth_service.verificar_credenciales(
            username,
            password,
        )
        password = None
        if success:
            self.login_attempts = 0
            self.session = UserSession.from_auth_data(user_data)
            self.audit.info(
                "AUDITORIA | Acceso CONCEDIDO | Usuario: %s | Rol: %s | ID: %s",
                username,
                role,
                self.session.user_id,
            )
            self.show_dashboard()
            return
        self.login_attempts += 1
        self.audit.warning(
            "AUDITORIA | Acceso DENEGADO | Usuario: %s | Intento: %s/%s",
            username,
            self.login_attempts,
            MAX_LOGIN_ATTEMPTS,
        )
        if self.login_attempts >= MAX_LOGIN_ATTEMPTS:
            self.login_attempts = 0
            self.lock_remaining = LOCK_SECONDS
            self._update_login_lock()
        else:
            remaining = MAX_LOGIN_ATTEMPTS - self.login_attempts
            self.login_frame.set_error(
                f"Credenciales incorrectas. Intentos restantes: {remaining}."
            )
            self.login_frame.set_busy(False)

    def _update_login_lock(self):
        if not self.winfo_exists() or not hasattr(self, "login_frame"):
            return
        if self.lock_remaining <= 0:
            self.login_frame.set_error("Puede intentar iniciar sesion nuevamente.")
            self.login_frame.set_busy(False)
            return
        self.login_frame.set_error(
            f"Acceso bloqueado temporalmente. Espere {self.lock_remaining} segundos."
        )
        self.login_frame.set_busy(True)
        self.lock_remaining -= 1
        self.after(1000, self._update_login_lock)

    def show_dashboard(self):
        self.clear_root()
        shell = ctk.CTkFrame(self, fg_color=COLORS["window"], corner_radius=0)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(
            shell,
            width=232,
            fg_color=COLORS["surface"],
            corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(7, weight=1)
        self.sidebar = sidebar
        ctk.CTkLabel(
            sidebar,
            text="Medicus-Privacy",
            font=ctk.CTkFont(size=19, weight="bold"),
        ).grid(row=0, column=0, padx=22, pady=(24, 3), sticky="w")
        ctk.CTkLabel(
            sidebar,
            text=f"v{APP_VERSION}",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=10),
        ).grid(row=1, column=0, padx=22, pady=(0, 20), sticky="w")

        self.nav_buttons = {}
        for index, (label, view_name) in enumerate(
            navigation_for_role(self.session.role),
            start=2,
        ):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                anchor="w",
                height=40,
                command=lambda name=view_name: self.show_view(name),
                fg_color="transparent",
                hover_color=COLORS["surface_alt"],
                text_color=COLORS["text"],
                corner_radius=5,
            )
            button.grid(row=index, column=0, padx=12, pady=3, sticky="ew")
            self.nav_buttons[view_name] = button

        session_panel = ctk.CTkFrame(
            sidebar,
            fg_color=COLORS["surface_alt"],
            corner_radius=6,
        )
        session_panel.grid(row=8, column=0, padx=12, pady=(10, 8), sticky="ew")
        ctk.CTkLabel(
            session_panel,
            text=self.session.name,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 1))
        ctk.CTkLabel(
            session_panel,
            text=self.session.role,
            text_color=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkSwitch(
            sidebar,
            text="Modo claro",
            command=self._toggle_appearance,
            text_color=COLORS["muted"],
        ).grid(row=9, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkButton(
            sidebar,
            text="Cerrar sesion",
            command=self.logout,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        ).grid(row=10, column=0, padx=12, pady=(6, 18), sticky="ew")

        self.content_host = ctk.CTkFrame(
            shell,
            fg_color=COLORS["window"],
            corner_radius=0,
        )
        self.content_host.grid(row=0, column=1, sticky="nsew")
        self.content_host.grid_columnconfigure(0, weight=1)
        self.content_host.grid_rowconfigure(0, weight=1)
        self.show_view(navigation_for_role(self.session.role)[0][1])

    def show_view(self, view_name):
        if self.current_view is not None:
            self.current_view.destroy()
        factories = {
            "users": AdminFrame,
            "appointments": CitasFrame,
            "patients": PatientsFrame,
            "histories": HistoryFrame,
        }
        allowed = {name for _label, name in navigation_for_role(self.session.role)}
        if view_name not in allowed:
            view_name = navigation_for_role(self.session.role)[0][1]
        self.current_view = factories[view_name](
            self.content_host,
            self.session,
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")
        for name, button in self.nav_buttons.items():
            selected = name == view_name
            button.configure(
                fg_color=COLORS["accent"] if selected else "transparent",
                text_color="#FFFFFF" if selected else COLORS["text"],
            )

    def logout(self):
        if self.session:
            self.audit.info(
                "AUDITORIA | Cierre de sesion | Usuario: %s",
                self.session.username,
            )
        self.show_login()

    def _toggle_appearance(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("Light" if current == "Dark" else "Dark")
        configure_treeview_style(self)

    def _close(self):
        if self.session:
            self.audit.info(
                "AUDITORIA | Aplicacion cerrada | Usuario: %s",
                self.session.username,
            )
        self.destroy()


def main():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    MedicusPrivacyApp().mainloop()


if __name__ == "__main__":
    main()
