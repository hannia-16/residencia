import os

os.environ["AUTH_JWT_SECRET"] = "test-jwt-secret-at-least-32-bytes-long"
os.environ["AUTH_REFRESH_TOKEN_KEY"] = "test-refresh-key-at-least-32-bytes-long"
os.environ["AUTH_SECURE_COOKIES"] = "false"
os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key"
os.environ["ENVIRONMENT"] = "local"
