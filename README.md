# Simulador conversacional de inglés con IA — Backend

## Qué es el proyecto

Aplicación web para que estudiantes de la Facultad de Idiomas de la Universidad
Veracruzana practiquen producción oral (*speaking*) en inglés conversando por voz
con un agente de IA dentro de un escenario elegido (por ejemplo, un restaurante o
un aeropuerto). Al cerrar la sesión, el estudiante recibe un reporte de
retroalimentación sobre gramática, vocabulario y áreas de mejora.

- Es práctica guiada por escenarios, ajustada al nivel MCER elegido, con pausa y
  reanudación, y con métricas de progreso.
- Se usa en PC o laptop con micrófono. **No** es una app móvil.
- **No** certifica nivel MCER, **no** sustituye al docente y **no** evalúa
  pronunciación: el sistema trabaja con la transcripción del audio.

Este repositorio es el **backend**: autenticación, base de datos, cliente de IA,
sondas de salud y el dominio del simulador (sesiones, turnos, retroalimentación y
métricas). La especificación completa del producto está en la skill
[`simulador-conversacional-ia-dev`](./.opencode/skills/simulador-conversacional-ia-dev/SKILL.md)
y las reglas de código en [`AGENTS.md`](./AGENTS.md).

### Endpoints de la ventana de chat

Todos requieren el token de acceso (`Authorization: Bearer ...`).

| Método y ruta                          | Qué hace                                             |
| -------------------------------------- | ---------------------------------------------------- |
| `GET /scenarios`                       | Escenarios y niveles MCER disponibles.               |
| `POST /sessions`                       | Inicia una sesión y genera el saludo del agente.     |
| `GET /sessions`                        | Lista las sesiones del estudiante.                   |
| `GET /sessions/{id}`                   | Carga la conversación (render o reanudar).           |
| `POST /sessions/{id}/turnos`           | Turno por texto.                                     |
| `POST /sessions/{id}/turnos/audio`     | Turno por audio (lo transcribe Groq Whisper).        |
| `POST /sessions/{id}/pausar`           | Pausa la sesión.                                     |
| `POST /sessions/{id}/reanudar`         | Reanuda (solo dentro de 30 días).                    |
| `POST /sessions/{id}/cerrar`           | Cierra y genera el reporte de retroalimentación.     |
| `GET /sessions/{id}/retroalimentacion` | Consulta el reporte ya generado.                     |
| `POST /sessions/{id}/evaluacion`       | Evaluación opcional del sistema (1 a 5).             |

## Cómo ejecutarlo

Los pasos 1 a 4 se hacen **una sola vez**. Después, para usar la app basta con el
paso 5.

### 1. Instala uv

`uv` es la herramienta que crea el entorno virtual y maneja las dependencias.
Abre **PowerShell** y copia y pega este comando:

```powershell
pip install uv
```

Verifica que quedó instalado y luego **cierra y vuelve a abrir PowerShell**:

```powershell
uv --version
```

> Si el comando `uv` no existe, cierra PowerShell, ábrelo de nuevo e inténtalo otra
> vez. No necesitas instalar Python aparte: `uv` lo descarga solo si hace falta.

### 2. Abre la carpeta del proyecto y crea el entorno virtual

En PowerShell, entra a la carpeta donde descargaste el proyecto (ajusta la ruta a la
tuya) y crea el entorno virtual `.venv`:

```powershell
cd ruta\donde\esta\residencia
uv venv
```

Ahora actívalo para que Windows use ese entorno:

```powershell
.venv\Scripts\Activate.ps1
```

Si aparece un error que dice que "la ejecución de scripts está deshabilitada",
ejecuta una sola vez este comando, cierra PowerShell, ábrelo de nuevo y repite la
activación:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Con el entorno activado (verás `(.venv)` al inicio de la línea), instala las
dependencias del proyecto:

```powershell
uv sync --all-extras
```

La carpeta `.venv` es el espacio privado donde viven las herramientas del proyecto,
sin afectar el resto de tu computadora. La primera vez tarda unos minutos.

> Activar el entorno es opcional: los comandos `uv run` de los siguientes pasos usan
> `.venv` automáticamente aunque no lo actives.

### 3. Crea tu archivo de configuración

Copia la plantilla y ábrela con un editor de texto (VS Code, Notepad, etc.):

```powershell
copy .env.example .env
```

Rellena al menos estas dos líneas con claves secretas propias (no compartas estas
claves con nadie):

| Línea                    | Qué es                                              |
| ------------------------ | --------------------------------------------------- |
| `AUTH_JWT_SECRET`        | Clave para firmar los accesos.                      |
| `AUTH_REFRESH_TOKEN_KEY` | Clave para renovar sesiones; debe ser **diferente**. |

Para generar cada clave, ejecuta este comando y copia el resultado:

```powershell
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`DEEPSEEK_API_KEY` es opcional: se necesita para crear sesiones (el agente que
conversa). `GROQ_API_KEY` es opcional: se necesita para los turnos por audio
(transcripción). Sin ellas, esos endpoints responden con un error claro y el resto
de la app funciona. Deja las demás líneas como están.

### 4. Prepara la base de datos

```powershell
uv run alembic upgrade head
```

Esto crea el archivo `cosa.db` con las tablas que la app necesita.

### 5. Arranca la aplicación

```powershell
uv run uvicorn src.main:app --reload
```

Cuando veas el mensaje `Application startup complete`, abre en tu navegador:

- <http://127.0.0.1:8000/docs> — documentación interactiva de la API.
- <http://127.0.0.1:8000/health> — debe responder `{"status":"ok",...}`.

Para detener el servidor presiona `Ctrl + C` en la terminal.

### La próxima vez

Abre PowerShell, entra a la carpeta del proyecto y arranca la app (no hace falta
activar el entorno):

```powershell
cd ruta\donde\esta\residencia
uv run uvicorn src.main:app --reload
```

### Correr las pruebas

```powershell
uv run pytest
```

## Si algo falla

- **`uv` no se reconoce como comando** — cierra PowerShell, ábrelo de nuevo; si
  sigue, reinstala uv con el comando del paso 1.
- **`Activate.ps1` no se puede cargar porque la ejecución de scripts está
  deshabilitada** — ejecuta el comando `Set-ExecutionPolicy` del paso 2.
- **`no such table: user`** — faltó el paso 4: ejecuta `uv run alembic upgrade head`.
- **El puerto 8000 está ocupado** — cierra el otro servidor o usa otro puerto:
  `uv run uvicorn src.main:app --reload --port 8001`.
- **Las cookies no se guardan / el login no funciona en local** — revisa que
  `.env` tenga `AUTH_SECURE_COOKIES=false`.
- **Quiero empezar de cero con la base de datos** — borra los archivos
  `cosa.db`, `cosa.db-wal` y `cosa.db-shm`, y repite el paso 4.
