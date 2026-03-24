"""
Configuracao central do script de exclusao.
Carrega credenciais do .env do projeto pai e define seletores DOM.
"""

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def _resolver_dir_projeto() -> Path:
    """Resolve a raiz do projeto procurando um .env acima do módulo."""
    for candidato in [BASE_DIR.parent, BASE_DIR.parent.parent, BASE_DIR.parent.parent.parent]:
        if (candidato / ".env").exists():
            return candidato
    return BASE_DIR.parent.parent


PROJETO_PAI_DIR = _resolver_dir_projeto()

try:
    from src.infraestrutura.caminhos import (
        AUTO_DELETE_DIR as LOGS_DIR,
        AUTO_DELETE_EXECUCOES_DIR as EXECUCOES_LOG_DIR,
        AUTO_DELETE_REPROCESSAMENTO_XLSX_PATH as ARQUIVO_REPROCESSAMENTO,
        AUTO_DELETE_SCREENSHOTS_DIR as SCREENSHOTS_DIR,
        LOGS_DIR as LOGS_RAIZ_PROJETO,
    )
except Exception:  # pragma: no cover - compatibilidade standalone
    LOGS_RAIZ_PROJETO = PROJETO_PAI_DIR / "logs"
    LOGS_DIR = LOGS_RAIZ_PROJETO / "auto_delete"
    EXECUCOES_LOG_DIR = LOGS_DIR / "execucoes"
    SCREENSHOTS_DIR = LOGS_DIR / "screenshots"
    ARQUIVO_REPROCESSAMENTO = LOGS_DIR / "reprocessar.xlsx"


# ---------------------------------------------------------------------------
# Carregamento do .env (do projeto pai)
# ---------------------------------------------------------------------------

def _carregar_env() -> None:
    """Le o .env do projeto pai e injeta no ambiente."""
    arquivo_env = PROJETO_PAI_DIR / ".env"
    if not arquivo_env.exists():
        return
    for linha_bruta in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha_bruta.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()


# ---------------------------------------------------------------------------
# Variaveis de ambiente
# ---------------------------------------------------------------------------

URL_LOGIN: str = os.getenv("URL_LOGIN", "")
EMAIL_LOGIN: str = os.getenv("EMAIL_LOGIN", "")
SENHA_LOGIN: str = os.getenv("SENHA_LOGIN", "")

HEADLESS: bool = os.getenv("HEADLESS", "false").lower() in {"1", "true", "sim", "yes"}
DEBUG_VISUAL: bool = os.getenv("DEBUG_VISUAL", "true").lower() in {"1", "true", "sim", "yes"}

for _diretorio in (LOGS_DIR, EXECUCOES_LOG_DIR, SCREENSHOTS_DIR):
    _diretorio.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Constantes operacionais
# ---------------------------------------------------------------------------

TIMEOUT: int = 30
PAGE_LOAD_TIMEOUT: int = 60
MAX_TENTATIVAS_EXCLUSAO: int = 5
MAX_ERROS_CONSECUTIVOS: int = 3
ATRASO_MINIMO: float = 0.3
ATRASO_MAXIMO: float = 1.2
TIMEOUT_TOAST_SUCESSO: int = 20
TIMEOUT_TOAST_DESAPARECER: int = 15
TIMEOUT_RESPOSTA_EXCLUSAO: int = 120

URL_TABELAS_CLIENTE: str = "https://rodogarcia.eslcloud.com.br/customer_price_tables"


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
    ],

    # --- Menu de navegacao ---
    "menu_cadastros": [
        ("xpath", "//a[contains(text(),'Cadastros')]"),
    ],
    "menu_tabelas_preco": [
        ("xpath", "//a[.//span[contains(text(),'Tabelas de preço')]]"),
    ],
    "menu_tabelas_cliente": [
        ("xpath", "//a[@href='/customer_price_tables']"),
    ],

    # --- Filtros da listagem ---
    "container_select2_ativa": [
        ("xpath", "//select[@id='search_price_tables_active']/following-sibling::span[contains(@class,'select2')]"),
    ],
    "input_pesquisa_nome": [
        ("id", "search_price_tables_name"),
        ("css selector", "input[name='search[price_tables][name]']"),
    ],
    "input_vigencia_fim": [
        ("id", "search_price_tables_effective_until"),
        ("css selector", "input[name='search[price_tables][effective_until]']"),
    ],
    "botao_pesquisar": [
        ("css selector", "button#submit.btn.btn-primary.vue-button.btn-sm:not(.btn-align-input)"),
        ("xpath", "//button[@id='submit' and contains(@class,'btn-sm') and not(contains(@class,'btn-align-input')) and .//i[contains(@class,'fa-search')]]"),
        ("id", "submit"),
        ("css selector", "button#submit.btn-primary"),
    ],

    # --- Tabela de resultados ---
    "linhas_tabela": [
        ("css selector", "tr.vue-item"),
    ],
    "botao_dropdown_acoes": [
        ("css selector", "button.dropdown-toggle.more-actions"),
    ],
    "info_registros": [
        ("css selector", "span.entries-info"),
    ],

    # --- Opcao Excluir (relativo a linha) ---
    "opcao_excluir": [
        ("xpath", ".//li[@title='Excluir']//a[contains(@class,'dropdown-link')]"),
        ("xpath", ".//a[contains(@class,'dropdown-link')][.//span[normalize-space(text())='Excluir']]"),
        ("xpath", ".//span[normalize-space(text())='Excluir']/ancestor::a[contains(@class,'dropdown-link')]"),
    ],

    # --- Modal SweetAlert ---
    "botao_swal_confirmar": [
        ("css selector", "div.swal2-popup.swal2-modal.swal2-show button#swal-confirm.swal2-confirm"),
        ("id", "swal-confirm"),
        ("css selector", "button.swal2-confirm"),
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
    ],
}
