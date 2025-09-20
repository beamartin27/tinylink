import secrets, string

ALPHABET = string.ascii_letters + string.digits
LENGTH = 6

def generate_code(length: int = LENGTH) -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))

def generate_unique_code(exists_fn, max_tries: int = 5) -> str:
    for _ in range(max_tries):
        c = generate_code()
        if not exists_fn(c):
            return c
    # rare fallback
    return generate_code(length=LENGTH + 1)
