"""
Facade sobre o Selenium. Centraliza waits, localizacao, clique e digitacao.
Versao simplificada e independente para o script de exclusao.
"""

import logging
import time
from datetime import datetime
from typing import Optional

try:
    from . import config
except ImportError:  # pragma: no cover - compatibilidade standalone
    from auto_delete_compat import carregar_modulo_local

    config = carregar_modulo_local("config")
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class AcoesNavegador:
    """Facade de interacao com o browser."""

    def __init__(self, driver, logger: Optional[logging.Logger] = None) -> None:
        self.driver = driver
        self.logger = logger or logging.getLogger("auto_delete_clientes")

    # ------------------------------------------------------------------
    # Waits de documento e overlay
    # ------------------------------------------------------------------

    def aguardar_documento_pronto(self, timeout: Optional[int] = None) -> None:
        """Aguarda document.readyState == 'complete'."""
        t = timeout or config.PAGE_LOAD_TIMEOUT
        WebDriverWait(self.driver, t).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def aguardar_carregamento_finalizar(self, timeout: Optional[int] = None, ignorar_swal: bool = False) -> None:
        """Aguarda ausencia de overlays, spinners e modais.
        Se ignorar_swal=True, nao espera .swal2-container (usar quando
        o toast de sucesso ja foi gerenciado explicitamente)."""
        t = timeout or config.TIMEOUT
        seletores_overlay = [
            ".loading", ".spinner", ".overlay",
            "[class*='loading']", "[class*='spinner']",
        ]
        if not ignorar_swal:
            seletores_overlay.append(".swal2-container")
        for seletor in seletores_overlay:
            try:
                WebDriverWait(self.driver, min(t, 10)).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, seletor))
                )
            except Exception:
                pass
        WebDriverWait(self.driver, t).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def aguardar_tabela_estavel(self, timeout: int = 15) -> None:
        """Bloqueia ate a tabela estar estavel: sem modais, sem spinners,
        readyState complete, e contagem de linhas estavel por 0.5s."""
        self.logger.info("Aguardando atualizacao da tabela...")

        # Fase 1: sem modais, sem overlays, readyState complete
        self.aguardar_carregamento_finalizar(timeout)

        # Fase 2: contagem de linhas estavel (2 leituras com 0.5s de intervalo)
        def _linhas_estaveis(driver):
            try:
                linhas1 = len(driver.find_elements(By.CSS_SELECTOR, "tr.vue-item"))
                time.sleep(0.5)
                linhas2 = len(driver.find_elements(By.CSS_SELECTOR, "tr.vue-item"))
                return linhas1 == linhas2
            except Exception:
                return False

        try:
            WebDriverWait(self.driver, timeout).until(_linhas_estaveis)
        except Exception:
            self.logger.warning("Tabela pode nao ter estabilizado dentro do timeout")

        self.logger.info("Tabela atualizada com sucesso")

    # ------------------------------------------------------------------
    # Localizacao por nome de seletor
    # ------------------------------------------------------------------

    _MAPA_BY = {
        "id": By.ID,
        "css selector": By.CSS_SELECTOR,
        "xpath": By.XPATH,
        "name": By.NAME,
        "class name": By.CLASS_NAME,
        "tag name": By.TAG_NAME,
    }

    def _by_para_selenium(self, tipo: str) -> str:
        return self._MAPA_BY.get(tipo.lower(), By.XPATH)

    def aguardar_seletor(
        self,
        nome: str,
        condicao: str = "visivel",
        timeout: Optional[int] = None,
        contexto: Optional[WebElement] = None,
    ) -> WebElement:
        """Aguarda e retorna elemento pelos seletores nomeados em config.SELETORES."""
        t = timeout or config.TIMEOUT
        seletores = config.SELETORES.get(nome)
        if not seletores:
            raise ValueError(f"Seletor '{nome}' nao encontrado em config.SELETORES")

        ultima_excecao: Exception = RuntimeError(f"Seletor '{nome}' nao encontrado")

        for tipo, valor in seletores:
            by = self._by_para_selenium(tipo)
            try:
                if contexto:
                    elemento = contexto.find_element(by, valor)
                    WebDriverWait(self.driver, t).until(lambda d: elemento.is_displayed())
                    return elemento
                else:
                    if condicao == "visivel":
                        cond = EC.visibility_of_element_located((by, valor))
                    elif condicao == "clicavel":
                        cond = EC.element_to_be_clickable((by, valor))
                    else:
                        cond = EC.presence_of_element_located((by, valor))
                    return WebDriverWait(self.driver, t).until(cond)
            except Exception as e:
                ultima_excecao = e
                continue

        raise ultima_excecao

    def aguardar_seletor_xpath(
        self, xpath: str, condicao: str = "visivel", timeout: Optional[int] = None
    ) -> WebElement:
        """Aguarda elemento por XPath direto."""
        t = timeout or config.TIMEOUT
        if condicao == "clicavel":
            return WebDriverWait(self.driver, t).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
        return WebDriverWait(self.driver, t).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
        )

    def aguardar_seletor_css(
        self, css: str, condicao: str = "visivel", timeout: Optional[int] = None
    ) -> WebElement:
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
        """Aguarda elemento CSS ficar invisivel."""
        t = timeout or config.TIMEOUT
        WebDriverWait(self.driver, t).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, css))
        )

    # ------------------------------------------------------------------
    # Clique seguro + debug visual
    # ------------------------------------------------------------------

    def destacar_elemento(self, elemento: WebElement, cor: str = "red", duracao: float = 0.4) -> None:
        """Aplica borda colorida temporaria no elemento para debug visual."""
        if not config.DEBUG_VISUAL:
            return
        try:
            self.executar_script(
                """
                const el = arguments[0];
                const corOriginal = el.style.border;
                el.style.border = '3px solid ' + arguments[1];
                setTimeout(() => { el.style.border = corOriginal; }, arguments[2]);
                """,
                elemento,
                cor,
                int(duracao * 1000),
            )
            time.sleep(duracao)
        except Exception:
            pass

    def clicar_com_seguranca(self, elemento: WebElement) -> None:
        """scrollIntoView + highlight + click, com fallback para JS click."""
        self._scroll_para_elemento(elemento)
        self.destacar_elemento(elemento, "red", 0.3)
        try:
            elemento.click()
        except Exception:
            self.executar_script("arguments[0].click()", elemento)

    def _scroll_para_elemento(self, elemento: WebElement) -> None:
        try:
            self.executar_script(
                "arguments[0].scrollIntoView({block:'center', inline:'nearest'})",
                elemento,
            )
            time.sleep(0.05)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Digitacao
    # ------------------------------------------------------------------

    def limpar_e_digitar(self, elemento: WebElement, texto: str) -> None:
        """Limpa o campo com Ctrl+A + Backspace e digita o texto."""
        self._scroll_para_elemento(elemento)
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
        """Interage com um Select2: clica no container, digita e seleciona a opcao."""
        container = self.aguardar_seletor(nome_seletor, "clicavel")
        self.clicar_com_seguranca(container)
        time.sleep(0.15)

        # Digitar no campo de busca do Select2 aberto
        campo_busca = self._obter_campo_busca_select2_aberto(timeout=2)
        if campo_busca:
            try:
                campo_busca.send_keys(Keys.CONTROL, "a")
                campo_busca.send_keys(Keys.BACKSPACE)
                campo_busca.send_keys(texto)
                time.sleep(0.15)
            except Exception:
                pass

        # Localizar e clicar na opcao
        xpath_exato = (
            f"//li[contains(@class,'select2-results__option') and "
            f"normalize-space(text())='{texto}']"
        )
        xpath_parcial = (
            f"//li[contains(@class,'select2-results__option') and "
            f"contains(normalize-space(text()),'{texto}')]"
        )
        for xpath in [xpath_exato, xpath_parcial]:
            try:
                opcao = WebDriverWait(self.driver, config.TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                self.clicar_com_seguranca(opcao)
                return
            except Exception:
                continue

        raise RuntimeError(f"Opcao '{texto}' nao encontrada no Select2 '{nome_seletor}'")

    def _obter_campo_busca_select2_aberto(self, timeout: int = 2) -> Optional[WebElement]:
        """Retorna o campo de busca do Select2 atualmente aberto."""
        limite = time.time() + timeout
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

    # ------------------------------------------------------------------
    # Utilitarios
    # ------------------------------------------------------------------

    def executar_script(self, script: str, *args):
        return self.driver.execute_script(script, *args)

    def elemento_visivel(self, elemento: WebElement) -> bool:
        try:
            return elemento.is_displayed()
        except Exception:
            return False

    def salvar_screenshot(self, nome: str) -> str:
        """Salva screenshot e retorna o caminho do arquivo."""
        config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{nome}_{timestamp}.png"
        caminho = config.SCREENSHOTS_DIR / nome_arquivo
        try:
            self.driver.save_screenshot(str(caminho))
        except Exception:
            pass
        return str(caminho)
