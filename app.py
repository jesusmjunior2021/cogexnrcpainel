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

import unicodedata

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
def secao_municipios_sem_ui(df: pd.DataFrame, col_municipio: str):
    if not col_municipio:
        return

    municipios_com_dado = {
        normalizar_nome(m) for m in df[col_municipio].unique() if m
    }
    sem_ui_norm = set(MUNICIPIOS_MA_NORMALIZADOS.keys()) - municipios_com_dado
    sem_ui = sorted(MUNICIPIOS_MA_NORMALIZADOS[n] for n in sem_ui_norm)
    com_ui = len(MUNICIPIOS_MA_NORMALIZADOS) - len(sem_ui)

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

    # KPIs
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

    # gráficos com biblioteca nativa do streamlit (sem libs externas)
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

    # cobertura de municípios sem UI (calculada sobre a base completa da
    # aba, não sobre o recorte filtrado, para refletir a realidade toda)
    secao_municipios_sem_ui(df, col_municipio)

    st.markdown("---")

    # tabela detalhada
    st.markdown(f"#### Detalhamento ({total} registros)")
    colunas_exibir = [c for c in df_filtrado.columns if c != "STATUS_FUNCIONAMENTO"]
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
