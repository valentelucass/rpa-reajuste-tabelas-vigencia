"""
Gestor de checkpoint para controle de progresso entre execucoes.
Persiste estado em JSON com escrita atomica para evitar corrupcao.
"""

import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.aplicacao.fase_execucao import FaseExecucao, StatusExecucao, TipoExecucao
from src.infraestrutura.caminhos import LOGS_DIR

if TYPE_CHECKING:
    from src.aplicacao.modo_execucao import ModoExecucao


_CAMINHO_CHECKPOINT = LOGS_DIR / "checkpoint.json"


def _calcular_hash_excel(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(8192), b""):
            h.update(bloco)
    return h.hexdigest()


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _estado_item_vazio(nome_tabela: str = "") -> dict:
    return {
        "nome_tabela": nome_tabela,
        "fase_1": StatusExecucao.PENDENTE.value,
        "fase_2": StatusExecucao.PENDENTE.value,
        "tentativas_fase_1": 0,
        "tentativas_fase_2": 0,
        "ultima_execucao": TipoExecucao.NORMAL.value,
        "reprocessado": False,
    }


def _estado_vazio(hash_excel: str, total_linhas: int, caminho_excel: str) -> dict:
    agora = _agora()
    return {
        "hash_excel": hash_excel,
        "total_linhas": total_linhas,
        "caminho_excel": caminho_excel,
        "criado_em": agora,
        "atualizado_em": agora,
        "fase1": {"status": StatusExecucao.PENDENTE.value, "linhas_processadas": {}},
        "fase2": {"status": StatusExecucao.PENDENTE.value, "linhas_processadas": {}},
        "itens": {},
    }


def _migrar_estado_legado(estado: dict) -> dict:
    estado = dict(estado or {})
    estado.setdefault("fase1", {"status": StatusExecucao.PENDENTE.value, "linhas_processadas": {}})
    estado.setdefault("fase2", {"status": StatusExecucao.PENDENTE.value, "linhas_processadas": {}})
    estado.setdefault("itens", {})

    for chave_fase in ("fase1", "fase2"):
        fase = estado.get(chave_fase, {})
        linhas = fase.get("linhas_processadas", {})
        if isinstance(linhas, list):
            fase["linhas_processadas"] = {str(i): "" for i in linhas}
        elif not isinstance(linhas, dict):
            fase["linhas_processadas"] = {}
        fase.setdefault("status", StatusExecucao.PENDENTE.value)

    itens = estado["itens"]
    for indice, nome in estado["fase1"]["linhas_processadas"].items():
        item = itens.setdefault(str(indice), _estado_item_vazio(nome))
        item["nome_tabela"] = item.get("nome_tabela") or nome
        item["fase_1"] = StatusExecucao.SUCESSO.value

    for indice, nome in estado["fase2"]["linhas_processadas"].items():
        item = itens.setdefault(str(indice), _estado_item_vazio(nome))
        item["nome_tabela"] = item.get("nome_tabela") or nome
        item["fase_1"] = StatusExecucao.SUCESSO.value
        item["fase_2"] = StatusExecucao.SUCESSO.value

    return estado


