"""
NRC PAINEL GERENCIAL
Painel gerencial das Unidades Interligadas - NRC/COGEX/TJMA
Dados carregados automaticamente da planilha Google Sheets publicada em CSV
(ou, opcionalmente, de um arquivo CSV/XLSX enviado manualmente, com suporte
a múltiplas abas).

IMPORTANTE - sobre sanitização dos dados:
Toda limpeza/normalização feita aqui (remover espaços, tratar células vazias,
classificar status etc.) acontece SOMENTE em memória, na cópia dos dados
carregada pelo app. O app é somente-leitura: ele nunca escreve, edita ou
apaga nada na planilha de origem (Google Sheets ou arquivo enviado). A
planilha original permanece intacta para qualquer outro processo de
push/get que dependa dela.

Como rodar localmente:
    streamlit run app.py

Deploy:
    1. Suba este repositório no GitHub.
    2. Em https://share.streamlit.io, aponte para o app.py.
    3. Configure em "Secrets" (Settings > Secrets) o usuário/senha reais,
       usando o modelo do arquivo .streamlit/secrets.toml.example.
"""

import io
import unicodedata
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="NRC PAINEL GERENCIAL",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta de cores institucional, usada de forma consistente nos gráficos
# do painel (Streamlit) e nos gráficos do relatório PDF.
COR_PRIMARIA = "#7A0C0C"      # vinho/bordô - identidade Judiciário
COR_SECUNDARIA = "#C9A227"    # dourado
COR_TEXTO_CLARO = "#FFFFFF"

STATUS_CORES = {
    "Ativa": "#2E7D32",                    # verde
    "Inativa": "#C62828",                  # vermelho
    "Em fase de reativação": "#1565C0",    # azul
    "Em fase de implantação": "#EF6C00",   # laranja
    "Outra situação": "#6A1B9A",           # roxo
    "Sem informação": "#757575",           # cinza
}
ORDEM_STATUS = list(STATUS_CORES.keys())

# URL da planilha Google Sheets publicada em formato CSV (fonte padrão).
# Para trocar a fonte de dados padrão, publique a planilha em
# Arquivo > Compartilhar > Publicar na Web > CSV, e cole o link abaixo.
DATA_URL_PADRAO = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vT73jQ3Ae7I0gSx-UqOvA3C_JznfDQYrb23nLx4jpQXH03i1-ocEzHxnRNZnYTTHQ/pub?output=csv"
)

COLUNAS_ESPERADAS = [
    "MUNICÍPIOS", "HOSPITAL", "DATA DA INSTALAÇÃO", "ESFERA", "SERVENTIA",
    "JUSTIÇA ABERTA", "HABILITAÇÃO CRC", "SITUAÇÃO ATUAL", "SITUAÇÃO GERAL",
    "ÍNDICES IBGE", "OBSERVAÇÕES",
]

