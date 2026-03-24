"""Configuracao de logging integrada ao projeto principal."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

try:
    from . import config
except ImportError:  # pragma: no cover - compatibilidade standalone
    from auto_delete_compat import carregar_modulo_local

    config = carregar_modulo_local("config")


class CallbackLogHandler(logging.Handler):
    """Encaminha logs para um callback externo sem acoplar a UI."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__(level=logging.INFO)
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._callback(record.getMessage())
        except Exception:
            pass


def configurar_logger(
    nome: str = "auto_delete_clientes",
    *,
    run_id: Optional[str] = None,
    callback: Optional[Callable[[str], None]] = None,
) -> logging.Logger:
    """Cria logger isolado em logs/auto_delete/execucoes."""
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = logging.getLogger(f"{nome}.{run_id}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    logs_dir = Path(config.EXECUCOES_LOG_DIR)
    logs_dir.mkdir(parents=True, exist_ok=True)

    formato = logging.Formatter(
        "[%(asctime)s] [AUTO_DELETE_CLIENTES] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    arquivo = logging.FileHandler(
        logs_dir / f"auto_delete_clientes_{run_id}.log",
        encoding="utf-8",
    )
    arquivo.setLevel(logging.DEBUG)
    arquivo.setFormatter(formato)
    logger.addHandler(arquivo)

    if callback is not None:
        logger.addHandler(CallbackLogHandler(callback))

    return logger
