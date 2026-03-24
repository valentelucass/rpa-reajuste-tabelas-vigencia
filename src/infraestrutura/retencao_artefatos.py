"""
Limita o crescimento de artefatos de execução (screenshots, CSV, trace).
"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional

import config
from src.infraestrutura.caminhos import LOGS_DIR, SCREENSHOTS_DIR
from src.infraestrutura.registro_execucoes import limpar_execucoes_antigas


class RetencaoArtefatos:
    """Aplica políticas de retenção após cada execução."""

    def __init__(
        self,
        run_id: str = "",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.run_id = run_id
        self.logger = logger

    def aplicar(self) -> None:
        self._limitar_screenshots()
        self._limitar_csv()
        self._limitar_trace()
        if self.run_id:
            limpar_execucoes_antigas(self.run_id, self.logger)

    def _limitar_screenshots(self) -> None:
        arquivos = sorted(
            SCREENSHOTS_DIR.glob("*.png"),
            key=lambda p: p.stat().st_mtime
        )
        excedente = len(arquivos) - config.MAX_SCREENSHOTS_ARMAZENADOS
        for arquivo in arquivos[:max(0, excedente)]:
            try:
                arquivo.unlink()
            except OSError:
                pass

    def _limitar_csv(self) -> None:
        caminho = LOGS_DIR / "processamento.csv"
        if not caminho.exists():
            return
        try:
            with open(caminho, "r", encoding="utf-8", newline="") as f:
                reader = list(csv.DictReader(f))
                cabecalho = reader[0].keys() if reader else []

            if len(reader) > config.MAX_REGISTROS_PROCESSAMENTO:
                registros = reader[-config.MAX_REGISTROS_PROCESSAMENTO:]
                with open(caminho, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(cabecalho))
                    writer.writeheader()
                    writer.writerows(registros)
        except Exception:
            pass

    def _limitar_trace(self) -> None:
        caminho = LOGS_DIR / "execution_trace.json"
        if not caminho.exists():
            return
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            etapas = dados.get("execucoes", [])
            if len(etapas) > config.MAX_REGISTROS_TRACE:
                dados["execucoes"] = etapas[-config.MAX_REGISTROS_TRACE:]
                caminho.write_text(
                    json.dumps(dados, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
        except Exception:
            pass
