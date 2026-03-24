from unittest.mock import MagicMock, patch

from src.auto_delete_clientes import ExecutorAutoDeleteClientes, ModoExecucaoAutoDelete, RegistroAutoDelete
from src.auto_delete_clientes.executor import NavegadorFechadoError


@patch("src.auto_delete_clientes.executor.LeitorExcelExclusao")
def test_executor_resolve_reprocessamento_pelo_excel_atual(mock_leitor_cls, tmp_path):
    arquivo = tmp_path / "auto_delete.xlsx"
    arquivo.write_text("ok", encoding="utf-8")

    registro_excel = MagicMock(
        nome_cliente="Cliente X",
        data_inicio="01/03/2026",
        data_fim="31/03/2026",
    )
    leitor = MagicMock()
    leitor.ler.return_value = [registro_excel]
    mock_leitor_cls.return_value = leitor

    executor = ExecutorAutoDeleteClientes(
        caminho_excel=arquivo,
        modo_execucao=ModoExecucaoAutoDelete.REPROCESSAMENTO_INDIVIDUAL,
        registro_individual=RegistroAutoDelete(
            linha_excel=4,
            nome_cliente="Cliente X",
            data_inicio="",
            data_fim="",
        ),
    )

    registros = executor._carregar_registros(MagicMock())

    assert len(registros) == 1
    assert registros[0].nome_cliente == "Cliente X"
    assert registros[0].data_inicio == "01/03/2026"
    assert registros[0].data_fim == "31/03/2026"


@patch("src.auto_delete_clientes.executor.configurar_logger")
def test_executor_finaliza_historico_quando_ocorre_erro_critico(mock_logger_factory, tmp_path):
    arquivo = tmp_path / "auto_delete.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    logger = MagicMock()
    mock_logger_factory.return_value = logger

    executor = ExecutorAutoDeleteClientes(caminho_excel=arquivo)
    executor._repositorio = MagicMock()
    executor._repositorio.gerar_run_id.return_value = "run_erro"
    executor._repositorio.caminho_log_execucao.return_value = tmp_path / "run_erro.log"

    with patch.object(
        executor,
        "_carregar_registros",
        side_effect=RuntimeError("falha de teste"),
    ):
        try:
            executor.executar()
        except RuntimeError as erro:
            assert str(erro) == "falha de teste"

    executor._repositorio.finalizar_execucao.assert_called_once()
    kwargs = executor._repositorio.finalizar_execucao.call_args.kwargs
    assert kwargs["status"] == "erro_critico"


@patch("src.auto_delete_clientes.executor.PaginaExclusao")
@patch("src.auto_delete_clientes.executor.PaginaLogin")
@patch("src.auto_delete_clientes.executor.AcoesNavegador")
@patch("src.auto_delete_clientes.executor.FabricaNavegador")
@patch("src.auto_delete_clientes.executor.configurar_logger")
def test_executor_execucao_completa_trata_nao_encontrado_como_ja_excluido(
    mock_logger_factory,
    mock_fabrica_navegador,
    _mock_acoes_cls,
    _mock_pagina_login_cls,
    mock_pagina_exclusao_cls,
    tmp_path,
):
    arquivo = tmp_path / "auto_delete.xlsx"
    arquivo.write_text("ok", encoding="utf-8")

    logger = MagicMock()
    mock_logger_factory.return_value = logger
    mock_fabrica_navegador.criar.return_value = MagicMock()

    pagina = MagicMock()
    pagina.excluir_registro.return_value = "nao_encontrado"
    mock_pagina_exclusao_cls.return_value = pagina

    observador = MagicMock()
    observador.validar_continuacao.return_value = True

    executor = ExecutorAutoDeleteClientes(
        caminho_excel=arquivo,
        observador=observador,
    )
    executor._repositorio = MagicMock()
    executor._repositorio.gerar_run_id.return_value = "run_nao_encontrado"
    executor._repositorio.caminho_log_execucao.return_value = tmp_path / "run_nao_encontrado.log"

    registro = RegistroAutoDelete(
        linha_excel=4,
        nome_cliente="Cliente X",
        data_inicio="01/03/2026",
        data_fim="31/03/2026",
    )

    with patch.object(executor, "_carregar_registros", return_value=[registro]):
        executor.executar()

    observador.registrar_sucesso.assert_called_once()
    observador.registrar_falha.assert_not_called()
    executor._repositorio.limpar_falhas_pendentes.assert_called_once()
    executor._repositorio.salvar_falhas_pendentes.assert_not_called()
    kwargs = executor._repositorio.finalizar_execucao.call_args.kwargs
    assert kwargs["total_registros"] == 1
    assert kwargs["sucessos"] == 1
    assert kwargs["falhas"] == 0


