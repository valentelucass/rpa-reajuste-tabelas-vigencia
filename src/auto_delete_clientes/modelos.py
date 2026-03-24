"""Modelos e enums do modulo auto delete clientes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrdemExecucaoAutoDelete(str, Enum):
    NORMAL = "normal"
    REVERSA = "reversa"

    @property
    def descricao(self) -> str:
        if self is OrdemExecucaoAutoDelete.REVERSA:
            return "de baixo para cima"
        return "de cima para baixo"

    def aplicar(self, registros: list["RegistroAutoDelete"]) -> list["RegistroAutoDelete"]:
        if self is OrdemExecucaoAutoDelete.REVERSA:
            return list(reversed(registros))
        return list(registros)


class ModoExecucaoAutoDelete(str, Enum):
    EXECUCAO_COMPLETA = "execucao_completa"
    REPROCESSAR_FALHAS = "reprocessar_falhas"
    REPROCESSAR_TUDO = "reprocessar_tudo"
    REPROCESSAMENTO_INDIVIDUAL = "reprocessamento_individual"

    @property
    def eh_reprocessamento(self) -> bool:
        return self is not ModoExecucaoAutoDelete.EXECUCAO_COMPLETA


@dataclass(frozen=True)
class RegistroAutoDelete:
    linha_excel: int
    nome_cliente: str
    data_inicio: str
    data_fim: str
    motivo: str = ""
    origem: str = "excel"

    @property
    def data_vigencia(self) -> str:
        if self.data_inicio and self.data_fim:
            return f"{self.data_inicio} - {self.data_fim}"
        return self.data_inicio or self.data_fim or ""

    def to_dict(self) -> dict[str, str | int]:
        return {
            "linha_excel": self.linha_excel,
            "nome_cliente": self.nome_cliente,
            "data_inicio": self.data_inicio,
            "data_fim": self.data_fim,
            "motivo": self.motivo,
            "origem": self.origem,
        }

    def to_reprocessamento_dict(self) -> dict[str, str | int]:
        return {
            "linha_excel": self.linha_excel,
            "nome_cliente": self.nome_cliente,
            "motivo": self.motivo,
            "origem": self.origem,
        }

    @classmethod
    def from_dict(cls, dados: dict) -> "RegistroAutoDelete":
        return cls(
            linha_excel=int(dados.get("linha_excel") or 0),
            nome_cliente=str(dados.get("nome_cliente") or "").strip(),
            data_inicio=str(dados.get("data_inicio") or "").strip(),
            data_fim=str(dados.get("data_fim") or "").strip(),
            motivo=str(dados.get("motivo") or "").strip(),
            origem=str(dados.get("origem") or "excel").strip() or "excel",
        )
