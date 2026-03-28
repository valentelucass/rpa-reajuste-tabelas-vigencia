"""
Orquestrador principal da automação.
Composition Root: monta todas as dependências e executa as duas fases.
"""

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import config
from src.aplicacao.fase_execucao import FaseExecucao, TipoExecucao
from src.aplicacao.gestor_checkpoint import GestorCheckpoint
from src.aplicacao.modo_execucao import ModoExecucao
from src.infraestrutura.acoes_navegador import AcoesNavegador
from src.infraestrutura.caminhos import LOGS_DIR, REPORTS_DIR
from src.infraestrutura.fabrica_navegador import FabricaNavegador
from src.infraestrutura.fabrica_registrador_execucao import criar_logger
from src.infraestrutura.logger_estruturado import LoggerEstruturado
from src.infraestrutura.preparador_arquivos_execucao import PreparadorArquivosExecucao
from src.infraestrutura.rastreador_etapas import RastreadorEtapas
from src.infraestrutura.retencao_artefatos import RetencaoArtefatos
from src.monitoramento.observador_execucao import (
    ContratoObservadorExecucao,
    ObservadorNulo,
)
from src.paginas.pagina_edicao_tabela import PaginaEdicaoTabela
from src.paginas.pagina_login import PaginaLogin
from src.paginas.pagina_reajuste import PaginaReajuste
from src.paginas.pagina_tabelas_cliente import PaginaTabelasCliente
from src.servicos.aplicador_reajuste import AplicadorReajuste
from src.servicos.criador_copia_tabela import CriadorCopiaTabela
from src.servicos.gestor_ocorrencias import GestorOcorrenciasProcessamento
from src.servicos.leitor_excel import LeitorExcel
from src.servicos.processador_fase_dois import ProcessadorFaseDois, RelatorioFaseDois
from src.servicos.processador_fase_um import ProcessadorFaseUm
from src.servicos.validador_elegibilidade_fase_dois import ValidadorElegibilidadeFaseDois


