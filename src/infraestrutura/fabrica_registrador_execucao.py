"""
Cria e configura o logger técnico com rotação de arquivo.
"""

import logging
from logging.handlers import RotatingFileHandler

import config
from src.infraestrutura.caminhos import REPORTS_DIR


def criar_logger(nome: str = "rpa") -> logging.Logger:
    """
    Retorna um logger com handler rotativo em reports/errors.log.
    Logs de nível DEBUG também são exibidos no console.
    """
    logger = logging.getLogger(nome)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Handler de arquivo com rotação
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    caminho_log = REPORTS_DIR / "errors.log"
    handler_arquivo = RotatingFileHandler(
        caminho_log,
        maxBytes=config.MAX_BYTES_LOG_ERROS,
        backupCount=config.MAX_BACKUPS_LOG_ERROS,
        encoding="utf-8"
    )
    handler_arquivo.setLevel(logging.WARNING)
    formato_arquivo = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler_arquivo.setFormatter(formato_arquivo)

    # Handler de console
    handler_console = logging.StreamHandler()
    handler_console.setLevel(logging.DEBUG)
    formato_console = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
    handler_console.setFormatter(formato_console)

    logger.addHandler(handler_arquivo)
    logger.addHandler(handler_console)

    return logger
