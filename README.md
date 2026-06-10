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


