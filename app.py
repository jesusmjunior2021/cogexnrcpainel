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
    initial_sidebar_state="expanded",
)

DATA_URL_PADRAO = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vT73jQ3Ae7I0gSx-UqOvA3C_JznfDQYrb23nLx4jpQXH03i1-ocEzHxnRNZnYTTHQ/pub?output=csv"
)

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
    df.columns = [str(c).strip() for c in df.columns]

    for c in df.columns:
        df[c] = df[c].apply(lambda x: "" if pd.isna(x) else str(x).strip())

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


@st.cache_data(ttl=600, show_spinner="Carregando dados da planilha...")
def load_data_url(url: str) -> dict:
    df = pd.read_csv(url)
    return {"Unidades Interligadas": tratar_dataframe(df)}


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
            f"<table><thead><tr><th>#</th>{cabecalho}</tr></thead>"
            f"<tbody>{corpo}</tbody></table>"
        )
    else:
        tabela = "<p><em>Nenhum registro nesta categoria.</em></p>"

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>{titulo}</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; color:#1a1a1a; margin:32px; }}
  .cab {{ text-align:center; border-bottom:3px solid #7b1f24; padding-bottom:12px; margin-bottom:18px; }}
  .cab h1 {{ margin:0; font-size:20px; }}
  .cab h2 {{ margin:4px 0 0; font-size:14px; font-weight:normal; color:#555; }}
  .cab .org {{ font-size:12px; color:#7b1f24; font-weight:bold; letter-spacing:1px; }}
  .kpis {{ display:flex; gap:14px; flex-wrap:wrap; margin:16px 0; }}
  .kpi {{ border:1px solid #ccc; border-radius:8px; padding:10px 18px; text-align:center; min-width:130px; }}
  .kpi-num {{ font-size:26px; font-weight:bold; color:#7b1f24; }}
  .kpi-lab {{ font-size:11px; color:#555; text-transform:uppercase; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; margin-top:10px; }}
  th, td {{ border:1px solid #bbb; padding:5px 7px; text-align:left; }}
  th {{ background:#7b1f24; color:#fff; }}
  tr:nth-child(even) td {{ background:#f6f2f2; }}
  .rod {{ margin-top:24px; font-size:11px; color:#777; border-top:1px solid #ccc; padding-top:8px; }}
  @media print {{ body {{ margin:12mm; }} }}
</style></head><body>
<div class="cab">
  <div class="org">PODER JUDICIÁRIO · TRIBUNAL DE JUSTIÇA DO MARANHÃO</div>
  <h1>Corregedoria-Geral do Foro Extrajudicial — COGEX/MA</h1>
  <h2>Núcleo de Registro Civil (NRC) — Unidades Interligadas</h2>
</div>
<h2 style="text-align:center;">{titulo}</h2>
<p style="text-align:center; color:#555;">{subtitulo}</p>
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
def renderizar_visao_executiva(df: pd.DataFrame):
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

    # LINHA 3 — alerta de produção
    c1, c2 = st.columns([1, 3])
    c1.metric("⚠️ Ativas SEM produção / índice baixo", len(ex["ativas_sem_producao"]))
    with c2:
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

    # ---------------- CENTRAL DE RELATÓRIOS ----------------
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

    d1, d2 = st.columns(2)
    with d1:
        csv_bytes = df_rel[cols_rel].to_csv(index=False).encode("utf-8-sig") if len(df_rel) else "sem registros".encode("utf-8")
        st.download_button(
            "⬇️ Baixar CSV desta categoria",
            data=csv_bytes,
            file_name=f"nrc_relatorio_{normalizar_nome(escolha).lower().replace(' ', '_')[:60]}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with d2:
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
            "Status (Ativa/Inativa/...)", "STATUS_FUNCIONAMENTO", "status"
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

    st.markdown("---")

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
    secao_municipios_sem_ui(df, col_municipio)
    st.markdown("---")

    st.markdown(f"#### Detalhamento ({total} registros)")
    colunas_exibir = [c for c in df_filtrado.columns
                      if c not in ("STATUS_FUNCIONAMENTO", "ALERTA_SEM_PRODUCAO")]
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
                abas = load_data_url(DATA_URL_PADRAO)
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

    nomes_abas = list(abas.keys())

    # A primeira aba de dados alimenta a Visão Executiva; se houver várias
    # abas no XLSX, a executiva usa a primeira (base principal de UIs).
    df_principal = abas[nomes_abas[0]]

    nomes_tabs = ["📋 Visão Executiva"] + nomes_abas
    tabs = st.tabs(nomes_tabs)

    with tabs[0]:
        renderizar_visao_executiva(df_principal)

    for tab, nome_aba in zip(tabs[1:], nomes_abas):
        with tab:
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
