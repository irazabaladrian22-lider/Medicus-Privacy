# Documentacion actual de Medicus-Privacy

## Estado general

Por ahora el proyecto es una aplicacion de consola en Python. La parte funcional implementada es la seccion de **Recepcion/Login**, encargada de validar quien entra al sistema y que rol tiene.

El flujo principal esta en `medicus_privacy/Main/Main.py`. Ese archivo muestra el banner, solicita usuario y contrasena, valida las credenciales usando el modulo de autenticacion y redirige segun el rol.

## Estructura actual

```text
Medicus-Privacy-main/
+-- data/
|   +-- users.json
+-- logs/
|   +-- medicus_audit.log
+-- medicus_privacy/
|   +-- Main/
|   |   +-- __init__.py
|   |   +-- Main.py
|   +-- modules/
|   |   +-- __init__.py
|   |   +-- auth.py
|   +-- __init__.py
+-- README.md
```

## Que hace el codigo

### `Main.py`

Es el punto de entrada del sistema.

Responsabilidades principales:

- Configura el nombre y version de la aplicacion.
- Configura el sistema de logs en `logs/medicus_audit.log`.
- Carga el servicio real de autenticacion `AuthService`.
- Muestra el banner de bienvenida.
- Solicita usuario y contrasena.
- Permite hasta 3 intentos fallidos.
- Registra accesos concedidos y denegados.
- Redirige segun el rol autenticado:
  - `Admin`
  - `Medico`
  - `Recepcionista`
  - `Estudiante`

### `auth.py`

Contiene el servicio real de autenticacion.

Responsabilidades principales:

- Cargar usuarios desde `data/users.json`.
- Buscar un usuario por nombre de usuario.
- Verificar si el usuario esta activo.
- Validar que el rol sea permitido.
- Comparar la contrasena ingresada contra el hash guardado.
- Devolver al `Main.py` si el acceso fue exitoso y que rol tiene el usuario.

### `users.json`

Guarda los usuarios iniciales del sistema.

Importante: las contrasenas no estan guardadas en texto plano. Cada usuario tiene:

- `salt`
- `password_hash`

Esto permite validar contrasenas sin almacenar directamente la contrasena real.

## Cambios realizados

- Se creo el paquete `medicus_privacy` agregando archivos `__init__.py`.
- Se creo la carpeta `medicus_privacy/modules`.
- Se implemento `medicus_privacy/modules/auth.py`.
- Se creo `data/users.json` con usuarios iniciales.
- Se conecto `Main.py` con `AuthService`.
- Se elimino el uso normal del mock de autenticacion.
- Se agrego lectura de contrasena oculta con `getpass`.
- Se agrego fallback para consolas que no soporten contrasena oculta.
- Se agregaron los roles oficiales del proyecto:
  - `Admin`
  - `Medico`
  - `Recepcionista`
  - `Estudiante`
- Se ajusto la ruta de logs para que siempre apunte a la carpeta `logs` del proyecto.

## Funciones y clases importantes

### `main()`

Ubicacion: `medicus_privacy/Main/Main.py`

Inicia el programa, controla el login y decide a que panel debe entrar el usuario segun su rol.

### `setup_logging()`

Ubicacion: `medicus_privacy/Main/Main.py`

Configura el logger del sistema. Guarda eventos importantes en archivo y tambien los muestra en consola.

### `mostrar_banner()`

Ubicacion: `medicus_privacy/Main/Main.py`

Limpia la pantalla y muestra el nombre, version y descripcion del sistema.

### `solicitar_password()`

Ubicacion: `medicus_privacy/Main/Main.py`

Solicita la contrasena al usuario. Normalmente la oculta en pantalla. Si la consola no permite ocultarla, usa una entrada visible como respaldo.

### `AuthService`

Ubicacion: `medicus_privacy/modules/auth.py`

Clase principal del modulo de autenticacion.

### `AuthService.verificar_credenciales(usuario, password)`

Ubicacion: `medicus_privacy/modules/auth.py`