# Lista oficial dos 217 municípios do Maranhão (fonte: IBGE), usada para
# calcular quais municípios ainda não possuem Unidade Interligada.
MUNICIPIOS_MA = [
    'Afonso Cunha',
    'Alcântara',
    'Aldeias Altas',
    'Altamira do Maranhão',
    'Alto Alegre do Maranhão',
    'Alto Alegre do Pindaré',
    'Alto Parnaíba',
    'Amapá do Maranhão',
    'Amarante do Maranhão',
    'Anajatuba',
    'Anapurus',
    'Apicum-Açu',
    'Araguanã',
    'Araioses',
    'Arame',
    'Arari',
    'Axixá',
    'Açailândia',
    'Bacabal',
    'Bacabeira',
    'Bacuri',
    'Bacurituba',
    'Balsas',
    'Barra do Corda',
    'Barreirinhas',
    'Barão de Grajaú',
    'Bela Vista do Maranhão',
    'Belágua',
    'Benedito Leite',
    'Bequimão',
    'Bernardo do Mearim',
    'Boa Vista do Gurupi',
    'Bom Jardim',
    'Bom Jesus das Selvas',
    'Bom Lugar',
    'Brejo',
    'Brejo de Areia',
    'Buriti',
    'Buriti Bravo',
    'Buriticupu',
    'Buritirana',
    'Cachoeira Grande',
    'Cajapió',
    'Cajari',
    'Campestre do Maranhão',
    'Cantanhede',
    'Capinzal do Norte',
    'Carolina',
    'Carutapera',
    'Caxias',
    'Cedral',
    'Central do Maranhão',
    'Centro Novo do Maranhão',
    'Centro do Guilherme',
    'Chapadinha',
    'Cidelândia',
    'Codó',
    'Coelho Neto',
    'Colinas',
    'Conceição do Lago-Açu',
    'Coroatá',
    'Cururupu',
    'Cândido Mendes',
    'Davinópolis',
    'Dom Pedro',
    'Duque Bacelar',
    'Esperantinópolis',
    'Estreito',
    'Feira Nova do Maranhão',
    'Fernando Falcão',
    'Formosa da Serra Negra',
    'Fortaleza dos Nogueiras',
    'Fortuna',
    'Godofredo Viana',
    'Gonçalves Dias',
    'Governador Archer',
    'Governador Edison Lobão',
    'Governador Eugênio Barros',
    'Governador Luiz Rocha',
    'Governador Newton Bello',
    'Governador Nunes Freire',
    'Grajaú',
    'Graça Aranha',
    'Guimarães',
    'Humberto de Campos',
    'Icatu',
    'Igarapé Grande',
    'Igarapé do Meio',
    'Imperatriz',
    'Itaipava do Grajaú',
    'Itapecuru Mirim',
    'Itinga do Maranhão',
    'Jatobá',
    'Jenipapo dos Vieiras',
    'Joselândia',
    'João Lisboa',
    'Junco do Maranhão',
    'Lago Verde',
    'Lago da Pedra',
    'Lago do Junco',
    'Lago dos Rodrigues',
    'Lagoa Grande do Maranhão',
    'Lagoa do Mato',
    'Lajeado Novo',
    'Lima Campos',
    'Loreto',
    'Luís Domingues',
    'Magalhães de Almeida',
    'Maracaçumé',
    'Marajá do Sena',
    'Maranhãozinho',
    'Mata Roma',
    'Matinha',
    'Matões',
    'Matões do Norte',
    'Milagres do Maranhão',
    'Mirador',
    'Miranda do Norte',
    'Mirinzal',
    'Montes Altos',
    'Monção',
    'Morros',
    'Nina Rodrigues',
    'Nova Colinas',
    'Nova Iorque',
    'Nova Olinda do Maranhão',
    "Olho d'Água das Cunhãs",
    'Olinda Nova do Maranhão',
    'Palmeirândia',
    'Paraibano',
    'Parnarama',
    'Passagem Franca',
    'Pastos Bons',
    'Paulino Neves',
    'Paulo Ramos',
    'Paço do Lumiar',
    'Pedreiras',
    'Pedro do Rosário',
    'Penalva',
    'Peri Mirim',
    'Peritoró',
    'Pindaré-Mirim',
    'Pinheiro',
    'Pio XII',
    'Pirapemas',
    'Porto Franco',
    'Porto Rico do Maranhão',
    'Poção de Pedras',
    'Presidente Dutra',
    'Presidente Juscelino',
    'Presidente Médici',
    'Presidente Sarney',
    'Presidente Vargas',
    'Primeira Cruz',
    'Raposa',
    'Riachão',
    'Ribamar Fiquene',
    'Rosário',
    'Sambaíba',
    'Santa Filomena do Maranhão',
    'Santa Helena',
    'Santa Inês',
    'Santa Luzia',
    'Santa Luzia do Paruá',
    'Santa Quitéria do Maranhão',
    'Santa Rita',
    'Santana do Maranhão',
    'Santo Amaro do Maranhão',
    'Santo Antônio dos Lopes',
    'Satubinha',
    'Senador Alexandre Costa',
    'Senador La Rocque',
    'Serrano do Maranhão',
    'Sucupira do Norte',
    'Sucupira do Riachão',
    'São Benedito do Rio Preto',
    'São Bento',
    'São Bernardo',
    'São Domingos do Azeitão',
    'São Domingos do Maranhão',
    'São Francisco do Brejão',
    'São Francisco do Maranhão',
    'São Félix de Balsas',
    'São José de Ribamar',
    'São José dos Basílios',
    'São João Batista',
    'São João do Carú',
    'São João do Paraíso',
    'São João do Soter',
    'São João dos Patos',
    'São Luís',
    'São Luís Gonzaga do Maranhão',
    'São Mateus do Maranhão',
    'São Pedro da Água Branca',
    'São Pedro dos Crentes',
    'São Raimundo das Mangabeiras',
    'São Raimundo do Doca Bezerra',
    'São Roberto',
    'São Vicente Ferrer',
    'Sítio Novo',
    'Tasso Fragoso',
    'Timbiras',
    'Timon',
    'Trizidela do Vale',
    'Tufilândia',
    'Tuntum',
    'Turiaçu',
    'Turilândia',
    'Tutóia',
    'Urbano Santos',
    'Vargem Grande',
    'Viana',
    'Vila Nova dos Martírios',
    'Vitorino Freire',
    'Vitória do Mearim',
    'Zé Doca',
    'Água Doce do Maranhão',
]

