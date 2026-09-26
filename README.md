# Simulador conversacional de inglés con IA — Backend

Backend del **Simulador conversacional en inglés basado en IA** para la Facultad de
Idiomas de la Universidad Veracruzana: una aplicación web donde los estudiantes
practican producción oral (*speaking*) conversando por voz con un agente de IA dentro
de un escenario elegido y, al cerrar la sesión, reciben un reporte de retroalimentación
sobre gramática, vocabulario y áreas de mejora.

> **Nombre provisional.** El repositorio y el paquete Python conservan el nombre
> `cosa-backend` por historia del proyecto; no es el nombre del producto. La fuente de
> verdad del dominio (alcance, modelo de datos, reglas de negocio y pipeline de IA) es
> la skill del proyecto:
> [`.opencode/skills/simulador-conversacional-ia-dev/SKILL.md`](./.opencode/skills/simulador-conversacional-ia-dev/SKILL.md).

> **Estado del repositorio.** El dominio del simulador (sesiones, turnos,
> retroalimentación, métricas) todavía **no está implementado**. Lo que existe es la
> infraestructura sobre la que se construirá: acceso a datos, autenticación, cliente
> de IA, sondas de salud y una suite de pruebas. La sección
> [Estado actual](#estado-actual) detalla qué hay y qué falta, y
> [Cómo agregar un dominio](#cómo-agregar-un-dominio) explica por dónde seguir.

## Contenido

- [Qué es el sistema](#qué-es-el-sistema)
- [Cómo funciona una sesión](#cómo-funciona-una-sesión)
- [Arquitectura](#arquitectura)
- [Pipeline de IA](#pipeline-de-ia)
- [Contrato de datos con el LLM](#contrato-de-datos-con-el-llm)
- [Modelo de datos](#modelo-de-datos)
- [Reglas de negocio](#reglas-de-negocio)
- [Requisitos no funcionales](#requisitos-no-funcionales)
- [Estado actual](#estado-actual)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecutar el proyecto](#ejecutar-el-proyecto)
- [API](#api)
- [Base de datos y migraciones](#base-de-datos-y-migraciones)
- [Pruebas](#pruebas)
- [Lint y formato](#lint-y-formato)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Convenciones importantes](#convenciones-importantes)
- [Cómo agregar un dominio](#cómo-agregar-un-dominio)
- [Problemas frecuentes](#problemas-frecuentes)
- [Referencias](#referencias)

## Qué es el sistema

El simulador resuelve una necesidad acotada: dar a los estudiantes de la Facultad de
Idiomas un espacio de práctica oral en inglés, disponible cuando lo necesiten y sin la
presión de un aula. El estudiante elige un nivel y un escenario, conversa por voz con
un agente de IA que adopta el rol del escenario y, al terminar, recibe un reporte con
observaciones sobre su desempeño.

**Sí es:**

- Práctica de *speaking* en inglés guiada por escenarios y ajustada al nivel MCER
  seleccionado.
- Una conversación por turnos de voz, con pausa y reanudación.
- Un reporte orientativo de retroalimentación al cerrar la sesión.
- Seguimiento de progreso mediante métricas agregadas.

**No es:**

- Una app móvil: el diseño es para PC/laptop con micrófono.
- Una certificación ni acreditación oficial de nivel MCER.
- Un sustituto del docente.
- Un evaluador de pronunciación: una transcripción de texto no permite calificar
  pronunciación (ver [Pipeline de IA](#pipeline-de-ia)).

## Cómo funciona una sesión

1. El estudiante se registra (si no tiene cuenta) o inicia sesión.
2. Selecciona su nivel y un escenario precargado.
3. La IA abre la conversación en inglés, asumiendo el rol del escenario.
4. El estudiante responde por turnos; puede pausar y reanudar la sesión.
5. Al cerrar explícitamente la sesión, el sistema analiza la conversación completa.
6. Se genera y muestra el reporte de retroalimentación.
7. El sistema solicita (opcionalmente) una evaluación del estudiante hacia el sistema.
8. Se actualizan las métricas de progreso del estudiante.

Casos de uso de interfaz ya identificados (le sirven al frontend para mapear
componentes y rutas): seleccionar simulación, ingresar audio, pausar/reanudar,
cerrar simulación, completar simulación, configuración (tema claro/oscuro, nivel,
tipo/color/tamaño de fuente, subtítulos on/off), visualizar perfil, editar perfil y
visualizar estadísticas.

## Arquitectura

El sistema se divide en cuatro capas. El frontend **nunca** habla directo con un
proveedor de IA: todo pasa por el backend, que valida los contratos y es dueño de la
persistencia.

```
Navegador (solo PC/laptop) — React / Next.js
  MediaRecorder (captura de voz) · SpeechSynthesis (reproducción)
        │
        │ HTTPS + JSON
        ▼
Backend FastAPI (este repositorio)
  auth · sesiones · retroalimentación · métricas
        │                                  │
        │ SQLAlchemy async                 │ HTTPS
        ▼                                  ▼
SQL Server (persistencia)          Servicios de IA
                                   Groq Whisper (STT)
                                   Gemini 2.0 Flash (LLM)
                                   Respaldo: Groq Llama 3.3 70B
```

| Capa          | Tecnología                                        | Notas                                                                 |
| ------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| Frontend      | React / Next.js                                   | Captura con `MediaRecorder`; reproducción con Web Speech API (`SpeechSynthesis`). Solo escritorio. |
| Backend       | Python + FastAPI                                   | Todo I/O de red con `async`/`await`; contratos de entrada/salida con Pydantic. |
| Base de datos | SQL Server (relacional)                           | Persistencia real vía ORM; sin archivos ni memoria para lo que deba sobrevivir a un reinicio. |
| STT           | Groq Cloud, Whisper-large-v3                       | El audio se recibe en buffer de memoria; no se escribe a disco antes de enviarlo. |
| LLM           | Google AI Studio, Gemini 2.0 Flash (Structured Outputs) | Respaldo: Groq con Llama 3.3 70B, implementado como función intercambiable. |
| TTS           | Web Speech API (nativa del navegador)              | Respaldo: Kokoro TTS o ElevenLabs, solo si la síntesis nativa falla.  |
| Despliegue    | Frontend en Vercel/CDN; backend en la nube          | Sin GPU local ni infraestructura propia especializada.                |

**Principios de diseño:**

- Cada integración externa vive en un módulo aislado, con su propio contrato de
  entrada/salida, timeouts explícitos, reintentos limitados y errores traducidos.
- Cambiar de proveedor de IA (por ejemplo, el respaldo del LLM) no debe requerir tocar
  el frontend ni el esquema de la base de datos.
- Una falla de IA no debe tumbar la sesión sin un mensaje claro para el frontend.

## Pipeline de IA

Cada turno de conversación recorre tres etapas. El backend orquesta las dos primeras;
la tercera ocurre en el navegador.

| Etapa | Servicio                          | Rol en el turno                                                                 |
| ----- | --------------------------------- | ------------------------------------------------------------------------------- |
| STT   | Groq Cloud, Whisper-large-v3      | Convierte el audio del estudiante en texto. El audio viaja como buffer en memoria. |
| LLM   | Gemini 2.0 Flash (respaldo: Groq Llama 3.3 70B) | Genera la respuesta del agente y los datos de retroalimentación en un solo JSON estructurado. |
| TTS   | Web Speech API del navegador      | Reproduce el mensaje del agente. Solo si falla se recurre a Kokoro TTS o ElevenLabs. |

**Requisitos del system prompt** (cuando se implemente el agente, el prompt debe fijar
explícitamente):

- El rol o personaje según el escenario.
- El idioma de respuesta: inglés.
- El nivel MCER seleccionado, para ajustar léxico y gramática.
- El límite de extensión del turno.
- El formato de salida estructurado (JSON) que separa el mensaje conversacional de los
  datos de retroalimentación.

No prometas en el prompt capacidades que el sistema no implementa: evaluación de
pronunciación desde texto, certificación oficial o comparación con hablantes nativos.

## Contrato de datos con el LLM

El LLM debe devolver **siempre** una salida estructurada (JSON) que separe:

- el **mensaje conversacional** que se muestra y reproduce al estudiante, de
- los **datos de retroalimentación** (errores detectados, tipo de error, sugerencia)
  que alimentarán el reporte final.

Antes de usar o persistir cualquier campo, el backend lo valida contra un esquema
Pydantic. Si la respuesta no cumple el esquema:

1. se reintenta con una instrucción de corrección acotada, o
2. se devuelve un error controlado de turno fallido.

Nunca se propaga tal cual al frontend, nunca se falla en silencio y nunca se inventan
campos faltantes.

Ejemplo **ilustrativo** del tipo de respuesta (los nombres definitivos de los campos se
fijan en el esquema Pydantic del dominio de sesiones, no aquí):

```json
{
  "mensaje_conversacional": "That sounds great! Where would you like to sit?",
  "retroalimentacion": {
    "errores": [
      {
        "tipo": "gramatica",
        "entrada": "I want go to the cinema",
        "correccion": "I want to go to the cinema",
        "sugerencia": "Después de 'want' se usa el infinitivo con 'to'."
      }
    ]
  }
}
```

**Limitación que aplica al código y a los prompts:** una transcripción de texto no es
evidencia suficiente para calificar pronunciación. No se implementa ni se promete una
evaluación de pronunciación basada solo en el texto transcrito; esa funcionalidad, si
alguna vez se agrega, requiere análisis de la señal de audio.

## Modelo de datos

Estas son las entidades base del proyecto. Si se agregan campos, los ya listados se
mantienen; no inventes variantes de nombre.

### Usuario

| Campo             | Descripción                                                        |
| ----------------- | ------------------------------------------------------------------ |
| `id_usuario`      | Identificador único de la cuenta.                                  |
| `nombre`          | Nombre del estudiante.                                             |
| `correo`          | Único; identifica la cuenta.                                       |
| `contraseña_hash` | Contraseña hasheada; nunca en claro.                               |
| `rol`             | Por ahora solo `estudiante`.                                       |
| `fecha_registro`  | Alta en el sistema.                                                |

La autenticación es local a la aplicación: **no** hay integración con sistemas
institucionales de la Universidad Veracruzana.

### Sesión

| Campo               | Descripción                                                                 |
| ------------------- | --------------------------------------------------------------------------- |
| `id_sesion`         | Identificador único de la sesión.                                           |
| `id_usuario`        | Estudiante dueño de la sesión.                                              |
| `escenario`         | Escenario precargado elegido.                                               |
| `nivel`             | Nivel MCER seleccionado.                                                    |
| `fecha_inicio`      | Inicio de la sesión; es la base del plazo de 30 días.                       |
| `estado`            | `activa`, `pausada` o `concluida`.                                          |
| `historial`         | Contexto conversacional, necesario para pausar y reanudar.                  |
| `resumen_desempeño` | Resumen de desempeño de la conversación.                                    |
| `evaluacion_sistema`| Evaluación opcional del estudiante hacia el sistema. Se almacena **separada** de la evaluación lingüística del estudiante. |

### Retroalimentación

| Campo                  | Descripción                                     |
| ---------------------- | ----------------------------------------------- |
| `id_retroalimentacion` | Identificador único.                            |
| `id_sesion`            | Sesión a la que pertenece.                      |
| `entrada_usuario`      | Texto transcrito con la corrección.             |
| `correccion_ia`        | Corrección generada por la IA.                  |

### Métricas

| Campo         | Descripción                                     |
| ------------- | ----------------------------------------------- |
| `id_métrica`  | Identificador único del registro agregado.      |
| `id_usuario`  | Estudiante al que pertenece la métrica.         |
| `escenario`   | Escenario de la sesión medida.                  |
| `nivel`       | Nivel MCER de la sesión medida.                 |
| `fecha_inicio`| Fecha de inicio de la sesión medida.            |
| `duracion`    | Duración de la sesión.                          |
| `errores`     | Errores agregados.                              |
| `resumen_ia`  | Resumen generado por la IA.                     |

La tabla de Métricas **se conserva de forma indefinida** (a diferencia de Sesión y
Retroalimentación) y **no debe contener** audio ni el texto completo de la
conversación: solo agregados.

## Reglas de negocio

Se implementan como validaciones en la capa de servicio del backend, no solo se
documentan aquí:

1. Un correo identifica una sola cuenta; toda operación de sesión requiere
   autenticación previa.
2. Una sesión pertenece a un único estudiante y a un escenario precargado válido. Un
   estudiante nunca debe poder leer sesiones de otro: verifica `id_usuario` en cada
   consulta, no solo en el frontend.
3. Una sesión no concluida puede reanudarse solo si han pasado menos de 30 días desde
   `fecha_inicio`; pasado ese plazo, se trata como no disponible.
4. La retroalimentación se genera y entrega únicamente al cerrar la sesión
   explícitamente. No se interrumpen los turnos con retroalimentación parcial.
5. Solo las sesiones marcadas como concluidas contribuyen a Métricas. Las sesiones
   abandonadas o pausadas indefinidamente no se cuentan.
6. Job de depuración: eliminar Sesión, sus turnos y su Retroalimentación al cumplir 30
   días desde su creación, en una operación transaccional (todo o nada) que no afecte
   los registros ya agregados de Métricas.
7. El reporte de retroalimentación es orientativo: el código y los textos generados no
   deben presentarse como certificación o acreditación oficial de nivel MCER.

## Requisitos no funcionales

- **Latencia por turno:** STT + LLM + TTS en 3–5 segundos. Si una etapa es lenta,
  considera streaming solo donde el proveedor lo soporte realmente; "asíncrono" por sí
  solo no reduce la latencia percibida.
- **Latencia del reporte:** parseado y desplegado en menos de 8 segundos tras cerrar
  la sesión.
- **Concurrencia:** diseñar para pocos usuarios concurrentes. La capa gratuita de los
  servicios de IA impone límites de peticiones por minuto/día y de tokens; no
  dimensiones el sistema para carga alta sin advertir esta limitación.
- **Desacoplamiento:** un cambio de proveedor de IA no debe requerir modificar el
  frontend ni el esquema de la base de datos.

## Estado actual

El repositorio es la **infraestructura del backend**, no el dominio terminado. Esto es
lo que existe hoy y lo que falta:

| Área                    | Módulo               | Estado      | Detalle                                                                                       |
| ----------------------- | -------------------- | ----------- | --------------------------------------------------------------------------------------------- |
| Autenticación           | `src/auth/`          | Implementado | Registro, login, rotación de tokens, logout y perfil. Argon2 + PyJWT.                          |
| Acceso a datos          | `src/datasources/`   | Implementado | `Repository[T]` genérico sobre `AsyncSession`, registro de datasources y dependencia de sesión. |
| Cliente de IA           | `src/ai/`            | Parcial     | Cliente DeepSeek async con mapeo de errores y `POST /ai/chat` sin persistencia. Falta la orquestación del agente (prompt por escenario/nivel, salida estructurada y validación). |
| Salud                   | `src/health/`        | Implementado | Sondas de *liveness* y *readiness* con verificación real de la base de datos.                  |
| Migraciones             | `migrations/`        | Implementado | Alembic asíncrono; migraciones estáticas y reversibles.                                        |
| Persistencia            | `src/database.py`    | Parcial     | SQLite para desarrollo. Falta migrar a SQL Server (driver ODBC async, tipos y migraciones).    |
| Dominio: sesiones       | —                    | Pendiente   | Entidad `Sesión`, turnos, historial, pausa/reanudación y regla de 30 días.                     |
| STT                     | —                    | Pendiente   | Endpoint que reciba el audio en memoria y lo envíe a Groq Whisper.                             |
| TTS                     | —                    | Pendiente   | Web Speech API en el frontend; respaldo Kokoro TTS o ElevenLabs si la nativa falla.             |
| Retroalimentación       | —                    | Pendiente   | Generación al cierre de la sesión, validada contra un esquema Pydantic, en menos de 8 s.       |
| Métricas                | —                    | Pendiente   | Agregados sin audio ni texto completo de la conversación.                                      |
| Job de depuración       | —                    | Pendiente   | Borrado transaccional de sesiones, turnos y retroalimentación a los 30 días.                    |
| Pruebas                 | `tests/`             | Implementado | 53 pruebas; no tocan la red ni el archivo real de base de datos.                               |

**Siguiente paso sugerido:** crear el dominio `src/sesion/` con las entidades del
[modelo de datos](#modelo-de-datos) y las [reglas de negocio](#reglas-de-negocio),
siguiendo la receta de [Cómo agregar un dominio](#cómo-agregar-un-dominio). Después
vienen el STT, la orquestación del LLM con salida estructurada, la retroalimentación,
las métricas y el job de depuración; el cambio a SQL Server conviene hacerlo antes de
producción.

## Requisitos

- **Python 3.11 o superior** — obligatorio para `StrEnum` y la sintaxis `X | Y`.
  (SQLAlchemy 2.1 también lo exige).
- **[uv](https://docs.astral.sh/uv/)** — gestor de paquetes y entorno virtual.
- **Una API key de DeepSeek** — solo si vas a usar `POST /ai/chat`, que es el cliente
  de IA que existe hoy. Consíguela en
  [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys). El resto
  del proyecto funciona sin ella.
- **Claves de Groq y Google AI Studio** — harán falta cuando se implementen el STT y el
  LLM del pipeline del simulador (ver [Pipeline de IA](#pipeline-de-ia)).

## Instalación

```shell
# 1. Instalar dependencias (crea .venv y actualiza uv.lock)
uv sync --all-extras

# 2. Crear el archivo de entorno
cp .env.example .env
```

Después edita `.env` y rellena como mínimo estos tres valores:

| Variable                 | Para qué sirve                                                              |
| ------------------------ | --------------------------------------------------------------------------- |
| `AUTH_JWT_SECRET`        | Clave de firma de los access tokens.                                        |
| `AUTH_REFRESH_TOKEN_KEY` | Clave de firma de los refresh tokens. **Debe ser distinta** de la anterior. |
| `DEEPSEEK_API_KEY`       | Únicamente para llamar a los endpoints de IA.                               |

Genera claves aleatorias con:

```shell
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> Las variables de entorno reales tienen prioridad sobre los valores de `.env`, así
> que puedes sobreescribir cualquier cosa desde la terminal sin tocar el archivo.

## Configuración

Todas las variables disponibles en `.env.example`:

### Aplicación

| Variable       | Por defecto                     | Descripción                                                          |
| -------------- | ------------------------------- | -------------------------------------------------------------------- |
| `ENVIRONMENT`  | `local`                         | Entorno actual. Solo `local` y `staging` muestran `/docs` y `/redoc`. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./cosa.db` | Cadena de conexión async. Cambia la ruta del archivo SQLite.         |
| `SQL_ECHO`     | `false`                         | Si es `true`, loguea todas las sentencias SQL. Útil para depurar.    |

### Autenticación (`prefijo AUTH_`)

| Variable                 | Por defecto  | Descripción                                                     |
| ------------------------ | ------------ | --------------------------------------------------------------- |
| `AUTH_JWT_ALG`           | `HS256`      | Algoritmo de firma.                                             |
| `AUTH_JWT_SECRET`        | *(inseguro)* | Clave de firma de los access tokens. Mínimo 32 bytes.           |
| `AUTH_JWT_EXP_MINUTES`   | `5`          | Vigencia del access token.                                      |
| `AUTH_REFRESH_TOKEN_KEY` | *(inseguro)* | Clave de firma de los refresh tokens. Distinta de la anterior.  |
| `AUTH_REFRESH_TOKEN_EXP` | `30d`        | Vigencia del refresh token. Acepta `30d`, `12h`, `90m`, etc.    |
| `AUTH_SECURE_COOKIES`    | `true`       | `false` en local, porque `Secure` impide cookies por HTTP plano. |

> Los valores por defecto de las dos claves existen para que `import src.main` no
> reviente sin un `.env`, pero **no son seguros para producción**. Configúralas
> siempre.

### DeepSeek (`prefijo DEEPSEEK_`)

| Variable                    | Por defecto                | Descripción                                          |
| --------------------------- | -------------------------- | ---------------------------------------------------- |
| `DEEPSEEK_API_KEY`          | *(vacío)*                  | Sin valor, los endpoints de IA responden `503`.      |
| `DEEPSEEK_BASE_URL`         | `https://api.deepseek.com` | Endpoint de la API.                                  |
| `DEEPSEEK_MODEL`            | `deepseek-flash`           | `deepseek-flash` o `deepseek-v4-pro`.                |
| `DEEPSEEK_THINKING`         | `false`                    | Activa el modo razonador por defecto.                |
| `DEEPSEEK_REASONING_EFFORT` | `medium`                   | `low`, `medium` o `high`. Solo aplica con `THINKING`. |
| `DEEPSEEK_TIMEOUT_SECONDS`  | `60`                       | Timeout de la petición HTTP.                         |
| `DEEPSEEK_MAX_TOKENS`       | `2048`                     | Máximo de tokens de la respuesta.                    |
| `DEEPSEEK_TEMPERATURE`      | `1.0`                      | Temperatura de muestreo (0–2).                       |

> Cada proveedor de IA tiene su propia `BaseSettings` por dominio. Cuando integres
> Gemini o Groq, crea su configuración con prefijo propio (por ejemplo `GEMINI_`,
> `GROQ_`) en lugar de mezclar variables con `DEEPSEEK_`.

## Ejecutar el proyecto

```shell
# 1. Crear (o actualizar) el esquema de la base de datos
uv run alembic upgrade head

# 2. Levantar el servidor en modo recarga
uv run uvicorn src.main:app --reload
```

La API queda disponible en <http://127.0.0.1:8000> y la documentación interactiva en
<http://127.0.0.1:8000/docs> (solo en `local` y `staging`; en cualquier otro entorno
`openapi_url` queda en `None` y no se expone).

Comprobación rápida:

```shell
curl localhost:8000/health
# {"status":"ok","environment":"local"}
```

## API

Endpoints de infraestructura que existen hoy. Los del simulador (sesiones, turnos,
retroalimentación, métricas) se montarán encima del dominio correspondiente.

| Método | Ruta            | Auth  | Descripción                                            |
| ------ | --------------- | ----- | ------------------------------------------------------ |
| `GET`  | `/health`       | —     | Sonda de vida. No toca la base de datos.               |
| `GET`  | `/ready`        | —     | Sonda de disponibilidad. Ejecuta `SELECT 1`.           |
| `POST` | `/auth/signup`  | —     | Registra un usuario. Responde `201`.                   |
| `POST` | `/auth/login`   | —     | Intercambia credenciales por tokens.                   |
| `POST` | `/auth/refresh` | Cookie | Rota el par de tokens usando la cookie de refresh.     |
| `POST` | `/auth/logout`  | —     | Limpia la cookie de refresh. Responde `204`.           |
| `GET`  | `/auth/me`      | Token | Devuelve el usuario autenticado.                       |
| `POST` | `/ai/chat`      | Token | Proxy a DeepSeek. No persiste nada.                    |

Token = `Authorization: Bearer <access_token>` · Cookie = cookie `refresh_token`

### Recorrido completo con `curl`

```shell
# 1. Registrarse (guarda la cookie de refresh)
curl -X POST localhost:8000/auth/signup \
  -H 'Content-Type: application/json' \
  -c cookies.txt \
  -d '{"email":"kenia@example.com","username":"kenia","password":"correct-horse-battery"}'

# 2. Iniciar sesión y guardar el access token en una variable
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -c cookies.txt \
  -d '{"email":"kenia@example.com","password":"correct-horse-battery"}' \
  | jq -r .access_token)

# 3. Consultar el perfil
curl localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"

# 4. Preguntarle a DeepSeek
curl -X POST localhost:8000/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hola, ¿qué es una cosa?"}]}'

# 5. Renovar el access token usando la cookie
curl -X POST localhost:8000/auth/refresh -b cookies.txt -c cookies.txt
```

### Formato de los errores

Todos los errores de dominio usan la misma forma, gracias a un único manejador de
excepciones registrado en `src/main.py`:

```json
{
  "detail": {
    "code": "user_already_exists",
    "message": "A user with that email or username already exists."
  }
}
```

El campo `code` es estable y pensado para que el frontend lo use; `message` es para
personas. Códigos que puedes encontrar:

| `code`                 | HTTP | Significado                                          |
| ---------------------- | ---- | ---------------------------------------------------- |
| `invalid_credentials`  | 401  | Email o contraseña incorrectos.                      |
| `invalid_token`        | 401  | Token ausente, mal formado, expirado o de otro tipo. |
| `user_already_exists`  | 409  | El email o el username ya están registrados.         |
| `user_not_found`       | 404  | El token es válido pero el usuario ya no existe.     |
| `user_not_active`      | 403  | Cuenta desactivada.                                  |
| `ai_not_configured`    | 503  | Falta `DEEPSEEK_API_KEY` en el servidor.             |
| `ai_rate_limited`      | 429  | DeepSeek limitó la tasa. Incluye `Retry-After`.      |
| `ai_request_rejected`  | 502  | DeepSeek rechazó la petición.                        |
| `ai_invalid_response`  | 502  | La respuesta de DeepSeek no se pudo interpretar.     |
| `ai_upstream_error`    | 502  | DeepSeek no está disponible o falló.                 |
| `ai_timeout`           | 504  | DeepSeek no respondió a tiempo.                      |
| `database_unavailable` | 503  | La base de datos no responde.                        |

## Base de datos y migraciones

El esquema se gestiona **solo con Alembic**; la aplicación no crea tablas al arrancar.
El archivo SQLite (`cosa.db`) se genera en el primer `alembic upgrade head`.

```shell
uv run alembic upgrade head                            # aplicar todo
uv run alembic downgrade -1                            # revertir el último paso
uv run alembic downgrade base                          # vaciar el esquema
uv run alembic revision --autogenerate -m "add sesion" # crear una migración
uv run alembic history                                 # ver el historial
uv run alembic current                                 # ver la versión aplicada
```

La URL de la base de datos **no está en `alembic.ini`**: `migrations/env.py` la toma de
la configuración de la aplicación, de modo que la app y las migraciones nunca pueden
apuntar a bases de datos distintas.

> **SQLite y ALTER TABLE.** SQLite no soporta la mayoría de los `ALTER TABLE`, así que
> `env.py` activa `render_as_batch=True`. Alembic emula esas operaciones creando una
> tabla nueva y copiando los datos. No lo desactives.

> **Claves foráneas.** SQLite las ignora por defecto. `src/database.py` ejecuta
> `PRAGMA foreign_keys=ON` en cada conexión nueva. Si añades claves foráneas y notas
> que no se aplican, revisa ese `PRAGMA` antes que tus modelos.

> **Camino a SQL Server.** El proyecto de referencia persiste en SQL Server. Al migrar
> tendrás que cambiar el driver async (por ejemplo `mssql+aioodbc`), revisar tipos y
> regenerar o ajustar las migraciones; el acceso a datos ya está aislado en
> `src/datasources/` y `src/database.py`, pero el cambio no es solo de URL.

## Pruebas

```shell
uv run pytest              # 53 pruebas
uv run pytest -v           # con nombres
uv run pytest tests/auth   # solo un módulo
```

| Módulo                           | Pruebas | Qué cubre                                            |
| -------------------------------- | ------- | ---------------------------------------------------- |
| `tests/auth/test_auth_routes.py` | 18      | Signup, login, refresh, logout, `/me`, conflictos.   |
| `tests/auth/test_security.py`    | 10      | Hashing, expiración, rotación de claves, `type`/`jti`. |
| `tests/test_ai.py`               | 14      | Payload enviado, modo razonador, cada código de error. |
| `tests/test_datasources.py`      | 9       | CRUD del repositorio, registro de datasources.       |
| `tests/test_health.py`           | 2       | Sondas de vida y disponibilidad.                     |

Dos detalles importantes sobre el diseño de las pruebas:

- **No tocan la red.** DeepSeek se simula con `httpx.MockTransport`, así que la suite
  corre sin `DEEPSEEK_API_KEY` y sin coste.
- **No usan el archivo real.** SQLite en memoria con `StaticPool` (ver
  `tests/conftest.py`). Cada prueba parte de un esquema limpio.

> Las pruebas fijan las variables de entorno en `tests/__init__.py`, que se ejecuta
> **antes** de que se importe nada de `src/`. Si añades una variable obligatoria a
> alguna config, considéralo o las pruebas fallarán al importar la app.

> Cuando implementes el dominio del simulador, prueba las reglas de negocio contra una
> base de datos real (por ejemplo SQL Server en un contenedor o esquema efímero), no
> solo con mocks: las reglas de propiedad de sesión, el plazo de 30 días y el job de
> depuración dependen del motor.

## Lint y formato

```shell
uv run ruff check src tests migrations            # detectar problemas
uv run ruff check --fix src tests migrations      # corregir lo corregible
uv run ruff format src tests migrations           # formatear
uv run ruff format --check src tests migrations   # verificar sin escribir
```

Ruff sustituye a `black` + `isort` + `flake8`. La configuración vive en
`pyproject.toml`, bajo `[tool.ruff.lint]`.

## Estructura del proyecto

```
cosa-backend/
├── AGENTS.md                    Convenciones que sigue el proyecto
├── pyproject.toml               Dependencias y configuración de ruff/pytest
├── alembic.ini                  Configuración de Alembic (la URL vive en el código)
├── .env.example                 Plantilla de configuración
├── migrations/
│   ├── env.py                   Entorno asíncrono; importa los modelos
│   └── versions/                Migraciones reversibles
├── src/
│   ├── main.py                  App, lifespan, manejador de errores, routers
│   ├── config.py                BaseSettings global
│   ├── models.py                Base declarativa, naming convention, CustomModel
│   ├── database.py              Engine async, session factory, PRAGMAs de SQLite
│   ├── exceptions.py            AppError + esquema de respuesta de error
│   ├── datasources/
│   │   ├── base.py              Repository[T] genérico
│   │   ├── registry.py          Registro nombre → repositorio
│   │   └── dependencies.py      DbSession
│   ├── auth/
│   │   ├── config.py            AuthConfig (prefijo AUTH_)
│   │   ├── constants.py         Tipos de token
│   │   ├── exceptions.py        Errores del dominio
│   │   ├── models.py            Tabla user
│   │   ├── schemas.py           UserCreate, UserLogin, UserRead, TokenPair
│   │   ├── security.py          Argon2 + PyJWT
│   │   ├── repository.py        UserRepository(Repository[User])
│   │   ├── service.py           Lógica de negocio; controla las transacciones
│   │   ├── dependencies.py      parse_jwt_data, CurrentUser
│   │   └── router.py            Rutas
│   ├── ai/
│   │   ├── config.py            AIConfig (prefijo DEEPSEEK_)
│   │   ├── constants.py         Ruta del endpoint
│   │   ├── exceptions.py        Errores del dominio
│   │   ├── schemas.py           ChatRequest, ChatResponse, TokenUsage
│   │   ├── client.py            DeepSeekClient sobre httpx
│   │   ├── service.py           complete_chat
│   │   ├── dependencies.py      AIClient
│   │   └── router.py            Rutas
│   └── health/
│       ├── exceptions.py        DatabaseUnavailable
│       ├── schemas.py           HealthStatus, ReadinessStatus
│       └── router.py            Sondas
└── tests/
    ├── __init__.py              Variables de entorno para las pruebas
    ├── conftest.py              Engine en memoria, overrides, cliente HTTP
    ├── factories.py             Datos de prueba
    ├── helpers.py               register(), auth_headers()
    ├── auth/
    ├── test_ai.py
    ├── test_datasources.py
    └── test_health.py
```

## Convenciones importantes

Estas son las reglas del proyecto que más conviene no romper. La lista completa está
en [`AGENTS.md`](./AGENTS.md).

**Dependencias**

- `Annotated[T, Depends(...)]`, nunca `x: T = Depends(...)`.
- `async def` para rutas y dependencias. Si necesitas algo bloqueante, envíalo a
  `run_in_threadpool`; nunca bloquees el event loop.

**Base de datos**

- Los repositorios llaman `flush()`, **nunca `commit()`**. El servicio cierra la
  transacción, de modo que una llamada al servicio es una unidad atómica.
- Los nombres de tabla van en singular: `user`, `sesion`, `retroalimentacion`.
- Todo `ForeignKey` se llama igual en cada tabla donde aparece (`id_usuario` siempre es
  `id_usuario`).

**IA**

- `httpx` siempre asíncrono. `requests` está prohibido dentro de `async def`.
- Nunca `except Exception` alrededor del cuerpo de una ruta: lanza la excepción
  específica del dominio y deja que el manejador global la formatee.
- El frontend nunca llama directo a un proveedor de IA: pasa por el backend.
- La retroalimentación que devuelve el LLM se valida contra un esquema Pydantic antes
  de usarse o persistirse.

**Modelos**

- `datetime` naive se asume UTC. `CustomModel` lo normaliza al serializar.
- Pydantic v2: `@field_serializer`, no `json_encoders`.
- Nunca `Field(ge=18, default=None)`. O es obligatorio (`Field(ge=18)`) u opcional
  (`int | None = Field(default=None, ge=18)`).

**Dominio del simulador**

- Usa los nombres de campos y entidades del [modelo de datos](#modelo-de-datos)
  (`id_sesion`, `id_usuario`, `escenario`, `nivel`, `fecha_inicio`, `estado`, …); no
  inventes variantes en inglés.
- Las [reglas de negocio](#reglas-de-negocio) se implementan en la capa de servicio,
  no solo se describen en comentarios.
- No prometas evaluación de pronunciación desde texto en prompts ni en respuestas.

## Cómo agregar un dominio

El siguiente dominio a construir es el de **sesiones** (`src/sesion/`), que agrupa la
conversación, su historial, su estado (`activa`/`pausada`/`concluida`) y su cierre. La
receta es la misma para cualquier dominio nuevo.

**1. Crea el paquete** `src/sesion/` con los archivos que necesite: `models.py`,
`schemas.py`, `repository.py`, `service.py`, `dependencies.py`, `router.py`.

**2. Hereda el repositorio genérico** en vez de escribir el CRUD a mano:

```python
from src.datasources.base import Repository

from src.sesion.models import Sesion


class SesionRepository(Repository[Sesion]):
    model = Sesion
```

**3. Regístralo** en `src/main.py`, dentro de `register_datasources()`:

```python
from src.sesion.repository import SesionRepository

registry.register("sesion", SesionRepository)
```

**4. Genera la migración:**

```shell
uv run alembic revision --autogenerate -m "add sesion"
```

> Autogenerate necesita que tu modelo esté importado en
> `migrations/env.py` (la lista `MODEL_MODULES`). Si te olvidas, Alembic no verá la
> tabla y generará una migración vacía.

**5. Monta el router** en `src/main.py`:

```python
from src.sesion import router as sesion_router

app.include_router(sesion_router.router)
```

**6. Escribe las pruebas** en `tests/sesion/`, usando los fixtures `client` y
`session`.

**Ejemplo de servicio** — recuerda: el repositorio hace `flush()`, el servicio hace
`commit()`:

```python
async def create_sesion(session: AsyncSession, data: SesionCreate) -> Sesion:
    sesiones = SesionRepository(session)
    sesion = await sesiones.create(**data.model_dump())
    await session.commit()
    return sesion
```

**Checklist antes de dar por terminado un dominio:**

- ¿El endpoint valida entrada y salida con modelos Pydantic, sin dicts sueltos?
- ¿Respeta la separación de capas, sin que el frontend hable directo con un servicio
  de IA?
- ¿Aísla las llamadas a servicios externos de forma que cambiar de proveedor no rompa
  otras partes?
- ¿Aplica las [reglas de negocio](#reglas-de-negocio) en el servicio, no solo las
  describe?
- ¿Usa los nombres de campos y entidades del [modelo de datos](#modelo-de-datos)?

## Problemas frecuentes

**`ModuleNotFoundError: No module named 'src'`**
El proyecto no está instalado. Ejecuta `uv sync --all-extras`.

**`no such table: user`**
Faltó aplicar las migraciones. Ejecuta `uv run alembic upgrade head`.

**`POST /ai/chat` devuelve `503 ai_not_configured`**
`DEEPSEEK_API_KEY` está vacía o no llegó al proceso. Recuerda que las variables de
entorno tienen prioridad sobre `.env`: si exportaste la variable antes de tener la
clave, elimínala de la sesión (`unset DEEPSEEK_API_KEY`) y reinicia el servidor.

**`401 invalid_token` en `/auth/refresh`**
La cookie `refresh_token` no viaja. Si usas un cliente que no guarda cookies, pásala
a mano. Recuerda también que un access token **no** sirve como refresh token: los dos
tipos están firmados con claves distintas y llevan un claim `type` que se valida.

**Las cookies no se guardan en local**
`AUTH_SECURE_COOKIES` debe ser `false` en desarrollo. Con `true`, el navegador
descarta la cookie porque la conexión no es HTTPS.

**El login falla aunque la contraseña sea correcta**
Si el usuario quedó con una fila creada por una versión anterior del esquema, su
`hashed_password` puede tener otro formato. argon2 no lanza `ValueError` ante un hash
corrupto sino `UnknownHashError`; `verify_password` ya la captura y devuelve `False`.

**`autogenerate` no detecta mi tabla nueva**
Añade el módulo a `MODEL_MODULES` en `migrations/env.py` y vuelve a intentarlo.

**No sé por dónde empezar con el dominio**
Revisa [Estado actual](#estado-actual) y la skill del proyecto; el primer hito es
`src/sesion/` siguiendo [Cómo agregar un dominio](#cómo-agregar-un-dominio).

**Quiero empezar de cero con la base de datos**

```shell
rm -f cosa.db cosa.db-wal cosa.db-shm
uv run alembic upgrade head
```

## Referencias

- [`AGENTS.md`](./AGENTS.md) — convenciones de FastAPI y de código que sigue el
  repositorio (versiones, estructura, dependencias, pruebas, migraciones).
- [Skill `simulador-conversacional-ia-dev`](./.opencode/skills/simulador-conversacional-ia-dev/SKILL.md)
  — especificación del proyecto: alcance, stack fijo, pipeline de IA, modelo de datos,
  reglas de negocio y requisitos no funcionales.
- [`.env.example`](./.env.example) — plantilla comentada de variables de entorno.
