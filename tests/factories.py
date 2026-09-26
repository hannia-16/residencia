VALID_SIGNUP = {
    "email": "kenia@example.com",
    "username": "kenia",
    "password": "correct-horse-battery",
}


def unique_signup(suffix: str) -> dict[str, str]:
    return {
        "email": f"user-{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": "correct-horse-battery",
    }
