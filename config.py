"""
Configuração central do projeto RPA Tabela Cliente Por Nome.
Carrega variáveis do .env, define paths, seletores DOM e flags operacionais.
"""

import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths base
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
PUBLIC_DIR = BASE_DIR / "public"


# ---------------------------------------------------------------------------
# Carregamento do .env
# ---------------------------------------------------------------------------

def _carregar_env() -> None:
    """Lê o arquivo .env e injeta as variáveis no ambiente."""
    arquivo_env = BASE_DIR / ".env"
    if not arquivo_env.exists():
        return
    for linha_bruta in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha_bruta.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(
            chave.strip(),
            valor.strip().strip('"').strip("'")
        )


def recarregar_configuracoes(sobrescrever_env: bool = False) -> None:
    """
    Recarrega as variáveis do .env, permitindo ajustes entre execuções
    sem reiniciar a aplicação.
    """
    arquivo_env = BASE_DIR / ".env"
    if not arquivo_env.exists():
        return
    for linha_bruta in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha_bruta.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if sobrescrever_env or chave not in os.environ:
            os.environ[chave] = valor
    _aplicar_variaveis()


def _aplicar_variaveis() -> None:
    """Atualiza as variáveis globais com os valores atuais do ambiente."""
    global URL_LOGIN, EMAIL_LOGIN, SENHA_LOGIN
    global HEADLESS, DEBUG_VISUAL, CONFIRMAR_FINAL
    global TIMEOUT, PAGE_LOAD_TIMEOUT, TIMEOUT_COPIA_FINALIZADA
    global INTERVALO_LOG_PROGRESSO_POPUP
    global MAX_SCREENSHOTS_ARMAZENADOS, MAX_REGISTROS_PROCESSAMENTO
    global MAX_REGISTROS_TRACE, MAX_BYTES_LOG_ERROS, MAX_BACKUPS_LOG_ERROS
    global MAX_EXECUCOES_LOG

    URL_LOGIN = os.getenv("URL_LOGIN", "")
    EMAIL_LOGIN = os.getenv("EMAIL_LOGIN", "")
    SENHA_LOGIN = os.getenv("SENHA_LOGIN", "")

    HEADLESS = os.getenv("HEADLESS", "false").lower() in {"1", "true", "sim", "yes"}
    DEBUG_VISUAL = os.getenv("DEBUG_VISUAL", "false").lower() in {"1", "true", "sim", "yes"}
    CONFIRMAR_FINAL = os.getenv("CONFIRMAR_FINAL", "true").lower() in {"1", "true", "sim", "yes"}

    TIMEOUT = int(os.getenv("TIMEOUT", "30"))
    PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
    TIMEOUT_COPIA_FINALIZADA = int(os.getenv("TIMEOUT_COPIA_FINALIZADA", "600"))
    INTERVALO_LOG_PROGRESSO_POPUP = int(os.getenv("INTERVALO_LOG_PROGRESSO_POPUP", "30"))

    MAX_SCREENSHOTS_ARMAZENADOS = int(os.getenv("MAX_SCREENSHOTS_ARMAZENADOS", "100"))
    MAX_REGISTROS_PROCESSAMENTO = int(os.getenv("MAX_REGISTROS_PROCESSAMENTO", "500"))
    MAX_REGISTROS_TRACE = int(os.getenv("MAX_REGISTROS_TRACE", "200"))
    MAX_BYTES_LOG_ERROS = int(os.getenv("MAX_BYTES_LOG_ERROS", "5242880"))
    MAX_BACKUPS_LOG_ERROS = int(os.getenv("MAX_BACKUPS_LOG_ERROS", "3"))
    MAX_EXECUCOES_LOG = int(os.getenv("MAX_EXECUCOES_LOG", "20"))


# Inicializa ao importar
_carregar_env()

URL_LOGIN: str = ""
EMAIL_LOGIN: str = ""
SENHA_LOGIN: str = ""
HEADLESS: bool = False
DEBUG_VISUAL: bool = False
CONFIRMAR_FINAL: bool = True
TIMEOUT: int = 30
PAGE_LOAD_TIMEOUT: int = 60
TIMEOUT_COPIA_FINALIZADA: int = 600
INTERVALO_LOG_PROGRESSO_POPUP: int = 30
MAX_SCREENSHOTS_ARMAZENADOS: int = 100
MAX_REGISTROS_PROCESSAMENTO: int = 500
MAX_REGISTROS_TRACE: int = 200
MAX_BYTES_LOG_ERROS: int = 5242880
MAX_BACKUPS_LOG_ERROS: int = 3
MAX_EXECUCOES_LOG: int = 20

_aplicar_variaveis()


