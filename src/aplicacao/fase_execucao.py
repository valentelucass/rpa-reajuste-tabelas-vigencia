"""
Enums centrais para controle de execucao por fase.
"""

from enum import Enum


class FaseExecucao(str, Enum):
    FASE_1 = "fase_1"
    FASE_2 = "fase_2"

    @property
    def numero(self) -> int:
        return 1 if self is FaseExecucao.FASE_1 else 2

    @property
    def chave_checkpoint(self) -> str:
        return self.value

    @classmethod
    def from_valor(cls, valor: "FaseExecucao | int | str") -> "FaseExecucao":
        if isinstance(valor, cls):
            return valor
        if valor == 1 or valor == "1" or valor == "fase1" or valor == "fase_1":
            return cls.FASE_1
        if valor == 2 or valor == "2" or valor == "fase2" or valor == "fase_2":
            return cls.FASE_2
        raise ValueError(f"Fase invalida: {valor}")


class TipoExecucao(str, Enum):
    NORMAL = "normal"
    REPROCESSAMENTO = "reprocessamento"


class StatusExecucao(str, Enum):
    PENDENTE = "pendente"
    SUCESSO = "sucesso"
    ERRO = "erro"
