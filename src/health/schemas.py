from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str
    environment: str


class ReadinessStatus(BaseModel):
    status: str
    database: str