class AutomacaoTabelaCliente:
    """
    Orquestrador do caso de uso completo:
    1. Ler Excel
    2. Login
    3. Fase 1: Criar cópias com nome e vigência corretos
    4. Fase 2: Aplicar reajuste em cada cópia
    """

    def __init__(
        self,
        caminho_excel: str | Path,
        observador: Optional[ContratoObservadorExecucao] = None,
        modo: ModoExecucao = ModoExecucao.MODO_COMPLETO,
        checkpoint: Optional[GestorCheckpoint] = None,
    ) -> None:
        self.caminho_excel = Path(caminho_excel)
        self.observador = observador or ObservadorNulo()
        self.modo = modo
        self.checkpoint = checkpoint
        self.run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"

        # Serão criados em _criar_componentes_execucao()
        self.logger: Optional[logging.Logger] = None
        self.log_estruturado: Optional[LoggerEstruturado] = None
        self.driver = None
        self.acoes: Optional[AcoesNavegador] = None
        self.rastreador: Optional[RastreadorEtapas] = None

        # Páginas
        self.pagina_login: Optional[PaginaLogin] = None
        self.pagina_tabelas: Optional[PaginaTabelasCliente] = None
        self.pagina_edicao: Optional[PaginaEdicaoTabela] = None
        self.pagina_reajuste: Optional[PaginaReajuste] = None

        # Serviços
        self.leitor_excel: Optional[LeitorExcel] = None
        self.gestor: Optional[GestorOcorrenciasProcessamento] = None
        self.criador: Optional[CriadorCopiaTabela] = None
        self.aplicador: Optional[AplicadorReajuste] = None
        self.processador_f1: Optional[ProcessadorFaseUm] = None
        self.processador_f2: Optional[ProcessadorFaseDois] = None
        self.validador_f2: Optional[ValidadorElegibilidadeFaseDois] = None

        # Relatorio da Fase 2 (preenchido apos execucao)
        self._relatorio_fase_dois: Optional[dict] = None

    # ------------------------------------------------------------------
    # Ponto de entrada principal
    # ------------------------------------------------------------------

    def executar(self) -> None:
        """Executa a automação conforme o modo selecionado."""
        try:
            config.recarregar_configuracoes(sobrescrever_env=True)
            self._validar_pre_requisitos()
            self._preparar_artefatos()
            self._iniciar_logger()
            self.logger.info(
                f"[run_id={self.run_id}] Iniciando automação — modo={self.modo.value}"
            )
            self.observador.registrar_sistema(
                f"Iniciando automação — modo: {self.modo.value}"
            )

            self._iniciar_navegador()
            self._criar_componentes_execucao()

            # Lê o Excel antes de abrir qualquer página
            self.leitor_excel.validar()
            tabelas = self.leitor_excel.ler_aba_um()
            componentes = self.leitor_excel.ler_aba_dois()

            self.logger.info(f"Excel lido: {len(tabelas)} tabela(s), {len(componentes)} componente(s)")
            self.observador.registrar_sistema(
                f"Excel carregado: {len(tabelas)} tabela(s) | {len(componentes)} componente(s)"
            )

            if self.checkpoint:
                self.checkpoint.atualizar_total_linhas(len(tabelas))
                self.checkpoint.sincronizar_tabelas(tabelas)

            # Login
            with self.rastreador.etapa("login", "Realizando login"):
                self.pagina_login.abrir()
                self.pagina_login.autenticar()

            itens_fase_um = self._obter_itens_para_execucao(FaseExecucao.FASE_1, tabelas)
            if self.modo in (ModoExecucao.MODO_COMPLETO, ModoExecucao.MODO_FASE1):
                self._executar_fase_um(itens_fase_um)

            itens_fase_dois = self._obter_itens_para_execucao(FaseExecucao.FASE_2, tabelas)
            if self.modo in (ModoExecucao.MODO_COMPLETO, ModoExecucao.MODO_FASE2):
                self._executar_fase_dois_interna(itens_fase_dois, componentes)

            self._registrar_alertas_analise()

        except Exception as erro:
            tb = traceback.format_exc()
            if self.logger:
                self.logger.error(f"Falha crítica na execução principal:\n{tb}")
            if self.rastreador:
                self.rastreador.registrar_erro(erro, tb=tb)
            self.observador.registrar_sistema(f"Erro crítico: {erro}")
            raise

        finally:
            self._encerrar()

    def executar_fase_dois(self) -> dict:
        """
        Executa somente a Fase 2 com agrupamento por vigencia.
        Wrapper que delega para executar(modo=MODO_FASE2).
        Mantido para compatibilidade com run_phase2_validation.py.
        """
        try:
            config.recarregar_configuracoes(sobrescrever_env=True)
            self._validar_pre_requisitos()
            self._preparar_artefatos()
            self._iniciar_logger()
            self.logger.info(f"[run_id={self.run_id}] Iniciando execucao isolada da Fase 2")
            self.observador.registrar_sistema("Iniciando execucao isolada da Fase 2...")

            self._iniciar_navegador()
            self._criar_componentes_execucao()

            self.leitor_excel.validar()
            tabelas = self.leitor_excel.ler_aba_um()
            componentes = self.leitor_excel.ler_aba_dois()

            self.logger.info(f"Excel lido: {len(tabelas)} tabela(s), {len(componentes)} componente(s)")
            self.observador.registrar_sistema(
                f"Excel carregado: {len(tabelas)} tabela(s) | {len(componentes)} componente(s)"
            )

            if self.checkpoint:
                self.checkpoint.atualizar_total_linhas(len(tabelas))
                self.checkpoint.sincronizar_tabelas(tabelas)

            with self.rastreador.etapa("login", "Realizando login"):
                self.pagina_login.abrir()
                self.pagina_login.autenticar()

            itens_fase_dois = self._obter_itens_para_execucao(FaseExecucao.FASE_2, tabelas)
            relatorio_final = self._executar_fase_dois_interna(itens_fase_dois, componentes)
            self._registrar_alertas_analise()
            return relatorio_final or {}

        except Exception as erro:
            tb = traceback.format_exc()
            if self.logger:
                self.logger.error(f"Falha critica na execucao isolada da Fase 2:\n{tb}")
            if self.rastreador:
                self.rastreador.registrar_erro(erro, tb=tb)
            self.observador.registrar_sistema(f"Erro critico: {erro}")
            raise

        finally:
            self._encerrar()

    # ------------------------------------------------------------------
    # Execução interna das fases
    # ------------------------------------------------------------------

    def _executar_fase_um(
        self,
        itens: list[tuple[int, object]],
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> None:
        """Executa a Fase 1: criação de cópias."""
        if not itens:
            self.observador.definir_total_fase_um(0)
            self.observador.registrar_sistema("Fase 1 sem itens pendentes para processar.")
            return
        self.observador.registrar_sistema("Iniciando Fase 1: criação de cópias")
        with self.rastreador.etapa("navegacao_fase_um", "Navegando para tabelas de cliente"):
            self.pagina_tabelas.acessar()
            self.pagina_tabelas.preparar_filtros_fase_um()

        self.processador_f1.processar(
            itens,
            self.run_id,
            checkpoint=self.checkpoint,
            tipo_execucao=tipo_execucao,
        )

    def _executar_fase_dois_interna(
        self,
        itens: list[tuple[int, object]],
        componentes: list,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> dict:
        """Executa a Fase 2 com pre-validacao por grupo de vigencia."""
        if not itens:
            self.observador.definir_total_fase_dois(0)
            mensagem = self._mensagem_sem_itens_fase_dois()
            self.observador.registrar_sistema(mensagem)
            relatorio_final = self._finalizar_relatorio_fase_dois([])
            self._emitir_alerta_sem_elegiveis(relatorio_final)
            return relatorio_final

        self.observador.registrar_sistema(
            "Iniciando Fase 2: validacao de elegibilidade no site e aplicacao de reajuste"
        )
        relatorios_grupo: list[RelatorioFaseDois] = []
        try:
            for grupo in self._agrupar_itens_fase_dois(itens):
                data_inicio = grupo["data_inicio"]
                data_fim = grupo["data_fim"]
                itens_grupo = grupo["itens"]
                percentual = itens_grupo[0][1].percentual if itens_grupo else 0.0

                with self.rastreador.etapa(
                    "validar_elegibilidade_fase_dois",
                    "Validando elegibilidade da Fase 2 no site",
                    {
                        "data_inicio": data_inicio,
                        "data_fim": data_fim,
                        "quantidade_itens_excel": len(itens_grupo),
                        "modo_validacao": config.FASE2_VALIDACAO_MODO,
                    },
                ):
                    pre_validacao = self.validador_f2.validar_grupo(
                        itens_grupo,
                        self.run_id,
                        data_inicio,
                        data_fim,
                        checkpoint=self.checkpoint,
                        tipo_execucao=tipo_execucao,
                    )

                relatorio_grupo = RelatorioFaseDois(
                    run_id=self.run_id,
                    filtro_vigencia=pre_validacao.filtro_vigencia,
                    percentual=percentual,
                    pre_validacao=pre_validacao.to_dict(),
                    total_registros_filtrados=pre_validacao.total_registros_filtrados,
                )

                itens_elegiveis_confirmados = pre_validacao.itens_elegiveis()
                if not itens_elegiveis_confirmados:
                    relatorio_grupo.validar_consistencia()
                    relatorios_grupo.append(relatorio_grupo)
                    self.observador.registrar_sistema(
                        "Grupo sem elegiveis na Fase 2: "
                        f"{pre_validacao.filtro_vigencia} | "
                        f"validados={pre_validacao.total_validados} | "
                        f"divergentes={pre_validacao.total_divergentes} | "
                        f"nao_encontrados={pre_validacao.total_nao_encontrados}"
                    )
                    continue

                with self.rastreador.etapa(
                    "processar_itens_elegiveis",
                    "Processando grupo elegivel da Fase 2",
                    {
                        "data_inicio": data_inicio,
                        "data_fim": data_fim,
                        "quantidade_grupo": len(itens_grupo),
                        "quantidade_elegiveis_confirmados": len(itens_elegiveis_confirmados),
                        "quantidade_validados": pre_validacao.total_validados,
                    },
                ):
                    relatorio_processamento = self.processador_f2.processar(
                        itens_grupo,
                        componentes,
                        self.run_id,
                        pre_validacao.total_registros_filtrados,
                        pre_validacao.filtro_vigencia,
                        data_inicio,
                        data_fim,
                        checkpoint=self.checkpoint,
                        tipo_execucao=tipo_execucao,
                    )

                relatorio_processamento.pre_validacao = pre_validacao.to_dict()
                relatorios_grupo.append(relatorio_processamento)

            relatorio_final = self._finalizar_relatorio_fase_dois(relatorios_grupo)
            self._emitir_alerta_sem_elegiveis(relatorio_final)
            return relatorio_final
        except Exception as erro:
            relatorio_final = self._consolidar_relatorio_fase_dois(relatorios_grupo)
            relatorio_final["erro_critico"] = str(erro)
            caminho_json, caminho_md = self._salvar_relatorio_fase_dois(relatorio_final)
            relatorio_final["artefatos"] = self._artefatos_fase_dois(caminho_json, caminho_md)
            self._relatorio_fase_dois = relatorio_final
            raise

    # ------------------------------------------------------------------
    # Composition Root
    # ------------------------------------------------------------------

    def _criar_componentes_execucao(self) -> None:
        """Monta manualmente o grafo de dependências da execução."""
        # Infraestrutura
        self.acoes = AcoesNavegador(self.driver, self.logger)
        self.rastreador = RastreadorEtapas(self.run_id, self.driver)
        self.log_estruturado = LoggerEstruturado(self.logger)

        # Páginas
        self.pagina_login = PaginaLogin(self.acoes, self.logger)
        self.pagina_tabelas = PaginaTabelasCliente(self.acoes, self.logger)
        self.pagina_edicao = PaginaEdicaoTabela(self.acoes, self.logger)
        self.pagina_reajuste = PaginaReajuste(self.acoes, self.logger)

        # Serviços
        self.leitor_excel = LeitorExcel(self.caminho_excel)
        self.gestor = GestorOcorrenciasProcessamento(self.acoes, self.logger)

        self.criador = CriadorCopiaTabela(
            self.pagina_tabelas,
            self.pagina_edicao,
            self.rastreador,
            self.logger
        )
        self.aplicador = AplicadorReajuste(
            self.pagina_tabelas,
            self.pagina_reajuste,
            self.rastreador,
            self.logger
        )
        self.processador_f1 = ProcessadorFaseUm(
            self.criador,
            self.gestor,
            self.observador,
            self.logger
        )
        self.processador_f2 = ProcessadorFaseDois(
            self.pagina_tabelas,
            self.aplicador,
            self.gestor,
            self.observador,
            self.logger
        )
        self.validador_f2 = ValidadorElegibilidadeFaseDois(
            self.pagina_tabelas,
            self.gestor,
            self.observador,
            self.rastreador,
            self.logger,
        )

    def _agrupar_tabelas_fase_dois(self, tabelas: list) -> list[dict]:
        """Mantido por compatibilidade: agrupa tabelas simples por vigencia."""
        return self._agrupar_itens_fase_dois(self._normalizar_itens(tabelas))

    def _agrupar_itens_fase_dois(self, itens: list[tuple[int, object]]) -> list[dict]:
        """Agrupa itens da Fase 2 por vigencia, preservando indice do Excel."""
        grupos: dict[tuple[str, str], dict] = {}
        for indice_excel, tabela in itens:
            chave = (tabela.data_inicio, tabela.data_fim)
            if chave not in grupos:
                grupos[chave] = {
                    "data_inicio": tabela.data_inicio,
                    "data_fim": tabela.data_fim,
                    "itens": [],
                }
            grupos[chave]["itens"].append((indice_excel, tabela))
        return list(grupos.values())

    def _consolidar_relatorio_fase_dois(self, relatorios_grupo: list[RelatorioFaseDois]) -> dict:
        """Consolida o resultado da Fase 2 em um unico relatorio estruturado."""
        detalhes = []
        tabelas_ignoradas: set[str] = set()
        itens_sem_log: set[str] = set()
        filtros = []
        pre_validacoes = []
        total_registros_filtrados = 0
        total_encontradas = 0
        total_processadas = 0
        total_com_erro = 0
        ordem_valida = True
        total_elegiveis_confirmados = 0
        total_nao_encontrados = 0
        total_nao_prontos = 0
        total_duplicados = 0
        total_divergentes = 0
        total_ja_processados = 0
        total_erros_tecnicos_validacao = 0
        grupos_sem_elegiveis = 0
        grupos_com_erro_tecnico = 0

        for relatorio in relatorios_grupo:
            relatorio.validar_consistencia()
            dados = relatorio.to_dict()
            pre_validacao = dados.get("pre_validacao") or {}
            filtros.append({
                "filtro_vigencia": dados["filtro_vigencia"],
                "percentual": dados["percentual"],
                "total_registros_filtrados": dados["total_registros_filtrados"],
                "total_encontradas": dados["total_encontradas"],
                "total_processadas": dados["total_processadas"],
                "total_com_erro": dados["total_com_erro"],
            })
            if pre_validacao:
                pre_validacoes.append(pre_validacao)
                total_elegiveis_confirmados += int(pre_validacao.get("total_elegiveis", 0))
                total_nao_encontrados += int(pre_validacao.get("total_nao_encontrados", 0))
                total_nao_prontos += int(pre_validacao.get("total_nao_prontos", 0))
                total_duplicados += int(pre_validacao.get("total_duplicados", 0))
                total_divergentes += int(pre_validacao.get("total_divergentes", 0))
                total_ja_processados += int(pre_validacao.get("total_ja_processados", 0))
                total_erros_tecnicos_validacao += int(pre_validacao.get("total_erros_tecnicos", 0))
                if pre_validacao.get("decisao_final") in {"sem_elegiveis", "sem_resultados_no_site"}:
                    grupos_sem_elegiveis += 1
                if pre_validacao.get("decisao_final") == "erro_tecnico_validacao":
                    grupos_com_erro_tecnico += 1
            detalhes.extend(dados["detalhamento"])
            tabelas_ignoradas.update(dados["tabelas_ignoradas"])
            itens_sem_log.update(dados["itens_sem_log"])
            total_registros_filtrados += dados["total_registros_filtrados"]
            total_encontradas += dados["total_encontradas"]
            total_processadas += dados["total_processadas"]
            total_com_erro += dados["total_com_erro"]
            ordem_valida = ordem_valida and dados["ordem_valida"]

        funcional = (
            total_encontradas > 0
            and total_processadas > 0
            and total_com_erro == 0
            and ordem_valida
            and not itens_sem_log
        )
        if total_elegiveis_confirmados == 0 and pre_validacoes:
            status_execucao = "concluido_com_alerta"
        elif total_com_erro > 0 or total_erros_tecnicos_validacao > 0:
            status_execucao = "concluido_com_alerta"
        elif funcional:
            status_execucao = "concluido"
        else:
            status_execucao = "concluido_parcial"

        return {
            "run_id": self.run_id,
            "fase": 2,
            "funcional": funcional,
            "status_execucao": status_execucao,
            "resumo": {
                "total_registros_filtrados": total_registros_filtrados,
                "total_encontradas": total_encontradas,
                "total_processadas": total_processadas,
                "total_com_erro": total_com_erro,
            },
            "validacao": {
                "filtro_aplicado": bool(filtros),
                "resultados_encontrados": any(
                    pre.get("resultado_site") == "resultados_filtrados"
                    for pre in pre_validacoes
                ),
                "execucao_ordenada": ordem_valida,
                "itens_sem_log": sorted(itens_sem_log),
                "total_elegiveis_confirmados": total_elegiveis_confirmados,
                "total_nao_encontrados": total_nao_encontrados,
                "total_nao_prontos": total_nao_prontos,
                "total_duplicados": total_duplicados,
                "total_divergentes": total_divergentes,
                "total_ja_processados": total_ja_processados,
                "total_erros_tecnicos_validacao": total_erros_tecnicos_validacao,
                "grupos_sem_elegiveis": grupos_sem_elegiveis,
                "grupos_com_erro_tecnico_validacao": grupos_com_erro_tecnico,
            },
            "pre_validacao": pre_validacoes,
            "filtros_processados": filtros,
            "tabelas_ignoradas": sorted(tabelas_ignoradas),
            "detalhamento": detalhes,
        }

    def _salvar_relatorio_fase_dois(self, relatorio: dict) -> tuple[Path, Path]:
        """Persistencia do relatorio estruturado da Fase 2."""
        caminho_json = REPORTS_DIR / f"fase2_relatorio_{self.run_id}.json"
        caminho_md = REPORTS_DIR / f"fase2_relatorio_{self.run_id}.md"
        caminho_json.write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        caminho_md.write_text(
            self._formatar_relatorio_fase_dois(relatorio),
            encoding="utf-8",
        )
        return caminho_json, caminho_md

    def _artefatos_fase_dois(self, caminho_json: Path, caminho_md: Path) -> dict:
        return {
            "relatorio_json": str(caminho_json),
            "relatorio_md": str(caminho_md),
            "processamento_csv": str(LOGS_DIR / "processamento.csv"),
            "execution_trace": str(LOGS_DIR / "execution_trace.json"),
            "errors_log": str(REPORTS_DIR / "errors.log"),
        }

    def _formatar_relatorio_fase_dois(self, relatorio: dict) -> str:
        """Gera uma versao Markdown enxuta do relatorio final."""
        resumo = relatorio["resumo"]
        validacao = relatorio["validacao"]
        linhas = [
            "# Relatorio Fase 2",
            "",
            "## Resumo",
            f"- Run ID: {relatorio['run_id']}",
            f"- Funcional: {'SIM' if relatorio['funcional'] else 'NAO'}",
            f"- Status execucao: {relatorio.get('status_execucao', 'desconhecido')}",
            f"- Total filtradas: {resumo['total_registros_filtrados']}",
            f"- Total encontradas: {resumo['total_encontradas']}",
            f"- Total processadas: {resumo['total_processadas']}",
            f"- Total com erro: {resumo['total_com_erro']}",
            "",
            "## Validacao",
            f"- Filtro aplicado: {'SIM' if validacao['filtro_aplicado'] else 'NAO'}",
            f"- Resultados encontrados: {'SIM' if validacao['resultados_encontrados'] else 'NAO'}",
            f"- Execucao ordenada: {'SIM' if validacao['execucao_ordenada'] else 'NAO'}",
            f"- Elegiveis confirmados: {validacao['total_elegiveis_confirmados']}",
            f"- Nao encontrados: {validacao['total_nao_encontrados']}",
            f"- Nao prontos: {validacao['total_nao_prontos']}",
            f"- Duplicados: {validacao['total_duplicados']}",
            f"- Divergentes: {validacao['total_divergentes']}",
            f"- Ja processados localmente: {validacao['total_ja_processados']}",
            f"- Erros tecnicos de validacao: {validacao['total_erros_tecnicos_validacao']}",
            f"- Itens sem log: {', '.join(validacao['itens_sem_log']) or 'Nenhum'}",
            "",
            "## Pre-validacao por Grupo",
        ]

        for grupo in relatorio.get("pre_validacao", []):
            linhas.append(
                "- "
                f"{grupo['filtro_vigencia']} | decisao={grupo['decisao_final']} | "
                f"elegiveis={grupo['total_elegiveis']} | "
                f"divergentes={grupo['total_divergentes']} | "
                f"nao_encontrados={grupo['total_nao_encontrados']}"
            )

        linhas.extend([
            "",
            "## Detalhamento",
        ])

        for item in relatorio["detalhamento"]:
            linhas.append(
                f"- {item['nome']} | status={item['status']} | erro={item.get('erro') or '-'}"
            )

        if relatorio["tabelas_ignoradas"]:
            linhas.extend([
                "",
                "## Tabelas Ignoradas",
            ])
            for nome in relatorio["tabelas_ignoradas"]:
                linhas.append(f"- {nome}")

        return "\n".join(linhas) + "\n"

    def _finalizar_relatorio_fase_dois(self, relatorios_grupo: list[RelatorioFaseDois]) -> dict:
        relatorio_final = self._consolidar_relatorio_fase_dois(relatorios_grupo)
        caminho_json, caminho_md = self._salvar_relatorio_fase_dois(relatorio_final)
        relatorio_final["artefatos"] = self._artefatos_fase_dois(caminho_json, caminho_md)
        self._relatorio_fase_dois = relatorio_final
        return relatorio_final

    def _emitir_alerta_sem_elegiveis(self, relatorio_final: Optional[dict]) -> None:
        if not relatorio_final:
            return
        validacao = relatorio_final.get("validacao", {})
        total_elegiveis = int(validacao.get("total_elegiveis_confirmados", 0) or 0)
        if total_elegiveis > 0:
            return
        mensagem = (
            "Fase 2 concluida sem itens elegiveis apos validacao do site. "
            f"Grupos sem elegiveis={validacao.get('grupos_sem_elegiveis', 0)} | "
            f"nao_encontrados={validacao.get('total_nao_encontrados', 0)} | "
            f"divergentes={validacao.get('total_divergentes', 0)} | "
            f"erros_tecnicos_validacao={validacao.get('total_erros_tecnicos_validacao', 0)}"
        )
        if self.logger:
            self.logger.warning(mensagem)
        self.observador.registrar_sistema(mensagem)

    # ------------------------------------------------------------------
    # Reprocessamento individual (chamado pela UI)
    # ------------------------------------------------------------------

    def reprocessar_tabela(self, nome_tabela: str) -> None:
        """
        Reprocessa o reajuste de uma tabela específica.
        Pressupõe que o navegador está ativo e autenticado.
        """
        config.recarregar_configuracoes(sobrescrever_env=True)

        tabelas, componentes = self._carregar_dados_excel()
        indice_excel, tabela_alvo = self._localizar_item_por_nome(tabelas, nome_tabela)
        if tabela_alvo is None:
            raise ValueError(f"Tabela '{nome_tabela}' não encontrada no Excel")

        if self.checkpoint:
            self.checkpoint.sincronizar_tabelas(tabelas)

        self._executar_fase_dois_interna(
            [(indice_excel, tabela_alvo)],
            componentes,
            tipo_execucao=TipoExecucao.REPROCESSAMENTO,
        )

        self.logger.info(f"Reprocessamento concluído: {nome_tabela}")

    def reprocessar_copia_tabela(self, nome_tabela: str) -> None:
        """
        Reprocessa a copia (Fase 1) de uma tabela específica.
        Pressupõe que o navegador está ativo e autenticado.
        """
        config.recarregar_configuracoes(sobrescrever_env=True)

        tabelas, _componentes = self._carregar_dados_excel()
        indice_excel, tabela_alvo = self._localizar_item_por_nome(tabelas, nome_tabela)
        if tabela_alvo is None:
            raise ValueError(f"Tabela '{nome_tabela}' não encontrada no Excel")

        if self.checkpoint:
            self.checkpoint.sincronizar_tabelas(tabelas)

        self._executar_fase_um(
            [(indice_excel, tabela_alvo)],
            tipo_execucao=TipoExecucao.REPROCESSAMENTO,
        )

        self.logger.info(f"Reprocessamento de cópia concluído: {nome_tabela}")

    def executar_reprocessamento(self, nome_tabela: str, fase: int) -> None:
        """
        Executa reprocessamento completo de uma tabela: abre navegador, faz login,
        reprocessa e encerra. Usado pelo worker de reprocessamento da UI.
        """
        try:
            config.recarregar_configuracoes(sobrescrever_env=True)
            self._validar_pre_requisitos()
            self._preparar_artefatos()
            self._iniciar_logger()
            self.logger.info(
                f"[REPROCESSAMENTO] Iniciando reprocessamento de '{nome_tabela}' fase={fase}"
            )

            self._iniciar_navegador()
            self._criar_componentes_execucao()

            with self.rastreador.etapa("login", "Realizando login"):
                self.pagina_login.abrir()
                self.pagina_login.autenticar()

            if self.checkpoint:
                tabelas, _componentes = self._carregar_dados_excel()
                self.checkpoint.atualizar_total_linhas(len(tabelas))
                self.checkpoint.sincronizar_tabelas(tabelas)

            fase_execucao = FaseExecucao.from_valor(fase)
            if fase_execucao is FaseExecucao.FASE_1:
                self.reprocessar_copia_tabela(nome_tabela)
            elif fase_execucao is FaseExecucao.FASE_2:
                self.reprocessar_tabela(nome_tabela)

            self.logger.info(f"[REPROCESSAMENTO] Concluído: '{nome_tabela}' fase={fase}")
            self._registrar_alertas_analise()

        except Exception as erro:
            if self.logger:
                self.logger.error(f"[REPROCESSAMENTO] Erro: {erro}")
            raise

        finally:
            self._encerrar()

    def executar_reprocessamento_falhas(self) -> None:
        """Reprocessa automaticamente todas as falhas, respeitando a ordem Fase 1 -> Fase 2."""
        try:
            config.recarregar_configuracoes(sobrescrever_env=True)
            self._validar_pre_requisitos()
            self._preparar_artefatos()
            self._iniciar_logger()
            self.logger.info("[REPROCESSAMENTO] Iniciando reprocessamento global de falhas")

            self._iniciar_navegador()
            self._criar_componentes_execucao()

            tabelas, componentes = self._carregar_dados_excel()
            if self.checkpoint:
                self.checkpoint.atualizar_total_linhas(len(tabelas))
                self.checkpoint.sincronizar_tabelas(tabelas)

            with self.rastreador.etapa("login", "Realizando login"):
                self.pagina_login.abrir()
                self.pagina_login.autenticar()

            itens_fase_um = self._obter_itens_para_execucao(
                FaseExecucao.FASE_1,
                tabelas,
                somente_falhas=True,
            )
            self._executar_fase_um(itens_fase_um, tipo_execucao=TipoExecucao.REPROCESSAMENTO)

            itens_fase_dois = self._obter_itens_para_execucao(
                FaseExecucao.FASE_2,
                tabelas,
                somente_falhas=True,
            )
            self._executar_fase_dois_interna(
                itens_fase_dois,
                componentes,
                tipo_execucao=TipoExecucao.REPROCESSAMENTO,
            )

            self._registrar_alertas_analise()
        finally:
            self._encerrar()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def _validar_pre_requisitos(self) -> None:
        if not self.caminho_excel.exists():
            raise FileNotFoundError(f"Arquivo Excel não encontrado: {self.caminho_excel}")
        if not config.EMAIL_LOGIN:
            raise ValueError("EMAIL_LOGIN não configurado no .env")
        if not config.SENHA_LOGIN:
            raise ValueError("SENHA_LOGIN não configurado no .env")
        if not config.URL_LOGIN:
            raise ValueError("URL_LOGIN não configurado no .env")

    def _preparar_artefatos(self) -> None:
        preparador = PreparadorArquivosExecucao(self.run_id)
        preparador.preparar()

    def _iniciar_logger(self) -> None:
        self.logger = criar_logger("rpa")

    def _iniciar_navegador(self) -> None:
        self.logger.info("Iniciando navegador...")
        self.driver = FabricaNavegador.criar()
        self.logger.info("Navegador iniciado")

    def _carregar_dados_excel(self) -> tuple[list, list]:
        leitor = LeitorExcel(self.caminho_excel)
        leitor.validar()
        return leitor.ler_aba_um(), leitor.ler_aba_dois()

    def _obter_itens_para_execucao(
        self,
        fase: FaseExecucao,
        tabelas: list,
        somente_falhas: bool = False,
    ) -> list[tuple[int, object]]:
        if self.checkpoint:
            return self.checkpoint.obter_tabelas_para_execucao(
                fase,
                tabelas,
                somente_falhas=somente_falhas,
            )
        return self._normalizar_itens(tabelas)

    @staticmethod
    def _normalizar_itens(tabelas: list) -> list[tuple[int, object]]:
        return [(indice, tabela) for indice, tabela in enumerate(tabelas, start=1)]

    @staticmethod
    def _localizar_item_por_nome(tabelas: list, nome_tabela: str) -> tuple[int, Optional[object]]:
        for indice, tabela in enumerate(tabelas, start=1):
            if tabela.nome.strip() == nome_tabela.strip():
                return indice, tabela
        return 0, None

    def _registrar_alertas_analise(self) -> None:
        if not self.gestor:
            return
        for alerta in self.gestor.analisar_execucao(self.run_id):
            self.observador.registrar_sistema(
                f"[ALERTA] {alerta.alerta}: {alerta.motivo}"
            )

    @staticmethod
    def _mensagem_sem_itens_fase_dois() -> str:
        return (
            "Nenhum item pendente para validacao da Fase 2 nesta execucao. "
            "Os itens do Excel ja podem ter sido processados localmente ou "
            "nao ha mais linhas disponiveis para validar."
        )

    def solicitar_parada_emergencial(self) -> None:
        """Força o encerramento do navegador para interromper a execução atual."""
        if self.logger:
            self.logger.warning("Parada emergencial solicitada pelo operador.")
        self.observador.registrar_sistema(
            "Parada solicitada pelo operador. Encerrando navegador atual..."
        )
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

    def _encerrar(self) -> None:
        """Fecha o navegador e aplica retenção de artefatos."""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("Navegador encerrado")
        except Exception:
            pass
        try:
            RetencaoArtefatos(self.run_id, self.logger).aplicar()
        except Exception:
            pass
        if self.logger:
            self.logger.info("Execução finalizada")
        self.observador.registrar_sistema("Execução finalizada")
