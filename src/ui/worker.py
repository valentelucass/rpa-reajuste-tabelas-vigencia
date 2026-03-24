"""
Thread de execucao do robo.
Implementa ContratoObservadorExecucao e emite sinais Qt para a UI.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from src.aplicacao.gestor_checkpoint import GestorCheckpoint
from src.aplicacao.modo_execucao import ModoExecucao
from src.auto_delete_clientes import (
    ExecutorAutoDeleteClientes,
    ModoExecucaoAutoDelete,
    OrdemExecucaoAutoDelete,
    RegistroAutoDelete,
)
from src.monitoramento.observador_execucao import ContextoTabelaProcessamento


class TrabalhadorExecucaoRpa(QThread):
    """
    Executa a automacao em thread separada e notifica a UI via sinais Qt.
    Implementa a interface de ContratoObservadorExecucao sem heranca multipla.
    """

    sinal_total_fase_um = Signal(int)
    sinal_total_fase_dois = Signal(int)
    sinal_processando = Signal(object)
    sinal_sucesso = Signal(object, str)
    sinal_falha = Signal(object, str)
    sinal_sistema = Signal(str)
    sinal_concluido = Signal()
    sinal_parado = Signal(str)
    sinal_erro_critico = Signal(str)

    def __init__(
        self,
        caminho_excel: str | Path,
        modo: ModoExecucao = ModoExecucao.MODO_COMPLETO,
    ) -> None:
        super().__init__()
        self.caminho_excel = Path(caminho_excel)
        self.modo = modo
        self._parar: bool = False
        self._automacao = None

    def run(self) -> None:
        from src.aplicacao.automacao_tabela_cliente import AutomacaoTabelaCliente
        from src.infraestrutura.fabrica_registrador_execucao import criar_logger

        try:
            logger = criar_logger("rpa")
            kwargs_checkpoint = {
                "logger": logger,
            }
            if self.modo in (ModoExecucao.MODO_COMPLETO, ModoExecucao.MODO_FASE1):
                kwargs_checkpoint["modo"] = self.modo
            checkpoint = GestorCheckpoint.carregar_ou_criar(
                self.caminho_excel,
                **kwargs_checkpoint,
            )
            self._automacao = AutomacaoTabelaCliente(
                caminho_excel=self.caminho_excel,
                observador=self,
                modo=self.modo,
                checkpoint=checkpoint,
            )
            if self._parar:
                self.sinal_parado.emit("Execução interrompida pelo operador.")
                return
            self._automacao.executar()
            if self._parar:
                self.sinal_parado.emit("Execução interrompida pelo operador.")
            else:
                self.sinal_concluido.emit()
        except Exception as erro:
            if self._parar:
                self.sinal_parado.emit("Execução interrompida pelo operador.")
            else:
                self.sinal_erro_critico.emit(str(erro))
        finally:
            self._automacao = None

    def definir_total_fase_um(self, total: int) -> None:
        self.sinal_total_fase_um.emit(total)

    def definir_total_fase_dois(self, total: int) -> None:
        self.sinal_total_fase_dois.emit(total)

    def registrar_processando(self, contexto: ContextoTabelaProcessamento) -> None:
        self.sinal_processando.emit(contexto)

    def registrar_sucesso(self, contexto: ContextoTabelaProcessamento, mensagem: str = "") -> None:
        self.sinal_sucesso.emit(contexto, mensagem)

    def registrar_falha(self, contexto: ContextoTabelaProcessamento, mensagem: str = "") -> None:
        self.sinal_falha.emit(contexto, mensagem)

    def registrar_sistema(self, mensagem: str) -> None:
        self.sinal_sistema.emit(mensagem)

    def validar_continuacao(self) -> bool:
        return not self._parar

    def solicitar_parada(self) -> None:
        self._parar = True
        if self._automacao is not None:
            try:
                self._automacao.solicitar_parada_emergencial()
            except Exception:
                pass


class TrabalhadorReprocessamento(QThread):
    """Reprocessa uma unica tabela em thread separada."""

    sinal_sucesso = Signal(str)
    sinal_erro = Signal(str, str)
    sinal_sistema = Signal(str)

    def __init__(
        self,
        caminho_excel: str | Path,
        nome_tabela: str,
        fase: int,
        indice: int,
    ) -> None:
        super().__init__()
        self.caminho_excel = Path(caminho_excel)
        self.nome_tabela = nome_tabela
        self.fase = fase
        self.indice = indice

    def run(self) -> None:
        from src.aplicacao.automacao_tabela_cliente import AutomacaoTabelaCliente
        from src.infraestrutura.fabrica_registrador_execucao import criar_logger

        try:
            criar_logger("rpa")
            self.sinal_sistema.emit(f"Reprocessando '{self.nome_tabela}'...")

            checkpoint = GestorCheckpoint.carregar_ou_criar(self.caminho_excel)
            automacao = AutomacaoTabelaCliente(
                caminho_excel=self.caminho_excel,
                checkpoint=checkpoint,
            )
            automacao.executar_reprocessamento(self.nome_tabela, self.fase)
            self.sinal_sucesso.emit(self.nome_tabela)
        except Exception as erro:
            self.sinal_erro.emit(self.nome_tabela, str(erro))


class TrabalhadorReprocessamentoFalhas(QThread):
    """Reprocessa automaticamente todas as falhas registradas no checkpoint."""

    sinal_concluido = Signal()
    sinal_erro = Signal(str)
    sinal_sistema = Signal(str)

    def __init__(self, caminho_excel: str | Path) -> None:
        super().__init__()
        self.caminho_excel = Path(caminho_excel)

    def run(self) -> None:
        from src.aplicacao.automacao_tabela_cliente import AutomacaoTabelaCliente

        try:
            self.sinal_sistema.emit("Reprocessando falhas registradas...")
            checkpoint = GestorCheckpoint.carregar_ou_criar(self.caminho_excel)
            automacao = AutomacaoTabelaCliente(
                caminho_excel=self.caminho_excel,
                checkpoint=checkpoint,
            )
            automacao.executar_reprocessamento_falhas()
            self.sinal_concluido.emit()
        except Exception as erro:
            self.sinal_erro.emit(str(erro))


class TrabalhadorAutoDeleteClientes(QThread):
    """Executa o modulo auto delete clientes em thread separada."""

    sinal_total_fase_um = Signal(int)
    sinal_total_fase_dois = Signal(int)
    sinal_processando = Signal(object)
    sinal_sucesso = Signal(object, str)
    sinal_falha = Signal(object, str)
    sinal_sistema = Signal(str)
    sinal_concluido = Signal()
    sinal_parado = Signal(str)
    sinal_erro_critico = Signal(str)

    def __init__(
        self,
        caminho_excel: str | Path | None,
        *,
        ordem_execucao: OrdemExecucaoAutoDelete,
        modo_execucao: ModoExecucaoAutoDelete,
        quantidade_ciclos: int = 1,
        registro_individual: Optional[RegistroAutoDelete] = None,
    ) -> None:
        super().__init__()
        self.caminho_excel = Path(caminho_excel) if caminho_excel else None
        self.ordem_execucao = ordem_execucao
        self.modo_execucao = modo_execucao
        self.quantidade_ciclos = max(int(quantidade_ciclos or 1), 1)
        self.registro_individual = registro_individual
        self._parar: bool = False
        self._executor: Optional[ExecutorAutoDeleteClientes] = None

    def run(self) -> None:
        try:
            self._executor = ExecutorAutoDeleteClientes(
                caminho_excel=self.caminho_excel,
                ordem_execucao=self.ordem_execucao,
                modo_execucao=self.modo_execucao,
                quantidade_ciclos=self.quantidade_ciclos,
                observador=self,
                registro_individual=self.registro_individual,
            )
            if self._parar:
                self.sinal_parado.emit("Execução interrompida pelo operador.")
                return
            self._executor.executar()
            if self._parar:
                self.sinal_parado.emit("Execução interrompida pelo operador.")
            else:
                self.sinal_concluido.emit()
        except Exception as erro:
            if self._parar:
                self.sinal_parado.emit("Execução interrompida pelo operador.")
            else:
                self.sinal_erro_critico.emit(str(erro))
        finally:
            self._executor = None

    def definir_total_fase_um(self, total: int) -> None:
        self.sinal_total_fase_um.emit(total)

    def definir_total_fase_dois(self, total: int) -> None:
        self.sinal_total_fase_dois.emit(total)

    def registrar_processando(self, contexto: ContextoTabelaProcessamento) -> None:
        self.sinal_processando.emit(contexto)

    def registrar_sucesso(self, contexto: ContextoTabelaProcessamento, mensagem: str = "") -> None:
        self.sinal_sucesso.emit(contexto, mensagem)

    def registrar_falha(self, contexto: ContextoTabelaProcessamento, mensagem: str = "") -> None:
        self.sinal_falha.emit(contexto, mensagem)

    def registrar_sistema(self, mensagem: str) -> None:
        self.sinal_sistema.emit(mensagem)

    def validar_continuacao(self) -> bool:
        return not self._parar

    def solicitar_parada(self) -> None:
        self._parar = True
        if self._executor is not None:
            try:
                self._executor.solicitar_parada()
            except Exception:
                pass
