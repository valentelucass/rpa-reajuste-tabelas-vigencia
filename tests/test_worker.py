from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication

from src.aplicacao.modo_execucao import ModoExecucao
from src.auto_delete_clientes import (
    ModoExecucaoAutoDelete,
    OrdemExecucaoAutoDelete,
    RegistroAutoDelete,
)
from src.ui.worker import TrabalhadorAutoDeleteClientes, TrabalhadorExecucaoRpa


def _app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@patch("src.aplicacao.automacao_tabela_cliente.AutomacaoTabelaCliente")
@patch("src.infraestrutura.fabrica_registrador_execucao.criar_logger")
@patch("src.ui.worker.GestorCheckpoint.carregar_ou_criar")
def test_trabalhador_execucao_reinicia_checkpoint_em_modo_completo(
    mock_carregar_checkpoint,
    _mock_criar_logger,
    mock_automacao_cls,
):
    checkpoint = MagicMock()
    mock_carregar_checkpoint.return_value = checkpoint
    mock_automacao = MagicMock()
    mock_automacao_cls.return_value = mock_automacao

    worker = TrabalhadorExecucaoRpa("teste.xlsx", modo=ModoExecucao.MODO_COMPLETO)
    worker.run()

    assert mock_carregar_checkpoint.call_args.kwargs["modo"] == ModoExecucao.MODO_COMPLETO
    mock_automacao_cls.assert_called_once()
    mock_automacao.executar.assert_called_once()


@patch("src.aplicacao.automacao_tabela_cliente.AutomacaoTabelaCliente")
@patch("src.infraestrutura.fabrica_registrador_execucao.criar_logger")
@patch("src.ui.worker.GestorCheckpoint.carregar_ou_criar")
def test_trabalhador_execucao_reinicia_checkpoint_em_modo_fase1(
    mock_carregar_checkpoint,
    _mock_criar_logger,
    mock_automacao_cls,
):
    checkpoint = MagicMock()
    mock_carregar_checkpoint.return_value = checkpoint
    mock_automacao = MagicMock()
    mock_automacao_cls.return_value = mock_automacao

    worker = TrabalhadorExecucaoRpa("teste.xlsx", modo=ModoExecucao.MODO_FASE1)
    worker.run()

    assert mock_carregar_checkpoint.call_args.kwargs["modo"] == ModoExecucao.MODO_FASE1
    mock_automacao_cls.assert_called_once()
    mock_automacao.executar.assert_called_once()


@patch("src.aplicacao.automacao_tabela_cliente.AutomacaoTabelaCliente")
@patch("src.infraestrutura.fabrica_registrador_execucao.criar_logger")
@patch("src.ui.worker.GestorCheckpoint.carregar_ou_criar")
def test_trabalhador_execucao_reutiliza_checkpoint_em_modo_fase2(
    mock_carregar_checkpoint,
    _mock_criar_logger,
    mock_automacao_cls,
):
    checkpoint = MagicMock()
    mock_carregar_checkpoint.return_value = checkpoint
    mock_automacao = MagicMock()
    mock_automacao_cls.return_value = mock_automacao

    worker = TrabalhadorExecucaoRpa("teste.xlsx", modo=ModoExecucao.MODO_FASE2)
    worker.run()

    assert "modo" not in mock_carregar_checkpoint.call_args.kwargs
    mock_automacao_cls.assert_called_once()
    mock_automacao.executar.assert_called_once()


def test_trabalhador_execucao_solicita_parada_em_automacao_ativa():
    worker = TrabalhadorExecucaoRpa("teste.xlsx", modo=ModoExecucao.MODO_FASE2)
    worker._automacao = MagicMock()

    worker.solicitar_parada()

    assert worker._parar is True
    worker._automacao.solicitar_parada_emergencial.assert_called_once()


@patch("src.aplicacao.automacao_tabela_cliente.AutomacaoTabelaCliente")
@patch("src.infraestrutura.fabrica_registrador_execucao.criar_logger")
@patch("src.ui.worker.GestorCheckpoint.carregar_ou_criar")
def test_trabalhador_execucao_emite_sinal_parado_quando_execucao_interrompida(
    mock_carregar_checkpoint,
    _mock_criar_logger,
    mock_automacao_cls,
):
    _app()
    mock_carregar_checkpoint.return_value = MagicMock()
    mock_automacao = MagicMock()
    mock_automacao.executar.side_effect = RuntimeError("driver encerrado")
    mock_automacao_cls.return_value = mock_automacao

    worker = TrabalhadorExecucaoRpa("teste.xlsx")
    worker._parar = True
    mensagens_parado: list[str] = []
    mensagens_erro: list[str] = []
    worker.sinal_parado.connect(mensagens_parado.append)
    worker.sinal_erro_critico.connect(mensagens_erro.append)

    worker.run()

    assert mensagens_parado == ["Execução interrompida pelo operador."]
    assert mensagens_erro == []


@patch("src.ui.worker.ExecutorAutoDeleteClientes")
def test_trabalhador_auto_delete_repassa_parametros_para_executor(mock_executor_cls):
    executor = MagicMock()
    mock_executor_cls.return_value = executor
    registro = RegistroAutoDelete(4, "Cliente X", "01/03/2026", "31/03/2026")

    worker = TrabalhadorAutoDeleteClientes(
        "clientes.xlsx",
        ordem_execucao=OrdemExecucaoAutoDelete.REVERSA,
        modo_execucao=ModoExecucaoAutoDelete.REPROCESSAMENTO_INDIVIDUAL,
        quantidade_ciclos=3,
        registro_individual=registro,
    )
    worker.run()

    mock_executor_cls.assert_called_once()
    kwargs = mock_executor_cls.call_args.kwargs
    assert kwargs["ordem_execucao"] == OrdemExecucaoAutoDelete.REVERSA
    assert kwargs["modo_execucao"] == ModoExecucaoAutoDelete.REPROCESSAMENTO_INDIVIDUAL
    assert kwargs["quantidade_ciclos"] == 3
    assert kwargs["registro_individual"] == registro
    executor.executar.assert_called_once()
