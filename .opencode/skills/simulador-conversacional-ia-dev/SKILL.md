---
name: simulador-conversacional-ia-dev
description: >
  Usar esta skill siempre que se desarrolle, implemente, depure o extienda
  código para el "Simulador conversacional en inglés basado en IA" de la
  Facultad de Idiomas de la Universidad Veracruzana: backend en Python con
  FastAPI, frontend en React/Next.js, base de datos SQL Server, e
  integración con servicios externos de IA (Speech-to-Text, LLM,
  Text-to-Speech). Activar ante peticiones como: crear un endpoint,
  microservicio o modelo de datos del proyecto; implementar la captura de
  audio con MediaRecorder; escribir o ajustar el prompt/system prompt del
  agente conversacional; validar o parsear la salida JSON del LLM;
  implementar el flujo de sesión (iniciar, pausar, reanudar, cerrar);
  generar el reporte de retroalimentación; construir el job de depuración
  de datos a 30 días; o cualquier tarea de código relacionada con este
  proyecto, aunque no se mencione el nombre completo. Sin esta skill es
  fácil usar un stack, una estructura de datos, un contrato de API o un
  comportamiento de negocio distinto del ya definido en el análisis y la
  documentación de residencia del proyecto, generando código incompatible
  con el resto del sistema.
---

# Desarrollo del simulador conversacional en inglés con IA

## Qué es el sistema (resumen para el desarrollador)

Aplicación web para que estudiantes de la Facultad de Idiomas practiquen
producción oral (speaking) en inglés conversando por voz con un agente de
IA dentro de un escenario elegido, y reciban al cerrar la sesión un
reporte JSON de retroalimentación (gramática, vocabulario, áreas de
mejora). Uso exclusivo en PC/laptop con micrófono; sin app móvil, sin
certificación oficial de idioma, sin sustituir al docente.

## Stack fijo — no sustituir sin que la persona lo pida explícitamente

- **Frontend:** React / Next.js. Captura de audio con la API nativa
  `MediaRecorder` del navegador. Reproducción de audio de respuesta vía
  Web Speech API (`SpeechSynthesis`). Sin soporte responsive para móvil:
  el diseño es de escritorio.
- **Backend:** Python + FastAPI. Todo I/O de red (llamadas a los
  servicios de IA, consultas a base de datos) debe usar `async`/`await`;
  no bloquear el event loop con llamadas síncronas a servicios externos.
- **Base de datos:** SQL Server, modelo relacional. Persistencia real
  vía SDK/ORM de la base de datos (no archivos ni almacenamiento en
  memoria para lo que deba sobrevivir a un reinicio).
- **Contrato API:** JSON estandarizado entre frontend y backend, validado
  en el backend con Pydantic. Cualquier endpoint nuevo debe definir su
  esquema de entrada y salida con modelos Pydantic, no dicts sueltos.
- **Despliegue objetivo:** frontend en Vercel/CDN, backend y
  microservicios en la nube. El código debe funcionar sin GPU local y sin
  asumir infraestructura propia especializada.

### Servicios de IA (capa gratuita) y su rol en el pipeline

| Etapa | Servicio | Notas de implementación |
|---|---|---|
| Speech-to-Text | Groq Cloud API, Whisper-large-v3 | Recibir el audio en buffer de memoria, no escribir a disco antes de enviarlo (evitar latencia de escritura). |
| LLM / orquestación | Google AI Studio, Gemini 2.0 Flash con Structured Outputs | Respaldo/fallback: Groq API con Llama 3.3 70B. Implementar el fallback como una función intercambiable (mismo contrato de entrada/salida) para poder cambiar de proveedor sin tocar el resto del backend. |
| Text-to-Speech | Web Speech API (frontend, nativa del navegador) | Respaldo: Kokoro TTS (Railway) o ElevenLabs API, solo si la síntesis nativa falla o el navegador la bloquea. |

Diseñar cada integración externa como un módulo aislado con manejo
explícito de timeouts, reintentos limitados y errores (caída del
servicio, límite de tasa de la capa gratuita) — no dejar que una falla de
IA tumbe la sesión sin un mensaje claro al frontend.

## Contrato de datos con el LLM

El LLM debe devolver **siempre** una salida estructurada (JSON), separando
explícitamente:
- el mensaje conversacional que se muestra/reproduce al estudiante, de
- los datos que alimentarán la retroalimentación final (errores
  detectados, tipo de error, sugerencia).

Antes de usar o persistir cualquier campo de esa respuesta, validarlo
contra un esquema (Pydantic) en el backend. Si la respuesta no cumple el
esquema, no debe propagarse tal cual al frontend: reintentar con una
instrucción de corrección acotada o devolver un error controlado de turno
fallido — nunca fallar silenciosamente ni inventar campos faltantes.

**Limitación a respetar en el código y en los prompts:** una transcripción
de texto no es evidencia suficiente para calificar pronunciación. No
implementar ni prometer en el system prompt una evaluación de
pronunciación basada solo en el texto transcrito; si se agrega esa
funcionalidad, requiere análisis de la señal de audio, no del texto.

## Modelo de datos (entidades base)

Usar estos nombres y campos como base al crear las tablas/modelos; si se
agregan campos, mantener los ya listados:

