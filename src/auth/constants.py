from enum import StrEnum


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


ACCESS_TOKEN_TYPE = TokenType.ACCESS
REFRESH_TOKEN_TYPE = TokenType.REFRESH