# ---------------------------------------------------------------------------
# Seletores DOM
# ---------------------------------------------------------------------------

SELETORES: dict[str, list[tuple[str, str]]] = {

    # --- Login ---
    "campo_email": [
        ("id", "user_email"),
        ("css selector", "input[name='user[email]']"),
        ("css selector", "input[type='email']"),
    ],
    "campo_senha": [
        ("id", "user_password"),
        ("css selector", "input[name='user[password]']"),
        ("css selector", "input[type='password']"),
    ],
    "botao_entrar": [
        ("css selector", "input[name='commit'][value='Entrar']"),
        ("css selector", "input.btn.btn-primary[type='submit'][value='Entrar']"),
        ("css selector", "button[type='submit']"),
        ("xpath", "//input[@type='submit']"),
        ("xpath", "//input[@name='commit' and @value='Entrar']"),
        ("xpath", "//button[contains(text(),'Entrar')]"),
    ],

    # --- Menu de navegação ---
    "menu_cadastros": [
        ("xpath", "//a[contains(text(),'Cadastros')]"),
        ("xpath", "//a[@tabindex='-1' and contains(.,'Cadastros')]"),
    ],
    "menu_tabelas_preco": [
        ("xpath", "//a[.//span[contains(text(),'Tabelas de preço')]]"),
        ("xpath", "//span[contains(text(),'Tabelas de preço')]/ancestor::a"),
    ],
    "menu_tabelas_cliente": [
        ("xpath", "//a[@href='/customer_price_tables']"),
        ("xpath", "//a[contains(text(),'Tabelas de cliente')]"),
    ],

    # --- Filtros da listagem ---
    "container_select2_filial": [
        ("xpath", "//select[@id='search_price_tables_corporation_id']/following-sibling::span[contains(@class,'select2')]"),
        ("xpath", "//select[@id='search_price_tables_branch_id']/following-sibling::span[contains(@class,'select2')]"),
    ],
    "botao_remover_filial": [
        ("css selector", ".select2-selection__choice__remove"),
        ("xpath", "//span[contains(@class,'select2-selection__choice__remove')]"),
    ],
    "container_select2_ativa": [
        ("xpath", "//select[@id='search_price_tables_active']/following-sibling::span[contains(@class,'select2')]"),
    ],
    "input_pesquisa_nome": [
        ("id", "search_price_tables_name"),
        ("css selector", "input[name='search[price_tables][name]']"),
    ],
    "botao_pesquisar": [
        ("css selector", "button#submit.btn.btn-primary.vue-button.btn-sm:not(.btn-align-input)"),
        ("xpath", "//button[@id='submit' and contains(@class,'btn-sm') and not(contains(@class,'btn-align-input')) and .//i[contains(@class,'fa-search')]]"),
        ("id", "submit"),
        ("css selector", "button#submit.btn-primary"),
    ],
    "botao_expandir_filtros": [
        ("css selector", "button.btn-primary.vue-button[type='button'] i.fa-angle-up"),
        ("xpath", "//button[contains(@class,'vue-button')][.//i[contains(@class,'fa-angle')]]"),
    ],
    "input_vigencia_fim": [
        ("id", "search_price_tables_effective_until"),
        ("css selector", "input[name='search[price_tables][effective_until]']"),
    ],

    # --- Tabela de resultados ---
    "linhas_tabela": [
        ("css selector", "tr.vue-item"),
        ("xpath", "//tr[contains(@class,'vue-item')]"),
    ],
    "botao_dropdown_acoes": [
        ("css selector", "button.dropdown-toggle.more-actions"),
        ("xpath", ".//button[contains(@class,'dropdown-toggle') and contains(@class,'more-actions')]"),
    ],
    "opcao_duplicar_tabela": [
        ("xpath", ".//a[.//span[contains(text(),'Duplicar tabela')]]"),
        ("xpath", ".//span[contains(text(),'Duplicar tabela')]/ancestor::a"),
    ],
    "opcao_reajuste": [
        ("xpath", ".//a[.//span[contains(text(),'Reajuste')]]"),
        ("xpath", ".//span[contains(text(),'Reajuste')]/ancestor::a"),
    ],
    "botao_proxima_pagina": [
        ("xpath", "//button[.//i[contains(@class,'fa-angle-right')]][not(@disabled)]"),
        ("css selector", "button.btn-default:not([disabled]) i.fa-angle-right"),
    ],
    "info_registros": [
        ("css selector", "span.entries-info"),
        ("xpath", "//span[contains(@class,'entries-info')]"),
    ],

    # --- Modal de duplicação ---
    "switch_duplicacao": [
        ("css selector", "div.swal2-popup.swal2-modal.swal2-show #duplicate_customers + span.switchery"),
        ("xpath", "//div[contains(@class,'swal2-popup') and contains(@class,'swal2-show')]//*[@id='duplicate_customers']/following-sibling::span[contains(@class,'switchery')]"),
        ("css selector", "span.switchery"),
        ("xpath", "//span[contains(@class,'switchery')]"),
    ],
    "botao_swal_confirmar": [
        ("css selector", "div.swal2-popup.swal2-modal.swal2-show button#swal-confirm.swal2-confirm"),
        ("xpath", "//div[contains(@class,'swal2-popup') and contains(@class,'swal2-show')]//button[@id='swal-confirm' and contains(@class,'swal2-confirm')]"),
        ("id", "swal-confirm"),
        ("css selector", "button.swal2-confirm"),
    ],

    # --- Tela de edição ---
    "input_nome_tabela": [
        ("id", "customer_price_table_name"),
        ("css selector", "input[name='customer_price_table[name]']"),
    ],
    "accordion_parametrizacoes": [
        ("id", "parameters_accordion"),
        ("css selector", "a#parameters_accordion"),
        ("xpath", "//a[contains(text(),'Parametrizações')]"),
    ],
    "input_data_inicio": [
        ("id", "customer_price_table_effective_since"),
        ("css selector", "input[name='customer_price_table[effective_since]']"),
    ],
    "input_data_fim": [
        ("id", "customer_price_table_effective_until"),
        ("css selector", "input[name='customer_price_table[effective_until]']"),
    ],
    "botao_salvar_edicao": [
        ("xpath", "//a[@id='submit' and contains(@class,'btn-primary') and .//span[normalize-space(text())='Salvar']]"),
        ("css selector", "a#submit.btn.btn-primary"),
        ("xpath", "//a[@id='submit' and contains(@class,'btn-primary') and .//i[contains(@class,'fa-save')]]"),
        ("css selector", "a#submit.btn-primary"),
    ],

    # --- Modal de reajuste ---
    "botao_considerar_todos_trechos": [
        ("xpath", "//button[.//span[contains(text(),'Considerar todos os trechos')]]"),
        ("css selector", "button.vue-button.btn-xs i.fa-square"),
    ],
    "aba_reajustar_taxas": [
        ("id", "fee"),
        ("xpath", "//li[@id='fee']"),
    ],
    "aba_reajustar_excedentes": [
        ("id", "overweights"),
        ("xpath", "//li[@id='overweights']"),
    ],
    "aba_reajustar_adicionais": [
        ("id", "additionals"),
        ("xpath", "//li[@id='additionals']"),
    ],
    "container_select2_taxa": [
        ("xpath", "//select[@id='readjust_form_fee']/following-sibling::span[contains(@class,'select2')]"),
        ("css selector", "span.select2-container span.select2-selection--single"),
    ],
    "input_valor_reajuste_modal": [
        ("id", "readjust_form_value"),
        ("css selector", "input[name='readjust_form[value]']"),
    ],
    "botao_adicionar_taxa": [
        ("css selector", "button[name='add_fee']"),
        ("xpath", "//button[@name='add_fee']"),
    ],
    "botao_salvar_reajuste": [
        ("id", "save-btn"),
        ("css selector", "button#save-btn"),
    ],
    "botao_fechar_modal": [
        ("css selector", "button.close"),
        ("css selector", "a[name='close_modal_button']"),
        ("xpath", "//a[@data-dismiss='modal' and .//span[contains(text(),'Fechar')]]"),
    ],

    # --- DateRangePicker ---
    "daterangepicker_input_inicio": [
        ("css selector", ".daterangepicker .calendar.left input.input-mini"),
        ("css selector", "input[name='daterangepicker_start']"),
    ],
    "daterangepicker_input_fim": [
        ("css selector", ".daterangepicker .calendar.right input.input-mini"),
        ("css selector", "input[name='daterangepicker_end']"),
    ],
    "botao_confirmar_daterangepicker": [
        ("css selector", "button.applyBtn"),
        ("xpath", "//button[contains(@class,'applyBtn')]"),
    ],
}


# ---------------------------------------------------------------------------
# Mapeamento de abas de reajuste
# ---------------------------------------------------------------------------

MAPA_ABAS_REAJUSTE: dict[str, str] = {
    "Taxa": "fee",
    "Reajustar Taxas": "fee",
    "Taxas": "fee",
    "Excedente": "overweights",
    "Reajustar Excedentes": "overweights",
    "Excedentes": "overweights",
    "Adicional": "additionals",
    "Reajustar Adicionais": "additionals",
    "Adicionais": "additionals",
}
