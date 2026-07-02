"""
MAT-COGEX-NRC-EXEC-001
NRC PAINEL GERENCIAL — v2 (Visão Executiva + Central de Relatórios)
Painel gerencial das Unidades Interligadas - NRC/COGEX/TJMA

NOVIDADES v2 (aditivo, nada do v1 foi removido):
  1. Aba "📋 Visão Executiva": responde de imediato as perguntas da
     Corregedora — quantos municípios têm/não têm UI, quantas UIs ativas,
     inativas, em implantação (previsão de instalação) e em reativação,
     e quais UIs ativas estão SEM PRODUÇÃO (sem registro / índice baixo).
  2. Central de Relatórios: emite relação nominal por categoria
     (ativas, inativas, implantação, reativação, municípios sem UI,
     ativas sem produção) com download em CSV e em relatório formatado
     (HTML pronto para imprimir/PDF pelo navegador).

IMPORTANTE - sobre sanitização dos dados:
Toda limpeza/normalização feita aqui acontece SOMENTE em memória, na cópia
dos dados carregada pelo app. O app é somente-leitura: nunca escreve, edita
ou apaga nada na planilha de origem (Google Sheets ou arquivo enviado).

Como rodar localmente:
    streamlit run app.py

Deploy:
    1. Suba este repositório no GitHub.
    2. Em https://share.streamlit.io, aponte para o app.py.
    3. Configure em "Secrets" o usuário/senha reais.
"""

import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="NRC PAINEL GERENCIAL",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",  # mobile-first: conteúdo primeiro
)

# ----------------------------------------------------------------------------
# CSS GLOBAL MOBILE-FIRST + PALETA INSTITUCIONAL COGEX
# Paleta oficial: MARROM, VINHO, AMARELO-QUEIMADO e PRETO.
# Todas as cores são declaradas EXPLICITAMENTE (fundo E texto de cada
# componente), de modo que o app fica idêntico com o navegador/SO em tema
# claro ou escuro — corrige o defeito de letra branca sobre fundo branco.
# ----------------------------------------------------------------------------
COGEX_PRETO = "#1C1713"          # texto principal
COGEX_MARROM = "#5C4033"         # estrutura / sidebar
COGEX_MARROM_ESCURO = "#3E2B22"  # sidebar fundo
COGEX_VINHO = "#7B1F24"          # destaque principal
COGEX_AMARELO = "#B8862B"        # amarelo-queimado (acento)
COGEX_CREME = "#FAF6EF"          # fundo do app
COGEX_CARD = "#FFFFFF"           # fundo de cards
COGEX_CINZA = "#6B6259"          # texto secundário