@patch("src.auto_delete_clientes.executor.PaginaExclusao")
@patch("src.auto_delete_clientes.executor.PaginaLogin")
@patch("src.auto_delete_clientes.executor.AcoesNavegador")
@patch("src.auto_delete_clientes.executor.FabricaNavegador")
@patch("src.auto_delete_clientes.executor.configurar_logger")
def test_executor_repete_ciclos_e_limpa_falha_recuperada(
    mock_logger_factory,
    mock_fabrica_navegador,
    _mock_acoes_cls,
    _mock_pagina_login_cls,
    mock_pagina_exclusao_cls,
    tmp_path,
):
    arquivo = tmp_path / "auto_delete.xlsx"
    arquivo.write_text("ok", encoding="utf-8")

    logger = MagicMock()
    mock_logger_factory.return_value = logger
    mock_fabrica_navegador.criar.return_value = MagicMock()

    pagina = MagicMock()
    pagina.excluir_registro.side_effect = ["erro_exclusao", "sucesso"]
    mock_pagina_exclusao_cls.return_value = pagina

    observador = MagicMock()
    observador.validar_continuacao.return_value = True

    executor = ExecutorAutoDeleteClientes(
        caminho_excel=arquivo,
        quantidade_ciclos=2,
        observador=observador,
    )
    executor._repositorio = MagicMock()
    executor._repositorio.gerar_run_id.return_value = "run_ciclos"
    executor._repositorio.caminho_log_execucao.return_value = tmp_path / "run_ciclos.log"

    registro = RegistroAutoDelete(
        linha_excel=4,
        nome_cliente="Cliente X",
        data_inicio="01/03/2026",
        data_fim="31/03/2026",
    )

    with patch.object(executor, "_carregar_registros", return_value=[registro]):
        executor.executar()

    observador.definir_total_fase_um.assert_called_once_with(2)
    assert pagina.excluir_registro.call_count == 2
    executor._repositorio.limpar_falhas_pendentes.assert_called_once()
    executor._repositorio.salvar_falhas_pendentes.assert_not_called()
    kwargs = executor._repositorio.finalizar_execucao.call_args.kwargs
    assert kwargs["total_registros"] == 2
    assert kwargs["sucessos"] == 1
    assert kwargs["falhas"] == 1


@patch("src.auto_delete_clientes.executor.PaginaExclusao")
@patch("src.auto_delete_clientes.executor.PaginaLogin")
@patch("src.auto_delete_clientes.executor.AcoesNavegador")
@patch("src.auto_delete_clientes.executor.FabricaNavegador")
@patch("src.auto_delete_clientes.executor.configurar_logger")
def test_executor_reprocessar_falhas_trata_nao_encontrado_como_resolvido(
    mock_logger_factory,
    mock_fabrica_navegador,
    _mock_acoes_cls,
    _mock_pagina_login_cls,
    mock_pagina_exclusao_cls,
    tmp_path,
):
    arquivo = tmp_path / "auto_delete.xlsx"
    arquivo.write_text("ok", encoding="utf-8")

    logger = MagicMock()
    mock_logger_factory.return_value = logger
    mock_fabrica_navegador.criar.return_value = MagicMock()

    pagina = MagicMock()
    pagina.excluir_registro.return_value = "nao_encontrado"
    mock_pagina_exclusao_cls.return_value = pagina

    observador = MagicMock()
    observador.validar_continuacao.return_value = True

    executor = ExecutorAutoDeleteClientes(
        caminho_excel=arquivo,
        modo_execucao=ModoExecucaoAutoDelete.REPROCESSAR_FALHAS,
        observador=observador,
    )
    executor._repositorio = MagicMock()
    executor._repositorio.gerar_run_id.return_value = "run_reprocessar_falhas"
    executor._repositorio.caminho_log_execucao.return_value = tmp_path / "run_reprocessar_falhas.log"

    registro = RegistroAutoDelete(
        linha_excel=4,
        nome_cliente="Cliente X",
        data_inicio="01/03/2026",
        data_fim="31/03/2026",
        motivo="Erro anterior",
        origem="reprocessamento",
    )
    executor._repositorio.carregar_falhas_pendentes.return_value = ({}, [registro])

    with patch.object(executor, "_resolver_registro_no_excel_atual", return_value=registro):
        executor.executar()

    observador.registrar_sucesso.assert_called_once()
    observador.registrar_falha.assert_not_called()
    executor._repositorio.limpar_falhas_pendentes.assert_called_once()
    executor._repositorio.salvar_falhas_pendentes.assert_not_called()
    kwargs = executor._repositorio.finalizar_execucao.call_args.kwargs
    assert kwargs["total_registros"] == 1
    assert kwargs["sucessos"] == 1
    assert kwargs["falhas"] == 0


