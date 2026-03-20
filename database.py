import os
import streamlit as st
from sqlalchemy import create_engine, text
from streamlit.errors import StreamlitSecretNotFoundError

def get_database_url():
    try:
        return st.secrets["DATABASE_URL"]
    except (StreamlitSecretNotFoundError, KeyError):
        return os.getenv("DATABASE_URL")

DATABASE_URL = get_database_url()

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não encontrada. Configure nos Secrets do Streamlit Cloud ou como variável de ambiente."
    )

if "sslmode=" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,
)

def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        st.error("Erro ao conectar ao banco:")
        st.code(str(e))
        raise

def get_connection():
    return engine.connect()

def create_tables():
    test_connection()

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS contas (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                nome TEXT,
                vencimento TEXT,
                valor DOUBLE PRECISION,
                recorrente TEXT,
                pago INTEGER
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS receitas (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                descricao TEXT,
                data TEXT,
                valor DOUBLE PRECISION
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                tipo TEXT,
                descricao TEXT,
                valor DOUBLE PRECISION,
                data TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS parcelas (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                descricao TEXT,
                valor DOUBLE PRECISION,
                total_parcelas INTEGER,
                parcela_atual INTEGER,
                tipo TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS saldo (
                user_id BIGINT PRIMARY KEY,
                valor DOUBLE PRECISION
            )
        """))