def aplicar_css_mobile_first():
    st.markdown(
        f"""
        <style>
        /* ---------- PALETA FORÇADA (independente de dark/light) ---------- */
        .stApp, [data-testid="stAppViewContainer"] {{
            background: {COGEX_CREME} !important;
            color: {COGEX_PRETO} !important;
        }}
        [data-testid="stHeader"] {{ background: {COGEX_CREME} !important; }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4,
        .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
        label, .stRadio label, .stSelectbox label, .stTextInput label,
        .stMultiSelect label, [data-testid="stWidgetLabel"] p {{
            color: {COGEX_PRETO} !important;
        }}
        .stCaption, [data-testid="stCaptionContainer"] p, small {{
            color: {COGEX_CINZA} !important;
        }}

        /* Sidebar: marrom escuro com texto claro (contraste garantido) */
        [data-testid="stSidebar"] {{
            background: {COGEX_MARROM_ESCURO} !important;
        }}
        [data-testid="stSidebar"] * {{ color: #F3EDE3 !important; }}
        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background: #FFFFFF !important;
            color: {COGEX_PRETO} !important;
        }}
        [data-testid="stSidebar"] hr {{ border-color: {COGEX_AMARELO} !important; }}

        /* Inputs/selects da área principal: fundo branco, texto preto */
        .stTextInput input, div[data-baseweb="select"] > div,
        [data-baseweb="popover"] li {{
            background: #FFFFFF !important;
            color: {COGEX_PRETO} !important;
        }}
        [data-baseweb="menu"] {{ background: #FFFFFF !important; }}

        /* Dataframes: fundo claro sempre */
        div[data-testid="stDataFrame"] {{
            background: {COGEX_CARD} !important;
            border: 1px solid {COGEX_MARROM}33;
            border-radius: 10px;
            overflow-x: auto !important;
        }}

        /* ---------- BASE (mobile) ---------- */
        .block-container {{
            padding: 0.8rem 0.7rem 3rem 0.7rem !important;
            max-width: 100% !important;
        }}
        h1, .stMarkdown h2 {{ font-size: 1.25rem !important; }}
        .stMarkdown h3 {{
            font-size: 1.05rem !important;
            border-left: 4px solid {COGEX_AMARELO};
            padding-left: 0.5rem;
        }}
        .stMarkdown h4 {{ font-size: 0.95rem !important; }}

        div[data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            gap: 0.5rem !important;
        }}
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
        }}

        /* Métricas: card branco, número vinho, rótulo marrom — sempre legível */
        div[data-testid="stMetric"] {{
            background: {COGEX_CARD} !important;
            border: 1px solid {COGEX_MARROM}40;
            border-left: 4px solid {COGEX_VINHO};
            border-radius: 10px;
            padding: 0.55rem 0.7rem;
            min-height: 44px;
            box-shadow: 0 1px 3px rgba(28,23,19,.07);
        }}
        div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] div {{
            font-size: 1.35rem !important;
            color: {COGEX_VINHO} !important;
        }}
        div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] p {{
            font-size: 0.72rem !important;
            white-space: normal !important;
            color: {COGEX_MARROM} !important;
            font-weight: 600;
        }}

        /* Botões: vinho sólido; download: contorno marrom */
        .stButton > button {{
            width: 100% !important;
            min-height: 46px;
            border-radius: 10px;
            font-size: 0.95rem;
            background: {COGEX_VINHO} !important;
            color: #FFFFFF !important;
            border: none !important;
        }}
        .stDownloadButton > button {{
            width: 100% !important;
            min-height: 46px;
            border-radius: 10px;
            font-size: 0.95rem;
            background: #FFFFFF !important;
            color: {COGEX_MARROM} !important;
            border: 1.5px solid {COGEX_MARROM} !important;
            font-weight: 600;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            border-color: {COGEX_AMARELO} !important;
            color: {COGEX_AMARELO} !important;
        }}
        .stButton > button:hover {{ background: {COGEX_MARROM} !important; color:#fff !important; }}
        .stTextInput input {{ min-height: 44px; font-size: 16px; }}

        /* Abas em pílulas: creme → ativa em vinho */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            scrollbar-width: thin;
            gap: 0.35rem;
            padding-bottom: 0.3rem;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab"] {{
            min-height: 44px;
            padding: 0.4rem 0.95rem;
            white-space: nowrap;
            background: {COGEX_CARD} !important;
            border: 1px solid {COGEX_MARROM}55;
            border-radius: 999px;
            font-size: 0.85rem;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab"] p {{ color: {COGEX_MARROM} !important; }}
        div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
            background: {COGEX_VINHO} !important;
            border-color: {COGEX_VINHO};
        }}
        div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] p {{
            color: #FFFFFF !important;
            font-weight: 600;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
        div[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none; }}

        hr {{ border-color: {COGEX_MARROM}30 !important; }}
        div[data-testid="stExpander"] {{
            border: 1px solid {COGEX_MARROM}40;
            border-radius: 10px;
            background: {COGEX_CARD};
        }}
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] p {{ color: {COGEX_PRETO} !important; }}

        /* Alertas/infos do Streamlit legíveis na paleta */
        div[data-testid="stAlert"] {{ color: {COGEX_PRETO} !important; }}

        /* ---------- TABLET (>= 641px) ---------- */
        @media (min-width: 641px) {{
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                flex: 1 1 calc(33.33% - 0.5rem) !important;
                min-width: calc(33.33% - 0.5rem) !important;
            }}
            .block-container {{ padding: 1.2rem 1.5rem 3rem 1.5rem !important; }}
        }}

        /* ---------- DESKTOP (>= 1024px) ---------- */
        @media (min-width: 1024px) {{
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                flex: 1 1 0 !important;
                min-width: 0 !important;
            }}
            h1, .stMarkdown h2 {{ font-size: 1.6rem !important; }}
            div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] div {{
                font-size: 1.7rem !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


aplicar_css_mobile_first()

DATA_URL_PADRAO = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vT73jQ3Ae7I0gSx-UqOvA3C_JznfDQYrb23nLx4jpQXH03i1-ocEzHxnRNZnYTTHQ/pub?output=csv"
)

# Mesma planilha publicada, em XLSX: entrega TODAS as abas de uma vez.
DATA_URL_XLSX = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vT73jQ3Ae7I0gSx-UqOvA3C_JznfDQYrb23nLx4jpQXH03i1-ocEzHxnRNZnYTTHQ/pub?output=xlsx"
)

# Identidade visual por aba (ícone + rótulo curto para a barra de abas).
# Casamento por nome normalizado; aba desconhecida ganha ícone genérico.
ABAS_IDENTIDADE = {
    "UNIDADES INTERLIGADAS":            ("🏥", "Unidades Interligadas"),
    "MUNICIPIOS PARA INSTALAR":         ("🚧", "Para Instalar"),
    "STATUS RECEB FORMULARIO":          ("📨", "Formulários"),
    "MUN. INVIAVEIS DE INSTALACAO":     ("🚫", "Inviáveis"),
    "PROVIMENTO 09":                    ("📜", "Provimento 09"),
    "MUNICIPIOS PARA REATIVA":          ("♻️", "Para Reativar"),
    "TAB ACOMPANHAMENTO ARTICULACAO":   ("🤝", "Articulação"),
    "INDICES DE SUB-REGISTRO":          ("📉", "Sub-registro"),
    "CONTATOS":                         ("📞", "Contatos"),
    "MUNICIPIOS C PIORES INDICES 2":    ("🔻", "Piores Índices"),
    "OPERADORES":                       ("👤", "Operadores"),
    "OPERADORES (M,C,E E T)":           ("👥", "Operadores M/C/E/T"),
    "HOSPITAIS DAS UI":                 ("🏨", "Hospitais"),
    "UI PARALISADAS E SEM CONTATO":     ("⛔", "Paralisadas/Sem contato"),
    "HORARIOS DE FUNCIONAMENTO UIS":    ("🕐", "Horários"),
    "CIDADES COM SELO UNICEF":          ("🏅", "Selo UNICEF"),
}


def identidade_aba(nome_aba: str):
    n = normalizar_nome(nome_aba)
    if n in ABAS_IDENTIDADE:                      # 1) casamento exato
        return ABAS_IDENTIDADE[n]
    for chave in sorted(ABAS_IDENTIDADE, key=len, reverse=True):
        if chave in n:                            # 2) chave contida no nome
            return ABAS_IDENTIDADE[chave]
    return "📄", str(nome_aba).strip().title()

COLUNAS_ESPERADAS = [
    "MUNICÍPIOS", "HOSPITAL", "DATA DA INSTALAÇÃO", "ESFERA", "SERVENTIA",
    "JUSTIÇA ABERTA", "HABILITAÇÃO CRC", "SITUAÇÃO ATUAL", "SITUAÇÃO GERAL",
    "ÍNDICES IBGE", "OBSERVAÇÕES",
]

# Lista oficial dos 217 municípios do Maranhão (fonte: IBGE) — universo fixo.
MUNICIPIOS_MA = [
    'Afonso Cunha', 'Alcântara', 'Aldeias Altas', 'Altamira do Maranhão',
    'Alto Alegre do Maranhão', 'Alto Alegre do Pindaré', 'Alto Parnaíba',
    'Amapá do Maranhão', 'Amarante do Maranhão', 'Anajatuba', 'Anapurus',
    'Apicum-Açu', 'Araguanã', 'Araioses', 'Arame', 'Arari', 'Axixá',
    'Açailândia', 'Bacabal', 'Bacabeira', 'Bacuri', 'Bacurituba', 'Balsas',
    'Barra do Corda', 'Barreirinhas', 'Barão de Grajaú',
    'Bela Vista do Maranhão', 'Belágua', 'Benedito Leite', 'Bequimão',
    'Bernardo do Mearim', 'Boa Vista do Gurupi', 'Bom Jardim',
    'Bom Jesus das Selvas', 'Bom Lugar', 'Brejo', 'Brejo de Areia', 'Buriti',
    'Buriti Bravo', 'Buriticupu', 'Buritirana', 'Cachoeira Grande', 'Cajapió',
    'Cajari', 'Campestre do Maranhão', 'Cantanhede', 'Capinzal do Norte',
    'Carolina', 'Carutapera', 'Caxias', 'Cedral', 'Central do Maranhão',
    'Centro Novo do Maranhão', 'Centro do Guilherme', 'Chapadinha',
    'Cidelândia', 'Codó', 'Coelho Neto', 'Colinas', 'Conceição do Lago-Açu',
    'Coroatá', 'Cururupu', 'Cândido Mendes', 'Davinópolis', 'Dom Pedro',
    'Duque Bacelar', 'Esperantinópolis', 'Estreito', 'Feira Nova do Maranhão',
    'Fernando Falcão', 'Formosa da Serra Negra', 'Fortaleza dos Nogueiras',
    'Fortuna', 'Godofredo Viana', 'Gonçalves Dias', 'Governador Archer',
    'Governador Edison Lobão', 'Governador Eugênio Barros',
    'Governador Luiz Rocha', 'Governador Newton Bello',
    'Governador Nunes Freire', 'Grajaú', 'Graça Aranha', 'Guimarães',
    'Humberto de Campos', 'Icatu', 'Igarapé Grande', 'Igarapé do Meio',
    'Imperatriz', 'Itaipava do Grajaú', 'Itapecuru Mirim',
    'Itinga do Maranhão', 'Jatobá', 'Jenipapo dos Vieiras', 'Joselândia',
    'João Lisboa', 'Junco do Maranhão', 'Lago Verde', 'Lago da Pedra',
    'Lago do Junco', 'Lago dos Rodrigues', 'Lagoa Grande do Maranhão',
    'Lagoa do Mato', 'Lajeado Novo', 'Lima Campos', 'Loreto',
    'Luís Domingues', 'Magalhães de Almeida', 'Maracaçumé', 'Marajá do Sena',
    'Maranhãozinho', 'Mata Roma', 'Matinha', 'Matões', 'Matões do Norte',
    'Milagres do Maranhão', 'Mirador', 'Miranda do Norte', 'Mirinzal',
    'Montes Altos', 'Monção', 'Morros', 'Nina Rodrigues', 'Nova Colinas',
    'Nova Iorque', 'Nova Olinda do Maranhão', "Olho d'Água das Cunhãs",
    'Olinda Nova do Maranhão', 'Palmeirândia', 'Paraibano', 'Parnarama',
    'Passagem Franca', 'Pastos Bons', 'Paulino Neves', 'Paulo Ramos',
    'Paço do Lumiar', 'Pedreiras', 'Pedro do Rosário', 'Penalva',
    'Peri Mirim', 'Peritoró', 'Pindaré-Mirim', 'Pinheiro', 'Pio XII',
    'Pirapemas', 'Porto Franco', 'Porto Rico do Maranhão', 'Poção de Pedras',
    'Presidente Dutra', 'Presidente Juscelino', 'Presidente Médici',
    'Presidente Sarney', 'Presidente Vargas', 'Primeira Cruz', 'Raposa',
    'Riachão', 'Ribamar Fiquene', 'Rosário', 'Sambaíba',
    'Santa Filomena do Maranhão', 'Santa Helena', 'Santa Inês', 'Santa Luzia',
    'Santa Luzia do Paruá', 'Santa Quitéria do Maranhão', 'Santa Rita',
    'Santana do Maranhão', 'Santo Amaro do Maranhão',
    'Santo Antônio dos Lopes', 'Satubinha', 'Senador Alexandre Costa',
    'Senador La Rocque', 'Serrano do Maranhão', 'Sucupira do Norte',
    'Sucupira do Riachão', 'São Benedito do Rio Preto', 'São Bento',
    'São Bernardo', 'São Domingos do Azeitão', 'São Domingos do Maranhão',
    'São Francisco do Brejão', 'São Francisco do Maranhão',
    'São Félix de Balsas', 'São José de Ribamar', 'São José dos Basílios',
    'São João Batista', 'São João do Carú', 'São João do Paraíso',
    'São João do Soter', 'São João dos Patos', 'São Luís',
    'São Luís Gonzaga do Maranhão', 'São Mateus do Maranhão',
    'São Pedro da Água Branca', 'São Pedro dos Crentes',
    'São Raimundo das Mangabeiras', 'São Raimundo do Doca Bezerra',
    'São Roberto', 'São Vicente Ferrer', 'Sítio Novo', 'Tasso Fragoso',
    'Timbiras', 'Timon', 'Trizidela do Vale', 'Tufilândia', 'Tuntum',
    'Turiaçu', 'Turilândia', 'Tutóia', 'Urbano Santos', 'Vargem Grande',
    'Viana', 'Vila Nova dos Martírios', 'Vitorino Freire',
    'Vitória do Mearim', 'Zé Doca', 'Água Doce do Maranhão',
]


def normalizar_nome(texto: str) -> str:
    """Remove acentos, espaços extras e padroniza para MAIÚSCULAS."""
    if texto is None:
        return ""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return texto


MUNICIPIOS_MA_NORMALIZADOS = {normalizar_nome(m): m for m in MUNICIPIOS_MA}

# ----------------------------------------------------------------------------
# AUTENTICAÇÃO
# ----------------------------------------------------------------------------
def get_credentials():
    try:
        user = st.secrets["credentials"]["username"]
        pwd = st.secrets["credentials"]["password"]
    except Exception:
        user, pwd = "COGEX", "cogex@nrc"  # fallback apenas para teste local
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
# CLASSIFICAÇÃO DE STATUS
# ----------------------------------------------------------------------------
def classificar_status(valor) -> str:
    if valor is None:
        return "Sem informação"
    v = str(valor).strip().upper()
    if v == "" or v == "NAN":
        return "Sem informação"
    if "IMPLANTA" in v or "PREVIS" in v or "EM PROCESSO" in v or "PROCESSO CNJ" in v:
        return "Em fase de implantação"
    if "REATIVA" in v or "REINAUGURA" in v or "REINSTALA" in v:
        return "Em fase de reativação"
    if "NÃO" in v and "FUNCION" in v:
        return "Inativa"
    if "PAROU" in v or "PARALISAD" in v or "DESATIVAD" in v:
        return "Inativa"
    if "FUNCIONANDO" in v or v == "OK":
        return "Ativa"
    return "Outra situação"


# Detecção de UI ativa SEM PRODUÇÃO (sem registro / sem parto / índice baixo).
# Heurística textual auditável sobre SITUAÇÃO GERAL + ÍNDICES IBGE +
# OBSERVAÇÕES. Nunca inventa: só marca quando há sinal explícito no texto.
TERMOS_SEM_PRODUCAO = [
    "SEM REGISTRO", "SEM MOVIMENTO", "SEM PRODUCAO", "SEM PRODUÇÃO",
    "NAO REALIZA", "NÃO REALIZA", "NAO ESTA REALIZANDO", "NÃO ESTÁ REALIZANDO",
    "SEM PARTO", "NAO HA PARTO", "NÃO HÁ PARTO", "SEM NASCIMENTO",
    "INDICE BAIXO", "ÍNDICE BAIXO", "BAIXO INDICE", "BAIXO ÍNDICE",
    "BAIXA PRODUCAO", "BAIXA PRODUÇÃO", "ZERO REGISTRO", "0 REGISTRO",
    "SEM ATO", "NENHUM REGISTRO", "NENHUM ATO",
]


def detectar_sem_producao(row, colunas_texto) -> str:
    """Retorna o trecho/sinal encontrado, ou '' se não há sinal de baixa
    produção. Auditável: devolve qual termo disparou."""
    blob = " | ".join(
        normalizar_nome(row.get(c, "")) for c in colunas_texto if c
    )
    for termo in TERMOS_SEM_PRODUCAO:
        if normalizar_nome(termo) in blob:
            return termo
    return ""


# ----------------------------------------------------------------------------
# DETECÇÃO GENÉRICA DE COLUNAS
# ----------------------------------------------------------------------------
def detectar_coluna(df: pd.DataFrame, candidatos):
    for c in df.columns:
        c_norm = normalizar_nome(c)
        for cand in candidatos:
            if normalizar_nome(cand) in c_norm:
                return c
    return None


# ----------------------------------------------------------------------------
# CARGA E TRATAMENTO (sanitização só em memória — app somente-leitura)
# ----------------------------------------------------------------------------
def tratar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    df = df.drop(columns=unnamed, errors="ignore")
    # cabeçalhos "lixo" (texto colado de nota/análise) viram rótulo curto
    df.columns = [
        (str(c).strip().split("\n")[0][:60] + "…")
        if len(str(c).strip()) > 60 else str(c).strip()
        for c in df.columns
    ]

    for c in df.columns:
        df[c] = df[c].apply(lambda x: "" if pd.isna(x) else str(x).strip())

    # remove colunas 100% vazias (sanitização em memória; fonte intacta)
    colunas_vazias = [c for c in df.columns if (df[c] == "").all()]
    df = df.drop(columns=colunas_vazias, errors="ignore")
    # remove linhas 100% vazias
    if len(df.columns):
        df = df[~(df == "").all(axis=1)].reset_index(drop=True)

    col_status = detectar_coluna(df, ["SITUAÇÃO ATUAL", "SITUACAO ATUAL", "STATUS"])
    if col_status:
        df["STATUS_FUNCIONAMENTO"] = df[col_status].apply(classificar_status)
    else:
        df["STATUS_FUNCIONAMENTO"] = "Sem informação"

    # marcação de baixa/nenhuma produção (heurística textual auditável)
    col_sitgeral = detectar_coluna(df, ["SITUAÇÃO GERAL", "SITUACAO GERAL"])
    col_indices = detectar_coluna(df, ["ÍNDICES IBGE", "INDICES IBGE", "ÍNDICE", "INDICE"])
    col_obs = detectar_coluna(df, ["OBSERVAÇÕES", "OBSERVACOES", "OBS"])
    colunas_texto = [c for c in [col_sitgeral, col_indices, col_obs] if c]
    if colunas_texto:
        df["ALERTA_SEM_PRODUCAO"] = df.apply(
            lambda r: detectar_sem_producao(r, colunas_texto), axis=1
        )
    else:
        df["ALERTA_SEM_PRODUCAO"] = ""

    return df


@st.cache_data(ttl=600, show_spinner="Carregando todas as abas da planilha...")
def load_data_url(url_csv: str, url_xlsx: str) -> dict:
    """Carrega TODAS as abas da planilha publicada (XLSX). Se o XLSX
    falhar (rede/permissão), cai para o CSV (apenas a primeira aba)."""
    try:
        planilhas = pd.read_excel(url_xlsx, sheet_name=None)
        return {
            str(aba).strip(): tratar_dataframe(df)
            for aba, df in planilhas.items()
        }
    except Exception:
        df = pd.read_csv(url_csv)
        return {"UNIDADES INTERLIGADAS": tratar_dataframe(df)}


def load_data_upload(arquivo) -> dict:
    nome = arquivo.name.lower()
    if nome.endswith(".csv"):
        df = pd.read_csv(arquivo)
        return {"Planilha enviada": tratar_dataframe(df)}
    else:
        planilhas = pd.read_excel(arquivo, sheet_name=None)
        return {aba: tratar_dataframe(df) for aba, df in planilhas.items()}


# ----------------------------------------------------------------------------
# NÚCLEO EXECUTIVO — cálculo único de todos os números da Corregedora
# ----------------------------------------------------------------------------
def calcular_executivo(df: pd.DataFrame) -> dict:
    """Calcula, sobre 100% da base, todos os números-resposta:
    municípios com/sem UI, UIs por status, ativas sem produção,
    e as relações nominais de cada categoria."""
    col_municipio = detectar_coluna(df, ["MUNICÍPIOS", "MUNICIPIO", "MUNICÍPIO"])

    municipios_com_dado = set()
    if col_municipio:
        municipios_com_dado = {
            normalizar_nome(m) for m in df[col_municipio].unique() if m
        }
        # só conta município que existe na lista oficial (protege contra typo)
        municipios_com_dado &= set(MUNICIPIOS_MA_NORMALIZADOS.keys())

    sem_ui_norm = set(MUNICIPIOS_MA_NORMALIZADOS.keys()) - municipios_com_dado
    municipios_sem_ui = sorted(MUNICIPIOS_MA_NORMALIZADOS[n] for n in sem_ui_norm)
    municipios_com_ui = sorted(MUNICIPIOS_MA_NORMALIZADOS[n] for n in municipios_com_dado)

    def recorte(status):
        return df[df["STATUS_FUNCIONAMENTO"] == status].copy()

    ativas = recorte("Ativa")
    inativas = recorte("Inativa")
    implantacao = recorte("Em fase de implantação")
    reativacao = recorte("Em fase de reativação")
    outras = df[~df["STATUS_FUNCIONAMENTO"].isin(
        ["Ativa", "Inativa", "Em fase de implantação", "Em fase de reativação"]
    )].copy()

    ativas_sem_producao = ativas[ativas["ALERTA_SEM_PRODUCAO"] != ""].copy()

    return {
        "col_municipio": col_municipio,
        "total_municipios_ma": len(MUNICIPIOS_MA_NORMALIZADOS),
        "municipios_com_ui": municipios_com_ui,
        "municipios_sem_ui": municipios_sem_ui,
        "total_unidades": len(df),
        "ativas": ativas,
        "inativas": inativas,
        "implantacao": implantacao,
        "reativacao": reativacao,
        "outras": outras,
        "ativas_sem_producao": ativas_sem_producao,
    }


# ----------------------------------------------------------------------------
# GERADOR DE RELATÓRIO FORMATADO (HTML imprimível — Ctrl+P → PDF)
# ----------------------------------------------------------------------------
def gerar_relatorio_html(titulo: str, subtitulo: str, df_rel: pd.DataFrame,
                         resumo_kpis: list, colunas: list) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas_kpi = "".join(
        f"<div class='kpi'><div class='kpi-num'>{v}</div><div class='kpi-lab'>{k}</div></div>"
        for k, v in resumo_kpis
    )
    if df_rel is not None and len(df_rel) > 0:
        cabecalho = "".join(f"<th>{c}</th>" for c in colunas)
        corpo = ""
        for i, (_, row) in enumerate(df_rel.iterrows(), start=1):
            celulas = "".join(f"<td>{row.get(c, '')}</td>" for c in colunas)
            corpo += f"<tr><td>{i}</td>{celulas}</tr>"
        tabela = (
            f"<div class='tabela-wrap'><table><thead><tr><th>#</th>{cabecalho}</tr></thead>"
            f"<tbody>{corpo}</tbody></table></div>"
        )
    else:
        tabela = "<p><em>Nenhum registro nesta categoria.</em></p>"

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
  /* Paleta institucional COGEX aplicada com sobriedade: fundo branco,
     texto preto, VINHO e AMARELO-QUEIMADO apenas em filetes finos.
     Nenhum bloco chapado de cor — impressão limpa, inclusive em P&B. */
  :root {{
    --preto:#1C1713; --marrom:#5C4033; --vinho:#7B1F24;
    --amarelo:#B8862B; --cinza:#6B6259;
  }}
  body {{ font-family: Georgia, 'Times New Roman', serif; color:var(--preto);
          background:#FFFFFF; margin:14px; line-height:1.45; }}
  .cab {{ text-align:center; padding-bottom:12px; margin-bottom:18px;
          border-bottom:2px solid var(--vinho); position:relative; }}
  .cab::after {{ content:""; display:block; width:120px; height:2px;
                 background:var(--amarelo); margin:4px auto 0; }}
  .cab h1 {{ margin:0; font-size:16px; letter-spacing:.4px; }}
  .cab h2 {{ margin:4px 0 0; font-size:12px; font-weight:normal; color:var(--marrom); }}
  .cab .org {{ font-size:10px; color:var(--marrom); font-weight:bold;
               letter-spacing:2px; text-transform:uppercase; }}
  h2.titulo {{ text-align:center; font-size:15px; margin:14px 0 2px;
               color:var(--preto); }}
  p.sub {{ text-align:center; color:var(--cinza); font-size:12px; margin-top:2px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; margin:16px 0; }}
  .kpi {{ border:1px solid #D8D2C8; border-top:3px solid var(--vinho);
          border-radius:4px; padding:9px 8px; text-align:center; background:#FFFFFF; }}
  .kpi-num {{ font-size:22px; font-weight:bold; color:var(--preto); }}
  .kpi-lab {{ font-size:9px; color:var(--marrom); text-transform:uppercase;
              letter-spacing:.6px; }}
  .tabela-wrap {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
  table {{ width:100%; border-collapse:collapse; font-size:11.5px;
           margin-top:10px; min-width:520px; }}
  th {{ background:#FFFFFF; color:var(--preto); text-align:left;
        border-bottom:2px solid var(--vinho); border-top:1px solid var(--marrom);
        padding:7px; font-size:10px; text-transform:uppercase; letter-spacing:.5px; }}
  td {{ border-bottom:1px solid #E4DED4; padding:6px 7px; }}
  tbody tr:hover td {{ background:#FAF6EF; }}
  .rod {{ margin-top:24px; font-size:10px; color:var(--cinza);
          border-top:1px solid var(--amarelo); padding-top:8px; }}
  @media (min-width: 700px) {{
    body {{ margin:32px 40px; }}
    .cab h1 {{ font-size:19px; }}
    .kpis {{ grid-template-columns:repeat(4, 1fr); }}
  }}
  @media print {{
    body {{ margin:14mm 16mm; }}
    .tabela-wrap {{ overflow:visible; }}
    table {{ min-width:0; }}
    tbody tr:hover td {{ background:transparent; }}
    .kpi {{ break-inside:avoid; }}
    thead {{ display:table-header-group; }}  /* cabeçalho repete a cada página */
    tr {{ break-inside:avoid; }}
  }}
</style></head><body>
<div class="cab">
  <div class="org">PODER JUDICIÁRIO · TRIBUNAL DE JUSTIÇA DO MARANHÃO</div>
  <h1>Corregedoria-Geral do Foro Extrajudicial — COGEX/MA</h1>
  <h2>Núcleo de Registro Civil (NRC) — Unidades Interligadas</h2>
</div>
<h2 class="titulo">{titulo}</h2>
<p class="sub">{subtitulo}</p>
<div class="kpis">{linhas_kpi}</div>
{tabela}
<div class="rod">
  Relatório gerado pelo NRC Painel Gerencial em {agora}.
  Fonte: planilha oficial de acompanhamento das Unidades Interligadas (NRC/COGEX).
  Documento gerado automaticamente — os dados refletem 100% dos registros da fonte na data/hora acima.
</div>
</body></html>"""


# ----------------------------------------------------------------------------
# ABA: VISÃO EXECUTIVA + CENTRAL DE RELATÓRIOS
# ----------------------------------------------------------------------------
def renderizar_visao_executiva(df: pd.DataFrame, abas: dict = None):
    abas = abas or {}
    ex = calcular_executivo(df)
    col_mun = ex["col_municipio"]

    st.markdown("### 📋 Visão Executiva — respostas diretas")
    st.caption(
        "Universo fixo: 217 municípios do Maranhão (IBGE). "
        "Números calculados sobre 100% dos registros da planilha, em tempo real."
    )

    # LINHA 1 — municípios
    a1, a2, a3 = st.columns(3)
    a1.metric("Municípios do MA", ex["total_municipios_ma"])
    a2.metric("✅ Municípios COM Unidade Interligada", len(ex["municipios_com_ui"]))
    a3.metric("❌ Municípios SEM Unidade Interligada", len(ex["municipios_sem_ui"]))

    # LINHA 2 — unidades por status
    b1, b2, b3, b4, b5 = st.columns(5)
    b1.metric("Total de UIs cadastradas", ex["total_unidades"])
    b2.metric("🟢 UIs Ativas", len(ex["ativas"]))
    b3.metric("🔴 UIs Inativas", len(ex["inativas"]))
    b4.metric("🚧 Previsão de instalação", len(ex["implantacao"]))
    b5.metric("♻️ Em reativação", len(ex["reativacao"]))

    # LINHA 3 — alerta de produção (fluxo vertical: melhor leitura no celular)
    st.metric("⚠️ Ativas SEM produção / índice baixo", len(ex["ativas_sem_producao"]))
    st.caption(
        "Critério auditável: UI classificada como Ativa cujo texto de "
        "SITUAÇÃO GERAL / ÍNDICES IBGE / OBSERVAÇÕES contém sinal explícito "
        "de ausência de registro, ausência de parto ou índice baixo. "
        "Nenhum registro é marcado por inferência sem sinal no texto."
    )
    if len(ex["outras"]):
        st.caption(
            f"ℹ️ {len(ex['outras'])} unidade(s) em outra situação / sem "
            "informação classificável — constam no relatório completo."
        )

    st.markdown("---")

    # ---------------- REFLEXO DAS DEMAIS ABAS (contexto executivo) --------
    def achar_aba(fragmento):
        for nome, dfa in abas.items():
            if fragmento in normalizar_nome(nome):
                return nome, dfa
        return None, None

    nome_sub, df_sub = achar_aba("SUB-REGISTRO")
    nome_piores, df_piores = achar_aba("PIORES INDICES")
    nome_paral, df_paral = achar_aba("PARALISADAS")
    nome_inv, df_inv = achar_aba("INVIAVEIS")

    if any(x is not None for x in (df_sub, df_piores, df_paral, df_inv)):
        st.markdown("### 🔎 Contexto das demais abas")

        e1, e2, e3 = st.columns(3)
        if df_paral is not None and len(df_paral.columns) >= 1:
            col_sem_contato = detectar_coluna(df_paral, ["SEM CONTATO"])
            col_paralisadas = detectar_coluna(df_paral, ["PARALIZADAS", "PARALISADAS"])
            n_sem_contato = int((df_paral[col_sem_contato] != "").sum()) if col_sem_contato else 0
            n_paralisadas = int((df_paral[col_paralisadas] != "").sum()) if col_paralisadas else 0
            e1.metric("📵 UIs sem contato", n_sem_contato)
            e2.metric("⛔ UIs paralisadas (lista)", n_paralisadas)
        if df_inv is not None:
            e3.metric("🚫 Municípios inviáveis de instalação", len(df_inv))

        if df_sub is not None:
            col_cidade = detectar_coluna(df_sub, ["CIDADE", "MUNICIPIO"])
            col_pct = detectar_coluna(df_sub, ["SUB-REGISTRO", "SUB REGISTRO"])
            if col_cidade and col_pct:
                df_rank = df_sub[[col_cidade, col_pct]].copy()
                df_rank["_pct"] = pd.to_numeric(
                    df_rank[col_pct].astype(str)
                    .str.replace("%", "", regex=False)
                    .str.replace(",", ".", regex=False),
                    errors="coerce",
                )
                df_rank = df_rank.dropna(subset=["_pct"]).sort_values("_pct", ascending=False)
                st.markdown(f"#### 📉 Top 10 piores índices de sub-registro (fonte: aba “{nome_sub}”)")
                st.dataframe(
                    df_rank.head(10)[[col_cidade, col_pct]],
                    use_container_width=True, hide_index=True,
                )

        if df_piores is not None:
            with st.expander(f"🔻 Detalhe — {len(df_piores)} municípios com piores índices (aba “{nome_piores}”)"):
                st.dataframe(df_piores, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🖨️ Central de Relatórios")
    st.caption(
        "Escolha a categoria, visualize a relação nominal e baixe em CSV "
        "(planilha) ou HTML formatado (abrir e imprimir/salvar como PDF)."
    )

    colunas_dado = [c for c in df.columns if c not in ("STATUS_FUNCIONAMENTO", "ALERTA_SEM_PRODUCAO")]

    df_sem_ui = pd.DataFrame({"MUNICÍPIO SEM UNIDADE INTERLIGADA": ex["municipios_sem_ui"]})
    df_com_ui = pd.DataFrame({"MUNICÍPIO COM UNIDADE INTERLIGADA": ex["municipios_com_ui"]})

    categorias = {
        "🟢 Unidades ATIVAS": (ex["ativas"], colunas_dado),
        "🔴 Unidades INATIVAS": (ex["inativas"], colunas_dado),
        "🚧 Previsão de instalação (em implantação)": (ex["implantacao"], colunas_dado),
        "♻️ Em reativação / reinauguração": (ex["reativacao"], colunas_dado),
        "⚠️ Ativas SEM produção / índice baixo": (
            ex["ativas_sem_producao"],
            colunas_dado + ["ALERTA_SEM_PRODUCAO"],
        ),
        "❌ Municípios SEM Unidade Interligada": (df_sem_ui, list(df_sem_ui.columns)),
        "✅ Municípios COM Unidade Interligada": (df_com_ui, list(df_com_ui.columns)),
        "📄 Relatório completo (todas as unidades)": (df, colunas_dado + ["STATUS_FUNCIONAMENTO"]),
        "❓ Outra situação / sem informação": (ex["outras"], colunas_dado),
    }

    escolha = st.selectbox("Categoria do relatório", list(categorias.keys()))
    df_rel, cols_rel = categorias[escolha]

    st.markdown(f"**{len(df_rel)} registro(s)** nesta categoria.")
    if len(df_rel):
        st.dataframe(df_rel[cols_rel], use_container_width=True, hide_index=True)

    resumo_kpis = [
        ("Municípios MA", ex["total_municipios_ma"]),
        ("Com UI", len(ex["municipios_com_ui"])),
        ("Sem UI", len(ex["municipios_sem_ui"])),
        ("UIs Ativas", len(ex["ativas"])),
        ("UIs Inativas", len(ex["inativas"])),
        ("Em implantação", len(ex["implantacao"])),
        ("Em reativação", len(ex["reativacao"])),
        ("Ativas sem produção", len(ex["ativas_sem_producao"])),
    ]

    # Downloads empilhados (largura total — alvo de toque no celular)
    csv_bytes = df_rel[cols_rel].to_csv(index=False).encode("utf-8-sig") if len(df_rel) else "sem registros".encode("utf-8")
    st.download_button(
        "⬇️ Baixar CSV desta categoria",
        data=csv_bytes,
        file_name=f"nrc_relatorio_{normalizar_nome(escolha).lower().replace(' ', '_')[:60]}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    html_rel = gerar_relatorio_html(
        titulo=f"RELATÓRIO — {escolha.split(' ', 1)[-1].upper()}",
        subtitulo="Situação das Unidades Interligadas de Registro Civil de Nascimento",
        df_rel=df_rel if len(df_rel) else None,
        resumo_kpis=resumo_kpis,
        colunas=cols_rel,
    )
    st.download_button(
        "🖨️ Baixar relatório formatado (HTML → imprimir/PDF)",
        data=html_rel.encode("utf-8"),
        file_name=f"nrc_relatorio_{normalizar_nome(escolha).lower().replace(' ', '_')[:60]}.html",
        mime="text/html",
        use_container_width=True,
    )

    st.caption(
        "💡 O arquivo HTML abre em qualquer navegador já formatado com "
        "cabeçalho institucional; use Ctrl+P → 'Salvar como PDF' para gerar "
        "o documento de entrega."
    )


# ----------------------------------------------------------------------------
# SEÇÃO: MUNICÍPIOS SEM UNIDADE INTERLIGADA (mantida do v1)
# ----------------------------------------------------------------------------
def secao_municipios_sem_ui(df: pd.DataFrame, col_municipio: str):
    if not col_municipio:
        return

    ex = calcular_executivo(df)
    sem_ui = ex["municipios_sem_ui"]
    com_ui = len(ex["municipios_com_ui"])

    st.markdown("#### Cobertura por município (base: 217 municípios do Maranhão)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de municípios do MA", ex["total_municipios_ma"])
    m2.metric("✅ Municípios com UI", com_ui)
    m3.metric("❌ Municípios sem UI", len(sem_ui))

    with st.expander(f"Ver os {len(sem_ui)} municípios sem Unidade Interligada"):
        if sem_ui:
            n_col = 4
            cols = st.columns(n_col)
            for i, m in enumerate(sem_ui):
                cols[i % n_col].write(f"- {m}")
        else:
            st.write("Todos os municípios possuem ao menos uma Unidade Interligada. 🎉")


# ----------------------------------------------------------------------------
# RENDERIZAÇÃO DE UMA ABA DE DADOS (mantida do v1)
# ----------------------------------------------------------------------------
def renderizar_aba(df: pd.DataFrame, chave: str):
    col_municipio = detectar_coluna(df, ["MUNICÍPIOS", "MUNICIPIO", "MUNICÍPIO"])
    col_esfera = detectar_coluna(df, ["ESFERA"])
    col_situacao_geral = detectar_coluna(df, ["SITUAÇÃO GERAL", "SITUACAO GERAL"])
    col_justica_aberta = detectar_coluna(df, ["JUSTIÇA ABERTA", "JUSTICA ABERTA"])
    col_crc = detectar_coluna(df, ["HABILITAÇÃO CRC", "HABILITACAO CRC", "CRC"])
    col_serventia = detectar_coluna(df, ["SERVENTIA"])
    tem_status = (df["STATUS_FUNCIONAMENTO"] != "Sem informação").any()

    with st.sidebar:
        st.markdown(f"#### Filtros — {chave}")

        def multiselect_filtro(label, coluna, key_suffix):
            if not coluna:
                return []
            opcoes = sorted([o for o in df[coluna].unique() if o])
            return st.multiselect(label, opcoes, default=[], key=f"{key_suffix}_{chave}")

        f_municipio = multiselect_filtro("Município", col_municipio, "municipio")
        f_esfera = multiselect_filtro("Esfera", col_esfera, "esfera")
        f_status = multiselect_filtro(
            "Status (Ativa/Inativa/...)",
            "STATUS_FUNCIONAMENTO" if tem_status else None,
            "status",
        )
        f_situacao_geral = multiselect_filtro("Situação geral", col_situacao_geral, "sitgeral")
        f_justica_aberta = multiselect_filtro("Justiça Aberta", col_justica_aberta, "justaberta")
        f_crc = multiselect_filtro("Habilitação CRC", col_crc, "crc")
        f_serventia = multiselect_filtro("Serventia", col_serventia, "serventia")

        busca = st.text_input("🔎 Buscar", key=f"busca_{chave}")

    df_filtrado = df.copy()
    if f_municipio:
        df_filtrado = df_filtrado[df_filtrado[col_municipio].isin(f_municipio)]
    if f_esfera:
        df_filtrado = df_filtrado[df_filtrado[col_esfera].isin(f_esfera)]
    if f_status:
        df_filtrado = df_filtrado[df_filtrado["STATUS_FUNCIONAMENTO"].isin(f_status)]
    if f_situacao_geral:
        df_filtrado = df_filtrado[df_filtrado[col_situacao_geral].isin(f_situacao_geral)]
    if f_justica_aberta:
        df_filtrado = df_filtrado[df_filtrado[col_justica_aberta].isin(f_justica_aberta)]
    if f_crc:
        df_filtrado = df_filtrado[df_filtrado[col_crc].isin(f_crc)]
    if f_serventia:
        df_filtrado = df_filtrado[df_filtrado[col_serventia].isin(f_serventia)]
    if busca:
        mask = df_filtrado.apply(
            lambda row: busca.upper() in " ".join(row.astype(str)).upper(), axis=1
        )
        df_filtrado = df_filtrado[mask]

    total = len(df_filtrado)

    if tem_status:
        ativas = (df_filtrado["STATUS_FUNCIONAMENTO"] == "Ativa").sum()
        inativas = (df_filtrado["STATUS_FUNCIONAMENTO"] == "Inativa").sum()
        reativacao = (df_filtrado["STATUS_FUNCIONAMENTO"] == "Em fase de reativação").sum()
        implantacao = (df_filtrado["STATUS_FUNCIONAMENTO"] == "Em fase de implantação").sum()
        outros = total - ativas - inativas - reativacao - implantacao

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total de unidades", total)
        c2.metric("✅ Ativas", int(ativas))
        c3.metric("⛔ Inativas", int(inativas))
        c4.metric("♻️ Em reativação", int(reativacao))
        c5.metric("🚧 Em implantação", int(implantacao))
        if outros:
            st.caption(f"ℹ️ {int(outros)} unidade(s) em outras situações / sem informação classificável.")
    else:
        st.metric("Total de registros nesta aba", total)

    st.markdown("---")

    if tem_status:
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("#### Unidades por status")
            st.bar_chart(df_filtrado["STATUS_FUNCIONAMENTO"].value_counts())
        with g2:
            if col_esfera:
                st.markdown("#### Unidades por esfera")
                esfera_counts = df_filtrado[df_filtrado[col_esfera] != ""][col_esfera].value_counts()
                st.bar_chart(esfera_counts)

    if col_justica_aberta or col_crc:
        g3, g4 = st.columns(2)
        with g3:
            if col_justica_aberta:
                st.markdown("#### Justiça Aberta")
                st.bar_chart(df_filtrado[col_justica_aberta].value_counts())
        with g4:
            if col_crc:
                st.markdown("#### Habilitação CRC")
                st.bar_chart(df_filtrado[col_crc].value_counts())

    if col_municipio:
        st.markdown("#### Top 15 municípios com mais unidades")
        st.bar_chart(df_filtrado[col_municipio].value_counts().head(15))

    st.markdown("---")
    if tem_status:
        secao_municipios_sem_ui(df, col_municipio)
        st.markdown("---")

    st.markdown(f"#### Detalhamento ({total} registros)")
    colunas_exibir = [c for c in df_filtrado.columns
                      if c not in ("STATUS_FUNCIONAMENTO", "ALERTA_SEM_PRODUCAO")]
    if tem_status:
        colunas_exibir += ["STATUS_FUNCIONAMENTO"]
    st.dataframe(df_filtrado[colunas_exibir], use_container_width=True, hide_index=True)

    csv_download = df_filtrado[colunas_exibir].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar dados filtrados (CSV)",
        data=csv_download,
        file_name=f"nrc_{chave.lower().replace(' ', '_')}_filtrado.csv",
        mime="text/csv",
        key=f"download_{chave}",
    )


# ----------------------------------------------------------------------------
# PAINEL PRINCIPAL
# ----------------------------------------------------------------------------
def painel():
    with st.sidebar:
        st.markdown("## 🏛️ NRC PAINEL GERENCIAL")
        st.caption("COGEX / TJMA")
        st.markdown("### Fonte de dados")

        fonte = st.radio(
            "Selecione a origem dos dados",
            ["Planilha publicada (padrão)", "Enviar arquivo (CSV/XLSX)"],
            index=0,
        )

        abas = None
        if fonte == "Planilha publicada (padrão)":
            try:
                abas = load_data_url(DATA_URL_PADRAO, DATA_URL_XLSX)
            except Exception as e:
                st.error(f"Não foi possível carregar a planilha publicada: {e}")
        else:
            arquivo = st.file_uploader("Envie o arquivo CSV ou XLSX", type=["csv", "xlsx", "xls"])
            if arquivo is not None:
                try:
                    abas = load_data_upload(arquivo)
                except Exception as e:
                    st.error(f"Não foi possível ler o arquivo: {e}")

        if not abas:
            st.info("Aguardando dados...")
            st.stop()

        if fonte == "Planilha publicada (padrão)" and st.button("🔄 Atualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("## 🏛️ NRC PAINEL GERENCIAL")
    st.caption("Unidades Interligadas - Corregedoria Geral de Justiça Extrajudicial (COGEX/MA)")
    st.caption("📱 Filtros e fonte de dados: toque no menu **»** no canto superior esquerdo.")

    nomes_abas = list(abas.keys())

    # Base principal de UIs: aba "UNIDADES INTERLIGADAS" (ou a primeira).
    nome_principal = next(
        (n for n in nomes_abas if "UNIDADES INTERLIGADAS" in normalizar_nome(n)),
        nomes_abas[0],
    )
    df_principal = abas[nome_principal]

    rotulos = ["📋 Visão Executiva"] + [
        f"{identidade_aba(n)[0]} {identidade_aba(n)[1]}" for n in nomes_abas
    ]
    st.caption(f"🗂️ {len(nomes_abas)} aba(s) carregada(s) da fonte — 100% dos registros.")
    tabs = st.tabs(rotulos)

    with tabs[0]:
        renderizar_visao_executiva(df_principal, abas)

    for tab, nome_aba in zip(tabs[1:], nomes_abas):
        with tab:
            st.caption(f"Fonte: aba “{nome_aba}” da planilha oficial · {len(abas[nome_aba])} registros")
            renderizar_aba(abas[nome_aba], nome_aba)


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
