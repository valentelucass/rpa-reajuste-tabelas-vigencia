from pathlib import Path
from unittest.mock import MagicMock

import pytest

import config
from src.aplicacao.automacao_tabela_cliente import AutomacaoTabelaCliente
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


def test_fase_dois_apenas_lanca_quando_nao_ha_itens_elegiveis(tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    observador = MagicMock()

    automacao = AutomacaoTabelaCliente(
        arquivo,
        observador=observador,
        modo=ModoExecucao.MODO_FASE2,
    )

    with pytest.raises(RuntimeError, match="Nenhum item elegivel para Fase 2"):
        automacao._executar_fase_dois_interna([], [])

    observador.definir_total_fase_dois.assert_called_once_with(0)
    observador.registrar_sistema.assert_called()


def test_fase_dois_em_modo_completo_tolera_sem_itens_elegiveis(tmp_path):
    arquivo = tmp_path / "ok.xlsx"
    arquivo.write_text("ok", encoding="utf-8")
    observador = MagicMock()

    automacao = AutomacaoTabelaCliente(
        arquivo,
        observador=observador,
        modo=ModoExecucao.MODO_COMPLETO,
    )

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
