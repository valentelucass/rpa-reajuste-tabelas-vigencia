"""
Façade sobre o Selenium. Centraliza waits, localização, clique e digitação.
Nenhum código fora desta classe deve usar WebDriverWait, find_element ou execute_script diretamente.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import config
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.infraestrutura.caminhos import SCREENSHOTS_DIR
from src.infraestrutura.debug_visual import DebugVisual


class AcoesNavegador:
    """
    Façade de interação com o browser.
    Resolve seletores por nome, abstrai waits e fornece clique/digitação robustos.
    """

    def __init__(self, driver, logger: Optional[logging.Logger] = None) -> None:
        self.driver = driver
        self.logger = logger or logging.getLogger("rpa")
        self.debug = DebugVisual(driver)

    # ------------------------------------------------------------------
    # Waits de documento e overlay
    # ------------------------------------------------------------------

    def aguardar_documento_pronto(self, timeout: Optional[int] = None) -> None:
        """Aguarda document.readyState == 'complete'."""
        t = timeout or config.PAGE_LOAD_TIMEOUT
        WebDriverWait(self.driver, t).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def aguardar_carregamento_finalizar(self, timeout: Optional[int] = None) -> None:
        """Aguarda a ausência de overlays e spinners comuns."""
        t = timeout or config.TIMEOUT
        seletores_overlay = [
            ".loading", ".spinner", ".overlay",
            "[class*='loading']", "[class*='spinner']"
        ]
        try:
            for seletor in seletores_overlay:
                WebDriverWait(self.driver, 3).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, seletor))
                )
        except Exception:
            pass
        # Aguarda JS finalizar
        WebDriverWait(self.driver, t).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    # ------------------------------------------------------------------
    # Localização por nome de seletor
    # ------------------------------------------------------------------

    def _resolver_seletores(self, nome: str) -> list[tuple[str, str]]:
        from config import SELETORES
        if nome not in SELETORES:
            raise ValueError(f"Seletor '{nome}' não encontrado em config.SELETORES")
        return SELETORES[nome]

    def _by_para_selenium(self, tipo: str) -> str:
        mapa = {
            "id": By.ID,
            "css selector": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "name": By.NAME,
            "class name": By.CLASS_NAME,
            "tag name": By.TAG_NAME,
        }
        return mapa.get(tipo.lower(), By.XPATH)

    def aguardar_seletor(
        self,
        nome: str,
        condicao: str = "visivel",
        timeout: Optional[int] = None,
        contexto: Optional[WebElement] = None
    ) -> WebElement:
        """
        Aguarda e retorna o primeiro elemento encontrado pelos seletores nomeados.
        condicao: 'visivel', 'clicavel', 'presente'
        """
        t = timeout or config.TIMEOUT
        seletores = self._resolver_seletores(nome)
        ultima_excecao: Exception = RuntimeError(f"Seletor '{nome}' não encontrado")

        for tipo, valor in seletores:
            by = self._by_para_selenium(tipo)
            localizador = (by, valor)
            try:
                raiz = contexto if contexto else self.driver
                if condicao == "visivel":
                    cond = EC.visibility_of_element_located(localizador)
                elif condicao == "clicavel":
                    cond = EC.element_to_be_clickable(localizador)
                else:
                    cond = EC.presence_of_element_located(localizador)

                if contexto:
                    elemento = contexto.find_element(by, valor)
                    WebDriverWait(self.driver, t).until(lambda d: elemento.is_displayed())
                    return elemento
                else:
                    return WebDriverWait(self.driver, t).until(cond)
            except Exception as e:
                ultima_excecao = e
                continue

        raise ultima_excecao

    def buscar_todos_por_nome_seletor(self, nome: str) -> list[WebElement]:
        """
        Busca todos os elementos pelo seletor nomeado, deduplicando por id interno.
        """
        from config import SELETORES
        seletores = SELETORES.get(nome, [])
        vistos: set[str] = set()
        resultado: list[WebElement] = []

        for tipo, valor in seletores:
            by = self._by_para_selenium(tipo)
            try:
                elementos = self.driver.find_elements(by, valor)
                for elem in elementos:
                    try:
                        eid = elem.id
                        if eid not in vistos:
                            vistos.add(eid)
                            resultado.append(elem)
                    except Exception:
                        pass
            except Exception:
                pass

        return resultado

    def aguardar_seletor_xpath(self, xpath: str, condicao: str = "visivel", timeout: Optional[int] = None) -> WebElement:
        """Aguarda elemento por XPath direto (sem passar por SELETORES)."""
        t = timeout or config.TIMEOUT
        if condicao == "clicavel":
            return WebDriverWait(self.driver, t).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
        return WebDriverWait(self.driver, t).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
        )

    def aguardar_seletor_css(self, css: str, condicao: str = "visivel", timeout: Optional[int] = None) -> WebElement:
        """Aguarda elemento por CSS direto."""
        t = timeout or config.TIMEOUT
        if condicao == "clicavel":
            return WebDriverWait(self.driver, t).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, css))
            )
        return WebDriverWait(self.driver, t).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css))
        )

    def aguardar_invisibilidade_css(self, css: str, timeout: Optional[int] = None) -> None:
        t = timeout or config.TIMEOUT
        WebDriverWait(self.driver, t).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, css))
        )

    def aguardar_invisibilidade_xpath(self, xpath: str, timeout: Optional[int] = None) -> None:
        t = timeout or config.TIMEOUT
        WebDriverWait(self.driver, t).until(
            EC.invisibility_of_element_located((By.XPATH, xpath))
        )

    # ------------------------------------------------------------------
    # Clique seguro
    # ------------------------------------------------------------------

    def clicar_com_seguranca(self, elemento: WebElement) -> None:
        """scrollIntoView + highlight + click, com fallback para JS click."""
        self._scroll_para_elemento(elemento)
        self.debug.destacar(elemento)
        try:
            elemento.click()
        except Exception:
            self.executar_script("arguments[0].click()", elemento)

    def _scroll_para_elemento(self, elemento: WebElement) -> None:
        try:
            self.executar_script(
                "arguments[0].scrollIntoView({block:'center', inline:'nearest'})",
                elemento
            )
            time.sleep(0.05)
        except Exception:
            pass

    def resolver_alvo_clicavel(self, elemento: WebElement) -> WebElement:
        """
        Sobe na árvore DOM até encontrar um elemento clicável real
        (button, a, label ou role=button).
        """
        tags_clicaveis = {"button", "a", "label"}
        try:
            tag = elemento.tag_name.lower()
            if tag in tags_clicaveis or elemento.get_attribute("role") == "button":
                return elemento
            # Tenta ancestrais via JS
            ancestral = self.executar_script(
                """
                var e = arguments[0];
                var tags = ['button','a','label'];
                while (e && e.parentElement) {
                    e = e.parentElement;
                    if (tags.includes(e.tagName.toLowerCase()) ||
                        e.getAttribute('role') === 'button') return e;
                }
                return null;
                """,
                elemento
            )
            return ancestral if ancestral else elemento
        except Exception:
            return elemento

    # ------------------------------------------------------------------
    # Digitação
    # ------------------------------------------------------------------

    def limpar_e_digitar(self, elemento: WebElement, texto: str) -> None:
        """Limpa o campo com Ctrl+A + Backspace e digita o texto."""
        self._scroll_para_elemento(elemento)
        self.debug.destacar(elemento)
        try:
            elemento.click()
        except Exception:
            pass
        time.sleep(0.1)
        elemento.send_keys(Keys.CONTROL, "a")
        elemento.send_keys(Keys.BACKSPACE)
        time.sleep(0.1)
        elemento.send_keys(texto)

    # ------------------------------------------------------------------
    # Select2
    # ------------------------------------------------------------------

    def selecionar_select2(self, nome_seletor: str, texto: str) -> None:
        """
        Interage com um componente Select2: clica no container,
        aguarda o dropdown e seleciona a opção pelo texto.
        """
        container = self.aguardar_seletor(nome_seletor, "clicavel")
        self.clicar_com_seguranca(container)
        time.sleep(0.15)

        # Digita apenas no campo de busca do Select2 atualmente aberto.
        campo_busca = self._obter_campo_busca_select2_aberto(timeout=1)
        if campo_busca:
            try:
                campo_busca.send_keys(Keys.CONTROL, "a")
                campo_busca.send_keys(Keys.BACKSPACE)
                campo_busca.send_keys(texto)
                time.sleep(0.15)
            except Exception:
                pass

        # Localiza a opção pelo texto
        xpath_opcao = (
            f"//li[contains(@class,'select2-results__option') and "
            f"normalize-space(text())='{texto}']"
        )
        xpath_opcao_parcial = (
            f"//li[contains(@class,'select2-results__option') and "
            f"contains(normalize-space(text()),'{texto}')]"
        )

        for xpath in [xpath_opcao, xpath_opcao_parcial]:
            try:
                opcao = WebDriverWait(self.driver, config.TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                self.clicar_com_seguranca(opcao)
                return
            except Exception:
                continue

        raise RuntimeError(f"Opção '{texto}' não encontrada no Select2 '{nome_seletor}'")

    def selecionar_select2_por_xpath_container(self, xpath_container: str, texto: str) -> None:
        """Versão que recebe o XPath do container diretamente."""
        container = self.aguardar_seletor_xpath(xpath_container, "clicavel")
        self.clicar_com_seguranca(container)
        time.sleep(0.15)

        campo_busca = self._obter_campo_busca_select2_aberto(timeout=1)
        if campo_busca:
            try:
                campo_busca.send_keys(Keys.CONTROL, "a")
                campo_busca.send_keys(Keys.BACKSPACE)
                campo_busca.send_keys(texto)
                time.sleep(0.15)
            except Exception:
                pass

        xpath_opcao = (
            f"//li[contains(@class,'select2-results__option') and "
            f"normalize-space(text())='{texto}']"
        )
        opcao = WebDriverWait(self.driver, config.TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, xpath_opcao))
        )
        self.clicar_com_seguranca(opcao)

    def _obter_campo_busca_select2_aberto(self, timeout: Optional[int] = None) -> Optional[WebElement]:
        """Retorna o campo de busca do Select2 atualmente aberto, se existir."""
        limite = time.time() + (timeout or 2)
        seletores = [
            ".select2-container--open .select2-search__field",
            ".select2-dropdown .select2-search__field",
        ]

        while time.time() < limite:
            for seletor in seletores:
                try:
                    campos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                    for campo in campos:
                        if campo.is_displayed() and campo.is_enabled():
                            return campo
                except Exception:
                    continue
            time.sleep(0.05)

        return None

    def limpar_select2(self, nome_seletor: str) -> None:
        """Remove a seleção atual de um Select2 clicando no botão '×'."""
        try:
            botao_remover = self.aguardar_seletor(nome_seletor, "clicavel", timeout=5)
            self.clicar_com_seguranca(botao_remover)
            time.sleep(0.3)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def executar_script(self, script: str, *args) -> any:
        return self.driver.execute_script(script, *args)

    def obter_texto_elemento(self, elemento: WebElement) -> str:
        try:
            texto = elemento.text.strip()
            if not texto:
                texto = elemento.get_attribute("value") or ""
            return texto.strip()
        except Exception:
            return ""

    def elemento_visivel(self, elemento: WebElement) -> bool:
        try:
            return elemento.is_displayed()
        except Exception:
            return False

    def elemento_habilitado(self, elemento: WebElement) -> bool:
        try:
            return elemento.is_enabled() and not elemento.get_attribute("disabled")
        except Exception:
            return False

    def salvar_screenshot(self, nome: str) -> str:
        """Salva screenshot e retorna o caminho do arquivo."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{nome}_{timestamp}.png"
        caminho = SCREENSHOTS_DIR / nome_arquivo
        try:
            self.driver.save_screenshot(str(caminho))
        except Exception:
            pass
        return str(caminho)

    def enviar_tecla(self, tecla) -> None:
        try:
            ActionChains(self.driver).send_keys(tecla).perform()
        except Exception:
            pass

    def aguardar_texto_em_elemento(self, by: str, valor: str, texto: str, timeout: Optional[int] = None) -> None:
        t = timeout or config.TIMEOUT
        WebDriverWait(self.driver, t).until(
            EC.text_to_be_present_in_element((by, valor), texto)
        )