class GestorCheckpoint:
    """
    Gerencia checkpoint de progresso da automacao.

    Mantem compatibilidade com o modelo antigo de `linhas_processadas`,
    mas adiciona estado granular por item:
    - fase_1: pendente | sucesso | erro
    - fase_2: pendente | sucesso | erro
    """

    def __init__(self, estado: dict, logger: Optional[logging.Logger] = None) -> None:
        self._estado = _migrar_estado_legado(estado)
        self._caminho = _CAMINHO_CHECKPOINT
        self.logger = logger or logging.getLogger("rpa")

    @classmethod
    def carregar_ou_criar(
        cls,
        caminho_excel: Path,
        total_linhas: int = 0,
        logger: Optional[logging.Logger] = None,
        modo: Optional["ModoExecucao"] = None,
    ) -> "GestorCheckpoint":
        _log = logger or logging.getLogger("rpa")
        caminho_excel = Path(caminho_excel)
        hash_atual = _calcular_hash_excel(caminho_excel)

        if _CAMINHO_CHECKPOINT.exists():
            try:
                estado = json.loads(_CAMINHO_CHECKPOINT.read_text(encoding="utf-8"))
                if estado.get("hash_excel") != hash_atual:
                    _log.info(
                        "[CHECKPOINT][INVALIDADO] Excel modificado desde ultimo checkpoint. "
                        "Criando checkpoint novo."
                    )
                else:
                    estado = _migrar_estado_legado(estado)
                    if modo is not None:
                        _log.info(
                            "[CHECKPOINT][REINICIANDO] Nova execucao via UI, criando checkpoint novo"
                        )
                    else:
                        inst = cls(estado, _log)
                        resumo_f1 = inst.obter_resumo(1)
                        resumo_f2 = inst.obter_resumo(2)
                        _log.info(
                            f"[CHECKPOINT][CARREGADO] fase1={resumo_f1['status']} "
                            f"({resumo_f1['total_processadas']} linhas) "
                            f"fase2={resumo_f2['status']} ({resumo_f2['total_processadas']} linhas)"
                        )
                        return inst
            except (json.JSONDecodeError, KeyError, ValueError) as erro:
                _log.warning(f"[CHECKPOINT][ERRO] Checkpoint corrompido, recriando: {erro}")

        estado = _estado_vazio(hash_atual, total_linhas, str(caminho_excel))
        inst = cls(estado, _log)
        inst._salvar()
        _log.info("[CHECKPOINT][CRIADO] novo checkpoint criado")
        return inst

    @classmethod
    def carregar_existente(
        cls,
        logger: Optional[logging.Logger] = None,
    ) -> Optional["GestorCheckpoint"]:
        _log = logger or logging.getLogger("rpa")
        if not _CAMINHO_CHECKPOINT.exists():
            return None
        try:
            estado = json.loads(_CAMINHO_CHECKPOINT.read_text(encoding="utf-8"))
            return cls(estado, _log)
        except (json.JSONDecodeError, KeyError, ValueError) as erro:
            _log.warning(f"[CHECKPOINT][ERRO] Checkpoint corrompido: {erro}")
            return None

    def sincronizar_tabelas(self, tabelas: list) -> None:
        itens = self._estado.setdefault("itens", {})
        indices_validos = set()

        for indice, tabela in enumerate(tabelas, start=1):
            chave = str(indice)
            indices_validos.add(chave)
            item = itens.setdefault(chave, _estado_item_vazio(tabela.nome))
            item["nome_tabela"] = tabela.nome
            item.setdefault("fase_1", StatusExecucao.PENDENTE.value)
            item.setdefault("fase_2", StatusExecucao.PENDENTE.value)
            item.setdefault("tentativas_fase_1", 0)
            item.setdefault("tentativas_fase_2", 0)
            item.setdefault("ultima_execucao", TipoExecucao.NORMAL.value)
            item.setdefault("reprocessado", False)

            if chave in self._estado["fase1"]["linhas_processadas"]:
                item["fase_1"] = StatusExecucao.SUCESSO.value
            if chave in self._estado["fase2"]["linhas_processadas"]:
                item["fase_1"] = StatusExecucao.SUCESSO.value
                item["fase_2"] = StatusExecucao.SUCESSO.value

        for chave in list(itens.keys()):
            if chave not in indices_validos:
                itens.pop(chave, None)

        self._estado["total_linhas"] = len(tabelas)
        self._salvar()

    def ja_processada(self, fase: int, indice: int, nome_tabela: str = "") -> bool:
        item = self.obter_estado_item(indice, nome_tabela)
        status_fase = item[self._chave_status_item(fase)]
        if status_fase == StatusExecucao.SUCESSO.value:
            nome_salvo = item.get("nome_tabela", "")
            if nome_tabela and nome_salvo and nome_salvo != nome_tabela:
                self.logger.warning(
                    f"[CHECKPOINT][DIVERGENCIA] fase={fase} indice={indice} "
                    f"checkpoint='{nome_salvo}' excel='{nome_tabela}' - indice sera reprocessado por seguranca"
                )
                return False
            return True

        if status_fase == StatusExecucao.PENDENTE.value and self._sincronizar_item_legado(fase, indice, nome_tabela):
            return True

        return False

    def fase_completa(self, fase: int) -> bool:
        return self._estado[self._chave_fase_topo(fase)]["status"] == "completo"

    def obter_proximo_indice(self, fase: int) -> int:
        chave = self._chave_fase_topo(fase)
        linhas = self._estado[chave]["linhas_processadas"]
        if not linhas:
            return 1
        return max(int(k) for k in linhas) + 1

    def obter_resumo(self, fase: int) -> dict:
        chave = self._chave_fase_topo(fase)
        linhas = self._estado[chave]["linhas_processadas"]
        return {
            "status": self._estado[chave]["status"],
            "total_processadas": len(linhas),
            "ultimo_indice": max((int(k) for k in linhas), default=0),
            "ultimo_nome": linhas.get(str(max((int(k) for k in linhas), default=0)), ""),
        }

    def obter_estado_item(self, indice: int, nome_tabela: str = "") -> dict:
        itens = self._estado.setdefault("itens", {})
        chave = str(indice)
        item = itens.setdefault(chave, _estado_item_vazio(nome_tabela))
        if nome_tabela:
            item["nome_tabela"] = nome_tabela
        return item

    def contar_tentativas(self, fase: int, indice: int, nome_tabela: str = "") -> int:
        item = self.obter_estado_item(indice, nome_tabela)
        return int(item.get(self._chave_tentativas(fase), 0))

    def obter_tabelas_para_execucao(
        self,
        fase: int | FaseExecucao,
        tabelas: list,
        somente_falhas: bool = False,
    ) -> list[tuple[int, object]]:
        fase_execucao = FaseExecucao.from_valor(fase)
        itens: list[tuple[int, object]] = []

        for indice, tabela in enumerate(tabelas, start=1):
            estado = self.obter_estado_item(indice, tabela.nome)
            status_f1 = estado["fase_1"]
            status_f2 = estado["fase_2"]

            if fase_execucao is FaseExecucao.FASE_1:
                if somente_falhas and status_f1 != StatusExecucao.ERRO.value:
                    continue
                if not somente_falhas and status_f1 == StatusExecucao.SUCESSO.value:
                    continue
            else:
                if status_f1 != StatusExecucao.SUCESSO.value:
                    continue
                if somente_falhas and status_f2 != StatusExecucao.ERRO.value:
                    continue
                if not somente_falhas and status_f2 == StatusExecucao.SUCESSO.value:
                    continue

            itens.append((indice, tabela))

        return itens

    def registrar_resultado(
        self,
        fase: int | FaseExecucao,
        indice: int,
        nome_tabela: str,
        status: str,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> None:
        fase_execucao = FaseExecucao.from_valor(fase)
        fase_numero = fase_execucao.numero
        item = self.obter_estado_item(indice, nome_tabela)
        item[self._chave_status_item(fase_numero)] = status
        item[self._chave_tentativas(fase_numero)] = int(
            item.get(self._chave_tentativas(fase_numero), 0)
        ) + 1
        item["ultima_execucao"] = tipo_execucao.value
        item["reprocessado"] = item.get("reprocessado", False) or (
            tipo_execucao == TipoExecucao.REPROCESSAMENTO
        )

        chave_topo = self._chave_fase_topo(fase_numero)
        linhas = self._estado[chave_topo]["linhas_processadas"]
        str_indice = str(indice)

        if status == StatusExecucao.SUCESSO.value:
            linhas[str_indice] = nome_tabela
        else:
            linhas.pop(str_indice, None)
            self._estado[chave_topo]["status"] = "parcial"
            if fase_numero == 1 and item.get("fase_2") == StatusExecucao.SUCESSO.value:
                item["fase_2"] = StatusExecucao.PENDENTE.value

        self._salvar()

    def registrar_processada(self, fase: int, indice: int, nome_tabela: str = "") -> None:
        self.registrar_resultado(
            fase=fase,
            indice=indice,
            nome_tabela=nome_tabela,
            status=StatusExecucao.SUCESSO.value,
            tipo_execucao=TipoExecucao.NORMAL,
        )
        self.logger.info(
            f"[CHECKPOINT][SALVO] fase={fase} indice={indice} tabela={nome_tabela} status=sucesso"
        )

    def marcar_fase_completa(self, fase: int) -> None:
        self._estado[self._chave_fase_topo(fase)]["status"] = "completo"
        self._salvar()
        self.logger.info(f"[CHECKPOINT][SALVO] fase={fase} status=completo")

    def pode_marcar_fase_completa(self, fase: int) -> bool:
        itens = list(self._estado.get("itens", {}).values())
        if not itens:
            return True
        if fase == 1:
            return all(item.get("fase_1") == StatusExecucao.SUCESSO.value for item in itens)
        if fase == 2:
            elegiveis = [
                item
                for item in itens
                if item.get("fase_1") == StatusExecucao.SUCESSO.value
            ]
            if not elegiveis:
                return True
            return all(item.get("fase_2") == StatusExecucao.SUCESSO.value for item in elegiveis)
        raise ValueError(f"Fase invalida: {fase}")

    def desmarcar_processada(self, fase: int, indice: int) -> None:
        chave = self._chave_fase_topo(fase)
        linhas = self._estado[chave]["linhas_processadas"]
        linhas.pop(str(indice), None)

        item = self.obter_estado_item(indice)
        item[self._chave_status_item(fase)] = StatusExecucao.PENDENTE.value
        if fase == 2:
            item["reprocessado"] = True

        if self._estado[chave]["status"] == "completo":
            self._estado[chave]["status"] = "parcial"

        self._salvar()
        self.logger.info(
            f"[CHECKPOINT][DESMARCADO] fase={fase} indice={indice} - sera reprocessada na proxima execucao"
        )

    def resetar(self) -> None:
        hash_excel = self._estado.get("hash_excel", "")
        total_linhas = self._estado.get("total_linhas", 0)
        caminho_excel = self._estado.get("caminho_excel", "")
        self._estado = _estado_vazio(hash_excel, total_linhas, caminho_excel)
        self._salvar()
        self.logger.info("[CHECKPOINT][RESETADO]")

    def atualizar_total_linhas(self, total: int) -> None:
        self._estado["total_linhas"] = total
        self._salvar()

    def _salvar(self) -> None:
        self._estado["atualizado_em"] = _agora()
        dados = json.dumps(self._estado, ensure_ascii=False, indent=2)

        self._caminho.parent.mkdir(parents=True, exist_ok=True)

        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(self._caminho.parent), suffix=".tmp")
            os.write(fd, dados.encode("utf-8"))
            os.close(fd)
            fd = None
            os.replace(tmp_path, str(self._caminho))
            tmp_path = None
        except Exception:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise

    @staticmethod
    def _chave_fase_topo(fase: int) -> str:
        if fase == 1:
            return "fase1"
        if fase == 2:
            return "fase2"
        raise ValueError(f"Fase invalida: {fase}")

    @staticmethod
    def _chave_status_item(fase: int) -> str:
        if fase == 1:
            return "fase_1"
        if fase == 2:
            return "fase_2"
        raise ValueError(f"Fase invalida: {fase}")

    @staticmethod
    def _chave_tentativas(fase: int) -> str:
        if fase == 1:
            return "tentativas_fase_1"
        if fase == 2:
            return "tentativas_fase_2"
        raise ValueError(f"Fase invalida: {fase}")

    def _sincronizar_item_legado(self, fase: int, indice: int, nome_tabela: str = "") -> bool:
        chave = str(indice)
        linhas_processadas = self._estado[self._chave_fase_topo(fase)]["linhas_processadas"]
        nome_legado = linhas_processadas.get(chave)
        if not nome_legado:
            return False

        if nome_tabela and nome_legado != nome_tabela:
            self.logger.warning(
                f"[CHECKPOINT][DIVERGENCIA] fase={fase} indice={indice} "
                f"checkpoint='{nome_legado}' excel='{nome_tabela}' - indice sera reprocessado por seguranca"
            )
            return False

        item = self.obter_estado_item(indice, nome_tabela or nome_legado)
        item["nome_tabela"] = nome_tabela or nome_legado
        item[self._chave_status_item(fase)] = StatusExecucao.SUCESSO.value
        if fase == 2:
            item["fase_1"] = StatusExecucao.SUCESSO.value
        return True
