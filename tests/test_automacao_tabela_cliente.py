from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import config
from src.aplicacao.automacao_tabela_cliente import AutomacaoTabelaCliente
from src.aplicacao.fase_execucao import TipoExecucao
from src.aplicacao.modo_execucao import ModoExecucao


def test_validar_pre_requisitos_lanca_para_excel_inexistente(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LOGIN", "teste@empresa.com")
    monkeypatch.setattr(config, "SENHA_LOGIN", "123")
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")
    automacao = AutomacaoTabelaCliente("arquivo_que_nao_existe.xlsx")

    with pytest.raises(FileNotFoundError):
        automacao._validar_pre_requisitos()


def test_validar_pre_requisitos_lanca_para_email_ausente(monkeypatch, tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(config, "EMAIL_LOGIN", "")
    monkeypatch.setattr(config, "SENHA_LOGIN", "123")
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")
    automacao = AutomacaoTabelaCliente(arquivo)

    with pytest.raises(ValueError, match="EMAIL_LOGIN"):
        automacao._validar_pre_requisitos()


def test_validar_pre_requisitos_lanca_para_senha_ausente(monkeypatch, tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(config, "EMAIL_LOGIN", "teste@empresa.com")
    monkeypatch.setattr(config, "SENHA_LOGIN", "")
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")
    automacao = AutomacaoTabelaCliente(arquivo)

    with pytest.raises(ValueError, match="SENHA_LOGIN"):
        automacao._validar_pre_requisitos()


def test_validar_pre_requisitos_lanca_para_url_ausente(monkeypatch, tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(config, "EMAIL_LOGIN", "teste@empresa.com")
    monkeypatch.setattr(config, "SENHA_LOGIN", "123")
    monkeypatch.setattr(config, "URL_LOGIN", "")
    automacao = AutomacaoTabelaCliente(arquivo)

    with pytest.raises(ValueError, match="URL_LOGIN"):
        automacao._validar_pre_requisitos()


def test_validar_pre_requisitos_passa_quando_tudo_esta_preenchido(monkeypatch, tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(config, "EMAIL_LOGIN", "teste@empresa.com")
    monkeypatch.setattr(config, "SENHA_LOGIN", "123")
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")
    automacao = AutomacaoTabelaCliente(Path(arquivo))

    automacao._validar_pre_requisitos()


def test_fase_dois_apenas_conclui_com_alerta_quando_nao_ha_itens_para_validar(tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    observador = MagicMock()

    automacao = AutomacaoTabelaCliente(
        arquivo,
        observador=observador,
        modo=ModoExecucao.MODO_FASE2,
    )

    automacao._finalizar_relatorio_fase_dois = MagicMock(return_value={"validacao": {}})
    automacao._emitir_alerta_sem_elegiveis = MagicMock()

    relatorio = automacao._executar_fase_dois_interna([], [])

    observador.definir_total_fase_dois.assert_called_once_with(0)
    observador.registrar_sistema.assert_called()
    automacao._emitir_alerta_sem_elegiveis.assert_called_once()
    assert relatorio == {"validacao": {}}


def test_fase_dois_em_modo_completo_tolera_sem_itens_elegiveis(tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    observador = MagicMock()

    automacao = AutomacaoTabelaCliente(
        arquivo,
        observador=observador,
        modo=ModoExecucao.MODO_COMPLETO,
    )

    automacao._finalizar_relatorio_fase_dois = MagicMock(return_value={"validacao": {}})
    automacao._emitir_alerta_sem_elegiveis = MagicMock()

    automacao._executar_fase_dois_interna([], [])

    observador.definir_total_fase_dois.assert_called_once_with(0)
    observador.registrar_sistema.assert_called()


def test_solicitar_parada_emergencial_encerra_driver_e_mantem_fluxo(tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    observador = MagicMock()
    automacao = AutomacaoTabelaCliente(arquivo, observador=observador)
    automacao.logger = MagicMock()
    driver = MagicMock()
    automacao.driver = driver

    automacao.solicitar_parada_emergencial()

    assert automacao.driver is None
    driver.quit.assert_called_once()
    automacao.logger.warning.assert_called_once()
    observador.registrar_sistema.assert_called_once()


def test_fase_dois_salva_relatorio_parcial_quando_validacao_quebra(tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    observador = MagicMock()
    automacao = AutomacaoTabelaCliente(
        arquivo,
        observador=observador,
        modo=ModoExecucao.MODO_FASE2,
    )
    automacao.logger = MagicMock()
    automacao.rastreador = MagicMock()
    automacao.rastreador.etapa.side_effect = lambda *args, **kwargs: nullcontext()
    automacao.validador_f2 = MagicMock()
    automacao.validador_f2.validar_grupo.side_effect = RuntimeError("falha na validacao")
    automacao._consolidar_relatorio_fase_dois = MagicMock(return_value={"validacao": {}})
    automacao._salvar_relatorio_fase_dois = MagicMock(return_value=(Path("fase2.json"), Path("fase2.md")))
    automacao._artefatos_fase_dois = MagicMock(return_value={"relatorio_json": "fase2.json"})

    tabela = MagicMock()
    tabela.nome = "Tabela X"
    tabela.data_inicio = "01/04/2026"
    tabela.data_fim = "31/03/2027"
    tabela.percentual = 9.8

    with pytest.raises(RuntimeError, match="falha na validacao"):
        automacao._executar_fase_dois_interna([(1, tabela)], [])

    automacao._salvar_relatorio_fase_dois.assert_called_once()
    assert automacao._relatorio_fase_dois is not None
    assert automacao._relatorio_fase_dois["erro_critico"] == "falha na validacao"


def test_fase_dois_processa_grupo_completo_apos_pre_validacao_indicar_sinal_verde(tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    observador = MagicMock()
    automacao = AutomacaoTabelaCliente(
        arquivo,
        observador=observador,
        modo=ModoExecucao.MODO_FASE2,
    )
    automacao.rastreador = MagicMock()
    automacao.rastreador.etapa.side_effect = lambda *args, **kwargs: nullcontext()
    automacao._finalizar_relatorio_fase_dois = MagicMock(return_value={"validacao": {}})
    automacao._emitir_alerta_sem_elegiveis = MagicMock()

    tabela1 = MagicMock()
    tabela1.nome = "Tabela 1"
    tabela1.data_inicio = "01/04/2026"
    tabela1.data_fim = "31/03/2027"
    tabela1.percentual = 9.8

    tabela2 = MagicMock()
    tabela2.nome = "Tabela 2"
    tabela2.data_inicio = "01/04/2026"
    tabela2.data_fim = "31/03/2027"
    tabela2.percentual = 9.8

    tabela3 = MagicMock()
    tabela3.nome = "Tabela 3"
    tabela3.data_inicio = "01/04/2026"
    tabela3.data_fim = "31/03/2027"
    tabela3.percentual = 9.8

    pre_validacao = MagicMock()
    pre_validacao.filtro_vigencia = "01/04/2026 - 31/03/2027"
    pre_validacao.total_registros_filtrados = 7
    pre_validacao.total_validados = 5
    pre_validacao.total_divergentes = 1
    pre_validacao.total_nao_encontrados = 1
    pre_validacao.itens_elegiveis.return_value = [(2, tabela2)]
    pre_validacao.to_dict.return_value = {"total_elegiveis": 1, "total_validados": 5}
    automacao.validador_f2 = MagicMock()
    automacao.validador_f2.validar_grupo.return_value = pre_validacao

    relatorio_processamento = MagicMock()
    automacao.processador_f2 = MagicMock()
    automacao.processador_f2.processar.return_value = relatorio_processamento

    itens_grupo = [(1, tabela1), (2, tabela2), (3, tabela3)]

    automacao._executar_fase_dois_interna(itens_grupo, [])

    automacao.processador_f2.processar.assert_called_once()
    assert automacao.processador_f2.processar.call_args.args[0] == itens_grupo


def test_reprocessar_tabela_dispara_fase_dois_individual_em_modo_reprocessamento(
    tmp_path,
    monkeypatch,
):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    automacao = AutomacaoTabelaCliente(
        arquivo,
        observador=MagicMock(),
        modo=ModoExecucao.MODO_FASE2,
    )
    automacao.logger = MagicMock()
    automacao.checkpoint = MagicMock()
    monkeypatch.setattr(config, "recarregar_configuracoes", lambda sobrescrever_env=True: None)

    tabela1 = MagicMock()
    tabela1.nome = "Tabela 1"
    tabela1.data_inicio = "01/04/2026"
    tabela1.data_fim = "31/03/2027"
    tabela1.percentual = 9.8

    tabela2 = MagicMock()
    tabela2.nome = "Tabela 2"
    tabela2.data_inicio = "01/04/2026"
    tabela2.data_fim = "31/03/2027"
    tabela2.percentual = 9.8

    componentes = [MagicMock()]
    automacao._carregar_dados_excel = MagicMock(return_value=([tabela1, tabela2], componentes))
    automacao._executar_fase_dois_interna = MagicMock()

    automacao.reprocessar_tabela("Tabela 2")

    automacao.checkpoint.sincronizar_tabelas.assert_called_once_with([tabela1, tabela2])
    automacao._executar_fase_dois_interna.assert_called_once_with(
        [(2, tabela2)],
        componentes,
        tipo_execucao=TipoExecucao.REPROCESSAMENTO,
    )
