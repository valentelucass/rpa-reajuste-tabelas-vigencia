from unittest.mock import MagicMock
from unittest.mock import call

from src.paginas.pagina_tabelas_cliente import PaginaTabelasCliente
from src.servicos.criador_copia_tabela import CriadorCopiaTabela
from src.servicos.leitor_excel import DadosTabelaExcel


def _tabela(nome: str = "FRANCHINI") -> DadosTabelaExcel:
    return DadosTabelaExcel(
        nome=nome,
        data_inicio="01/04/2026",
        data_fim="31/03/2027",
        percentual=9.8,
    )


def test_criador_usa_linha_exata_do_excel_para_duplicar():
    pagina_tabelas = MagicMock()
    pagina_edicao = MagicMock()
    linha_original = MagicMock()
    pagina_tabelas.localizar_linha_por_nome_exato.return_value = linha_original

    criador = CriadorCopiaTabela(
        pagina_tabelas=pagina_tabelas,
        pagina_edicao=pagina_edicao,
        rastreador=None,
        logger=MagicMock(),
    )

    criador.criar_copia(_tabela())

    pagina_tabelas.pesquisar_por_nome.assert_called_once_with("FRANCHINI")
    pagina_tabelas.localizar_linha_por_nome_exato.assert_called_once_with("FRANCHINI")
    pagina_tabelas.abrir_dropdown_linha.assert_called_once_with(linha_original)
    pagina_tabelas.abrir_dropdown_primeira_linha.assert_not_called()


def test_localiza_linha_exata_antes_de_copia_existente():
    pagina = PaginaTabelasCliente(acoes=MagicMock(), logger=MagicMock())
    linha_original = MagicMock()
    linha_original.is_displayed.return_value = True
    linha_copia = MagicMock()
    linha_copia.is_displayed.return_value = True

    pagina.obter_linhas_tabela = MagicMock(return_value=[linha_copia, linha_original])
    nomes = {
        id(linha_copia): "FRANCHINI - Copia",
        id(linha_original): "FRANCHINI",
    }
    pagina.extrair_nome_linha = MagicMock(side_effect=lambda linha: nomes[id(linha)])

    resultado = pagina.localizar_linha_por_nome_exato("FRANCHINI")

    assert resultado is linha_original


def test_criador_aguarda_modal_finalizada_antes_de_editar():
    pagina_tabelas = MagicMock()
    pagina_edicao = MagicMock()
    linha_original = MagicMock()
    pagina_tabelas.localizar_linha_por_nome_exato.return_value = linha_original

    criador = CriadorCopiaTabela(
        pagina_tabelas=pagina_tabelas,
        pagina_edicao=pagina_edicao,
        rastreador=None,
        logger=MagicMock(),
    )

    criador.criar_copia(_tabela())

    chamadas = pagina_tabelas.method_calls
    assert chamadas.index(call.aguardar_modal_copia_finalizada()) < chamadas.index(
        call.confirmar_editar_copia()
    )


def test_criador_descarta_popup_inesperado_antes_de_iniciar():
    pagina_tabelas = MagicMock()
    pagina_edicao = MagicMock()
    pagina_tabelas.localizar_linha_por_nome_exato.return_value = MagicMock()

    criador = CriadorCopiaTabela(
        pagina_tabelas=pagina_tabelas,
        pagina_edicao=pagina_edicao,
        rastreador=None,
        logger=MagicMock(),
    )

    criador.criar_copia(_tabela())

    pagina_tabelas.descartar_popup_swal_inesperado.assert_called_once()
    chamadas = pagina_tabelas.method_calls
    assert chamadas.index(call.descartar_popup_swal_inesperado()) < chamadas.index(
        call.pesquisar_por_nome("FRANCHINI")
    )


def test_criador_retorna_para_listagem_apos_salvar():
    pagina_tabelas = MagicMock()
    pagina_edicao = MagicMock()
    linha_original = MagicMock()
    pagina_tabelas.localizar_linha_por_nome_exato.return_value = linha_original

    criador = CriadorCopiaTabela(
        pagina_tabelas=pagina_tabelas,
        pagina_edicao=pagina_edicao,
        rastreador=None,
        logger=MagicMock(),
    )

    criador.criar_copia(_tabela())

    pagina_tabelas.retornar_para_listagem.assert_called_once()
    pagina_tabelas.aguardar_retorno_listagem.assert_not_called()
