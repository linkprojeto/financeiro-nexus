import bcrypt
from sqlalchemy import text
from database import engine

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def register_user(username: str, password: str) -> bool:
    hashed = hash_password(password)

    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, password) VALUES (:username, :password)"),
                {"username": username, "password": hashed}
            )
        return True
    except Exception:
        return False

def login_user(username: str, password: str):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, password FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()

    if result:
        user_id, hashed = result
        if verify_password(password, hashed):
            return user_id
    return None