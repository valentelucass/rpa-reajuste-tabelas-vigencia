from unittest.mock import MagicMock, patch

import pytest
import config
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.paginas.pagina_tabelas_cliente import PaginaTabelasCliente


def _pagina():
    acoes = MagicMock()
    acoes.driver = MagicMock()
    logger = MagicMock()
    return PaginaTabelasCliente(acoes, logger), acoes, logger


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_acessar_prefere_url_direta(_sleep):
    pagina, acoes, _logger = _pagina()
    pagina.acessar_por_url = MagicMock()

    pagina.acessar()

    pagina.acessar_por_url.assert_called_once()
    acoes.aguardar_seletor.assert_not_called()


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_acessar_faz_fallback_para_menu(_sleep):
    pagina, acoes, _logger = _pagina()
    pagina.acessar_por_url = MagicMock(side_effect=RuntimeError("falha"))
    menu = MagicMock()
    submenu = MagicMock()
    item = MagicMock()
    acoes.aguardar_seletor.side_effect = [menu, submenu, item]

    pagina.acessar()

    assert acoes.clicar_com_seguranca.call_count == 3
    acoes.aguardar_documento_pronto.assert_called_once()
    acoes.aguardar_carregamento_finalizar.assert_called_once()


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_limpar_filtro_filial_remove_apenas_botoes_visiveis(_sleep):
    pagina, acoes, _logger = _pagina()
    select = MagicMock()
    grupo = MagicMock()
    botao_visivel = MagicMock()
    botao_visivel.is_displayed.return_value = True
    botao_oculto = MagicMock()
    botao_oculto.is_displayed.return_value = False
    acoes.driver.find_element.return_value = select
    select.find_element.return_value = grupo
    grupo.find_elements.return_value = [botao_visivel, botao_oculto]

    pagina._limpar_filtro_filial()

    acoes.clicar_com_seguranca.assert_called_once_with(botao_visivel)


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_pesquisar_por_nome_preenche_e_dispara_pesquisa(_sleep):
    pagina, acoes, _logger = _pagina()
    input_nome = MagicMock()
    acoes.aguardar_seletor.return_value = input_nome
    pagina._clicar_botao_pesquisar = MagicMock()
    pagina._garantir_nome_digitado = MagicMock()

    pagina.pesquisar_por_nome("FRANCHINI")

    acoes.limpar_e_digitar.assert_called_once_with(input_nome, "FRANCHINI")
    pagina._garantir_nome_digitado.assert_called_once_with(input_nome, "FRANCHINI")
    pagina._clicar_botao_pesquisar.assert_called_once_with(input_nome)
    acoes.aguardar_carregamento_finalizar.assert_called_once()


def test_limpar_pesquisa_nome_limpa_sem_clicar_no_input():
    pagina, acoes, _logger = _pagina()
    input_nome = MagicMock()
    input_nome.get_attribute.return_value = "FRANCHINI"
    acoes.aguardar_seletor.return_value = input_nome

    pagina.limpar_pesquisa_nome()

    acoes.executar_script.assert_called_once()
    acoes.limpar_e_digitar.assert_not_called()


def test_limpar_pesquisa_nome_nao_faz_nada_quando_ja_vazio():
    pagina, acoes, _logger = _pagina()
    input_nome = MagicMock()
    input_nome.get_attribute.return_value = ""
    acoes.aguardar_seletor.return_value = input_nome

    pagina.limpar_pesquisa_nome()

    acoes.executar_script.assert_not_called()
    acoes.limpar_e_digitar.assert_not_called()


def test_clicar_botao_pesquisar_usa_seletor_principal():
    pagina, acoes, _logger = _pagina()
    input_nome = MagicMock()
    botao = MagicMock()
    acoes.aguardar_seletor.return_value = botao

    pagina._clicar_botao_pesquisar(input_nome)

    acoes.clicar_com_seguranca.assert_called_once_with(botao)
    input_nome.send_keys.assert_not_called()


def test_clicar_botao_pesquisar_faz_fallback_para_formulario():
    pagina, acoes, _logger = _pagina()
    input_nome = MagicMock()
    formulario = MagicMock()
    botao = MagicMock()
    acoes.aguardar_seletor.side_effect = RuntimeError("falha")
    input_nome.find_element.return_value = formulario
    formulario.find_element.return_value = botao

    pagina._clicar_botao_pesquisar(input_nome)

    acoes.clicar_com_seguranca.assert_called_once_with(botao)


def test_clicar_botao_pesquisar_faz_fallback_para_enter():
    pagina, acoes, _logger = _pagina()
    input_nome = MagicMock()
    acoes.aguardar_seletor.side_effect = RuntimeError("falha")
    input_nome.find_element.side_effect = RuntimeError("falha")

    pagina._clicar_botao_pesquisar(input_nome)

    input_nome.send_keys.assert_called_once_with(Keys.ENTER)


