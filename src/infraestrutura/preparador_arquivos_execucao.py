"""
Prepara os diretórios e arquivos de artefatos necessários para a execução.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import config
from src.infraestrutura.caminhos import LOGS_DIR, REPORTS_DIR, SCREENSHOTS_DIR
from src.infraestrutura.registro_execucoes import registrar_execucao


CABECALHO_CSV = [
    "run_id",
    "fase",
    "tipo_execucao",
    "pagina",
    "linha",
    "nome_tabela",
    "status",
    "mensagem",
    "timestamp_inicio",
    "timestamp_fim",
    "duracao_ms",
    "tentativas",
    "erro_tipo",
    "reprocessado",
    "status_fase_1",
    "status_fase_2",
    "screenshot",
    "acao_recomendada",
    "etapa_falha",
]


class PreparadorArquivosExecucao:
    """Garante que todos os diretórios e arquivos base existam."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    def preparar(self) -> None:
        self._criar_diretorios()
        self._inicializar_csv()
        self._inicializar_trace()
        registrar_execucao(self.run_id)

    def _criar_diretorios(self) -> None:
        for diretorio in [LOGS_DIR, REPORTS_DIR, SCREENSHOTS_DIR]:
            diretorio.mkdir(parents=True, exist_ok=True)

    def _inicializar_csv(self) -> None:
        caminho = LOGS_DIR / "processamento.csv"
        if not caminho.exists():
            with open(caminho, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CABECALHO_CSV)
                writer.writeheader()

    def _inicializar_trace(self) -> None:
        caminho_trace = LOGS_DIR / "execution_trace.json"
        if not caminho_trace.exists():
            caminho_trace.write_text(
                json.dumps({"execucoes": []}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        caminho_step = LOGS_DIR / "current_step.json"
        caminho_step.write_text(
            json.dumps({
                "run_id": self.run_id,
                "etapa": "inicializando",
                "descricao": "Preparando execução",
                "status": "em_andamento",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
