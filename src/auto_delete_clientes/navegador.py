"""
Fabrica do navegador Selenium.
Usa Microsoft Edge como navegador padrao.
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    from . import config
except ImportError:  # pragma: no cover - compatibilidade standalone
    from auto_delete_compat import carregar_modulo_local

    config = carregar_modulo_local("config")
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions


class FabricaNavegador:
    """Cria instancia do WebDriver com Microsoft Edge."""

    @staticmethod
    def criar(logger: Optional[logging.Logger] = None) -> webdriver.Edge:
        log = logger or logging.getLogger("auto_delete_clientes")
        log.info("Iniciando Microsoft Edge...")
        opcoes = EdgeOptions()
        if config.HEADLESS:
            opcoes.add_argument("--headless=new")
        opcoes.add_argument("--start-maximized")
        opcoes.add_argument("--disable-gpu")
        opcoes.add_argument("--no-sandbox")
        opcoes.add_argument("--disable-dev-shm-usage")
        opcoes.add_argument("--disable-extensions")
        opcoes.add_argument("--disable-infobars")
        opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])
        opcoes.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Edge(options=opcoes)
        driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        return driver
