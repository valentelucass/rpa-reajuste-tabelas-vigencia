import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parent))

from pagina_exclusao import PaginaExclusao, config


@dataclass
class LinhaFake:
    key: str
    nome: str

    def get_attribute(self, nome: str) -> str:
        if nome == "data-id":
            return self.key
        return ""


def criar_pagina() -> tuple[PaginaExclusao, MagicMock]:
    acoes = MagicMock()
    acoes.driver = MagicMock()
    acoes.aguardar_documento_pronto = MagicMock()
    acoes.aguardar_carregamento_finalizar = MagicMock()
    acoes.aguardar_tabela_estavel = MagicMock()
    acoes.aguardar_invisibilidade_css = MagicMock()
    acoes.executar_script = MagicMock(return_value={})

    logger = logging.getLogger(f"auto_delete_test_{id(acoes)}")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    return PaginaExclusao(acoes, logger), acoes


def preparar_fluxo_linhas(pagina: PaginaExclusao, linhas: list[LinhaFake]) -> dict:
    estado = {"visiveis": list(linhas)}
    pagina.buscar_cliente = MagicMock()
    pagina.verificar_navegador_aberto = MagicMock(return_value=True)
    pagina.obter_linhas_tabela = MagicMock(side_effect=lambda: list(estado["visiveis"]))
    pagina.extrair_nome_linha = MagicMock(side_effect=lambda linha: linha.nome)
    pagina.abrir_dropdown_linha = MagicMock()
    return estado


def test_confirmar_exclusao_modal_registra_timeout(caplog):
    pagina, acoes = criar_pagina()
    popup = MagicMock()
    botao = MagicMock()
    popup.find_element.return_value = botao

    caplog.set_level(logging.INFO, logger=pagina.logger.name)

    with patch.object(pagina, "_encontrar_popup_swal_visivel", return_value=popup):
        with patch.object(
            pagina,
            "_aguardar_resultado_visual_exclusao",
            return_value="timeout",
        ):
            resultado = pagina.confirmar_exclusao_modal("data-id:linha-1")

    assert resultado == "timeout"
    acoes.clicar_com_seguranca.assert_called_once_with(botao)
    assert "Exclusao iniciada" in caplog.text
    assert (
        f"Aguardando resposta do sistema (ate {config.TIMEOUT_RESPOSTA_EXCLUSAO}s)"
        in caplog.text
    )
    assert "Timeout - nenhuma resposta do sistema" in caplog.text


def test_confirmar_exclusao_modal_trata_popup_de_erro(caplog):
    pagina, acoes = criar_pagina()
    popup = MagicMock()
    botao = MagicMock()
    popup.find_element.return_value = botao

    caplog.set_level(logging.INFO, logger=pagina.logger.name)

    with patch.object(pagina, "_encontrar_popup_swal_visivel", return_value=popup):
        with patch.object(
            pagina,
            "_aguardar_resultado_visual_exclusao",
            return_value="erro",
        ):
            with patch.object(pagina, "_fechar_popup_resultado", return_value=True) as fechar:
                resultado = pagina.confirmar_exclusao_modal("data-id:linha-1")

    assert resultado == "erro"
    fechar.assert_called_once_with("erro")
    acoes.clicar_com_seguranca.assert_called_once_with(botao)
    assert "Erro detectado - popup tratado" in caplog.text


def test_confirmar_exclusao_modal_executa_refresh_quando_timeout_sem_atualizacao(caplog):
    pagina, acoes = criar_pagina()
    popup = MagicMock()
    botao = MagicMock()
    popup.find_element.return_value = botao

    caplog.set_level(logging.INFO, logger=pagina.logger.name)

    with patch.object(pagina, "_encontrar_popup_swal_visivel", return_value=popup):
        with patch.object(
            pagina,
            "_aguardar_resultado_visual_exclusao",
            return_value="timeout_refresh",
        ):
            resultado = pagina.confirmar_exclusao_modal("data-id:linha-1")

    assert resultado == "timeout_refresh"
    acoes.driver.refresh.assert_called_once()
    acoes.aguardar_documento_pronto.assert_called_once()
    acoes.aguardar_carregamento_finalizar.assert_called_once()
    acoes.aguardar_tabela_estavel.assert_called_once()
    assert "Timeout de 2 minutos atingido sem resposta" in caplog.text
    assert "Executando refresh do navegador" in caplog.text
    assert "Seguindo para proximo nome apos refresh" in caplog.text


