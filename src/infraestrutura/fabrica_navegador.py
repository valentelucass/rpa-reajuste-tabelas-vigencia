"""
Fábrica do navegador Selenium.
Tenta Chrome primeiro, com fallback para Edge.
"""

import logging

import config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService


logger = logging.getLogger("rpa")


def _opcoes_base(opcoes) -> None:
    """Aplica as opções comuns em qualquer driver."""
    if config.HEADLESS:
        opcoes.add_argument("--headless=new")
    opcoes.add_argument("--start-maximized")
    opcoes.add_argument("--disable-gpu")
    opcoes.add_argument("--no-sandbox")
    opcoes.add_argument("--disable-dev-shm-usage")
    opcoes.add_argument("--disable-extensions")
    opcoes.add_argument("--disable-infobars")
    try:
        opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])
        opcoes.add_experimental_option("useAutomationExtension", False)
    except Exception:
        pass


class FabricaNavegador:
    """Cria a instância do WebDriver com Chrome ou Edge como fallback."""

    @staticmethod
    def criar() -> webdriver.Chrome | webdriver.Edge:
        try:
            return FabricaNavegador._criar_chrome()
        except Exception as erro_chrome:
            logger.warning(f"Chrome não disponível ({erro_chrome}). Tentando Edge...")
            try:
                return FabricaNavegador._criar_edge()
            except Exception as erro_edge:
                raise RuntimeError(
                    f"Nenhum navegador disponível.\nChrome: {erro_chrome}\nEdge: {erro_edge}"
                )

    @staticmethod
    def _criar_chrome() -> webdriver.Chrome:
        opcoes = ChromeOptions()
        _opcoes_base(opcoes)
        driver = webdriver.Chrome(options=opcoes)
        driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        return driver

    @staticmethod
    def _criar_edge() -> webdriver.Edge:
        opcoes = EdgeOptions()
        _opcoes_base(opcoes)
        driver = webdriver.Edge(options=opcoes)
        driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        return driver
