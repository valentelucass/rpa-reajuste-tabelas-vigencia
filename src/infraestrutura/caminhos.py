"""
Resolução de paths compatível com execução em desenvolvimento e com PyInstaller.

Quando empacotado (frozen):
- Recursos bundled (ícones, fontes) ficam em sys._MEIPASS (_internal/)
- Diretórios graváveis (logs, reports) e .env ficam junto ao .exe
"""

import shutil
import sys
from pathlib import Path


def _resolver_dir_recursos() -> Path:
    """Diretório dos recursos empacotados (public/, fonts)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent


def _resolver_dir_app() -> Path:
    """Diretório do aplicativo (onde ficam logs/, reports/, .env)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def _migrar_conteudo_diretorio(origem: Path, destino: Path) -> None:
    """Move artefatos legados sem sobrescrever arquivos ja migrados."""
    if not origem.exists():
        return

    destino.mkdir(parents=True, exist_ok=True)
    for item in origem.iterdir():
        destino_item = destino / item.name
        if item.is_dir():
            _migrar_conteudo_diretorio(item, destino_item)
            try:
                item.rmdir()
            except OSError:
                pass
            continue
        if destino_item.exists():
            continue
        shutil.move(str(item), str(destino_item))

    try:
        origem.rmdir()
    except OSError:
        pass


def _migrar_logs_modulo_auto_delete_legado(origem: Path) -> None:
    """Consolida logs antigos do modulo dentro de logs/auto_delete."""
    if not origem.exists():
        return

    _migrar_conteudo_diretorio(origem / "screenshots", AUTO_DELETE_SCREENSHOTS_DIR)

    for item in list(origem.iterdir()):
        if item.is_dir():
            continue
        if item.suffix.lower() == ".log":
            destino = AUTO_DELETE_EXECUCOES_DIR / item.name
        else:
            destino = AUTO_DELETE_DIR / item.name
        if destino.exists():
            continue
        shutil.move(str(item), str(destino))

    try:
        origem.rmdir()
    except OSError:
        pass


RESOURCES_DIR = _resolver_dir_recursos()
APP_DIR = _resolver_dir_app()

PUBLIC_DIR = RESOURCES_DIR / "public"
LOGS_DIR = APP_DIR / "logs"
REPORTS_DIR = APP_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
AUTO_DELETE_DIR = LOGS_DIR / "auto_delete"
AUTO_DELETE_EXECUCOES_DIR = AUTO_DELETE_DIR / "execucoes"
AUTO_DELETE_SCREENSHOTS_DIR = AUTO_DELETE_DIR / "screenshots"
AUTO_DELETE_FALHAS_PENDENTES_PATH = AUTO_DELETE_DIR / "falhas_pendentes.json"
AUTO_DELETE_REPROCESSAMENTO_XLSX_PATH = AUTO_DELETE_DIR / "reprocessar.xlsx"
AUTO_DELETE_HISTORICO_EXECUCOES_PATH = AUTO_DELETE_DIR / "execucoes.json"
AUTO_DELETE_LEGACY_DIR = LOGS_DIR / "auto_delete_clientes"
AUTO_DELETE_MODULE_LEGACY_DIR = APP_DIR / "src" / "auto_delete_clientes" / "logs"

# Garante que diretórios graváveis existam desde o início (evita Errno 2 no exe)
for _dir in (LOGS_DIR, REPORTS_DIR, SCREENSHOTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

_migrar_conteudo_diretorio(AUTO_DELETE_LEGACY_DIR, AUTO_DELETE_DIR)
_migrar_logs_modulo_auto_delete_legado(AUTO_DELETE_MODULE_LEGACY_DIR)

for _dir in (AUTO_DELETE_DIR, AUTO_DELETE_EXECUCOES_DIR, AUTO_DELETE_SCREENSHOTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# Retrocompatibilidade — código legado que importe BASE_DIR continua funcionando
BASE_DIR = APP_DIR
