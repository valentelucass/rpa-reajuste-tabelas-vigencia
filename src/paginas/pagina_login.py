"""
Page Object da tela de login.
Responsabilidade: acessar a URL, preencher credenciais e verificar autenticacao.
"""

import logging
from typing import Optional

import config
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src.infraestrutura.acoes_navegador import AcoesNavegador


class PaginaLogin:
    """Encapsula toda a interacao com a tela de login do ESL Cloud."""

    def __init__(self, acoes: AcoesNavegador, logger: Optional[logging.Logger] = None) -> None:
        self.acoes = acoes
        self.logger = logger or logging.getLogger("rpa")

    def abrir(self) -> None:
        """Navega para a URL de login e aguarda o carregamento."""
        self.logger.info(f"Abrindo login: {config.URL_LOGIN}")
        self.acoes.driver.get(config.URL_LOGIN)
        self.acoes.aguardar_documento_pronto()

    def autenticar(self) -> None:
        """Preenche email, senha e clica em Entrar."""
        self.logger.info("Autenticando...")

        campo_email = self.acoes.aguardar_seletor("campo_email", "visivel")
        self.acoes.limpar_e_digitar(campo_email, config.EMAIL_LOGIN)

        campo_senha = self.acoes.aguardar_seletor("campo_senha", "visivel")
        self.acoes.limpar_e_digitar(campo_senha, config.SENHA_LOGIN)

        botao_entrar = self.acoes.aguardar_seletor("botao_entrar", "clicavel")
        self.acoes.clicar_com_seguranca(botao_entrar)

        self._aguardar_resultado_login()
        self._verificar_login_sucedido()

    def _aguardar_resultado_login(self) -> None:
        """Aguarda o login concluir sem pagar espera fixa desnecessaria."""
        seletor_erro = ".alert-danger, .alert-warning, #error_explanation"

        try:
            WebDriverWait(self.acoes.driver, config.PAGE_LOAD_TIMEOUT).until(
                lambda d: (
                    d.execute_script("return document.readyState") == "complete"
                    and (
                        d.current_url.rstrip("/") != config.URL_LOGIN.rstrip("/")
                        or len(d.find_elements(By.CSS_SELECTOR, seletor_erro)) > 0
                    )
                )
            )
        except TimeoutException:
            pass

    def _verificar_login_sucedido(self) -> None:
        """Valida se o login foi concluido com sucesso ou se houve erro visivel."""
        seletor_erro = ".alert-danger, .alert-warning, #error_explanation"
        erros = self.acoes.driver.find_elements(By.CSS_SELECTOR, seletor_erro)
        if erros:
            mensagem = erros[0].text.strip()
            raise RuntimeError(f"Falha no login: {mensagem}")

        if self.acoes.driver.current_url.rstrip("/") == config.URL_LOGIN.rstrip("/"):
            raise RuntimeError("Falha no login: o sistema permaneceu na tela de entrada.")

        self.logger.info("Login realizado com sucesso")
