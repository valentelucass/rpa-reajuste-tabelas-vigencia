"""
Teste controlado de transição Fase 1 → Fase 2.

Valida que:
1. F1 finaliza corretamente ao processar os ultimos itens dentro do limite
2. O sistema detecta o fim do loop e marca fase completa
3. F2 inicia corretamente da PRIMEIRA tabela da lista

Estratégia: pré-popula checkpoint marcando linhas 1..N-k como processadas,
forçando o processador a executar apenas os ultimos itens permitidos. Código de produção
real, sem mocks.
"""

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Garante que o projeto está no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src.aplicacao.gestor_checkpoint import GestorCheckpoint
from src.infraestrutura.acoes_navegador import AcoesNavegador
from src.infraestrutura.fabrica_navegador import FabricaNavegador
from src.infraestrutura.fabrica_registrador_execucao import criar_logger
from src.infraestrutura.preparador_arquivos_execucao import PreparadorArquivosExecucao
from src.infraestrutura.rastreador_etapas import RastreadorEtapas
from src.monitoramento.observador_execucao import (
    ContratoObservadorExecucao,
    ContextoTabelaProcessamento,
)
from src.paginas.pagina_edicao_tabela import PaginaEdicaoTabela
from src.paginas.pagina_login import PaginaLogin
from src.paginas.pagina_reajuste import PaginaReajuste
from src.paginas.pagina_tabelas_cliente import PaginaTabelasCliente
from src.servicos.aplicador_reajuste import AplicadorReajuste
from src.servicos.criador_copia_tabela import CriadorCopiaTabela
from src.servicos.gestor_ocorrencias import GestorOcorrenciasProcessamento
from src.servicos.leitor_excel import LeitorExcel
from src.servicos.processador_fase_dois import ProcessadorFaseDois
from src.servicos.processador_fase_um import ProcessadorFaseUm
from tests.constantes_teste import LIMITE_TESTE_FASE_1, LIMITE_TESTE_FASE_2


# ---------------------------------------------------------------------------
# Observador de teste — captura eventos para validação
# ---------------------------------------------------------------------------