def test_excluir_registro_pula_linha_apos_timeout_sem_segundo_clique(caplog):
    pagina, _ = criar_pagina()
    linhas = [LinhaFake("linha-1", "CLIENTE"), LinhaFake("linha-2", "CLIENTE")]
    estado = preparar_fluxo_linhas(pagina, linhas)
    cliques: list[str] = []

    def clicar_excluir(linha: LinhaFake) -> None:
        cliques.append(linha.key)

    def confirmar_exclusao(chave_linha: str) -> str:
        if chave_linha == "data-id:linha-1":
            return "timeout"
        estado["visiveis"] = [
            linha for linha in estado["visiveis"] if linha.key != "linha-2"
        ]
        return "sucesso"

    pagina.clicar_excluir = MagicMock(side_effect=clicar_excluir)
    pagina.confirmar_exclusao_modal = MagicMock(side_effect=confirmar_exclusao)

    caplog.set_level(logging.INFO, logger=pagina.logger.name)

    with patch("pagina_exclusao.atraso_humano", lambda *args, **kwargs: None):
        resultado = pagina.excluir_registro("CLIENTE")

    assert resultado == "erro_exclusao"
    assert cliques == ["linha-1", "linha-2"]
    assert cliques.count("linha-1") == 1
    assert "Pulando para proxima linha" in caplog.text


def test_excluir_registro_pula_linha_apos_popup_sem_segundo_clique(caplog):
    pagina, _ = criar_pagina()
    linhas = [LinhaFake("linha-1", "CLIENTE"), LinhaFake("linha-2", "CLIENTE")]
    estado = preparar_fluxo_linhas(pagina, linhas)
    cliques: list[str] = []

    def clicar_excluir(linha: LinhaFake) -> None:
        cliques.append(linha.key)

    def confirmar_exclusao(chave_linha: str) -> str:
        if chave_linha == "data-id:linha-1":
            return "erro"
        estado["visiveis"] = [
            linha for linha in estado["visiveis"] if linha.key != "linha-2"
        ]
        return "sucesso"

    pagina.clicar_excluir = MagicMock(side_effect=clicar_excluir)
    pagina.confirmar_exclusao_modal = MagicMock(side_effect=confirmar_exclusao)

    caplog.set_level(logging.INFO, logger=pagina.logger.name)

    with patch("pagina_exclusao.atraso_humano", lambda *args, **kwargs: None):
        resultado = pagina.excluir_registro("CLIENTE")

    assert resultado == "erro_exclusao"
    assert cliques == ["linha-1", "linha-2"]
    assert cliques.count("linha-1") == 1
    assert "Pulando para proxima linha" in caplog.text


def test_excluir_registro_interrompe_nome_atual_apos_timeout_refresh():
    pagina, _ = criar_pagina()
    linhas = [LinhaFake("linha-1", "CLIENTE"), LinhaFake("linha-2", "CLIENTE")]
    preparar_fluxo_linhas(pagina, linhas)
    cliques: list[str] = []

    def clicar_excluir(linha: LinhaFake) -> None:
        cliques.append(linha.key)

    pagina.clicar_excluir = MagicMock(side_effect=clicar_excluir)
    pagina.confirmar_exclusao_modal = MagicMock(return_value="timeout_refresh")

    with patch("pagina_exclusao.atraso_humano", lambda *args, **kwargs: None):
        resultado = pagina.excluir_registro("CLIENTE")

    assert resultado == "erro_exclusao"
    assert cliques == ["linha-1"]
