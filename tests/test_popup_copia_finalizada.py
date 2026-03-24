"""
Testes do mecanismo de controle de popup assincrono (SweetAlert2).
Cobre: espera com progresso, timeout, validacao de titulo, interceptador tardio.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.paginas.pagina_tabelas_cliente import PaginaTabelasCliente


def _pagina():
    acoes = MagicMock()
    acoes.driver = MagicMock()
    logger = MagicMock()
    return PaginaTabelasCliente(acoes, logger), acoes, logger


def _criar_popup_visivel(texto: str) -> MagicMock:
    popup = MagicMock()
    popup.is_displayed.return_value = True
    popup.text = texto
    return popup


def _relogio(intervalo: float = 0.5):
    """Callable para side_effect de time.time() que avanca por intervalo."""
    estado = {"chamadas": 0}

    def tick():
        n = estado["chamadas"]
        estado["chamadas"] += 1
        # Primeira chamada (inicio) retorna 0
        if n == 0:
            return 0.0
        # Demais chamadas avancam de 2 em 2 calls (2 calls por iteracao do loop)
        iteracao = (n - 1) // 2
        return iteracao * intervalo

    return tick


# ---------------------------------------------------------------------------
# _aguardar_popup_swal_com_progresso — popup rapido (2s)
# ---------------------------------------------------------------------------


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
@patch("src.paginas.pagina_tabelas_cliente.time.time")
def test_popup_rapido_sem_log_progresso(mock_time, _sleep):
    """Popup encontrado na primeira verificacao — nenhum log de progresso."""
    pagina, acoes, logger = _pagina()

    mock_time.side_effect = _relogio(0.5)
    popup_mock = _criar_popup_visivel("Copia finalizada! Deseja editar a copia?")
    acoes.driver.find_elements.return_value = [popup_mock]

    resultado = pagina._aguardar_popup_swal_com_progresso(
        "copia finalizada", timeout=600, intervalo_log=30
    )

    assert resultado is popup_mock
    logs_progresso = [
        c for c in logger.info.call_args_list if "AGUARDANDO_POPUP" in str(c)
    ]
    assert len(logs_progresso) == 0


# ---------------------------------------------------------------------------
# _aguardar_popup_swal_com_progresso — popup em 2 minutos
# ---------------------------------------------------------------------------


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
@patch("src.paginas.pagina_tabelas_cliente.time.time")
def test_popup_em_dois_minutos_com_logs(mock_time, _sleep):
    """Popup aparece apos ~120s — deve emitir logs de progresso."""
    pagina, acoes, logger = _pagina()

    mock_time.side_effect = _relogio(0.5)
    popup_poll = 240  # 120s / 0.5s
    contador = {"n": 0}

    def find_elements_side_effect(*args, **kwargs):
        contador["n"] += 1
        if contador["n"] >= popup_poll:
            return [_criar_popup_visivel("Copia finalizada! Deseja editar a copia?")]
        return []

    acoes.driver.find_elements.side_effect = find_elements_side_effect

    resultado = pagina._aguardar_popup_swal_com_progresso(
        "copia finalizada", timeout=600, intervalo_log=30
    )

    assert resultado is not None
    logs_progresso = [
        c for c in logger.info.call_args_list if "AGUARDANDO_POPUP" in str(c)
    ]
    assert len(logs_progresso) >= 2  # ao menos 30s e 60s


# ---------------------------------------------------------------------------
# _aguardar_popup_swal_com_progresso — popup em 8 minutos
# ---------------------------------------------------------------------------


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
@patch("src.paginas.pagina_tabelas_cliente.time.time")
def test_popup_em_oito_minutos_com_logs(mock_time, _sleep):
    """Popup aparece apos ~480s — deve emitir muitos logs de progresso."""
    pagina, acoes, logger = _pagina()

    mock_time.side_effect = _relogio(0.5)
    popup_poll = 960  # 480s / 0.5s
    contador = {"n": 0}

    def find_elements_side_effect(*args, **kwargs):
        contador["n"] += 1
        if contador["n"] >= popup_poll:
            return [_criar_popup_visivel("Copia finalizada! Deseja editar a copia?")]
        return []

    acoes.driver.find_elements.side_effect = find_elements_side_effect

    resultado = pagina._aguardar_popup_swal_com_progresso(
        "copia finalizada", timeout=600, intervalo_log=30
    )

    assert resultado is not None
    logs_progresso = [
        c for c in logger.info.call_args_list if "AGUARDANDO_POPUP" in str(c)
    ]
    assert len(logs_progresso) >= 10


# ---------------------------------------------------------------------------
# _aguardar_popup_swal_com_progresso — timeout (popup NAO aparece)
# ---------------------------------------------------------------------------


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
@patch("src.paginas.pagina_tabelas_cliente.time.time")
def test_timeout_emite_critical_e_levanta(mock_time, _sleep):
    """Popup nao aparece — logger.critical + TimeoutError."""
    pagina, acoes, logger = _pagina()

    # Simula timeout rapido: cada poll avanca 5s, timeout eh 10s
    mock_time.side_effect = _relogio(5.0)
    acoes.driver.find_elements.return_value = []

    pagina._aguardar_popup_swal_com_progresso = (
        lambda *a, **kw: None  # simula retorno None (timeout)
    )

    with pytest.raises(TimeoutError, match="nao apareceu"):
        pagina.aguardar_modal_copia_finalizada()

    logger.critical.assert_called_once()
    assert "TIMEOUT_COPIA" in str(logger.critical.call_args)


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
@patch("src.paginas.pagina_tabelas_cliente.time.time")
def test_timeout_retorna_none(mock_time, _sleep):
    """Timeout curto — metodo de progresso retorna None."""
    pagina, acoes, logger = _pagina()

    # Cada poll avanca 3s, timeout = 5s → timeout na 2a iteracao
    mock_time.side_effect = _relogio(3.0)
    acoes.driver.find_elements.return_value = []

    resultado = pagina._aguardar_popup_swal_com_progresso(
        "copia finalizada", timeout=5, intervalo_log=2
    )

    assert resultado is None


# ---------------------------------------------------------------------------
# verificar_popup_swal_inesperado — interceptador tardio
# ---------------------------------------------------------------------------


def test_verificar_popup_inesperado_detecta_popup_presente():
    pagina, acoes, logger = _pagina()
    popup = _criar_popup_visivel("Copia finalizada")
    acoes.driver.find_elements.return_value = [popup]

    resultado = pagina.verificar_popup_swal_inesperado()

    assert resultado is popup
    logger.warning.assert_called_once()
    assert "POPUP_INESPERADO" in str(logger.warning.call_args)


def test_verificar_popup_inesperado_retorna_none_sem_popup():
    pagina, acoes, _logger = _pagina()
    acoes.driver.find_elements.return_value = []

    resultado = pagina.verificar_popup_swal_inesperado()

    assert resultado is None


def test_descartar_popup_inesperado_clica_confirmar_e_aguarda():
    pagina, acoes, logger = _pagina()
    popup = _criar_popup_visivel("Copia finalizada")
    botao = MagicMock()
    acoes.driver.find_elements.return_value = [popup]
    pagina._obter_botao_confirmar_popup = MagicMock(return_value=botao)
    pagina._aguardar_popup_desaparecer = MagicMock()

    resultado = pagina.descartar_popup_swal_inesperado()

    assert resultado is True
    acoes.clicar_com_seguranca.assert_called_once_with(botao)
    pagina._aguardar_popup_desaparecer.assert_called_once_with(timeout=5)


# ---------------------------------------------------------------------------
# _validar_titulo_popup_copia — validacao de titulo
# ---------------------------------------------------------------------------


def test_validar_titulo_emite_warning_quando_texto_diferente():
    pagina, _acoes, logger = _pagina()
    popup = MagicMock()
    popup.text = "Erro inesperado no servidor"

    pagina._validar_titulo_popup_copia(popup)

    logger.warning.assert_called_once()
    assert "POPUP_INESPERADO" in str(logger.warning.call_args)


def test_validar_titulo_nao_emite_warning_quando_correto():
    pagina, _acoes, logger = _pagina()
    popup = MagicMock()
    popup.text = "Copia finalizada! Deseja editar a copia?"

    pagina._validar_titulo_popup_copia(popup)

    logger.warning.assert_not_called()