def test_preparar_estado_listagem_fase_dois_reaplica_baseline():
    pagina, _acoes, _logger = _pagina()
    pagina.acessar = MagicMock()
    pagina._limpar_filtro_filial = MagicMock()
    pagina._filtrar_ativa_sim = MagicMock()
    pagina.preparar_filtros_fase_dois = MagicMock()

    pagina.preparar_estado_listagem_fase_dois("01/04/2026", "31/03/2027")

    pagina.acessar.assert_called_once()
    pagina._limpar_filtro_filial.assert_called_once()
    pagina._filtrar_ativa_sim.assert_called_once()
    pagina.preparar_filtros_fase_dois.assert_called_once_with("01/04/2026", "31/03/2027")


def test_validar_filtro_vigencia_aplicado_compara_valor_normalizado():
    pagina, _acoes, _logger = _pagina()
    pagina.obter_valor_filtro_vigencia = MagicMock(return_value="01/04/2026 - 31/03/2027")

    assert pagina.validar_filtro_vigencia_aplicado("01/04/2026", "31/03/2027") is True
    assert pagina.validar_filtro_vigencia_aplicado("02/04/2026", "31/03/2027") is False


def test_intervalo_vigencia_corresponde_aceita_ano_curto():
    pagina, _acoes, _logger = _pagina()

    assert pagina.intervalo_vigencia_corresponde(
        "01/04/26 - 31/03/27",
        "01/04/2026",
        "31/03/2027",
    ) is True


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_obter_linhas_tabela_filtra_apenas_visiveis(_sleep):
    pagina, acoes, _logger = _pagina()
    visivel = MagicMock()
    visivel.is_displayed.return_value = True
    oculta = MagicMock()
    oculta.is_displayed.return_value = False
    acoes.driver.find_elements.return_value = [visivel, oculta]

    linhas = pagina.obter_linhas_tabela()

    assert linhas == [visivel]


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_preparar_filtros_fase_dois_lanca_quando_filtro_nao_fica_aplicado(_sleep):
    pagina, acoes, _logger = _pagina()
    input_nome = MagicMock()
    acoes.aguardar_seletor.return_value = input_nome
    pagina._expandir_filtros_avancados = MagicMock()
    pagina._preencher_daterangepicker = MagicMock()
    pagina._clicar_botao_pesquisar = MagicMock()
    pagina.validar_filtro_vigencia_aplicado = MagicMock(return_value=False)

    with pytest.raises(RuntimeError, match="Filtro de vigencia"):
        pagina.preparar_filtros_fase_dois("01/04/2026", "31/03/2027")


def test_garantir_contexto_fase_dois_reaplica_quando_vigencia_se_perde():
    pagina, acoes, _logger = _pagina()
    pagina._expandir_filtros_avancados = MagicMock()
    pagina.validar_filtro_vigencia_aplicado = MagicMock(side_effect=[False, True])
    pagina.preparar_filtros_fase_dois = MagicMock()

    reaplicado = pagina.garantir_contexto_fase_dois("01/04/2026", "31/03/2027")

    assert reaplicado is True
    pagina.preparar_filtros_fase_dois.assert_called_once_with("01/04/2026", "31/03/2027")
    acoes.aguardar_carregamento_finalizar.assert_not_called()


def test_garantir_contexto_fase_dois_limpa_nome_quando_vigencia_ja_esta_correta():
    pagina, acoes, _logger = _pagina()
    pagina._expandir_filtros_avancados = MagicMock()
    pagina.validar_filtro_vigencia_aplicado = MagicMock(return_value=True)
    pagina.limpar_pesquisa_nome = MagicMock()

    reaplicado = pagina.garantir_contexto_fase_dois("01/04/2026", "31/03/2027")

    assert reaplicado is False
    pagina.limpar_pesquisa_nome.assert_called_once()
    acoes.aguardar_carregamento_finalizar.assert_called_once()


def test_localizar_linha_por_nome_exato_prefere_nome_original():
    pagina, _acoes, _logger = _pagina()
    linha_original = MagicMock()
    linha_copia = MagicMock()
    pagina.obter_linhas_tabela = MagicMock(return_value=[linha_copia, linha_original])
    nomes = {
        id(linha_copia): "FRANCHINI - Copia",
        id(linha_original): "FRANCHINI",
    }
    pagina.extrair_nome_linha = MagicMock(side_effect=lambda linha: nomes[id(linha)])

    linha = pagina.localizar_linha_por_nome_exato("FRANCHINI")

    assert linha is linha_original


def test_localizar_linha_por_nome_exato_lanca_quando_nao_encontra():
    pagina, _acoes, _logger = _pagina()
    pagina.obter_linhas_tabela = MagicMock(return_value=[])

    with pytest.raises(RuntimeError, match="nao encontrada"):
        pagina.localizar_linha_por_nome_exato("INEXISTENTE")