Funcion principal de Recepcion/Login. Recibe usuario y contrasena.

Si las credenciales son correctas, devuelve:

```python
(True, rol, datos_usuario)
```

Ejemplo:

```python
(True, "Admin", {
    "user_id": 1,
    "nombre": "Admin Sistema",
    "usuario": "admin",
    "rol": "Admin"
})
```

Si las credenciales son incorrectas, devuelve:

```python
(False, None, None)
```

### `generar_hash_password(password)`

Ubicacion: `medicus_privacy/modules/auth.py`

Funcion auxiliar para generar un `salt` y un `password_hash`. Sirve para crear nuevos usuarios sin guardar contrasenas en texto plano.

## Usuarios de prueba

```text
Usuario: admin
Contrasena: admin123
Rol: Admin

Usuario: medico
Contrasena: med123
Rol: Medico

Usuario: recepcion
Contrasena: rec123
Rol: Recepcionista

Usuario: estudiante
Contrasena: est123
Rol: Estudiante
```

## Como ejecutar

Desde la carpeta `Medicus-Privacy-main`:

```bash
python medicus_privacy/Main/Main.py
```

Al pedir la contrasena, puede que no se vea nada mientras se escribe. Eso es normal: la entrada esta oculta por seguridad. Se escribe la contrasena y se presiona Enter.

## Como verificar que compila

Desde la carpeta `Medicus-Privacy-main`:

```bash
python -m py_compile medicus_privacy/Main/Main.py medicus_privacy/modules/auth.py
```

## Proximos pasos sugeridos

- Crear el modulo de Administracion para gestionar usuarios y roles.
- Crear el modulo de Citas para recepcionista, medico y estudiante.
- Crear una base de datos real para reemplazar el JSON cuando el proyecto avance.
- Agregar pruebas automatizadas con `unittest` o `pytest`.
- Corregir textos con caracteres danados por codificacion en archivos antiguos.

# Medicus-Privacy 🛡️🩺

**Medicus-Privacy** es un sistema modular en Python diseñado para la gestión de usuarios, programación de citas médicas y protección estricta de la privacidad mediante criptografía. El sistema está estructurado bajo una arquitectura de "caja negra" dividida en estaciones de trabajo para facilitar la colaboración en equipo.

Este repositorio contiene la implementación de los tres módulos principales:
1. **Seguridad e Integridad** (`seguridad.py`)
2. **Administración de Usuarios** (`admin.py`)
3. **Gestión de Reservas y Citas** (`citas.py`)

---

## 📂 Arquitectura de Archivos

* `seguridad.py`: Proporciona las funciones de criptografía simétrica y hashing de contraseñas.
* `admin.py`: Gestiona la base de datos de usuarios, altas, bajas, roles y contraseñas.
* `citas.py`: Gestiona la agenda, verifica disponibilidad médica y encripta datos sensibles.
* `db_medicus.json`: Archivo de persistencia de datos (base de datos JSON).
* `test_admin.py` y `test_citas.py`: Scripts de pruebas automatizadas para garantizar la calidad del código.

---

## 🛠️ Detalle de los Módulos

### 1. 🔒 Módulo de Seguridad (`seguridad.py`)
Es la "caja fuerte" del sistema. No tiene dependencias externas y provee seguridad criptográfica robusta.

* **Funciones principales**:
  * `hash_password(password: str) -> str`: Genera un hash seguro con sal (salt) usando PBKDF2-HMAC-SHA256 para contraseñas.
  * `verificar_password(password: str, password_hash: str) -> bool`: Compara contraseñas usando algoritmos en tiempo constante contra ataques de canal lateral.
  * `cifrar_datos(texto: str, clave: str) -> str`: Cifra textos planos (como diagnósticos) con cifrado de flujo simétrico, generando un IV aleatorio y un código MAC (HMAC-SHA256) para asegurar la integridad.
  * `descifrar_datos(texto_cifrado_b64: str, clave: str) -> str`: Descifra y verifica la integridad del texto. Lanza un `ValueError` si la clave es incorrecta o los datos fueron alterados.

