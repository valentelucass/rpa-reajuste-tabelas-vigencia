"""
Page Object da tela de Reajuste (modal).
Responsabilidade: abas, selecao de taxa, valor, adicionar e salvar.
"""

import logging
import time
import unicodedata
from typing import Optional

import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.infraestrutura.acoes_navegador import AcoesNavegador


_XPATH_ABA: dict[str, str] = {
    "fee": "//li[@id='fee']",
    "overweights": "//li[@id='overweights']",
    "additionals": "//li[@id='additionals']",
}

_LABEL_ABA: dict[str, str] = {
    "fee": "Reajustar Taxas",
    "overweights": "Reajustar Excedentes",
    "additionals": "Reajustar Adicionais",
}


class PaginaReajuste:
    """Encapsula a interacao com o modal de reajuste de tabela."""

    def __init__(self, acoes: AcoesNavegador, logger: Optional[logging.Logger] = None) -> None:
        self.acoes = acoes
        self.logger = logger or logging.getLogger("rpa")
        self._aba_atual: Optional[str] = None

    def aguardar_modal(self) -> None:
        """Aguarda o modal de reajuste abrir."""
        self._obter_aba_visivel("fee", timeout=config.TIMEOUT)
        time.sleep(0.5)
        self._aba_atual = None
        self.logger.debug("Modal de reajuste aberto")

    def considerar_todos_trechos(self) -> None:
        """Clica no botao 'Considerar todos os trechos'."""
        xpath = "//button[.//span[contains(text(),'Considerar todos os trechos')]]"
        try:
            for botao in self.acoes.driver.find_elements(By.XPATH, xpath):
                try:
                    if botao.is_displayed() and botao.is_enabled():
                        self.acoes.clicar_com_seguranca(botao)
                        time.sleep(0.3)
                        self.logger.debug("Todos os trechos marcados")
                        return
                except Exception:
                    continue

            botao = self.acoes.aguardar_seletor_xpath(xpath, "clicavel", timeout=2)
            self.acoes.clicar_com_seguranca(botao)
            time.sleep(0.3)
            self.logger.debug("Todos os trechos marcados")
        except Exception as erro:
            self.logger.warning(f"Botao 'Considerar todos os trechos' nao encontrado: {erro}")

    def navegar_para_aba(self, aba_id: str, forcar_clique: bool = False) -> None:
        """Navega para a aba correta (fee / overweights / additionals)."""
        if self._aba_atual == aba_id and not forcar_clique:
            return

        label = _LABEL_ABA.get(aba_id, aba_id)

        try:
            aba, alvo = self._obter_aba_visivel(aba_id, timeout=10)
            classe = aba.get_attribute("class") or ""
            if forcar_clique or "active" not in classe:
                self.acoes.clicar_com_seguranca(alvo)
                time.sleep(0.4)
                WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                    lambda d: self._aba_esta_ativa(aba_id)
                )

            self._aba_atual = aba_id
            self.logger.debug(f"Aba ativa: {label}")

        except Exception as erro:
            raise RuntimeError(f"Nao foi possivel navegar para aba '{label}': {erro}")

    def selecionar_taxa(self, nome_taxa: str) -> None:
        """
        Seleciona a taxa pelo Select2 visivel.
        Se o componente visual falhar, cai para o select nativo como fallback.
        """
        try:
            container = self.acoes.aguardar_seletor_xpath(
                "//span[@id='select2-readjust_form_fee-container']"
                "/ancestor::span[contains(@class,'select2-selection')]",
                "clicavel",
                timeout=10,
            )
            self.acoes.clicar_com_seguranca(container)
            time.sleep(0.2)

            campo_busca = self.acoes._obter_campo_busca_select2_aberto(timeout=3)
            if campo_busca:
                campo_busca.clear()
                campo_busca.send_keys(nome_taxa)
                time.sleep(0.2)

            xpaths_opcao = [
                (
                    "//li[contains(@class,'select2-results__option') and "
                    f"normalize-space(.)='{nome_taxa}']"
                ),
                (
                    "//li[contains(@class,'select2-results__option') and "
                    f"contains(normalize-space(.),'{nome_taxa}')]"
                ),
            ]
            opcao = None
            for xpath_opcao in xpaths_opcao:
                try:
                    opcao = WebDriverWait(self.acoes.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath_opcao))
                    )
                    break
                except Exception:
                    continue
            if opcao is None:
                raise RuntimeError("Opcao da taxa nao apareceu no Select2")

            self.acoes.clicar_com_seguranca(opcao)
            WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                lambda d: self._taxa_visual_foi_selecionada(nome_taxa)
            )
            self.logger.debug(f"Taxa selecionada: {nome_taxa}")
            return
        except Exception as erro_visual:
            self.logger.warning(
                f"Selecao visual da taxa '{nome_taxa}' falhou ({erro_visual}). "
                "Tentando fallback pelo select nativo..."
            )

        try:
            select = self.acoes.aguardar_seletor_css(
                "select#readjust_form_fee",
                "presente",
                timeout=10,
            )
            valor = self._obter_valor_opcao_taxa(select, nome_taxa)
            self.acoes.executar_script(
                """
                const select = arguments[0];
                const value = arguments[1];
                select.value = value;
                if (window.jQuery) {
                    window.jQuery(select).val(value).trigger('change');
                }
                select.dispatchEvent(new Event('input', { bubbles: true }));
                select.dispatchEvent(new Event('change', { bubbles: true }));
                """,
                select,
                valor,
            )
            WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                lambda d: self._taxa_foi_selecionada(select, nome_taxa, valor)
            )
            self.logger.debug(f"Taxa selecionada: {nome_taxa}")
        except Exception as erro:
            raise RuntimeError(f"Erro ao selecionar taxa '{nome_taxa}': {erro}")

    def definir_valor(self, percentual: float) -> None:
        """Preenche o campo de valor com o percentual formatado."""
        valor_str = f"{percentual:.2f}".replace(".", ",").rstrip("0").rstrip(",")
        campo = self._obter_campo_valor_visivel()
        self.acoes.limpar_e_digitar(campo, valor_str)
        time.sleep(0.2)
        self.logger.debug(f"Valor definido: {valor_str}")

    def clicar_adicionar(self) -> None:
        """Clica no botao Adicionar (aguarda estar habilitado primeiro)."""
        xpath_botao = "//button[@name='add_fee' and not(@disabled)]"
        try:
            botao = WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, xpath_botao))
            )
            self.acoes.clicar_com_seguranca(botao)
            time.sleep(0.5)
            self.logger.debug("Taxa adicionada")
        except Exception as erro:
            raise RuntimeError(f"Botao Adicionar nao ficou disponivel: {erro}")

    def salvar(self) -> None:
        """Clica no botao Salvar do modal de reajuste."""
        botao = self.acoes.aguardar_seletor("botao_salvar_reajuste", "clicavel")
        self.acoes.clicar_com_seguranca(botao)
        time.sleep(0.5)
        self.logger.debug("Reajuste salvo")

    def confirmar_modal_ok(self) -> None:
        """Confirma os popups SweetAlert exibidos apos salvar o reajuste."""
        try:
            etapas_confirmadas: list[str] = []
            popup = self._aguardar_popup_confirmacao(timeout=20)

            for _ in range(3):
                descricao = self._descrever_popup_confirmacao(popup)
                self._clicar_confirmacao_popup(popup)
                self._aguardar_popup_sumir(popup, timeout=10)
                etapas_confirmadas.append(descricao)
                popup = self._aguardar_popup_confirmacao(timeout=3, obrigatorio=False)
                if popup is None:
                    break

            if not etapas_confirmadas:
                raise RuntimeError("Nenhum popup SweetAlert foi confirmado apos salvar.")

            self.logger.debug(
                "Fluxo de confirmacao do Swal concluido: %s",
                " -> ".join(etapas_confirmadas),
            )
        except Exception as erro:
            raise RuntimeError(
                f"Nao foi possivel confirmar o popup apos salvar: {erro}"
            )

    def fechar_modal(self) -> None:
        """Fecha o modal de reajuste priorizando o botao X do cabecalho."""
        seletores = [
            "button.close",
            "a[name='close_modal_button']",
            "a[data-dismiss='modal']",
            "button[data-dismiss='modal']",
        ]
        ultima_excecao: Optional[Exception] = None

        try:
            WebDriverWait(self.acoes.driver, 3).until(
                lambda d: any(
                    botao.is_displayed()
                    for botao in d.find_elements(By.CSS_SELECTOR, "button.close")
                )
            )
            time.sleep(0.5)
        except Exception:
            time.sleep(0.3)

        for css in seletores:
            try:
                botoes = self.acoes.driver.find_elements(By.CSS_SELECTOR, css)
                for botao in botoes:
                    if botao.is_displayed():
                        self.acoes.clicar_com_seguranca(botao)
                        self.aguardar_modal_fechado()
                        self._aba_atual = None
                        self.logger.debug(f"Modal de reajuste fechado via seletor {css}")
                        return
            except Exception as erro:
                ultima_excecao = erro

        raise RuntimeError(
            f"Nao foi possivel fechar o modal de reajuste pelo X/botao de fechar: {ultima_excecao}"
        )

    def aguardar_modal_fechado(self) -> None:
        """Aguarda o modal de reajuste desaparecer."""
        self.acoes.aguardar_invisibilidade_css(
            "ul.nav.nav-tabs li#fee",
            timeout=config.TIMEOUT,
        )
        time.sleep(0.3)

    def _obter_valor_opcao_taxa(self, select, nome_taxa: str) -> str:
        """Mapeia o texto da taxa para o value do option correspondente."""
        nome_normalizado = self._normalizar_texto(nome_taxa)
        opcoes = select.find_elements(By.TAG_NAME, "option")
        for opcao in opcoes:
            if self._normalizar_texto(opcao.text) == nome_normalizado:
                return opcao.get_attribute("value") or ""
        for opcao in opcoes:
            if nome_normalizado and nome_normalizado in self._normalizar_texto(opcao.text):
                return opcao.get_attribute("value") or ""
        raise RuntimeError(f"Opcao de taxa '{nome_taxa}' nao encontrada no Select")

    def _taxa_foi_selecionada(self, select, nome_taxa: str, valor: str) -> bool:
        """Valida que o valor foi aplicado ao campo e refletido no Select2."""
        try:
            if (select.get_attribute("value") or "") == valor:
                return True
        except Exception:
            pass

        try:
            texto = self._obter_texto_select2_visivel()
            return self._normalizar_texto(texto) == self._normalizar_texto(nome_taxa)
        except Exception:
            return False

    def _taxa_visual_foi_selecionada(self, nome_taxa: str) -> bool:
        """Confere o texto atual renderizado no Select2."""
        try:
            texto = self._obter_texto_select2_visivel()
            texto_normalizado = self._normalizar_texto(texto).replace("x ", "").strip()
            nome_normalizado = self._normalizar_texto(nome_taxa)
            return nome_normalizado in texto_normalizado
        except Exception:
            return False

    def _obter_aba_visivel(self, aba_id: str, timeout: int):
        """Retorna a aba visivel atual e o alvo clicavel associado."""
        return WebDriverWait(self.acoes.driver, timeout).until(
            lambda d: self._resolver_aba_visivel(aba_id) or False
        )

    def _resolver_aba_visivel(self, aba_id: str):
        """Resolve a aba visivel por texto e fallback por id do li."""
        label = _LABEL_ABA.get(aba_id, aba_id)
        xpaths = [
            f"//a[contains(@class,'btn') and normalize-space(.)='{label}']",
            f"//li[@id='{aba_id}']//a[contains(@class,'btn')]",
            _XPATH_ABA.get(aba_id, _XPATH_ABA["fee"]),
        ]

        for xpath in xpaths:
            elementos = self.acoes.driver.find_elements(By.XPATH, xpath)
            for elemento in reversed(elementos):
                try:
                    if not elemento.is_displayed():
                        continue
                    if (elemento.tag_name or "").lower() == "li":
                        aba = elemento
                        try:
                            alvo = elemento.find_element(By.CSS_SELECTOR, "a.btn")
                        except Exception:
                            alvo = elemento
                    else:
                        alvo = elemento
                        try:
                            aba = elemento.find_element(By.XPATH, "./ancestor::li[1]")
                        except Exception:
                            aba = elemento

                    if aba.is_displayed():
                        return aba, alvo
                except Exception:
                    continue
        return None

    def _aba_esta_ativa(self, aba_id: str) -> bool:
        """Confere se a aba visivel atual ficou ativa apos o clique."""
        resolvida = self._resolver_aba_visivel(aba_id)
        if not resolvida:
            return False
        aba, _alvo = resolvida
        try:
            return "active" in (aba.get_attribute("class") or "")
        except Exception:
            return False

    def _obter_texto_select2_visivel(self) -> str:
        """Retorna o texto do container Select2 visivel do modal atual."""
        elementos = self.acoes.driver.find_elements(
            By.ID,
            "select2-readjust_form_fee-container",
        )
        for elemento in reversed(elementos):
            try:
                if elemento.is_displayed():
                    return elemento.text
            except Exception:
                continue
        raise RuntimeError("Container Select2 visivel da taxa nao encontrado.")

    def _obter_campo_valor_visivel(self):
        """Retorna o input de valor visivel da aba atual."""
        campos = self.acoes.driver.find_elements(
            By.CSS_SELECTOR,
            "input[name='readjust_form[value]']",
        )
        for campo in campos:
            try:
                if campo.is_displayed() and campo.is_enabled():
                    return campo
            except Exception:
                continue
        return self.acoes.aguardar_seletor("input_valor_reajuste_modal", "visivel")

    def _aguardar_popup_confirmacao(
        self, timeout: int, obrigatorio: bool = True
    ):
        """Aguarda um popup SweetAlert visivel com botao de confirmacao."""
        try:
            return WebDriverWait(self.acoes.driver, timeout).until(
                lambda d: self._obter_popup_confirmacao_visivel()
            )
        except Exception:
            if obrigatorio:
                raise
            return None

    def _clicar_confirmacao_popup(self, popup) -> None:
        """Clica no botao principal do SweetAlert usando fallback JS se necessario."""
        botao = self._obter_botao_confirmar_popup(popup)
        try:
            self.acoes.clicar_com_seguranca(botao)
        except Exception:
            self.acoes.executar_script("arguments[0].click()", botao)
        time.sleep(0.2)

    def _aguardar_popup_sumir(self, popup, timeout: int) -> None:
        """Aguarda o popup atual sair da tela antes do proximo passo."""
        WebDriverWait(self.acoes.driver, timeout).until(
            lambda d: self._popup_foi_fechado(popup)
        )

    def _popup_foi_fechado(self, popup) -> bool:
        try:
            return not popup.is_displayed()
        except Exception:
            return True

    def _obter_botao_confirmar_popup(self, popup):
        """Localiza o botao principal do popup SweetAlert."""
        try:
            return popup.find_element(
                By.CSS_SELECTOR, "button#swal-confirm.swal2-confirm"
            )
        except Exception:
            return popup.find_element(By.CSS_SELECTOR, "button.swal2-confirm")

    def _descrever_popup_confirmacao(self, popup) -> str:
        """Classifica o popup para fins de log e validacao."""
        texto = self._normalizar_texto(popup.text)
        if "confirma reajuste das taxas" in texto or "atencao" in texto:
            return "sim_confirmacao"
        if "reajuste aplicado" in texto or "sucesso" in texto:
            return "ok_sucesso"
        return "confirmacao_generica"

    def _obter_popup_confirmacao_visivel(self):
        """Retorna o SweetAlert visivel com botao de confirmacao, se existir."""
        popups = self.acoes.driver.find_elements(By.CSS_SELECTOR, "div.swal2-popup.swal2-modal")
        for popup in reversed(popups):
            try:
                if not popup.is_displayed():
                    continue
                self._obter_botao_confirmar_popup(popup)
                return popup
            except Exception:
                continue
        return None

    def _normalizar_texto(self, valor: str) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or ""))
        texto = "".join(
            caractere for caractere in texto if not unicodedata.combining(caractere)
        )
        return " ".join(texto.lower().split())