def test_validar_linha_para_reajuste_confere_nome_e_vigencia():
    pagina, _acoes, _logger = _pagina()
    linha = MagicMock()
    pagina.extrair_nome_linha = MagicMock(return_value="FRANCHINI")
    pagina.extrair_assinatura_linha = MagicMock(
        return_value="FRANCHINI | CLIENTE | Rodoviario | Peso | 01/04/26 - 31/03/27"
    )
    pagina.extrair_vigencia_linha = MagicMock(return_value="01/04/26 - 31/03/27")

    assinatura = pagina.validar_linha_para_reajuste(
        linha,
        "FRANCHINI",
        "01/04/2026",
        "31/03/2027",
    )

    assert assinatura.startswith("FRANCHINI |")


def test_validar_linha_para_reajuste_lanca_quando_vigencia_diferente():
    pagina, _acoes, _logger = _pagina()
    linha = MagicMock()
    pagina.extrair_nome_linha = MagicMock(return_value="FRANCHINI")
    pagina.extrair_assinatura_linha = MagicMock(return_value="FRANCHINI | 02/04/26 - 31/03/27")
    pagina.extrair_vigencia_linha = MagicMock(return_value="02/04/26 - 31/03/27")

    with pytest.raises(RuntimeError, match="vigencia divergente"):
        pagina.validar_linha_para_reajuste(
            linha,
            "FRANCHINI",
            "01/04/2026",
            "31/03/2027",
        )


def test_clicar_duplicar_tabela_usa_menu_visivel():
    pagina, acoes, _logger = _pagina()
    opcao = MagicMock()
    acoes.aguardar_seletor_xpath.return_value = opcao

    pagina.clicar_duplicar_tabela()

    xpath = acoes.aguardar_seletor_xpath.call_args.args[0]
    assert "Duplicar tabela" in xpath
    assert "display: none" in xpath
    acoes.clicar_com_seguranca.assert_called_once_with(opcao)


def test_clicar_reajuste_faz_fallback_quando_necessario():
    pagina, acoes, _logger = _pagina()
    opcao = MagicMock()
    pagina._localizar_opcao_reajuste_no_menu = MagicMock(side_effect=RuntimeError("falha"))
    acoes.aguardar_seletor_xpath.return_value = opcao
    acoes.resolver_alvo_clicavel.return_value = opcao

    pagina.clicar_reajuste()

    pagina._localizar_opcao_reajuste_no_menu.assert_called_once()
    acoes.aguardar_seletor_xpath.assert_called_once()
    acoes.resolver_alvo_clicavel.assert_called_once_with(opcao)
    acoes.clicar_com_seguranca.assert_called_once_with(opcao)