---

### 2. 👥 Módulo de Administración (`admin.py`)
Controla la administración del personal de la clínica y sus roles (`Admin`, `Recep`, `Médico`, `Estudiante`).

* **Funciones de Negocio**:
  * `crear_usuario(username, password, rol, nombre_completo)`: Registra un usuario y hace hash de su contraseña.
  * `eliminar_usuario(username)`: Elimina un usuario (protege contra la eliminación del único Administrador).
  * `listar_usuarios()`: Retorna información básica sin exponer contraseñas.
  * `actualizar_rol_usuario(username, nuevo_rol)`: Actualiza permisos.
* **Interfaz de Consola**:
  * `mostrar_menu_admin()`: Menú interactivo CLI para la gestión rápida de usuarios.

---

### 3. 📅 Módulo de Citas y Reservas (`citas.py`)
Gestiona el calendario, la disponibilidad de los médicos y el agendamiento seguro.

* **Funciones de Negocio**:
  * `agendar_cita(medico_username, alumno_username, fecha, hora, especialidad, motivo_sensible, clave_seguridad)`: Crea una cita. Si se pasa un motivo, lo cifra con la clave de seguridad a través de `seguridad.py`.
  * `verificar_disponibilidad(medico_username, fecha, hora)`: Valida colisiones de horario (un médico no puede duplicar citas en el mismo bloque).
  * `cancelar_cita(cita_id)`: Cancela y libera el horario del médico.
  * `obtener_citas_filtradas(rol_usuario, username)`: Filtra citas automáticamente según el rol del usuario conectado.
  * `descifrar_motivo_cita(cita, clave_seguridad)`: Permite descifrar el motivo médico de forma controlada.
* **Interfaz de Consola**:
  * `mostrar_menu_citas(username_actual, rol_actual)`: Menú CLI adaptado al rol del usuario (por ejemplo, el Estudiante agenda y ve sus citas; el Médico puede descifrar los diagnósticos introduciendo su clave privada).

---

## 🗄️ Estructura de la Base de Datos (`db_medicus.json`)

El archivo JSON almacena los registros estructurados con la siguiente forma:

```json
{
  "usuarios": {
    "admin": {
      "password_hash": "salt$hash_de_prueba",
      "rol": "Admin",
      "nombre_completo": "Administrador Principal"
    }
  },
  "citas": [
    {
      "id": "1",
      "medico": "nombre_medico",
      "alumno": "nombre_estudiante",
      "fecha": "YYYY-MM-DD",
      "hora": "HH:MM",
      "especialidad": "Odontología",
      "motivo": "TextoCifradoEnBase64...",
      "cifrado": true,
      "estado": "Programada"
    }
  ]
}
```

---

## 🚀 Cómo Ejecutar e Integrar

### Ejecución de Pruebas Unitarias
Para validar que todo el backend y cifrado funcionan correctamente, ejecuta:
```bash
python test_admin.py
python test_citas.py
```

### Ejecutar Módulos de Forma Autónoma
Cada módulo cuenta con un bloque ejecutable para pruebas individuales:
* Ejecutar Administración: `python admin.py`
* Ejecutar Reservas: `python citas.py`
* *Nota: Puedes iniciar sesión usando el usuario por defecto `admin` y la contraseña `admin123`.*

### Guía de Integración para el Director (`main.py`)
Para conectar estas piezas en el menú principal (`main.py`), solo debes importar las funciones de interfaz:

```python
from admin import mostrar_menu_admin
from citas import mostrar_menu_citas

# Ejemplo de flujo tras autenticar al usuario:
if rol == "Admin":
    # Muestra el panel de administración
    mostrar_menu_admin()
elif rol in ["Médico", "Estudiante", "Recep"]:
    # Muestra la agenda adaptada a sus permisos
    mostrar_menu_citas(usuario_actual, rol)
```

