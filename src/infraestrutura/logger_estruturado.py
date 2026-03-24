"""
Logger com tags estruturadas para rastreamento de execucao.
Formato: [FASE][TAG] indice=N tabela=NOME timestamp=ISO status=STATUS extras...
"""

import logging
from datetime import datetime
from typing import Optional


class LoggerEstruturado:
    """Emite logs com tags estruturadas sobre o logger padrao."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or logging.getLogger("rpa")

    def fase1(self, tag: str, indice: int = 0, nome_tabela: str = "", status: str = "OK", **extras: str) -> None:
        self._emitir("F1", tag, indice, nome_tabela, status, **extras)

    def fase2(self, tag: str, indice: int = 0, nome_tabela: str = "", status: str = "OK", **extras: str) -> None:
        self._emitir("F2", tag, indice, nome_tabela, status, **extras)

    def checkpoint(self, tag: str, **extras: str) -> None:
        self._emitir("CHECKPOINT", tag, **extras)

    def _emitir(
        self,
        prefixo: str,
        tag: str,
        indice: int = 0,
        nome_tabela: str = "",
        status: str = "OK",
        **extras: str,
    ) -> None:
        timestamp = datetime.now().isoformat(timespec="seconds")
        partes = [f"[{prefixo}][{tag}]"]

        if indice:
            partes.append(f"indice={indice}")
        if nome_tabela:
            partes.append(f"tabela={nome_tabela}")

        partes.append(f"timestamp={timestamp}")
        partes.append(f"status={status}")

        for chave, valor in extras.items():
            if valor not in ("", None):
                partes.append(f"{chave}={valor}")

        mensagem = " ".join(partes)

        if tag == "ERRO":
            self._logger.error(mensagem)
        else:
            self._logger.info(mensagem)