def normalizar_nome(texto: str) -> str:
    """Remove acentos, espaços extras e padroniza para MAIÚSCULAS,
    para comparar nomes de município vindos de fontes diferentes."""
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
# CLASSIFICAÇÃO DE STATUS (robusta contra valores vazios/NaN/não-string)
# ----------------------------------------------------------------------------
def classificar_status(valor) -> str:
    if valor is None:
        return "Sem informação"
    v = str(valor).strip().upper()
    if v == "" or v == "NAN":
        return "Sem informação"
    if "IMPLANTA" in v or "PREVIS" in v or "EM PROCESSO" in v or "PROCESSO CNJ" in v:
        return "Em fase de implantação"
    if "REATIVA" in v:
        return "Em fase de reativação"
    if "NÃO" in v and "FUNCION" in v:
        return "Inativa"
    if "PAROU" in v or "PARALISAD" in v or "DESATIVAD" in v:
        return "Inativa"
    if "FUNCIONANDO" in v or v == "OK":
        return "Ativa"
    return "Outra situação"


# ----------------------------------------------------------------------------
# DETECÇÃO GENÉRICA DE COLUNAS (permite que abas com estrutura diferente
# ainda ganhem filtros/KPIs relevantes automaticamente)
# ----------------------------------------------------------------------------
def detectar_coluna(df: pd.DataFrame, candidatos) -> str:
    for c in df.columns:
        c_norm = normalizar_nome(c)
        for cand in candidatos:
            if normalizar_nome(cand) in c_norm:
                return c
    return None


# ----------------------------------------------------------------------------
# CARGA E TRATAMENTO DOS DADOS (sanitização só em memória, nunca grava
# de volta na planilha de origem)
# ----------------------------------------------------------------------------
def tratar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # remove eventual coluna de índice sem nome, vinda da planilha
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    df = df.drop(columns=unnamed, errors="ignore")

    # limpa espaços dos nomes de coluna
    df.columns = [str(c).strip() for c in df.columns]

    # limpa espaços em branco de TODAS as colunas, tratando NaN de forma
    # segura (independe do dtype interno usado pelo pandas)
    for c in df.columns:
        df[c] = df[c].apply(lambda x: "" if pd.isna(x) else str(x).strip())

    # coluna normalizada de status, usada nos filtros e KPIs
    col_status = detectar_coluna(df, ["SITUAÇÃO ATUAL", "SITUACAO ATUAL", "STATUS"])
    if col_status:
        df["STATUS_FUNCIONAMENTO"] = df[col_status].apply(classificar_status)
    else:
        df["STATUS_FUNCIONAMENTO"] = "Sem informação"

    return df


