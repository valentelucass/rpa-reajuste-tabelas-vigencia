"""Persistencia de logs e falhas do modulo auto delete clientes."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from src.infraestrutura.caminhos import (
    AUTO_DELETE_DIR,
    AUTO_DELETE_EXECUCOES_DIR as EXECUCOES_DIR,
    AUTO_DELETE_FALHAS_PENDENTES_PATH as FALHAS_PENDENTES_PATH,
    AUTO_DELETE_HISTORICO_EXECUCOES_PATH as HISTORICO_EXECUCOES_PATH,
    AUTO_DELETE_REPROCESSAMENTO_XLSX_PATH as REPROCESSAMENTO_XLSX_PATH,
    AUTO_DELETE_SCREENSHOTS_DIR as SCREENSHOTS_DIR,
)

from .modelos import ModoExecucaoAutoDelete, OrdemExecucaoAutoDelete, RegistroAutoDelete


def garantir_estrutura_auto_delete() -> None:
    for diretorio in (AUTO_DELETE_DIR, EXECUCOES_DIR, SCREENSHOTS_DIR):
        diretorio.mkdir(parents=True, exist_ok=True)

    if not HISTORICO_EXECUCOES_PATH.exists():
        HISTORICO_EXECUCOES_PATH.write_text("[]", encoding="utf-8")


class RepositorioAutoDeleteClientes:
    """Isola a persistencia do modulo sem acoplar ao fluxo principal."""

    def __init__(self) -> None:
        garantir_estrutura_auto_delete()

    def gerar_run_id(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def caminho_log_execucao(self, run_id: str) -> Path:
        return EXECUCOES_DIR / f"auto_delete_clientes_{run_id}.log"

    def registrar_execucao(
        self,
        run_id: str,
        *,
        caminho_excel: Path | None,
        ordem: OrdemExecucaoAutoDelete,
        modo: ModoExecucaoAutoDelete,
        quantidade_ciclos: int,
        caminho_log: Path,
    ) -> None:
        historico = self._carregar_historico()
        historico.append(
            {
                "run_id": run_id,
                "timestamp_inicio": datetime.now().isoformat(timespec="seconds"),
                "timestamp_fim": "",
                "status": "em_andamento",
                "caminho_excel": str(caminho_excel) if caminho_excel else "",
                "ordem_execucao": ordem.value,
                "modo_execucao": modo.value,
                "quantidade_ciclos": quantidade_ciclos,
                "caminho_log": str(caminho_log),
                "total_registros": 0,
                "sucessos": 0,
                "falhas": 0,
            }
        )
        self._salvar_historico(historico)

    def finalizar_execucao(
        self,
        run_id: str,
        *,
        status: str,
        total_registros: int,
        sucessos: int,
        falhas: int,
    ) -> None:
        historico = self._carregar_historico()
        for execucao in historico:
            if execucao.get("run_id") != run_id:
                continue
            execucao["timestamp_fim"] = datetime.now().isoformat(timespec="seconds")
            execucao["status"] = status
            execucao["total_registros"] = total_registros
            execucao["sucessos"] = sucessos
            execucao["falhas"] = falhas
            break
        self._salvar_historico(historico)

    def salvar_falhas_pendentes(
        self,
        run_id: str,
        registros: list[RegistroAutoDelete],
        *,
        caminho_excel: Path | None,
        ordem: OrdemExecucaoAutoDelete,
        modo: ModoExecucaoAutoDelete,
        quantidade_ciclos: int,
    ) -> None:
        payload = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "caminho_excel": str(caminho_excel) if caminho_excel else "",
            "ordem_execucao": ordem.value,
            "modo_execucao": modo.value,
            "quantidade_ciclos": quantidade_ciclos,
            "total_falhas": len(registros),
            "registros": [registro.to_reprocessamento_dict() for registro in registros],
        }
        FALHAS_PENDENTES_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._salvar_planilha_reprocessamento(registros)

    def carregar_falhas_pendentes(self) -> tuple[dict, list[RegistroAutoDelete]]:
        if not FALHAS_PENDENTES_PATH.exists():
            return {}, []

        try:
            payload = json.loads(FALHAS_PENDENTES_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}, []

        registros = [
            RegistroAutoDelete.from_dict(item)
            for item in payload.get("registros", [])
            if isinstance(item, dict)
        ]
        return payload, registros

    def limpar_falhas_pendentes(self) -> None:
        payload = {
            "run_id": "",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "caminho_excel": "",
            "ordem_execucao": OrdemExecucaoAutoDelete.NORMAL.value,
            "modo_execucao": ModoExecucaoAutoDelete.EXECUCAO_COMPLETA.value,
            "quantidade_ciclos": 1,
            "total_falhas": 0,
            "registros": [],
        }
        FALHAS_PENDENTES_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._salvar_planilha_reprocessamento([])

    def _carregar_historico(self) -> list[dict]:
        try:
            return json.loads(HISTORICO_EXECUCOES_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _salvar_historico(self, historico: list[dict]) -> None:
        HISTORICO_EXECUCOES_PATH.write_text(
            json.dumps(historico, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _salvar_planilha_reprocessamento(
        self,
        registros: list[RegistroAutoDelete],
    ) -> None:
        if not registros:
            if REPROCESSAMENTO_XLSX_PATH.exists():
                REPROCESSAMENTO_XLSX_PATH.unlink()
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Reprocessar"
        ws.append(["LINHA EXCEL", "NOME DA TABELA", "MOTIVO"])
        for registro in registros:
            ws.append(
                [
                    registro.linha_excel,
                    registro.nome_cliente,
                    registro.motivo,
                ]
            )

        wb.save(str(REPROCESSAMENTO_XLSX_PATH))
        wb.close()
