"""
Mock completo do navegador Selenium para testes E2E simulados.
Simula DOM, elementos, cliques, digitacao e waits sem browser real.
"""

import time
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, PropertyMock


@dataclass
class ElementoDOM:
    """Representa um elemento HTML simulado."""
    tag: str = "div"
    texto: str = ""
    classes: str = ""
    atributos: dict = field(default_factory=dict)
    visivel: bool = True
    habilitado: bool = True
    filhos: list = field(default_factory=list)
    valor: str = ""
    selecionado: bool = False

    def is_displayed(self) -> bool:
        return self.visivel

    def is_enabled(self) -> bool:
        return self.habilitado

    def is_selected(self) -> bool:
        return self.selecionado

    @property
    def text(self) -> str:
        return self.texto

    @property
    def tag_name(self) -> str:
        return self.tag

    @property
    def id(self) -> str:
        return self.atributos.get("id", f"elem_{id(self)}")

    def get_attribute(self, nome: str) -> Optional[str]:
        if nome == "class":
            return self.classes
        if nome == "value":
            return self.valor
        if nome == "title":
            return self.atributos.get("title", self.texto)
        return self.atributos.get(nome)

    def click(self) -> None:
        if not self.visivel or not self.habilitado:
            raise Exception("Elemento nao clicavel")

    def send_keys(self, *args) -> None:
        for arg in args:
            if isinstance(arg, str):
                self.valor = arg
                self.texto = arg

    def find_element(self, by, valor) -> "ElementoDOM":
        for filho in self.filhos:
            if _elemento_bate_com_seletor(filho, by, valor):
                return filho
            try:
                return filho.find_element(by, valor)
            except Exception:
                continue
        raise Exception(f"Elemento nao encontrado: {by}={valor}")

    def find_elements(self, by, valor) -> list["ElementoDOM"]:
        resultado = []
        for filho in self.filhos:
            if _elemento_bate_com_seletor(filho, by, valor):
                resultado.append(filho)
            resultado.extend(filho.find_elements(by, valor))
        return resultado

    def clear(self) -> None:
        self.valor = ""
        self.texto = ""


def _elemento_bate_com_seletor(elem: ElementoDOM, by: str, valor: str) -> bool:
    """Verifica se um elemento bate com um seletor simplificado."""
    if by == "id" and elem.atributos.get("id") == valor:
        return True
    if by == "css selector":
        if valor.startswith("#") and elem.atributos.get("id") == valor[1:]:
            return True
        if valor.startswith(".") and valor[1:] in (elem.classes or ""):
            return True
        if valor.startswith("tr.") and elem.tag == "tr" and valor[3:] in (elem.classes or ""):
            return True
        if valor == elem.tag:
            return True
        if "div.table-text" in valor and elem.tag == "div" and "table-text" in (elem.classes or ""):
            return True
        if "dropdown-toggle" in valor and "dropdown-toggle" in (elem.classes or ""):
            return True
        if "swal2-popup" in valor and "swal2-popup" in (elem.classes or ""):
            return True
        if "swal2-confirm" in valor and "swal2-confirm" in (elem.classes or ""):
            return True
        if "switchery" in valor and "switchery" in (elem.classes or ""):
            return True
        if "vue-paginated-table" in valor and "vue-paginated-table" in (elem.classes or ""):
            return True
        if "select2" in valor and "select2" in (elem.classes or ""):
            return True
        if "dropdown-menu" in valor and "dropdown-menu" in (elem.classes or ""):
            return True
    if by == "xpath":
        if "vue-item" in valor and elem.tag == "tr" and "vue-item" in (elem.classes or ""):
            return True
        if "Duplicar tabela" in valor and "Duplicar tabela" in elem.texto:
            return True
        if "Reajuste" in valor and elem.texto == "Reajuste":
            return True
        if "dropdown-menu" in valor and "dropdown-menu" in (elem.classes or ""):
            return True
    return False


class LinhaTabela(ElementoDOM):
    """Linha da tabela de clientes simulada."""

    def __init__(self, nome: str, data_id: str = "", colunas_extras: list[str] = None):
        colunas = colunas_extras or ["Filial A", "Sim", "01/01/2026", "31/12/2026"]
        coluna_nome = ElementoDOM(
            tag="div",
            texto=nome,
            classes="table-text",
            atributos={"title": nome},
        )
        td_nome = ElementoDOM(tag="td", filhos=[coluna_nome])

        colunas_dom = [td_nome]
        for col_texto in colunas:
            col_elem = ElementoDOM(
                tag="div", texto=col_texto, classes="table-text",
                atributos={"title": col_texto},
            )
            colunas_dom.append(ElementoDOM(tag="td", filhos=[col_elem]))

        botao_dropdown = ElementoDOM(
            tag="button",
            classes="dropdown-toggle more-actions",
            atributos={"title": "Acoes"},
        )

        menu_dropdown = ElementoDOM(
            tag="ul",
            classes="dropdown-menu vue-dropdown-menu",
            visivel=False,
            filhos=[
                ElementoDOM(tag="span", texto="Duplicar tabela",
                            atributos={"title": "Duplicar tabela"}),
                ElementoDOM(tag="span", texto="Reajuste",
                            atributos={"title": "Reajuste"}),
            ],
        )

        super().__init__(
            tag="tr",
            classes="vue-item",
            atributos={"data-id": data_id or f"id_{nome[:10]}"},
            filhos=colunas_dom + [botao_dropdown, menu_dropdown],
        )
        self._nome = nome
        self.botao_dropdown = botao_dropdown
        self.menu_dropdown = menu_dropdown

    def abrir_dropdown(self):
        self.menu_dropdown.visivel = True

    def fechar_dropdown(self):
        self.menu_dropdown.visivel = False


