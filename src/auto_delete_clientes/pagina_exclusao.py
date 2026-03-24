"""
Page Object para exclusao de registros na tela de Tabelas de Cliente.
Encapsula: navegacao, filtros, busca, dropdown, exclusao, validacao.

Fluxo otimizado:
  1. configurar_filtros_iniciais() — UMA VEZ (filial, ativo, data)
  2. excluir_registro() — POR NOME (busca + exclusao em loop)
  Entre registros: apenas limpa o campo nome, sem reaplicar filtros.
"""

import logging
import time
import unicodedata
from typing import Optional

try:
    from . import config
    from .acoes_navegador import AcoesNavegador
    from .utils.atraso_humano import atraso_humano
except ImportError:  # pragma: no cover - compatibilidade standalone
    from auto_delete_compat import carregar_modulo_local

    config = carregar_modulo_local("config")
    from acoes_navegador import AcoesNavegador
    from utils.atraso_humano import atraso_humano
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class NavegadorFechadoError(Exception):
    """Levantada quando o navegador foi fechado pelo usuario."""


class PaginaExclusao:
    """Encapsula todas as interacoes para excluir registros de tabelas de cliente."""

    def __init__(self, acoes: AcoesNavegador, logger: Optional[logging.Logger] = None) -> None:
        self.acoes = acoes
        self.logger = logger or logging.getLogger("auto_delete_clientes")
        self._filtros_configurados = False
        self._data_inicio_esperada: Optional[str] = None
        self._data_fim_esperada: Optional[str] = None

    # ------------------------------------------------------------------
    # Verificacao de navegador aberto
    # ------------------------------------------------------------------

    def verificar_navegador_aberto(self) -> bool:
        """Retorna True se o navegador ainda esta acessivel.
        Levanta NavegadorFechadoError se detectar que foi fechado."""
        try:
            _ = self.acoes.driver.title
            return True
        except Exception:
            self.logger.error("Navegador fechado. Encerrando automacao.")
            raise NavegadorFechadoError("Navegador fechado. Encerrando automacao.")

    # ------------------------------------------------------------------
    # Navegacao
    # ------------------------------------------------------------------

    def acessar_tabelas_cliente(self) -> None:
        """Navega ate a tela de tabelas de cliente."""
        self.logger.info("Navegando para Tabelas de Cliente...")
        try:
            self.acoes.driver.get(config.URL_TABELAS_CLIENTE)
            self.acoes.aguardar_documento_pronto()
            self.acoes.aguardar_carregamento_finalizar()
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

    # ------------------------------------------------------------------
    # ETAPA 2 — Configuracao inicial dos filtros (UMA VEZ)
    # ------------------------------------------------------------------

    def configurar_filtros_iniciais(self, data_inicio: str, data_fim: str) -> None:
        """Configura todos os filtros UMA UNICA VEZ antes do loop de exclusao.
        1. Limpa filial
        2. Define Ativo = Sim
        3. Preenche data de vigencia
        4. Clica pesquisar para aplicar
        """
        if self._filtros_configurados:
            self.logger.debug("Filtros ja configurados, pulando")
            return

        self.verificar_navegador_aberto()
        self.logger.info("Configurando filtros iniciais...")

        # 1. Limpar filial
        self._limpar_filial()

        # 2. Ativo = Sim
        self._garantir_ativo_sim()

        # 3. Data de vigencia
        self._preencher_data_vigencia(data_inicio, data_fim)

        # 4. Disparar pesquisa para aplicar todos os filtros
        self._clicar_pesquisar()
        self.acoes.aguardar_carregamento_finalizar()

        self._filtros_configurados = True
        self._data_inicio_esperada = data_inicio
        self._data_fim_esperada = data_fim
        self.logger.info(
            f"Filtros iniciais configurados: Filial=Limpo | Ativo=Sim | "
            f"Vigencia={data_inicio} - {data_fim}"
        )

    # ------------------------------------------------------------------
    # Limpeza de filial
    # ------------------------------------------------------------------

    def _limpar_filial(self) -> bool:
        """Remove a selecao atual de Filial Responsavel (Select2), se existir."""
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

            if removeu:
                self.logger.info("Filtro de filial limpo com sucesso")
                self.acoes.aguardar_carregamento_finalizar()
            else:
                self.logger.debug("Filtro de filial ja estava vazio")
            return removeu
        except Exception:
            self.logger.debug("Filtro de filial ja estava vazio")
            return False

    # ------------------------------------------------------------------
    # Filtro Ativo = Sim
    # ------------------------------------------------------------------

    def _garantir_ativo_sim(self) -> None:
        """Garante que o filtro 'Ativo' esteja como 'Sim'."""
        if self._ativo_ja_selecionado_sim():
            self.logger.debug("Filtro ativo ja esta como Sim")
            return

        self.logger.info("Selecionando Ativo = Sim")
        try:
            self.acoes.selecionar_select2("container_select2_ativa", "Sim")
            time.sleep(0.2)
            self.acoes.aguardar_carregamento_finalizar()
        except Exception as erro:
            self.logger.warning(f"Nao foi possivel filtrar Ativa=Sim: {erro}")
            return

        if self._ativo_ja_selecionado_sim():
            self.logger.info("Filtro ativo configurado com sucesso")
        else:
            self.logger.warning("Filtro ativo pode nao ter sido aplicado corretamente")

    def _ativo_ja_selecionado_sim(self) -> bool:
        """Verifica se o filtro Ativo ja esta como 'Sim'."""
        try:
            container = self.acoes.aguardar_seletor(
                "container_select2_ativa", "presente", timeout=3
            )
            selecao = container.find_element(
                By.CSS_SELECTOR, ".select2-selection__rendered"
            )
            texto = (selecao.get_attribute("title") or "").strip().lower()
            return texto == "sim"
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Validacao de filtros
    # ------------------------------------------------------------------

    def _validar_filial_limpa(self) -> bool:
        """Verifica se o filtro de filial esta vazio (sem chips selecionados)."""
        try:
            grupo_filial = self.acoes.driver.find_element(
                By.ID, "search_price_tables_corporation_id"
            ).find_element(
                By.XPATH, "./ancestor::div[contains(@class,'form-group')][1]"
            )
            chips = grupo_filial.find_elements(
                By.CSS_SELECTOR, ".select2-selection__choice"
            )
            visiveis = [c for c in chips if c.is_displayed()]
            return len(visiveis) == 0
        except Exception:
            return True

    def _validar_data_vigencia(self, data_inicio: str, data_fim: str) -> bool:
        """Verifica se o input de vigencia contem as datas esperadas."""
        try:
            input_vigencia = self.acoes.driver.find_element(
                By.ID, "search_price_tables_effective_until"
            )
            valor = (input_vigencia.get_attribute("value") or "").strip()
            if not valor:
                return False
            return data_inicio in valor and data_fim in valor
        except Exception:
            return False

    def _validar_filtros(self) -> None:
        """Valida e, se necessario, reaplica os filtros antes de cada busca.
        Levanta RuntimeError se nao conseguir restaurar os filtros."""
        if not self._filtros_configurados:
            return

        self.logger.info("Validando filtros antes da busca")
        filtro_corrigido = False

        # 1. Filial vazia
        if not self._validar_filial_limpa():
            self.logger.warning("FILTRO ALTERADO: Filial nao esta vazia. Reaplicando...")
            self._limpar_filial()
            filtro_corrigido = True
            if not self._validar_filial_limpa():
                raise RuntimeError("Nao foi possivel restaurar filtro de filial")
            self.logger.info("Filial limpa confirmada")
        else:
            self.logger.debug("Filial limpa confirmada")

        # 2. Ativo = Sim
        if not self._ativo_ja_selecionado_sim():
            self.logger.warning("FILTRO ALTERADO: Ativo nao esta como Sim. Reaplicando...")
            self._garantir_ativo_sim()
            filtro_corrigido = True
            if not self._ativo_ja_selecionado_sim():
                raise RuntimeError("Nao foi possivel restaurar filtro Ativo=Sim")
            self.logger.info("Ativo = Sim confirmado")
        else:
            self.logger.debug("Ativo = Sim confirmado")

        # 3. Data de vigencia
        if not self._validar_data_vigencia(self._data_inicio_esperada, self._data_fim_esperada):
            self.logger.warning("FILTRO ALTERADO: Data de vigencia incorreta. Reaplicando...")
            self._preencher_data_vigencia(self._data_inicio_esperada, self._data_fim_esperada)
            filtro_corrigido = True
            if not self._validar_data_vigencia(self._data_inicio_esperada, self._data_fim_esperada):
                raise RuntimeError("Nao foi possivel restaurar filtro de data de vigencia")
            self.logger.info("Data confirmada")
        else:
            self.logger.debug("Data confirmada")

        if filtro_corrigido:
            self.logger.warning("Filtros foram restaurados antes da busca")
        else:
            self.logger.info("Filtros validados com sucesso")

    # ------------------------------------------------------------------
    # Data de vigencia
    # ------------------------------------------------------------------

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

    def _preencher_data_vigencia(self, data_inicio: str, data_fim: str) -> None:
        """Preenche o daterangepicker com data_inicio e data_fim."""
        self.logger.info(f"Aplicando filtro de data: {data_inicio} - {data_fim}")
        self._expandir_filtros_avancados()

        input_vigencia = self.acoes.aguardar_seletor("input_vigencia_fim", "clicavel", timeout=10)
        self.acoes.clicar_com_seguranca(input_vigencia)
        time.sleep(0.2)

        # Aguardar daterangepicker abrir
        WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".daterangepicker.active, .daterangepicker[style*='display: block']")
            )
        )

        # Preencher inicio e fim separadamente
        try:
            input_inicio_el = self.acoes.driver.find_element(
                By.CSS_SELECTOR, "input[name='daterangepicker_start']"
            )
            self.acoes.limpar_e_digitar(input_inicio_el, data_inicio)
            time.sleep(0.1)

            input_fim_el = self.acoes.driver.find_element(
                By.CSS_SELECTOR, "input[name='daterangepicker_end']"
            )
            self.acoes.limpar_e_digitar(input_fim_el, data_fim)
            time.sleep(0.1)
        except Exception:
            self.acoes.limpar_e_digitar(input_vigencia, f"{data_inicio} - {data_fim}")

        # OBRIGATORIO: Clicar em Confirmar no daterangepicker
        self.logger.info("Clicando em Confirmar no daterangepicker...")
        botao_confirmar = self.acoes.aguardar_seletor_css(
            "button.applyBtn.btn.btn-sm.btn-primary", "clicavel", timeout=10
        )
        self.acoes.clicar_com_seguranca(botao_confirmar)

        # Aguardar daterangepicker fechar (confirma que a data foi aplicada)
        try:
            WebDriverWait(self.acoes.driver, 5).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, ".daterangepicker.active, .daterangepicker[style*='display: block']")
                )
            )
        except Exception:
            pass
        self.logger.info("Data confirmada com sucesso")

    # ------------------------------------------------------------------
    # ETAPA 3 — Busca por nome (apenas troca o nome, filtros persistem)
    # ------------------------------------------------------------------

    def buscar_cliente(self, nome: str) -> None:
        """Limpa o campo nome, digita o novo nome e clica na lupa."""
        self.logger.info(f"Buscando cliente: {nome}")
        self._validar_filtros()
        input_nome = self.acoes.aguardar_seletor("input_pesquisa_nome", "visivel")
        self.acoes.limpar_e_digitar(input_nome, nome)
        time.sleep(0.2)
        self._garantir_nome_digitado(input_nome, nome)
        self._clicar_pesquisar()
        self.acoes.aguardar_carregamento_finalizar()

    def limpar_campo_nome(self) -> None:
        """Limpa apenas o campo de nome (sem tocar nos outros filtros)."""
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

    def _clicar_pesquisar(self) -> None:
        """Clica no botao de pesquisa (lupa), com fallback por Enter."""
        self.logger.info("Clicando na lupa")
        try:
            botao = self.acoes.aguardar_seletor("botao_pesquisar", "clicavel", timeout=5)
            self.acoes.clicar_com_seguranca(botao)
            return
        except Exception:
            pass

        try:
            input_nome = self.acoes.aguardar_seletor("input_pesquisa_nome", "visivel", timeout=3)
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

        try:
            input_nome = self.acoes.aguardar_seletor("input_pesquisa_nome", "visivel", timeout=3)
            input_nome.send_keys(Keys.ENTER)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers de pesquisa
    # ------------------------------------------------------------------

    def _garantir_nome_digitado(self, input_nome: WebElement, nome: str) -> None:
        """Garante que o campo Nome refletiu o valor esperado."""
        valor_atual = (input_nome.get_attribute("value") or "").strip()
        if self._normalizar_nome(valor_atual) == self._normalizar_nome(nome):
            return

        self.logger.warning(f"Campo Nome nao refletiu '{nome}'. Aplicando fallback por script.")
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

    def _normalizar_nome(self, valor: str) -> str:
        """Normaliza nome para comparacao."""
        return " ".join((valor or "").strip().upper().split())

    # ------------------------------------------------------------------
    # Leitura da tabela
    # ------------------------------------------------------------------

    def obter_linhas_tabela(self) -> list[WebElement]:
        """Retorna as linhas visiveis da grid."""
        time.sleep(0.15)
        try:
            linhas = self.acoes.driver.find_elements(By.CSS_SELECTOR, "tr.vue-item")
            return [linha for linha in linhas if linha.is_displayed()]
        except Exception:
            return []

    def extrair_nome_linha(self, linha: WebElement) -> str:
        """Extrai o nome da tabela da primeira coluna."""
        try:
            coluna_nome = linha.find_element(By.CSS_SELECTOR, "td:first-child div.table-text")
            return (coluna_nome.get_attribute("title") or coluna_nome.text).strip()
        except Exception:
            return ""

    def localizar_linha_por_nome(self, nome: str) -> Optional[WebElement]:
        """Encontra a linha cujo nome bate exatamente. Retorna None se nao encontrar."""
        nome_alvo = nome.strip()
        candidatas: list[WebElement] = []

        for linha in self.obter_linhas_tabela():
            nome_linha = self.extrair_nome_linha(linha).strip()
            if nome_linha == nome_alvo:
                return linha
            if nome_linha.rstrip() == nome_alvo:
                candidatas.append(linha)

        return candidatas[0] if candidatas else None

    def _localizar_proxima_linha(
        self, ignorar_chaves: set[str]
    ) -> tuple[Optional[int], Optional[WebElement]]:
        """Retorna a proxima linha visivel ainda nao processada."""
        for idx, linha in enumerate(self.obter_linhas_tabela()):
            chave_linha = self._obter_chave_linha(linha, idx)
            if chave_linha not in ignorar_chaves:
                return idx, linha
        return None, None

    def _obter_chave_linha(self, linha: WebElement, indice: Optional[int] = None) -> str:
        """Gera uma chave estavel para identificar a linha no DOM."""
        for atributo in ("data-id", "row_key", "row-key"):
            try:
                valor = (linha.get_attribute(atributo) or "").strip()
            except Exception:
                valor = ""
            if valor:
                return f"{atributo}:{valor}"

        nome_linha = self._normalizar_nome(self.extrair_nome_linha(linha))
        texto_linha = self._normalizar_nome(getattr(linha, "text", ""))
        partes = [parte for parte in (nome_linha, texto_linha) if parte]
        if indice is not None:
            partes.append(f"idx:{indice}")
        return "|".join(partes) or f"idx:{indice if indice is not None else 'desconhecido'}"

    def _linha_existe_por_chave(self, chave_linha: str) -> bool:
        """Verifica se a linha ainda esta visivel na tabela atual."""
        for idx, linha in enumerate(self.obter_linhas_tabela()):
            if self._obter_chave_linha(linha, idx) == chave_linha:
                return True
        return False

    def registro_existe(self, nome: str) -> bool:
        """Verifica se ha alguma linha com o nome dado apos a busca atual."""
        return self.localizar_linha_por_nome(nome) is not None

    # ------------------------------------------------------------------
    # Acoes de exclusao
    # ------------------------------------------------------------------

    def abrir_dropdown_linha(self, linha: WebElement) -> None:
        """Abre o menu de acoes (dropdown) da linha informada."""
        try:
            botao = linha.find_element(
                By.CSS_SELECTOR, "button.dropdown-toggle.more-actions"
            )
            self.acoes.clicar_com_seguranca(botao)
            time.sleep(0.3)

            WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
                lambda d: self._obter_menu_dropdown_linha(linha, obrigar_visivel=True) is not None
            )
        except Exception as erro:
            raise RuntimeError(f"Nao foi possivel abrir dropdown da linha: {erro}")

    def clicar_excluir(self, linha: WebElement) -> None:
        """Clica na opcao Excluir dentro do dropdown aberto da linha."""
        menu = self._obter_menu_dropdown_linha(linha, obrigar_visivel=True)
        if menu is None:
            raise RuntimeError("Menu dropdown nao esta visivel para clicar em Excluir")

        seletores = config.SELETORES.get("opcao_excluir", [])
        for tipo, valor in seletores:
            try:
                by = self.acoes._by_para_selenium(tipo)
                elementos = menu.find_elements(by, valor)
                for elem in elementos:
                    if self.acoes.elemento_visivel(elem):
                        self.acoes.clicar_com_seguranca(elem)
                        self.logger.info("Clicando em excluir")
                        return
            except Exception:
                continue

        raise RuntimeError("Opcao 'Excluir' nao encontrada no menu dropdown")

    def confirmar_exclusao_modal(self, chave_linha: str) -> str:
        """Confirma a exclusao e so retorna apos um resultado visual final.
        Retorna: sucesso | erro | ja_processado | timeout | timeout_refresh."""
        self.logger.info("Confirmando exclusao no modal...")

        # 1. Esperar modal de confirmacao aparecer
        popup = WebDriverWait(self.acoes.driver, config.TIMEOUT).until(
            lambda d: self._encontrar_popup_swal_visivel()
        )

        # 2. Clicar botao de confirmacao
        try:
            botao = popup.find_element(
                By.CSS_SELECTOR, "button#swal-confirm.swal2-confirm"
            )
        except Exception:
            botao = popup.find_element(By.CSS_SELECTOR, "button.swal2-confirm")

        self.acoes.clicar_com_seguranca(botao)
        self.logger.info("Exclusao iniciada")
        self.logger.info(
            f"Aguardando resposta do sistema (ate {config.TIMEOUT_RESPOSTA_EXCLUSAO}s)"
        )

        resultado = self._aguardar_resultado_visual_exclusao(
            chave_linha,
            timeout=config.TIMEOUT_RESPOSTA_EXCLUSAO,
        )

        if resultado == "sucesso":
            self.logger.info("Sucesso - linha removida")
            self.acoes.aguardar_carregamento_finalizar(ignorar_swal=True)
            self.acoes.aguardar_tabela_estavel()
            return "sucesso"

        if resultado == "erro":
            self._fechar_popup_resultado("erro")
            self.logger.warning("Erro detectado - popup tratado")
            self.acoes.aguardar_carregamento_finalizar(ignorar_swal=True)
            self.acoes.aguardar_tabela_estavel()
            return "erro"

        if resultado == "ja_processado":
            self._fechar_popup_resultado("ja_processado")
            self.logger.warning("Popup de resultado tratado - solicitacao ja processada")
            self.acoes.aguardar_carregamento_finalizar(ignorar_swal=True)
            self.acoes.aguardar_tabela_estavel()
            return "ja_processado"

        if resultado == "timeout_refresh":
            self.logger.warning("Timeout de 2 minutos atingido sem resposta")
            self._executar_refresh_apos_timeout()
            self.logger.info("Seguindo para proximo nome apos refresh")
            return "timeout_refresh"

        self.logger.warning("Timeout - nenhuma resposta do sistema")
        return "timeout"

    def _encontrar_popup_swal_visivel(self) -> Optional[WebElement]:
        """Retorna o popup SweetAlert visivel ou None."""
        try:
            popups = self.acoes.driver.find_elements(
                By.CSS_SELECTOR, "div.swal2-popup.swal2-modal"
            )
            for popup in popups:
                try:
                    if popup.is_displayed():
                        return popup
                except Exception:
                    continue
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Tratamento de popup de erro do sistema
    # ------------------------------------------------------------------

    def _normalizar_texto_popup(self, texto: str) -> str:
        """Normaliza texto de popup para comparacao sem acentos."""
        texto = (texto or "").strip().lower()
        return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")

    def _classificar_popup_resultado(self, popup: WebElement) -> Optional[str]:
        """Classifica o popup visivel em erro ou ja_processado."""
        try:
            texto = self._normalizar_texto_popup(popup.text)
        except Exception:
            return None

        ja_processado = [
            "essa solicitacao ja foi realizada",
            "solicitacao ja foi realizada",
            "ja foi realizada",
            "ja foi processado",
            "registro ja processado",
        ]
        if any(chave in texto for chave in ja_processado):
            return "ja_processado"

        erros = [
            "erro",
            "ocorreu um erro",
            "ja existe uma solicitacao em processamento",
            "solicitacao em processamento",
            "aguarde o retorno",
            "atualize a pagina para continuar",
        ]
        if any(chave in texto for chave in erros):
            return "erro"
        return None

    def _detectar_popup_resultado(self) -> tuple[Optional[str], Optional[WebElement]]:
        """Retorna o tipo do popup SweetAlert visivel e o proprio elemento."""
        popup = self._encontrar_popup_swal_visivel()
        if popup is None:
            return None, None
        tipo = self._classificar_popup_resultado(popup)
        if tipo:
            return tipo, popup
        return None, None

    def _detectar_popup_erro(self) -> Optional[WebElement]:
        """Detecta popup SweetAlert de erro/bloqueio visivel."""
        tipo, popup = self._detectar_popup_resultado()
        if tipo == "erro":
            return popup
        return None

    def _detectar_popup_ja_processado(self) -> Optional[WebElement]:
        """Detecta popup SweetAlert que indica item ja resolvido."""
        tipo, popup = self._detectar_popup_resultado()
        if tipo == "ja_processado":
            return popup
        return None

    def _encontrar_swal_sucesso_visivel(self) -> Optional[WebElement]:
        """Procura qualquer SweetAlert2 visivel (modal ou toast) com indicacao de sucesso."""
        seletores = [
            "div.swal2-popup.swal2-modal",
            "div.swal2-popup.swal2-toast",
            "div.swal2-popup",
        ]
        for seletor in seletores:
            try:
                popups = self.acoes.driver.find_elements(By.CSS_SELECTOR, seletor)
                for popup in popups:
                    try:
                        if not popup.is_displayed():
                            continue
                        # Verificar icone de sucesso
                        icones = popup.find_elements(
                            By.CSS_SELECTOR, ".swal2-icon-success, .swal2-success"
                        )
                        if any(i.is_displayed() for i in icones):
                            return popup
                        # Verificar texto de sucesso
                        texto = popup.text.lower()
                        palavras_sucesso = ["sucesso", "exclu", "removid", "deletad"]
                        if any(p in texto for p in palavras_sucesso):
                            return popup
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def _capturar_estado_dom_exclusao(self, chave_linha: str) -> dict[str, object]:
        """Captura um resumo leve do DOM para detectar se houve reacao da pagina."""
        linhas = self.obter_linhas_tabela()
        chaves_linhas: list[str] = []
        for idx, linha in enumerate(linhas[:5]):
            try:
                chaves_linhas.append(self._obter_chave_linha(linha, idx))
            except Exception:
                continue

        estado_dom = {
            "ready_state": "",
            "url": "",
            "loading_count": 0,
            "campo_nome": "",
        }
        try:
            dados = self.acoes.executar_script(
                """
                const campoNome = document.querySelector('#search_price_tables_name');
                const overlays = document.querySelectorAll(
                    '.loading, .spinner, .overlay, [class*="loading"], [class*="spinner"]'
                );
                return {
                    readyState: document.readyState || '',
                    url: window.location.href || '',
                    loadingCount: overlays.length,
                    campoNome: campoNome ? (campoNome.value || '') : '',
                };
                """
            ) or {}
            estado_dom.update(
                {
                    "ready_state": str(dados.get("readyState") or ""),
                    "url": str(dados.get("url") or ""),
                    "loading_count": int(dados.get("loadingCount") or 0),
                    "campo_nome": str(dados.get("campoNome") or ""),
                }
            )
        except Exception:
            pass

        estado_dom.update(
            {
                "total_linhas": len(linhas),
                "chaves_linhas": tuple(chaves_linhas),
                "linha_alvo_existe": any(chave == chave_linha for chave in chaves_linhas)
                or self._linha_existe_por_chave(chave_linha),
            }
        )
        return estado_dom

    @staticmethod
    def _houve_atualizacao_dom(
        estado_inicial: dict[str, object],
        estado_atual: dict[str, object],
    ) -> bool:
        """Retorna True quando algum sinal relevante do DOM mudou."""
        for chave in (
            "ready_state",
            "url",
            "loading_count",
            "campo_nome",
            "total_linhas",
            "chaves_linhas",
            "linha_alvo_existe",
        ):
            if estado_inicial.get(chave) != estado_atual.get(chave):
                return True
        return False

    def _executar_refresh_apos_timeout(self) -> None:
        """Recarrega a pagina apos detectar travamento da exclusao."""
        self.logger.warning("Executando refresh do navegador")
        try:
            self.acoes.driver.refresh()
        except Exception:
            self.acoes.executar_script("window.location.reload()")

        self.acoes.aguardar_documento_pronto(timeout=config.PAGE_LOAD_TIMEOUT)
        self.acoes.aguardar_carregamento_finalizar(
            timeout=config.PAGE_LOAD_TIMEOUT,
            ignorar_swal=True,
        )
        self.acoes.aguardar_tabela_estavel(timeout=min(config.PAGE_LOAD_TIMEOUT, 30))

    def _aguardar_resultado_visual_exclusao(self, chave_linha: str, timeout: int = 0) -> str:
        """Monitora o DOM ate a linha sumir, um popup aparecer ou o timeout expirar."""
        timeout = timeout or config.TIMEOUT_RESPOSTA_EXCLUSAO
        prazo_final = time.monotonic() + timeout
        linha_ausente_desde: Optional[float] = None
        estado_inicial = self._capturar_estado_dom_exclusao(chave_linha)
        houve_atualizacao_dom = False
        ultimo_snapshot = 0.0

        while time.monotonic() <= prazo_final:
            self.verificar_navegador_aberto()

            tipo_popup, _ = self._detectar_popup_resultado()
            if tipo_popup in {"erro", "ja_processado"}:
                return tipo_popup

            agora = time.monotonic()
            if agora - ultimo_snapshot >= 0.5:
                ultimo_snapshot = agora
                estado_atual = self._capturar_estado_dom_exclusao(chave_linha)
                houve_atualizacao_dom = (
                    houve_atualizacao_dom
                    or self._houve_atualizacao_dom(estado_inicial, estado_atual)
                )
            else:
                estado_atual = None

            linha_alvo_existe = (
                estado_atual.get("linha_alvo_existe", True)
                if estado_atual is not None
                else self._linha_existe_por_chave(chave_linha)
            )
            if not linha_alvo_existe:
                agora = time.monotonic()
                if linha_ausente_desde is None:
                    linha_ausente_desde = agora
                elif agora - linha_ausente_desde >= 0.5:
                    try:
                        WebDriverWait(
                            self.acoes.driver,
                            config.TIMEOUT_TOAST_DESAPARECER,
                            poll_frequency=0.1,
                        ).until(
                            lambda d: self._encontrar_swal_sucesso_visivel() is None
                        )
                    except Exception:
                        self.logger.warning("Toast de sucesso nao desapareceu, continuando")
                    return "sucesso"
            else:
                linha_ausente_desde = None

            time.sleep(0.2)

        if houve_atualizacao_dom:
            return "timeout"
        return "timeout_refresh"

    def _fechar_popup_resultado(self, tipo: str) -> bool:
        """Fecha popup de erro ou ja_processado e aguarda desaparecer."""
        if tipo == "ja_processado":
            popup = self._detectar_popup_ja_processado()
        else:
            popup = self._detectar_popup_erro()
        if popup is None:
            return False

        self.logger.info("Fechando popup de resultado")
        try:
            try:
                botao = popup.find_element(By.ID, "swal-confirm")
            except Exception:
                botao = popup.find_element(By.CSS_SELECTOR, "button.swal2-confirm")

            self.acoes.clicar_com_seguranca(botao)

            # 1. Aguardar popup desaparecer completamente
            self.acoes.aguardar_invisibilidade_css(
                "div.swal2-popup.swal2-modal", timeout=10
            )
            return True
        except Exception as erro:
            self.logger.error(f"Nao foi possivel fechar popup de resultado: {erro}")
            return False

    def _fechar_popup_erro(self) -> bool:
        """Compatibilidade com fluxos existentes de tratamento de erro."""
        return self._fechar_popup_resultado("erro")

    def _obter_menu_dropdown_linha(
        self, linha: WebElement, obrigar_visivel: bool = False
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
    # ETAPA 5 — Exclusao em loop (sem reaplicar filtros)
    # ------------------------------------------------------------------

    def contar_linhas_nome(self, nome: str) -> int:
        """Conta quantas linhas na grid correspondem ao nome."""
        nome_alvo = nome.strip()
        contagem = 0
        for linha in self.obter_linhas_tabela():
            nome_linha = self.extrair_nome_linha(linha).strip()
            if nome_linha == nome_alvo or nome_linha.rstrip() == nome_alvo:
                contagem += 1
        return contagem

    def contar_linhas_visiveis(self) -> int:
        """Conta quantas linhas visiveis existem na grid atual."""
        return len(self.obter_linhas_tabela())

    def _aguardar_contagem_diminuir(self, contagem_antes: int, timeout: int = 15) -> bool:
        """Aguarda ate a contagem de linhas diminuir E tabela estabilizar."""
        try:
            WebDriverWait(self.acoes.driver, timeout).until(
                lambda d: self.contar_linhas_visiveis() < contagem_antes
            )
            # Contagem diminuiu — agora verificar estabilidade
            self.acoes.aguardar_tabela_estavel(timeout=10)
            self.logger.info("Registro removido, validando proximo")
            return True
        except Exception:
            return False

    def excluir_registro(self, nome: str) -> str:
        """
        Exclusao COMPLETA de todos os registros de um nome.
        Assume que os filtros (filial, ativo, data) ja foram aplicados.

        Cada linha recebe no maximo uma tentativa de exclusao.
        Depois que a exclusao e iniciada, a mesma linha nunca e clicada novamente.

        Retorna:
            "sucesso"         - todos os registros foram excluidos (zero linhas)
            "ja_processado"   - sistema informou que a solicitacao ja foi realizada
            "nao_encontrado"  - nenhum registro encontrado na busca; no auto delete isso
                                significa cliente ja excluido
            "erro_exclusao"   - encontrou mas falhou ao excluir
        """
        self.verificar_navegador_aberto()

        # Buscar pelo nome (filtros ja aplicados, so troca o nome)
        self.buscar_cliente(nome)

        total_visivel = self.contar_linhas_visiveis()
        total_correspondente = self.contar_linhas_nome(nome)
        if total_visivel == 0:
            self.logger.info(
                f"Cliente {nome} -> NAO ENCONTRADO (tabela vazia, considerado ja excluido)"
            )
            return "nao_encontrado"

        if total_correspondente == 0:
            self.logger.warning(
                f"Cliente {nome} -> busca retornou {total_visivel} linha(s) visivel(is) sem "
                "correspondencia exata. Mesmo assim elas serao processadas."
            )
        else:
            self.logger.info(
                f"Cliente {nome} -> {total_correspondente} correspondencia(s) exata(s) "
                f"em {total_visivel} linha(s) visivel(is)"
            )

        exclusoes = 0
        houve_ja_processado = False
        houve_falha = False
        linhas_processadas: set[str] = set()

        while True:
            self.verificar_navegador_aberto()

            restantes = self.contar_linhas_visiveis()
            if restantes == 0:
                break

            idx_linha, linha = self._localizar_proxima_linha(linhas_processadas)
            if linha is None:
                self.logger.warning(
                    f"Restaram {restantes} linha(s) ja avaliadas sem nova tentativa permitida para '{nome}'"
                )
                break

            nome_linha = self.extrair_nome_linha(linha) or nome
            chave_linha = self._obter_chave_linha(linha, idx_linha)
            linhas_processadas.add(chave_linha)
            exclusao_iniciada = False
            self.logger.info(
                f"Linha detectada - fluxo unico de exclusao ({len(linhas_processadas)}/{total_visivel}) "
                f"[linha={idx_linha + 1}, nome_tela='{nome_linha}']"
            )
            try:
                self.acoes.aguardar_carregamento_finalizar()
                self.abrir_dropdown_linha(linha)
                atraso_humano(0.3, 0.6)
                self.clicar_excluir(linha)
                exclusao_iniciada = True
                atraso_humano(0.3, 0.6)

                resultado_exclusao = self.confirmar_exclusao_modal(chave_linha)

                if resultado_exclusao == "erro":
                    houve_falha = True
                    self.logger.info("Pulando para proxima linha")
                    continue

                if resultado_exclusao == "ja_processado":
                    houve_ja_processado = True
                    self.logger.info("Pulando para proxima linha")
                    continue

                if resultado_exclusao == "timeout":
                    houve_falha = True
                    self.logger.info("Pulando para proxima linha")
                    continue

                if resultado_exclusao == "timeout_refresh":
                    houve_falha = True
                    return "erro_exclusao"

                exclusoes += 1

            except NavegadorFechadoError:
                raise
            except Exception as erro:
                tipo_popup, _ = self._detectar_popup_resultado()
                if tipo_popup == "erro":
                    self._fechar_popup_resultado("erro")
                    houve_falha = True
                    self.logger.warning("Erro detectado - popup tratado")
                    self.logger.info("Pulando para proxima linha")
                    continue
                if tipo_popup == "ja_processado":
                    self._fechar_popup_resultado("ja_processado")
                    houve_ja_processado = True
                    self.logger.warning("Popup de resultado tratado - solicitacao ja processada")
                    self.logger.info("Pulando para proxima linha")
                    continue

                houve_falha = True
                if exclusao_iniciada:
                    self.logger.error(f"Erro apos iniciar exclusao da linha: {erro}")
                    self.logger.warning(
                        "A exclusao desta linha ja foi iniciada e nao sera repetida."
                    )
                else:
                    self.logger.error(f"Erro ao preparar exclusao da linha: {erro}")
                self.logger.info("Pulando para proxima linha")
                continue

        self.acoes.aguardar_tabela_estavel(timeout=10)
        restantes_final = self.contar_linhas_visiveis()
        if restantes_final == 0:
            if houve_ja_processado and exclusoes == 0:
                self.logger.info(
                    f"Nenhuma nova exclusao executada para {nome}; sistema indicou itens ja processados"
                )
                return "ja_processado"
            self.logger.info(f"Todas linhas removidas para {nome} ({exclusoes} exclusao(oes))")
            return "sucesso"

        self.logger.error(
            f"Falha: ainda existem {restantes_final} registros apos processar cada linha uma unica vez para '{nome}'"
        )
        return "erro_exclusao" if houve_falha or houve_ja_processado else "erro_exclusao"