class ObservadorTeste(ContratoObservadorExecucao):
    """Observador que captura todos os eventos e limita execução na F2."""

    def __init__(self, logger: logging.Logger, limite_f2: int = LIMITE_TESTE_FASE_2) -> None:
        self.logger = logger
        self.limite_f2 = limite_f2
        self._parar = False
        self.eventos_f1: list[ContextoTabelaProcessamento] = []
        self.eventos_f2: list[ContextoTabelaProcessamento] = []
        self.sucessos_f1: list[str] = []
        self.sucessos_f2: list[str] = []
        self.falhas_f1: list[str] = []
        self.falhas_f2: list[str] = []
        self._fase_atual = 1
        self._contagem_sucesso_f2 = 0

    def definir_total_fase_um(self, total: int) -> None:
        self.logger.info(f"[TESTE] F1 total definido: {total}")

    def definir_total_fase_dois(self, total: int) -> None:
        self.logger.info(f"[TESTE] F2 total definido: {total}")
        self._fase_atual = 2

    def registrar_processando(self, contexto: ContextoTabelaProcessamento) -> None:
        if contexto.fase == 1:
            self.eventos_f1.append(contexto)
        else:
            self.eventos_f2.append(contexto)

    def registrar_sucesso(self, contexto: ContextoTabelaProcessamento, mensagem: str = "") -> None:
        if contexto.fase == 1:
            self.sucessos_f1.append(contexto.nome_tabela)
        else:
            self.sucessos_f2.append(contexto.nome_tabela)
            self._contagem_sucesso_f2 += 1

    def registrar_falha(self, contexto: ContextoTabelaProcessamento, mensagem: str = "") -> None:
        if contexto.fase == 1:
            self.falhas_f1.append(contexto.nome_tabela)
        else:
            self.falhas_f2.append(contexto.nome_tabela)

    def registrar_sistema(self, mensagem: str) -> None:
        self.logger.info(f"[TESTE][SISTEMA] {mensagem}")

    def validar_continuacao(self) -> bool:
        if self._parar:
            return False
        # Na F2, parar após atingir o limite de sucessos
        if self._fase_atual == 2 and self._contagem_sucesso_f2 >= self.limite_f2:
            return False
        return True

    def solicitar_parada(self) -> None:
        self._parar = True


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _criar_checkpoint_fake(
    caminho_excel: Path,
    tabelas: list,
    logger: logging.Logger,
) -> GestorCheckpoint:
    """
    Cria checkpoint com linhas 1..N-k pré-marcadas como processadas na F1.
    Isso faz o processador pular tudo e executar apenas os ultimos itens permitidos.
    Popula em memória e salva uma única vez para evitar I/O lento.
    """
    total = len(tabelas)
    checkpoint = GestorCheckpoint.carregar_ou_criar(
        caminho_excel, total_linhas=total, logger=logger
    )
    # Resetar para estado limpo
    checkpoint.resetar()

    # Pré-marcar linhas 1..N-k diretamente no estado interno (sem I/O por linha)
    linhas_a_pular = total - LIMITE_TESTE_FASE_1
    linhas_dict = {}
    itens_dict = {}
    for i in range(1, linhas_a_pular + 1):
        linhas_dict[str(i)] = tabelas[i - 1].nome

    for i, tabela in enumerate(tabelas, start=1):
        itens_dict[str(i)] = {
            "nome_tabela": tabela.nome,
            "fase_1": "sucesso" if i <= linhas_a_pular else "pendente",
            "fase_2": "pendente",
            "tentativas_fase_1": 0,
            "tentativas_fase_2": 0,
            "ultima_execucao": "normal",
            "reprocessado": False,
        }

    checkpoint._estado["fase1"]["linhas_processadas"] = linhas_dict
    checkpoint._estado["fase1"]["status"] = "parcial"
    checkpoint._estado["itens"] = itens_dict
    checkpoint._salvar()

    indices_pendentes = list(range(total - LIMITE_TESTE_FASE_1 + 1, total + 1))
    logger.info(
        f"[TESTE][SETUP] Checkpoint fake criado: {linhas_a_pular} linhas pré-marcadas, "
        f"{LIMITE_TESTE_FASE_1} pendentes (indices {indices_pendentes})"
    )
    return checkpoint


# ---------------------------------------------------------------------------
# Teste principal
# ---------------------------------------------------------------------------