@st.cache_data(ttl=600, show_spinner="Carregando dados da planilha...")
def load_data_url(url: str) -> dict:
    """Retorna um dicionário {nome_da_aba: dataframe_tratado}."""
    df = pd.read_csv(url)
    return {"Unidades Interligadas": tratar_dataframe(df)}


def load_data_upload(arquivo) -> dict:
    """Lê CSV (1 aba) ou XLSX (todas as abas) e retorna
    {nome_da_aba: dataframe_tratado}."""
    nome = arquivo.name.lower()
    if nome.endswith(".csv"):
        df = pd.read_csv(arquivo)
        return {"Planilha enviada": tratar_dataframe(df)}
    else:
        planilhas = pd.read_excel(arquivo, sheet_name=None)
        return {aba: tratar_dataframe(df) for aba, df in planilhas.items()}


# ----------------------------------------------------------------------------
# SEÇÃO: MUNICÍPIOS SEM UNIDADE INTERLIGADA
# ----------------------------------------------------------------------------
def calcular_cobertura_municipios(df: pd.DataFrame, col_municipio: str):
    """Retorna (com_ui, sem_ui_lista_ordenada) comparando os municípios
    presentes nos dados com a lista oficial dos 217 municípios do MA."""
    if not col_municipio:
        return None, None
    municipios_com_dado = {
        normalizar_nome(m) for m in df[col_municipio].unique() if m
    }
    sem_ui_norm = set(MUNICIPIOS_MA_NORMALIZADOS.keys()) - municipios_com_dado
    sem_ui = sorted(MUNICIPIOS_MA_NORMALIZADOS[n] for n in sem_ui_norm)
    com_ui = len(MUNICIPIOS_MA_NORMALIZADOS) - len(sem_ui)
    return com_ui, sem_ui


def secao_municipios_sem_ui(df: pd.DataFrame, col_municipio: str):
    if not col_municipio:
        return

    com_ui, sem_ui = calcular_cobertura_municipios(df, col_municipio)

    st.markdown("#### Cobertura por município (base: 217 municípios do Maranhão)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de municípios do MA", len(MUNICIPIOS_MA_NORMALIZADOS))
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
# GRÁFICOS PARA O PDF (matplotlib, com a mesma paleta de cores do painel)
# ----------------------------------------------------------------------------
def _grafico_barras_png(labels, valores, cores, titulo, horizontal=False, figsize=(7.5, 4)):
    fig, ax = plt.subplots(figsize=figsize, dpi=170)
    if horizontal:
        ax.barh(labels, valores, color=cores)
        ax.invert_yaxis()
        ax.set_xlabel("Quantidade")
    else:
        ax.bar(labels, valores, color=cores)
        ax.set_ylabel("Quantidade")
        plt.setp(ax.get_xticklabels(), rotation=40, ha="right", fontsize=8)
    ax.set_title(titulo, fontsize=12, fontweight="bold", color=COR_PRIMARIA)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x" if horizontal else "y", linestyle="--", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


