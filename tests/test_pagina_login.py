from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import TimeoutException

import config
from src.paginas.pagina_login import PaginaLogin


def _pagina_login():
    acoes = MagicMock()
    acoes.driver = MagicMock()
    logger = MagicMock()
    return PaginaLogin(acoes, logger), acoes, logger


def test_abrir_navega_para_url_e_aguarda_documento(monkeypatch):
    pagina, acoes, _logger = _pagina_login()
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")

    pagina.abrir()

    acoes.driver.get.assert_called_once_with("https://exemplo/login")
    acoes.aguardar_documento_pronto.assert_called_once()


def test_autenticar_preenche_campos_e_clica_entrar():
    pagina, acoes, _logger = _pagina_login()
    campo_email = MagicMock()
    campo_senha = MagicMock()
    botao = MagicMock()
    acoes.aguardar_seletor.side_effect = [campo_email, campo_senha, botao]

    with patch.object(pagina, "_aguardar_resultado_login") as aguardar, patch.object(
        pagina, "_verificar_login_sucedido"
    ) as verificar:
        pagina.autenticar()

    assert acoes.limpar_e_digitar.call_count == 2
    acoes.clicar_com_seguranca.assert_called_once_with(botao)
    aguardar.assert_called_once()
    verificar.assert_called_once()


def test_aguardar_resultado_login_tolera_timeout():
    pagina, acoes, _logger = _pagina_login()

    with patch("src.paginas.pagina_login.WebDriverWait") as wait_cls:
        wait_cls.return_value.until.side_effect = TimeoutException()
        pagina._aguardar_resultado_login()


def test_verificar_login_sucedido_lanca_erro_visivel(monkeypatch):
    pagina, acoes, _logger = _pagina_login()
    erro = MagicMock()
    erro.text = "Senha invalida"
    acoes.driver.find_elements.return_value = [erro]
    acoes.driver.current_url = "https://outra-url"
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")

    with pytest.raises(RuntimeError, match="Senha invalida"):
        pagina._verificar_login_sucedido()


def test_verificar_login_sucedido_lanca_quando_permanece_na_tela_login(monkeypatch):
    pagina, acoes, _logger = _pagina_login()
    acoes.driver.find_elements.return_value = []
    acoes.driver.current_url = "https://exemplo/login"
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")

    with pytest.raises(RuntimeError, match="permaneceu na tela de entrada"):
        pagina._verificar_login_sucedido()


def test_verificar_login_sucedido_registra_sucesso(monkeypatch):
    pagina, acoes, logger = _pagina_login()
    acoes.driver.find_elements.return_value = []
    acoes.driver.current_url = "https://exemplo/tms"
    monkeypatch.setattr(config, "URL_LOGIN", "https://exemplo/login")

    pagina._verificar_login_sucedido()

    logger.info.assert_called_once()
