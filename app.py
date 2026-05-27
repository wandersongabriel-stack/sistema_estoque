import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import html
from datetime import datetime

st.set_page_config(
    page_title="Sistema de Estoque",
    layout="wide"
)


def aplicar_estilo_botoes_centralizados():
    st.markdown(
        """
        <style>
            div.stButton {
                display: flex;
                justify-content: center;
            }

            div.stFormSubmitButton {
                display: flex;
                justify-content: center;
            }

            div.stButton > button,
            div.stFormSubmitButton > button {
                min-width: 120px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )


aplicar_estilo_botoes_centralizados()


TEMPO_ALERTA_MS = 6000


def exibir_alerta_temporario(mensagem, tipo="info", duracao_ms=TEMPO_ALERTA_MS):
    mensagem = str(mensagem or "").strip()

    if not mensagem:
        return

    estilos = {
        "success": {
            "background": "#0f5132",
            "color": "#d1e7dd",
            "border": "#198754",
        },
        "error": {
            "background": "#3f1d26",
            "color": "#ffb3c1",
            "border": "#842029",
        },
        "warning": {
            "background": "#4d3b12",
            "color": "#ffe8a1",
            "border": "#997404",
        },
        "info": {
            "background": "#16324f",
            "color": "#cfe2ff",
            "border": "#084298",
        },
    }

    estilo = estilos.get(tipo, estilos["info"])
    mensagem_segura = html.escape(mensagem)
    alerta_id = f"alerta_{abs(hash((mensagem, tipo, datetime.now().timestamp())))}"
    duracao_segundos = max(float(duracao_ms) / 1000, 1)

    st.markdown(
        f"""
        <style>
            @keyframes esconder_{alerta_id} {{
                0% {{ opacity: 1; visibility: visible; }}
                80% {{ opacity: 1; visibility: visible; }}
                100% {{ opacity: 0; visibility: hidden; }}
            }}

            #{alerta_id} {{
                position: fixed;
                top: 0.75rem;
                left: 50%;
                transform: translateX(-50%);
                width: min(1100px, calc(100vw - 2rem));
                z-index: 999999;
                background-color: {estilo["background"]};
                color: {estilo["color"]};
                border: 1px solid {estilo["border"]};
                border-radius: 0.5rem;
                padding: 0.9rem 1rem;
                font-weight: 600;
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.35);
                pointer-events: none;
                animation: esconder_{alerta_id} {duracao_segundos}s forwards;
            }}
        </style>

        <div id="{alerta_id}">{mensagem_segura}</div>
        """,
        unsafe_allow_html=True
    )

SHEET_URL = st.secrets["SHEET_URL"]
GID_PRODUTOS = st.secrets["GID_PRODUTOS"]
GID_MOVIMENTACOES = st.secrets["GID_MOVIMENTACOES"]
GID_KITS = st.secrets["GID_KITS"]
GID_COMPOSICAO_KITS = st.secrets["GID_COMPOSICAO_KITS"]
APPS_SCRIPT_URL = st.secrets["APPS_SCRIPT_URL"]



PERMISSOES_POR_PERFIL = {
    "admin": [
        "Consulta de Estoque",
        "Entrada de Produtos",
        "Avaria",
        "Saída de Produtos",
        "Cadastro de Produtos",
        "Edição de Produtos",
        "Consulta de Kits",
        "Histórico",
    ],
    "entrada": [
        "Consulta de Estoque",
        "Entrada de Produtos",
        "Avaria",
        "Edição de Produtos",
        "Consulta de Kits",
        "Histórico",
    ],
    "saida": [
        "Consulta de Estoque",
        "Saída de Produtos",
        "Consulta de Kits",
        "Histórico",
    ],
}


PERMISSOES_HISTORICO = {
    "admin": ["excluir_entrada", "excluir_avaria", "cancelar_saida"],
    "entrada": ["excluir_entrada", "excluir_avaria"],
    "saida": ["cancelar_saida"],
}


def obter_usuarios_configurados():
    try:
        return st.secrets["usuarios"]
    except Exception:
        return {}


def autenticar_usuario(usuario, senha):
    usuarios = obter_usuarios_configurados()
    usuario = str(usuario or "").strip()
    senha = str(senha or "")

    if not usuario or not senha:
        return None

    try:
        dados_usuario = usuarios[usuario]
    except Exception:
        return None

    senha_correta = str(dados_usuario.get("senha", ""))
    perfil = str(dados_usuario.get("perfil", "")).strip().lower()

    if senha != senha_correta:
        return None

    if perfil not in PERMISSOES_POR_PERFIL:
        return None

    return {
        "usuario": usuario,
        "perfil": perfil
    }


def perfil_atual():
    return str(st.session_state.get("perfil", "")).strip().lower()


def usuario_tem_acesso(tela):
    perfil = perfil_atual()
    return tela in PERMISSOES_POR_PERFIL.get(perfil, [])


def usuario_pode_acao_historico(acao):
    perfil = perfil_atual()
    return acao in PERMISSOES_HISTORICO.get(perfil, [])


def primeira_tela_permitida():
    perfil = perfil_atual()
    telas = PERMISSOES_POR_PERFIL.get(perfil, [])
    if telas:
        return telas[0]
    return "Consulta de Estoque"


def tela_login():
    st.title("Sistema de Estoque")
    st.subheader("Login")

    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")

    if entrar:
        dados_login = autenticar_usuario(usuario, senha)

        if dados_login is None:
            exibir_alerta_temporario("Usuário ou senha inválidos.", tipo="error")
            st.stop()

        st.session_state["autenticado"] = True
        st.session_state["usuario"] = dados_login["usuario"]
        st.session_state["perfil"] = dados_login["perfil"]
        st.session_state["menu_principal"] = primeira_tela_permitida()
        st.rerun()

    st.stop()


def exigir_login():
    if not st.session_state.get("autenticado", False):
        tela_login()


def sair_do_sistema():
    chaves_para_limpar = [
        "autenticado",
        "usuario",
        "perfil",
        "confirmar_entrada",
        "confirmar_avaria",
        "confirmar_cadastro",
        "confirmar_edicao",
        "confirmar_saida",
        "erro_confirmar_saida",
        "erro_saida_form",
        "rascunho_saida",
        "entrada_processando",
        "avaria_processando",
        "saida_processando",
        "simulacao_saida",
        "cadastro_processando",
        "edicao_processando",
        "confirmar_exclusao_entrada",
        "confirmar_exclusao_avaria",
        "confirmar_cancelamento_saida",
        "exclusao_entrada_processando",
        "exclusao_avaria_processando",
        "cancelamento_saida_processando",
        "cancelamento_processando",
    ]

    for chave in chaves_para_limpar:
        if chave in st.session_state:
            del st.session_state[chave]

    st.rerun()

def gerar_url_csv(sheet_url, gid):
    base_url = sheet_url.split("/edit")[0]
    return f"{base_url}/export?format=csv&gid={gid}"


def carregar_aba(gid):
    url_csv = gerar_url_csv(SHEET_URL, gid)
    return pd.read_csv(url_csv)


def carregar_dados():
    produtos = carregar_aba(GID_PRODUTOS)
    movimentacoes = carregar_aba(GID_MOVIMENTACOES)
    kits = carregar_aba(GID_KITS)
    composicao_kits = carregar_aba(GID_COMPOSICAO_KITS)

    if movimentacoes.empty:
        movimentacoes = pd.DataFrame(columns=[
            "id",
            "codigo_produto",
            "tipo",
            "pedido",
            "quantidade",
            "observacao",
            "criado_em"
        ])

    if kits.empty:
        kits = pd.DataFrame(columns=[
            "codigo_kit",
            "nome_kit",
            "tipo",
            "ativo",
            "criado_em",
            "atualizado_em"
        ])

    if composicao_kits.empty:
        composicao_kits = pd.DataFrame(columns=[
            "id",
            "codigo_kit",
            "tipo_item",
            "codigo_item",
            "quantidade",
            "ativo",
            "criado_em"
        ])

    return produtos, movimentacoes, kits, composicao_kits


def tratar_produtos(produtos):
    produtos = produtos.copy()

    produtos["codigo"] = produtos["codigo"].astype(str)

    produtos["estoque_atual"] = pd.to_numeric(
        produtos["estoque_atual"],
        errors="coerce"
    ).fillna(0)

    produtos["estoque_minimo"] = pd.to_numeric(
        produtos["estoque_minimo"],
        errors="coerce"
    ).fillna(0)

    return produtos

def recalcular_status_produtos(produtos):
    produtos = produtos.copy()

    def calcular_status_linha(row):
        estoque_atual = float(row["estoque_atual"])
        estoque_minimo = float(row["estoque_minimo"])

        if estoque_atual <= 0:
            return "SEM ESTOQUE"

        if estoque_atual <= estoque_minimo:
            return "ACABANDO"

        return "OK"

    produtos["status"] = produtos.apply(calcular_status_linha, axis=1)

    return produtos

def produto_nome_ja_existe(produtos, nome, codigo_ignorar=None):
    nome_comparacao = str(nome).strip().lower()

    if not nome_comparacao:
        return False

    produtos_validacao = produtos.copy()
    produtos_validacao["codigo"] = produtos_validacao["codigo"].astype(str)
    produtos_validacao["nome"] = produtos_validacao["nome"].astype(str)

    if codigo_ignorar is not None:
        produtos_validacao = produtos_validacao[
            produtos_validacao["codigo"] != str(codigo_ignorar)
        ]

    nomes_existentes = (
        produtos_validacao["nome"]
        .str.strip()
        .str.lower()
        .tolist()
    )

    return nome_comparacao in nomes_existentes



def pedido_saida_ja_existe(movimentacoes, pedido):
    pedido_comparacao = str(pedido or "").strip().lower()

    if not pedido_comparacao:
        return False

    if movimentacoes is None or movimentacoes.empty:
        return False

    if "tipo" not in movimentacoes.columns or "pedido" not in movimentacoes.columns:
        return False

    movimentacoes_validacao = movimentacoes.copy()

    tipos_saida_ativos = ["SAIDA_TORRE", "SAIDA_ILHA", "SAIDA_OUTROS"]

    movimentacoes_validacao["tipo"] = (
        movimentacoes_validacao["tipo"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    movimentacoes_validacao["pedido"] = (
        movimentacoes_validacao["pedido"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    pedidos_encontrados = movimentacoes_validacao[
        movimentacoes_validacao["tipo"].isin(tipos_saida_ativos)
        & (movimentacoes_validacao["pedido"] == pedido_comparacao)
    ]

    return not pedidos_encontrados.empty


def montar_composicao_completa(codigo_kit, quantidade_base, kits, composicao_kits, produtos, nivel=0):
    itens_finais = []

    composicao = composicao_kits[
        (composicao_kits["codigo_kit"] == str(codigo_kit)) &
        (composicao_kits["ativo"] == "SIM")
    ].copy()

    for _, item in composicao.iterrows():
        tipo_item = str(item["tipo_item"]).strip()
        codigo_item = str(item["codigo_item"]).strip()
        quantidade_item = float(item["quantidade"]) * float(quantidade_base)

        if tipo_item == "PRODUTO":
            produto = produtos[
                produtos["codigo"].astype(str) == codigo_item
            ]

            if produto.empty:
                nome_produto = "Produto não encontrado"
                unidade = ""
                estoque_atual = 0
            else:
                nome_produto = produto.iloc[0]["nome"]
                unidade = produto.iloc[0]["unidade"]
                estoque_atual = produto.iloc[0]["estoque_atual"]

            itens_finais.append({
                "codigo_produto": codigo_item,
                "produto": nome_produto,
                "quantidade": quantidade_item,
                "unidade": unidade,
                "estoque_atual": estoque_atual,
                "origem": codigo_kit,
                "nivel": nivel
            })

        elif tipo_item == "KIT":
            itens_do_subkit = montar_composicao_completa(
                codigo_kit=codigo_item,
                quantidade_base=quantidade_item,
                kits=kits,
                composicao_kits=composicao_kits,
                produtos=produtos,
                nivel=nivel + 1
            )

            itens_finais.extend(itens_do_subkit)

    return itens_finais


def montar_saida(tipo_saida, tipo_monzi, kits, composicao_kits, produtos):
    tipo_saida = str(tipo_saida).strip().upper()
    tipo_monzi = str(tipo_monzi).strip()

    if tipo_saida == "ILHA":
        codigo_kit_principal = "KIT7"
    else:
        codigo_kit_principal = "KIT1"
        tipo_saida = "TORRE"

    kits_para_baixar = [
        {"codigo_kit": codigo_kit_principal, "quantidade": 1}
    ]

    if tipo_saida == "ILHA":
        if tipo_monzi == "Prata":
            kits_para_baixar.append({"codigo_kit": "KIT4", "quantidade": 2})
        elif tipo_monzi == "Amarelo":
            kits_para_baixar.append({"codigo_kit": "KIT5", "quantidade": 2})
        elif tipo_monzi == "Ambos":
            # Ilha leva 2 Monzis. Em "Ambos", baixa 1 prata e 1 amarelo.
            kits_para_baixar.append({"codigo_kit": "KIT4", "quantidade": 1})
            kits_para_baixar.append({"codigo_kit": "KIT5", "quantidade": 1})
    else:
        if tipo_monzi == "Prata":
            kits_para_baixar.append({"codigo_kit": "KIT4", "quantidade": 1})
        elif tipo_monzi == "Amarelo":
            kits_para_baixar.append({"codigo_kit": "KIT5", "quantidade": 1})
        elif tipo_monzi == "Ambos":
            kits_para_baixar.append({"codigo_kit": "KIT4", "quantidade": 1})
            kits_para_baixar.append({"codigo_kit": "KIT5", "quantidade": 1})

    itens_saida = []

    for kit_baixa in kits_para_baixar:
        itens_do_kit = montar_composicao_completa(
            codigo_kit=kit_baixa["codigo_kit"],
            quantidade_base=kit_baixa["quantidade"],
            kits=kits,
            composicao_kits=composicao_kits,
            produtos=produtos
        )

        itens_saida.extend(itens_do_kit)

    if not itens_saida:
        return pd.DataFrame()

    df_saida = pd.DataFrame(itens_saida)

    df_saida = (
        df_saida
        .groupby(["codigo_produto", "produto", "unidade"], as_index=False)
        .agg({
            "quantidade": "sum",
            "estoque_atual": "max"
        })
    )

    df_saida["saldo_apos_saida"] = (
        df_saida["estoque_atual"] - df_saida["quantidade"]
    )

    df_saida["status"] = df_saida["saldo_apos_saida"].apply(
        lambda saldo: "INSUFICIENTE" if saldo < 0 else "OK"
    )

    return df_saida


def montar_saida_torre(quantidade_torres, tipo_monzi, kits, composicao_kits, produtos):
    # Mantido apenas por compatibilidade com versões anteriores do app.
    return montar_saida(
        tipo_saida="TORRE",
        tipo_monzi=tipo_monzi,
        kits=kits,
        composicao_kits=composicao_kits,
        produtos=produtos
    )


def obter_definicoes_checklist(tipo_saida, tipo_monzi):
    tipo_saida = str(tipo_saida).strip().upper()
    tipo_monzi = str(tipo_monzi).strip()

    if tipo_saida == "ILHA":
        definicoes = [
            {
                "chave": "flyer_institucional",
                "grupo": "Flyer ilha institucional",
                "codigos": ["24"],
                "padrao": 2,
                "quantidades_por_unidade": {"24": 1}
            },
            {
                "chave": "flyer_promocional",
                "grupo": "Flyer ilha promocional",
                "codigos": ["25"],
                "padrao": 1,
                "quantidades_por_unidade": {"25": 1}
            },
            {
                "chave": "fragrancia",
                "grupo": "Fragrância",
                "codigos": ["3", "4", "5"],
                "padrao": 2,
                "quantidades_por_unidade": {"3": 1, "4": 1, "5": 30}
            },
            {
                "chave": "cartao_fragrancia",
                "grupo": "Cartão fragrância",
                "codigos": ["6"],
                "padrao": 1,
                "quantidades_por_unidade": {"6": 1}
            },
            {
                "chave": "urna",
                "grupo": "Urna",
                "codigos": ["10"],
                "padrao": 1,
                "quantidades_por_unidade": {"10": 1}
            },
            {
                "chave": "blocos_cupons",
                "grupo": "Blocos cupons",
                "codigos": ["11"],
                "padrao": 6,
                "quantidades_por_unidade": {"11": 1}
            },
            {
                "chave": "garantia",
                "grupo": "Garantia",
                "codigos": ["12"],
                "padrao": 300,
                "quantidades_por_unidade": {"12": 1}
            },
            {
                "chave": "envelopes",
                "grupo": "Envelopes",
                "codigos": ["13"],
                "padrao": 150,
                "quantidades_por_unidade": {"13": 1}
            },
            {
                "chave": "sacolas",
                "grupo": "Sacolas",
                "codigos": ["14"],
                "padrao": 120,
                "quantidades_por_unidade": {"14": 1}
            },
            {
                "chave": "manual_uso",
                "grupo": "Manual de uso",
                "codigos": ["15"],
                "padrao": 1,
                "quantidades_por_unidade": {"15": 1}
            },
            {
                "chave": "manual_montagem",
                "grupo": "Manual de montagem ilha",
                "codigos": ["23"],
                "padrao": 1,
                "quantidades_por_unidade": {"23": 1}
            },
            {
                "chave": "raspadinha",
                "grupo": "Raspadinha",
                "codigos": ["17"],
                "padrao": 2,
                "quantidades_por_unidade": {"17": 1}
            },
            {
                "chave": "revista_apresentacao",
                "grupo": "Revista apresentação",
                "codigos": ["18"],
                "padrao": 1,
                "quantidades_por_unidade": {"18": 1}
            },
            {
                "chave": "expositor_pulseira",
                "grupo": "Expositor pulseira",
                "codigos": ["19"],
                "padrao": 2,
                "quantidades_por_unidade": {"19": 1}
            },
            {
                "chave": "expositor_brinco",
                "grupo": "Expositor brinco",
                "codigos": ["20"],
                "padrao": 2,
                "quantidades_por_unidade": {"20": 1}
            },
            {
                "chave": "expositor_busto",
                "grupo": "Expositor busto",
                "codigos": ["21"],
                "padrao": 2,
                "quantidades_por_unidade": {"21": 1}
            },
            {
                "chave": "expositor_abaulado",
                "grupo": "Expositor abaulado",
                "codigos": ["22"],
                "padrao": 2,
                "quantidades_por_unidade": {"22": 1}
            },
            {
                "chave": "expositor_anel",
                "grupo": "Expositor anel",
                "codigos": ["26"],
                "padrao": 2,
                "quantidades_por_unidade": {"26": 1}
            },
        ]

        if tipo_monzi == "Prata":
            definicoes.insert(4, {
                "chave": "monzi_prata",
                "grupo": "Monzi prata",
                "codigos": ["7", "9"],
                "padrao": 2,
                "quantidades_por_unidade": {"7": 1, "9": 1}
            })
        elif tipo_monzi == "Amarelo":
            definicoes.insert(4, {
                "chave": "monzi_amarelo",
                "grupo": "Monzi amarelo",
                "codigos": ["8", "27"],
                "padrao": 2,
                "quantidades_por_unidade": {"8": 1, "27": 1}
            })
        else:
            definicoes.insert(4, {
                "chave": "monzi_prata",
                "grupo": "Monzi prata",
                "codigos": ["7", "9"],
                "padrao": 1,
                "quantidades_por_unidade": {"7": 1, "9": 1}
            })
            definicoes.insert(5, {
                "chave": "monzi_amarelo",
                "grupo": "Monzi amarelo",
                "codigos": ["8", "27"],
                "padrao": 1,
                "quantidades_por_unidade": {"8": 1, "27": 1}
            })

        return definicoes

    definicoes = [
        {
            "chave": "flyer_institucional",
            "grupo": "Flyer torre institucional",
            "codigos": ["1"],
            "padrao": 1,
            "quantidades_por_unidade": {"1": 1}
        },
        {
            "chave": "flyer_promocional",
            "grupo": "Flyer torre promocional",
            "codigos": ["2"],
            "padrao": 1,
            "quantidades_por_unidade": {"2": 1}
        },
        {
            "chave": "fragrancia",
            "grupo": "Fragrância",
            "codigos": ["3", "4", "5"],
            "padrao": 1,
            "quantidades_por_unidade": {"3": 1, "4": 1, "5": 30}
        },
        {
            "chave": "cartao_fragrancia",
            "grupo": "Cartão fragrância",
            "codigos": ["6"],
            "padrao": 1,
            "quantidades_por_unidade": {"6": 1}
        },
        {
            "chave": "urna",
            "grupo": "Urna",
            "codigos": ["10"],
            "padrao": 1,
            "quantidades_por_unidade": {"10": 1}
        },
        {
            "chave": "blocos_cupons",
            "grupo": "Blocos cupons",
            "codigos": ["11"],
            "padrao": 2,
            "quantidades_por_unidade": {"11": 1}
        },
        {
            "chave": "garantia",
            "grupo": "Garantia",
            "codigos": ["12"],
            "padrao": 100,
            "quantidades_por_unidade": {"12": 1}
        },
        {
            "chave": "envelopes",
            "grupo": "Envelopes",
            "codigos": ["13"],
            "padrao": 50,
            "quantidades_por_unidade": {"13": 1}
        },
        {
            "chave": "sacolas",
            "grupo": "Sacolas",
            "codigos": ["14"],
            "padrao": 40,
            "quantidades_por_unidade": {"14": 1}
        },
        {
            "chave": "manual_uso",
            "grupo": "Manual de uso",
            "codigos": ["15"],
            "padrao": 1,
            "quantidades_por_unidade": {"15": 1}
        },
        {
            "chave": "manual_montagem",
            "grupo": "Manual de montagem torre",
            "codigos": ["16"],
            "padrao": 1,
            "quantidades_por_unidade": {"16": 1}
        },
        {
            "chave": "raspadinha",
            "grupo": "Raspadinha",
            "codigos": ["17"],
            "padrao": 1,
            "quantidades_por_unidade": {"17": 1}
        },
        {
            "chave": "revista_apresentacao",
            "grupo": "Revista apresentação",
            "codigos": ["18"],
            "padrao": 1,
            "quantidades_por_unidade": {"18": 1}
        },
        {
            "chave": "expositor_pulseira",
            "grupo": "Expositor pulseira",
            "codigos": ["19"],
            "padrao": 1,
            "quantidades_por_unidade": {"19": 1}
        },
        {
            "chave": "expositor_brinco",
            "grupo": "Expositor brinco",
            "codigos": ["20"],
            "padrao": 1,
            "quantidades_por_unidade": {"20": 1}
        },
        {
            "chave": "expositor_busto",
            "grupo": "Expositor busto",
            "codigos": ["21"],
            "padrao": 1,
            "quantidades_por_unidade": {"21": 1}
        },
        {
            "chave": "expositor_abaulado",
            "grupo": "Expositor abaulado",
            "codigos": ["22"],
            "padrao": 1,
            "quantidades_por_unidade": {"22": 1}
        },
        {
            "chave": "expositor_anel",
            "grupo": "Expositor anel",
            "codigos": ["26"],
            "padrao": 1,
            "quantidades_por_unidade": {"26": 1}
        },
    ]

    if tipo_monzi == "Prata":
        definicoes.insert(4, {
            "chave": "monzi_prata",
            "grupo": "Monzi prata",
            "codigos": ["7", "9"],
            "padrao": 1,
            "quantidades_por_unidade": {"7": 1, "9": 1}
        })
    elif tipo_monzi == "Amarelo":
        definicoes.insert(4, {
            "chave": "monzi_amarelo",
            "grupo": "Monzi amarelo",
            "codigos": ["8", "27"],
            "padrao": 1,
            "quantidades_por_unidade": {"8": 1, "27": 1}
        })
    else:
        definicoes.insert(4, {
            "chave": "monzi_prata",
            "grupo": "Monzi prata",
            "codigos": ["7", "9"],
            "padrao": 1,
            "quantidades_por_unidade": {"7": 1, "9": 1}
        })
        definicoes.insert(5, {
            "chave": "monzi_amarelo",
            "grupo": "Monzi amarelo",
            "codigos": ["8", "27"],
            "padrao": 1,
            "quantidades_por_unidade": {"8": 1, "27": 1}
        })

    return definicoes


def aplicar_ajustes_checklist(df_saida, ajustes_checklist, tipo_saida, tipo_monzi, produtos=None):
    df_saida = df_saida.copy()

    quantidades_desejadas_por_codigo = {}

    for definicao in obter_definicoes_checklist(tipo_saida, tipo_monzi):
        chave = definicao["chave"]
        quantidade_desejada = float(ajustes_checklist.get(chave, definicao["padrao"]) or 0)

        for codigo, quantidade_por_unidade in definicao["quantidades_por_unidade"].items():
            codigo = str(codigo)
            quantidades_desejadas_por_codigo[codigo] = (
                quantidades_desejadas_por_codigo.get(codigo, 0)
                + (quantidade_desejada * float(quantidade_por_unidade))
            )

    produtos_lookup = pd.DataFrame()
    if produtos is not None:
        produtos_lookup = produtos.copy()
        if "codigo" in produtos_lookup.columns:
            produtos_lookup["codigo"] = produtos_lookup["codigo"].astype(str)

    for codigo_produto, quantidade_final in quantidades_desejadas_por_codigo.items():
        codigo_produto = str(codigo_produto)
        filtro = df_saida["codigo_produto"].astype(str) == codigo_produto

        if filtro.any():
            df_saida.loc[filtro, "quantidade"] = quantidade_final
        elif quantidade_final > 0 and not produtos_lookup.empty:
            produto = produtos_lookup[produtos_lookup["codigo"] == codigo_produto]

            if not produto.empty:
                linha_produto = produto.iloc[0]
                estoque_atual = float(linha_produto.get("estoque_atual", 0) or 0)

                df_saida = pd.concat(
                    [
                        df_saida,
                        pd.DataFrame([
                            {
                                "codigo_produto": codigo_produto,
                                "produto": linha_produto.get("nome", ""),
                                "quantidade": quantidade_final,
                                "unidade": linha_produto.get("unidade", ""),
                                "estoque_atual": estoque_atual,
                                "saldo_apos_saida": estoque_atual - quantidade_final,
                                "status": "INSUFICIENTE" if (estoque_atual - quantidade_final) < 0 else "OK"
                            }
                        ])
                    ],
                    ignore_index=True
                )

    codigos_controlados_checklist = set()
    for tipo_monzi_possivel in ["Prata", "Amarelo", "Ambos"]:
        for definicao in obter_definicoes_checklist(tipo_saida, tipo_monzi_possivel):
            for codigo in definicao.get("quantidades_por_unidade", {}).keys():
                codigos_controlados_checklist.add(str(codigo))

    codigos_desejados = set(str(codigo) for codigo in quantidades_desejadas_por_codigo.keys())
    codigos_para_remover = codigos_controlados_checklist - codigos_desejados

    if codigos_para_remover and not df_saida.empty:
        df_saida = df_saida[
            ~df_saida["codigo_produto"].astype(str).isin(codigos_para_remover)
        ].copy()

    df_saida = df_saida[df_saida["quantidade"] > 0].copy()

    if df_saida.empty:
        return df_saida

    df_saida = (
        df_saida
        .groupby(["codigo_produto", "produto", "unidade"], as_index=False)
        .agg({
            "quantidade": "sum",
            "estoque_atual": "max"
        })
    )

    df_saida["saldo_apos_saida"] = (
        df_saida["estoque_atual"] - df_saida["quantidade"]
    )

    df_saida["status"] = df_saida["saldo_apos_saida"].apply(
        lambda saldo: "INSUFICIENTE" if saldo < 0 else "OK"
    )

    return df_saida


def adicionar_produtos_extras(df_saida, produtos_extras, produtos):
    df_saida = df_saida.copy()
    linhas_extras = []

    produtos_lookup = produtos.copy()
    produtos_lookup["codigo"] = produtos_lookup["codigo"].astype(str)

    for extra in produtos_extras:
        codigo_produto = str(extra.get("codigo_produto", "")).strip()
        quantidade = float(extra.get("quantidade", 0) or 0)

        if not codigo_produto or quantidade <= 0:
            continue

        produto = produtos_lookup[produtos_lookup["codigo"] == codigo_produto]

        if produto.empty:
            continue

        linha_produto = produto.iloc[0]

        linhas_extras.append({
            "codigo_produto": codigo_produto,
            "produto": linha_produto["nome"],
            "quantidade": quantidade,
            "unidade": linha_produto["unidade"],
            "estoque_atual": linha_produto["estoque_atual"],
            "saldo_apos_saida": linha_produto["estoque_atual"] - quantidade,
            "status": "INSUFICIENTE" if (linha_produto["estoque_atual"] - quantidade) < 0 else "OK"
        })

    if linhas_extras:
        df_saida = pd.concat(
            [df_saida, pd.DataFrame(linhas_extras)],
            ignore_index=True
        )

    if df_saida.empty:
        return df_saida

    df_saida = (
        df_saida
        .groupby(["codigo_produto", "produto", "unidade"], as_index=False)
        .agg({
            "quantidade": "sum",
            "estoque_atual": "max"
        })
    )

    df_saida["saldo_apos_saida"] = (
        df_saida["estoque_atual"] - df_saida["quantidade"]
    )

    df_saida["status"] = df_saida["saldo_apos_saida"].apply(
        lambda saldo: "INSUFICIENTE" if saldo < 0 else "OK"
    )

    return df_saida


def formatar_numero_exibicao(valor):
    try:
        if pd.isna(valor):
            return ""

        numero = float(valor)

        if numero.is_integer():
            return str(int(numero))

        return str(numero).rstrip("0").rstrip(".")
    except Exception:
        return valor


def formatar_colunas_numericas_exibicao(df, colunas):
    df = df.copy()

    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = df[coluna].apply(formatar_numero_exibicao)

    return df


def enviar_para_apps_script(payload):
    resposta = requests.post(APPS_SCRIPT_URL, json=payload, timeout=20)

    if resposta.status_code != 200:
        raise Exception(f"Erro na requisição: {resposta.text}")

    retorno = resposta.json()

    if retorno.get("status") == "erro":
        raise Exception(retorno.get("message", "Erro desconhecido no Apps Script."))

    return retorno


def registrar_movimentacao(codigo_produto, tipo, quantidade, pedido="", observacao=""):
    payload = {
        "acao": "REGISTRAR_MOVIMENTACAO",
        "codigo_produto": codigo_produto,
        "tipo": tipo,
        "pedido": pedido,
        "quantidade": quantidade,
        "observacao": observacao,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return enviar_para_apps_script(payload)


def registrar_saida_kit(pedido, tipo_saida, tipo_monzi, itens, observacao=""):
    itens_payload = []

    for item in itens:
        quantidade = float(item["quantidade"])

        if quantidade <= 0:
            continue

        if quantidade.is_integer():
            quantidade = int(quantidade)

        itens_payload.append({
            "codigo_produto": str(item["codigo_produto"]),
            "quantidade": quantidade,
            "observacao": str(item.get("observacao", "") or "").strip()
        })

    if not itens_payload:
        raise Exception("Nenhum item válido foi informado para baixa.")

    payload = {
        "acao": "REGISTRAR_SAIDA_KIT",
        "pedido": pedido,
        "tipo_saida": str(tipo_saida).strip().upper(),
        "tipo_monzi": tipo_monzi,
        "observacao": str(observacao or "").strip(),
        "itens": itens_payload,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return enviar_para_apps_script(payload)


def excluir_entrada_historico(id_movimentacao):
    payload = {
        "acao": "EXCLUIR_ENTRADA",
        "id_movimentacao": id_movimentacao,
        "cancelado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return enviar_para_apps_script(payload)


def excluir_avaria_historico(id_movimentacao):
    payload = {
        "acao": "EXCLUIR_AVARIA",
        "id_movimentacao": id_movimentacao,
        "cancelado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return enviar_para_apps_script(payload)


def cancelar_saida_historico(pedido):
    payload = {
        "acao": "CANCELAR_SAIDA",
        "pedido": pedido,
        "cancelado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return enviar_para_apps_script(payload)


def cadastrar_produto(nome, unidade, estoque_minimo):
    payload = {
        "acao": "CADASTRAR_PRODUTO",
        "nome": nome,
        "unidade": unidade,
        "estoque_minimo": estoque_minimo,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return enviar_para_apps_script(payload)


def editar_produto(codigo, nome, unidade, estoque_minimo, ativo):
    payload = {
        "acao": "EDITAR_PRODUTO",
        "codigo": codigo,
        "nome": nome,
        "unidade": unidade,
        "estoque_minimo": estoque_minimo,
        "ativo": ativo,
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return enviar_para_apps_script(payload)


def bloquear_cliques_interface():
    st.markdown(
        """
        <style>
            html, body, .stApp {
                cursor: wait !important;
            }

            button, input, textarea, select, [role="button"] {
                pointer-events: none !important;
                cursor: wait !important;
            }

            .bloqueio-cliques {
                position: fixed;
                inset: 0;
                width: 100vw;
                height: 100vh;
                z-index: 2147483647;
                background: rgba(0, 0, 0, 0.02);
                cursor: wait !important;
                pointer-events: auto !important;
            }
        </style>

        <div class="bloqueio-cliques"></div>
        """,
        unsafe_allow_html=True
    )


# ESTADOS DO SISTEMA
if "mensagem_sucesso" not in st.session_state:
    st.session_state["mensagem_sucesso"] = None

if "mensagem_erro" not in st.session_state:
    st.session_state["mensagem_erro"] = None

if "rolar_topo_apos_sucesso" not in st.session_state:
    st.session_state["rolar_topo_apos_sucesso"] = False

if "menu_principal" not in st.session_state:
    st.session_state["menu_principal"] = "Consulta de Estoque"

if "confirmar_entrada" not in st.session_state:
    st.session_state["confirmar_entrada"] = None

if "confirmar_avaria" not in st.session_state:
    st.session_state["confirmar_avaria"] = None

if "confirmar_cadastro" not in st.session_state:
    st.session_state["confirmar_cadastro"] = None

if "confirmar_edicao" not in st.session_state:
    st.session_state["confirmar_edicao"] = None

if "confirmar_exclusao_entrada" not in st.session_state:
    st.session_state["confirmar_exclusao_entrada"] = None

if "confirmar_exclusao_avaria" not in st.session_state:
    st.session_state["confirmar_exclusao_avaria"] = None

if "confirmar_cancelamento_saida" not in st.session_state:
    st.session_state["confirmar_cancelamento_saida"] = None

if "confirmar_saida" not in st.session_state:
    st.session_state["confirmar_saida"] = None

if "erro_confirmar_saida" not in st.session_state:
    st.session_state["erro_confirmar_saida"] = None

if "erro_saida_form" not in st.session_state:
    st.session_state["erro_saida_form"] = None

if "rascunho_saida" not in st.session_state:
    st.session_state["rascunho_saida"] = None

if "entrada_processando" not in st.session_state:
    st.session_state["entrada_processando"] = None

if "avaria_processando" not in st.session_state:
    st.session_state["avaria_processando"] = None

if "saida_processando" not in st.session_state:
    st.session_state["saida_processando"] = None

if "simulacao_saida" not in st.session_state:
    st.session_state["simulacao_saida"] = None

if "cadastro_processando" not in st.session_state:
    st.session_state["cadastro_processando"] = None

if "edicao_processando" not in st.session_state:
    st.session_state["edicao_processando"] = None

if "exclusao_entrada_processando" not in st.session_state:
    st.session_state["exclusao_entrada_processando"] = None

if "exclusao_avaria_processando" not in st.session_state:
    st.session_state["exclusao_avaria_processando"] = None

if "cancelamento_saida_processando" not in st.session_state:
    st.session_state["cancelamento_saida_processando"] = None

if "cancelamento_processando" not in st.session_state:
    st.session_state["cancelamento_processando"] = None

if "reset_entrada" not in st.session_state:
    st.session_state["reset_entrada"] = 0

if "reset_avaria" not in st.session_state:
    st.session_state["reset_avaria"] = 0

if "reset_saida" not in st.session_state:
    st.session_state["reset_saida"] = 0

if "reset_cadastro" not in st.session_state:
    st.session_state["reset_cadastro"] = 0

if "reset_edicao" not in st.session_state:
    st.session_state["reset_edicao"] = 0

if "reset_historico" not in st.session_state:
    st.session_state["reset_historico"] = 0

if "bloqueado" not in st.session_state:
    st.session_state["bloqueado"] = False

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

if "perfil" not in st.session_state:
    st.session_state["perfil"] = None


exigir_login()

if not usuario_tem_acesso(st.session_state["menu_principal"]):
    st.session_state["menu_principal"] = primeira_tela_permitida()


def iniciar_processamento_saida(saida):
    st.session_state["bloqueado"] = True
    st.session_state["saida_processando"] = saida


def limpar_simulacao_saida():
    st.session_state["simulacao_saida"] = None
    st.session_state["confirmar_saida"] = None
    st.session_state["erro_confirmar_saida"] = None
    st.session_state["erro_saida_form"] = None
    st.session_state["rascunho_saida"] = None
    st.session_state["reset_saida"] += 1
    st.session_state["bloqueado"] = False


# PROCESSAMENTO DE ENTRADA
if st.session_state["entrada_processando"] is not None:
    bloquear_cliques_interface()

    entrada = st.session_state["entrada_processando"]

    st.divider()
    st.subheader("Processando entrada")

    try:
        with st.spinner("Registrando entrada no estoque. Aguarde..."):
            itens_entrada = entrada.get("itens")

            if itens_entrada:
                for item_entrada in itens_entrada:
                    registrar_movimentacao(
                        codigo_produto=item_entrada["codigo_produto"],
                        tipo="ENTRADA",
                        quantidade=item_entrada["quantidade"],
                        observacao=item_entrada.get("observacao", "")
                    )
            else:
                registrar_movimentacao(
                    codigo_produto=entrada["codigo_produto"],
                    tipo="ENTRADA",
                    quantidade=entrada["quantidade"],
                    observacao=entrada["observacao"]
                )

        quantidade_itens = len(entrada.get("itens") or [])

        if quantidade_itens > 1:
            st.session_state["mensagem_sucesso"] = f"{quantidade_itens} entradas registradas no estoque."
        else:
            st.session_state["mensagem_sucesso"] = "Entrada registrada no estoque."

        st.session_state["reset_entrada"] += 1

    except Exception as e:
        st.session_state["mensagem_erro"] = f"Erro ao registrar entrada: {e}"

    finally:
        st.session_state["entrada_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Entrada de Produtos"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE AVARIA
if st.session_state["avaria_processando"] is not None:
    bloquear_cliques_interface()

    avaria = st.session_state["avaria_processando"]

    st.divider()
    st.subheader("Processando avaria")

    try:
        with st.spinner("Registrando saída por avaria no estoque. Aguarde..."):
            motivo = str(avaria.get("motivo", "")).strip()
            observacao_avaria = f"AVARIA - {motivo}" if motivo else "AVARIA"

            for item_avaria in avaria.get("itens", []):
                registrar_movimentacao(
                    codigo_produto=item_avaria["codigo_produto"],
                    tipo="SAIDA",
                    quantidade=item_avaria["quantidade"],
                    pedido="AVARIA",
                    observacao=observacao_avaria
                )

        quantidade_itens = len(avaria.get("itens") or [])

        if quantidade_itens > 1:
            st.session_state["mensagem_sucesso"] = f"{quantidade_itens} saídas por avaria registradas no estoque."
        else:
            st.session_state["mensagem_sucesso"] = "Saída por avaria registrada no estoque."

        st.session_state["reset_avaria"] += 1

    except Exception as e:
        st.session_state["mensagem_erro"] = f"Erro ao registrar avaria: {e}"

    finally:
        st.session_state["avaria_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Avaria"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE SAÍDA
if st.session_state["saida_processando"] is not None:
    bloquear_cliques_interface()

    saida = st.session_state["saida_processando"]

    st.divider()
    st.subheader("Processando saída")

    try:
        with st.spinner("Registrando saída no estoque. Aguarde..."):
            registrar_saida_kit(
                pedido=saida["pedido"],
                tipo_saida=saida["tipo_saida"],
                tipo_monzi=saida["tipo_monzi"],
                itens=saida["itens"],
                observacao=saida.get("observacao", "")
            )

        st.session_state["mensagem_sucesso"] = "Saída registrada com sucesso."
        st.session_state["rolar_topo_apos_sucesso"] = True
        st.session_state["simulacao_saida"] = None
        st.session_state["confirmar_saida"] = None
        st.session_state["erro_confirmar_saida"] = None
        st.session_state["erro_saida_form"] = None
        st.session_state["rascunho_saida"] = None
        st.session_state["reset_saida"] += 1

    except Exception as e:
        st.session_state["erro_saida_form"] = f"Erro ao registrar saída: {e}"
        st.session_state["rascunho_saida"] = saida
        st.session_state["confirmar_saida"] = None
        st.session_state["erro_confirmar_saida"] = None
        st.session_state["simulacao_saida"] = None

    finally:
        st.session_state["saida_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Saída de Produtos"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE CADASTRO
if st.session_state["cadastro_processando"] is not None:
    bloquear_cliques_interface()

    cadastro = st.session_state["cadastro_processando"]

    st.divider()
    st.subheader("Processando cadastro")

    try:
        with st.spinner("Cadastrando produto. Aguarde..."):
            retorno = cadastrar_produto(
                nome=cadastro["nome"],
                unidade=cadastro["unidade"],
                estoque_minimo=cadastro["estoque_minimo"]
            )

        codigo = retorno.get("codigo", "")
        st.session_state["mensagem_sucesso"] = f"Produto cadastrado com sucesso. Código: {codigo}"
        st.session_state["reset_cadastro"] += 1

    except Exception as e:
        st.session_state["mensagem_erro"] = f"Erro ao cadastrar produto: {e}"

    finally:
        st.session_state["cadastro_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Cadastro de Produtos"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE EDIÇÃO
if st.session_state["edicao_processando"] is not None:
    bloquear_cliques_interface()

    edicao = st.session_state["edicao_processando"]

    st.divider()
    st.subheader("Processando edição")

    try:
        with st.spinner("Atualizando produto. Aguarde..."):
            editar_produto(
                codigo=edicao["codigo"],
                nome=edicao["nome"],
                unidade=edicao["unidade"],
                estoque_minimo=edicao["estoque_minimo"],
                ativo=edicao["ativo"]
            )

        st.session_state["mensagem_sucesso"] = "Produto atualizado com sucesso."
        st.session_state["reset_edicao"] += 1

    except Exception as e:
        st.session_state["mensagem_erro"] = f"Erro ao atualizar produto: {e}"

    finally:
        st.session_state["edicao_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Edição de Produtos"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE EXCLUSÃO DE ENTRADA PELO HISTÓRICO
if st.session_state["exclusao_entrada_processando"] is not None:
    bloquear_cliques_interface()

    exclusao_entrada = st.session_state["exclusao_entrada_processando"]

    st.divider()
    st.subheader("Processando exclusão de entrada")

    try:
        with st.spinner("Excluindo entrada e recalculando estoque. Aguarde..."):
            excluir_entrada_historico(
                id_movimentacao=exclusao_entrada["id_movimentacao"]
            )

        st.session_state["mensagem_sucesso"] = "Entrada excluída com sucesso. O estoque foi ajustado."
        st.session_state["reset_historico"] += 1

    except Exception as e:
        st.session_state["mensagem_erro"] = f"Erro ao excluir entrada: {e}"

    finally:
        st.session_state["exclusao_entrada_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Histórico"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE EXCLUSÃO DE AVARIA PELO HISTÓRICO
if st.session_state["exclusao_avaria_processando"] is not None:
    bloquear_cliques_interface()

    exclusao_avaria = st.session_state["exclusao_avaria_processando"]

    st.divider()
    st.subheader("Processando exclusão de avaria")

    try:
        with st.spinner("Excluindo avaria e devolvendo item ao estoque. Aguarde..."):
            excluir_avaria_historico(
                id_movimentacao=exclusao_avaria["id_movimentacao"]
            )

        st.session_state["mensagem_sucesso"] = "Avaria excluída com sucesso. O item foi devolvido ao estoque."
        st.session_state["reset_historico"] += 1

    except Exception as e:
        st.session_state["mensagem_erro"] = f"Erro ao excluir avaria: {e}"

    finally:
        st.session_state["exclusao_avaria_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Histórico"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE CANCELAMENTO DE SAÍDA PELO HISTÓRICO
if st.session_state["cancelamento_saida_processando"] is not None:
    bloquear_cliques_interface()

    cancelamento_saida = st.session_state["cancelamento_saida_processando"]

    st.divider()
    st.subheader("Processando cancelamento de saída")

    try:
        with st.spinner("Cancelando saída e devolvendo itens ao estoque. Aguarde..."):
            cancelar_saida_historico(
                pedido=cancelamento_saida["pedido"]
            )

        st.session_state["mensagem_sucesso"] = "Saída cancelada com sucesso. Os itens foram devolvidos ao estoque."
        st.session_state["reset_historico"] += 1

    except Exception as e:
        st.session_state["mensagem_erro"] = f"Erro ao cancelar saída: {e}"

    finally:
        st.session_state["cancelamento_saida_processando"] = None
        st.session_state["bloqueado"] = False
        st.session_state["menu_principal"] = "Histórico"
        st.rerun()

    st.stop()


# PROCESSAMENTO DE CANCELAMENTO
if st.session_state["cancelamento_processando"] is not None:
    bloquear_cliques_interface()

    cancelamento = st.session_state["cancelamento_processando"]

    st.divider()
    st.subheader("Cancelando operação")

    try:
        with st.spinner("Cancelando e retornando à tela anterior. Aguarde..."):
            st.session_state[cancelamento["chave_confirmacao"]] = None
            st.session_state["menu_principal"] = cancelamento["destino"]

    finally:
        st.session_state["cancelamento_processando"] = None
        st.session_state["bloqueado"] = False
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE ENTRADA
if st.session_state["confirmar_entrada"] is not None:
    entrada = st.session_state["confirmar_entrada"]

    st.divider()
    st.subheader("Confirmação de entrada")

    st.info("Revise as informações abaixo antes de confirmar o registro da entrada no estoque.")

    itens_entrada = entrada.get("itens")

    if itens_entrada:
        df_confirmacao_entrada = pd.DataFrame(itens_entrada)
        df_confirmacao_entrada = df_confirmacao_entrada.rename(columns={
            "codigo_produto": "Código do Produto",
            "produto_nome": "Produto",
            "quantidade": "Quantidade",
            "observacao": "Observação"
        })

        df_confirmacao_entrada = formatar_colunas_numericas_exibicao(
            df_confirmacao_entrada,
            ["Quantidade"]
        )

        st.dataframe(
            df_confirmacao_entrada[
                ["Código do Produto", "Produto", "Quantidade", "Observação"]
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write(f"**Produto:** {entrada['produto_nome']}")
        st.write(f"**Quantidade:** {entrada['quantidade']}")

        if entrada["observacao"]:
            st.write(f"**Observação:** {entrada['observacao']}")
        else:
            st.write("**Observação:** Não informada")

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"]
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["entrada_processando"] = entrada
        st.session_state["confirmar_entrada"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_processando"] = {
            "chave_confirmacao": "confirmar_entrada",
            "destino": "Entrada de Produtos"
        }
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE AVARIA
if st.session_state["confirmar_avaria"] is not None:
    avaria = st.session_state["confirmar_avaria"]

    st.divider()
    st.subheader("Confirmação de avaria")

    st.info("Revise as informações abaixo antes de confirmar a saída por avaria no estoque.")

    st.write(f"**Motivo da avaria:** {avaria['motivo']}")

    itens_avaria = avaria.get("itens", [])
    df_confirmacao_avaria = pd.DataFrame(itens_avaria)

    possui_insuficiente = False
    if not df_confirmacao_avaria.empty and "status" in df_confirmacao_avaria.columns:
        possui_insuficiente = (
            df_confirmacao_avaria["status"].astype(str).str.upper() == "INSUFICIENTE"
        ).any()

    if df_confirmacao_avaria.empty:
        st.warning("Nenhum item encontrado para esta avaria.")
    else:
        df_confirmacao_avaria = df_confirmacao_avaria.rename(columns={
            "codigo_produto": "Código do Produto",
            "produto_nome": "Produto",
            "quantidade": "Quantidade",
            "estoque_atual": "Estoque Atual",
            "saldo_apos_saida": "Saldo Após Saída",
            "observacao": "Observação",
            "status": "Status"
        })

        df_confirmacao_avaria = formatar_colunas_numericas_exibicao(
            df_confirmacao_avaria,
            ["Quantidade", "Estoque Atual", "Saldo Após Saída"]
        )

        def colorir_status_avaria(valor):
            valor = str(valor).upper()

            if valor == "INSUFICIENTE":
                return "background-color: #7f1d1d; color: white; font-weight: 700;"

            if valor == "OK":
                return "background-color: #14532d; color: white; font-weight: 700;"

            return ""

        tabela_avaria = df_confirmacao_avaria[
            ["Código do Produto", "Produto", "Quantidade", "Estoque Atual", "Saldo Após Saída", "Status"]
        ].style.map(
            colorir_status_avaria,
            subset=["Status"]
        )

        st.dataframe(
            tabela_avaria,
            use_container_width=True,
            hide_index=True
        )

    if possui_insuficiente:
        exibir_alerta_temporario(
            "Não é possível confirmar esta avaria. Existem itens com estoque insuficiente.",
            tipo="error"
        )

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"] or possui_insuficiente or df_confirmacao_avaria.empty
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["avaria_processando"] = avaria
        st.session_state["confirmar_avaria"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_processando"] = {
            "chave_confirmacao": "confirmar_avaria",
            "destino": "Avaria"
        }
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE CADASTRO
if st.session_state["confirmar_cadastro"] is not None:
    cadastro = st.session_state["confirmar_cadastro"]

    st.divider()
    st.subheader("Confirmação de cadastro")

    st.info("Revise as informações abaixo antes de confirmar o cadastro do produto.")

    st.write(f"**Nome do produto:** {cadastro['nome']}")
    st.write(f"**Unidade:** {cadastro['unidade']}")
    st.write(f"**Estoque mínimo:** {cadastro['estoque_minimo']}")

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"]
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cadastro_processando"] = cadastro
        st.session_state["confirmar_cadastro"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_processando"] = {
            "chave_confirmacao": "confirmar_cadastro",
            "destino": "Cadastro de Produtos"
        }
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE EDIÇÃO
if st.session_state["confirmar_edicao"] is not None:
    edicao = st.session_state["confirmar_edicao"]

    st.divider()
    st.subheader("Confirmação de edição")

    st.info("Revise as informações abaixo antes de confirmar a atualização do produto.")

    st.write(f"**Código:** {edicao['codigo']}")
    st.write(f"**Nome do produto:** {edicao['nome']}")
    st.write(f"**Unidade:** {edicao['unidade']}")
    st.write(f"**Estoque mínimo:** {edicao['estoque_minimo']}")
    st.write(f"**Ativo:** {edicao['ativo']}")

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"]
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["edicao_processando"] = edicao
        st.session_state["confirmar_edicao"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_processando"] = {
            "chave_confirmacao": "confirmar_edicao",
            "destino": "Edição de Produtos"
        }
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE EXCLUSÃO DE ENTRADA
if st.session_state["confirmar_exclusao_entrada"] is not None:
    exclusao = st.session_state["confirmar_exclusao_entrada"]

    st.divider()
    st.subheader("Confirmação de exclusão de entrada")

    st.warning(
        "Revise as informações abaixo antes de confirmar a exclusão da entrada. "
        "A linha não será apagada; ela será marcada como ENTRADA_CANCELADA e o estoque será ajustado."
    )

    st.write(f"**ID da movimentação:** {exclusao['id_movimentacao']}")
    st.write(f"**Produto:** {exclusao['produto']}")
    st.write(f"**Quantidade que será removida do estoque:** {exclusao['quantidade']}")

    if exclusao.get("data"):
        st.write(f"**Data:** {exclusao['data']}")

    if exclusao.get("observacao"):
        st.write(f"**Observação:** {exclusao['observacao']}")
    else:
        st.write("**Observação:** Não informada")

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"]
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["exclusao_entrada_processando"] = {
            "id_movimentacao": exclusao["id_movimentacao"]
        }
        st.session_state["confirmar_exclusao_entrada"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_processando"] = {
            "chave_confirmacao": "confirmar_exclusao_entrada",
            "destino": "Histórico"
        }
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE EXCLUSÃO DE AVARIA
if st.session_state["confirmar_exclusao_avaria"] is not None:
    exclusao = st.session_state["confirmar_exclusao_avaria"]

    st.divider()
    st.subheader("Confirmação de exclusão de avaria")

    st.warning(
        "Revise as informações abaixo antes de confirmar a exclusão da avaria. "
        "A linha não será apagada; ela será marcada como AVARIA_CANCELADA e o item será devolvido ao estoque."
    )

    st.write(f"**ID da movimentação:** {exclusao['id_movimentacao']}")
    st.write(f"**Produto:** {exclusao['produto']}")
    st.write(f"**Quantidade que será devolvida ao estoque:** {exclusao['quantidade']}")

    if exclusao.get("data"):
        st.write(f"**Data:** {exclusao['data']}")

    if exclusao.get("observacao"):
        st.write(f"**Observação:** {exclusao['observacao']}")
    else:
        st.write("**Observação:** Não informada")

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"]
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["exclusao_avaria_processando"] = {
            "id_movimentacao": exclusao["id_movimentacao"]
        }
        st.session_state["confirmar_exclusao_avaria"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_processando"] = {
            "chave_confirmacao": "confirmar_exclusao_avaria",
            "destino": "Histórico"
        }
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE SAÍDA
if st.session_state["confirmar_saida"] is not None:
    saida = st.session_state["confirmar_saida"]

    st.divider()
    st.subheader("Confirmação de saída")

    st.info("Revise as informações abaixo antes de confirmar a baixa no estoque.")

    st.write(f"**Pedido:** {saida['pedido']}")
    st.write(f"**Saída:** {saida['tipo_saida']}")
    if str(saida.get("tipo_saida", "")).strip().upper() != "OUTROS":
        st.write(f"**Tipo de Monzi:** {saida['tipo_monzi']}")
    else:
        st.write("**Tipo de Monzi:** Não se aplica")


    df_saida_confirmacao = pd.DataFrame(saida["itens"])

    possui_insuficiente = False
    if not df_saida_confirmacao.empty and "status" in df_saida_confirmacao.columns:
        possui_insuficiente = (
            df_saida_confirmacao["status"].astype(str).str.upper() == "INSUFICIENTE"
        ).any()

    st.markdown("### Itens que serão baixados")

    if df_saida_confirmacao.empty:
        st.warning("Nenhum item encontrado para esta saída.")
    else:
        df_confirmacao_exibir = df_saida_confirmacao.rename(columns={
            "codigo_produto": "Código do Produto",
            "produto": "Produto",
            "unidade": "Unidade",
            "quantidade": "Quantidade Necessária",
            "estoque_atual": "Estoque Atual",
            "saldo_apos_saida": "Saldo Após Saída",
            "observacao": "Observação",
            "status": "Status"
        })

        colunas_confirmacao = [
            "Código do Produto",
            "Produto",
            "Quantidade Necessária",
            "Unidade",
            "Estoque Atual",
            "Saldo Após Saída",
            "Observação",
            "Status"
        ]

        colunas_confirmacao = [
            coluna for coluna in colunas_confirmacao
            if coluna in df_confirmacao_exibir.columns
        ]

        df_confirmacao_exibir = formatar_colunas_numericas_exibicao(
            df_confirmacao_exibir,
            ["Quantidade Necessária", "Estoque Atual", "Saldo Após Saída"]
        )

        def colorir_status_confirmacao(valor):
            valor = str(valor).upper()

            if valor == "INSUFICIENTE":
                return "background-color: #7f1d1d; color: white; font-weight: 700;"

            if valor == "OK":
                return "background-color: #14532d; color: white; font-weight: 700;"

            return ""

        if "Status" in df_confirmacao_exibir.columns:
            tabela_confirmacao = df_confirmacao_exibir[colunas_confirmacao].style.map(
                colorir_status_confirmacao,
                subset=["Status"]
            )
        else:
            tabela_confirmacao = df_confirmacao_exibir[colunas_confirmacao]

        st.dataframe(
            tabela_confirmacao,
            use_container_width=True,
            hide_index=True
        )

    if str(saida.get("tipo_saida", "")).strip().upper() != "OUTROS" and saida.get("produtos_extras"):
        st.markdown("### Produtos extras")
        df_extras_confirmacao = pd.DataFrame(saida["produtos_extras"])
        if not df_extras_confirmacao.empty:
            df_extras_confirmacao = df_extras_confirmacao.rename(columns={
                "codigo_produto": "Código do Produto",
                "produto": "Produto",
                "quantidade": "Quantidade"
            })
            df_extras_confirmacao = formatar_colunas_numericas_exibicao(
                df_extras_confirmacao,
                ["Quantidade"]
            )

            st.dataframe(
                df_extras_confirmacao[["Código do Produto", "Produto", "Quantidade"]],
                use_container_width=True,
                hide_index=True
            )

    if possui_insuficiente:
        exibir_alerta_temporario(
            "Não é possível confirmar esta saída. "
            "Existem itens com estoque insuficiente.",
            tipo="error"
        )

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"] or possui_insuficiente or df_saida_confirmacao.empty
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["saida_processando"] = saida
        st.session_state["erro_confirmar_saida"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["rascunho_saida"] = saida
        st.session_state["confirmar_saida"] = None
        st.session_state["erro_confirmar_saida"] = None
        st.session_state["erro_saida_form"] = None
        st.session_state["menu_principal"] = "Saída de Produtos"
        st.rerun()

    st.stop()


# CONFIRMAÇÃO DE CANCELAMENTO DE SAÍDA
if st.session_state["confirmar_cancelamento_saida"] is not None:
    cancelamento_saida = st.session_state["confirmar_cancelamento_saida"]

    st.divider()
    st.subheader("Confirmação de cancelamento de saída")

    st.warning(
        "Revise as informações abaixo antes de confirmar o cancelamento da saída. "
        "As linhas não serão apagadas; elas serão marcadas como canceladas e os itens serão devolvidos ao estoque."
    )

    st.write(f"**Pedido:** {cancelamento_saida['pedido']}")
    st.write(f"**Tipo:** {cancelamento_saida['tipo']}")
    st.write(f"**Quantidade de itens:** {cancelamento_saida['total_itens']}")

    df_itens_cancelamento = pd.DataFrame(cancelamento_saida["itens"])

    if not df_itens_cancelamento.empty:
        st.markdown("### Itens que serão devolvidos ao estoque")
        st.dataframe(
            df_itens_cancelamento,
            use_container_width=True,
            hide_index=True
        )

    col_vazio_esq, col_confirmar, col_cancelar, col_vazio_dir = st.columns([3, 1, 1, 3])

    with col_confirmar:
        confirmar = st.button(
            "Confirmar",
            type="primary",
            disabled=st.session_state["bloqueado"]
        )

    with col_cancelar:
        cancelar = st.button(
            "Cancelar",
            disabled=st.session_state["bloqueado"]
        )

    if confirmar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_saida_processando"] = {
            "pedido": cancelamento_saida["pedido"]
        }
        st.session_state["confirmar_cancelamento_saida"] = None
        st.rerun()

    if cancelar and not st.session_state["bloqueado"]:
        st.session_state["bloqueado"] = True
        st.session_state["cancelamento_processando"] = {
            "chave_confirmacao": "confirmar_cancelamento_saida",
            "destino": "Histórico"
        }
        st.rerun()

    st.stop()


# MENSAGENS
if st.session_state["mensagem_sucesso"]:
    exibir_alerta_temporario(
        st.session_state["mensagem_sucesso"],
        tipo="success"
    )
    st.session_state["mensagem_sucesso"] = None

if st.session_state["mensagem_erro"]:
    exibir_alerta_temporario(
        st.session_state["mensagem_erro"],
        tipo="error"
    )
    st.session_state["mensagem_erro"] = None


try:
    produtos, movimentacoes, kits, composicao_kits = carregar_dados()
    produtos = tratar_produtos(produtos)
    produtos = recalcular_status_produtos(produtos)

    kits["codigo_kit"] = kits["codigo_kit"].astype(str)
    kits["nome_kit"] = kits["nome_kit"].astype(str)
    kits["ativo"] = kits["ativo"].astype(str)

    composicao_kits["id"] = composicao_kits["id"].astype(str)
    composicao_kits["codigo_kit"] = composicao_kits["codigo_kit"].astype(str)
    composicao_kits["tipo_item"] = composicao_kits["tipo_item"].astype(str)
    composicao_kits["codigo_item"] = composicao_kits["codigo_item"].astype(str)
    composicao_kits["ativo"] = composicao_kits["ativo"].astype(str)
    composicao_kits["quantidade"] = pd.to_numeric(
        composicao_kits["quantidade"],
        errors="coerce"
    ).fillna(0)

    def trocar_tela(nome_tela):
        st.session_state["menu_principal"] = nome_tela


    def botao_menu(nome_tela):
        tela_atual = st.session_state["menu_principal"]

        if tela_atual == nome_tela:
            st.markdown(
                f"""
                <div style="
                    background-color: #ff4b4b;
                    color: white;
                    width: 100%;
                    min-height: 2.5rem;
                    padding: 0.55rem 0.9rem;
                    border-radius: 0.5rem;
                    font-weight: 700;
                    margin-bottom: 0.45rem;
                    border: 1px solid #ff6b6b;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    box-sizing: border-box;
                ">
                    {nome_tela}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.button(
                nome_tela,
                use_container_width=True,
                on_click=trocar_tela,
                args=(nome_tela,)
            )


    with st.sidebar:
        st.title("Sistema de Estoque")

        st.caption(f"Usuário: {st.session_state.get('usuario', '')}")

        st.divider()

        st.markdown("### Estoque")
        if usuario_tem_acesso("Consulta de Estoque"):
            botao_menu("Consulta de Estoque")
        if usuario_tem_acesso("Entrada de Produtos"):
            botao_menu("Entrada de Produtos")
        if usuario_tem_acesso("Avaria"):
            botao_menu("Avaria")
        if usuario_tem_acesso("Saída de Produtos"):
            botao_menu("Saída de Produtos")

        if (
            usuario_tem_acesso("Cadastro de Produtos")
            or usuario_tem_acesso("Edição de Produtos")
            or usuario_tem_acesso("Consulta de Kits")
        ):
            st.markdown("### Produtos")

        if usuario_tem_acesso("Cadastro de Produtos"):
            botao_menu("Cadastro de Produtos")
        if usuario_tem_acesso("Edição de Produtos"):
            botao_menu("Edição de Produtos")
        if usuario_tem_acesso("Consulta de Kits"):
            botao_menu("Consulta de Kits")

        st.markdown("### Relatórios")
        if usuario_tem_acesso("Histórico"):
            botao_menu("Histórico")

        st.divider()

        if st.button("Sair", use_container_width=True):
            sair_do_sistema()

    aba_atual = st.session_state["menu_principal"]

    if not usuario_tem_acesso(aba_atual):
        exibir_alerta_temporario("Você não tem permissão para acessar esta tela.", tipo="error")
        st.stop()

    if aba_atual == "Consulta de Estoque":
        st.subheader("Consulta de Estoque")

        consulta_base = produtos.copy()

        if "filtros_consulta_aplicados" not in st.session_state:
            st.session_state["filtros_consulta_aplicados"] = {
                "busca_nome": "",
                "ativo": "Todos",
                "status": "Todos",
                "unidade": "Todas"
            }

        with st.form("form_filtros_consulta"):
            col_filtro1, col_filtro2, col_filtro3, col_filtro4, col_botao = st.columns([3, 1, 1, 1, 1])

            with col_filtro1:
                busca_nome = st.text_input(
                    "Buscar produto",
                    placeholder="Digite o nome do produto",
                    key="consulta_busca_nome_input"
                )

            with col_filtro2:
                filtro_ativo = st.selectbox(
                    "Ativo",
                    ["Todos", "SIM", "NÃO"],
                    key="consulta_ativo_input"
                )

            with col_filtro3:
                status_disponiveis = ["Todos"] + sorted(
                    consulta_base["status"].dropna().astype(str).unique().tolist()
                )

                filtro_status = st.selectbox(
                    "Status",
                    status_disponiveis,
                    key="consulta_status_input"
                )

            with col_filtro4:
                unidades_disponiveis = ["Todas"] + sorted(
                    consulta_base["unidade"].dropna().astype(str).unique().tolist()
                )

                filtro_unidade = st.selectbox(
                    "Unidade",
                    unidades_disponiveis,
                    key="consulta_unidade_input"
                )

            with col_botao:
                st.write("")
                st.write("")
                botao_pesquisar = st.form_submit_button("Pesquisar")

        if botao_pesquisar:
            st.session_state["filtros_consulta_aplicados"] = {
                "busca_nome": busca_nome.strip(),
                "ativo": filtro_ativo,
                "status": filtro_status,
                "unidade": filtro_unidade
            }

        filtros = st.session_state["filtros_consulta_aplicados"]

        consulta = consulta_base.copy()

        if filtros["busca_nome"]:
            consulta = consulta[
                consulta["nome"]
                .astype(str)
                .str.contains(filtros["busca_nome"], case=False, na=False)
            ]

        if filtros["ativo"] != "Todos":
            consulta = consulta[consulta["ativo"].astype(str) == filtros["ativo"]]

        if filtros["status"] != "Todos":
            consulta = consulta[consulta["status"].astype(str) == filtros["status"]]

        if filtros["unidade"] != "Todas":
            consulta = consulta[consulta["unidade"].astype(str) == filtros["unidade"]]

        colunas_exibir = [
            "codigo",
            "nome",
            "unidade",
            "estoque_atual",
            "estoque_minimo",
            "status",
            "ativo",
            "atualizado_em"
        ]

        st.caption(f"Produtos encontrados: {len(consulta)}")

        consulta_exibir = consulta[colunas_exibir].copy()

        consulta_exibir["status"] = (
            consulta_exibir["status"]
            .astype(str)
            .str.upper()
        )

        def colorir_status(valor):
            valor = str(valor).upper()

            if valor == "SEM ESTOQUE":
                return "background-color: #7f1d1d; color: white; font-weight: 700;"

            if valor == "ACABANDO":
                return "background-color: #854d0e; color: white; font-weight: 700;"

            if valor == "OK":
                return "background-color: #14532d; color: white; font-weight: 700;"

            return ""

        tabela_estilizada = consulta_exibir.style.map(
            colorir_status,
            subset=["status"]
        )

        st.dataframe(
            tabela_estilizada,
            use_container_width=True,
            hide_index=True
        )

    elif aba_atual == "Entrada de Produtos":
        st.subheader("Entrada de Produtos")

        produtos_ativos = produtos[produtos["ativo"] == "SIM"].copy()

        if produtos_ativos.empty:
            st.warning("Nenhum produto ativo encontrado.")
        else:
            produtos_ativos["produto_opcao"] = (
                produtos_ativos["codigo"].astype(str) + " - " + produtos_ativos["nome"]
            )

            opcoes_produtos_entrada = [""] + produtos_ativos["produto_opcao"].tolist()

            with st.form(f"form_entrada_produtos_{st.session_state['reset_entrada']}"):
                st.caption(
                    "Adicione uma linha para cada produto que entrará no estoque. "
                    "Use o botão de + da tabela para criar novas linhas."
                )

                df_entrada_editor = st.data_editor(
                    pd.DataFrame([{"Produto": "", "Quantidade": 0, "Observação": ""}]),
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        "Produto": st.column_config.SelectboxColumn(
                            "Produto",
                            options=opcoes_produtos_entrada,
                            required=False
                        ),
                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            min_value=0,
                            step=1,
                            default=0,
                            required=False
                        ),
                        "Observação": st.column_config.TextColumn(
                            "Observação",
                            required=False
                        )
                    },
                    key=f"entrada_produtos_editor_{st.session_state['reset_entrada']}"
                )

                col_vazio_esq, col_direita, col_vazio_dir = st.columns([4, 1, 4])

                with col_direita:
                    botao_entrada = st.form_submit_button("Registrar entrada")

            if botao_entrada:
                itens_entrada = []

                if df_entrada_editor is not None and not df_entrada_editor.empty:
                    for _, linha_entrada in df_entrada_editor.iterrows():
                        produto_entrada = str(linha_entrada.get("Produto", "") or "").strip()
                        quantidade_entrada = linha_entrada.get("Quantidade", 0)
                        observacao_entrada = str(linha_entrada.get("Observação", "") or "").strip()

                        try:
                            quantidade_entrada = float(quantidade_entrada or 0)
                        except Exception:
                            quantidade_entrada = 0

                        if not produto_entrada and quantidade_entrada <= 0:
                            continue

                        if not produto_entrada:
                            exibir_alerta_temporario("Selecione o produto em todas as linhas preenchidas.", tipo="error")
                            st.stop()

                        if quantidade_entrada <= 0:
                            exibir_alerta_temporario("Informe uma quantidade maior que zero em todas as linhas preenchidas.", tipo="error")
                            st.stop()

                        codigo_produto = produto_entrada.split(" - ")[0]
                        produto_nome = produto_entrada.split(" - ", 1)[1] if " - " in produto_entrada else produto_entrada

                        itens_entrada.append({
                            "codigo_produto": codigo_produto,
                            "produto_nome": produto_nome,
                            "quantidade": int(quantidade_entrada) if quantidade_entrada.is_integer() else quantidade_entrada,
                            "observacao": observacao_entrada
                        })

                if not itens_entrada:
                    exibir_alerta_temporario("Informe pelo menos um produto para entrada.", tipo="error")
                    st.stop()

                st.session_state["confirmar_entrada"] = {
                    "itens": itens_entrada
                }

                st.rerun()

    elif aba_atual == "Avaria":
        st.subheader("Avaria")

        produtos_ativos = produtos[produtos["ativo"] == "SIM"].copy()

        if produtos_ativos.empty:
            st.warning("Nenhum produto ativo encontrado.")
        else:
            produtos_ativos["produto_opcao"] = (
                produtos_ativos["codigo"].astype(str) + " - " + produtos_ativos["nome"].astype(str)
            )

            opcoes_produtos_avaria = [""] + produtos_ativos["produto_opcao"].tolist()
            produtos_lookup_avaria = produtos_ativos.copy()
            produtos_lookup_avaria["codigo"] = produtos_lookup_avaria["codigo"].astype(str)

            with st.form(f"form_avaria_produtos_{st.session_state['reset_avaria']}"):
                st.caption(
                    "Registre saídas por avaria item por item. O motivo é obrigatório e será gravado na observação das movimentações."
                )

                motivo_avaria = st.text_area(
                    "Motivo da avaria",
                    placeholder="Ex: produto danificado, embalagem rasgada, item quebrado...",
                    key=f"motivo_avaria_{st.session_state['reset_avaria']}"
                )

                df_avaria_editor = st.data_editor(
                    pd.DataFrame([{"Produto": "", "Quantidade": 0}]),
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        "Produto": st.column_config.SelectboxColumn(
                            "Produto",
                            options=opcoes_produtos_avaria,
                            required=False
                        ),
                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            min_value=0,
                            step=1,
                            default=0,
                            required=False
                        )
                    },
                    key=f"avaria_produtos_editor_{st.session_state['reset_avaria']}"
                )

                col_vazio_esq, col_centro, col_vazio_dir = st.columns([4, 1, 4])

                with col_centro:
                    botao_avaria = st.form_submit_button("Registrar avaria")

            if botao_avaria:
                motivo_avaria = str(motivo_avaria or "").strip()

                if not motivo_avaria:
                    exibir_alerta_temporario("Informe o motivo da avaria.", tipo="error")
                    st.stop()

                itens_avaria = []

                if df_avaria_editor is not None and not df_avaria_editor.empty:
                    for _, linha_avaria in df_avaria_editor.iterrows():
                        produto_avaria = str(linha_avaria.get("Produto", "") or "").strip()
                        quantidade_avaria = linha_avaria.get("Quantidade", 0)

                        try:
                            quantidade_avaria = float(quantidade_avaria or 0)
                        except Exception:
                            quantidade_avaria = 0

                        if not produto_avaria and quantidade_avaria <= 0:
                            continue

                        if not produto_avaria:
                            exibir_alerta_temporario("Selecione o produto em todas as linhas preenchidas.", tipo="error")
                            st.stop()

                        if quantidade_avaria <= 0:
                            exibir_alerta_temporario("Informe uma quantidade maior que zero em todas as linhas preenchidas.", tipo="error")
                            st.stop()

                        codigo_produto = produto_avaria.split(" - ")[0]
                        produto_nome = produto_avaria.split(" - ", 1)[1] if " - " in produto_avaria else produto_avaria

                        produto_linha = produtos_lookup_avaria[
                            produtos_lookup_avaria["codigo"] == str(codigo_produto)
                        ]

                        estoque_atual = 0
                        if not produto_linha.empty:
                            estoque_atual = float(produto_linha.iloc[0].get("estoque_atual", 0) or 0)

                        saldo_apos_saida = estoque_atual - quantidade_avaria

                        itens_avaria.append({
                            "codigo_produto": codigo_produto,
                            "produto_nome": produto_nome,
                            "quantidade": int(quantidade_avaria) if quantidade_avaria.is_integer() else quantidade_avaria,
                            "estoque_atual": estoque_atual,
                            "saldo_apos_saida": saldo_apos_saida,
                            "status": "INSUFICIENTE" if saldo_apos_saida < 0 else "OK"
                        })

                if not itens_avaria:
                    exibir_alerta_temporario("Informe pelo menos um produto para avaria.", tipo="error")
                    st.stop()

                st.session_state["confirmar_avaria"] = {
                    "motivo": motivo_avaria,
                    "itens": itens_avaria
                }

                st.rerun()


    elif aba_atual == "Saída de Produtos":
        st.subheader("Saída de Produtos")

        produtos_ativos_saida = produtos[produtos["ativo"] == "SIM"].copy()
        produtos_ativos_saida["produto_opcao"] = (
            produtos_ativos_saida["codigo"].astype(str) + " - " + produtos_ativos_saida["nome"].astype(str)
        )
        opcoes_produtos_saida = [""] + produtos_ativos_saida["produto_opcao"].tolist()

        rascunho_saida = st.session_state.get("rascunho_saida") or {}

        if "tipo_saida_selecionado" not in st.session_state:
            st.session_state["tipo_saida_selecionado"] = rascunho_saida.get("tipo_saida", "TORRE")

        if "tipo_monzi_selecionado" not in st.session_state:
            st.session_state["tipo_monzi_selecionado"] = rascunho_saida.get("tipo_monzi", "Prata")

        col_tipo_1, col_tipo_2, col_tipo_3 = st.columns([2, 1, 1])

        with col_tipo_2:
            tipo_saida = st.selectbox(
                "Tipo de saída",
                ["TORRE", "ILHA", "OUTROS"],
                key="tipo_saida_selecionado",
                on_change=limpar_simulacao_saida
            )

        with col_tipo_3:
            if tipo_saida == "OUTROS":
                st.text_input(
                    "Tipo de Monzi",
                    value="Não se aplica",
                    disabled=True
                )
                tipo_monzi = "Não se aplica"
            else:
                tipo_monzi = st.selectbox(
                    "Tipo de Monzi",
                    ["Prata", "Amarelo", "Ambos"],
                    key="tipo_monzi_selecionado",
                    on_change=limpar_simulacao_saida
                )

        with st.form(f"form_saida_produtos_{tipo_saida}_{tipo_monzi}_{st.session_state['reset_saida']}"):
            pedido_saida = st.text_input(
                "Número do pedido",
                placeholder="Ex: PED123",
                value=rascunho_saida.get("pedido", ""),
                key=f"pedido_saida_{st.session_state['reset_saida']}"
            )

            observacao_saida = ""

            ajustes_checklist = {}
            df_itens_outros_editor = None
            df_extras_editor = None

            if tipo_saida == "OUTROS":
                st.markdown("### Itens da saída")
                st.caption(
                    "Adicione os produtos que serão baixados manualmente. "
                    "Use o botão de + da tabela para criar novas linhas."
                )

                itens_outros_rascunho = []

                for item_rascunho in rascunho_saida.get("produtos_extras", []):
                    codigo_rascunho = str(item_rascunho.get("codigo_produto", "")).strip()
                    nome_rascunho = str(item_rascunho.get("produto", "")).strip()
                    quantidade_rascunho = item_rascunho.get("quantidade", 0)
                    observacao_rascunho = str(item_rascunho.get("observacao", "") or "")

                    produto_opcao_rascunho = ""
                    if codigo_rascunho and nome_rascunho:
                        produto_opcao_rascunho = f"{codigo_rascunho} - {nome_rascunho}"

                    itens_outros_rascunho.append({
                        "Produto": produto_opcao_rascunho,
                        "Quantidade": quantidade_rascunho,
                        "Observação": observacao_rascunho
                    })

                if not itens_outros_rascunho:
                    itens_outros_rascunho = [{"Produto": "", "Quantidade": 0, "Observação": ""}]

                df_itens_outros_editor = st.data_editor(
                    pd.DataFrame(itens_outros_rascunho),
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        "Produto": st.column_config.SelectboxColumn(
                            "Produto",
                            options=opcoes_produtos_saida,
                            required=False
                        ),
                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            min_value=0,
                            step=1,
                            default=0,
                            required=False
                        ),
                        "Observação": st.column_config.TextColumn(
                            "Observação",
                            help="Campo opcional"
                        )
                    },
                    key=f"itens_outros_editor_{st.session_state['reset_saida']}"
                )

                col_botao_esquerda, col_botao_confirmar, col_botao_direita = st.columns([2, 1, 2])

                with col_botao_confirmar:
                    botao_confirmar_saida = st.form_submit_button(
                        "Confirmar saída",
                        disabled=st.session_state["bloqueado"],
                        use_container_width=True
                    )

                botao_restaurar_padrao_saida = False

            else:
                st.markdown(f"### Ajustes da {tipo_saida.lower()}")
                st.caption(
                    "Altere a quantidade final de cada item somente quando o pedido for diferente do padrão. "
                    "Exemplo: na ILHA, Blocos cupons já vem com 6 como padrão; se trocar para 5, o sistema baixa 5 blocos."
                )

                definicoes_checklist = obter_definicoes_checklist(tipo_saida, tipo_monzi)
                colunas_ajustes = st.columns(3)

                for indice_def, definicao in enumerate(definicoes_checklist):
                    coluna_atual = colunas_ajustes[indice_def % 3]

                    with coluna_atual:
                        ajustes_rascunho = rascunho_saida.get("ajustes_checklist", {})

                        ajustes_checklist[definicao["chave"]] = st.number_input(
                            definicao["grupo"],
                            min_value=0,
                            step=1,
                            value=int(ajustes_rascunho.get(definicao["chave"], definicao["padrao"])),
                            key=f"ajuste_{tipo_saida}_{tipo_monzi}_{definicao['chave']}_{st.session_state['reset_saida']}"
                        )

                st.markdown("### Produtos extras da saída")
                st.caption(
                    "Adicione quantos produtos extras forem necessários. "
                    "Use o botão de + da tabela para criar novas linhas. Se o produto já existir na saída, a quantidade será somada."
                )

                produtos_extras_rascunho = []

                for extra in rascunho_saida.get("produtos_extras", []):
                    codigo_extra_rascunho = str(extra.get("codigo_produto", "")).strip()
                    nome_extra_rascunho = str(extra.get("produto", "")).strip()
                    quantidade_extra_rascunho = extra.get("quantidade", 0)

                    produto_opcao_rascunho = ""
                    if codigo_extra_rascunho and nome_extra_rascunho:
                        produto_opcao_rascunho = f"{codigo_extra_rascunho} - {nome_extra_rascunho}"

                    produtos_extras_rascunho.append({
                        "Produto": produto_opcao_rascunho,
                        "Quantidade": quantidade_extra_rascunho
                    })

                if not produtos_extras_rascunho:
                    produtos_extras_rascunho = [{"Produto": "", "Quantidade": 0}]

                df_extras_editor = st.data_editor(
                    pd.DataFrame(produtos_extras_rascunho),
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        "Produto": st.column_config.SelectboxColumn(
                            "Produto",
                            options=opcoes_produtos_saida,
                            required=False
                        ),
                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            min_value=0,
                            step=1,
                            default=0,
                            required=False
                        )
                    },
                    key=f"produtos_extras_editor_{st.session_state['reset_saida']}"
                )

                col_botao_esquerda, col_botao_confirmar, col_botao_restaurar, col_botao_direita = st.columns([2, 1, 1, 2])

                with col_botao_confirmar:
                    botao_confirmar_saida = st.form_submit_button(
                        "Confirmar saída",
                        disabled=st.session_state["bloqueado"],
                        use_container_width=True
                    )

                with col_botao_restaurar:
                    botao_restaurar_padrao_saida = st.form_submit_button(
                        "Restaurar padrão torre/ilha",
                        disabled=st.session_state["bloqueado"],
                        use_container_width=True
                    )

        if tipo_saida != "OUTROS" and botao_restaurar_padrao_saida:
            ajustes_padrao = {
                definicao["chave"]: int(definicao["padrao"])
                for definicao in obter_definicoes_checklist(tipo_saida, tipo_monzi)
            }

            st.session_state["rascunho_saida"] = {
                "pedido": pedido_saida.strip(),
                "tipo_saida": tipo_saida,
                "tipo_monzi": tipo_monzi,
                "observacao": observacao_saida.strip(),
                "ajustes_checklist": ajustes_padrao,
                "produtos_extras": []
            }
            st.session_state["erro_saida_form"] = None
            st.session_state["erro_confirmar_saida"] = None
            st.session_state["reset_saida"] += 1
            st.rerun()

        if botao_confirmar_saida:
            st.session_state["erro_saida_form"] = None
            st.session_state["erro_confirmar_saida"] = None

            produtos_manuais = []

            if tipo_saida == "OUTROS" and df_itens_outros_editor is not None and not df_itens_outros_editor.empty:
                for _, linha_item in df_itens_outros_editor.iterrows():
                    produto_item = str(linha_item.get("Produto", "") or "").strip()
                    quantidade_item = linha_item.get("Quantidade", 0)
                    observacao_item = str(linha_item.get("Observação", "") or "").strip()

                    try:
                        quantidade_item = float(quantidade_item or 0)
                    except Exception:
                        quantidade_item = 0

                    if not produto_item or quantidade_item <= 0:
                        continue

                    codigo_item = produto_item.split(" - ")[0]
                    nome_item = produto_item.split(" - ", 1)[1] if " - " in produto_item else produto_item

                    produtos_manuais.append({
                        "codigo_produto": codigo_item,
                        "produto": nome_item,
                        "quantidade": int(quantidade_item) if quantidade_item.is_integer() else quantidade_item,
                        "observacao": observacao_item
                    })

            if not pedido_saida.strip():
                st.session_state["erro_saida_form"] = "Informe o número do pedido."
            elif pedido_saida_ja_existe(movimentacoes, pedido_saida.strip()):
                st.session_state["erro_saida_form"] = (
                    "Erro ao registrar saída: Este pedido já possui saída registrada. "
                    "Não é possível baixar novamente."
                )
            elif tipo_saida == "OUTROS" and not produtos_manuais:
                st.session_state["erro_saida_form"] = "Informe pelo menos um produto para a saída."
            else:
                if tipo_saida == "OUTROS":
                    df_saida = adicionar_produtos_extras(
                        df_saida=pd.DataFrame(),
                        produtos_extras=produtos_manuais,
                        produtos=produtos
                    )

                    observacoes_por_codigo = {}
                    for item_manual in produtos_manuais:
                        codigo_observacao = str(item_manual.get("codigo_produto", "")).strip()
                        observacao_manual = str(item_manual.get("observacao", "") or "").strip()

                        if not codigo_observacao:
                            continue

                        if observacao_manual:
                            observacoes_por_codigo.setdefault(codigo_observacao, [])
                            if observacao_manual not in observacoes_por_codigo[codigo_observacao]:
                                observacoes_por_codigo[codigo_observacao].append(observacao_manual)
                        else:
                            observacoes_por_codigo.setdefault(codigo_observacao, [])

                    if not df_saida.empty:
                        df_saida["observacao"] = df_saida["codigo_produto"].astype(str).map(
                            lambda codigo: " | ".join(observacoes_por_codigo.get(str(codigo), []))
                        )

                    produtos_extras = []
                else:
                    df_saida = montar_saida(
                        tipo_saida=tipo_saida,
                        tipo_monzi=tipo_monzi,
                        kits=kits,
                        composicao_kits=composicao_kits,
                        produtos=produtos
                    )

                    if df_saida.empty:
                        st.session_state["erro_saida_form"] = "Nenhum item foi encontrado para a saída."

                    if not st.session_state.get("erro_saida_form"):
                        df_saida = aplicar_ajustes_checklist(
                            df_saida=df_saida,
                            ajustes_checklist=ajustes_checklist,
                            tipo_saida=tipo_saida,
                            tipo_monzi=tipo_monzi,
                            produtos=produtos
                        )

                        produtos_extras = []

                        if df_extras_editor is not None and not df_extras_editor.empty:
                            for _, linha_extra in df_extras_editor.iterrows():
                                produto_extra = str(linha_extra.get("Produto", "") or "").strip()
                                quantidade_extra = linha_extra.get("Quantidade", 0)

                                try:
                                    quantidade_extra = float(quantidade_extra or 0)
                                except Exception:
                                    quantidade_extra = 0

                                if not produto_extra or quantidade_extra <= 0:
                                    continue

                                codigo_extra = produto_extra.split(" - ")[0]
                                nome_extra = produto_extra.split(" - ", 1)[1] if " - " in produto_extra else produto_extra

                                produtos_extras.append({
                                    "codigo_produto": codigo_extra,
                                    "produto": nome_extra,
                                    "quantidade": int(quantidade_extra) if quantidade_extra.is_integer() else quantidade_extra
                                })

                        df_saida = adicionar_produtos_extras(
                            df_saida=df_saida,
                            produtos_extras=produtos_extras,
                            produtos=produtos
                        )

                if not st.session_state.get("erro_saida_form"):
                    if df_saida.empty:
                        st.session_state["erro_saida_form"] = "Nenhum item será baixado com os ajustes informados."
                    else:
                        saida_confirmacao = {
                            "pedido": pedido_saida.strip(),
                            "tipo_saida": tipo_saida,
                            "tipo_monzi": tipo_monzi,
                            "observacao": observacao_saida.strip(),
                            "ajustes_checklist": ajustes_checklist,
                            "produtos_extras": produtos_manuais if tipo_saida == "OUTROS" else produtos_extras,
                            "itens": df_saida.to_dict("records")
                        }

                        st.session_state["rascunho_saida"] = saida_confirmacao
                        st.session_state["confirmar_saida"] = saida_confirmacao
                        st.session_state["simulacao_saida"] = None
                        st.rerun()

            if st.session_state.get("erro_saida_form"):
                if tipo_saida == "OUTROS":
                    st.session_state["rascunho_saida"] = {
                        "pedido": pedido_saida.strip(),
                        "tipo_saida": tipo_saida,
                        "tipo_monzi": tipo_monzi,
                        "observacao": observacao_saida.strip(),
                        "ajustes_checklist": {},
                        "produtos_extras": produtos_manuais
                    }
                else:
                    produtos_extras_rascunho_erro = []

                    if df_extras_editor is not None and not df_extras_editor.empty:
                        for _, linha_extra in df_extras_editor.iterrows():
                            produto_extra = str(linha_extra.get("Produto", "") or "").strip()
                            quantidade_extra = linha_extra.get("Quantidade", 0)

                            try:
                                quantidade_extra = float(quantidade_extra or 0)
                            except Exception:
                                quantidade_extra = 0

                            if not produto_extra or quantidade_extra <= 0:
                                continue

                            codigo_extra = produto_extra.split(" - ")[0]
                            nome_extra = produto_extra.split(" - ", 1)[1] if " - " in produto_extra else produto_extra

                            produtos_extras_rascunho_erro.append({
                                "codigo_produto": codigo_extra,
                                "produto": nome_extra,
                                "quantidade": int(quantidade_extra) if quantidade_extra.is_integer() else quantidade_extra
                            })

                    st.session_state["rascunho_saida"] = {
                        "pedido": pedido_saida.strip(),
                        "tipo_saida": tipo_saida,
                        "tipo_monzi": tipo_monzi,
                        "observacao": observacao_saida.strip(),
                        "ajustes_checklist": ajustes_checklist,
                        "produtos_extras": produtos_extras_rascunho_erro
                    }

        if st.session_state.get("erro_saida_form"):
            exibir_alerta_temporario(st.session_state["erro_saida_form"], tipo="error")

    elif aba_atual == "Cadastro de Produtos":
        st.subheader("Cadastro de Produtos")

        with st.form(f"form_cadastro_produtos_{st.session_state['reset_cadastro']}"):
            nome = st.text_input(
                "Nome do produto",
                placeholder="Ex: Saco veludo",
                key=f"nome_cadastro_{st.session_state['reset_cadastro']}"
            )

            unidade = st.selectbox(
                "Unidade",
                [
                    "Unidade",
                    "Rolo",
                    "Metro",
                    "Ml",
                    "Bloco"
                ],
                key=f"unidade_cadastro_{st.session_state['reset_cadastro']}"
            )

            estoque_minimo = st.number_input(
                "Estoque mínimo",
                min_value=0,
                step=1,
                key=f"estoque_minimo_cadastro_{st.session_state['reset_cadastro']}"
            )

            col_vazio_esq, col_direita, col_vazio_dir = st.columns([4, 1, 4])

            with col_direita:
                botao_cadastro = st.form_submit_button("Cadastrar")

        if botao_cadastro:
            if not nome.strip():
                st.session_state["mensagem_erro"] = "Informe o nome do produto."
                st.rerun()

            elif produto_nome_ja_existe(produtos, nome):
                st.session_state["mensagem_erro"] = "Já existe um produto cadastrado com esse nome."
                st.rerun()

            else:
                st.session_state["confirmar_cadastro"] = {
                    "nome": nome.strip(),
                    "unidade": unidade,
                    "estoque_minimo": int(estoque_minimo)
                }

                st.rerun()

    elif aba_atual == "Edição de Produtos":
        st.subheader("Edição de Produtos")

        produtos_edicao = produtos.copy()

        if produtos_edicao.empty:
            st.warning("Nenhum produto cadastrado.")
        else:
            produtos_edicao["produto_opcao"] = (
                produtos_edicao["codigo"].astype(str) + " - " + produtos_edicao["nome"]
            )

            produto_selecionado = st.selectbox(
                "Produto para editar",
                produtos_edicao["produto_opcao"].tolist(),
                key=f"produto_edicao_{st.session_state['reset_edicao']}"
            )

            codigo_selecionado = produto_selecionado.split(" - ")[0]

            produto_linha = produtos_edicao[
                produtos_edicao["codigo"].astype(str) == str(codigo_selecionado)
            ].iloc[0]

            unidades = [
                "Unidade",
                "Rolo",
                "Metro",
                "Ml",
                "Bloco"
            ]

            unidade_atual = str(produto_linha["unidade"])

            if unidade_atual in unidades:
                index_unidade = unidades.index(unidade_atual)
            else:
                index_unidade = 0

            ativo_atual = str(produto_linha["ativo"])

            if ativo_atual not in ["SIM", "NÃO"]:
                ativo_atual = "SIM"

            with st.form(
                f"form_edicao_produtos_{st.session_state['reset_edicao']}_{codigo_selecionado}"
            ):
                nome_editado = st.text_input(
                    "Nome do produto",
                    value=str(produto_linha["nome"]),
                    key=f"nome_edicao_{st.session_state['reset_edicao']}_{codigo_selecionado}"
                )

                unidade_editada = st.selectbox(
                    "Unidade",
                    unidades,
                    index=index_unidade,
                    key=f"unidade_edicao_{st.session_state['reset_edicao']}_{codigo_selecionado}"
                )

                estoque_minimo_editado = st.number_input(
                    "Estoque mínimo",
                    min_value=0,
                    step=1,
                    value=int(produto_linha["estoque_minimo"]),
                    key=f"estoque_minimo_edicao_{st.session_state['reset_edicao']}_{codigo_selecionado}"
                )

                ativo_editado = st.selectbox(
                    "Ativo",
                    ["SIM", "NÃO"],
                    index=0 if ativo_atual == "SIM" else 1,
                    key=f"ativo_edicao_{st.session_state['reset_edicao']}_{codigo_selecionado}"
                )

                col_vazio_esq, col_direita, col_vazio_dir = st.columns([4, 1, 4])

                with col_direita:
                    botao_edicao = st.form_submit_button("Atualizar")

            if botao_edicao:
                estoque_atual_produto = int(produto_linha["estoque_atual"])

                if not nome_editado.strip():
                    st.session_state["mensagem_erro"] = "Informe o nome do produto."
                    st.rerun()

                elif produto_nome_ja_existe(
                    produtos,
                    nome_editado,
                    codigo_ignorar=codigo_selecionado
                ):
                    st.session_state["mensagem_erro"] = "Já existe outro produto cadastrado com esse nome."
                    st.rerun()

                elif ativo_editado == "NÃO" and estoque_atual_produto > 0:
                    st.session_state["mensagem_erro"] = (
                        "Não é possível inativar este produto, pois ele ainda possui estoque. "
                        "Para inativar, primeiro ajuste ou zere o estoque."
                    )
                    st.rerun()

                else:
                    st.session_state["confirmar_edicao"] = {
                        "codigo": str(codigo_selecionado),
                        "nome": nome_editado.strip(),
                        "unidade": unidade_editada,
                        "estoque_minimo": int(estoque_minimo_editado),
                        "ativo": ativo_editado
                    }

                    st.rerun()

    elif aba_atual == "Consulta de Kits":
        st.subheader("Consulta de Kits")

        kits_ativos = kits[kits["ativo"] == "SIM"].copy()

        if kits_ativos.empty:
            st.warning("Nenhum kit ativo encontrado.")
        else:
            kits_ativos["opcao_kit"] = (
                kits_ativos["codigo_kit"].astype(str) + " - " + kits_ativos["nome_kit"]
            )

            kit_selecionado = st.selectbox(
                "Kit",
                kits_ativos["opcao_kit"].tolist()
            )

            codigo_kit_selecionado = kit_selecionado.split(" - ")[0]

            st.markdown("### Composição direta")

            composicao_filtrada = composicao_kits[
                (composicao_kits["codigo_kit"] == codigo_kit_selecionado) &
                (composicao_kits["ativo"] == "SIM")
            ].copy()

            if composicao_filtrada.empty:
                st.info("Este kit ainda não possui composição cadastrada.")
            else:
                produtos_lookup = produtos[["codigo", "nome", "unidade"]].copy()
                produtos_lookup["codigo"] = produtos_lookup["codigo"].astype(str)

                kits_lookup = kits[["codigo_kit", "nome_kit"]].copy()
                kits_lookup["codigo_kit"] = kits_lookup["codigo_kit"].astype(str)

                def buscar_nome_item(row):
                    if row["tipo_item"] == "PRODUTO":
                        produto = produtos_lookup[
                            produtos_lookup["codigo"] == str(row["codigo_item"])
                        ]

                        if not produto.empty:
                            return produto.iloc[0]["nome"]

                        return "Produto não encontrado"

                    if row["tipo_item"] == "KIT":
                        kit = kits_lookup[
                            kits_lookup["codigo_kit"] == str(row["codigo_item"])
                        ]

                        if not kit.empty:
                            return kit.iloc[0]["nome_kit"]

                        return "Kit não encontrado"

                    return ""

                def buscar_unidade_item(row):
                    if row["tipo_item"] == "PRODUTO":
                        produto = produtos_lookup[
                            produtos_lookup["codigo"] == str(row["codigo_item"])
                        ]

                        if not produto.empty:
                            return produto.iloc[0]["unidade"]

                    return ""

                composicao_filtrada["item"] = composicao_filtrada.apply(
                    buscar_nome_item,
                    axis=1
                )

                composicao_filtrada["unidade"] = composicao_filtrada.apply(
                    buscar_unidade_item,
                    axis=1
                )

                composicao_filtrada = composicao_filtrada.rename(columns={
                    "id": "ID",
                    "codigo_kit": "Código do Kit",
                    "tipo_item": "Tipo",
                    "codigo_item": "Código do Item",
                    "item": "Item",
                    "quantidade": "Quantidade",
                    "unidade": "Unidade"
                })

                st.dataframe(
                    composicao_filtrada[
                        [
                            "ID",
                            "Código do Kit",
                            "Tipo",
                            "Código do Item",
                            "Item",
                            "Quantidade",
                            "Unidade"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            st.markdown("### Composição completa para baixa")

            quantidade_teste = st.number_input(
                "Quantidade do kit para simular",
                min_value=1,
                step=1,
                value=1
            )

            itens_completos = montar_composicao_completa(
                codigo_kit=codigo_kit_selecionado,
                quantidade_base=quantidade_teste,
                kits=kits,
                composicao_kits=composicao_kits,
                produtos=produtos
            )

            if not itens_completos:
                st.info("Nenhum produto final encontrado para este kit.")
            else:
                df_completo = pd.DataFrame(itens_completos)

                df_completo = (
                    df_completo
                    .groupby(["codigo_produto", "produto", "unidade"], as_index=False)
                    .agg({
                        "quantidade": "sum",
                        "estoque_atual": "max"
                    })
                )

                df_completo["saldo_apos_saida"] = (
                    df_completo["estoque_atual"] - df_completo["quantidade"]
                )

                df_completo["status"] = df_completo["saldo_apos_saida"].apply(
                    lambda saldo: "INSUFICIENTE" if saldo < 0 else "OK"
                )

                df_completo = df_completo.rename(columns={
                    "codigo_produto": "Código do Produto",
                    "produto": "Produto",
                    "unidade": "Unidade",
                    "quantidade": "Quantidade Necessária",
                    "estoque_atual": "Estoque Atual",
                    "saldo_apos_saida": "Saldo Após Saída",
                    "status": "Status"
                })

                df_completo = formatar_colunas_numericas_exibicao(
                    df_completo,
                    ["Quantidade Necessária", "Estoque Atual", "Saldo Após Saída"]
                )

                st.dataframe(
                    df_completo[
                        [
                            "Código do Produto",
                            "Produto",
                            "Quantidade Necessária",
                            "Unidade",
                            "Estoque Atual",
                            "Saldo Após Saída",
                            "Status"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

    elif aba_atual == "Histórico":
        st.subheader("Histórico de Movimentações")

        historico_base = movimentacoes.copy()

        if historico_base.empty:
            st.info("Nenhuma movimentação encontrada.")
            st.stop()

        historico_base["id"] = historico_base["id"].astype(str)
        historico_base["codigo_produto"] = historico_base["codigo_produto"].astype(str)
        historico_base["tipo"] = historico_base["tipo"].astype(str)
        historico_base["pedido"] = historico_base["pedido"].fillna("").astype(str)
        historico_base["observacao"] = historico_base["observacao"].fillna("").astype(str)
        historico_base["quantidade"] = pd.to_numeric(
            historico_base["quantidade"],
            errors="coerce"
        ).fillna(0)

        produtos_lookup = produtos[["codigo", "nome"]].copy()
        produtos_lookup["codigo"] = produtos_lookup["codigo"].astype(str)

        historico = historico_base.merge(
            produtos_lookup,
            left_on="codigo_produto",
            right_on="codigo",
            how="left"
        )

        historico["nome"] = historico["nome"].fillna("Produto não encontrado")

        historico_exibir = historico.rename(columns={
            "id": "ID",
            "codigo_produto": "Código do Produto",
            "nome": "Produto",
            "tipo": "Tipo",
            "pedido": "Pedido",
            "quantidade": "Quantidade",
            "observacao": "Observação",
            "criado_em": "Data"
        })

        colunas_historico = [
            "ID",
            "Código do Produto",
            "Produto",
            "Tipo",
            "Pedido",
            "Quantidade",
            "Observação",
            "Data"
        ]

        st.dataframe(
            historico_exibir[colunas_historico],
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.markdown("### Ações do histórico")

        pode_excluir_entrada = usuario_pode_acao_historico("excluir_entrada")
        pode_excluir_avaria = usuario_pode_acao_historico("excluir_avaria")
        pode_cancelar_saida = usuario_pode_acao_historico("cancelar_saida")

        if not pode_excluir_entrada and not pode_excluir_avaria and not pode_cancelar_saida:
            st.info("Seu perfil pode consultar o histórico, mas não possui ações liberadas nesta tela.")

        if pode_excluir_entrada:
            st.markdown("#### Excluir entrada")
            st.caption(
                "Exclua somente movimentações do tipo ENTRADA. "
                "A linha não será apagada da planilha; ela será marcada como ENTRADA_CANCELADA e o estoque será ajustado automaticamente."
            )

            entradas = historico[
                historico["tipo"].astype(str).str.upper() == "ENTRADA"
            ].copy()

            if entradas.empty:
                st.info("Nenhuma entrada ativa encontrada para exclusão.")
            else:
                entradas = entradas.sort_values("criado_em", ascending=False)

                entradas["opcao_exclusao"] = entradas.apply(
                    lambda row: (
                        f"{row['id']} - {row['nome']} | "
                        f"Qtd: {row['quantidade']} | "
                        f"Data: {row.get('criado_em', '')}"
                    ),
                    axis=1
                )

                entrada_selecionada = st.selectbox(
                    "Movimentação de entrada",
                    entradas["opcao_exclusao"].tolist(),
                    key=f"entrada_excluir_{st.session_state['reset_historico']}"
                )

                id_entrada = entrada_selecionada.split(" - ")[0]
                linha_entrada = entradas[entradas["id"] == id_entrada].iloc[0]

                st.write(f"**Produto:** {linha_entrada['nome']}")
                st.write(f"**Quantidade que será removida do estoque:** {linha_entrada['quantidade']}")
                st.write(f"**Data:** {linha_entrada.get('criado_em', '')}")

                if str(linha_entrada.get("observacao", "")).strip():
                    st.write(f"**Observação:** {linha_entrada['observacao']}")

                col_excluir_esq, col_excluir_centro, col_excluir_dir = st.columns([4, 1, 4])

                with col_excluir_centro:
                    botao_excluir_entrada = st.button(
                        "Excluir entrada",
                        type="primary",
                        disabled=st.session_state["bloqueado"]
                    )

                if botao_excluir_entrada and not st.session_state["bloqueado"]:
                    st.session_state["confirmar_exclusao_entrada"] = {
                        "id_movimentacao": id_entrada,
                        "produto": str(linha_entrada["nome"]),
                        "quantidade": int(linha_entrada["quantidade"]) if float(linha_entrada["quantidade"]).is_integer() else float(linha_entrada["quantidade"]),
                        "data": str(linha_entrada.get("criado_em", "")),
                        "observacao": str(linha_entrada.get("observacao", "")).strip()
                    }
                    st.rerun()

        if pode_excluir_entrada and (pode_excluir_avaria or pode_cancelar_saida):
            st.divider()

        if pode_excluir_avaria:
            st.markdown("#### Excluir avaria")
            st.caption(
                "Exclua somente movimentações ativas de avaria. "
                "A linha não será apagada da planilha; ela será marcada como AVARIA_CANCELADA e o item será devolvido ao estoque."
            )

            avarias = historico[
                (historico["tipo"].astype(str).str.upper() == "SAIDA") &
                (historico["pedido"].astype(str).str.upper() == "AVARIA")
            ].copy()

            if avarias.empty:
                st.info("Nenhuma avaria ativa encontrada para exclusão.")
            else:
                avarias = avarias.sort_values("criado_em", ascending=False)

                avarias["opcao_exclusao_avaria"] = avarias.apply(
                    lambda row: (
                        f"{row['id']} - {row['nome']} | "
                        f"Qtd: {row['quantidade']} | "
                        f"Data: {row.get('criado_em', '')}"
                    ),
                    axis=1
                )

                avaria_selecionada = st.selectbox(
                    "Movimentação de avaria",
                    avarias["opcao_exclusao_avaria"].tolist(),
                    key=f"avaria_excluir_{st.session_state['reset_historico']}"
                )

                id_avaria = avaria_selecionada.split(" - ")[0]
                linha_avaria = avarias[avarias["id"] == id_avaria].iloc[0]

                st.write(f"**Produto:** {linha_avaria['nome']}")
                st.write(f"**Quantidade que será devolvida ao estoque:** {linha_avaria['quantidade']}")
                st.write(f"**Data:** {linha_avaria.get('criado_em', '')}")

                if str(linha_avaria.get("observacao", "")).strip():
                    st.write(f"**Observação:** {linha_avaria['observacao']}")

                col_avaria_esq, col_avaria_centro, col_avaria_dir = st.columns([4, 1, 4])

                with col_avaria_centro:
                    botao_excluir_avaria = st.button(
                        "Excluir avaria",
                        type="primary",
                        disabled=st.session_state["bloqueado"]
                    )

                if botao_excluir_avaria and not st.session_state["bloqueado"]:
                    st.session_state["confirmar_exclusao_avaria"] = {
                        "id_movimentacao": id_avaria,
                        "produto": str(linha_avaria["nome"]),
                        "quantidade": int(linha_avaria["quantidade"]) if float(linha_avaria["quantidade"]).is_integer() else float(linha_avaria["quantidade"]),
                        "data": str(linha_avaria.get("criado_em", "")),
                        "observacao": str(linha_avaria.get("observacao", "")).strip()
                    }
                    st.rerun()

        if pode_excluir_avaria and pode_cancelar_saida:
            st.divider()

        if pode_cancelar_saida:
            st.markdown("#### Cancelar saída")
            st.caption(
                "Cancele uma saída inteira pelo pedido. "
                "O sistema devolve todos os produtos daquela TORRE, ILHA ou OUTROS ao estoque e marca as movimentações como canceladas."
            )

            tipos_saida_ativos = ["SAIDA_TORRE", "SAIDA_ILHA", "SAIDA_OUTROS"]

            saidas = historico[
                historico["tipo"].astype(str).str.upper().isin(tipos_saida_ativos)
            ].copy()

            saidas = saidas[saidas["pedido"].astype(str).str.strip() != ""]

            if saidas.empty:
                st.info("Nenhuma saída ativa encontrada para cancelamento.")
            else:
                saidas["pedido"] = saidas["pedido"].astype(str)
                saidas["tipo"] = saidas["tipo"].astype(str).str.upper()

                resumo_saidas = (
                    saidas
                    .groupby(["pedido", "tipo"], as_index=False)
                    .agg({
                        "id": "count",
                        "quantidade": "sum",
                        "criado_em": "max"
                    })
                    .rename(columns={
                        "id": "itens",
                        "quantidade": "quantidade_total",
                        "criado_em": "data"
                    })
                )

                resumo_saidas = resumo_saidas.sort_values("data", ascending=False)

                resumo_saidas["opcao_cancelamento"] = resumo_saidas.apply(
                    lambda row: (
                        f"{row['pedido']} | {row['tipo']} | "
                        f"Itens: {row['itens']} | Data: {row['data']}"
                    ),
                    axis=1
                )

                saida_selecionada = st.selectbox(
                    "Pedido de saída para cancelar",
                    resumo_saidas["opcao_cancelamento"].tolist(),
                    key=f"saida_cancelar_{st.session_state['reset_historico']}"
                )

                pedido_cancelar = saida_selecionada.split(" | ")[0]
                tipo_saida_cancelar = saida_selecionada.split(" | ")[1]

                itens_cancelamento = saidas[
                    (saidas["pedido"].astype(str) == pedido_cancelar) &
                    (saidas["tipo"].astype(str).str.upper() == tipo_saida_cancelar)
                ].copy()

                itens_cancelamento_exibir = itens_cancelamento.rename(columns={
                    "id": "ID",
                    "codigo_produto": "Código do Produto",
                    "nome": "Produto",
                    "tipo": "Tipo",
                    "pedido": "Pedido",
                    "quantidade": "Quantidade a Devolver",
                    "observacao": "Observação",
                    "criado_em": "Data"
                })

                st.markdown("##### Itens que serão devolvidos ao estoque")

                st.dataframe(
                    itens_cancelamento_exibir[
                        [
                            "ID",
                            "Código do Produto",
                            "Produto",
                            "Tipo",
                            "Pedido",
                            "Quantidade a Devolver",
                            "Data"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                col_botao_esquerda, col_botao_centro, col_botao_direita = st.columns([1, 1, 1])

                with col_botao_centro:
                    botao_cancelar_saida = st.button(
                        "Cancelar saída do pedido",
                        type="primary",
                        disabled=st.session_state["bloqueado"],
                        use_container_width=True
                    )

                if botao_cancelar_saida and not st.session_state["bloqueado"]:
                    itens_confirmacao = itens_cancelamento_exibir[
                        [
                            "ID",
                            "Código do Produto",
                            "Produto",
                            "Tipo",
                            "Pedido",
                            "Quantidade a Devolver",
                            "Data"
                        ]
                    ].to_dict("records")

                    st.session_state["confirmar_cancelamento_saida"] = {
                        "pedido": pedido_cancelar,
                        "tipo": tipo_saida_cancelar,
                        "total_itens": len(itens_confirmacao),
                        "itens": itens_confirmacao
                    }
                    st.rerun()

except Exception as e:
    exibir_alerta_temporario("Erro ao carregar ou registrar dados.", tipo="error")
    st.exception(e)
