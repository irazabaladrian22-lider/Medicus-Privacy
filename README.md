# Medicus-Privacy

Aplicación de escritorio hospitalaria para administrar personal, pacientes,
citas e historias clínicas con autenticación por roles, SQLite y cifrado
AES-256-GCM.

# Integrantes del equipo

- Adrian Irazabal 30.458.791
- ⁠Andrés Jesús Ramos 30.507.057
- Dylan Isava
- ⁠Wilmer Joel Pérez González 24.331.903

## Instalación y ejecución

Desde `Medicus-Privacy-main`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m medicus_privacy.gui.app
```

En el IDE seleccione `.venv\Scripts\python.exe`, use
`Medicus-Privacy-main` como directorio de trabajo y ejecute el módulo
`medicus_privacy.gui.app`.

## Usuarios iniciales

Una base nueva incluye:

| Usuario      | Contraseña | Rol           | Especialidad     |
| ------------ | ---------- | ------------- | ---------------- |
| `admin`      | `admin123` | Admin         | No aplica        |
| `medico`     | `med123`   | Médico        | Medicina Interna |
| `recepcion`  | `rec123`   | Recepcionista | No aplica        |
| `estudiante` | `est123`   | Estudiante    | Medicina Interna |

Estas credenciales son solo para desarrollo. Una migración conserva el estado
activo o inactivo que ya tenía cada cuenta.

## Navegación y permisos

| Rol           | Paneles                    | Acciones                                                                                |
| ------------- | -------------------------- | --------------------------------------------------------------------------------------- |
| Admin         | Usuarios, Citas, Pacientes | Gestiona perfiles y opera cualquier cita; no ve contenido clínico.                      |
| Recepcionista | Citas, Pacientes           | Registra pacientes, agenda y cancela cualquier cita; no ve contenido clínico.           |
| Médico        | Citas, Historias clínicas  | Agenda y cancela sus consultas, registra evoluciones y consulta historias relacionadas. |
| Estudiante    | Citas, Historias clínicas  | Ve citas asignadas y, después de ser atendidas, historias en modo lectura.              |

El paciente no tiene cuenta ni inicia sesión. Es un registro administrativo y
clínico independiente del personal hospitalario.

## Flujo de citas

1. Seleccionar una especialidad.
2. Elegir un médico activo de esa especialidad.
3. Admin o Recepción pueden asignar opcionalmente un estudiante de la misma
   especialidad.
4. Buscar al paciente por cédula. Si no existe, registrar nombres, apellidos,
   fecha de nacimiento y sexo.
5. Seleccionar una fecha desde el calendario y una hora entre 07:00 y 19:00 en
   intervalos de 30 minutos.

La capa de servicios vuelve a validar permisos, especialidad, fecha futura y
colisiones de médico, paciente o estudiante. No es posible evitar estas reglas
modificando la interfaz.

## Historias clínicas

El médico accede a Historias clínicas desde el menú lateral. Cada historia
contiene los datos del paciente y una secuencia de evoluciones con:

- Fecha, médico y especialidad.
- Altura y peso.
- Diagnóstico.
- Conducta y/o tratamiento.

Para agregar una evolución debe existir una cita programada del paciente con
el médico autenticado. Al guardar, la cita pasa a `Atendida`. El botón
`Próxima consulta` permite agendar el seguimiento.

Un médico relacionado mediante una cita programada o atendida puede consultar
la historia completa para mantener continuidad clínica. El estudiante obtiene
acceso de solo lectura únicamente después de atender una cita en la que fue
asignado.

## Privacidad

- Las contraseñas usan PBKDF2-HMAC-SHA256 con sal aleatoria.
- Diagnósticos y tratamientos se cifran individualmente con AES-256-GCM.
- La clave clínica es generada por la aplicación y protegida mediante Windows
  DPAPI en `%LOCALAPPDATA%\MedicusPrivacy\clinical.key`.
- La clave no se guarda en SQLite ni se solicita al usuario.
- Admin y Recepción son rechazados por `ClinicalHistoryService`, aunque se
  intente invocar el servicio sin usar la GUI.
- Las consultas y escrituras clínicas se auditan sin registrar su contenido.

La protección de la clave con DPAPI está diseñada para el despliegue actual en
Windows. En pruebas puede inyectarse `MEDICUS_MASTER_KEY` en Base64.

## Generación segura de contraseñas

### `generar_hash_password(password)` / `hash_password(password)`

```python
from medicus_privacy.modules.seguridad import hash_password

password_hash = hash_password("ContrasenaTemporal123")
```

Ubicación: `medicus_privacy/modules/seguridad.py`.

La función recibe una contraseña en texto plano y devuelve una cadena preparada
para persistirse en `usuarios.password_hash`. Internamente:

1. Genera una sal aleatoria de 16 bytes.
2. Aplica PBKDF2-HMAC-SHA256 con 600.000 iteraciones.
3. Devuelve algoritmo, iteraciones, sal y resultado codificados en una sola
   cadena:

```text
pbkdf2_sha256$600000$<sal_hexadecimal>$<hash_hexadecimal>
```

La misma contraseña genera hashes diferentes porque cada llamada utiliza una
sal nueva. Para comprobar una contraseña no se genera otro hash manualmente; se
usa:

```python
from medicus_privacy.modules.seguridad import verificar_password

