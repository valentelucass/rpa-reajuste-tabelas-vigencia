"""Executor integrado do processo auto delete clientes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.aplicacao.fase_execucao import StatusExecucao, TipoExecucao
from src.monitoramento.observador_execucao import (
    ContextoTabelaProcessamento,
    ContratoObservadorExecucao,
    ObservadorNulo,
)

try:
    from .acoes_navegador import AcoesNavegador
    from .config import ARQUIVO_REPROCESSAMENTO
    from .leitor_excel import LeitorExcelExclusao
    from .logger_config import configurar_logger
    from .modelos import (
        ModoExecucaoAutoDelete,
        OrdemExecucaoAutoDelete,
        RegistroAutoDelete,
    )
    from .navegador import FabricaNavegador
    from .pagina_exclusao import NavegadorFechadoError, PaginaExclusao
    from .pagina_login import PaginaLogin
    from .persistencia import RepositorioAutoDeleteClientes
except ImportError:  # pragma: no cover - compatibilidade standalone
    from auto_delete_compat import carregar_modulo_local

    AcoesNavegador = carregar_modulo_local("acoes_navegador").AcoesNavegador
    ARQUIVO_REPROCESSAMENTO = carregar_modulo_local("config").ARQUIVO_REPROCESSAMENTO
    from leitor_excel import LeitorExcelExclusao
    from logger_config import configurar_logger
    from modelos import ModoExecucaoAutoDelete, OrdemExecucaoAutoDelete, RegistroAutoDelete
    from navegador import FabricaNavegador
    from pagina_exclusao import NavegadorFechadoError, PaginaExclusao
    from pagina_login import PaginaLogin
    from persistencia import RepositorioAutoDeleteClientes


PROCESSO_AUTO_DELETE = "auto_delete_clientes"

TIPOS_ERRO_AUTO_DELETE = {
    "nao_encontrado": (
        "nao_encontrado",
        "Nao encontrado",
        "Validar se o cliente ainda existe no ESL Cloud",
    ),
    "erro_exclusao": (
        "erro_exclusao",
        "Erro na exclusao",
        "Reprocessar o registro ou validar o popup de retorno",
    ),
    "navegador_fechado": (
        "sessao_invalida",
        "Navegador fechado",
        "Abrir nova execucao e reprocessar os registros pendentes",
    ),
    "interrompido": (
        "interrompido",
        "Execucao interrompida",
        "Retomar pelo reprocessamento de falhas",
    ),
    "erro_inesperado": (
        "erro_desconhecido",
        "Erro inesperado",
        "Consultar o log detalhado e reprocessar o registro",
    ),
}


class ExecucaoAutoDeleteInterrompida(RuntimeError):
    """Interrupcao controlada da execucao pelo operador."""


class ExecutorAutoDeleteClientes:
    """Orquestra o auto delete como modulo independente integrado ao projeto."""

    def __init__(
        self,
        *,
        caminho_excel: str | Path | None,
        ordem_execucao: OrdemExecucaoAutoDelete = OrdemExecucaoAutoDelete.NORMAL,
        modo_execucao: ModoExecucaoAutoDelete = ModoExecucaoAutoDelete.EXECUCAO_COMPLETA,
        quantidade_ciclos: int = 1,
        observador: Optional[ContratoObservadorExecucao] = None,
        registro_individual: Optional[RegistroAutoDelete] = None,
    ) -> None:
        self.caminho_excel = Path(caminho_excel) if caminho_excel else None
        self.ordem_execucao = ordem_execucao
        self.modo_execucao = modo_execucao
        self.quantidade_ciclos = max(int(quantidade_ciclos or 1), 1)
        self.observador = observador or ObservadorNulo()
        self.registro_individual = registro_individual
        self._repositorio = RepositorioAutoDeleteClientes()
        self._parar = False

    def solicitar_parada(self) -> None:
        self._parar = True

    def executar(self) -> None:
        run_id = self._repositorio.gerar_run_id()
        caminho_log = self._repositorio.caminho_log_execucao(run_id)
        logger = configurar_logger(
            run_id=run_id,
            callback=lambda mensagem: self.observador.registrar_sistema(
                f"[AUTO_DELETE_CLIENTES] {mensagem}"
            ),
        )
        self._repositorio.registrar_execucao(
            run_id,
            caminho_excel=self.caminho_excel,
            ordem=self.ordem_execucao,
            modo=self.modo_execucao,
            quantidade_ciclos=self.quantidade_ciclos,
            caminho_log=caminho_log,
        )

        registros: list[RegistroAutoDelete] = []
        total = 0
        resultados = {"sucesso": 0, "erro": 0}
        falhas_pendentes: dict[str, RegistroAutoDelete] = {}
        registros_resolvidos: set[str] = set()
        status_execucao = "concluida"
        ciclos_concluidos = 0
        driver = None

        try:
            registros = self.ordem_execucao.aplicar(self._carregar_registros(logger))
            total_registros = len(registros)
            total = total_registros * self.quantidade_ciclos

            self.observador.definir_total_fase_um(total)
            self.observador.definir_total_fase_dois(0)

            if total_registros == 0:
                self._repositorio.limpar_falhas_pendentes()
                self._repositorio.finalizar_execucao(
                    run_id,
                    status="sem_registros",
                    total_registros=0,
                    sucessos=0,
                    falhas=0,
                )
                return

            logger.info(
                "Execucao iniciada | modo=%s | ordem=%s | arquivo=%s | reprocessamento=%s | ciclos=%s",
                self.modo_execucao.value,
                self.ordem_execucao.value,
                str(self.caminho_excel) if self.caminho_excel else ARQUIVO_REPROCESSAMENTO,
                self.modo_execucao.eh_reprocessamento,
                self.quantidade_ciclos,
            )

            self._verificar_continuacao()

            driver = FabricaNavegador.criar(logger=logger)
            acoes = AcoesNavegador(driver, logger)

            pagina_login = PaginaLogin(acoes, logger)
            pagina_login.abrir()
            pagina_login.autenticar()

            pagina = PaginaExclusao(acoes, logger)
            pagina.acessar_tabelas_cliente()
            primeiro = registros[0]
            pagina.configurar_filtros_iniciais(primeiro.data_inicio, primeiro.data_fim)

            for ciclo_execucao in range(1, self.quantidade_ciclos + 1):
                self._verificar_continuacao()
                logger.info("Iniciando ciclo %s de %s", ciclo_execucao, self.quantidade_ciclos)

                for posicao_ciclo, registro in enumerate(registros, start=1):
                    self._verificar_continuacao()
                    posicao = ((ciclo_execucao - 1) * total_registros) + posicao_ciclo

                    contexto_processando = self._criar_contexto(
                        registro=registro,
                        total=total,
                        posicao=posicao,
                        status_fase_1=StatusExecucao.PENDENTE.value,
                        ciclo_execucao=ciclo_execucao,
                        total_ciclos_execucao=self.quantidade_ciclos,
                    )
                    self.observador.registrar_processando(contexto_processando)

                    try:
                        pagina.verificar_navegador_aberto()
                        resultado = pagina.excluir_registro(registro.nome_cliente)
                        if resultado in {"sucesso", "ja_processado"}:
                            registros_resolvidos.add(self._chave_registro(registro))
                            self._remover_falha_pendente(falhas_pendentes, registro)
                            resultados["sucesso"] += 1
                            mensagem = (
                                "Solicitacao ja processada anteriormente"
                                if resultado == "ja_processado"
                                else "Cliente excluido com sucesso"
                            )
                            self.observador.registrar_sucesso(
                                self._criar_contexto(
                                    registro=registro,
                                    total=total,
                                    posicao=posicao,
                                    status_fase_1=StatusExecucao.SUCESSO.value,
                                    ciclo_execucao=ciclo_execucao,
                                    total_ciclos_execucao=self.quantidade_ciclos,
                                ),
                                mensagem,
                            )
                            continue

                        if resultado == "nao_encontrado":
                            registros_resolvidos.add(self._chave_registro(registro))
                            self._remover_falha_pendente(falhas_pendentes, registro)
                            resultados["sucesso"] += 1
                            mensagem = self._mensagem_nao_encontrado_concluido(registro)
                            logger.info(mensagem)
                            self.observador.registrar_sucesso(
                                self._criar_contexto(
                                    registro=registro,
                                    total=total,
                                    posicao=posicao,
                                    status_fase_1=StatusExecucao.SUCESSO.value,
                                    ciclo_execucao=ciclo_execucao,
                                    total_ciclos_execucao=self.quantidade_ciclos,
                                ),
                                mensagem,
                            )
                            continue

                        resultados["erro"] += 1
                        falha = self._registrar_falha(
                            registro=registro,
                            posicao=posicao,
                            total=total,
                            codigo_falha="erro_exclusao",
                            mensagem="Falha ao excluir o cliente na tela de tabelas",
                            ciclo_execucao=ciclo_execucao,
                            total_ciclos_execucao=self.quantidade_ciclos,
                        )
                        self._atualizar_falha_pendente(falhas_pendentes, falha)
                    except NavegadorFechadoError:
                        resultados["erro"] += 1
                        falha = self._registrar_falha(
                            registro=registro,
                            posicao=posicao,
                            total=total,
                            codigo_falha="navegador_fechado",
                            mensagem="Navegador fechado durante o processamento",
                            ciclo_execucao=ciclo_execucao,
                            total_ciclos_execucao=self.quantidade_ciclos,
                        )
                        self._atualizar_falha_pendente(falhas_pendentes, falha)
                        for deslocamento, restante in enumerate(registros[posicao_ciclo:], start=1):
                            resultados["erro"] += 1
                            falha_restante = self._registrar_falha(
                                registro=restante,
                                posicao=posicao + deslocamento,
                                total=total,
                                codigo_falha="navegador_fechado",
                                mensagem="Navegador fechado antes do processamento do registro",
                                emitir_contexto=False,
                                ciclo_execucao=ciclo_execucao,
                                total_ciclos_execucao=self.quantidade_ciclos,
                            )
                            self._atualizar_falha_pendente(falhas_pendentes, falha_restante)
                        status_execucao = "navegador_fechado"
                        break
                    except ExecucaoAutoDeleteInterrompida:
                        resultados["erro"] += 1
                        falha = self._registrar_falha(
                            registro=registro,
                            posicao=posicao,
                            total=total,
                            codigo_falha="interrompido",
                            mensagem="Execucao interrompida pelo operador",
                            ciclo_execucao=ciclo_execucao,
                            total_ciclos_execucao=self.quantidade_ciclos,
                        )
                        self._atualizar_falha_pendente(falhas_pendentes, falha)
                        for deslocamento, restante in enumerate(registros[posicao_ciclo:], start=1):
                            resultados["erro"] += 1
                            falha_restante = self._registrar_falha(
                                registro=restante,
                                posicao=posicao + deslocamento,
                                total=total,
                                codigo_falha="interrompido",
                                mensagem="Registro pendente apos parada solicitada",
                                emitir_contexto=False,
                                ciclo_execucao=ciclo_execucao,
                                total_ciclos_execucao=self.quantidade_ciclos,
                            )
                            self._atualizar_falha_pendente(falhas_pendentes, falha_restante)
                        status_execucao = "interrompida"
                        raise
                    except Exception as erro:
                        resultados["erro"] += 1
                        screenshot = ""
                        if driver is not None:
                            screenshot = acoes.salvar_screenshot(
                                f"erro_{registro.nome_cliente.replace(' ', '_')}"
                            )
                        falha = self._registrar_falha(
                            registro=registro,
                            posicao=posicao,
                            total=total,
                            codigo_falha="erro_inesperado",
                            mensagem=str(erro),
                            screenshot=screenshot,
                            ciclo_execucao=ciclo_execucao,
                            total_ciclos_execucao=self.quantidade_ciclos,
                        )
                        self._atualizar_falha_pendente(falhas_pendentes, falha)
                    finally:
                        try:
                            pagina.limpar_campo_nome()
                        except Exception:
                            pass

                if status_execucao == "navegador_fechado":
                    break

                logger.info("Ciclo %s concluido", ciclo_execucao)
                ciclos_concluidos = ciclo_execucao

            if falhas_pendentes:
                self._repositorio.salvar_falhas_pendentes(
                    run_id,
                    list(falhas_pendentes.values()),
                    caminho_excel=self.caminho_excel,
                    ordem=self.ordem_execucao,
                    modo=self.modo_execucao,
                    quantidade_ciclos=self.quantidade_ciclos,
                )
            else:
                self._repositorio.limpar_falhas_pendentes()

            if status_execucao == "concluida":
                logger.info("Execucao finalizada apos %s ciclos", ciclos_concluidos)
            else:
                logger.info(
                    "Execucao encerrada com status=%s apos %s de %s ciclo(s)",
                    status_execucao,
                    ciclos_concluidos,
                    self.quantidade_ciclos,
                )
            logger.info(
                "Execucao finalizada | total=%s | sucesso=%s | erro=%s | log=%s",
                self._total_finalizado(total, status_execucao, resultados),
                resultados["sucesso"],
                resultados["erro"],
                caminho_log,
            )
            self._repositorio.finalizar_execucao(
                run_id,
                status=status_execucao,
                total_registros=self._total_finalizado(total, status_execucao, resultados),
                sucessos=resultados["sucesso"],
                falhas=resultados["erro"],
            )
        except ExecucaoAutoDeleteInterrompida:
            if falhas_pendentes:
                self._repositorio.salvar_falhas_pendentes(
                    run_id,
                    list(falhas_pendentes.values()),
                    caminho_excel=self.caminho_excel,
                    ordem=self.ordem_execucao,
                    modo=self.modo_execucao,
                    quantidade_ciclos=self.quantidade_ciclos,
                )
            self._repositorio.finalizar_execucao(
                run_id,
                status="interrompida",
                total_registros=self._total_finalizado(total, "interrompida", resultados),
                sucessos=resultados["sucesso"],
                falhas=resultados["erro"],
            )
            raise
        except Exception as erro:
            logger.exception("Erro critico na execucao do auto delete clientes: %s", erro)
            if falhas_pendentes:
                self._repositorio.salvar_falhas_pendentes(
                    run_id,
                    list(falhas_pendentes.values()),
                    caminho_excel=self.caminho_excel,
                    ordem=self.ordem_execucao,
                    modo=self.modo_execucao,
                    quantidade_ciclos=self.quantidade_ciclos,
                )
            self._repositorio.finalizar_execucao(
                run_id,
                status="erro_critico",
                total_registros=self._total_finalizado(total, "erro_critico", resultados),
                sucessos=resultados["sucesso"],
                falhas=resultados["erro"],
            )
            raise
        finally:
            if driver is not None:
                try:
                    logger.info("Fechando navegador...")
                    driver.quit()
                except Exception:
                    pass

    def _carregar_registros(self, logger) -> list[RegistroAutoDelete]:
        if self.modo_execucao is ModoExecucaoAutoDelete.REPROCESSAMENTO_INDIVIDUAL:
            if self.registro_individual is None:
                raise RuntimeError("Registro individual nao informado para o reprocessamento.")
            return [self._resolver_registro_no_excel_atual(self.registro_individual, logger)]

        if self.modo_execucao is ModoExecucaoAutoDelete.REPROCESSAR_FALHAS:
            _, registros = self._repositorio.carregar_falhas_pendentes()
            if not registros:
                raise RuntimeError("Nao existem falhas pendentes para reprocessar.")
            return [
                self._resolver_registro_no_excel_atual(registro, logger)
                for registro in registros
            ]

        if self.caminho_excel is None or not self.caminho_excel.exists():
            raise RuntimeError("Selecione um arquivo Excel valido para o auto delete clientes.")

        leitor = LeitorExcelExclusao(self.caminho_excel, logger)
        leitor.validar()
        return [
            RegistroAutoDelete(
                linha_excel=indice,
                nome_cliente=registro.nome_cliente,
                data_inicio=registro.data_inicio,
                data_fim=registro.data_fim,
            )
            for indice, registro in enumerate(leitor.ler(), start=2)
        ]

    def _resolver_registro_no_excel_atual(
        self,
        referencia: RegistroAutoDelete,
        logger,
    ) -> RegistroAutoDelete:
        if self.caminho_excel is None or not self.caminho_excel.exists():
            raise RuntimeError(
                "Selecione o arquivo Excel atual na interface para reprocessar o auto delete."
            )

        registros_excel = self._carregar_registros_excel(logger)
        if not registros_excel:
            raise RuntimeError("Nenhum registro válido encontrado no Excel selecionado.")

        mapa_por_linha = {registro.linha_excel: registro for registro in registros_excel}
        if referencia.linha_excel in mapa_por_linha:
            candidato = mapa_por_linha[referencia.linha_excel]
            if self._normalizar_nome(candidato.nome_cliente) == self._normalizar_nome(
                referencia.nome_cliente
            ):
                return candidato

        nome_referencia = self._normalizar_nome(referencia.nome_cliente)
        for registro in registros_excel:
            if self._normalizar_nome(registro.nome_cliente) == nome_referencia:
                logger.info(
                    "Reprocessamento resolvido pelo Excel atual | linha=%s | cliente=%s",
                    registro.linha_excel,
                    registro.nome_cliente,
                )
                return registro

        raise RuntimeError(
            f"Cliente '{referencia.nome_cliente}' não foi encontrado no Excel selecionado."
        )

    def _carregar_registros_excel(self, logger) -> list[RegistroAutoDelete]:
        if self.caminho_excel is None or not self.caminho_excel.exists():
            raise RuntimeError("Selecione um arquivo Excel valido para o auto delete clientes.")

        leitor = LeitorExcelExclusao(self.caminho_excel, logger)
        leitor.validar()
        return [
            RegistroAutoDelete(
                linha_excel=indice,
                nome_cliente=registro.nome_cliente,
                data_inicio=registro.data_inicio,
                data_fim=registro.data_fim,
            )
            for indice, registro in enumerate(leitor.ler(), start=2)
        ]

    @staticmethod
    def _normalizar_nome(valor: str) -> str:
        return " ".join((valor or "").strip().upper().split())

    def _chave_registro(self, registro: RegistroAutoDelete) -> str:
        return f"{registro.linha_excel}|{self._normalizar_nome(registro.nome_cliente)}"

    def _mensagem_nao_encontrado_concluido(self, registro: RegistroAutoDelete) -> str:
        return (
            f"Cliente '{registro.nome_cliente}' nao encontrado na lista; "
            "considerando como ja excluido"
        )

    @staticmethod
    def _total_finalizado(
        total_planejado: int,
        status_execucao: str,
        resultados: dict[str, int],
    ) -> int:
        if status_execucao == "concluida":
            return total_planejado
        return resultados["sucesso"] + resultados["erro"]

    def _atualizar_falha_pendente(
        self,
        falhas_pendentes: dict[str, RegistroAutoDelete],
        registro: RegistroAutoDelete,
    ) -> None:
        falhas_pendentes[self._chave_registro(registro)] = registro

    def _remover_falha_pendente(
        self,
        falhas_pendentes: dict[str, RegistroAutoDelete],
        registro: RegistroAutoDelete,
    ) -> None:
        falhas_pendentes.pop(self._chave_registro(registro), None)

    def _criar_contexto(
        self,
        *,
        registro: RegistroAutoDelete,
        total: int,
        posicao: int,
        status_fase_1: str,
        ciclo_execucao: int = 1,
        total_ciclos_execucao: int = 1,
        codigo_falha: str = "",
        mensagem: str = "",
        screenshot: str = "",
    ) -> ContextoTabelaProcessamento:
        tipo_execucao = (
            TipoExecucao.REPROCESSAMENTO
            if self.modo_execucao.eh_reprocessamento
            else TipoExecucao.NORMAL
        )
        dados_extras = {
            "processo": PROCESSO_AUTO_DELETE,
            "rotulo_fase": "Auto Delete",
            "fase_execucao_ui": "auto_delete",
            "ordem_execucao": self.ordem_execucao.value,
            "modo_auto_delete": self.modo_execucao.value,
            "ciclo_execucao": ciclo_execucao,
            "total_ciclos_execucao": total_ciclos_execucao,
            "reprocessamento_dados": registro.to_reprocessamento_dict(),
        }

        if codigo_falha:
            tipo_erro, tipo_legivel, acao = TIPOS_ERRO_AUTO_DELETE[codigo_falha]
            dados_extras.update(
                {
                    "tipo_erro": tipo_erro,
                    "tipo_erro_legivel": tipo_legivel,
                    "motivo": mensagem,
                    "acao_recomendada": acao,
                    "screenshot": screenshot,
                }
            )

        return ContextoTabelaProcessamento(
            fase=3,
            indice=registro.linha_excel or posicao,
            nome_tabela=registro.nome_cliente,
            total=total,
            dados_extras=dados_extras,
            tipo_execucao=tipo_execucao,
            pagina=1,
            tentativas=ciclo_execucao,
            reprocessado=self.modo_execucao.eh_reprocessamento,
            status_fase_1="nao_aplicavel",
            status_fase_2="nao_aplicavel",
        )

    def _registrar_falha(
        self,
        *,
        registro: RegistroAutoDelete,
        posicao: int,
        total: int,
        codigo_falha: str,
        mensagem: str,
        screenshot: str = "",
        emitir_contexto: bool = True,
        ciclo_execucao: int = 1,
        total_ciclos_execucao: int = 1,
    ) -> RegistroAutoDelete:
        registro_falha = RegistroAutoDelete(
            linha_excel=registro.linha_excel,
            nome_cliente=registro.nome_cliente,
            data_inicio=registro.data_inicio,
            data_fim=registro.data_fim,
            motivo=mensagem,
            origem="reprocessamento" if self.modo_execucao.eh_reprocessamento else registro.origem,
        )
        if emitir_contexto:
            self.observador.registrar_falha(
                self._criar_contexto(
                    registro=registro_falha,
                    total=total,
                    posicao=posicao,
                    status_fase_1=StatusExecucao.ERRO.value,
                    ciclo_execucao=ciclo_execucao,
                    total_ciclos_execucao=total_ciclos_execucao,
                    codigo_falha=codigo_falha,
                    mensagem=mensagem,
                    screenshot=screenshot,
                ),
                mensagem,
            )
        return registro_falha

    def _verificar_continuacao(self) -> None:
        if self._parar or not self.observador.validar_continuacao():
            raise ExecucaoAutoDeleteInterrompida("Execucao interrompida pelo operador.")
