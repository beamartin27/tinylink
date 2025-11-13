import secrets
import string # secrets: cryptographically secure random generator

ALPHABET = string.ascii_letters + string.digits # set of characters used for codes: 62 possibilities
LENGTH = 6 # With 62^6 combos ≈ 56 billion possible codes.

def generate_code(length: int = LENGTH) -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(length)) # picks a random char from the alphabet, do that lenght times and join into string

def generate_unique_code(exists_fn, max_tries: int = 5) -> str: # When you call it you pass a function exists_fn that checks the existance (eg: exists_code or fake_exists)
    for _ in range(max_tries): # Avoid collissions with 5 max tries, else generate it with lenght 7 (rare)
        c = generate_code()
        if not exists_fn(c):
            return c
    # rare fallback
    return generate_code(length=LENGTH + 1)