es_correcta = verificar_password(
    "ContrasenaTemporal123",
    password_hash,
)
```

`verificar_password` realiza una comparación en tiempo constante. Además,
durante un login correcto, `AuthService` actualiza automáticamente los hashes
heredados que ya no cumplen el número actual de iteraciones.

Las contraseñas en texto plano solo deben existir mientras se valida o crea la
cuenta. No deben escribirse en SQLite, logs ni archivos de configuración.

## 🗄 Estructura de la Base de Datos

### Base activa: `data/medicus_privacy.db`

El sistema utiliza SQLite con esquema versión 2. `DatabaseService` crea y
migra el esquema automáticamente, activa claves foráneas y administra cada
conexión con commit, rollback y cierre garantizado.

#### Tabla `usuarios`

| Campo             | Descripción                                           |
| ----------------- | ----------------------------------------------------- |
| `id`              | Identificador interno.                                |
| `username`        | Nombre de acceso único, sin distinguir mayúsculas.    |
| `password_hash`   | Hash PBKDF2; nunca contiene la contraseña original.   |
| `rol`             | Admin, Médico, Recepcionista o Estudiante.            |
| `nombre_completo` | Nombre mostrado en la interfaz.                       |
| `especialidad`    | Obligatoria para Médico y Estudiante.                 |
| `activo`          | Permite desactivar la cuenta sin borrar su historial. |
| `creado_en`       | Fecha de creación del usuario.                        |

#### Tabla `pacientes`

| Campo                               | Descripción                                     |
| ----------------------------------- | ----------------------------------------------- |
| `id`                                | Identificador interno del paciente.             |
| `cedula`                            | Identificación única normalizada.               |
| `nombres`, `apellidos`              | Identidad del paciente.                         |
| `fecha_nacimiento`                  | Permite calcular la edad en tiempo real.        |
| `sexo`, `nacionalidad`, `direccion` | Datos administrativos.                          |
| `datos_completos`                   | Indica si un registro migrado debe completarse. |
| `creado_en`, `actualizado_en`       | Trazabilidad del registro.                      |

El paciente no pertenece a `usuarios`: no posee contraseña ni puede iniciar
sesión.

#### Tabla `citas`

Relaciona un paciente con un médico y, opcionalmente, un estudiante:

| Campo           | Descripción                                              |
| --------------- | -------------------------------------------------------- |
| `medico_id`     | Médico responsable.                                      |
| `paciente_id`   | Paciente atendido.                                       |
| `estudiante_id` | Estudiante asignado; puede ser nulo.                     |
| `fecha`, `hora` | Franja de atención.                                      |
| `especialidad`  | Especialidad bajo la que se agenda.                      |
| `estado`        | `Programada`, `Atendida` o `Cancelada`.                  |
| `motivo_legacy` | Dato conservado únicamente durante migraciones antiguas. |

Los índices parciales impiden que un médico, paciente o estudiante tenga dos
citas programadas en la misma fecha y hora.

#### Tablas `historias_clinicas` y `evoluciones_clinicas`

`historias_clinicas` mantiene una única historia por paciente.
`evoluciones_clinicas` conserva cada consulta por separado:

- Cita y médico que registraron la evolución.
- Altura y peso.
- Diagnóstico cifrado.
- Conducta o tratamiento cifrado.
- Fecha de creación.

Diagnóstico y tratamiento usan AES-256-GCM. La clave clínica se protege fuera
de SQLite mediante Windows DPAPI.

### Relaciones principales

```text
usuarios (Médico) ──< citas >── pacientes
usuarios (Estudiante) ──< citas
pacientes ──0..1 historias_clinicas
historias_clinicas ──< evoluciones_clinicas
citas ──0..1 evoluciones_clinicas
```

### Archivo heredado: `db_medicus.json`

`db_medicus.json` pertenece a la versión inicial y ya no es la base activa. Se
conserva como fuente histórica para migraciones. Su estructura original era:

```json
{
  "usuarios": {
    "admin": {
      "password_hash": "salt$hash_heredado",
      "rol": "Admin",
      "nombre_completo": "Administrador Principal"
    }
  },
  "citas": [
    {
      "id": "1",
      "medico": "nombre_medico",
      "alumno": "nombre_estudiante",
      "fecha": "AAAA-MM-DD",
      "hora": "HH:MM",
      "especialidad": "Odontologia",
      "motivo": "TextoCifrado...",
      "cifrado": true,
      "estado": "Programada"
    }
  ]
}
```

Al detectar el esquema SQLite anterior, el sistema:

1. Crea `data/medicus_privacy.backup-v1-AAAAMMDD-HHMMSS.db`.
2. Añade especialidad a médicos y estudiantes antiguos.
3. Convierte los antiguos estudiantes usados como pacientes en registros
   `LEGACY-<id>` pendientes de completar.
4. Conserva las citas y sus estados.

Ninguna operación nueva escribe en `db_medicus.json`.

## Arquitectura

```text
medicus_privacy/
+-- gui/
|   +-- app.py
|   +-- admin_frame.py
|   +-- citas_frame.py
|   +-- patients_frame.py
|   +-- history_frame.py
|   +-- widgets.py
+-- modules/
    +-- database.py
    +-- admin.py
    +-- patients.py
    +-- citas.py
    +-- clinical.py
    +-- clinical_crypto.py
    +-- key_manager.py
    +-- directory.py
    +-- catalogs.py
