
import time
import httpx
from src.ai.config import AIConfig

config = AIConfig()

print("URL:", config.BASE_URL)
print("Modelo:", config.MODEL.value)
print("API key configurada:", bool(config.API_KEY))

inicio = time.perf_counter()

try:
    respuesta = httpx.post(
        config.BASE_URL.rstrip("/") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.MODEL.value,
            "messages": [
                {"role": "user", "content": "Responde solamente OK"}
            ],
            "max_tokens": 10,
            "stream": False,
        },
        timeout=20,
    )

    print("HTTP:", respuesta.status_code)
    print("Respuesta:", respuesta.text[:800])

except Exception as error:
    print("Tipo de error:", type(error).__name__)
    print("Detalle:", str(error))

finally:
    print("Tiempo:", round(time.perf_counter() - inicio, 2), "segundos")