# ----------------------------------------------------------------------------
# RELATÓRIO PDF — timbrado, organizado e legível para impressão/anexo
# ----------------------------------------------------------------------------
def gerar_pdf(df_filtrado, df_completo, chave, col_municipio, col_esfera,
              col_situacao_geral, col_justica_aberta, col_crc, filtros_aplicados,
              logo_bytes=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.3 * cm,
        rightMargin=1.3 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.4 * cm,
        title=f"NRC Painel Gerencial - {chave}",
    )

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloRelatorio", parent=styles["Heading1"],
        fontSize=15, textColor=rl_colors.HexColor(COR_PRIMARIA), spaceAfter=2,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloRelatorio", parent=styles["Normal"],
        fontSize=9.5, textColor=rl_colors.HexColor("#444444"), spaceAfter=0,
    )
    estilo_secao = ParagraphStyle(
        "SecaoRelatorio", parent=styles["Heading2"],
        fontSize=12, textColor=rl_colors.HexColor(COR_PRIMARIA),
        spaceBefore=14, spaceAfter=6,
    )
    estilo_rodape_info = ParagraphStyle(
        "InfoRelatorio", parent=styles["Normal"], fontSize=8, textColor=rl_colors.grey,
    )

    elementos = []

    # ---------- CABEÇALHO / TIMBRE ----------
    texto_timbre = Paragraph(
        "<b>PODER JUDICIÁRIO DO ESTADO DO MARANHÃO</b><br/>"
        "Tribunal de Justiça do Maranhão — TJMA<br/>"
        "Corregedoria Geral de Justiça Extrajudicial — COGEX / NRC",
        ParagraphStyle("Timbre", parent=styles["Normal"], fontSize=10,
                       textColor=rl_colors.HexColor(COR_PRIMARIA), leading=13),
    )
    if logo_bytes:
        logo_img = Image(io.BytesIO(logo_bytes), width=2.1 * cm, height=2.1 * cm)
        tabela_timbre = Table([[logo_img, texto_timbre]], colWidths=[2.6 * cm, None])
    else:
        tabela_timbre = Table([[texto_timbre]], colWidths=[None])
    tabela_timbre.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, rl_colors.HexColor(COR_SECUNDARIA)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela_timbre)
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("NRC PAINEL GERENCIAL — RELATÓRIO DE UNIDADES INTERLIGADAS", estilo_titulo))
    elementos.append(Paragraph(f"Aba de dados: {chave}", estilo_subtitulo))
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    elementos.append(Paragraph(f"Gerado em {agora}", estilo_subtitulo))
    if filtros_aplicados:
        elementos.append(Paragraph(f"Filtros aplicados: {filtros_aplicados}", estilo_subtitulo))
    else:
        elementos.append(Paragraph("Filtros aplicados: nenhum (base completa)", estilo_subtitulo))
    elementos.append(Spacer(1, 6))

    # ---------- KPIs ----------
    total = len(df_filtrado)
    ativas = int((df_filtrado["STATUS_FUNCIONAMENTO"] == "Ativa").sum())
    inativas = int((df_filtrado["STATUS_FUNCIONAMENTO"] == "Inativa").sum())
    reativacao = int((df_filtrado["STATUS_FUNCIONAMENTO"] == "Em fase de reativação").sum())
    implantacao = int((df_filtrado["STATUS_FUNCIONAMENTO"] == "Em fase de implantação").sum())
    outros = total - ativas - inativas - reativacao - implantacao
    perc_ativas = (ativas / total * 100) if total else 0

    elementos.append(Paragraph("Indicadores gerais", estilo_secao))
    dados_kpi = [
        ["Total de\nunidades", "Ativas", "Inativas", "Em\nreativação", "Em\nimplantação",
         "Outras /\nsem info.", "% ativas"],
        [str(total), str(ativas), str(inativas), str(reativacao), str(implantacao),
         str(outros), f"{perc_ativas:.1f}%"],
    ]
    tabela_kpi = Table(dados_kpi, colWidths=[3.6 * cm] * 7)
    tabela_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor(COR_PRIMARIA)),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.6, rl_colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, 1), [rl_colors.HexColor("#FBF6EC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabela_kpi)
    elementos.append(Spacer(1, 10))

    # ---------- GRÁFICOS ----------
    elementos.append(Paragraph("Gráficos", estilo_secao))
    status_counts = df_filtrado["STATUS_FUNCIONAMENTO"].value_counts()
    cores_status = [STATUS_CORES.get(s, "#757575") for s in status_counts.index]
    graf_status = _grafico_barras_png(
        status_counts.index.tolist(), status_counts.values.tolist(), cores_status,
        "Unidades por status", horizontal=True, figsize=(6.2, 3.6),
    )

    linha_graficos = [Image(graf_status, width=9.5 * cm, height=5.5 * cm)]
    if col_municipio:
        top_mun = df_filtrado[col_municipio].value_counts().head(10)
        graf_municipios = _grafico_barras_png(
            top_mun.index.tolist(), top_mun.values.tolist(),
            [COR_PRIMARIA] * len(top_mun), "Top 10 municípios com mais unidades",
            horizontal=True, figsize=(6.2, 3.6),
        )
        linha_graficos.append(Image(graf_municipios, width=9.5 * cm, height=5.5 * cm))
    if col_esfera:
        esfera_counts = df_filtrado[df_filtrado[col_esfera] != ""][col_esfera].value_counts()
        if len(esfera_counts):
            graf_esfera = _grafico_barras_png(
                esfera_counts.index.tolist(), esfera_counts.values.tolist(),
                [COR_SECUNDARIA] * len(esfera_counts), "Unidades por esfera",
                horizontal=True, figsize=(6.2, 3.6),
            )
            linha_graficos.append(Image(graf_esfera, width=9.5 * cm, height=5.5 * cm))

    tabela_graficos = Table([linha_graficos])
    tabela_graficos.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(tabela_graficos)
    elementos.append(Spacer(1, 6))

    # ---------- COBERTURA DE MUNICÍPIOS ----------
    com_ui, sem_ui = calcular_cobertura_municipios(df_completo, col_municipio)
    if com_ui is not None:
        elementos.append(Paragraph(
            "Cobertura por município (base: 217 municípios do Maranhão)", estilo_secao
        ))
        dados_cobertura = [
            ["Total de municípios do MA", "Municípios com UI", "Municípios sem UI"],
            [str(len(MUNICIPIOS_MA_NORMALIZADOS)), str(com_ui), str(len(sem_ui))],
        ]
        tabela_cobertura = Table(dados_cobertura, colWidths=[7 * cm, 7 * cm, 7 * cm])
        tabela_cobertura.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor(COR_SECUNDARIA)),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.6, rl_colors.HexColor("#DDDDDD")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elementos.append(tabela_cobertura)

        if sem_ui:
            elementos.append(Spacer(1, 6))
            estilo_lista = ParagraphStyle("ListaMunicipios", parent=styles["Normal"], fontSize=8, leading=11)
            colunas_txt = 5
            linhas = [sem_ui[i:i + colunas_txt] for i in range(0, len(sem_ui), colunas_txt)]
            linhas_formatadas = [
                [Paragraph(f"• {m}", estilo_lista) for m in linha] +
                [Paragraph("", estilo_lista)] * (colunas_txt - len(linha))
                for linha in linhas
            ]
            tabela_sem_ui = Table(linhas_formatadas, colWidths=[4.6 * cm] * colunas_txt)
            tabela_sem_ui.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            elementos.append(tabela_sem_ui)

    elementos.append(PageBreak())

    # ---------- TABELA DETALHADA ----------
    elementos.append(Paragraph(f"Detalhamento das unidades ({total} registros)", estilo_secao))
    colunas_tabela = [c for c in df_filtrado.columns if c not in ("STATUS_FUNCIONAMENTO",)]
    # remove colunas muito longas/pouco relevantes para impressão, se existirem
    colunas_tabela = [c for c in colunas_tabela if c not in ("ÍNDICES IBGE",)]
    colunas_tabela = colunas_tabela + ["STATUS_FUNCIONAMENTO"]

    estilo_celula = ParagraphStyle("Celula", parent=styles["Normal"], fontSize=6.8, leading=8.2)
    estilo_cabecalho = ParagraphStyle(
        "Cabecalho", parent=styles["Normal"], fontSize=7.2, leading=8.5,
        textColor=rl_colors.white, fontName="Helvetica-Bold",
    )

    cabecalho = [Paragraph(c, estilo_cabecalho) for c in colunas_tabela]
    linhas_dados = [cabecalho]
    for _, linha in df_filtrado[colunas_tabela].iterrows():
        linhas_dados.append([Paragraph(str(v) if str(v) else "—", estilo_celula) for v in linha])

    largura_disponivel = landscape(A4)[0] - 2.6 * cm
    largura_col = largura_disponivel / len(colunas_tabela)
    tabela_dados = Table(linhas_dados, colWidths=[largura_col] * len(colunas_tabela), repeatRows=1)

    estilo_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor(COR_PRIMARIA)),
        ("GRID", (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    # zebra striping + destaque de cor por status na última coluna
    for i, (_, linha) in enumerate(df_filtrado[colunas_tabela].iterrows(), start=1):
        if i % 2 == 0:
            estilo_tabela.append(("BACKGROUND", (0, i), (-2, i), rl_colors.HexColor("#F7F7F7")))
        status_valor = linha.get("STATUS_FUNCIONAMENTO", "")
        cor_status = STATUS_CORES.get(status_valor, "#757575")
        estilo_tabela.append(("BACKGROUND", (-1, i), (-1, i), rl_colors.HexColor(cor_status)))
        estilo_tabela.append(("TEXTCOLOR", (-1, i), (-1, i), rl_colors.white))
    tabela_dados.setStyle(TableStyle(estilo_tabela))
    elementos.append(tabela_dados)

    # ---------- RODAPÉ ----------
    def _rodape(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(rl_colors.grey)
        texto = (
            "NRC Painel Gerencial · COGEX/TJMA · Documento gerado automaticamente "
            "a partir da planilha de origem, apenas para fins de consulta gerencial."
        )
        canvas.drawString(1.3 * cm, 0.9 * cm, texto)
        canvas.drawRightString(
            landscape(A4)[0] - 1.3 * cm, 0.9 * cm, f"Página {doc_.page}"
        )
        canvas.restoreState()

    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer.getvalue()


# ----------------------------------------------------------------------------
# RENDERIZAÇÃO DE UMA ABA (genérica: se as colunas esperadas não existirem,
# ainda assim mostra filtros/tabela com o que houver disponível)
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

    # KPIs principais
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

    # KPIs complementares (indicadores adicionais)
    perc_ativas = (ativas / total * 100) if total else 0
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("📈 % de unidades ativas", f"{perc_ativas:.1f}%")
    if col_municipio and total:
        municipio_top = df_filtrado[col_municipio].value_counts().idxmax()
        qtd_top = df_filtrado[col_municipio].value_counts().max()
        d2.metric("🏙️ Município com mais unidades", municipio_top, f"{qtd_top} unidade(s)")
    if col_justica_aberta:
        sim_ja = df_filtrado[col_justica_aberta].astype(str).str.upper().str.startswith("S").sum()
        d3.metric("⚖️ Justiça Aberta = Sim", int(sim_ja))
    if col_crc:
        sim_crc = df_filtrado[col_crc].astype(str).str.upper().str.startswith("S").sum()
        d4.metric("📝 Habilitação CRC = Sim", int(sim_crc))

    st.markdown("---")

    # gráficos com biblioteca nativa do streamlit, com cores semânticas
    # (verde=ativa, vermelho=inativa, azul=reativação, laranja=implantação)
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### Unidades por status")
        status_counts = df_filtrado["STATUS_FUNCIONAMENTO"].value_counts()
        df_status = pd.DataFrame({
            "Status": status_counts.index,
            "Quantidade": status_counts.values,
        })
        df_status["Cor"] = df_status["Status"].map(STATUS_CORES).fillna("#757575")
        st.bar_chart(df_status, x="Status", y="Quantidade", color="Cor", horizontal=True)
    with g2:
        if col_esfera:
            st.markdown("#### Unidades por esfera")
            esfera_counts = df_filtrado[df_filtrado[col_esfera] != ""][col_esfera].value_counts()
            st.bar_chart(esfera_counts, color=COR_PRIMARIA)

    if col_justica_aberta or col_crc:
        g3, g4 = st.columns(2)
        with g3:
            if col_justica_aberta:
                st.markdown("#### Justiça Aberta")
                st.bar_chart(df_filtrado[col_justica_aberta].value_counts(), color=COR_SECUNDARIA)
        with g4:
            if col_crc:
                st.markdown("#### Habilitação CRC")
                st.bar_chart(df_filtrado[col_crc].value_counts(), color="#1565C0")

    if col_situacao_geral:
        st.markdown("#### Unidades por situação geral")
        st.bar_chart(
            df_filtrado[df_filtrado[col_situacao_geral] != ""][col_situacao_geral].value_counts(),
            color="#6A1B9A",
        )

    if col_municipio:
        st.markdown("#### Top 15 municípios com mais unidades")
        st.bar_chart(df_filtrado[col_municipio].value_counts().head(15), color=COR_PRIMARIA)

    st.markdown("---")

    # cobertura de municípios sem UI (calculada sobre a base completa da
    # aba, não sobre o recorte filtrado, para refletir a realidade toda)
    secao_municipios_sem_ui(df, col_municipio)

    st.markdown("---")

    # tabela detalhada
    st.markdown(f"#### Detalhamento ({total} registros)")
    colunas_exibir = [c for c in df_filtrado.columns if c != "STATUS_FUNCIONAMENTO"]
    colunas_exibir += ["STATUS_FUNCIONAMENTO"]
    st.dataframe(df_filtrado[colunas_exibir], use_container_width=True, hide_index=True)

    col_csv, col_pdf = st.columns(2)

    with col_csv:
        csv_download = df_filtrado[colunas_exibir].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Baixar dados filtrados (CSV)",
            data=csv_download,
            file_name=f"nrc_{chave.lower().replace(' ', '_')}_filtrado.csv",
            mime="text/csv",
            key=f"download_{chave}",
            use_container_width=True,
        )

    with col_pdf:
        filtros_texto = "; ".join(
            f"{label}: {', '.join(valores)}"
            for label, valores in [
                ("Município", f_municipio), ("Esfera", f_esfera), ("Status", f_status),
                ("Situação geral", f_situacao_geral), ("Justiça Aberta", f_justica_aberta),
                ("CRC", f_crc), ("Serventia", f_serventia),
            ]
            if valores
        )
        if busca:
            filtros_texto += f"{'; ' if filtros_texto else ''}Busca: \"{busca}\""

        if st.button("📄 Gerar relatório em PDF", key=f"gerar_pdf_{chave}", use_container_width=True):
            with st.spinner("Montando relatório em PDF..."):
                pdf_bytes = gerar_pdf(
                    df_filtrado=df_filtrado,
                    df_completo=df,
                    chave=chave,
                    col_municipio=col_municipio,
                    col_esfera=col_esfera,
                    col_situacao_geral=col_situacao_geral,
                    col_justica_aberta=col_justica_aberta,
                    col_crc=col_crc,
                    filtros_aplicados=filtros_texto,
                    logo_bytes=st.session_state.get("logo_bytes"),
                )
            st.session_state[f"pdf_bytes_{chave}"] = pdf_bytes

        if st.session_state.get(f"pdf_bytes_{chave}"):
            st.download_button(
                "⬇️ Baixar relatório PDF",
                data=st.session_state[f"pdf_bytes_{chave}"],
                file_name=f"nrc_relatorio_{chave.lower().replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"download_pdf_{chave}",
                use_container_width=True,
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

        st.markdown("### Relatório PDF")
        logo_upload = st.file_uploader(
            "Brasão/logo para o timbre (opcional)", type=["png", "jpg", "jpeg"],
            help="Envie o brasão do TJMA/COGEX para aparecer no cabeçalho do PDF. "
                 "Se não enviar, o relatório sai só com o timbre em texto.",
        )
        if logo_upload is not None:
            st.session_state["logo_bytes"] = logo_upload.read()

    # cabeçalho
    st.markdown("## 🏛️ NRC PAINEL GERENCIAL")
    st.caption("Unidades Interligadas - Corregedoria Geral de Justiça Extrajudicial (COGEX/MA)")

    nomes_abas = list(abas.keys())
    if len(nomes_abas) == 1:
        renderizar_aba(abas[nomes_abas[0]], nomes_abas[0])
    else:
        tabs = st.tabs(nomes_abas)
        for tab, nome_aba in zip(tabs, nomes_abas):
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
