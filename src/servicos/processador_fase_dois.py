"""
Processador da Fase 2: loop de aplicacao de reajuste.
Percorre as tabelas da Aba 1 do Excel em ordem, sob o filtro de vigencia,
pesquisando cada nome explicitamente antes de abrir o reajuste.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
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
from src.servicos.leitor_excel import ComponenteReajuste, DadosTabelaExcel

if TYPE_CHECKING:
    from src.aplicacao.gestor_checkpoint import GestorCheckpoint


ORDEM_EVENTOS_FASE_DOIS = {
    "INICIO": 1,
    "FILTRO_APLICADO": 2,
    "ABRINDO_TABELA": 3,
    "REAJUSTE_APLICADO": 4,
    "SALVO": 5,
    "ERRO": 6,
}


@dataclass
class EventoFaseDois:
    codigo: str
    nome_tabela: str
    timestamp: str
    status: str
    detalhes: dict[str, str] = field(default_factory=dict)


@dataclass
class ItemRelatorioFaseDois:
    nome: str
    status: str = "PENDENTE"
    erro: str = ""
    encontrada: bool = False
    eventos: list[EventoFaseDois] = field(default_factory=list)


@dataclass
class RelatorioFaseDois:
    run_id: str
    filtro_vigencia: str
    percentual: float
    total_registros_filtrados: int = 0
    total_encontradas: int = 0
    total_processadas: int = 0
    total_com_erro: int = 0
    ordem_valida: bool = True
    itens_sem_log: list[str] = field(default_factory=list)
    tabelas_ignoradas: list[str] = field(default_factory=list)
    detalhamento: list[ItemRelatorioFaseDois] = field(default_factory=list)

    @property
    def funcional(self) -> bool:
        return (
            self.total_encontradas > 0
            and self.total_processadas > 0
            and self.total_com_erro == 0
            and self.ordem_valida
            and not self.itens_sem_log
        )

    def validar_consistencia(self) -> None:
        """Confere ordem minima dos eventos e se nenhum item ficou sem log."""
        self.total_encontradas = sum(1 for item in self.detalhamento if item.encontrada)
        self.total_processadas = sum(1 for item in self.detalhamento if item.status == "SUCESSO")
        self.total_com_erro = sum(1 for item in self.detalhamento if item.status == "ERRO")
        self.itens_sem_log = []
        self.ordem_valida = True

        obrigatorios_base = {"INICIO", "FILTRO_APLICADO"}
        obrigatorios_sucesso = obrigatorios_base | {"ABRINDO_TABELA", "REAJUSTE_APLICADO", "SALVO"}
        obrigatorios_erro = obrigatorios_base | {"ERRO"}

        for item in self.detalhamento:
            codigos = [evento.codigo for evento in item.eventos]
            conjunto_codigos = set(codigos)

            if item.status == "SUCESSO" and not obrigatorios_sucesso.issubset(conjunto_codigos):
                self.itens_sem_log.append(item.nome)
            elif item.status == "ERRO" and not obrigatorios_erro.issubset(conjunto_codigos):
                self.itens_sem_log.append(item.nome)
            elif item.status not in {"SUCESSO", "ERRO"}:
                self.itens_sem_log.append(item.nome)

            ordem_codigos = [
                ORDEM_EVENTOS_FASE_DOIS[codigo]
                for codigo in codigos
                if codigo in ORDEM_EVENTOS_FASE_DOIS
            ]
            if ordem_codigos != sorted(ordem_codigos):
                self.ordem_valida = False

        self.itens_sem_log = sorted(set(self.itens_sem_log))
        self.tabelas_ignoradas = sorted(set(self.tabelas_ignoradas))

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados["funcional"] = self.funcional
        return dados


class ProcessadorFaseDois:
    """
    Coordena o loop de reajuste de copias (Fase 2).
    Trabalha sobre a ordem do Excel, filtrando por vigencia e pesquisando o nome
    explicitamente antes de abrir o reajuste.
    """

    def __init__(
        self,
        pagina_tabelas,
        aplicador,
        gestor: GestorOcorrenciasProcessamento,
        observador: Optional[ContratoObservadorExecucao] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.pagina_tabelas = pagina_tabelas
        self.aplicador = aplicador
        self.gestor = gestor
        self.observador = observador or ObservadorNulo()
        self.logger = logger or logging.getLogger("rpa")
        self.log_estruturado = LoggerEstruturado(self.logger)
        self.ultimo_relatorio: Optional[RelatorioFaseDois] = None

    def processar(
        self,
        tabelas: list[DadosTabelaExcel] | list[tuple[int, DadosTabelaExcel]],
        componentes: list[ComponenteReajuste],
        run_id: str,
        total_estimado: int = 0,
        filtro_vigencia: str = "",
        data_inicio: str = "",
        data_fim: str = "",
        checkpoint: Optional["GestorCheckpoint"] = None,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
    ) -> RelatorioFaseDois:
        """
        Processa as tabelas da Aba 1 do Excel em ordem.
        Continua apos falhas isoladas de linha individual.
        Pula linhas já processadas quando checkpoint é fornecido.
        """
        itens = self._normalizar_itens(tabelas)
        total_planejado = len(itens)
        percentual_referencia = itens[0][1].percentual if itens else 0.0

        relatorio = RelatorioFaseDois(
            run_id=run_id,
            filtro_vigencia=filtro_vigencia,
            percentual=percentual_referencia,
            total_registros_filtrados=total_estimado,
        )
        self.ultimo_relatorio = relatorio

        self.observador.definir_total_fase_dois(total_planejado)
        self.log_estruturado.fase2(
            "INICIO",
            status="INICIADO",
            total=str(total_planejado),
            tipo_execucao=tipo_execucao.value,
        )

        for indice_excel, tabela in itens:
            if not self.observador.validar_continuacao():
                self.logger.info("[F2] Parada solicitada pelo operador")
                break

            nome_tabela = tabela.nome

            if checkpoint and checkpoint.ja_processada(2, indice_excel, nome_tabela):
                self.log_estruturado.fase2(
                    "SKIP",
                    indice_excel,
                    nome_tabela,
                    status="JA_PROCESSADA",
                )
                continue

            item = self._obter_item(relatorio, nome_tabela)
            self._registrar_evento(
                item,
                "INICIO",
                "INICIADO",
                indice_excel=str(indice_excel),
            )

            tentativas = (
                checkpoint.contar_tentativas(2, indice_excel, nome_tabela) + 1
                if checkpoint
                else 1
            )
            estado_item = (
                checkpoint.obter_estado_item(indice_excel, nome_tabela)
                if checkpoint
                else {}
            )
            contexto = ContextoTabelaProcessamento(
                fase=2,
                indice=indice_excel,
                nome_tabela=nome_tabela,
                total=total_planejado,
                dados_extras={"indice_excel": indice_excel},
                fase_execucao=FaseExecucao.FASE_2,
                tipo_execucao=tipo_execucao,
                tentativas=tentativas,
                reprocessado=bool(estado_item.get("reprocessado")) or (
                    tipo_execucao == TipoExecucao.REPROCESSAMENTO
                ),
                status_fase_1=estado_item.get("fase_1", StatusExecucao.PENDENTE.value),
                status_fase_2=estado_item.get("fase_2", StatusExecucao.PENDENTE.value),
            )
            self.observador.registrar_processando(contexto)
            self.log_estruturado.fase2(
                "PROCESSANDO_TABELA",
                indice_excel,
                nome_tabela,
                status="EM_ANDAMENTO",
                tipo_execucao=tipo_execucao.value,
                tentativas=str(tentativas),
            )

            t_inicio = time.time()
            timestamp_inicio = agora_iso()
            try:
                filtro_reaplicado = self._garantir_contexto_pesquisa(data_inicio, data_fim)
                self._registrar_evento(
                    item,
                    "FILTRO_APLICADO",
                    "OK",
                    vigencia=filtro_vigencia or f"{data_inicio} - {data_fim}" or "N/A",
                    nome_pesquisa=nome_tabela,
                    filtro_reaplicado=str(filtro_reaplicado).lower(),
                )
                self.log_estruturado.fase2(
                    "FILTRO_DATA",
                    indice_excel,
                    nome_tabela,
                    vigencia=filtro_vigencia or f"{data_inicio} - {data_fim}",
                )

                linha, assinatura = self._localizar_linha_tabela(
                    nome_tabela,
                    data_inicio,
                    data_fim,
                )
                item.encontrada = True
                self._registrar_evento(
                    item,
                    "ABRINDO_TABELA",
                    "EM_ANDAMENTO",
                    assinatura=assinatura[:180],
                )
                self.aplicador.aplicar(
                    assinatura_linha=assinatura,
                    nome_tabela=nome_tabela,
                    componentes=componentes,
                    percentual=tabela.percentual,
                    linha=linha,
                    registrar_evento=lambda codigo, detalhe="": self._registrar_evento(
                        item,
                        codigo,
                        "OK",
                        detalhe=detalhe,
                    ),
                )
                item.status = "SUCESSO"
                duracao_ms = (time.time() - t_inicio) * 1000
                timestamp_fim = agora_iso()

                if checkpoint:
                    checkpoint.registrar_resultado(
                        FaseExecucao.FASE_2,
                        indice_excel,
                        nome_tabela,
                        StatusExecucao.SUCESSO.value,
                        tipo_execucao=tipo_execucao,
                    )
                    estado_item = checkpoint.obter_estado_item(indice_excel, nome_tabela)
                else:
                    estado_item = {
                        "fase_1": StatusExecucao.SUCESSO.value,
                        "fase_2": StatusExecucao.SUCESSO.value,
                        "reprocessado": tipo_execucao == TipoExecucao.REPROCESSAMENTO,
                    }

                contexto.status_fase_1 = estado_item.get("fase_1", StatusExecucao.SUCESSO.value)
                contexto.status_fase_2 = estado_item.get("fase_2", StatusExecucao.SUCESSO.value)
                contexto.reprocessado = bool(estado_item.get("reprocessado"))

                self.gestor.registrar_sucesso(
                    run_id,
                    FaseExecucao.FASE_2,
                    indice_excel,
                    nome_tabela,
                    tipo_execucao=tipo_execucao,
                    tentativas=tentativas,
                    timestamp_inicio=timestamp_inicio,
                    timestamp_fim=timestamp_fim,
                    duracao_ms=duracao_ms,
                    reprocessado=contexto.reprocessado,
                    status_fase_1=contexto.status_fase_1,
                    status_fase_2=contexto.status_fase_2,
                )
                self.observador.registrar_sucesso(contexto, "Reajuste aplicado com sucesso")
                self.log_estruturado.fase2(
                    "SUCESSO",
                    indice_excel,
                    nome_tabela,
                    tipo_execucao=tipo_execucao.value,
                    tentativas=str(tentativas),
                )

            except Exception as erro:
                item.status = "ERRO"
                item.erro = str(erro)
                tempo_ms = (time.time() - t_inicio) * 1000
                timestamp_fim = agora_iso()
                navegador_encerrado = erro_indica_navegador_encerrado(erro)
                screenshot = ""
                try:
                    screenshot = self.pagina_tabelas.acoes.salvar_screenshot(
                        f"fase2_erro_{nome_tabela}"
                    )
                except Exception:
                    pass
                self._registrar_evento(
                    item,
                    "ERRO",
                    "ERRO",
                    mensagem=str(erro)[:300],
                    tempo_ms=str(round(tempo_ms, 1)),
                )

                if checkpoint:
                    checkpoint.registrar_resultado(
                        FaseExecucao.FASE_2,
                        indice_excel,
                        nome_tabela,
                        StatusExecucao.ERRO.value,
                        tipo_execucao=tipo_execucao,
                    )
                    estado_item = checkpoint.obter_estado_item(indice_excel, nome_tabela)
                else:
                    estado_item = {
                        "fase_1": StatusExecucao.SUCESSO.value,
                        "fase_2": StatusExecucao.ERRO.value,
                        "reprocessado": tipo_execucao == TipoExecucao.REPROCESSAMENTO,
                    }

                contexto.status_fase_1 = estado_item.get("fase_1", StatusExecucao.SUCESSO.value)
                contexto.status_fase_2 = estado_item.get("fase_2", StatusExecucao.ERRO.value)
                contexto.reprocessado = bool(estado_item.get("reprocessado"))

                erro_classificado = self.gestor.registrar_falha(
                    run_id,
                    FaseExecucao.FASE_2,
                    indice_excel,
                    nome_tabela,
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
                contexto.dados_extras.update(
                    {
                        "tipo_erro": erro_classificado.tipo,
                        "tipo_erro_legivel": erro_classificado.tipo_legivel,
                        "motivo": erro_classificado.mensagem_operador,
                        "acao_recomendada": erro_classificado.acao_recomendada,
                        "screenshot": screenshot,
                        "tempo_ms": round(tempo_ms, 1),
                    }
                )
                self.observador.registrar_falha(
                    contexto,
                    erro_classificado.mensagem_operador,
                )
                self.log_estruturado.fase2(
                    "ERRO",
                    indice_excel,
                    nome_tabela,
                    status="ERRO",
                    tipo=erro_classificado.tipo,
                    tipo_execucao=tipo_execucao.value,
                    tentativas=str(tentativas),
                    mensagem=str(erro)[:200],
                )
                if navegador_encerrado:
                    relatorio.validar_consistencia()
                    self.observador.registrar_sistema(
                        "Navegador encerrado durante a Fase 2. Execucao interrompida."
                    )
                    raise RuntimeError(
                        "Navegador encerrado ou sessao perdida durante a Fase 2."
                    ) from erro
                self.gestor.recuperar_interface_apos_erro()
                if data_inicio and data_fim:
                    try:
                        self.pagina_tabelas.preparar_filtros_fase_dois(data_inicio, data_fim)
                    except Exception:
                        pass

            time.sleep(0.15)

        # Só marca fase completa se o loop terminou naturalmente (sem parada pelo operador)
        loop_completo = self.observador.validar_continuacao()
        if checkpoint and loop_completo and checkpoint.pode_marcar_fase_completa(2):
            checkpoint.marcar_fase_completa(2)
        relatorio.validar_consistencia()
        self.log_estruturado.fase2(
            "CONCLUIDO",
            status="COMPLETO" if loop_completo else "INTERROMPIDO",
            total=str(total_planejado),
            tipo_execucao=tipo_execucao.value,
        )
        return relatorio

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

    def _obter_item(self, relatorio: RelatorioFaseDois, nome_tabela: str) -> ItemRelatorioFaseDois:
        for item in relatorio.detalhamento:
            if item.nome == nome_tabela:
                return item
        item = ItemRelatorioFaseDois(nome=nome_tabela)
        relatorio.detalhamento.append(item)
        return item

    def _registrar_evento(
        self,
        item: ItemRelatorioFaseDois,
        codigo: str,
        status: str,
        **detalhes: str,
    ) -> None:
        timestamp = datetime.now().isoformat(timespec="seconds")
        evento = EventoFaseDois(
            codigo=codigo,
            nome_tabela=item.nome,
            timestamp=timestamp,
            status=status,
            detalhes={chave: str(valor) for chave, valor in detalhes.items() if valor not in {"", None}},
        )
        item.eventos.append(evento)

        mensagem = (
            f"[F2][{codigo}] nome_tabela={item.nome} "
            f"timestamp={timestamp} status={status}"
        )
        if evento.detalhes:
            detalhes_formatados = " ".join(
                f"{chave}={valor}" for chave, valor in sorted(evento.detalhes.items())
            )
            mensagem = f"{mensagem} {detalhes_formatados}"

        if codigo == "ERRO":
            self.logger.error(mensagem)
        else:
            self.logger.info(mensagem)

    def _garantir_contexto_pesquisa(self, data_inicio: str, data_fim: str) -> bool:
        """Garante que a pesquisa do proximo nome comece com a vigencia correta."""
        if not data_inicio or not data_fim:
            self.pagina_tabelas.limpar_pesquisa_nome()
            self.pagina_tabelas.acoes.aguardar_carregamento_finalizar()
            return False

        return self.pagina_tabelas.garantir_contexto_fase_dois(data_inicio, data_fim)

    def _localizar_linha_tabela(
        self,
        nome_tabela: str,
        data_inicio: str = "",
        data_fim: str = "",
    ) -> tuple[object, str]:
        """Pesquisa a tabela pelo nome dentro do filtro atual e retorna a linha e a assinatura."""
        self.pagina_tabelas.pesquisar_por_nome(nome_tabela)
        if data_inicio and data_fim and not self.pagina_tabelas.validar_filtro_vigencia_aplicado(
            data_inicio,
            data_fim,
        ):
            raise RuntimeError(
                "Filtro de vigencia foi perdido apos pesquisar por nome. "
                f"Esperado: {data_inicio} - {data_fim}"
            )
        self.pagina_tabelas.aguardar_resultado_pesquisa()
        self.pagina_tabelas.validar_resultado_encontrado(nome_tabela)
        linha = self.pagina_tabelas.localizar_linha_por_nome_exato(nome_tabela)
        assinatura = self.pagina_tabelas.validar_linha_para_reajuste(
            linha,
            nome_tabela,
            data_inicio,
            data_fim,
        )
        return linha, assinatura
