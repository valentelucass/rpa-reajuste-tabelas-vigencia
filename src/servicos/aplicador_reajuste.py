"""
Serviço responsável por aplicar o reajuste em uma tabela copiada.
Orquestra: dropdown → reajuste → abas → taxas → salvar → fechar.
"""

import logging
from typing import Callable, Optional

from selenium.webdriver.remote.webelement import WebElement

from src.infraestrutura.rastreador_etapas import RastreadorEtapas
from src.servicos.leitor_excel import ComponenteReajuste


class AplicadorReajuste:
    """
    Executa o fluxo completo de reajuste de uma tabela copiada.
    Depende das páginas PaginaTabelasCliente e PaginaReajuste.
    """

    def __init__(
        self,
        pagina_tabelas,
        pagina_reajuste,
        rastreador: Optional[RastreadorEtapas] = None,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.pagina_tabelas = pagina_tabelas
        self.pagina_reajuste = pagina_reajuste
        self.rastreador = rastreador
        self.logger = logger or logging.getLogger("rpa")

    def aplicar(
        self,
        assinatura_linha: str,
        nome_tabela: str,
        componentes: list[ComponenteReajuste],
        percentual: float,
        linha: Optional[WebElement] = None,
        registrar_evento: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """
        Aplica reajuste em uma linha identificada por assinatura textual.
        Levanta exceção em caso de falha — o chamador decide como tratar.
        """
        ctx = {
            "nome_tabela": nome_tabela,
            "assinatura": assinatura_linha,
            "percentual": percentual
        }

        if linha is None:
            with self._etapa("relocalizar_linha", f"Relocalizando linha '{nome_tabela}'", ctx):
                linha = self.pagina_tabelas.relocalizar_linha_por_assinatura(assinatura_linha)

        with self._etapa("abrir_dropdown", "Abrindo menu de ações da linha", ctx):
            self.pagina_tabelas.abrir_dropdown_linha(linha)

        with self._etapa("clicar_reajuste", "Clicando em Reajuste", ctx):
            self.pagina_tabelas.clicar_reajuste(linha)

        with self._etapa("aguardar_modal_reajuste", "Aguardando modal de reajuste", ctx):
            self.pagina_reajuste.aguardar_modal()

        with self._etapa("posicionar_em_reajustar_taxas", "Garantindo aba inicial Reajustar Taxas", ctx):
            self.pagina_reajuste.navegar_para_aba("fee", forcar_clique=True)

        with self._etapa("considerar_todos_trechos", "Marcando todos os trechos", ctx):
            self.pagina_reajuste.considerar_todos_trechos()

        for componente in componentes:
            nome_etapa = f"reajuste_{componente.aba}_{componente.nome_taxa}"
            descricao = f"Aplicando reajuste: [{componente.aba}] {componente.nome_taxa}"
            with self._etapa(nome_etapa, descricao, {**ctx, "taxa": componente.nome_taxa}):
                self.pagina_reajuste.navegar_para_aba(componente.aba)
                self.pagina_reajuste.selecionar_taxa(componente.nome_taxa)
                self.pagina_reajuste.definir_valor(percentual)
                self.pagina_reajuste.clicar_adicionar()

        if registrar_evento:
            registrar_evento(
                "REAJUSTE_APLICADO",
                f"percentual={percentual} componentes={len(componentes)}",
            )

        with self._etapa("salvar_reajuste", "Salvando reajuste", ctx):
            self.pagina_reajuste.salvar()
            self.pagina_reajuste.confirmar_modal_ok()
            self.pagina_reajuste.fechar_modal()
            self.pagina_tabelas.aguardar_carregamento_apos_fechar()

        if registrar_evento:
            registrar_evento("SALVO", "modal_reajuste_fechado=true")

        self.logger.info(f"Reajuste aplicado com sucesso: {nome_tabela}")

    def _etapa(self, nome: str, descricao: str, contexto: dict):
        if self.rastreador:
            return self.rastreador.etapa(nome, descricao, contexto)
        from contextlib import nullcontext
        return nullcontext()
