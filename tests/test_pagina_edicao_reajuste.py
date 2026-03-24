from unittest.mock import MagicMock, patch

import pytest
from src.paginas.pagina_edicao_tabela import PaginaEdicaoTabela
from src.paginas.pagina_reajuste import PaginaReajuste


def _pagina_edicao():
    acoes = MagicMock()
    acoes.driver = MagicMock()
    logger = MagicMock()
    return PaginaEdicaoTabela(acoes, logger), acoes, logger


def _pagina_reajuste():
    acoes = MagicMock()
    acoes.driver = MagicMock()
    logger = MagicMock()
    return PaginaReajuste(acoes, logger), acoes, logger


def test_aguardar_tela_edicao_usa_campos_corretos():
    pagina, acoes, logger = _pagina_edicao()

    pagina.aguardar_tela_edicao()

    acoes.aguardar_seletor.assert_called_once_with("input_nome_tabela", "visivel", timeout=60)
    acoes.aguardar_carregamento_finalizar.assert_called_once()
    logger.info.assert_called_once()


@patch("src.paginas.pagina_edicao_tabela.time.sleep")
@patch("src.paginas.pagina_edicao_tabela.WebDriverWait")
def test_expandir_parametrizacoes_clica_quando_colapsado(_wait_cls, _sleep):
    pagina, acoes, _logger = _pagina_edicao()
    accordion = MagicMock()
    accordion.get_attribute.side_effect = ["false", "collapsed"]
    acoes.aguardar_seletor.return_value = accordion

    pagina.expandir_parametrizacoes()

    acoes.clicar_com_seguranca.assert_called_once_with(accordion)


@patch("src.paginas.pagina_edicao_tabela.time.sleep")
@patch("src.paginas.pagina_edicao_tabela.WebDriverWait")
def test_expandir_parametrizacoes_nao_clica_quando_ja_expandido(_wait_cls, _sleep):
    pagina, acoes, _logger = _pagina_edicao()
    accordion = MagicMock()
    accordion.get_attribute.side_effect = ["true", ""]
    acoes.aguardar_seletor.return_value = accordion

    pagina.expandir_parametrizacoes()

    acoes.clicar_com_seguranca.assert_not_called()


@patch("src.paginas.pagina_edicao_tabela.time.sleep")
def test_definir_datas_preenche_campos_corretos(_sleep):
    pagina, acoes, _logger = _pagina_edicao()
    campo_inicio = MagicMock()
    campo_fim = MagicMock()
    acoes.aguardar_seletor.side_effect = [campo_inicio, campo_fim]

    pagina.definir_data_inicio("01/04/2026")
    pagina.definir_data_fim("31/03/2027")

    assert acoes.limpar_e_digitar.call_args_list == [
        ((campo_inicio, "01/04/2026"),),
        ((campo_fim, "31/03/2027"),),
    ]


@patch("src.paginas.pagina_edicao_tabela.time.sleep")
def test_salvar_prioriza_link_salvar_visivel(_sleep):
    pagina, acoes, _logger = _pagina_edicao()
    botao = MagicMock()
    acoes.aguardar_seletor_xpath.return_value = botao

    pagina.salvar()

    xpath = acoes.aguardar_seletor_xpath.call_args.args[0]
    assert "normalize-space(text())='Salvar'" in xpath
    acoes.clicar_com_seguranca.assert_called_once_with(botao)


@patch("src.paginas.pagina_edicao_tabela.time.sleep")
def test_salvar_faz_fallback_para_seletor_nomeado(_sleep):
    pagina, acoes, _logger = _pagina_edicao()
    botao = MagicMock()
    acoes.aguardar_seletor_xpath.side_effect = RuntimeError("falha")
    acoes.aguardar_seletor.return_value = botao

    pagina.salvar()

    acoes.aguardar_seletor.assert_called_once_with("botao_salvar_edicao", "clicavel")
    acoes.clicar_com_seguranca.assert_called_once_with(botao)


def test_confirmar_modal_swal_aguarda_popup_sumir():
    pagina, acoes, logger = _pagina_edicao()
    botao = MagicMock()
    acoes.aguardar_seletor.return_value = botao

    pagina.confirmar_modal_swal()

    acoes.clicar_com_seguranca.assert_called_once_with(botao)
    acoes.aguardar_invisibilidade_css.assert_called_once_with(
        "div.swal2-popup.swal2-modal.swal2-show",
        timeout=5,
    )
    logger.debug.assert_called_once()


@patch("src.paginas.pagina_reajuste.time.sleep")
def test_definir_valor_formata_percentual_com_virgula(_sleep):
    pagina, acoes, _logger = _pagina_reajuste()
    campo = MagicMock()
    pagina._obter_campo_valor_visivel = MagicMock(return_value=campo)

    pagina.definir_valor(9.8)

    acoes.limpar_e_digitar.assert_called_once_with(campo, "9,8")


def test_navegar_para_aba_nao_faz_nada_quando_ja_esta_na_aba():
    pagina, acoes, _logger = _pagina_reajuste()
    pagina._aba_atual = "overweights"

    pagina.navegar_para_aba("overweights")

    acoes.clicar_com_seguranca.assert_not_called()


@patch("src.paginas.pagina_reajuste.time.sleep")
@patch("src.paginas.pagina_reajuste.WebDriverWait")
def test_navegar_para_aba_clica_quando_aba_nao_esta_ativa(_wait_cls, _sleep):
    pagina, acoes, _logger = _pagina_reajuste()
    aba = MagicMock()
    botao_aba = MagicMock()
    aba.get_attribute.return_value = ""
    pagina._obter_aba_visivel = MagicMock(return_value=(aba, botao_aba))
    pagina._aba_esta_ativa = MagicMock(return_value=True)

    pagina.navegar_para_aba("overweights")

    acoes.clicar_com_seguranca.assert_called_once_with(botao_aba)
    assert pagina._aba_atual == "overweights"


