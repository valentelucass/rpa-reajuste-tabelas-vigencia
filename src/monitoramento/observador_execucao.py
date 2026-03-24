"""
Contrato de observacao da execucao do robo.
Define como o robo reporta progresso sem conhecer a UI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from src.aplicacao.fase_execucao import FaseExecucao, StatusExecucao, TipoExecucao


@dataclass
class ContextoTabelaProcessamento:
    """Contexto de uma tabela sendo processada."""

    fase: int
    indice: int
    nome_tabela: str
    total: int = 0
    dados_extras: dict = field(default_factory=dict)
    fase_execucao: Optional[FaseExecucao] = None
    tipo_execucao: TipoExecucao = TipoExecucao.NORMAL
    pagina: int = 1
    tentativas: int = 1
    reprocessado: bool = False
    status_fase_1: str = StatusExecucao.PENDENTE.value
    status_fase_2: str = StatusExecucao.PENDENTE.value

    def __post_init__(self) -> None:
        if self.fase_execucao is None and self.fase in {1, 2}:
            self.fase_execucao = FaseExecucao.from_valor(self.fase)
        self.reprocessado = self.reprocessado or (
            self.tipo_execucao == TipoExecucao.REPROCESSAMENTO
        )

    @property
    def identificador(self) -> str:
        return f"Fase {self.fase} | #{self.indice} | {self.nome_tabela}"


class ContratoObservadorExecucao(ABC):
    """
    Contrato que desacopla o robo da interface.
    A thread Qt e apenas uma implementacao concreta deste contrato.
    """

    @abstractmethod
    def definir_total_fase_um(self, total: int) -> None:
        """Informa o total de tabelas a processar na Fase 1."""

    @abstractmethod
    def definir_total_fase_dois(self, total: int) -> None:
        """Informa o total de tabelas a processar na Fase 2."""

    @abstractmethod
    def registrar_processando(self, contexto: ContextoTabelaProcessamento) -> None:
        """Notifica que uma tabela esta sendo processada."""

    @abstractmethod
    def registrar_sucesso(
        self,
        contexto: ContextoTabelaProcessamento,
        mensagem: str = "",
    ) -> None:
        """Notifica que uma tabela foi processada com sucesso."""

    @abstractmethod
    def registrar_falha(
        self,
        contexto: ContextoTabelaProcessamento,
        mensagem: str = "",
    ) -> None:
        """Notifica que uma tabela falhou."""

    @abstractmethod
    def registrar_sistema(self, mensagem: str) -> None:
        """Envia uma mensagem de sistema para o observador."""

    @abstractmethod
    def validar_continuacao(self) -> bool:
        """Retorna False se a execucao deve ser interrompida."""

    @abstractmethod
    def solicitar_parada(self) -> None:
        """Solicita parada controlada da execucao."""


class ObservadorNulo(ContratoObservadorExecucao):
    """Implementacao nula do observador."""

    def definir_total_fase_um(self, total: int) -> None:
        pass

    def definir_total_fase_dois(self, total: int) -> None:
        pass

    def registrar_processando(self, contexto: ContextoTabelaProcessamento) -> None:
        pass

    def registrar_sucesso(
        self,
        contexto: ContextoTabelaProcessamento,
        mensagem: str = "",
    ) -> None:
        pass

    def registrar_falha(
        self,
        contexto: ContextoTabelaProcessamento,
        mensagem: str = "",
    ) -> None:
        pass

    def registrar_sistema(self, mensagem: str) -> None:
        pass

    def validar_continuacao(self) -> bool:
        return True

    def solicitar_parada(self) -> None:
        pass
