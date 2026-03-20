import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import text
from database import create_tables, get_connection
from auth import login_user, register_user

st.set_page_config(page_title="Nexus Finance", layout="centered")

st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 700px;
    }

    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        min-height: 3rem;
        font-size: 16px;
    }

    div[data-baseweb="select"] > div {
        border-radius: 10px;
    }

    input, textarea {
        font-size: 16px !important;
    }

    .card {
        padding: 1rem;
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 14px;
        margin-bottom: 0.8rem;
        background-color: rgba(255, 255, 255, 0.02);
    }
</style>
""", unsafe_allow_html=True)

create_tables()

if "user_id" not in st.session_state:
    st.session_state.user_id = None


def format_brl(valor):
    return f"R$ {valor:,.2f}"


# ---------------- LOGIN / REGISTRO ----------------
if st.session_state.user_id is None:
    st.title("🔐 Nexus Finance")

    tab1, tab2 = st.tabs(["Login", "Registrar"])

    with tab1:
        with st.form("form_login"):
            username_input = st.text_input("Usuário")
            password_input = st.text_input("Senha", type="password")
            login_pressed = st.form_submit_button("Entrar")

        if login_pressed:
            uid = login_user(username_input.strip(), password_input)
            if uid:
                st.session_state.user_id = uid
                st.success("Login bem-sucedido!")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

    with tab2:
        with st.form("form_register"):
            new_user_input = st.text_input("Novo usuário")
            new_pass_input = st.text_input("Nova senha", type="password")
            register_pressed = st.form_submit_button("Registrar")

        if register_pressed:
            if not new_user_input.strip() or not new_pass_input.strip():
                st.error("Preencha usuário e senha.")
            elif register_user(new_user_input.strip(), new_pass_input):
                st.success("Usuário criado! Faça login agora.")
            else:
                st.error("Usuário já existe.")

    st.stop()


# ---------------- APP PRINCIPAL ----------------
user_id = st.session_state.user_id
conn = get_connection()

st.title("💸 Nexus Finance")

page = st.selectbox(
    "Escolha uma tela",
    ["Início", "Movimentações", "Contas Fixas", "Logout"]
)

if page == "Logout":
    st.session_state.user_id = None
    conn.close()
    st.rerun()


# ---------------- TELA INÍCIO ----------------
if page == "Início":
    st.subheader("Resumo")

    df_parcelas = pd.read_sql(
        text("SELECT * FROM parcelas WHERE user_id=:user_id"),
        conn,
        params={"user_id": user_id}
    )

    df_mov = pd.read_sql(
        text("SELECT * FROM movimentacoes WHERE user_id=:user_id"),
        conn,
        params={"user_id": user_id}
    )

    entradas = df_mov[df_mov["tipo"] == "entrada"]["valor"].sum() if not df_mov.empty else 0
    saidas = df_mov[df_mov["tipo"] == "saida"]["valor"].sum() if not df_mov.empty else 0
    saldo = entradas - saidas

    st.metric("Saldo", format_brl(saldo))
    st.metric("Total Entradas", format_brl(entradas))
    st.metric("Total Saídas", format_brl(saidas))

    st.subheader("Últimas Movimentações")
    if not df_mov.empty:
        df_ultimas = df_mov.sort_values(by=["data", "id"], ascending=[False, False]).head(10)

        for _, row in df_ultimas.iterrows():
            icone = "🟢" if row["tipo"] == "entrada" else "🔴"
            st.markdown(
                f"""
                <div class="card">
                    <strong>{icone} {row["tipo"].capitalize()}</strong><br>
                    <strong>Descrição:</strong> {row["descricao"]}<br>
                    <strong>Valor:</strong> {format_brl(row["valor"])}<br>
                    <strong>Data:</strong> {row["data"]}
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("Nenhuma movimentação registrada ainda.")

    st.subheader("Contas Fixas / Parceladas")
    if not df_parcelas.empty:
        for _, row in df_parcelas.iterrows():
            st.markdown(
                f"""
                <div class="card">
                    <strong>📅 {row["descricao"]}</strong><br>
                    <strong>Valor:</strong> {format_brl(row["valor"])}<br>
                    <strong>Parcela:</strong> {row["parcela_atual"]}/{row["total_parcelas"]}<br>
                    <strong>Tipo:</strong> {row["tipo"]}
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("Nenhuma conta fixa ou parcelada registrada.")


# ---------------- MOVIMENTAÇÕES ----------------
elif page == "Movimentações":
    st.subheader("Nova movimentação")

    with st.form("form_movimentacao"):
        tipo = st.selectbox("Tipo", ["entrada", "saida"])
        desc = st.text_input("Descrição")
        valor = st.number_input("Valor", min_value=0.01, format="%.2f")
        data_mov = st.date_input("Data", value=date.today())
        salvar_mov = st.form_submit_button("Salvar Movimentação")

    if salvar_mov:
        if not desc.strip():
            st.error("Informe uma descrição.")
        else:
            conn.execute(
                text("""
                    INSERT INTO movimentacoes (user_id, tipo, descricao, valor, data)
                    VALUES (:user_id, :tipo, :descricao, :valor, :data)
                """),
                {
                    "user_id": user_id,
                    "tipo": tipo,
                    "descricao": desc.strip(),
                    "valor": float(valor),
                    "data": str(data_mov)
                }
            )
            conn.commit()
            st.success("Movimentação salva!")
            st.rerun()

    st.subheader("Histórico de Movimentações")
    df_mov = pd.read_sql(
        text("SELECT * FROM movimentacoes WHERE user_id=:user_id ORDER BY data DESC, id DESC"),
        conn,
        params={"user_id": user_id}
    )

    if not df_mov.empty:
        for _, row in df_mov.iterrows():
            icone = "🟢" if row["tipo"] == "entrada" else "🔴"

            st.markdown(
                f"""
                <div class="card">
                    <strong>{icone} {row["tipo"].capitalize()}</strong><br>
                    <strong>Descrição:</strong> {row["descricao"]}<br>
                    <strong>Valor:</strong> {format_brl(row["valor"])}<br>
                    <strong>Data:</strong> {row["data"]}
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Apagar movimentação", key=f"del_mov_{row['id']}"):
                conn.execute(
                    text("DELETE FROM movimentacoes WHERE id=:id AND user_id=:user_id"),
                    {"id": int(row["id"]), "user_id": user_id}
                )
                conn.commit()
                st.success(f"Movimentação '{row['descricao']}' removida!")
                st.rerun()
    else:
        st.info("Nenhuma movimentação registrada.")


# ---------------- CONTAS FIXAS / PARCELADAS ----------------
elif page == "Contas Fixas":
    st.subheader("Nova conta fixa / parcelada")

    with st.form("form_parcelas"):
        desc = st.text_input("Descrição (Ex: Cartão, Academia, MEO)")
        valor = st.number_input("Valor", min_value=0.01, step=0.01)
        total = st.number_input("Total de parcelas", min_value=1, step=1)
        atual = st.number_input("Parcela atual", min_value=1, step=1)
        salvar_conta = st.form_submit_button("Salvar Conta Fixa")

    if salvar_conta:
        if not desc.strip():
            st.error("Informe uma descrição.")
        elif atual > total:
            st.error("A parcela atual não pode ser maior que o total de parcelas.")
        else:
            conn.execute(
                text("""
                    INSERT INTO parcelas (user_id, descricao, valor, total_parcelas, parcela_atual, tipo)
                    VALUES (:user_id, :descricao, :valor, :total_parcelas, :parcela_atual, :tipo)
                """),
                {
                    "user_id": user_id,
                    "descricao": desc.strip(),
                    "valor": float(valor),
                    "total_parcelas": int(total),
                    "parcela_atual": int(atual),
                    "tipo": "fixo"
                }
            )
            conn.commit()
            st.success("Conta fixa salva!")
            st.rerun()

    st.subheader("Contas cadastradas")
    df_parc = pd.read_sql(
        text("SELECT * FROM parcelas WHERE user_id=:user_id ORDER BY id DESC"),
        conn,
        params={"user_id": user_id}
    )

    if not df_parc.empty:
        for _, row in df_parc.iterrows():
            st.markdown(
                f"""
                <div class="card">
                    <strong>📅 {row["descricao"]}</strong><br>
                    <strong>Valor:</strong> {format_brl(row["valor"])}<br>
                    <strong>Parcela:</strong> {row["parcela_atual"]}/{row["total_parcelas"]}<br>
                    <strong>Tipo:</strong> {row["tipo"]}
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Apagar conta", key=f"del_parc_{row['id']}"):
                conn.execute(
                    text("DELETE FROM parcelas WHERE id=:id AND user_id=:user_id"),
                    {"id": int(row["id"]), "user_id": user_id}
                )
                conn.commit()
                st.success(f"Parcela '{row['descricao']}' removida!")
                st.rerun()
    else:
        st.info("Nenhuma conta parcelada registrada.")

conn.close()
