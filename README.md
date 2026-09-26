# cosa-backend

Backend base construido con **FastAPI**, **SQLite** (SQLAlchemy 2.0 asíncrono) y la
**API de DeepSeek**, siguiendo las convenciones definidas en [`AGENTS.md`](./AGENTS.md).

> **Todavía no existe un dominio de negocio.** "cosa" es un nombre genérico y
> provisorio. Lo que hay es toda la infraestructura que un dominio necesitará:
> acceso a datos, autenticación, cliente de IA y observabilidad de salud. Cuando
> sepas qué quieres construir, añades un dominio nuevo encima (ver
> [Agregar un dominio](#agregar-un-dominio)).

## Contenido

- [Qué hay dentro](#qué-hay-dentro)
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
- [Agregar un dominio](#agregar-un-dominio)
- [Problemas frecuentes](#problemas-frecuentes)

## Qué hay dentro

| Módulo              | Qué resuelve                                                                                                                                          |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/datasources/`  | Repositorio genérico `Repository[T]` sobre `AsyncSession`, un registro de datasources y la dependencia de sesión. Sin lógica de negocio.              |
| `src/auth/`         | Autenticación JWT completa: registro, login, rotación de tokens, logout y perfil. Contraseñas con Argon2.                                            |
| `src/ai/`           | Cliente de DeepSeek sobre `httpx.AsyncClient` con mapeo de errores, y un endpoint delgado `POST /ai/chat` que no persiste nada.                          |
| `src/health/`       | Sondas de *liveness* (`/health`) y *readiness* (`/ready`) con verificación real de la base de datos.                                                   |
| `migrations/`       | Entorno Alembic asíncrono. Las migraciones son estáticas y reversibles.                                                                              |

## Requisitos

- **Python 3.11 o superior** — obligatorio para `StrEnum` y la sintaxis `X | Y`.
  (SQLAlchemy 2.1 también lo exige).
- **[uv](https://docs.astral.sh/uv/)** — gestor de paquetes y entorno virtual.
- **Una API key de DeepSeek** — solo si vas a usar `POST /ai/chat`. Consíguela en
  [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys). El resto
  del proyecto funciona sin ella.

## Instalación

```shell
# 1. Instalar dependencias (crea .venv y actualiza uv.lock)
uv sync --all-extras

# 2. Crear el archivo de entorno
cp .env.example .env
```

Después edita `.env` y rellena como mínimo estos tres valores:

| Variable                | Para qué sirve                                                  |
| ----------------------- | --------------------------------------------------------------- |
| `AUTH_JWT_SECRET`       | Clave de firma de los access tokens.                            |
| `AUTH_REFRESH_TOKEN_KEY` | Clave de firma de los refresh tokens. **Debe ser distinta** de la anterior. |
| `DEEPSEEK_API_KEY`      | Únicamente para llamar a los endpoints de IA.                   |

Genera claves aleatorias con:

```shell
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> Las variables de entorno reales tienen prioridad sobre los valores de `.env`, así
> que puedes sobreescribir cualquier cosa desde la terminal sin tocar el archivo.

## Configuración

Todas las variables disponibles en `.env.example`:

### Aplicación

| Variable       | Por defecto                    | Descripción                                                          |
| -------------- | ------------------------------ | -------------------------------------------------------------------- |
| `ENVIRONMENT`  | `local`                        | Entorno actual. Solo `local` y `staging` muestran `/docs` y `/redoc`. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./cosa.db` | Cadena de conexión async. Cambia la ruta del archivo SQLite.         |
| `SQL_ECHO`     | `false`                        | Si es `true`, loguea todas las sentencias SQL. Útil para depurar.    |

### Autenticación (`prefijo AUTH_`)

| Variable                  | Por defecto      | Descripción                                                        |
| ------------------------- | ---------------- | ------------------------------------------------------------------ |
| `AUTH_JWT_ALG`            | `HS256`          | Algoritmo de firma.                                                 |
| `AUTH_JWT_SECRET`         | *(inseguro)*     | Clave de firma de los access tokens. Mínimo 32 bytes.               |
| `AUTH_JWT_EXP_MINUTES`    | `5`              | Vigencia del access token.                                          |
| `AUTH_REFRESH_TOKEN_KEY`  | *(inseguro)*     | Clave de firma de los refresh tokens. Distinta de la anterior.      |
| `AUTH_REFRESH_TOKEN_EXP`  | `30d`            | Vigencia del refresh token. Acepta `30d`, `12h`, `90m`, etc.        |
| `AUTH_SECURE_COOKIES`     | `true`           | `false` en local, porque `Secure` impide cookies por HTTP plano.    |

> Los valores por defecto de las dos claves existen para que `import src.main` no
> reviente sin un `.env`, pero **no son seguros para producción**. Configúralas
> siempre.

### DeepSeek (`prefijo DEEPSEEK_`)

| Variable                       | Por defecto                    | Descripción                                              |
| ------------------------------ | ------------------------------ | -------------------------------------------------------- |
| `DEEPSEEK_API_KEY`             | *(vacío)*                      | Sin valor, los endpoints de IA responden `503`.           |
| `DEEPSEEK_BASE_URL`            | `https://api.deepseek.com`     | Endpoint de la API.                                       |
| `DEEPSEEK_MODEL`               | `deepseek-flash`               | `deepseek-flash` o `deepseek-v4-pro`.                    |
| `DEEPSEEK_THINKING`            | `false`                        | Activa el modo razonador por defecto.                    |
| `DEEPSEEK_REASONING_EFFORT`    | `medium`                       | `low`, `medium` o `high`. Solo aplica con `THINKING`.      |
| `DEEPSEEK_TIMEOUT_SECONDS`     | `60`                           | Timeout de la petición HTTP.                              |
| `DEEPSEEK_MAX_TOKENS`          | `2048`                         | Máximo de tokens de la respuesta.                         |
| `DEEPSEEK_TEMPERATURE`         | `1.0`                          | Temperatura de muestreo (0–2).                            |

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

| Método | Ruta            | Auth  | Descripción                                            |
| ------ | --------------- | ----- | ------------------------------------------------------ |
| `GET`  | `/health`       | —     | Sonda de vida. No toca la base de datos.               |
| `GET`  | `/ready`        | —     | Sonda de disponibilidad. Ejecuta `SELECT 1`.           |
| `POST` | `/auth/signup`  | —     | Registra un usuario. Responde `201`.                   |
| `POST` | `/auth/login`   | —     | Intercambia credenciales por tokens.                   |
| `POST` | `/auth/refresh` | 🍪    | Rota el par de tokens usando la cookie de refresh.     |
| `POST` | `/auth/logout`  | —     | Limpia la cookie de refresh. Responde `204`.           |
| `GET`  | `/auth/me`      | 🔑    | Devuelve el usuario autenticado.                       |
| `POST` | `/ai/chat`      | 🔑    | Proxy a DeepSeek. No persiste nada.                    |

🔑 Requiere `Authorization: Bearer <access_token>` · 🍪 Requiere la cookie `refresh_token`

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

| `code`                 | HTTP | Significado                                     |
| ---------------------- | ---- | ----------------------------------------------- |
| `invalid_credentials`  | 401  | Email o contraseña incorrectos.                 |
| `invalid_token`        | 401  | Token ausente, mal formado, expirado o de otro tipo. |
| `user_already_exists`  | 409  | El email o el username ya están registrados.    |
| `user_not_found`       | 404  | El token es válido pero el usuario ya no existe. |
| `user_not_active`      | 403  | Cuenta desactivada.                             |
| `ai_not_configured`    | 503  | Falta `DEEPSEEK_API_KEY` en el servidor.        |
| `ai_rate_limited`      | 429  | DeepSeek limitó la tasa. Incluye `Retry-After`.  |
| `ai_request_rejected`  | 502  | DeepSeek rechazó la petición.                   |
| `ai_invalid_response`  | 502  | La respuesta de DeepSeek no se pudo interpretar. |
| `ai_upstream_error`    | 502  | DeepSeek no está disponible o falló.            |
| `ai_timeout`           | 504  | DeepSeek no respondió a tiempo.                 |
| `database_unavailable` | 503  | La base de datos no responde.                   |

## Base de datos y migraciones

El esquema se gestiona **solo con Alembic**; la aplicación no crea tablas al arrancar.
El archivo SQLite (`cosa.db`) se genera en el primer `alembic upgrade head`.

```shell
uv run alembic upgrade head                                # aplicar todo
uv run alembic downgrade -1                                # revertir el último paso
uv run alembic downgrade base                              # vaciar el esquema
uv run alembic revision --autogenerate -m "add posts"      # crear una migración
uv run alembic history                                     # ver el historial
uv run alembic current                                     # ver la versión aplicada
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

## Pruebas

```shell
uv run pytest              # 53 pruebas
uv run pytest -v           # con nombres
uv run pytest tests/auth   # solo un módulo
```

| Módulo                        | Pruebas | Qué cubre                                        |
| ----------------------------- | ------- | ------------------------------------------------ |
| `tests/auth/test_auth_routes.py` | 18    | Signup, login, refresh, logout, `/me`, conflictos. |
| `tests/auth/test_security.py`   | 10    | Hashing, expiración, rotación de claves, `type`/`jti`. |
| `tests/test_ai.py`             | 14    | Payload enviado, modo razonador, cada código de error. |
| `tests/test_datasources.py`    |  9    | CRUD del repositorio, registro de datasources.   |
| `tests/test_health.py`         |  2    | Sondas de vida y disponibilidad.                 |

Dos detalles importantes sobre el diseño de las pruebas:

- **No tocan la red.** DeepSeek se simula con `httpx.MockTransport`, así que la suite
  corre sin `DEEPSEEK_API_KEY` y sin coste.
- **No usan el archivo real.** SQLite en memoria con `StaticPool` (ver
  `tests/conftest.py`). Cada prueba parte de un esquema limpio.

> Las pruebas fijan las variables de entorno en `tests/__init__.py`, que se ejecuta
> **antes** de que se importe nada de `src/`. Si añades una variable obligatoria a
  alguna config, considéralo o las pruebas fallarán al importar la app.

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
- Los nombres de tabla van en singular: `user`, `post`, `post_like`.
- Todo `ForeignKey` se llama igual en cada tabla donde aparece.

**IA**

- `httpx` siempre asíncrono. `requests` está prohibido dentro de `async def`.
- Nunca `except Exception` alrededor del cuerpo de una ruta: lanza la excepción
  específica del dominio y deja que el manejador global la formatee.

**Modelos**

- `datetime` naive se asume UTC. `CustomModel` lo normaliza al serializar.
- Pydantic v2: `@field_serializer`, no `json_encoders`.
- Nunca `Field(ge=18, default=None)`. O es obligatorio (`Field(ge=18)`) u opcional
  (`int | None = Field(default=None, ge=18)`).

## Agregar un dominio

Cuando sepas qué quieres construir, sigue estos pasos.

**1. Crea el paquete** `src/{dominio}/` con los archivos que necesite: `models.py`,
`schemas.py`, `repository.py`, `service.py`, `dependencies.py`, `router.py`.

**2. Hereda el repositorio genérico** en vez de escribir el CRUD a mano:

```python
from src.datasources.base import Repository

from src.posts.models import Post


class PostRepository(Repository[Post]):
    model = Post
```

**3. Regístralo** en `src/datasources/registry.py`:

```python
from src.posts.repository import PostRepository

registry.register("post", PostRepository)
```

**4. Genera la migración:**

```shell
uv run alembic revision --autogenerate -m "add posts"
```

> Autogenerate necesita que tu modelo esté importado en
> `migrations/env.py` (la lista `MODEL_MODULES`). Si te olvidas, Alembic no verá la
> tabla y generará una migración vacía.

**5. Monta el router** en `src/main.py`:

```python
from src.posts import router as posts_router

app.include_router(posts_router.router)
```

**6. Escribe las pruebas** en `tests/test_posts.py`, usando los fixtures `client` y
`session`.

**Ejemplo de servicio** — recuerda: el repositorio hace `flush()`, el servicio hace
`commit()`:

```python
async def create_post(session: AsyncSession, data: PostCreate) -> Post:
    posts = PostRepository(session)
    post = await posts.create(**data.model_dump(), author_id=data.author_id)
    await session.commit()
    return post
```

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

**Quiero empezar de cero con la base de datos**
```shell
rm -f cosa.db cosa.db-wal cosa.db-shm
uv run alembic upgrade head
```
