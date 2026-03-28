"""
Pre-validacao da Fase 2 baseada em Excel + estado real do site.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import logging
import time
from typing import TYPE_CHECKING, Optional

import config
from src.aplicacao.fase_execucao import FaseExecucao, StatusExecucao, TipoExecucao
from src.infraestrutura.logger_estruturado import LoggerEstruturado
from src.infraestrutura.registro_processamento import agora_iso
from src.monitoramento.observador_execucao import (
    ContextoTabelaProcessamento,
    ContratoObservadorExecucao,
    ObservadorNulo,
)
from src.servicos.leitor_excel import DadosTabelaExcel

if TYPE_CHECKING:
    from src.aplicacao.gestor_checkpoint import GestorCheckpoint
    from src.infraestrutura.rastreador_etapas import RastreadorEtapas
    from src.servicos.gestor_ocorrencias import GestorOcorrenciasProcessamento


class DecisaoElegibilidadeFaseDois(str, Enum):
    ELEGIVEL = "elegivel"
    NAO_ENCONTRADO_NO_SITE = "nao_encontrado_no_site"
    NAO_PRONTO_PARA_FASE_2 = "nao_pronto_para_fase_2"
    VIGENCIA_DIVERGENTE = "vigencia_divergente"
    NOME_DIVERGENTE = "nome_divergente"
    DUPLICADO_NO_SITE = "duplicado_no_site"
    JA_PROCESSADO_FASE_2 = "ja_processado_fase_2"
    ERRO_TECNICO_VALIDACAO = "erro_tecnico_validacao"


@dataclass
class ResultadoValidacaoItemFaseDois:
    indice_excel: int
    nome_tabela: str
    data_inicio: str
    data_fim: str
    decisao: DecisaoElegibilidadeFaseDois
    motivo: str = ""
    status_site: str = ""
    assinatura_site: str = ""
    amostrado: bool = False
    janela_validacao: str = ""
    origem_decisao: str = "site"
    confirmado_no_site: bool = False
    detalhes_site: dict[str, str] = field(default_factory=dict)
    item_excel: Optional[tuple[int, DadosTabelaExcel]] = field(
        default=None,
        repr=False,
        compare=False,
    )

    @property
    def elegivel(self) -> bool:
        return self.decisao == DecisaoElegibilidadeFaseDois.ELEGIVEL

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados.pop("item_excel", None)
        dados["decisao"] = self.decisao.value
        dados["elegivel"] = self.elegivel
        return dados


@dataclass
class ResultadoValidacaoGrupoFaseDois:
    filtro_vigencia: str
    data_inicio: str
    data_fim: str
    modo_validacao: str
    total_itens_excel: int
    total_registros_filtrados: int = 0
    resultado_site: str = "nao_validado"
    decisao_final: str = "pendente"
    itens: list[ResultadoValidacaoItemFaseDois] = field(default_factory=list)
    total_amostrados: int = 0
    total_validados: int = 0
    total_elegiveis: int = 0
    total_nao_encontrados: int = 0
    total_nao_prontos: int = 0
    total_duplicados: int = 0
    total_divergentes: int = 0
    total_ja_processados: int = 0
    total_erros_tecnicos: int = 0

    def adicionar_resultado(self, resultado: ResultadoValidacaoItemFaseDois) -> None:
        self.itens.append(resultado)

    def itens_elegiveis(self) -> list[tuple[int, DadosTabelaExcel]]:
        itens: list[tuple[int, DadosTabelaExcel]] = []
        for resultado in self.itens:
            if resultado.elegivel and resultado.item_excel is not None:
                itens.append(resultado.item_excel)
        return itens

    def validar_consistencia(self) -> None:
        self.total_validados = len(self.itens)
        self.total_amostrados = sum(1 for item in self.itens if item.amostrado)
        self.total_elegiveis = sum(1 for item in self.itens if item.decisao == DecisaoElegibilidadeFaseDois.ELEGIVEL)
        self.total_nao_encontrados = sum(
            1 for item in self.itens if item.decisao == DecisaoElegibilidadeFaseDois.NAO_ENCONTRADO_NO_SITE
        )
        self.total_nao_prontos = sum(
            1 for item in self.itens if item.decisao == DecisaoElegibilidadeFaseDois.NAO_PRONTO_PARA_FASE_2
        )
        self.total_duplicados = sum(
            1 for item in self.itens if item.decisao == DecisaoElegibilidadeFaseDois.DUPLICADO_NO_SITE
        )
        self.total_divergentes = sum(
            1
            for item in self.itens
            if item.decisao
            in {
                DecisaoElegibilidadeFaseDois.VIGENCIA_DIVERGENTE,
                DecisaoElegibilidadeFaseDois.NOME_DIVERGENTE,
            }
        )
        self.total_ja_processados = sum(
            1 for item in self.itens if item.decisao == DecisaoElegibilidadeFaseDois.JA_PROCESSADO_FASE_2
        )
        self.total_erros_tecnicos = sum(
            1 for item in self.itens if item.decisao == DecisaoElegibilidadeFaseDois.ERRO_TECNICO_VALIDACAO
        )

        if self.resultado_site == "sem_resultados_no_site":
            self.decisao_final = "sem_resultados_no_site"
        elif self.total_elegiveis > 0:
            self.decisao_final = "elegivel"
        elif self.total_erros_tecnicos == self.total_validados and self.total_validados > 0:
            self.decisao_final = "erro_tecnico_validacao"
        else:
            self.decisao_final = "sem_elegiveis"

    def to_dict(self) -> dict:
        self.validar_consistencia()
        return {
            "filtro_vigencia": self.filtro_vigencia,
            "data_inicio": self.data_inicio,
            "data_fim": self.data_fim,
            "modo_validacao": self.modo_validacao,
            "total_itens_excel": self.total_itens_excel,
            "total_registros_filtrados": self.total_registros_filtrados,
            "resultado_site": self.resultado_site,
            "decisao_final": self.decisao_final,
            "total_amostrados": self.total_amostrados,
            "total_validados": self.total_validados,
            "total_elegiveis": self.total_elegiveis,
            "total_nao_encontrados": self.total_nao_encontrados,
            "total_nao_prontos": self.total_nao_prontos,
            "total_duplicados": self.total_duplicados,
            "total_divergentes": self.total_divergentes,
            "total_ja_processados": self.total_ja_processados,
            "total_erros_tecnicos": self.total_erros_tecnicos,
            "itens": [item.to_dict() for item in self.itens],
        }


class _EtapaNula:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ValidadorElegibilidadeFaseDois:
    """Valida elegibilidade da Fase 2 usando o site como fonte de verdade."""

    def __init__(
        self,
        pagina_tabelas,
        gestor: "GestorOcorrenciasProcessamento",
        observador: Optional[ContratoObservadorExecucao] = None,
        rastreador: Optional["RastreadorEtapas"] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.pagina_tabelas = pagina_tabelas
        self.gestor = gestor
        self.observador = observador or ObservadorNulo()
        self.rastreador = rastreador
        self.logger = logger or logging.getLogger("rpa")
        self.log_estruturado = LoggerEstruturado(self.logger)

    def validar_grupo(
        self,
        itens: list[tuple[int, DadosTabelaExcel]],
        run_id: str,
        data_inicio: str,
        data_fim: str,
        *,
        checkpoint: Optional["GestorCheckpoint"] = None,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> ResultadoValidacaoGrupoFaseDois:
        filtro_vigencia = f"{data_inicio} - {data_fim}".strip(" -")
        resultado = ResultadoValidacaoGrupoFaseDois(
            filtro_vigencia=filtro_vigencia,
            data_inicio=data_inicio,
            data_fim=data_fim,
            modo_validacao=config.FASE2_VALIDACAO_MODO,
            total_itens_excel=len(itens),
        )
        if not itens:
            resultado.resultado_site = "sem_itens_excel"
            resultado.validar_consistencia()
            return resultado

        self.log_estruturado.fase2(
            "F2_VALIDACAO_INICIO",
            status="INICIADO",
            total=str(len(itens)),
            vigencia=filtro_vigencia,
            modo=config.FASE2_VALIDACAO_MODO,
        )

        with self._etapa(
            "validar_grupo_vigencia",
            "Validando grupo de vigencia da Fase 2",
            {
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "quantidade_itens": len(itens),
                "modo_validacao": config.FASE2_VALIDACAO_MODO,
            },
        ):
            self.pagina_tabelas.preparar_estado_listagem_fase_dois(data_inicio, data_fim)
            resultado.filtro_vigencia = (
                self.pagina_tabelas.obter_valor_filtro_vigencia() or filtro_vigencia
            )
            resultado.total_registros_filtrados = self.pagina_tabelas.obter_total_tabelas()
            self.log_estruturado.fase2(
                "F2_GRUPO_INICIO",
                status="EM_ANDAMENTO",
                total_excel=str(len(itens)),
                filtro_vigencia=resultado.filtro_vigencia,
                total_site=str(resultado.total_registros_filtrados),
            )

            if not self.pagina_tabelas.ha_resultados_filtrados():
                resultado.resultado_site = "sem_resultados_no_site"
                for indice_excel, tabela in itens:
                    item_resultado = ResultadoValidacaoItemFaseDois(
                        indice_excel=indice_excel,
                        nome_tabela=tabela.nome,
                        data_inicio=tabela.data_inicio,
                        data_fim=tabela.data_fim,
                        decisao=DecisaoElegibilidadeFaseDois.NAO_ENCONTRADO_NO_SITE,
                        motivo=(
                            "Nenhum item foi retornado pelo site para o filtro de vigencia "
                            f"{resultado.filtro_vigencia}."
                        ),
                        status_site="sem_resultados_no_site",
                        origem_decisao="site",
                        item_excel=(indice_excel, tabela),
                    )
                    resultado.adicionar_resultado(item_resultado)
                    self._registrar_resultado_item(
                        resultado=item_resultado,
                        total_planejado=len(itens),
                        run_id=run_id,
                        grupo_vigencia=resultado.filtro_vigencia,
                        checkpoint=checkpoint,
                        tipo_execucao=tipo_execucao,
                    )
                resultado.validar_consistencia()
                self._registrar_resumo_grupo(resultado)
                return resultado

            resultado.resultado_site = "resultados_filtrados"
            indices_amostra = self._selecionar_posicoes(
                len(itens),
                min(max(config.FASE2_AMOSTRA_INICIAL, 1), len(itens)),
            )
            resultados_por_indice: dict[int, ResultadoValidacaoItemFaseDois] = {}

            with self._etapa(
                "amostra_inicial_fase_dois",
                "Executando amostra inicial da Fase 2",
                {
                    "quantidade_amostra": len(indices_amostra),
                    "vigencia": resultado.filtro_vigencia,
                },
            ):
                self._validar_posicoes(
                    itens,
                    indices_amostra,
                    resultados_por_indice,
                    run_id,
                    resultado.filtro_vigencia,
                    checkpoint=checkpoint,
                    tipo_execucao=tipo_execucao,
                    janela_validacao="amostra_inicial",
                    amostrado=True,
                )

            if not self._ha_elegivel(resultados_por_indice):
                restantes = [posicao for posicao in range(len(itens)) if posicao not in indices_amostra]
                confirmacao = self._selecionar_posicoes_restantes(
                    restantes,
                    min(max(config.FASE2_JANELA_CONFIRMACAO, 1), len(restantes)),
                )
                if confirmacao:
                    with self._etapa(
                        "confirmacao_sem_elegiveis",
                        "Confirmando ausencia de elegiveis na Fase 2",
                        {
                            "quantidade_confirmacao": len(confirmacao),
                            "vigencia": resultado.filtro_vigencia,
                        },
                    ):
                        self._validar_posicoes(
                            itens,
                            confirmacao,
                            resultados_por_indice,
                            run_id,
                            resultado.filtro_vigencia,
                            checkpoint=checkpoint,
                            tipo_execucao=tipo_execucao,
                            janela_validacao="confirmacao_sem_elegiveis",
                            amostrado=True,
                        )

                if not self._ha_elegivel(resultados_por_indice) and config.FASE2_VALIDACAO_MODO == "estrito":
                    restantes = [
                        posicao
                        for posicao in range(len(itens))
                        if posicao not in resultados_por_indice
                    ]
                    self._validar_restantes(
                        itens,
                        restantes,
                        resultados_por_indice,
                        run_id,
                        resultado.filtro_vigencia,
                        checkpoint=checkpoint,
                        tipo_execucao=tipo_execucao,
                    )

            for posicao in range(len(itens)):
                resultado_item = resultados_por_indice.get(posicao)
                if resultado_item is not None:
                    resultado.adicionar_resultado(resultado_item)

        resultado.validar_consistencia()
        self._registrar_resumo_grupo(resultado)
        return resultado

    def _validar_restantes(
        self,
        itens: list[tuple[int, DadosTabelaExcel]],
        posicoes: list[int],
        resultados_por_indice: dict[int, ResultadoValidacaoItemFaseDois],
        run_id: str,
        grupo_vigencia: str,
        *,
        checkpoint: Optional["GestorCheckpoint"] = None,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> None:
        if not posicoes:
            return
        with self._etapa(
            "varredura_completa_grupo",
            "Executando varredura completa do grupo da Fase 2",
            {
                "quantidade_restante": len(posicoes),
                "vigencia": grupo_vigencia,
            },
        ):
            self._validar_posicoes(
                itens,
                posicoes,
                resultados_por_indice,
                run_id,
                grupo_vigencia,
                checkpoint=checkpoint,
                tipo_execucao=tipo_execucao,
                janela_validacao="varredura_completa",
                amostrado=False,
            )

    def _validar_posicoes(
        self,
        itens: list[tuple[int, DadosTabelaExcel]],
        posicoes: list[int],
        resultados_por_indice: dict[int, ResultadoValidacaoItemFaseDois],
        run_id: str,
        grupo_vigencia: str,
        *,
        checkpoint: Optional["GestorCheckpoint"] = None,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
        janela_validacao: str,
        amostrado: bool,
    ) -> None:
        for posicao in posicoes:
            if posicao in resultados_por_indice:
                continue
            indice_excel, tabela = itens[posicao]
            resultado = self._validar_item(
                indice_excel,
                tabela,
                checkpoint=checkpoint,
            )
            resultado.amostrado = amostrado
            resultado.janela_validacao = janela_validacao
            resultados_por_indice[posicao] = resultado
            self._registrar_resultado_item(
                resultado=resultado,
                total_planejado=len(itens),
                run_id=run_id,
                grupo_vigencia=grupo_vigencia,
                checkpoint=checkpoint,
                tipo_execucao=tipo_execucao,
            )
            time.sleep(0.05)

    def _validar_item(
        self,
        indice_excel: int,
        tabela: DadosTabelaExcel,
        *,
        checkpoint: Optional["GestorCheckpoint"] = None,
    ) -> ResultadoValidacaoItemFaseDois:
        if checkpoint and checkpoint.ja_processada(2, indice_excel, tabela.nome):
            return ResultadoValidacaoItemFaseDois(
                indice_excel=indice_excel,
                nome_tabela=tabela.nome,
                data_inicio=tabela.data_inicio,
                data_fim=tabela.data_fim,
                decisao=DecisaoElegibilidadeFaseDois.JA_PROCESSADO_FASE_2,
                motivo="Item ja concluido localmente na Fase 2; sera preservado no checkpoint.",
                status_site="nao_validado_checkpoint_local",
                origem_decisao="checkpoint_local",
                item_excel=(indice_excel, tabela),
            )

        inicio_validacao = time.time()
        timestamp_inicio = agora_iso()
        try:
            filtro_reaplicado = self.pagina_tabelas.garantir_contexto_fase_dois(
                tabela.data_inicio,
                tabela.data_fim,
            )
            self.pagina_tabelas.pesquisar_por_nome(tabela.nome)
            if not self.pagina_tabelas.validar_filtro_vigencia_aplicado(
                tabela.data_inicio,
                tabela.data_fim,
            ):
                raise RuntimeError(
                    "Filtro de vigencia foi perdido durante a validacao do item."
                )
            self.pagina_tabelas.aguardar_resultado_pesquisa()
            total_resultados = self.pagina_tabelas.obter_total_tabelas()
            linhas = self.pagina_tabelas.obter_linhas_tabela()

            if total_resultados <= 0 or not linhas:
                return ResultadoValidacaoItemFaseDois(
                    indice_excel=indice_excel,
                    nome_tabela=tabela.nome,
                    data_inicio=tabela.data_inicio,
                    data_fim=tabela.data_fim,
                    decisao=DecisaoElegibilidadeFaseDois.NAO_ENCONTRADO_NO_SITE,
                    motivo=(
                        "O site nao retornou nenhuma linha para o nome informado "
                        f"sob a vigencia {tabela.data_inicio} - {tabela.data_fim}."
                    ),
                    status_site="sem_resultado_pesquisa",
                    origem_decisao="site",
                    detalhes_site={
                        "filtro_reaplicado": str(filtro_reaplicado).lower(),
                        "total_resultados": str(total_resultados),
                    },
                    item_excel=(indice_excel, tabela),
                )

            nome_alvo = self._normalizar_nome(tabela.nome)
            linhas_nome_exato = [
                linha
                for linha in linhas
                if self._normalizar_nome(self.pagina_tabelas.extrair_nome_linha(linha)) == nome_alvo
            ]
            if not linhas_nome_exato:
                nomes_encontrados = [
                    self.pagina_tabelas.extrair_nome_linha(linha).strip()
                    for linha in linhas[:3]
                ]
                return ResultadoValidacaoItemFaseDois(
                    indice_excel=indice_excel,
                    nome_tabela=tabela.nome,
                    data_inicio=tabela.data_inicio,
                    data_fim=tabela.data_fim,
                    decisao=DecisaoElegibilidadeFaseDois.NOME_DIVERGENTE,
                    motivo=(
                        "O site retornou resultados, mas nenhum com nome exato. "
                        f"Exemplos encontrados: {', '.join(filter(None, nomes_encontrados)) or 'nenhum'}"
                    ),
                    status_site="resultado_divergente",
                    origem_decisao="site",
                    detalhes_site={
                        "filtro_reaplicado": str(filtro_reaplicado).lower(),
                        "total_resultados": str(total_resultados),
                    },
                    item_excel=(indice_excel, tabela),
                )

            correspondentes: list[tuple[object, str]] = []
            vigencias_divergentes: list[str] = []
            for linha in linhas_nome_exato:
                vigencia_linha = (
                    self.pagina_tabelas.extrair_vigencia_linha(linha)
                    or self.pagina_tabelas.extrair_assinatura_linha(linha)
                )
                if self.pagina_tabelas.intervalo_vigencia_corresponde(
                    vigencia_linha,
                    tabela.data_inicio,
                    tabela.data_fim,
                ):
                    correspondentes.append((linha, vigencia_linha))
                else:
                    vigencias_divergentes.append(vigencia_linha)

            if not correspondentes:
                return ResultadoValidacaoItemFaseDois(
                    indice_excel=indice_excel,
                    nome_tabela=tabela.nome,
                    data_inicio=tabela.data_inicio,
                    data_fim=tabela.data_fim,
                    decisao=DecisaoElegibilidadeFaseDois.VIGENCIA_DIVERGENTE,
                    motivo=(
                        "Existe item com nome correspondente no site, mas a vigencia nao bate. "
                        f"Esperado: {tabela.data_inicio} - {tabela.data_fim} | "
                        f"Encontrado: {', '.join(filter(None, vigencias_divergentes[:3])) or 'vazio'}"
                    ),
                    status_site="vigencia_divergente",
                    origem_decisao="site",
                    detalhes_site={
                        "filtro_reaplicado": str(filtro_reaplicado).lower(),
                        "total_resultados": str(total_resultados),
                    },
                    item_excel=(indice_excel, tabela),
                )

            if len(correspondentes) > 1:
                assinaturas = [
                    self.pagina_tabelas.extrair_assinatura_linha(linha)
                    for linha, _ in correspondentes[:3]
                ]
                return ResultadoValidacaoItemFaseDois(
                    indice_excel=indice_excel,
                    nome_tabela=tabela.nome,
                    data_inicio=tabela.data_inicio,
                    data_fim=tabela.data_fim,
                    decisao=DecisaoElegibilidadeFaseDois.DUPLICADO_NO_SITE,
                    motivo=(
                        "Ha mais de um item com nome e vigencia compativeis no site; "
                        "o reajuste automatico nao e seguro."
                    ),
                    status_site="duplicado_no_site",
                    origem_decisao="site",
                    assinatura_site=" | ".join(filter(None, assinaturas)),
                    detalhes_site={
                        "filtro_reaplicado": str(filtro_reaplicado).lower(),
                        "total_resultados": str(total_resultados),
                    },
                    item_excel=(indice_excel, tabela),
                )

            linha, _vigencia_linha = correspondentes[0]
            try:
                assinatura = self.pagina_tabelas.validar_linha_para_reajuste(
                    linha,
                    tabela.nome,
                    tabela.data_inicio,
                    tabela.data_fim,
                )
            except Exception as erro_linha:
                mensagem = str(erro_linha)
                mensagem_normalizada = mensagem.lower()
                decisao = DecisaoElegibilidadeFaseDois.NAO_PRONTO_PARA_FASE_2
                if "vigencia divergente" in mensagem_normalizada:
                    decisao = DecisaoElegibilidadeFaseDois.VIGENCIA_DIVERGENTE
                elif "nome esperado" in mensagem_normalizada or "nome exato" in mensagem_normalizada:
                    decisao = DecisaoElegibilidadeFaseDois.NOME_DIVERGENTE
                return ResultadoValidacaoItemFaseDois(
                    indice_excel=indice_excel,
                    nome_tabela=tabela.nome,
                    data_inicio=tabela.data_inicio,
                    data_fim=tabela.data_fim,
                    decisao=decisao,
                    motivo=mensagem[:500],
                    status_site="linha_nao_acionavel",
                    origem_decisao="site",
                    detalhes_site={
                        "filtro_reaplicado": str(filtro_reaplicado).lower(),
                        "total_resultados": str(total_resultados),
                    },
                    item_excel=(indice_excel, tabela),
                )

            return ResultadoValidacaoItemFaseDois(
                indice_excel=indice_excel,
                nome_tabela=tabela.nome,
                data_inicio=tabela.data_inicio,
                data_fim=tabela.data_fim,
                decisao=DecisaoElegibilidadeFaseDois.ELEGIVEL,
                motivo="Item validado no site e pronto para a Fase 2.",
                status_site="pronto_para_fase_2",
                assinatura_site=assinatura,
                origem_decisao="site",
                confirmado_no_site=True,
                detalhes_site={
                    "filtro_reaplicado": str(filtro_reaplicado).lower(),
                    "total_resultados": str(total_resultados),
                    "tempo_validacao_ms": str(int(round((time.time() - inicio_validacao) * 1000))),
                },
                item_excel=(indice_excel, tabela),
            )
        except Exception as erro:
            return ResultadoValidacaoItemFaseDois(
                indice_excel=indice_excel,
                nome_tabela=tabela.nome,
                data_inicio=tabela.data_inicio,
                data_fim=tabela.data_fim,
                decisao=DecisaoElegibilidadeFaseDois.ERRO_TECNICO_VALIDACAO,
                motivo=str(erro)[:500],
                status_site="erro_validacao",
                origem_decisao="site",
                detalhes_site={
                    "timestamp_inicio": timestamp_inicio,
                    "tempo_validacao_ms": str(int(round((time.time() - inicio_validacao) * 1000))),
                },
                item_excel=(indice_excel, tabela),
            )

    def _registrar_resultado_item(
        self,
        *,
        resultado: ResultadoValidacaoItemFaseDois,
        total_planejado: int,
        run_id: str,
        grupo_vigencia: str,
        checkpoint: Optional["GestorCheckpoint"] = None,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> None:
        estado_item = (
            checkpoint.obter_estado_item(resultado.indice_excel, resultado.nome_tabela)
            if checkpoint
            else {}
        )
        tentativas = (
            checkpoint.contar_tentativas(2, resultado.indice_excel, resultado.nome_tabela) + 1
            if checkpoint
            else 1
        )
        extras = {
            "tipo_registro": "validacao",
            "fase_execucao_ui": "validacao_fase_2",
            "contabilizar_progresso": False,
            "decisao_elegibilidade": resultado.decisao.value,
            "motivo_decisao": resultado.motivo,
            "status_site": resultado.status_site,
            "assinatura_site": resultado.assinatura_site,
            "amostrado": resultado.amostrado,
            "janela_validacao": resultado.janela_validacao,
            "origem_decisao": resultado.origem_decisao,
            "confirmado_no_site": resultado.confirmado_no_site,
            "grupo_vigencia": grupo_vigencia,
            "status_ui": self._status_ui_validacao(resultado.decisao),
            "processo": "reajuste_tabelas",
        }
        contexto = ContextoTabelaProcessamento(
            fase=2,
            indice=resultado.indice_excel,
            nome_tabela=resultado.nome_tabela,
            total=total_planejado,
            dados_extras=extras,
            fase_execucao=FaseExecucao.FASE_2,
            tipo_execucao=tipo_execucao,
            tentativas=tentativas,
            status_fase_1=estado_item.get("fase_1", StatusExecucao.PENDENTE.value),
            status_fase_2=estado_item.get("fase_2", StatusExecucao.PENDENTE.value),
            reprocessado=bool(estado_item.get("reprocessado")) or (
                tipo_execucao == TipoExecucao.REPROCESSAMENTO
            ),
        )
        self.observador.registrar_processando(contexto)
        mensagem_ui = self._mensagem_ui_validacao(resultado)
        if resultado.decisao == DecisaoElegibilidadeFaseDois.ERRO_TECNICO_VALIDACAO:
            self.observador.registrar_falha(contexto, mensagem_ui)
        else:
            self.observador.registrar_sucesso(contexto, mensagem_ui)

        self.gestor.registrar_validacao(
            run_id=run_id,
            indice=resultado.indice_excel,
            nome_tabela=resultado.nome_tabela,
            decisao_elegibilidade=resultado.decisao.value,
            motivo_decisao=resultado.motivo,
            grupo_vigencia=grupo_vigencia,
            status_site=resultado.status_site,
            assinatura_site=resultado.assinatura_site,
            amostrado=resultado.amostrado,
            janela_validacao=resultado.janela_validacao,
            origem_decisao=resultado.origem_decisao,
            tipo_execucao=tipo_execucao,
            tentativas=tentativas,
            status_fase_1=contexto.status_fase_1,
            status_fase_2=contexto.status_fase_2,
        )
        self.log_estruturado.fase2(
            "F2_ITEM_DECISAO",
            resultado.indice_excel,
            resultado.nome_tabela,
            status=resultado.decisao.value,
            grupo_vigencia=grupo_vigencia,
            janela_validacao=resultado.janela_validacao,
            status_site=resultado.status_site,
            origem_decisao=resultado.origem_decisao,
        )

    def _registrar_resumo_grupo(self, resultado: ResultadoValidacaoGrupoFaseDois) -> None:
        self.log_estruturado.fase2(
            "F2_GRUPO_RESUMO",
            status=resultado.decisao_final.upper(),
            vigencia=resultado.filtro_vigencia,
            total_excel=str(resultado.total_itens_excel),
            validados=str(resultado.total_validados),
            elegiveis=str(resultado.total_elegiveis),
            divergentes=str(resultado.total_divergentes),
            duplicados=str(resultado.total_duplicados),
            nao_encontrados=str(resultado.total_nao_encontrados),
            erros_tecnicos=str(resultado.total_erros_tecnicos),
        )
        if resultado.total_elegiveis == 0:
            self.log_estruturado.fase2(
                "F2_SEM_ELEGIVEIS",
                status="ALERTA",
                vigencia=resultado.filtro_vigencia,
                decisao_final=resultado.decisao_final,
            )

    def _etapa(self, nome: str, descricao: str, contexto: dict):
        if self.rastreador is None:
            return _EtapaNula()
        return self.rastreador.etapa(nome, descricao, contexto)

    @staticmethod
    def _selecionar_posicoes(total: int, quantidade: int) -> list[int]:
        if total <= 0 or quantidade <= 0:
            return []
        if quantidade >= total:
            return list(range(total))
        if not config.FASE2_AMOSTRAGEM_DISTRIBUIDA:
            return list(range(quantidade))
        posicoes: list[int] = []
        for indice in range(quantidade):
            if quantidade == 1:
                posicao = 0
            else:
                posicao = round(indice * (total - 1) / (quantidade - 1))
            if posicao not in posicoes:
                posicoes.append(posicao)
        return posicoes

    @classmethod
    def _selecionar_posicoes_restantes(cls, restantes: list[int], quantidade: int) -> list[int]:
        if quantidade <= 0 or not restantes:
            return []
        if quantidade >= len(restantes):
            return list(restantes)
        if not config.FASE2_AMOSTRAGEM_DISTRIBUIDA:
            return list(restantes[:quantidade])
        indices_relativos = cls._selecionar_posicoes(len(restantes), quantidade)
        return [restantes[indice] for indice in indices_relativos]

    @staticmethod
    def _ha_elegivel(resultados_por_indice: dict[int, ResultadoValidacaoItemFaseDois]) -> bool:
        return any(resultado.elegivel for resultado in resultados_por_indice.values())

    @staticmethod
    def _normalizar_nome(valor: str) -> str:
        return " ".join((valor or "").strip().upper().split())

    @staticmethod
    def _mensagem_ui_validacao(resultado: ResultadoValidacaoItemFaseDois) -> str:
        mensagens = {
            DecisaoElegibilidadeFaseDois.ELEGIVEL: "Elegivel na validacao do site",
            DecisaoElegibilidadeFaseDois.NAO_ENCONTRADO_NO_SITE: "Nao encontrado no site",
            DecisaoElegibilidadeFaseDois.NAO_PRONTO_PARA_FASE_2: "Encontrado, mas nao pronto para Fase 2",
            DecisaoElegibilidadeFaseDois.VIGENCIA_DIVERGENTE: "Vigencia divergente no site",
            DecisaoElegibilidadeFaseDois.NOME_DIVERGENTE: "Nome divergente no site",
            DecisaoElegibilidadeFaseDois.DUPLICADO_NO_SITE: "Duplicidade detectada no site",
            DecisaoElegibilidadeFaseDois.JA_PROCESSADO_FASE_2: "Ja processado localmente na Fase 2",
            DecisaoElegibilidadeFaseDois.ERRO_TECNICO_VALIDACAO: "Erro tecnico na validacao",
        }
        base = mensagens.get(resultado.decisao, resultado.decisao.value)
        return f"{base}: {resultado.motivo}" if resultado.motivo else base

    @staticmethod
    def _status_ui_validacao(decisao: DecisaoElegibilidadeFaseDois) -> str:
        if decisao == DecisaoElegibilidadeFaseDois.ERRO_TECNICO_VALIDACAO:
            return "Erro"
        if decisao in {
            DecisaoElegibilidadeFaseDois.ELEGIVEL,
            DecisaoElegibilidadeFaseDois.JA_PROCESSADO_FASE_2,
        }:
            return "Validado"
        return "Alerta"