def executar_teste() -> dict:
    """Executa o teste de transição F1→F2 e retorna o resultado."""

    resultado = {
        "modo_teste": True,
        "limite_fase_1": LIMITE_TESTE_FASE_1,
        "limite_fase_2": LIMITE_TESTE_FASE_2,
        "f1_itens": [],
        "fim_f1": {"ok": False, "detalhe": ""},
        "transicao": {"ok": False, "detalhe": ""},
        "f2_inicio": {"ok": False, "detalhe": ""},
        "f2_primeira": {"ok": False, "nome": ""},
    }

    driver = None

    try:
        # ---- SETUP ----
        config.recarregar_configuracoes(sobrescrever_env=True)
        run_id = f"teste_transicao_{datetime.now().strftime('%H%M%S')}_{uuid4().hex[:4]}"

        preparador = PreparadorArquivosExecucao(run_id)
        preparador.preparar()

        logger = criar_logger("rpa_teste_transicao")
        logger.info(f"[TESTE][INICIO] run_id={run_id} timestamp={_timestamp()}")
        logger.info(
            f"[TESTE][LIMITES] modo_teste=true limite_fase_1={LIMITE_TESTE_FASE_1} "
            f"limite_fase_2={LIMITE_TESTE_FASE_2}"
        )

        # Ler Excel
        caminho_excel = Path(r"C:\Users\lucas\Downloads\REAJUSTE.xlsx")
        if not caminho_excel.exists():
            raise FileNotFoundError(f"Excel não encontrado: {caminho_excel}")

        leitor = LeitorExcel(caminho_excel)
        leitor.validar()
        tabelas = leitor.ler_aba_um()
        componentes = leitor.ler_aba_dois()
        total = len(tabelas)

        if total < LIMITE_TESTE_FASE_1 + 1:
            raise ValueError(
                f"Excel tem apenas {total} linhas — precisa de pelo menos "
                f"{LIMITE_TESTE_FASE_1 + 1} para o teste"
            )

        ultimas_f1 = tabelas[-LIMITE_TESTE_FASE_1:]
        primeira = tabelas[0]

        logger.info(
            f"[TESTE][SETUP] Excel: {total} tabelas | "
            f"ultimas_f1={[t.nome for t in ultimas_f1]} | primeira={primeira.nome}"
        )

        # Criar checkpoint fake
        checkpoint = _criar_checkpoint_fake(caminho_excel, tabelas, logger)

        # Criar observador
        observador = ObservadorTeste(logger, limite_f2=LIMITE_TESTE_FASE_2)

        # Iniciar navegador
        logger.info("[TESTE][SETUP] Iniciando navegador...")
        driver = FabricaNavegador.criar()
        logger.info("[TESTE][SETUP] Navegador iniciado")

        # Montar componentes
        acoes = AcoesNavegador(driver, logger)
        rastreador = RastreadorEtapas(run_id, driver)

        pagina_login = PaginaLogin(acoes, logger)
        pagina_tabelas = PaginaTabelasCliente(acoes, logger)
        pagina_edicao = PaginaEdicaoTabela(acoes, logger)
        pagina_reajuste = PaginaReajuste(acoes, logger)

        gestor = GestorOcorrenciasProcessamento(acoes, logger)
        criador = CriadorCopiaTabela(pagina_tabelas, pagina_edicao, rastreador, logger)
        aplicador = AplicadorReajuste(pagina_tabelas, pagina_reajuste, rastreador, logger)

        processador_f1 = ProcessadorFaseUm(criador, gestor, observador, logger)
        processador_f2 = ProcessadorFaseDois(pagina_tabelas, aplicador, gestor, observador, logger)

        # Login
        logger.info("[TESTE][SETUP] Fazendo login...")
        pagina_login.abrir()
        pagina_login.autenticar()
        logger.info("[TESTE][SETUP] Login OK")

        # ==============================================================
        # ETAPA 2 — FASE 1 (CONTROLADA: ultimos itens permitidos)
        # ==============================================================

        for deslocamento, tabela_f1 in enumerate(
            ultimas_f1,
            start=total - LIMITE_TESTE_FASE_1 + 1,
        ):
            logger.info(
                f"[TESTE][F1][ITEM_{deslocamento}] timestamp={_timestamp()} "
                f"nome_tabela={tabela_f1.nome} indice={deslocamento}"
            )

        # Navegar e preparar filtros
        pagina_tabelas.acessar()
        pagina_tabelas.preparar_filtros_fase_um()

        # Executar F1 — o checkpoint vai pular tudo até os ultimos itens limitados
        logger.info(
            f"[TESTE][F1] Iniciando processamento ({LIMITE_TESTE_FASE_1} ultimos itens)..."
        )
        processador_f1.processar(tabelas, run_id, checkpoint=checkpoint)

        # ---- Validar F1 ----
        logger.info(f"[TESTE][FIM_FASE_1] timestamp={_timestamp()}")

        # Verificar quantas linhas F1 realmente processou
        itens_processados_f1 = len(observador.eventos_f1)
        sucessos_f1 = observador.sucessos_f1
        falhas_f1 = observador.falhas_f1

        logger.info(
            f"[TESTE][F1][RESULTADO] processados={itens_processados_f1} "
            f"sucessos={len(sucessos_f1)} falhas={len(falhas_f1)}"
        )

        for indice, tabela_esperada in enumerate(ultimas_f1, start=1):
            item_resultado = {
                "ok": False,
                "indice": total - LIMITE_TESTE_FASE_1 + indice,
                "nome_esperado": tabela_esperada.nome,
                "nome": "",
            }
            if itens_processados_f1 >= indice:
                nome_processado = observador.eventos_f1[indice - 1].nome_tabela
                item_resultado["nome"] = nome_processado
                item_resultado["ok"] = nome_processado == tabela_esperada.nome
                logger.info(
                    f"[TESTE][F1][ITEM_{indice}] "
                    f"resultado={'OK' if item_resultado['ok'] else 'FALHA'} "
                    f"esperado={tabela_esperada.nome} obtido={nome_processado}"
                )
            resultado["f1_itens"].append(item_resultado)

        # Fim F1 — fase marcada como completa?
        fase1_completa = checkpoint.fase_completa(1)
        resultado["fim_f1"]["ok"] = fase1_completa
        resultado["fim_f1"]["detalhe"] = (
            "fase1 marcada completa" if fase1_completa else "fase1 NÃO marcada completa"
        )
        logger.info(
            f"[TESTE][FIM_FASE_1] fase_completa={fase1_completa} "
            f"itens_processados={itens_processados_f1} "
            f"timestamp={_timestamp()}"
        )

        # Verificou exatamente o limite configurado?
        if itens_processados_f1 != LIMITE_TESTE_FASE_1:
            logger.warning(
                f"[TESTE][F1][ALERTA] Esperado {LIMITE_TESTE_FASE_1} itens processados, "
                f"obteve {itens_processados_f1}"
            )

        # ==============================================================
        # ETAPA 3 — TRANSIÇÃO
        # ==============================================================

        logger.info(f"[TESTE][TRANSICAO_F1_F2] timestamp={_timestamp()}")

        try:
            # Resetar estado da tela para F2
            data_inicio = primeira.data_inicio
            data_fim = primeira.data_fim

            pagina_tabelas.preparar_estado_listagem_fase_dois(data_inicio, data_fim)
            filtro_vigencia = pagina_tabelas.obter_valor_filtro_vigencia()
            total_copias = pagina_tabelas.obter_total_tabelas()
            tem_resultados = pagina_tabelas.ha_resultados_filtrados()

            resultado["transicao"]["ok"] = True
            resultado["transicao"]["detalhe"] = (
                f"filtro={filtro_vigencia} total_copias={total_copias} "
                f"tem_resultados={tem_resultados}"
            )
            logger.info(
                f"[TESTE][TRANSICAO_F1_F2] resultado=OK "
                f"filtro={filtro_vigencia} total_copias={total_copias} "
                f"timestamp={_timestamp()}"
            )

        except Exception as erro_transicao:
            resultado["transicao"]["detalhe"] = f"ERRO: {erro_transicao}"
            logger.error(
                f"[TESTE][TRANSICAO_F1_F2] resultado=FALHA erro={erro_transicao}"
            )
            raise

        # ==============================================================
        # ETAPA 4 — FASE 2 (primeiros itens limitados)
        # ==============================================================

        ITENS_F2 = LIMITE_TESTE_FASE_2

        if not tem_resultados:
            logger.error("[TESTE][F2] Sem resultados filtrados — F2 abortada")
            resultado["f2_inicio"]["detalhe"] = "sem resultados filtrados"
        else:
            tabelas_f2 = tabelas[:ITENS_F2]
            logger.info(
                f"[TESTE][F2][INICIO] timestamp={_timestamp()} "
                f"total_itens={ITENS_F2} "
                f"tabelas={[t.nome for t in tabelas_f2]}"
            )
            resultado["f2_inicio"]["ok"] = True
            resultado["f2_inicio"]["detalhe"] = (
                f"iniciando com {tabelas_f2[0].nome} "
                f"({ITENS_F2} itens)"
            )

            # Sinalizar ao observador que estamos na F2 (sem limite — processar tudo)
            observador._fase_atual = 2
            observador.limite_f2 = ITENS_F2

            for i, t in enumerate(tabelas_f2, 1):
                logger.info(
                    f"[TESTE][F2][TABELA_{i}] timestamp={_timestamp()} "
                    f"nome_tabela={t.nome}"
                )

            relatorio = processador_f2.processar(
                tabelas_f2,
                componentes,
                run_id,
                total_copias,
                filtro_vigencia,
                data_inicio,
                data_fim,
                checkpoint=checkpoint,
            )

            # Validar F2
            for i, evento in enumerate(observador.eventos_f2):
                status = "OK" if i < len(tabelas_f2) and evento.nome_tabela == tabelas_f2[i].nome else "FALHA"
                logger.info(
                    f"[TESTE][F2][ITEM_{i+1}] resultado={status} "
                    f"nome_tabela={evento.nome_tabela}"
                )

            if observador.eventos_f2:
                nome_f2 = observador.eventos_f2[0].nome_tabela
                resultado["f2_primeira"]["nome"] = nome_f2
                resultado["f2_primeira"]["ok"] = (nome_f2 == primeira.nome)

            logger.info(
                f"[TESTE][F2][RESULTADO] processados={len(observador.eventos_f2)} "
                f"sucessos={len(observador.sucessos_f2)} "
                f"falhas={len(observador.falhas_f2)}"
            )

    except Exception as erro:
        tb = traceback.format_exc()
        logger.error(f"[TESTE][ERRO_CRITICO] {erro}\n{tb}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return resultado


# ---------------------------------------------------------------------------
# Relatório final
# ---------------------------------------------------------------------------

def imprimir_relatorio(resultado: dict) -> bool:
    """Imprime relatório formatado e retorna True se tudo OK."""

    print("\n" + "=" * 60)
    print("  RESULTADO DO TESTE DE TRANSICAO F1 -> F2")
    print("=" * 60)
    print(
        f"  modo_teste={resultado.get('modo_teste')} "
        f"limite_f1={resultado.get('limite_fase_1')} "
        f"limite_f2={resultado.get('limite_fase_2')}"
    )
    print("-" * 60)

    todas_ok = True

    for indice, dados in enumerate(resultado.get("f1_itens", []), start=1):
        ok = dados.get("ok", False)
        detalhe = (
            f"esperado={dados.get('nome_esperado', '')} "
            f"obtido={dados.get('nome', '')}"
        )
        status = "OK" if ok else "FALHA"
        marcador = "+" if ok else "X"
        print(f"  [{marcador}] F1 item {indice:<5}: {status} - {detalhe}")
        if not ok:
            todas_ok = False

    itens = [
        ("Fim F1      ", resultado["fim_f1"]),
        ("Transição   ", resultado["transicao"]),
        ("F2 início   ", resultado["f2_inicio"]),
        ("F2 primeira ", resultado["f2_primeira"]),
    ]

    for label, dados in itens:
        ok = dados.get("ok", False)
        detalhe = dados.get("nome", "") or dados.get("detalhe", "")
        status = "OK" if ok else "FALHA"
        marcador = "+" if ok else "X"
        print(f"  [{marcador}] {label}: {status} - {detalhe}")
        if not ok:
            todas_ok = False

    print()
    if todas_ok:
        print("  >>> TRANSICAO: OK")
    else:
        print("  >>> TRANSICAO: FALHA")
    print("=" * 60 + "\n")

    return todas_ok


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    resultado = executar_teste()
    sucesso = imprimir_relatorio(resultado)
    sys.exit(0 if sucesso else 1)