@patch("src.auto_delete_clientes.executor.PaginaExclusao")
@patch("src.auto_delete_clientes.executor.PaginaLogin")
@patch("src.auto_delete_clientes.executor.AcoesNavegador")
@patch("src.auto_delete_clientes.executor.FabricaNavegador")
@patch("src.auto_delete_clientes.executor.configurar_logger")
def test_executor_ciclos_nao_reconta_como_falha_registro_ja_resolvido(
    mock_logger_factory,
    mock_fabrica_navegador,
    _mock_acoes_cls,
    _mock_pagina_login_cls,
    mock_pagina_exclusao_cls,
    tmp_path,
):
    arquivo = tmp_path / "auto_delete.xlsx"
    arquivo.write_text("ok", encoding="utf-8")

    logger = MagicMock()
    mock_logger_factory.return_value = logger
    mock_fabrica_navegador.criar.return_value = MagicMock()

    pagina = MagicMock()
    pagina.excluir_registro.side_effect = ["sucesso", "nao_encontrado"]
    mock_pagina_exclusao_cls.return_value = pagina

    observador = MagicMock()
    observador.validar_continuacao.return_value = True

    executor = ExecutorAutoDeleteClientes(
        caminho_excel=arquivo,
        quantidade_ciclos=2,
        observador=observador,
    )
    executor._repositorio = MagicMock()
    executor._repositorio.gerar_run_id.return_value = "run_ciclos_resolvidos"
    executor._repositorio.caminho_log_execucao.return_value = tmp_path / "run_ciclos_resolvidos.log"

    registro = RegistroAutoDelete(
        linha_excel=4,
        nome_cliente="Cliente X",
        data_inicio="01/03/2026",
        data_fim="31/03/2026",
    )

    with patch.object(executor, "_carregar_registros", return_value=[registro]):
        executor.executar()

    assert pagina.excluir_registro.call_count == 2
    executor._repositorio.limpar_falhas_pendentes.assert_called_once()
    executor._repositorio.salvar_falhas_pendentes.assert_not_called()
    kwargs = executor._repositorio.finalizar_execucao.call_args.kwargs
    assert kwargs["total_registros"] == 2
    assert kwargs["sucessos"] == 2
    assert kwargs["falhas"] == 0


@patch("src.auto_delete_clientes.executor.PaginaExclusao")
@patch("src.auto_delete_clientes.executor.PaginaLogin")
@patch("src.auto_delete_clientes.executor.AcoesNavegador")
@patch("src.auto_delete_clientes.executor.FabricaNavegador")
@patch("src.auto_delete_clientes.executor.configurar_logger")
def test_executor_interrompido_antes_do_fim_nao_grava_total_planejado_como_executado(
    mock_logger_factory,
    mock_fabrica_navegador,
    _mock_acoes_cls,
    _mock_pagina_login_cls,
    mock_pagina_exclusao_cls,
    tmp_path,
):
    arquivo = tmp_path / "auto_delete.xlsx"
    arquivo.write_text("ok", encoding="utf-8")

    logger = MagicMock()
    mock_logger_factory.return_value = logger
    mock_fabrica_navegador.criar.return_value = MagicMock()

    pagina = MagicMock()
    pagina.excluir_registro.side_effect = NavegadorFechadoError("navegador fechado")
    mock_pagina_exclusao_cls.return_value = pagina

    observador = MagicMock()
    observador.validar_continuacao.return_value = True

    executor = ExecutorAutoDeleteClientes(
        caminho_excel=arquivo,
        quantidade_ciclos=3,
        observador=observador,
    )
    executor._repositorio = MagicMock()
    executor._repositorio.gerar_run_id.return_value = "run_interrompido"
    executor._repositorio.caminho_log_execucao.return_value = tmp_path / "run_interrompido.log"

    registro = RegistroAutoDelete(
        linha_excel=4,
        nome_cliente="Cliente X",
        data_inicio="01/03/2026",
        data_fim="31/03/2026",
    )

    with patch.object(executor, "_carregar_registros", return_value=[registro]):
        executor.executar()

    kwargs = executor._repositorio.finalizar_execucao.call_args.kwargs
    assert kwargs["status"] == "navegador_fechado"
    assert kwargs["total_registros"] == 1
    assert kwargs["falhas"] == 1
