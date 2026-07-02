"""
NRC PAINEL GERENCIAL
Painel gerencial das Unidades Interligadas - NRC/COGEX/TJMA
Dados carregados automaticamente a partir de planilha Google Sheets publicada em CSV.

Como rodar localmente:
    streamlit run app.py

Deploy:
    1. Suba este repositório no GitHub.
    2. Em https://share.streamlit.io, aponte para o app.py.
    3. Configure em "Secrets" (Settings > Secrets) o usuário/senha reais,
       usando o modelo do arquivo .streamlit/secrets.toml.example.
"""

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="NRC PAINEL GERENCIAL",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# URL da planilha Google Sheets publicada em formato CSV.
# Para trocar a fonte de dados, publique a planilha em
# Arquivo > Compartilhar > Publicar na Web > CSV, e cole o link abaixo.
DATA_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vT73jQ3Ae7I0gSx-UqOvA3C_JznfDQYrb23nLx4jpQXH03i1-ocEzHxnRNZnYTTHQ/pub?output=csv"
)

# ----------------------------------------------------------------------------
# AUTENTICAÇÃO
# ----------------------------------------------------------------------------
def get_credentials():
    """
    Busca usuário/senha em st.secrets (recomendado em produção).
    Se não houver secrets configurados, usa um valor padrão apenas
    para permitir testes locais - TROQUE antes de publicar!
    """
    try:
        user = st.secrets["credentials"]["username"]
        pwd = st.secrets["credentials"]["password"]
    except Exception:
        user, pwd = "COGEX", "cogex@nrc"  # valor padrão de fallback (apenas teste local)
    return user, pwd


