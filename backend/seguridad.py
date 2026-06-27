import bcrypt


def hashear_password(password: str) -> str:
    """Recibe la contraseña en claro y devuelve el hash bcrypt (texto)."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara la contraseña tecleada contra el hash guardado. True si coincide."""
    password_bytes = password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)
