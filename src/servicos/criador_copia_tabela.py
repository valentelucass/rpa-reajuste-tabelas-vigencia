"""
Servico responsavel por criar a copia de uma tabela de clientes.
Orquestra: pesquisa, duplicacao, edicao de nome, vigencia e salvar.
"""

import logging
from typing import Optional

from src.infraestrutura.rastreador_etapas import RastreadorEtapas
from src.servicos.leitor_excel import DadosTabelaExcel


class CriadorCopiaTabela:
    """
    Executa o fluxo completo de criacao de copia de uma tabela.
    Depende das paginas PaginaTabelasCliente e PaginaEdicaoTabela.
    """

    def __init__(
        self,
        pagina_tabelas,
        pagina_edicao,
        rastreador: Optional[RastreadorEtapas] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.pagina_tabelas = pagina_tabelas
        self.pagina_edicao = pagina_edicao
        self.rastreador = rastreador
        self.logger = logger or logging.getLogger("rpa")

    def criar_copia(self, tabela: DadosTabelaExcel) -> None:
        """
        Cria a copia da tabela e configura nome e vigencia.
        Levanta excecao em caso de falha; o chamador decide como tratar.
        """
        contexto = {
            "nome_tabela": tabela.nome,
            "data_inicio": tabela.data_inicio,
            "data_fim": tabela.data_fim,
        }

        self.pagina_tabelas.descartar_popup_swal_inesperado()

        with self._etapa("pesquisar_tabela", f"Pesquisando tabela '{tabela.nome}'", contexto):
            self.pagina_tabelas.pesquisar_por_nome(tabela.nome)
            self.pagina_tabelas.aguardar_resultado_pesquisa()
            self.pagina_tabelas.validar_resultado_encontrado(tabela.nome)
            linha_original = self.pagina_tabelas.localizar_linha_por_nome_exato(tabela.nome)

        with self._etapa("abrir_dropdown", "Abrindo menu de acoes", contexto):
            self.pagina_tabelas.abrir_dropdown_linha(linha_original)

        with self._etapa("clicar_duplicar", "Clicando em Duplicar tabela", contexto):
            self.pagina_tabelas.clicar_duplicar_tabela()

        with self._etapa("ativar_switch", "Ativando switch de duplicacao", contexto):
            self.pagina_tabelas.aguardar_modal_duplicacao()
            self.pagina_tabelas.ativar_switch_duplicacao()

        with self._etapa("confirmar_duplicacao", "Confirmando duplicacao", contexto):
            self.pagina_tabelas.confirmar_modal_swal()

        with self._etapa("aguardar_copia_finalizada", "Aguardando copia ser finalizada", contexto):
            self.pagina_tabelas.aguardar_modal_copia_finalizada()

        with self._etapa("abrir_edicao", "Abrindo tela de edicao da copia", contexto):
            self.pagina_tabelas.confirmar_editar_copia()
            self.pagina_edicao.aguardar_tela_edicao()

        with self._etapa("definir_nome", f"Definindo nome '{tabela.nome}'", contexto):
            self.pagina_edicao.definir_nome(tabela.nome)

        with self._etapa("expandir_parametrizacoes", "Expandindo secao Parametrizacoes", contexto):
            self.pagina_edicao.expandir_parametrizacoes()

        with self._etapa(
            "definir_datas",
            f"Definindo vigencia {tabela.data_inicio} a {tabela.data_fim}",
            contexto,
        ):
            self.pagina_edicao.definir_data_inicio(tabela.data_inicio)
            self.pagina_edicao.definir_data_fim(tabela.data_fim)

        with self._etapa("salvar_edicao", "Salvando edicao da tabela", contexto):
            self.pagina_edicao.salvar()
            self.pagina_edicao.confirmar_modal_swal()
            self.pagina_tabelas.retornar_para_listagem()

        self.logger.info(f"Copia criada com sucesso: {tabela.nome}")

    def _etapa(self, nome: str, descricao: str, contexto: dict):
        if self.rastreador:
            return self.rastreador.etapa(nome, descricao, contexto)
        from contextlib import nullcontext

        return nullcontext()
