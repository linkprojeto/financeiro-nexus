import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import text
from database import create_tables, get_connection
from auth import login_user, register_user

st.set_page_config(page_title="Nexus Finance", layout="wide")

create_tables()

if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ---------------- LOGIN / REGISTRO ----------------
if st.session_state.user_id is None:
    st.title("🔐 Nexus Finance - Login")

    tab1, tab2 = st.tabs(["Login", "Registrar"])

    with tab1:
        username_input = st.text_input("Usuário", key="login_user")
        password_input = st.text_input("Senha", type="password", key="login_pass")
        login_pressed = st.button("Entrar", key="btn_login")

        if login_pressed:
            uid = login_user(username_input.strip(), password_input)
            if uid:
                st.session_state.user_id = uid
                st.success("Login bem-sucedido!")
                st.rerun()
            else:
                st.error("Credenciais inválidas")

    with tab2:
        new_user_input = st.text_input("Novo usuário", key="reg_user")
        new_pass_input = st.text_input("Nova senha", type="password", key="reg_pass")
        register_pressed = st.button("Registrar", key="btn_register")

        if register_pressed:
            if not new_user_input.strip() or not new_pass_input.strip():
                st.error("Preencha usuário e senha.")
            elif register_user(new_user_input.strip(), new_pass_input):
                st.success("Usuário criado! Faça login agora.")
            else:
                st.error("Usuário já existe")

    st.stop()

# ---------------- APP PRINCIPAL ----------------
user_id = st.session_state.user_id

st.sidebar.title("Menu")
page = st.sidebar.selectbox(
    "Menu",
    ["Início", "Movimentações", "Contas Fixas", "Logout"]
)

if page == "Logout":
    st.session_state.user_id = None
    st.rerun()

conn = get_connection()

# ---------------- TELA INÍCIO ----------------
if page == "Início":
    st.title("💰 Início")

    df_contas = pd.read_sql(
        text("SELECT * FROM contas WHERE user_id=:user_id"),
        conn,
        params={"user_id": user_id}
    )
    df_parcelas = pd.read_sql(
        text("SELECT * FROM parcelas WHERE user_id=:user_id"),
        conn,
        params={"user_id": user_id}
    )
    df_receitas = pd.read_sql(
        text("SELECT * FROM receitas WHERE user_id=:user_id"),
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

    st.subheader("Resumo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo", f"R$ {saldo:,.2f}")
    col2.metric("Total Entradas", f"R$ {entradas:,.2f}")
    col3.metric("Total Saídas", f"R$ {saidas:,.2f}")

    st.subheader("Últimas Movimentações")
    if not df_mov.empty:
        st.dataframe(
            df_mov.sort_values(by=["data", "id"], ascending=[False, False]).head(10),
            use_container_width=True
        )
    else:
        st.info("Nenhuma movimentação registrada ainda.")

    st.subheader("Contas Fixas / Parceladas")
    if not df_parcelas.empty:
        st.dataframe(df_parcelas, use_container_width=True)
    else:
        st.info("Nenhuma conta fixa ou parcelada registrada.")

# ---------------- MOVIMENTAÇÕES ----------------
elif page == "Movimentações":
    st.title("💸 Movimentações")

    tipo = st.selectbox("Tipo", ["entrada", "saida"])
    desc = st.text_input("Descrição", key="mov_desc")
    valor = st.number_input("Valor", min_value=0.01, step=0.01, key="mov_valor")
    data_mov = st.date_input("Data", value=date.today(), key="mov_data")
    salvar_mov = st.button("Salvar Movimentação", key="btn_mov")

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
            cols = st.columns([2, 3, 2, 2, 1])
            cols[0].write(row["tipo"])
            cols[1].write(row["descricao"])
            cols[2].write(f"R$ {row['valor']:,.2f}")
            cols[3].write(str(row["data"]))

            if cols[4].button("❌", key=f"del_mov_{row['id']}"):
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
    st.title("📅 Contas Fixas / Parceladas")

    desc = st.text_input("Descrição (Ex: Cartão, Academia, MEO)", key="parc_desc")
    valor = st.number_input("Valor", min_value=0.01, step=0.01, key="parc_valor")
    total = st.number_input("Total de parcelas", min_value=1, step=1, key="parc_total")
    atual = st.number_input("Parcela atual", min_value=1, step=1, key="parc_atual")
    salvar_conta = st.button("Salvar Conta Fixa", key="btn_parc")

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

    st.subheader("Contas Parceladas")
    df_parc = pd.read_sql(
        text("SELECT * FROM parcelas WHERE user_id=:user_id ORDER BY id DESC"),
        conn,
        params={"user_id": user_id}
    )

    if not df_parc.empty:
        for _, row in df_parc.iterrows():
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].write(row["descricao"])
            cols[1].write(f"R$ {row['valor']:,.2f}")
            cols[2].write(f"{row['parcela_atual']}/{row['total_parcelas']}")
            cols[3].write(row["tipo"])

            if cols[4].button("❌", key=f"del_parc_{row['id']}"):
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