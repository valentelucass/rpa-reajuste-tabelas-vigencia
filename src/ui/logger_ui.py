"""
Gerenciador de logs da interface.
Consolida registros por chave, suporta paginacao e filtros avancados.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Optional


@dataclass
class EntradaLog:
    """Registro de uma tabela no log da UI."""

    fase: int
    indice: int
    nome_tabela: str
    status: str
    detalhe: str = ""
    horario: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    chave: str = ""
    tipo_erro: str = ""
    tipo_erro_legivel: str = ""
    motivo: str = ""
    acao_recomendada: str = ""
    screenshot: str = ""
    fase_execucao: str = ""
    tipo_execucao: str = "normal"
    reprocessado: bool = False
    status_fase_1: str = "pendente"
    status_fase_2: str = "pendente"
    processo: str = "reajuste_tabelas"
    dados_reprocessamento: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.fase_execucao and self.fase > 0 and self.processo == "auto_delete_clientes":
            self.fase_execucao = "auto_delete"
        elif not self.fase_execucao and self.fase > 0:
            self.fase_execucao = f"fase_{self.fase}"
        if not self.chave:
            self.chave = f"f{self.fase}_{self.nome_tabela}"


class GerenciadorLogsUi:
    """
    Mantem a lista de registros de log para exibicao na tabela da UI.
    Consolida registros por chave (mesma tabela na mesma fase).
    Suporta filtros por status, fase, tipo de execucao e reprocessamento.
    """

    def __init__(self, linhas_por_pagina: int = 8) -> None:
        self.linhas_por_pagina = linhas_por_pagina
        self._registros: list[EntradaLog] = []
        self._pagina_atual: int = 1
        self._filtro_status: Optional[str] = None
        self._filtro_fase: Optional[str] = None
        self._filtro_tipo_execucao: Optional[str] = None
        self._filtro_reprocessamento: Optional[str] = None
        self._filtro_processo: Optional[str] = None

    def adicionar_ou_atualizar(self, entrada: EntradaLog) -> None:
        for i, registro in enumerate(self._registros):
            if registro.chave == entrada.chave:
                self._registros[i] = entrada
                return
        self._registros.insert(0, entrada)

    def adicionar_sistema(self, mensagem: str, processo: str = "reajuste_tabelas") -> None:
        entrada = EntradaLog(
            fase=0,
            indice=0,
            nome_tabela="Sistema",
            status="Sistema",
            detalhe=mensagem,
            tipo_execucao="normal",
            chave=f"{processo}_sistema_{datetime.now().timestamp()}",
            processo=processo,
        )
        self._registros.insert(0, entrada)

    def definir_filtro(self, status: Optional[str]) -> None:
        """Mantido por compatibilidade com a UI atual."""
        self._filtro_status = status
        self._pagina_atual = 1

    def definir_filtros(
        self,
        *,
        status: Optional[str] = None,
        fase: Optional[str] = None,
        tipo_execucao: Optional[str] = None,
        filtro_reprocessamento: Optional[str] = None,
        processo: Optional[str] = None,
    ) -> None:
        self._filtro_status = status
        self._filtro_fase = fase
        self._filtro_tipo_execucao = tipo_execucao
        self._filtro_reprocessamento = filtro_reprocessamento
        self._filtro_processo = processo
        self._pagina_atual = 1

    def limpar_filtro(self) -> None:
        self._filtro_status = None
        self._filtro_fase = None
        self._filtro_tipo_execucao = None
        self._filtro_reprocessamento = None
        self._filtro_processo = None
        self._pagina_atual = 1

    @property
    def filtro_ativo(self) -> Optional[str]:
        return self._filtro_status

    def _registros_filtrados(self) -> list[EntradaLog]:
        registros = list(self._registros)

        if self._filtro_status:
            registros = [r for r in registros if r.status == self._filtro_status]
        if self._filtro_fase:
            registros = [r for r in registros if r.fase_execucao == self._filtro_fase]
        if self._filtro_tipo_execucao:
            registros = [r for r in registros if r.tipo_execucao == self._filtro_tipo_execucao]
        if self._filtro_reprocessamento == "apenas_falhas":
            registros = [r for r in registros if r.status in {"Erro", "Interrompido"}]
        elif self._filtro_reprocessamento == "reprocessados_sucesso":
            registros = [r for r in registros if r.reprocessado and r.status == "Sucesso"]
        elif self._filtro_reprocessamento == "reprocessados_erro":
            registros = [r for r in registros if r.reprocessado and r.status == "Erro"]
        if self._filtro_processo:
            registros = [r for r in registros if r.processo == self._filtro_processo]

        return registros

    def pagina_atual(self) -> list[EntradaLog]:
        registros = self._registros_filtrados()
        inicio = (self._pagina_atual - 1) * self.linhas_por_pagina
        fim = inicio + self.linhas_por_pagina
        return registros[inicio:fim]

    def total_paginas(self) -> int:
        total = len(self._registros_filtrados())
        if total == 0:
            return 1
        return (total + self.linhas_por_pagina - 1) // self.linhas_por_pagina

    def ir_para_pagina(self, pagina: int) -> None:
        self._pagina_atual = max(1, min(pagina, self.total_paginas()))

    def pagina_anterior(self) -> None:
        self.ir_para_pagina(self._pagina_atual - 1)

    def proxima_pagina(self) -> None:
        self.ir_para_pagina(self._pagina_atual + 1)

    @property
    def numero_pagina(self) -> int:
        return self._pagina_atual

    @property
    def total_registros(self) -> int:
        return len(self._registros)

    def contar_por_status(self, status: str) -> int:
        return sum(1 for r in self._registros if r.status == status)

    def obter_erros(self) -> list[EntradaLog]:
        return [r for r in self._registros if r.status == "Erro"]

    def obter_falhas_exportaveis(self, aplicar_filtros: bool = False) -> list[EntradaLog]:
        registros = self._registros_filtrados() if aplicar_filtros else self._registros
        return [r for r in registros if r.status in {"Erro", "Interrompido"}]

    def filtrar_reprocesso(self) -> list[EntradaLog]:
        return self.obter_falhas_exportaveis()

    def buscar_por_chave(self, chave: str) -> Optional[EntradaLog]:
        for registro in self._registros:
            if registro.chave == chave:
                return registro
        return None

    def obter_reprocessados_com_sucesso(self) -> list[EntradaLog]:
        return [r for r in self._registros if r.reprocessado and r.status == "Sucesso"]

    def obter_reprocessados_com_erro(self) -> list[EntradaLog]:
        return [r for r in self._registros if r.reprocessado and r.status == "Erro"]

    def obter_nomes_com_erro(self) -> list[str]:
        nomes: list[str] = []
        for registro in self._registros:
            if registro.status == "Erro" and registro.nome_tabela not in nomes:
                nomes.append(registro.nome_tabela)
        return nomes

    def buscar_entrada_erro(self, nome_tabela: str, fase: Optional[int] = None) -> Optional[EntradaLog]:
        for registro in self._registros:
            if registro.status != "Erro":
                continue
            if registro.nome_tabela != nome_tabela:
                continue
            if fase is not None and registro.fase != fase:
                continue
            return registro
        return None

    def buscar_entrada_reprocessavel(
        self,
        nome_tabela: str,
        fase: Optional[int] = None,
    ) -> Optional[EntradaLog]:
        for registro in self._registros:
            if registro.status not in {"Erro", "Interrompido"}:
                continue
            if registro.nome_tabela != nome_tabela:
                continue
            if fase is not None and registro.fase != fase:
                continue
            return registro
        return None

    def marcar_processando_como_interrompido(
        self,
        chave_prefixo: str,
        detalhe: str = "Execução interrompida pelo operador.",
    ) -> int:
        total = 0
        horario = datetime.now().strftime("%H:%M:%S")
        for indice, registro in enumerate(self._registros):
            if not registro.chave.startswith(chave_prefixo):
                continue
            if registro.status != "Processando":
                continue
            self._registros[indice] = replace(
                registro,
                status="Interrompido",
                detalhe=detalhe,
                horario=horario,
            )
            total += 1
        return total

    def limpar(self) -> None:
        self._registros.clear()
        self._pagina_atual = 1
        self._filtro_status = None
        self._filtro_fase = None
        self._filtro_tipo_execucao = None
        self._filtro_reprocessamento = None
        self._filtro_processo = None
