"""
Processador da Fase 1: loop de criação de cópias.
Itera sobre cada tabela do Excel e cria sua cópia no sistema.
"""

import logging
import time
from typing import TYPE_CHECKING, Optional

from src.aplicacao.fase_execucao import FaseExecucao, StatusExecucao, TipoExecucao
from src.infraestrutura.diagnostico_navegador import erro_indica_navegador_encerrado
from src.infraestrutura.logger_estruturado import LoggerEstruturado
from src.infraestrutura.registro_processamento import agora_iso
from src.monitoramento.observador_execucao import (
    ContratoObservadorExecucao,
    ContextoTabelaProcessamento,
    ObservadorNulo,
)
from src.servicos.gestor_ocorrencias import GestorOcorrenciasProcessamento
from src.servicos.leitor_excel import DadosTabelaExcel

if TYPE_CHECKING:
    from src.aplicacao.gestor_checkpoint import GestorCheckpoint


class ProcessadorFaseUm:
    """
    Coordena o loop de criação de cópias (Fase 1).
    Continua após falhas isoladas de tabela individual.
    """

    def __init__(
        self,
        criador,
        gestor: GestorOcorrenciasProcessamento,
        observador: Optional[ContratoObservadorExecucao] = None,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.criador = criador
        self.gestor = gestor
        self.observador = observador or ObservadorNulo()
        self.logger = logger or logging.getLogger("rpa")
        self.log_estruturado = LoggerEstruturado(self.logger)

    def processar(
        self,
        tabelas: list[DadosTabelaExcel] | list[tuple[int, DadosTabelaExcel]],
        run_id: str,
        checkpoint: Optional["GestorCheckpoint"] = None,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> None:
        """
        Processa todas as tabelas da Fase 1.
        Registra sucesso ou falha individualmente e continua após erros isolados.
        Pula linhas já processadas quando checkpoint é fornecido.
        """
        itens = self._normalizar_itens(tabelas)
        total = len(itens)
        self.observador.definir_total_fase_um(total)
        self.log_estruturado.fase1(
            "INICIO",
            status="INICIADO",
            total=str(total),
            tipo_execucao=tipo_execucao.value,
        )

        for indice_excel, tabela in itens:
            if not self.observador.validar_continuacao():
                self.logger.info("[F1] Parada solicitada pelo operador")
                break

            if checkpoint and checkpoint.ja_processada(1, indice_excel, tabela.nome):
                self.log_estruturado.fase1(
                    "SKIP",
                    indice_excel,
                    tabela.nome,
                    status="JA_PROCESSADA",
                )
                continue

            try:
                self.criador.pagina_tabelas.preparar_estado_listagem()
            except Exception as erro_estado:
                self.logger.warning(f"[F1] Falha ao preparar estado da listagem: {erro_estado}")

            tentativas = (
                checkpoint.contar_tentativas(1, indice_excel, tabela.nome) + 1
                if checkpoint
                else 1
            )
            estado_item = (
                checkpoint.obter_estado_item(indice_excel, tabela.nome)
                if checkpoint
                else {}
            )
            contexto = ContextoTabelaProcessamento(
                fase=1,
                indice=indice_excel,
                nome_tabela=tabela.nome,
                total=total,
                fase_execucao=FaseExecucao.FASE_1,
                tipo_execucao=tipo_execucao,
                tentativas=tentativas,
                reprocessado=bool(estado_item.get("reprocessado")) or (
                    tipo_execucao == TipoExecucao.REPROCESSAMENTO
                ),
                status_fase_1=estado_item.get("fase_1", StatusExecucao.PENDENTE.value),
                status_fase_2=estado_item.get("fase_2", StatusExecucao.PENDENTE.value),
            )
            self.observador.registrar_processando(contexto)
            self.log_estruturado.fase1(
                "LINHA_PROCESSADA",
                indice_excel,
                tabela.nome,
                status="EM_ANDAMENTO",
                tipo_execucao=tipo_execucao.value,
                tentativas=str(tentativas),
            )

            t_inicio = time.time()
            timestamp_inicio = agora_iso()
            try:
                self.criador.criar_copia(tabela)
                duracao_ms = (time.time() - t_inicio) * 1000
                timestamp_fim = agora_iso()

                if checkpoint:
                    checkpoint.registrar_resultado(
                        FaseExecucao.FASE_1,
                        indice_excel,
                        tabela.nome,
                        StatusExecucao.SUCESSO.value,
                        tipo_execucao=tipo_execucao,
                    )
                    estado_item = checkpoint.obter_estado_item(indice_excel, tabela.nome)
                else:
                    estado_item = {
                        "fase_1": StatusExecucao.SUCESSO.value,
                        "fase_2": StatusExecucao.PENDENTE.value,
                        "reprocessado": tipo_execucao == TipoExecucao.REPROCESSAMENTO,
                    }

                contexto.status_fase_1 = estado_item.get("fase_1", StatusExecucao.SUCESSO.value)
                contexto.status_fase_2 = estado_item.get("fase_2", StatusExecucao.PENDENTE.value)
                contexto.reprocessado = bool(estado_item.get("reprocessado"))

                self.gestor.registrar_sucesso(
                    run_id,
                    FaseExecucao.FASE_1,
                    indice_excel,
                    tabela.nome,
                    tipo_execucao=tipo_execucao,
                    tentativas=tentativas,
                    timestamp_inicio=timestamp_inicio,
                    timestamp_fim=timestamp_fim,
                    duracao_ms=duracao_ms,
                    reprocessado=contexto.reprocessado,
                    status_fase_1=contexto.status_fase_1,
                    status_fase_2=contexto.status_fase_2,
                )
                self.observador.registrar_sucesso(contexto, "Cópia criada com sucesso")
                self.log_estruturado.fase1(
                    "SUCESSO",
                    indice_excel,
                    tabela.nome,
                    tipo_execucao=tipo_execucao.value,
                    tentativas=str(tentativas),
                )

            except Exception as erro:
                tempo_ms = (time.time() - t_inicio) * 1000
                timestamp_fim = agora_iso()
                navegador_encerrado = erro_indica_navegador_encerrado(erro)
                screenshot = ""
                try:
                    screenshot = self.criador.pagina_tabelas.acoes.salvar_screenshot(
                        f"fase1_erro_{tabela.nome}"
                    )
                except Exception:
                    pass
                if checkpoint:
                    checkpoint.registrar_resultado(
                        FaseExecucao.FASE_1,
                        indice_excel,
                        tabela.nome,
                        StatusExecucao.ERRO.value,
                        tipo_execucao=tipo_execucao,
                    )
                    estado_item = checkpoint.obter_estado_item(indice_excel, tabela.nome)
                else:
                    estado_item = {
                        "fase_1": StatusExecucao.ERRO.value,
                        "fase_2": StatusExecucao.PENDENTE.value,
                        "reprocessado": tipo_execucao == TipoExecucao.REPROCESSAMENTO,
                    }

                contexto.status_fase_1 = estado_item.get("fase_1", StatusExecucao.ERRO.value)
                contexto.status_fase_2 = estado_item.get("fase_2", StatusExecucao.PENDENTE.value)
                contexto.reprocessado = bool(estado_item.get("reprocessado"))

                erro_classificado = self.gestor.registrar_falha(
                    run_id,
                    FaseExecucao.FASE_1,
                    indice_excel,
                    tabela.nome,
                    str(erro),
                    screenshot,
                    tempo_ms=tempo_ms,
                    tipo_execucao=tipo_execucao,
                    tentativas=tentativas,
                    timestamp_inicio=timestamp_inicio,
                    timestamp_fim=timestamp_fim,
                    reprocessado=contexto.reprocessado,
                    status_fase_1=contexto.status_fase_1,
                    status_fase_2=contexto.status_fase_2,
                )
                contexto.dados_extras = {
                    "tipo_erro": erro_classificado.tipo,
                    "tipo_erro_legivel": erro_classificado.tipo_legivel,
                    "motivo": erro_classificado.mensagem_operador,
                    "acao_recomendada": erro_classificado.acao_recomendada,
                    "screenshot": screenshot,
                    "tempo_ms": round(tempo_ms, 1),
                }
                self.observador.registrar_falha(contexto, erro_classificado.mensagem_operador)
                self.log_estruturado.fase1(
                    "ERRO",
                    indice_excel,
                    tabela.nome,
                    status="ERRO",
                    tipo=erro_classificado.tipo,
                    tipo_execucao=tipo_execucao.value,
                    tentativas=str(tentativas),
                    mensagem=str(erro)[:200],
                )
                if navegador_encerrado:
                    self.observador.registrar_sistema(
                        "Navegador encerrado durante a Fase 1. Execucao interrompida."
                    )
                    raise RuntimeError(
                        "Navegador encerrado ou sessao perdida durante a Fase 1."
                    ) from erro
                self.gestor.recuperar_interface_apos_erro()
                try:
                    self.criador.pagina_tabelas.descartar_popup_swal_inesperado()
                    self.criador.pagina_tabelas.acessar()
                    self.criador.pagina_tabelas.preparar_filtros_fase_um()
                except Exception:
                    pass

        # Só marca fase completa se o loop terminou naturalmente (sem parada pelo operador)
        loop_completo = self.observador.validar_continuacao()
        if checkpoint and loop_completo and checkpoint.pode_marcar_fase_completa(1):
            checkpoint.marcar_fase_completa(1)
        self.log_estruturado.fase1(
            "CONCLUIDO",
            status="COMPLETO" if loop_completo else "INTERROMPIDO",
            total=str(total),
            tipo_execucao=tipo_execucao.value,
        )

    @staticmethod
    def _normalizar_itens(
        tabelas: list[DadosTabelaExcel] | list[tuple[int, DadosTabelaExcel]],
    ) -> list[tuple[int, DadosTabelaExcel]]:
        itens: list[tuple[int, DadosTabelaExcel]] = []
        for indice_padrao, item in enumerate(tabelas, start=1):
            if isinstance(item, tuple):
                indice_excel, tabela = item
            else:
                indice_excel, tabela = indice_padrao, item
            itens.append((int(indice_excel), tabela))
        return itens