def login_screen():
    st.markdown(
        """
        <div style="text-align:center; padding-top: 40px;">
            <h1>🏛️ NRC PAINEL GERENCIAL</h1>
            <p style="color:gray;">COGEX / TJMA - Unidades Interligadas</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("Acesso restrito")
            user_input = st.text_input("Usuário")
            pwd_input = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            valid_user, valid_pwd = get_credentials()
            if user_input == valid_user and pwd_input == valid_pwd:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")


def logout_button():
    with st.sidebar:
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()


# ----------------------------------------------------------------------------
# CARGA E TRATAMENTO DOS DADOS
# ----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Carregando dados da planilha...")
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)

    # remove eventual coluna de índice sem nome, vinda da planilha
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    df = df.drop(columns=unnamed, errors="ignore")

    # limpa espaços dos nomes de coluna
    df.columns = [str(c).strip() for c in df.columns]

    # limpa espaços em branco dos valores texto
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
            df[c] = df[c].replace({"nan": "", "None": ""})

    # coluna normalizada de status de funcionamento, para facilitar filtro
    def classificar_status(valor: str) -> str:
        v = valor.upper()
        if not v:
            return "Sem informação"
        if "NÃO" in v and "FUNCION" in v:
            return "Não funcionando"
        if "PAROU" in v or "PARALISAD" in v:
            return "Paralisada"
        if "FUNCIONANDO" in v or v == "OK" or "REATIVADA" in v:
            return "Funcionando"
        return "Outra situação"

    if "SITUAÇÃO ATUAL" in df.columns:
        df["STATUS_FUNCIONAMENTO"] = df["SITUAÇÃO ATUAL"].apply(classificar_status)
    else:
        df["STATUS_FUNCIONAMENTO"] = "Sem informação"

    return df


# ----------------------------------------------------------------------------
# PAINEL PRINCIPAL
# ----------------------------------------------------------------------------
def painel():
    df = load_data(DATA_URL)

    with st.sidebar:
        st.markdown("## 🏛️ NRC PAINEL GERENCIAL")
        st.caption("COGEX / TJMA")
        st.markdown("### Filtros")

        def multiselect_filtro(label, coluna):
            if coluna not in df.columns:
                return []
            opcoes = sorted([o for o in df[coluna].unique() if o])
            return st.multiselect(label, opcoes, default=[])

        f_municipio = multiselect_filtro("Município", "MUNICÍPIOS")
        f_esfera = multiselect_filtro("Esfera", "ESFERA")
        f_status = multiselect_filtro("Status de funcionamento", "STATUS_FUNCIONAMENTO")
        f_situacao_geral = multiselect_filtro("Situação geral", "SITUAÇÃO GERAL")
        f_justica_aberta = multiselect_filtro("Justiça Aberta", "JUSTIÇA ABERTA")
        f_crc = multiselect_filtro("Habilitação CRC", "HABILITAÇÃO CRC")
        f_serventia = multiselect_filtro("Serventia", "SERVENTIA")

        busca = st.text_input("🔎 Buscar hospital/unidade")

        if st.button("🔄 Atualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # aplica filtros
    df_filtrado = df.copy()
    if f_municipio:
        df_filtrado = df_filtrado[df_filtrado["MUNICÍPIOS"].isin(f_municipio)]
    if f_esfera:
        df_filtrado = df_filtrado[df_filtrado["ESFERA"].isin(f_esfera)]
    if f_status:
        df_filtrado = df_filtrado[df_filtrado["STATUS_FUNCIONAMENTO"].isin(f_status)]
    if f_situacao_geral:
        df_filtrado = df_filtrado[df_filtrado["SITUAÇÃO GERAL"].isin(f_situacao_geral)]
    if f_justica_aberta:
        df_filtrado = df_filtrado[df_filtrado["JUSTIÇA ABERTA"].isin(f_justica_aberta)]
    if f_crc:
        df_filtrado = df_filtrado[df_filtrado["HABILITAÇÃO CRC"].isin(f_crc)]
    if f_serventia:
        df_filtrado = df_filtrado[df_filtrado["SERVENTIA"].isin(f_serventia)]
    if busca:
        mask = df_filtrado.apply(
            lambda row: busca.upper() in " ".join(row.astype(str)).upper(), axis=1
        )
        df_filtrado = df_filtrado[mask]

    # cabeçalho
    st.markdown("## 🏛️ NRC PAINEL GERENCIAL")
    st.caption("Unidades Interligadas - Corregedoria Geral de Justiça Extrajudicial (COGEX/MA)")

    # KPIs
    total = len(df_filtrado)
    funcionando = (df_filtrado["STATUS_FUNCIONAMENTO"] == "Funcionando").sum()
    nao_funcionando = (df_filtrado["STATUS_FUNCIONAMENTO"] == "Não funcionando").sum()
    paralisada = (df_filtrado["STATUS_FUNCIONAMENTO"] == "Paralisada").sum()
    outros = total - funcionando - nao_funcionando - paralisada

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de unidades", total)
    c2.metric("✅ Funcionando", int(funcionando))
    c3.metric("⛔ Não funcionando", int(nao_funcionando))
    c4.metric("⏸️ Paralisada", int(paralisada))
    c5.metric("ℹ️ Outras situações", int(outros))

    st.markdown("---")

    # gráficos com biblioteca nativa do streamlit
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### Unidades por status de funcionamento")
        st.bar_chart(df_filtrado["STATUS_FUNCIONAMENTO"].value_counts())
    with g2:
        st.markdown("#### Unidades por esfera")
        if "ESFERA" in df_filtrado.columns:
            esfera_counts = df_filtrado[df_filtrado["ESFERA"] != ""]["ESFERA"].value_counts()
            st.bar_chart(esfera_counts)

    st.markdown("#### Unidades por Justiça Aberta x Habilitação CRC")
    g3, g4 = st.columns(2)
    with g3:
        if "JUSTIÇA ABERTA" in df_filtrado.columns:
            st.bar_chart(df_filtrado["JUSTIÇA ABERTA"].value_counts())
    with g4:
        if "HABILITAÇÃO CRC" in df_filtrado.columns:
            st.bar_chart(df_filtrado["HABILITAÇÃO CRC"].value_counts())

    st.markdown("---")

    # tabela detalhada
    st.markdown(f"#### Detalhamento das unidades ({total} registros)")
    colunas_exibir = [
        c for c in [
            "MUNICÍPIOS", "HOSPITAL", "DATA DA INSTALAÇÃO", "ESFERA", "SERVENTIA",
            "JUSTIÇA ABERTA", "HABILITAÇÃO CRC", "SITUAÇÃO ATUAL", "SITUAÇÃO GERAL",
            "ÍNDICES IBGE", "OBSERVAÇÕES",
        ] if c in df_filtrado.columns
    ]
    st.dataframe(df_filtrado[colunas_exibir], use_container_width=True, hide_index=True)

    csv_download = df_filtrado[colunas_exibir].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar dados filtrados (CSV)",
        data=csv_download,
        file_name="nrc_unidades_interligadas_filtrado.csv",
        mime="text/csv",
    )


# ----------------------------------------------------------------------------
# CONTROLE DE FLUXO (LOGIN -> PAINEL)
# ----------------------------------------------------------------------------
def main():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        login_screen()
    else:
        logout_button()
        painel()


if __name__ == "__main__":
    main()
