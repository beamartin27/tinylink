import secrets
import string # secrets: cryptographically secure random generator

ALPHABET = string.ascii_letters + string.digits # set of characters used for codes: 62 possibilities
LENGTH = 6 # With 62^6 combos ≈ 56 billion possible codes.

def generate_code(length: int = LENGTH) -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(length)) # picks a random char from the alphabet, do that lenght times and join into string

def generate_unique_code(exists_fn, *, max_tries: int = 5, length: int = LENGTH,) -> str:
    """
    Try to generate a unique short code of the given length.

    - `exists_fn(code) -> bool` tells us if the code is already taken.
    - `max_tries` limits how many collisions we tolerate.
    - `length` controls the base length of generated codes.
    """
    for _ in range(max_tries):
        c = generate_code(length=length)
        if not exists_fn(c):
            return c

    # rare fallback: bump length by 1 if we somehow collide too much
    return generate_code(length=length + 1)
