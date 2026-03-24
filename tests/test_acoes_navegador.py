from unittest.mock import MagicMock, call, patch

import pytest

from src.infraestrutura.acoes_navegador import AcoesNavegador


def _acoes():
    with patch("src.infraestrutura.acoes_navegador.DebugVisual") as debug_cls:
        driver = MagicMock()
        logger = MagicMock()
        acoes = AcoesNavegador(driver, logger)
        debug_cls.assert_called_once_with(driver)
        return acoes, driver, logger


def test_buscar_todos_por_nome_seletor_deduplica_elementos(monkeypatch):
    acoes, driver, _logger = _acoes()
    e1 = MagicMock()
    e1.id = "1"
    e2 = MagicMock()
    e2.id = "2"
    e1_dup = MagicMock()
    e1_dup.id = "1"

    monkeypatch.setattr(
        "config.SELETORES",
        {"teste": [("css selector", ".a"), ("xpath", "//a")]},
        raising=False,
    )
    driver.find_elements.side_effect = [[e1, e2], [e1_dup]]

    elementos = acoes.buscar_todos_por_nome_seletor("teste")

    assert elementos == [e1, e2]


def test_obter_campo_busca_select2_aberto_retorna_campo_visivel():
    acoes, driver, _logger = _acoes()
    oculto = MagicMock()
    oculto.is_displayed.return_value = False
    visivel = MagicMock()
    visivel.is_displayed.return_value = True
    visivel.is_enabled.return_value = True
    driver.find_elements.side_effect = [[oculto, visivel]]

    campo = acoes._obter_campo_busca_select2_aberto(timeout=1)

    assert campo is visivel


@patch("src.infraestrutura.acoes_navegador.time.sleep")
@patch("src.infraestrutura.acoes_navegador.WebDriverWait")
def test_selecionar_select2_digita_no_campo_aberto_e_clica_na_opcao(wait_cls, _sleep):
    acoes, _driver, _logger = _acoes()
    container = MagicMock()
    campo_busca = MagicMock()
    opcao = MagicMock()
    acoes.aguardar_seletor = MagicMock(return_value=container)
    acoes._obter_campo_busca_select2_aberto = MagicMock(return_value=campo_busca)
    acoes.clicar_com_seguranca = MagicMock()
    wait_cls.return_value.until.return_value = opcao

    acoes.selecionar_select2("container_select2_ativa", "Sim")

    assert campo_busca.send_keys.call_args_list == [
        call("", "a"),
        call(""),
        call("Sim"),
    ]
    assert acoes.clicar_com_seguranca.call_args_list == [call(container), call(opcao)]


@patch("src.infraestrutura.acoes_navegador.time.sleep")
@patch("src.infraestrutura.acoes_navegador.WebDriverWait")
def test_selecionar_select2_levanta_quando_nao_encontra_opcao(wait_cls, _sleep):
    acoes, _driver, _logger = _acoes()
    container = MagicMock()
    acoes.aguardar_seletor = MagicMock(return_value=container)
    acoes._obter_campo_busca_select2_aberto = MagicMock(return_value=None)
    acoes.clicar_com_seguranca = MagicMock()
    wait_cls.return_value.until.side_effect = [RuntimeError("x"), RuntimeError("y")]

    with pytest.raises(RuntimeError, match="Opção 'Sim' não encontrada"):
        acoes.selecionar_select2("container_select2_ativa", "Sim")


@patch("src.infraestrutura.acoes_navegador.time.sleep")
@patch("src.infraestrutura.acoes_navegador.WebDriverWait")
def test_selecionar_select2_por_xpath_container_reutiliza_campo_aberto(wait_cls, _sleep):
    acoes, _driver, _logger = _acoes()
    container = MagicMock()
    campo_busca = MagicMock()
    opcao = MagicMock()
    acoes.aguardar_seletor_xpath = MagicMock(return_value=container)
    acoes._obter_campo_busca_select2_aberto = MagicMock(return_value=campo_busca)
    acoes.clicar_com_seguranca = MagicMock()
    wait_cls.return_value.until.return_value = opcao

    acoes.selecionar_select2_por_xpath_container("//div", "Taxa A")

    assert campo_busca.send_keys.call_args_list == [
        call("", "a"),
        call(""),
        call("Taxa A"),
    ]
    assert acoes.clicar_com_seguranca.call_args_list == [call(container), call(opcao)]
