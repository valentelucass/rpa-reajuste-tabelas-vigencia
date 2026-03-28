from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

import config
from src.monitoramento.observador_execucao import ContratoObservadorExecucao
from src.servicos.gestor_ocorrencias import GestorOcorrenciasProcessamento
from src.servicos.leitor_excel import DadosTabelaExcel
from src.servicos.validador_elegibilidade_fase_dois import (
    DecisaoElegibilidadeFaseDois,
    ValidadorElegibilidadeFaseDois,
)


def _tabela(nome: str) -> DadosTabelaExcel:
    return DadosTabelaExcel(
        nome=nome,
        data_inicio="01/04/2026",
        data_fim="31/03/2027",
        percentual=9.8,
    )


@dataclass
class _LinhaFake:
    nome: str
    vigencia: str
    assinatura: str
    pronta: bool = True


class _PaginaFake:
    def __init__(self, resultados_por_nome=None, *, ha_resultados_grupo: bool = True):
        self.resultados_por_nome = resultados_por_nome or {}
        self.ha_resultados_grupo = ha_resultados_grupo
        self.data_inicio = ""
        self.data_fim = ""
        self.nome_pesquisado = ""
        self.pesquisas = []

    def preparar_estado_listagem_fase_dois(self, data_inicio: str, data_fim: str) -> None:
        self.data_inicio = data_inicio
        self.data_fim = data_fim

    def obter_valor_filtro_vigencia(self) -> str:
        return f"{self.data_inicio} - {self.data_fim}"

    def obter_total_tabelas(self) -> int:
        if not self.ha_resultados_grupo:
            return 0
        return sum(len(linhas) for linhas in self.resultados_por_nome.values())

    def ha_resultados_filtrados(self) -> bool:
        return self.ha_resultados_grupo

    def garantir_contexto_fase_dois(self, data_inicio: str, data_fim: str) -> bool:
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        return False

    def pesquisar_por_nome(self, nome: str) -> None:
        self.nome_pesquisado = nome
        self.pesquisas.append(nome)

    def validar_filtro_vigencia_aplicado(self, data_inicio: str, data_fim: str) -> bool:
        return self.data_inicio == data_inicio and self.data_fim == data_fim

    def aguardar_resultado_pesquisa(self) -> None:
        return None

    def obter_linhas_tabela(self) -> list[_LinhaFake]:
        if not self.ha_resultados_grupo:
            return []
        return list(self.resultados_por_nome.get(self.nome_pesquisado, []))

    @staticmethod
    def extrair_nome_linha(linha: _LinhaFake) -> str:
        return linha.nome

    @staticmethod
    def extrair_vigencia_linha(linha: _LinhaFake) -> str:
        return linha.vigencia

    @staticmethod
    def extrair_assinatura_linha(linha: _LinhaFake) -> str:
        return linha.assinatura

    @staticmethod
    def intervalo_vigencia_corresponde(valor: str, data_inicio: str, data_fim: str) -> bool:
        return valor.strip() == f"{data_inicio} - {data_fim}"

    def validar_linha_para_reajuste(
        self,
        linha: _LinhaFake,
        nome_esperado: str,
        data_inicio: str = "",
        data_fim: str = "",
    ) -> str:
        if linha.nome != nome_esperado:
            raise RuntimeError("nome divergente")
        if linha.vigencia != f"{data_inicio} - {data_fim}":
            raise RuntimeError("vigencia divergente")
        if not linha.pronta:
            raise RuntimeError("linha nao pronta para reajuste")
        return linha.assinatura


def _observador() -> MagicMock:
    observador = MagicMock(spec=ContratoObservadorExecucao)
    observador.validar_continuacao.return_value = True
    return observador


def _validador(pagina, observador=None):
    gestor = MagicMock(spec=GestorOcorrenciasProcessamento)
    observador = observador or _observador()
    logger = MagicMock()
    return ValidadorElegibilidadeFaseDois(
        pagina,
        gestor,
        observador,
        None,
        logger,
    )


def test_primeira_linha_invalida_nao_bloqueia_grupo_com_item_elegivel(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", True)

    pagina = _PaginaFake(
        {
            "T2": [
                _LinhaFake(
                    nome="T2",
                    vigencia="01/04/2026 - 31/03/2027",
                    assinatura="sig_t2",
                )
            ]
        }
    )
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        [(1, _tabela("T1")), (2, _tabela("T2"))],
        "run",
        "01/04/2026",
        "31/03/2027",
    )

    assert resultado.total_elegiveis == 1
    assert resultado.total_nao_encontrados == 1
    assert resultado.decisao_final == "elegivel"