```

La GUI no contiene SQL, hashing ni cifrado. Cada panel usa servicios
autorizados con la identidad de `UserSession`.

## Cómo verificar que compila

Ejecute los comandos desde `Medicus-Privacy-main` con el entorno virtual
activado.

### Compilar todo el paquete

```powershell
python -m compileall -q medicus_privacy
```

Si el comando termina sin mensajes de error, todos los módulos del paquete
pueden compilarse. La opción `-q` oculta las líneas exitosas.

### Verificar los puntos de entrada principales

```powershell
python -m py_compile `
  medicus_privacy\gui\app.py `
  medicus_privacy\Main\Main.py `
  medicus_privacy\modules\database.py `
  medicus_privacy\modules\auth.py `
  medicus_privacy\modules\seguridad.py
```

`py_compile` detecta errores de sintaxis en archivos concretos sin iniciar la
GUI ni modificar la base de datos.

### Validación completa para desarrollo

```powershell
python -m unittest discover -v
python -m compileall -q medicus_privacy
python -m pip check
```

- `unittest` comprueba reglas de negocio, permisos, migración y cifrado.
- `compileall` verifica la sintaxis de todos los módulos.
- `pip check` detecta dependencias incompatibles o incompletas.

La suite utiliza bases `.test_*.db` aisladas y no debe modificar
`data/medicus_privacy.db`. La validación manual está en
`..\CHECKLIST_PRUEBAS_GUI.md`.

## Especificaciones del sistema

### Identidad y acceso

- El acceso requiere usuario y contraseña; cada sesión conserva la identidad,
  el nombre y el rol autenticado.
- Los roles disponibles son Admin, Médico, Recepcionista y Estudiante.
- La navegación y las operaciones cambian según el rol, y los servicios vuelven
  a validar cada permiso aunque una acción se invoque fuera de la GUI.
- Los pacientes son registros asistenciales y no poseen credenciales ni acceso
  al sistema.

### Personal y especialidades

- Admin crea, edita, activa y desactiva cuentas del personal.
- Los perfiles de Médico y Estudiante requieren una especialidad.
- Las especialidades disponibles son Medicina Interna, Pediatría, Ginecología y
  Obstetricia, Cardiología, Traumatología y Ortopedia, y Odontología.
- Al agendar, solo se muestran médicos y estudiantes activos que pertenecen a
  la especialidad seleccionada.

### Pacientes y citas

- Admin, Recepción y Médico pueden registrar un paciente durante la creación de
  su primera cita.
- Cada paciente se identifica mediante una cédula única y conserva nombres,
  apellidos, fecha de nacimiento, sexo, nacionalidad y dirección.
- La edad se calcula desde la fecha de nacimiento y no se almacena como un dato
  fijo.
- Las citas se seleccionan mediante calendario y horarios entre 07:00 y 19:00
  en intervalos de 30 minutos.
- El sistema rechaza fechas u horas pasadas y evita colisiones de médico,
  paciente o estudiante.
- Admin y Recepción operan cualquier cita; el Médico agenda y cancela solo sus
  consultas; el Estudiante únicamente consulta las citas asignadas.

### Historias clínicas

- Cada paciente posee una historia clínica longitudinal con múltiples
  evoluciones.
- Cada evolución registra fecha, médico, especialidad, altura, peso,
  diagnóstico y conducta o tratamiento.
- Solo el Médico asignado puede crear una evolución a partir de una cita
  programada; al guardarla, la cita cambia a `Atendida`.
- Un Médico con relación asistencial puede consultar la historia completa para
  mantener la continuidad del tratamiento.
- El Estudiante asignado obtiene acceso de solo lectura después de que la cita
  sea atendida.
- Admin y Recepción solo acceden a información administrativa del paciente.

### Seguridad y privacidad

- Las contraseñas se almacenan mediante PBKDF2-HMAC-SHA256 con sal aleatoria.
- Los diagnósticos y tratamientos se cifran individualmente con AES-256-GCM.
- La clave clínica es administrada por la aplicación, está protegida mediante
  Windows DPAPI y no se almacena en SQLite.
- Los eventos de autenticación y acceso clínico se auditan sin registrar
  contraseñas, claves, diagnósticos ni tratamientos.

### Interfaz y persistencia

- La interfaz admite modo claro y oscuro, filtros de búsqueda y tablas
  actualizables sin reiniciar.
- Los formularios extensos son desplazables y mantienen visibles las acciones
  Guardar, Agendar, Cancelar o Cerrar.
- SQLite conserva usuarios, pacientes, citas e historias entre ejecuciones.
- La migración desde el esquema anterior crea una copia de seguridad antes de
  transformar los datos.
