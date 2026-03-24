"""
Page Object da tela de edição de uma tabela de cliente.
Responsabilidade: nome, vigência, parametrizações e salvar.
"""

import logging
import time
from typing import Optional

import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.infraestrutura.acoes_navegador import AcoesNavegador


class PaginaEdicaoTabela:
    """Encapsula a tela de edição de tabela (formulário após duplicação)."""

    def __init__(self, acoes: AcoesNavegador, logger: Optional[logging.Logger] = None) -> None:
        self.acoes = acoes
        self.logger = logger or logging.getLogger("rpa")

    def aguardar_tela_edicao(self) -> None:
        """Aguarda o campo de nome da tabela estar visível."""
        self.acoes.aguardar_seletor("input_nome_tabela", "visivel", timeout=config.PAGE_LOAD_TIMEOUT)
        self.acoes.aguardar_carregamento_finalizar()
        self.logger.info("Tela de edição carregada")

    def definir_nome(self, nome: str) -> None:
        """Substitui o nome atual (que contém '- Cópia') pelo nome correto."""
        campo = self.acoes.aguardar_seletor("input_nome_tabela", "visivel")
        self.acoes.limpar_e_digitar(campo, nome)
        self.logger.debug(f"Nome definido: {nome}")

    def expandir_parametrizacoes(self) -> None:
        """Expande o accordion de Parametrizações para tornar os campos de data visíveis."""
        try:
            accordion = self.acoes.aguardar_seletor("accordion_parametrizacoes", "clicavel", timeout=5)
            # Verifica se já está expandido
            aria_expanded = accordion.get_attribute("aria-expanded")
            if aria_expanded == "false" or "collapsed" in (accordion.get_attribute("class") or ""):
                self.acoes.clicar_com_seguranca(accordion)
                time.sleep(0.5)
            # Aguarda os campos de data ficarem visíveis
            WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.ID, "customer_price_table_effective_since")
                )
            )
        except Exception as e:
            self.logger.warning(f"Erro ao expandir parametrizações: {e}")

    def definir_data_inicio(self, data: str) -> None:
        """Preenche o campo 'Válida de' com a data de início da vigência."""
        campo = self.acoes.aguardar_seletor("input_data_inicio", "visivel")
        self.acoes.limpar_e_digitar(campo, data)
        time.sleep(0.2)
        self.logger.debug(f"Data início: {data}")

    def definir_data_fim(self, data: str) -> None:
        """Preenche o campo 'Válida até' com a data de fim da vigência."""
        campo = self.acoes.aguardar_seletor("input_data_fim", "visivel")
        self.acoes.limpar_e_digitar(campo, data)
        time.sleep(0.2)
        self.logger.debug(f"Data fim: {data}")

    def salvar(self) -> None:
        """Clica no botão Salvar do formulário de edição."""
        xpath = (
            "//a[@id='submit' and contains(@class,'btn-primary') "
            "and .//span[normalize-space(text())='Salvar']]"
        )
        try:
            botao = self.acoes.aguardar_seletor_xpath(xpath, "clicavel", timeout=5)
        except Exception:
            botao = self.acoes.aguardar_seletor("botao_salvar_edicao", "clicavel")
        self.acoes.clicar_com_seguranca(botao)
        time.sleep(0.5)

    def confirmar_modal_swal(self) -> None:
        """Clica em Sim no SweetAlert de confirmação do salvamento."""
        botao = self.acoes.aguardar_seletor("botao_swal_confirmar", "clicavel")
        self.acoes.clicar_com_seguranca(botao)
        try:
            self.acoes.aguardar_invisibilidade_css(
                "div.swal2-popup.swal2-modal.swal2-show",
                timeout=5,
            )
        except Exception:
            time.sleep(0.5)
        self.logger.debug("Salvamento confirmado")