class NavegadorMock:
    """
    Mock completo do WebDriver Selenium.
    Suporta find_element, find_elements, execute_script, get, save_screenshot.
    """

    def __init__(self):
        self.url_atual = ""
        self.elementos_raiz: list[ElementoDOM] = []
        self._documento_pronto = True
        self._titulo = "Mock Browser"
        self.screenshots_salvos: list[str] = []
        self.scripts_executados: list[str] = []
        self._linhas_tabela: list[LinhaTabela] = []
        self._modal_swal: Optional[ElementoDOM] = None
        self._input_pesquisa: Optional[ElementoDOM] = None
        self._select2_ativa: Optional[ElementoDOM] = None
        self._tabela_paginada: Optional[ElementoDOM] = None
        self._pagina_atual = 1
        self._total_paginas = 1

        self._inicializar_dom_base()

    def _inicializar_dom_base(self):
        """Cria a estrutura basica do DOM."""
        self._input_pesquisa = ElementoDOM(
            tag="input",
            atributos={"id": "search_price_tables_name", "name": "search[price_tables][name]"},
            classes="form-control",
        )
        self._select2_ativa = ElementoDOM(
            tag="span",
            classes="select2-container select2",
            atributos={"id": "container_select2_ativa"},
        )
        self._tabela_paginada = ElementoDOM(
            tag="div",
            classes="vue-paginated-table",
        )
        self.elementos_raiz = [
            self._input_pesquisa,
            self._select2_ativa,
            self._tabela_paginada,
        ]

    def get(self, url: str) -> None:
        self.url_atual = url

    @property
    def title(self) -> str:
        return self._titulo

    @property
    def current_url(self) -> str:
        return self.url_atual

    def find_element(self, by, valor) -> ElementoDOM:
        for elem in self.elementos_raiz + self._linhas_tabela:
            if _elemento_bate_com_seletor(elem, by, valor):
                return elem
            try:
                return elem.find_element(by, valor)
            except Exception:
                continue

        if self._modal_swal and _elemento_bate_com_seletor(self._modal_swal, by, valor):
            return self._modal_swal
        if self._modal_swal:
            try:
                return self._modal_swal.find_element(by, valor)
            except Exception:
                pass

        raise Exception(f"Elemento nao encontrado no mock: {by}={valor}")

    def find_elements(self, by, valor) -> list[ElementoDOM]:
        resultado = []
        for elem in self.elementos_raiz + self._linhas_tabela:
            if _elemento_bate_com_seletor(elem, by, valor):
                resultado.append(elem)
            resultado.extend(elem.find_elements(by, valor))

        if self._modal_swal:
            if _elemento_bate_com_seletor(self._modal_swal, by, valor):
                resultado.append(self._modal_swal)
            resultado.extend(self._modal_swal.find_elements(by, valor))

        return resultado

    def execute_script(self, script: str, *args) -> any:
        self.scripts_executados.append(script)
        if "readyState" in script:
            return "complete"
        if "scrollIntoView" in script:
            return None
        if "click" in script and args:
            return None
        return None

    def save_screenshot(self, caminho: str) -> bool:
        self.screenshots_salvos.append(caminho)
        return True

    def close(self) -> None:
        pass

    def quit(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Helpers para configurar cenarios de teste
    # ------------------------------------------------------------------

    def configurar_linhas(self, nomes: list[str]) -> None:
        """Configura linhas da tabela com os nomes fornecidos."""
        self._linhas_tabela = [
            LinhaTabela(nome=nome, data_id=f"id_{i}")
            for i, nome in enumerate(nomes)
        ]

    def configurar_modal_swal(self, texto: str, com_switch: bool = False) -> ElementoDOM:
        """Cria um modal SweetAlert simulado."""
        filhos = [
            ElementoDOM(tag="div", texto=texto, classes="swal2-html-container"),
            ElementoDOM(
                tag="button",
                texto="Sim",
                classes="swal2-confirm",
                atributos={"id": "swal-confirm"},
            ),
        ]
        if com_switch:
            checkbox = ElementoDOM(
                tag="input",
                atributos={"id": "duplicate_customers", "type": "checkbox"},
            )
            switch = ElementoDOM(tag="span", classes="switchery")
            filhos.extend([checkbox, switch])

        self._modal_swal = ElementoDOM(
            tag="div",
            texto=texto,
            classes="swal2-popup swal2-modal swal2-show",
            filhos=filhos,
        )
        return self._modal_swal

    def remover_modal(self) -> None:
        self._modal_swal = None

    def configurar_paginacao(self, total_paginas: int) -> None:
        """Configura simulacao de paginacao."""
        self._total_paginas = total_paginas
        self._pagina_atual = 1


class RegistroAcao:
    """Registra todas as acoes executadas no mock para validacao posterior."""

    def __init__(self):
        self.acoes: list[dict] = []
        self._tempo_inicio = time.time()

    def registrar(self, tipo: str, detalhe: str = "", linha: int = 0, valor: str = "") -> None:
        self.acoes.append({
            "tipo": tipo,
            "detalhe": detalhe,
            "linha": linha,
            "valor": valor,
            "tempo_ms": round((time.time() - self._tempo_inicio) * 1000),
        })

    def obter_por_tipo(self, tipo: str) -> list[dict]:
        return [a for a in self.acoes if a["tipo"] == tipo]

    def total_por_tipo(self, tipo: str) -> int:
        return len(self.obter_por_tipo(tipo))

    def limpar(self) -> None:
        self.acoes.clear()
        self._tempo_inicio = time.time()
