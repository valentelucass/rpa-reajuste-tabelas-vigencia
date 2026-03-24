"""
Page Object da tela de Tabelas de Cliente.
Responsabilidade: navegacao, filtros, pesquisa, listagem, paginacao e acoes de linha.
"""

import logging
import re
import time
import unicodedata
from datetime import datetime
from typing import Optional

import config
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.infraestrutura.acoes_navegador import AcoesNavegador


class PaginaTabelasCliente:
    """Encapsula toda a interacao com a listagem de tabelas de cliente."""

    def __init__(self, acoes: AcoesNavegador, logger: Optional[logging.Logger] = None) -> None:
        self.acoes = acoes
        self.logger = logger or logging.getLogger("rpa")
        self._ultima_linha_dropdown: Optional[WebElement] = None

    # ------------------------------------------------------------------
    # Navegacao
    # ------------------------------------------------------------------

    def acessar(self) -> None:
        """Navega ate a tela de tabelas de cliente."""
        self.logger.info("Navegando para Tabelas de Cliente...")
        try:
            self.acessar_por_url()
            return
        except Exception as erro:
            self.logger.warning(f"Acesso direto falhou ({erro}). Tentando via menu...")

        menu = self.acoes.aguardar_seletor("menu_cadastros", "clicavel")
        self.acoes.clicar_com_seguranca(menu)
        time.sleep(0.2)

        sub_menu = self.acoes.aguardar_seletor("menu_tabelas_preco", "clicavel")
        self.acoes.clicar_com_seguranca(sub_menu)
        time.sleep(0.2)

        item = self.acoes.aguardar_seletor("menu_tabelas_cliente", "clicavel")
        self.acoes.clicar_com_seguranca(item)

        self.acoes.aguardar_documento_pronto()
        self.acoes.aguardar_carregamento_finalizar()

    def acessar_por_url(self) -> None:
        """Acesso direto por URL, mais rapido que navegar pelo menu."""
        self.acoes.driver.get("https://rodogarcia.eslcloud.com.br/customer_price_tables")
        self.acoes.aguardar_documento_pronto()
        self.acoes.aguardar_carregamento_finalizar()

    # ------------------------------------------------------------------
    # Filtros - Fase 1
    # ------------------------------------------------------------------

    def preparar_filtros_fase_um(self) -> None:
        """Remove a filial e define Ativa = Sim.
        Idempotente: verifica estado antes de agir para evitar reload desnecessario.
        """
        filial_tinha_selecao = self._limpar_filtro_filial()
        ativa_ja_correta = self._ativa_ja_selecionada_sim()

        if not ativa_ja_correta:
            self._filtrar_ativa_sim()

        if filial_tinha_selecao or not ativa_ja_correta:
            self.acoes.aguardar_carregamento_finalizar()

    def preparar_estado_listagem(self) -> None:
        """Garante baseline consistente da listagem com filtros padrão da Fase 1.
        Idempotente: pode ser chamado várias vezes sem quebrar o estado.
        Nao recarrega a pagina se ja estiver na listagem — apenas reaplica filtros.
        """
        if not self._ja_esta_na_listagem():
            self.acessar()
        self.preparar_filtros_fase_um()

    def preparar_estado_listagem_fase_dois(self, data_inicio: str, data_fim: str) -> None:
        """Garante baseline consistente da listagem antes de executar a Fase 2."""
        self.acessar()
        self._limpar_filtro_filial()
        if not self._ativa_ja_selecionada_sim():
            self._filtrar_ativa_sim()
        self.preparar_filtros_fase_dois(data_inicio, data_fim)

    def _limpar_filtro_filial(self) -> bool:
        """Remove a selecao atual de Filial Responsavel, se existir.
        Retorna True se havia selecao e foi removida.
        """
        try:
            grupo_filial = self.acoes.driver.find_element(
                By.ID, "search_price_tables_corporation_id"
            ).find_element(
                By.XPATH, "./ancestor::div[contains(@class,'form-group')][1]"
            )
            botoes_remover = grupo_filial.find_elements(
                By.CSS_SELECTOR, ".select2-selection__choice__remove"
            )
            removeu = False
            for botao in botoes_remover:
                if botao.is_displayed():
                    self.acoes.clicar_com_seguranca(botao)
                    time.sleep(0.15)
                    removeu = True
            return removeu
        except Exception:
            return False

    def _filtrar_ativa_sim(self) -> None:
        """Seleciona Sim no filtro de Ativa."""
        try:
            self.acoes.selecionar_select2("container_select2_ativa", "Sim")
        except Exception as erro:
            self.logger.warning(f"Nao foi possivel filtrar Ativa=Sim: {erro}")

    def _ativa_ja_selecionada_sim(self) -> bool:
        """Verifica se o filtro Ativa ja esta selecionado como 'Sim'."""
        try:
            container = self.acoes.aguardar_seletor(
                "container_select2_ativa", "presente", timeout=3
            )
            selecao = container.find_element(
                By.CSS_SELECTOR, ".select2-selection__rendered"
            )
            # Usar title (confiavel) pois .text inclui o "x" do botao limpar
            texto = (selecao.get_attribute("title") or "").strip().lower()
            return texto == "sim"
        except Exception:
            return False

    def _ja_esta_na_listagem(self) -> bool:
        """Verifica se ja esta na pagina de listagem de tabelas sem navegar."""
        try:
            url_atual = self.acoes.driver.current_url or ""
            if "customer_price_tables" not in url_atual:
                return False
            self.acoes.driver.find_element(By.CSS_SELECTOR, ".vue-paginated-table")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Pesquisa por nome
    # ------------------------------------------------------------------

    def pesquisar_por_nome(self, nome: str) -> None:
        """Preenche o campo de nome e dispara a pesquisa."""
        input_nome = self.acoes.aguardar_seletor("input_pesquisa_nome", "visivel")
        self.acoes.limpar_e_digitar(input_nome, nome)
        time.sleep(0.2)
        self._garantir_nome_digitado(input_nome, nome)

        self._clicar_botao_pesquisar(input_nome)
        self.acoes.aguardar_carregamento_finalizar()

    def limpar_pesquisa_nome(self) -> None:
        """Limpa o campo de pesquisa por nome."""
        try:
            input_nome = self.acoes.aguardar_seletor("input_pesquisa_nome", "visivel", timeout=5)
            valor_atual = (input_nome.get_attribute("value") or "").strip()
            if not valor_atual:
                return

            self.acoes.executar_script(
                """
                const input = arguments[0];
                input.value = '';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                """,
                input_nome,
            )
        except Exception:
            pass

    def aguardar_resultado_pesquisa(self) -> None:
        """Aguarda a grid estabilizar apos a pesquisa."""
        time.sleep(0.5)
        self.acoes.aguardar_carregamento_finalizar()

    def validar_resultado_encontrado(self, nome: str) -> None:
        """Valida que a pesquisa retornou ao menos uma linha."""
        if not self.obter_linhas_tabela():
            raise RuntimeError(
                f"Tabela '{nome}' nao encontrada na pesquisa. "
                "Verifique o nome no Excel e os filtros aplicados."
            )

    def localizar_linha_por_nome_exato(self, nome: str) -> WebElement:
        """
        Localiza a linha cujo nome bate exatamente com o nome do Excel.
        Isso evita duplicar uma linha '- Copia' existente.
        """
        nome_alvo = nome.strip()
        candidatas: list[WebElement] = []

        for linha in self.obter_linhas_tabela():
            nome_linha = self.extrair_nome_linha(linha).strip()
            if nome_linha == nome_alvo:
                return linha
            if nome_linha.rstrip() == nome_alvo:
                candidatas.append(linha)

        if candidatas:
            return candidatas[0]

        raise RuntimeError(
            f"Tabela exata '{nome_alvo}' nao encontrada na listagem apos a pesquisa."
        )

    def _clicar_botao_pesquisar(self, input_nome: WebElement) -> None:
        """Clica no botao visivel de pesquisa da listagem, com fallback por Enter."""
        try:
            botao = self.acoes.aguardar_seletor("botao_pesquisar", "clicavel", timeout=5)
            self.acoes.clicar_com_seguranca(botao)
            return
        except Exception:
            pass

        try:
            formulario = input_nome.find_element(By.XPATH, "./ancestor::form[1]")
            botao = formulario.find_element(
                By.XPATH,
                ".//button[@id='submit' and contains(@class,'btn-sm') "
                "and not(contains(@class,'btn-align-input')) and .//i[contains(@class,'fa-search')]]",
            )
            self.acoes.clicar_com_seguranca(botao)
            return
        except Exception:
            pass

        input_nome.send_keys(Keys.ENTER)

    # ------------------------------------------------------------------
    # Filtros - Fase 2
    # ------------------------------------------------------------------

    def preparar_filtros_fase_dois(self, data_inicio: str, data_fim: str) -> None:
        """
        Filtra as copias pelo intervalo de vigencia para isolar o que foi criado.
        """
        self.limpar_pesquisa_nome()
        self._expandir_filtros_avancados()
        self._preencher_daterangepicker(data_inicio, data_fim)
        input_nome = self.acoes.aguardar_seletor("input_pesquisa_nome", "visivel", timeout=5)
        self._clicar_botao_pesquisar(input_nome)
        self.acoes.aguardar_carregamento_finalizar()
        if not self.validar_filtro_vigencia_aplicado(data_inicio, data_fim):
            raise RuntimeError(
                "Filtro de vigencia nao ficou aplicado corretamente. "
                f"Esperado: {data_inicio} - {data_fim}"
            )
        self.logger.info(f"Filtro de vigencia aplicado: {data_inicio} - {data_fim}")

    def garantir_contexto_fase_dois(self, data_inicio: str, data_fim: str) -> bool:
        """Garante filtro de vigencia valido e campo Nome limpo antes da pesquisa."""
        filtro_reaplicado = False

        if data_inicio and data_fim and not self.validar_filtro_vigencia_aplicado(data_inicio, data_fim):
            self.logger.warning(
                "Filtro de vigencia perdido antes da pesquisa. "
                f"Reaplicando {data_inicio} - {data_fim}."
            )
            self.preparar_filtros_fase_dois(data_inicio, data_fim)
            filtro_reaplicado = True
        else:
            self.limpar_pesquisa_nome()
            self.acoes.aguardar_carregamento_finalizar()

        if data_inicio and data_fim and not self.validar_filtro_vigencia_aplicado(data_inicio, data_fim):
            raise RuntimeError(
                "Filtro de vigencia nao esta aplicado antes de pesquisar a proxima tabela. "
                f"Esperado: {data_inicio} - {data_fim}"
            )

        return filtro_reaplicado

    def obter_valor_filtro_vigencia(self) -> str:
        """Retorna o valor atual exibido no campo de vigencia."""
        try:
            campo = self.acoes.aguardar_seletor("input_vigencia_fim", "presente", timeout=5)
            return (campo.get_attribute("value") or campo.text or "").strip()
        except Exception:
            return ""

    def validar_filtro_vigencia_aplicado(self, data_inicio: str, data_fim: str) -> bool:
        """Confere se o valor exibido no input corresponde ao intervalo esperado."""
        valor_atual = self.obter_valor_filtro_vigencia()
        return self.intervalo_vigencia_corresponde(valor_atual, data_inicio, data_fim)

    def ha_resultados_filtrados(self) -> bool:
        """Indica se a grid possui ao menos um resultado apos o filtro."""
        return self.obter_total_tabelas() > 0 or bool(self.obter_linhas_tabela())

    def _normalizar_intervalo_vigencia(self, valor: str) -> str:
        """Normaliza o intervalo removendo espacos e separadores."""
        datas = self._extrair_datas_intervalo(valor)
        if datas:
            return "".join(self._normalizar_data_intervalo(data) for data in datas[:2])
        return "".join(caractere for caractere in str(valor or "") if caractere.isdigit())

    def intervalo_vigencia_corresponde(self, valor: str, data_inicio: str, data_fim: str) -> bool:
        """Compara intervalos aceitando ano com 2 ou 4 digitos."""
        esperado = self._normalizar_intervalo_vigencia(f"{data_inicio} - {data_fim}")
        atual = self._normalizar_intervalo_vigencia(valor)
        return bool(esperado and atual and esperado == atual)

    def _extrair_datas_intervalo(self, valor: str) -> list[str]:
        """Extrai datas dd/mm/aa ou dd/mm/aaaa de um texto livre."""
        return re.findall(r"\d{2}/\d{2}/\d{2,4}", str(valor or ""))

    def _normalizar_data_intervalo(self, valor: str) -> str:
        """Converte datas com ano curto ou longo para ddmmaaaa."""
        texto = str(valor or "").strip()
        for formato in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(texto, formato).strftime("%d%m%Y")
            except ValueError:
                continue
        return "".join(caractere for caractere in texto if caractere.isdigit())

    def _garantir_nome_digitado(self, input_nome: WebElement, nome: str) -> None:
        """Garante que o campo Nome refletiu exatamente o valor esperado."""
        if self._nome_digitado_confere(input_nome, nome):
            return

        self.logger.warning(
            f"Campo Nome nao refletiu '{nome}' apos digitacao. Aplicando fallback por script."
        )
        self.acoes.executar_script(
            """
            const input = arguments[0];
            const valor = arguments[1];
            input.value = valor;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            input_nome,
            nome,
        )
        time.sleep(0.1)

        if not self._nome_digitado_confere(input_nome, nome):
            valor_atual = (input_nome.get_attribute("value") or "").strip()
            raise RuntimeError(
                f"Campo Nome nao ficou com o valor esperado. "
                f"Esperado: '{nome}' | Atual: '{valor_atual or 'vazio'}'"
            )

    def _nome_digitado_confere(self, input_nome: WebElement, nome: str) -> bool:
        """Valida se o valor atual do input Nome bate com o valor esperado."""
        valor_atual = (input_nome.get_attribute("value") or "").strip()
        return self._normalizar_nome(valor_atual) == self._normalizar_nome(nome)

    def _normalizar_nome(self, valor: str) -> str:
        """Normaliza o nome para comparacao robusta."""
        return " ".join((valor or "").strip().upper().split())

    def _expandir_filtros_avancados(self) -> None:
        """Expande a area de filtros para exibir o calendario de vigencia."""
        try:
            botao = self.acoes.aguardar_seletor_xpath(
                "//button[contains(@class,'vue-button') and .//i[contains(@class,'fa-angle')]]",
                "clicavel",
                timeout=5,
            )
            self.acoes.clicar_com_seguranca(botao)
            time.sleep(0.4)
        except Exception:
            self.logger.debug("Filtros avancados ja visiveis ou botao nao encontrado")

    def _preencher_daterangepicker(self, data_inicio: str, data_fim: str) -> None:
        """Preenche o daterangepicker com a vigencia do Excel."""
        try:
            input_vigencia = self.acoes.aguardar_seletor("input_vigencia_fim", "clicavel", timeout=10)
            self.acoes.clicar_com_seguranca(input_vigencia)
            time.sleep(0.4)

            WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, ".daterangepicker.active, .daterangepicker[style*='display: block']")
                )
            )
            time.sleep(0.2)

            try:
                input_inicio = self.acoes.driver.find_element(
                    By.CSS_SELECTOR, "input[name='daterangepicker_start']"
                )
                self.acoes.limpar_e_digitar(input_inicio, data_inicio)
                time.sleep(0.1)

                input_fim = self.acoes.driver.find_element(
                    By.CSS_SELECTOR, "input[name='daterangepicker_end']"
                )
                self.acoes.limpar_e_digitar(input_fim, data_fim)
                time.sleep(0.1)
            except Exception:
                self.acoes.limpar_e_digitar(input_vigencia, f"{data_inicio} - {data_fim}")

            botao_confirmar = self.acoes.aguardar_seletor_css("button.applyBtn", "clicavel")
            self.acoes.clicar_com_seguranca(botao_confirmar)
            time.sleep(0.3)

        except Exception as erro:
            self.logger.warning(f"Erro ao preencher daterangepicker: {erro}")
            raise RuntimeError(
                f"Nao foi possivel preencher o filtro de vigencia {data_inicio} - {data_fim}"
            ) from erro

    # ------------------------------------------------------------------
    # Leitura da tabela
    # ------------------------------------------------------------------

    def obter_linhas_tabela(self) -> list[WebElement]:
        """Retorna apenas as linhas visiveis da grid."""
        time.sleep(0.3)
        try:
            linhas = self.acoes.driver.find_elements(By.CSS_SELECTOR, "tr.vue-item")
            return [linha for linha in linhas if linha.is_displayed()]
        except Exception:
            return []

    def extrair_assinatura_linha(self, linha: WebElement) -> str:
        """Gera uma assinatura textual da linha para relocalizacao."""
        try:
            colunas = linha.find_elements(By.CSS_SELECTOR, "td div.table-text")
            textos = [coluna.get_attribute("title") or coluna.text for coluna in colunas[:6]]
            return " | ".join(texto.strip() for texto in textos if texto.strip())
        except Exception:
            return linha.get_attribute("data-id") or ""

    def extrair_nome_linha(self, linha: WebElement) -> str:
        """Extrai o nome da tabela da primeira coluna."""
        try:
            coluna_nome = linha.find_element(By.CSS_SELECTOR, "td:first-child div.table-text")
            return (coluna_nome.get_attribute("title") or coluna_nome.text).strip()
        except Exception:
            return ""

    def extrair_data_id_linha(self, linha: WebElement) -> str:
        """Retorna o data-id da linha."""
        return linha.get_attribute("data-id") or ""

    def extrair_vigencia_linha(self, linha: WebElement) -> str:
        """Extrai o intervalo de vigencia exibido na linha, quando presente."""
        try:
            colunas = linha.find_elements(By.CSS_SELECTOR, "td div.table-text")
            for coluna in colunas:
                texto = (coluna.get_attribute("title") or coluna.text or "").strip()
                if self._extrair_datas_intervalo(texto):
                    return texto
        except Exception:
            pass
        return ""

    def validar_linha_para_reajuste(
        self,
        linha: WebElement,
        nome_esperado: str,
        data_inicio: str = "",
        data_fim: str = "",
    ) -> str:
        """Confere se a linha localizada bate com nome e vigencia esperados."""
        nome_linha = self.extrair_nome_linha(linha).strip()
        if self._normalizar_nome(nome_linha) != self._normalizar_nome(nome_esperado):
            raise RuntimeError(
                f"Linha localizada nao corresponde ao nome esperado. "
                f"Esperado: '{nome_esperado}' | Encontrado: '{nome_linha or 'vazio'}'"
            )

        assinatura = self.extrair_assinatura_linha(linha)
        if not assinatura:
            raise RuntimeError(
                f"Tabela '{nome_esperado}' encontrada, mas sem assinatura de linha para abrir o reajuste."
            )

        if data_inicio and data_fim:
            vigencia_linha = self.extrair_vigencia_linha(linha) or assinatura
            if not self.intervalo_vigencia_corresponde(vigencia_linha, data_inicio, data_fim):
                raise RuntimeError(
                    f"Linha '{nome_esperado}' encontrada com vigencia divergente. "
                    f"Esperado: {data_inicio} - {data_fim} | Encontrado: {vigencia_linha or 'vazio'}"
                )

        return assinatura

    def relocalizar_linha_por_assinatura(self, assinatura: str) -> WebElement:
        """Relocaliza uma linha apos re-render da grid Vue."""
        linhas = self.obter_linhas_tabela()
        for linha in linhas:
            if self.extrair_assinatura_linha(linha) == assinatura:
                return linha

        nome_alvo = assinatura.split(" | ")[0] if " | " in assinatura else assinatura
        for linha in linhas:
            if self.extrair_nome_linha(linha).strip() == nome_alvo.strip():
                return linha

        raise RuntimeError(
            f"Linha com assinatura '{assinatura[:60]}...' nao encontrada apos re-render"
        )

    def obter_total_tabelas(self) -> int:
        """Le o total de registros exibidos na grid."""
        try:
            info = self.acoes.aguardar_seletor("info_registros", "presente", timeout=5)
            texto = info.text.strip()
            if " de " in texto:
                return int(texto.split(" de ")[-1].strip())
        except Exception:
            pass
        return len(self.obter_linhas_tabela())

    # ------------------------------------------------------------------
    # Acoes de linha
    # ------------------------------------------------------------------

    def abrir_dropdown_primeira_linha(self) -> None:
        """Abre o dropdown da primeira linha visivel."""
        linhas = self.obter_linhas_tabela()
        if not linhas:
            raise RuntimeError("Nenhuma linha encontrada para abrir dropdown")
        self.abrir_dropdown_linha(linhas[0])

    def abrir_dropdown_linha(self, linha: WebElement) -> None:
        """Abre o menu de acoes da linha informada."""
        try:
            botao = linha.find_element(
                By.CSS_SELECTOR,
                "button.dropdown-toggle.more-actions",
            )
            self.acoes.clicar_com_seguranca(botao)
            time.sleep(0.3)
            self._ultima_linha_dropdown = linha
            WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                lambda d: self._obter_menu_dropdown_linha(linha, obrigar_visivel=True) is not None
            )
        except Exception as erro:
            raise RuntimeError(f"Nao foi possivel abrir dropdown da linha: {erro}")

    def clicar_duplicar_tabela(self) -> None:
        """Clica na opcao visivel de Duplicar tabela do dropdown aberto."""
        xpath = (
            "//ul[contains(@class,'dropdown-menu') and not(contains(@style,'display: none'))]"
            "//li[@title='Duplicar tabela']//span[normalize-space(text())='Duplicar tabela']"
        )
        opcao = self.acoes.aguardar_seletor_xpath(xpath, "clicavel")
        self.acoes.clicar_com_seguranca(opcao)

    def clicar_reajuste(self, linha: Optional[WebElement] = None) -> None:
        """Clica na opcao visivel de Reajuste do dropdown aberto."""
        try:
            opcao = self._localizar_opcao_reajuste_no_menu(linha or self._ultima_linha_dropdown)
        except Exception as erro_contexto:
            self.logger.warning(
                f"Falha ao localizar Reajuste no menu da linha atual ({erro_contexto}). "
                "Tentando fallback global..."
            )
            xpath = (
                "//ul[contains(@class,'dropdown-menu') and contains(@class,'vue-dropdown-menu')]"
                "//li[@title='Reajuste']//a[contains(@class,'dropdown-link')]"
            )
            opcao = self.acoes.aguardar_seletor_xpath(xpath, "clicavel")
        self.acoes.clicar_com_seguranca(self.acoes.resolver_alvo_clicavel(opcao))

    def _localizar_opcao_reajuste_no_menu(self, linha: Optional[WebElement]) -> WebElement:
        """Localiza a opcao Reajuste dentro do dropdown da linha aberta."""
        if linha is None:
            raise RuntimeError("Nenhuma linha com dropdown aberto disponivel para buscar Reajuste")

        menu = self._obter_menu_dropdown_linha(linha, obrigar_visivel=True)
        if menu is None:
            raise RuntimeError("Menu dropdown da linha nao ficou visivel apos abrir a seta")

        xpaths = [
            ".//li[@title='Reajuste']//a[contains(@class,'dropdown-link')]",
            ".//span[normalize-space(text())='Reajuste']/ancestor::a[contains(@class,'dropdown-link')]",
            ".//li[@title='Reajuste']",
        ]
        for xpath in xpaths:
            for elemento in menu.find_elements(By.XPATH, xpath):
                alvo = self.acoes.resolver_alvo_clicavel(elemento)
                if self.acoes.elemento_visivel(alvo) or self.acoes.elemento_visivel(elemento):
                    return alvo
        raise RuntimeError("Opcao Reajuste nao encontrada dentro do dropdown da linha")

    def _obter_menu_dropdown_linha(
        self,
        linha: WebElement,
        obrigar_visivel: bool = False,
    ) -> Optional[WebElement]:
        """Retorna o menu dropdown associado a linha informada."""
        try:
            menus = linha.find_elements(By.CSS_SELECTOR, "ul.dropdown-menu.vue-dropdown-menu")
        except Exception:
            return None

        for menu in menus:
            try:
                if not obrigar_visivel or menu.is_displayed():
                    return menu
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    # Modal de duplicacao
    # ------------------------------------------------------------------

    def aguardar_modal_duplicacao(self) -> None:
        """Aguarda o modal de duplicacao abrir."""
        popup = self._aguardar_popup_swal_visivel(
            "copiar os clientes vinculados",
            "duplicar a tabela",
        )
        popup.find_element(By.ID, "duplicate_customers")
        self._obter_switch_duplicacao_popup(popup)
        time.sleep(0.1)

    def ativar_switch_duplicacao(self) -> None:
        """Ativa o switch da duplicacao."""
        popup = self._aguardar_popup_swal_visivel(
            "copiar os clientes vinculados",
            "duplicar a tabela",
        )
        if self._switch_duplicacao_esta_ativo(popup):
            return

        switch = self._obter_switch_duplicacao_popup(popup)
        self.acoes.clicar_com_seguranca(switch)
        time.sleep(0.15)

    def confirmar_modal_swal(self, *textos_contexto: str) -> None:
        """Confirma o SweetAlert com o botao Sim."""
        popup = self._aguardar_popup_swal_visivel(*textos_contexto)
        botao = self._obter_botao_confirmar_popup(popup)
        self.acoes.clicar_com_seguranca(botao)
        time.sleep(0.2)

    def aguardar_modal_copia_finalizada(self) -> None:
        """Aguarda o SweetAlert que informa copia finalizada, com log de progresso."""
        self.logger.info(
            f"Aguardando copia ser finalizada pelo servidor "
            f"(limite={config.TIMEOUT_COPIA_FINALIZADA}s)..."
        )
        popup = self._aguardar_popup_swal_com_progresso(
            "copia finalizada",
            "editar a copia",
            "deseja editar",
            timeout=config.TIMEOUT_COPIA_FINALIZADA,
        )
        if popup is None:
            self.logger.critical(
                f"[TIMEOUT_COPIA] Popup 'Copia finalizada' nao apareceu "
                f"em {config.TIMEOUT_COPIA_FINALIZADA}s. "
                f"A copia pode ainda estar em andamento no servidor."
            )
            raise TimeoutError(
                f"Timeout: popup 'Copia finalizada' nao apareceu em "
                f"{config.TIMEOUT_COPIA_FINALIZADA}s"
            )
        self._validar_titulo_popup_copia(popup)
        self._obter_botao_confirmar_popup(popup)
        self.logger.info("[POPUP_DETECTADO] titulo=copia finalizada acao=validar_e_confirmar")
        time.sleep(0.2)

    def confirmar_editar_copia(self) -> None:
        """Confirma a abertura da tela de edicao da copia."""
        self.confirmar_modal_swal(
            "copia finalizada",
            "editar a copia",
            "deseja editar",
        )
        self._aguardar_popup_desaparecer()
        time.sleep(0.3)

    def _aguardar_popup_swal_visivel(
        self,
        *textos_esperados: str,
        timeout: Optional[int] = None,
    ) -> WebElement:
        """Retorna o SweetAlert visivel, opcionalmente filtrado por texto."""
        textos_normalizados = [
            self._normalizar_texto_popup(texto) for texto in textos_esperados if texto
        ]

        def _encontrar_popup(driver):
            popups = driver.find_elements(By.CSS_SELECTOR, "div.swal2-popup.swal2-modal")
            for popup in popups:
                try:
                    if not popup.is_displayed():
                        continue
                    if not textos_normalizados:
                        return popup

                    texto_popup = self._normalizar_texto_popup(popup.text)
                    if any(texto in texto_popup for texto in textos_normalizados):
                        return popup
                except Exception:
                    continue
            return False

        return WebDriverWait(self.acoes.driver, timeout or config.TIMEOUT).until(
            _encontrar_popup
        )

    def _aguardar_popup_swal_com_progresso(
        self,
        *textos_esperados: str,
        timeout: Optional[int] = None,
        intervalo_log: Optional[int] = None,
    ) -> Optional[WebElement]:
        """Polling wait com log periodico de progresso. Retorna popup ou None."""
        tempo_limite = timeout or config.TIMEOUT_COPIA_FINALIZADA
        intervalo = intervalo_log or config.INTERVALO_LOG_PROGRESSO_POPUP
        textos_normalizados = [
            self._normalizar_texto_popup(t) for t in textos_esperados if t
        ]

        inicio = time.time()
        ultimo_log = inicio

        while True:
            decorrido = time.time() - inicio
            if decorrido >= tempo_limite:
                return None

            try:
                popups = self.acoes.driver.find_elements(
                    By.CSS_SELECTOR, "div.swal2-popup.swal2-modal"
                )
                for popup in popups:
                    try:
                        if not popup.is_displayed():
                            continue
                        if not textos_normalizados:
                            return popup
                        texto_popup = self._normalizar_texto_popup(popup.text)
                        if any(t in texto_popup for t in textos_normalizados):
                            return popup
                    except Exception:
                        continue
            except Exception:
                pass

            agora = time.time()
            if agora - ultimo_log >= intervalo:
                minutos = int(decorrido) // 60
                segundos = int(decorrido) % 60
                tempo_fmt = f"{minutos}min{segundos:02d}s" if minutos else f"{segundos}s"
                limite_fmt = f"{int(tempo_limite) // 60}min"
                self.logger.info(
                    f"[AGUARDANDO_POPUP] tempo_espera={tempo_fmt} "
                    f"limite={limite_fmt} status=aguardando"
                )
                ultimo_log = agora

            time.sleep(0.5)

    def _validar_titulo_popup_copia(self, popup: WebElement) -> None:
        """Valida que o popup visivel e o de 'Copia finalizada'."""
        try:
            texto_popup = self._normalizar_texto_popup(popup.text)
            textos_validos = ["copia finalizada", "deseja editar"]
            if not any(t in texto_popup for t in textos_validos):
                self.logger.warning(
                    f"[POPUP_INESPERADO] Popup detectado mas texto nao corresponde a "
                    f"'Copia finalizada'. Texto encontrado: '{texto_popup[:100]}'"
                )
        except Exception as erro:
            self.logger.warning(f"Nao foi possivel validar titulo do popup: {erro}")

    def _aguardar_popup_desaparecer(self, timeout: int = 10) -> None:
        """Aguarda o SweetAlert desaparecer apos confirmacao."""
        try:
            self.acoes.aguardar_invisibilidade_css(
                "div.swal2-popup.swal2-modal",
                timeout=timeout,
            )
        except Exception:
            self.logger.warning(
                f"[POPUP_NAO_FECHOU] SweetAlert nao desapareceu em "
                f"{timeout}s apos confirmacao"
            )

    def verificar_popup_swal_inesperado(self) -> Optional[WebElement]:
        """Check instantaneo: retorna popup SweetAlert visivel ou None."""
        try:
            popups = self.acoes.driver.find_elements(
                By.CSS_SELECTOR, "div.swal2-popup.swal2-modal"
            )
            for popup in popups:
                try:
                    if popup.is_displayed():
                        texto = self._normalizar_texto_popup(popup.text)
                        self.logger.warning(
                            f"[POPUP_INESPERADO] Popup SweetAlert detectado fora do "
                            f"fluxo esperado. Texto: '{texto[:100]}'"
                        )
                        return popup
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def descartar_popup_swal_inesperado(self) -> bool:
        """Verifica e descarta popup SweetAlert inesperado. Retorna True se descartou."""
        popup = self.verificar_popup_swal_inesperado()
        if popup is None:
            return False
        try:
            botao = self._obter_botao_confirmar_popup(popup)
            self.acoes.clicar_com_seguranca(botao)
            self._aguardar_popup_desaparecer(timeout=5)
            self.logger.info("[POPUP_INESPERADO] Popup descartado com sucesso")
            return True
        except Exception as erro:
            self.logger.warning(
                f"[POPUP_INESPERADO] Nao foi possivel descartar popup: {erro}"
            )
            return False

    def _normalizar_texto_popup(self, texto: str) -> str:
        """Normaliza texto para comparacao robusta entre modais."""
        texto_normalizado = unicodedata.normalize("NFKD", texto or "")
        texto_sem_acento = "".join(
            caractere
            for caractere in texto_normalizado
            if not unicodedata.combining(caractere)
        )
        return " ".join(texto_sem_acento.lower().split())

    def _obter_switch_duplicacao_popup(self, popup: WebElement) -> WebElement:
        """Localiza o switch do modal de duplicacao no popup visivel."""
        try:
            return popup.find_element(
                By.CSS_SELECTOR, "#duplicate_customers + span.switchery"
            )
        except Exception:
            return popup.find_element(By.CSS_SELECTOR, "span.switchery")

    def _switch_duplicacao_esta_ativo(self, popup: WebElement) -> bool:
        """Detecta se o switch de copiar clientes ja esta ativo."""
        try:
            checkbox = popup.find_element(By.ID, "duplicate_customers")
            if checkbox.is_selected():
                return True
            valor = (checkbox.get_attribute("checked") or "").strip().lower()
            if valor in {"true", "checked", "1"}:
                return True
        except Exception:
            pass

        try:
            switch = self._obter_switch_duplicacao_popup(popup)
            classes = (switch.get_attribute("class") or "").lower()
            return "switchery-checked" in classes
        except Exception:
            return False

    def _obter_botao_confirmar_popup(self, popup: WebElement) -> WebElement:
        """Localiza o botao Sim dentro do popup visivel."""
        try:
            return popup.find_element(
                By.CSS_SELECTOR, "button#swal-confirm.swal2-confirm"
            )
        except Exception:
            return popup.find_element(By.CSS_SELECTOR, "button.swal2-confirm")

    # ------------------------------------------------------------------
    # Retorno a listagem e paginacao
    # ------------------------------------------------------------------

    def retornar_para_listagem(self) -> None:
        """Volta da tela atual para a listagem de tabelas de cliente."""
        xpath_link = (
            "//a[@href='/customer_price_tables' "
            "and normalize-space(text())='Tabelas de cliente']"
        )
        self.logger.info("Retornando para a listagem de Tabelas de Cliente...")

        try:
            link = self.acoes.aguardar_seletor_xpath(xpath_link, "clicavel", timeout=2)
            self.acoes.clicar_com_seguranca(link)
            self.aguardar_retorno_listagem(timeout=10)
            return
        except Exception as erro:
            self.logger.warning(
                f"Retorno via link falhou ({erro}). Tentando acesso direto pela URL..."
            )

        self.acessar_por_url()
        self.aguardar_retorno_listagem(timeout=10)

    def aguardar_retorno_listagem(self, timeout: Optional[int] = None) -> None:
        """Aguarda os elementos principais da listagem apos uma navegacao."""
        t = timeout or config.TIMEOUT
        self.acoes.aguardar_documento_pronto(timeout=t)
        self.acoes.aguardar_seletor("input_pesquisa_nome", "visivel", timeout=t)
        WebDriverWait(self.acoes.driver, t).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".vue-paginated-table"))
        )
        self.acoes.aguardar_carregamento_finalizar(timeout=t)

    def ir_para_proxima_pagina(self) -> bool:
        """Avanca para a proxima pagina, se existir."""
        try:
            botoes = self.acoes.driver.find_elements(
                By.XPATH, "//button[.//i[contains(@class,'fa-angle-right')]]"
            )
            for botao in botoes:
                if botao.is_displayed() and botao.is_enabled() and not botao.get_attribute("disabled"):
                    self.acoes.clicar_com_seguranca(botao)
                    time.sleep(0.6)
                    self.acoes.aguardar_carregamento_finalizar()
                    return True
        except Exception:
            pass
        return False

    def aguardar_carregamento_apos_fechar(self) -> None:
        """Aguarda a grid estabilizar apos fechar o modal de reajuste."""
        time.sleep(0.4)
        self.acoes.aguardar_carregamento_finalizar()