def test_encontra_elegivel_na_confirmacao_quando_amostra_inicial_zerou(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", True)

    tabelas = [(indice, _tabela(f"T{indice}")) for indice in range(1, 7)]
    pagina = _PaginaFake(
        {
            "T4": [
                _LinhaFake(
                    nome="T4",
                    vigencia="01/04/2026 - 31/03/2027",
                    assinatura="sig_t4",
                )
            ]
        }
    )
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        tabelas,
        "run",
        "01/04/2026",
        "31/03/2027",
    )

    assert resultado.total_elegiveis == 1
    assert resultado.total_validados == 6
    assert "T4" in pagina.pesquisas


def test_para_na_amostra_inicial_quando_ja_encontra_elegivel(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", True)

    tabelas = [(indice, _tabela(f"T{indice}")) for indice in range(1, 11)]
    pagina = _PaginaFake(
        {
            "T5": [
                _LinhaFake(
                    nome="T5",
                    vigencia="01/04/2026 - 31/03/2027",
                    assinatura="sig_t5",
                )
            ]
        }
    )
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        tabelas,
        "run",
        "01/04/2026",
        "31/03/2027",
    )

    assert resultado.total_elegiveis == 1
    assert resultado.total_validados == 5
    assert pagina.pesquisas == ["T1", "T3", "T5", "T8", "T10"]


def test_modo_estrito_encontra_elegivel_apenas_na_varredura_final(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", False)

    tabelas = [(indice, _tabela(f"T{indice}")) for indice in range(1, 27)]
    pagina = _PaginaFake(
        {
            "T26": [
                _LinhaFake(
                    nome="T26",
                    vigencia="01/04/2026 - 31/03/2027",
                    assinatura="sig_t26",
                )
            ]
        }
    )
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        tabelas,
        "run",
        "01/04/2026",
        "31/03/2027",
    )

    assert resultado.total_elegiveis == 1
    assert resultado.total_validados == 26
    assert pagina.pesquisas[-1] == "T26"


def test_classifica_duplicado_no_site(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", True)

    pagina = _PaginaFake(
        {
            "T1": [
                _LinhaFake("T1", "01/04/2026 - 31/03/2027", "sig1"),
                _LinhaFake("T1", "01/04/2026 - 31/03/2027", "sig2"),
            ]
        }
    )
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        [(1, _tabela("T1"))],
        "run",
        "01/04/2026",
        "31/03/2027",
    )

    assert resultado.total_duplicados == 1
    assert resultado.itens[0].decisao == DecisaoElegibilidadeFaseDois.DUPLICADO_NO_SITE


def test_respeita_checkpoint_local_para_ja_processado(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", True)

    pagina = _PaginaFake({})
    checkpoint = MagicMock()
    checkpoint.ja_processada.return_value = True
    checkpoint.obter_estado_item.return_value = {"fase_1": "pendente", "fase_2": "sucesso"}
    checkpoint.contar_tentativas.return_value = 1
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        [(1, _tabela("T1"))],
        "run",
        "01/04/2026",
        "31/03/2027",
        checkpoint=checkpoint,
    )

    assert resultado.total_ja_processados == 1
    assert resultado.itens[0].decisao == DecisaoElegibilidadeFaseDois.JA_PROCESSADO_FASE_2
    assert pagina.pesquisas == []


def test_classifica_item_nao_pronto_para_fase_dois(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", True)

    pagina = _PaginaFake(
        {
            "T1": [
                _LinhaFake(
                    nome="T1",
                    vigencia="01/04/2026 - 31/03/2027",
                    assinatura="sig_t1",
                    pronta=False,
                )
            ]
        }
    )
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        [(1, _tabela("T1"))],
        "run",
        "01/04/2026",
        "31/03/2027",
    )

    assert resultado.total_nao_prontos == 1
    assert resultado.itens[0].decisao == DecisaoElegibilidadeFaseDois.NAO_PRONTO_PARA_FASE_2


def test_pesquisa_sem_linhas_visiveis_nao_pode_ser_marcada_como_elegivel(monkeypatch):
    monkeypatch.setattr(config, "FASE2_VALIDACAO_MODO", "estrito")
    monkeypatch.setattr(config, "FASE2_AMOSTRA_INICIAL", 5)
    monkeypatch.setattr(config, "FASE2_JANELA_CONFIRMACAO", 20)
    monkeypatch.setattr(config, "FASE2_AMOSTRAGEM_DISTRIBUIDA", True)

    pagina = _PaginaFake(
        {
            "OUTRA": [
                _LinhaFake(
                    nome="OUTRA",
                    vigencia="01/04/2026 - 31/03/2027",
                    assinatura="sig_outra",
                )
            ]
        }
    )
    validador = _validador(pagina)

    resultado = validador.validar_grupo(
        [(1, _tabela("T1"))],
        "run",
        "01/04/2026",
        "31/03/2027",
    )

    assert resultado.total_elegiveis == 0
    assert resultado.total_nao_encontrados == 1
    assert resultado.itens[0].decisao == DecisaoElegibilidadeFaseDois.NAO_ENCONTRADO_NO_SITE