def test_clicar_reajuste_prefere_menu_da_linha_atual():
    pagina, acoes, _logger = _pagina()
    opcao = MagicMock()
    linha = MagicMock()
    pagina._localizar_opcao_reajuste_no_menu = MagicMock(return_value=opcao)
    acoes.resolver_alvo_clicavel.return_value = opcao

    pagina.clicar_reajuste(linha)

    pagina._localizar_opcao_reajuste_no_menu.assert_called_once_with(linha)
    acoes.aguardar_seletor_xpath.assert_not_called()
    acoes.clicar_com_seguranca.assert_called_once_with(opcao)


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_aguardar_modal_duplicacao_valida_popup_visivel(_sleep):
    pagina, _acoes, _logger = _pagina()
    popup = MagicMock()

    def _find(by, valor):
        if by == By.ID and valor == "duplicate_customers":
            return MagicMock()
        if by == By.CSS_SELECTOR and valor == "#duplicate_customers + span.switchery":
            return MagicMock()
        raise RuntimeError("nao encontrado")

    popup.find_element.side_effect = _find
    pagina._aguardar_popup_swal_visivel = MagicMock(return_value=popup)

    pagina.aguardar_modal_duplicacao()

    assert pagina._aguardar_popup_swal_visivel.call_args.args == (
        "copiar os clientes vinculados",
        "duplicar a tabela",
    )


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_ativar_switch_duplicacao_clica_switch_do_popup(_sleep):
    pagina, acoes, _logger = _pagina()
    popup = MagicMock()
    checkbox = MagicMock()
    checkbox.is_selected.return_value = False
    checkbox.get_attribute.return_value = ""
    switch = MagicMock()
    switch.get_attribute.return_value = ""

    def _find(by, valor):
        if by == By.ID and valor == "duplicate_customers":
            return checkbox
        if by == By.CSS_SELECTOR and valor == "#duplicate_customers + span.switchery":
            return switch
        raise RuntimeError("nao encontrado")

    popup.find_element.side_effect = _find
    pagina._aguardar_popup_swal_visivel = MagicMock(return_value=popup)

    pagina.ativar_switch_duplicacao()

    acoes.clicar_com_seguranca.assert_called_once_with(switch)


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_ativar_switch_duplicacao_nao_clica_quando_ja_esta_ativo(_sleep):
    pagina, acoes, _logger = _pagina()
    popup = MagicMock()
    checkbox = MagicMock()
    checkbox.is_selected.return_value = True
    popup.find_element.return_value = checkbox
    pagina._aguardar_popup_swal_visivel = MagicMock(return_value=popup)

    pagina.ativar_switch_duplicacao()

    acoes.clicar_com_seguranca.assert_not_called()


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_confirmar_modal_swal_clica_botao_do_popup_visivel(_sleep):
    pagina, acoes, _logger = _pagina()
    popup = MagicMock()
    botao = MagicMock()
    pagina._aguardar_popup_swal_visivel = MagicMock(return_value=popup)
    pagina._obter_botao_confirmar_popup = MagicMock(return_value=botao)

    pagina.confirmar_modal_swal("copiar os clientes vinculados")

    pagina._aguardar_popup_swal_visivel.assert_called_once_with(
        "copiar os clientes vinculados"
    )
    acoes.clicar_com_seguranca.assert_called_once_with(botao)


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_aguardar_modal_copia_finalizada_espera_texto_especifico(_sleep):
    pagina, _acoes, logger = _pagina()
    popup = MagicMock()
    popup.text = "Copia finalizada! Deseja editar a copia?"
    pagina._aguardar_popup_swal_com_progresso = MagicMock(return_value=popup)
    pagina._obter_botao_confirmar_popup = MagicMock(return_value=MagicMock())

    pagina.aguardar_modal_copia_finalizada()

    assert pagina._aguardar_popup_swal_com_progresso.call_args.args == (
        "copia finalizada",
        "editar a copia",
        "deseja editar",
    )
    assert (
        pagina._aguardar_popup_swal_com_progresso.call_args.kwargs["timeout"]
        == config.TIMEOUT_COPIA_FINALIZADA
    )
    pagina._obter_botao_confirmar_popup.assert_called_once_with(popup)


@patch("src.paginas.pagina_tabelas_cliente.time.sleep")
def test_confirmar_editar_copia_usa_modal_de_conclusao(_sleep):
    pagina, _acoes, _logger = _pagina()
    pagina.confirmar_modal_swal = MagicMock()
    pagina._aguardar_popup_desaparecer = MagicMock()

    pagina.confirmar_editar_copia()

    pagina.confirmar_modal_swal.assert_called_once_with(
        "copia finalizada",
        "editar a copia",
        "deseja editar",
    )
    pagina._aguardar_popup_desaparecer.assert_called_once()


def test_retornar_para_listagem_clica_link_e_aguarda_grid():
    pagina, acoes, logger = _pagina()
    link = MagicMock()
    acoes.aguardar_seletor_xpath.return_value = link
    pagina.aguardar_retorno_listagem = MagicMock()

    pagina.retornar_para_listagem()

    acoes.clicar_com_seguranca.assert_called_once_with(link)
    pagina.aguardar_retorno_listagem.assert_called_once_with(timeout=10)
    logger.info.assert_called_once()


def test_retornar_para_listagem_faz_fallback_para_url_direta():
    pagina, acoes, logger = _pagina()
    link = MagicMock()
    acoes.aguardar_seletor_xpath.return_value = link
    pagina.aguardar_retorno_listagem = MagicMock(side_effect=[RuntimeError("falha"), None])
    pagina.acessar_por_url = MagicMock()

    pagina.retornar_para_listagem()

    acoes.clicar_com_seguranca.assert_called_once_with(link)
    pagina.acessar_por_url.assert_called_once()
    assert pagina.aguardar_retorno_listagem.call_count == 2
    logger.warning.assert_called_once()


@patch("src.paginas.pagina_tabelas_cliente.WebDriverWait")
def test_aguardar_retorno_listagem_valida_input_e_grid(wait_cls):
    pagina, acoes, _logger = _pagina()

    pagina.aguardar_retorno_listagem(timeout=12)

    acoes.aguardar_documento_pronto.assert_called_once_with(timeout=12)
    acoes.aguardar_seletor.assert_called_once_with(
        "input_pesquisa_nome",
        "visivel",
        timeout=12,
    )
    wait_cls.return_value.until.assert_called_once()
    acoes.aguardar_carregamento_finalizar.assert_called_once_with(timeout=12)


def test_normalizar_texto_popup_remove_acentos():
    pagina, _acoes, _logger = _pagina()

    texto = pagina._normalizar_texto_popup("  Cópia   finalizada  ")

    assert texto == "copia finalizada"