- **Usuario:** `id_usuario`, `nombre`, `correo` (único), `contraseña_hash`,
  `rol` (por ahora solo "estudiante"), `fecha_registro`. Autenticación
  local a la app — sin integración con sistemas institucionales de la
  Universidad Veracruzana.
- **Sesión:** `id_sesion`, `id_usuario`, `escenario`, `nivel`,
  `fecha_inicio`, `estado` (activa/pausada/concluida), `historial`
  (contexto conversacional para poder pausar y reanudar),
  `resumen_desempeño`, `evaluacion_sistema` (evaluación opcional que el
  estudiante da al sistema, **almacenar separada** de la evaluación
  lingüística del estudiante).
- **Retroalimentación:** `id_retroalimentacion`, `id_sesion`,
  `entrada_usuario` (texto transcrito con corrección), `correccion_ia`.
- **Métricas:** `id_métrica`, `id_usuario`, `escenario`, `nivel`,
  `fecha_inicio`, `duracion`, `errores`, `resumen_ia`. Esta tabla se
  conserva de forma indefinida (a diferencia de Sesión/Retroalimentación)
  y **no debe contener** audio ni texto completo de la conversación.

## Reglas de negocio a implementar como validaciones de backend

Estas reglas deben aplicarse en la capa de servicio/backend, no solo
documentarse:

1. Un correo identifica una sola cuenta; toda operación de sesión
   requiere autenticación previa.
2. Una sesión pertenece a un único estudiante y a un escenario
   precargado válido; un estudiante nunca debe poder leer sesiones de
   otro (verificar `id_usuario` en cada consulta, no solo en el
   frontend).
3. Una sesión no concluida puede reanudarse solo si han pasado menos de
   30 días desde `fecha_inicio`; pasado ese plazo, tratarla como no
   disponible.
4. La retroalimentación se genera y entrega únicamente al cerrar la
   sesión explícitamente — no interrumpir los turnos con retroalimentación
   parcial.
5. Solo las sesiones marcadas como concluidas deben contribuir a
   Métricas; sesiones abandonadas/pausadas indefinidamente no se cuentan.
6. Job de depuración: eliminar Sesión, sus turnos y su Retroalimentación
   al cumplir 30 días desde la creación, en una operación transaccional
   (todo o nada) que no afecte los registros de Métricas ya agregados.
7. El reporte de retroalimentación es orientativo: el código y los textos
   generados no deben presentarse como certificación o acreditación
   oficial de nivel MCER.

## Flujo principal (para diseñar rutas/endpoints y estados de UI)

Registro (si no tiene cuenta) → inicio de sesión → selección de nivel →
selección de escenario → la IA inicia la conversación → el estudiante
responde (por turnos, pudiendo pausar/reanudar) → el estudiante cierra la
sesión → el sistema analiza la conversación completa → genera y muestra
la retroalimentación → solicita evaluación de rendimiento (opcional, del
sistema) → actualiza métricas de progreso del estudiante.

Casos de uso ya identificados a nivel de interacción de UI (para mapear a
componentes/rutas del frontend): seleccionar simulación, ingresar audio,
pausar/reanudar simulación, cerrar simulación, completar simulación,
configuración (tema claro/oscuro, nivel, tipo/color/tamaño de fuente,
subtítulos on/off), visualizar perfil, editar perfil, visualizar
estadísticas.

## Requisitos no funcionales que afectan decisiones de implementación

- Turno conversacional completo (STT + LLM + TTS) en 3-5 segundos: si una
  etapa es lenta, considerar streaming solo donde el proveedor lo soporte
  realmente — no asumir que "asíncrono" por sí solo reduce la latencia
  percibida.
- Reporte final parseado y desplegado en menos de 8 segundos tras cerrar
  sesión.
- Diseñar pensando en pocos usuarios concurrentes: la capa gratuita de
  los servicios de IA impone límites de peticiones por minuto/día y de
  tokens; no dimensionar el sistema para carga alta sin advertir esta
  limitación.
- Arquitectura desacoplada: un cambio de proveedor de IA (p. ej. cambiar
  el fallback de LLM) no debe requerir modificar el frontend ni el
  esquema de la base de datos.

## Al escribir o ajustar el system prompt del agente de IA

El prompt debe fijar explícitamente: el rol/personaje según el escenario,
el idioma de respuesta (inglés), el nivel MCER seleccionado (para ajustar
léxico/gramática), el límite de extensión del turno, y el formato de
salida estructurado (JSON) que separa mensaje conversacional de datos de
retroalimentación. No prometer en el prompt capacidades que el sistema no
implementa (evaluación de pronunciación desde texto, certificación
oficial, comparación con hablantes nativos).

## Verificación antes de dar por terminada una implementación

- ¿El endpoint nuevo valida entrada/salida con modelos Pydantic?
- ¿Respeta la separación de capas (presentación / backend / datos /
  servicios de IA) sin que el frontend hable directo con un servicio de
  IA?
- ¿Aísla las llamadas a servicios externos de forma que cambiar de
  proveedor no rompa otras partes?
- ¿Aplica las reglas de negocio de la sección anterior (no solo las
  describe en un comentario)?
- ¿Usa los nombres de campos y entidades ya establecidos, en vez de
  inventar variantes?