@patch("src.paginas.pagina_reajuste.time.sleep")
@patch("src.paginas.pagina_reajuste.WebDriverWait")
def test_navegar_para_aba_forca_clique_mesmo_quando_ja_esta_na_aba(_wait_cls, _sleep):
    pagina, acoes, _logger = _pagina_reajuste()
    pagina._aba_atual = "fee"
    aba = MagicMock()
    botao_aba = MagicMock()
    aba.get_attribute.return_value = "active"
    pagina._obter_aba_visivel = MagicMock(return_value=(aba, botao_aba))
    pagina._aba_esta_ativa = MagicMock(return_value=True)

    pagina.navegar_para_aba("fee", forcar_clique=True)

    acoes.clicar_com_seguranca.assert_called_once_with(botao_aba)
    assert pagina._aba_atual == "fee"


@patch("src.paginas.pagina_reajuste.time.sleep")
@patch("src.paginas.pagina_reajuste.WebDriverWait")
def test_navegar_para_aba_fee_nao_clica_novamente_sem_flag(_wait_cls, _sleep):
    pagina, acoes, _logger = _pagina_reajuste()
    pagina._aba_atual = "fee"

    pagina.navegar_para_aba("fee")

    acoes.clicar_com_seguranca.assert_not_called()
    assert pagina._aba_atual == "fee"


def test_considerar_todos_trechos_tolera_ausencia_do_botao():
    pagina, acoes, logger = _pagina_reajuste()
    acoes.aguardar_seletor_xpath.side_effect = RuntimeError("nao achou")

    pagina.considerar_todos_trechos()

    logger.warning.assert_called_once()


def test_confirmar_modal_ok_clica_e_aguarda_sumir():
    pagina, acoes, logger = _pagina_reajuste()
    popup = MagicMock()
    pagina._aguardar_popup_confirmacao = MagicMock(side_effect=[popup, None])
    pagina._descrever_popup_confirmacao = MagicMock(return_value="ok_sucesso")
    pagina._clicar_confirmacao_popup = MagicMock()
    pagina._aguardar_popup_sumir = MagicMock()

    pagina.confirmar_modal_ok()

    pagina._clicar_confirmacao_popup.assert_called_once_with(popup)
    pagina._aguardar_popup_sumir.assert_called_once_with(popup, timeout=10)
    logger.debug.assert_called_once()


def test_confirmar_modal_ok_confirma_sim_e_ok_em_sequencia():
    pagina, acoes, _logger = _pagina_reajuste()
    popup_sim = MagicMock()
    popup_ok = MagicMock()
    pagina._aguardar_popup_confirmacao = MagicMock(side_effect=[popup_sim, popup_ok, None])
    pagina._descrever_popup_confirmacao = MagicMock(
        side_effect=["sim_confirmacao", "ok_sucesso"]
    )
    pagina._clicar_confirmacao_popup = MagicMock()
    pagina._aguardar_popup_sumir = MagicMock()

    pagina.confirmar_modal_ok()

    assert pagina._clicar_confirmacao_popup.call_args_list == [((popup_sim,),), ((popup_ok,),)]


def test_confirmar_modal_ok_lanca_erro_quando_nao_encontra():
    pagina, acoes, _logger = _pagina_reajuste()
    pagina._aguardar_popup_confirmacao = MagicMock(side_effect=RuntimeError("sem swal"))

    with pytest.raises(RuntimeError, match="Nao foi possivel confirmar o popup"):
        pagina.confirmar_modal_ok()


def test_fechar_modal_prioriza_botao_x():
    pagina, acoes, logger = _pagina_reajuste()
    botao_x = MagicMock()
    botao_x.is_displayed.return_value = True
    botao_secundario = MagicMock()
    botao_secundario.is_displayed.return_value = False
    acoes.driver.find_elements.side_effect = [[botao_x], [botao_x], [botao_secundario], [], []]
    pagina.aguardar_modal_fechado = MagicMock()

    pagina.fechar_modal()

    acoes.clicar_com_seguranca.assert_called_once_with(botao_x)
    pagina.aguardar_modal_fechado.assert_called_once()
    logger.debug.assert_called_once()
    assert pagina._aba_atual is None


def test_fechar_modal_lanca_quando_nao_acha_botoes():
    pagina, acoes, _logger = _pagina_reajuste()
    acoes.driver.find_elements.side_effect = RuntimeError("nao achou")

    with pytest.raises(RuntimeError, match="Nao foi possivel fechar o modal"):
        pagina.fechar_modal()


@patch("src.paginas.pagina_reajuste.time.sleep")
@patch("src.paginas.pagina_reajuste.WebDriverWait")
def test_selecionar_taxa_usa_select2_visivel(wait_cls, _sleep):
    pagina, acoes, logger = _pagina_reajuste()
    container = MagicMock()
    campo_busca = MagicMock()
    opcao = MagicMock()
    acoes.aguardar_seletor_xpath.return_value = container
    acoes._obter_campo_busca_select2_aberto.return_value = campo_busca
    acoes.clicar_com_seguranca = MagicMock()
    wait_cls.return_value.until.side_effect = [opcao, True]

    pagina.selecionar_taxa("Taxa A")

    campo_busca.send_keys.assert_called_once_with("Taxa A")
    assert acoes.clicar_com_seguranca.call_args_list[0].args[0] is container
    assert acoes.clicar_com_seguranca.call_args_list[1].args[0] is opcao
    logger.debug.assert_called()
