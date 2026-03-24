"""
Teste 1 — Loop Completo com Excel (PRINCIPAL)
Simula o fluxo E2E da Fase 1 com massa limitada de teste:
  Para cada linha do Excel:
    1. Acessar pagina de Tabelas de Cliente
    2. Desmarcar "Filial responsavel"
    3. Marcar filtro "Ativa = Sim"
    4. Ler nome da tabela do Excel
    5. Inserir nome no campo de busca
    6. Executar pesquisa
    7. Validar que a busca foi executada corretamente
    8. Dar refresh da pagina
    9. Repetir para proxima linha

Valida cada acao individualmente. Gera logs inteligentes e autoavaliacao.
"""

import json
import time

import pytest

from tests.constantes_teste import LIMITE_TESTE_FASE_1
from tests.utils.analisador_execucao import (
    AnalisadorExecucao,
    LogEtapa,
    LogFluxoLinha,
)
from tests.utils.gerador_excel_fake import gerar_excel_fake
from tests.utils.mock_navegador import (
    NavegadorMock,
    RegistroAcao,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_excel(tmp_path):
    """Gera Excel com volume limitado para a Fase 1."""
    caminho = tmp_path / "teste_limitado.xlsx"
    gerar_excel_fake(
        caminho,
        total_linhas=LIMITE_TESTE_FASE_1,
        percentual_fixo="9,80%",
        vigencia_fixa="01/04/2026 - 31/03/2027",
    )
    return caminho


@pytest.fixture
def navegador_mock():
    return NavegadorMock()


@pytest.fixture
def registro():
    return RegistroAcao()


@pytest.fixture
def analisador():
    return AnalisadorExecucao()


# ---------------------------------------------------------------------------
# Simulador do fluxo de loop (mock do comportamento real)
# ---------------------------------------------------------------------------

class SimuladorFluxoLoop:
    """
    Simula o fluxo completo da Fase 1 usando mocks.
    Cada etapa e validada individualmente para garantir que nao pule nada.
    """

    ETAPAS = [
        "acessar_pagina",
        "desmarcar_filial",
        "filtrar_ativa_sim",
        "ler_nome_excel",
        "inserir_nome_busca",
        "executar_pesquisa",
        "validar_pesquisa",
        "refresh_pagina",
    ]

    def __init__(self, navegador: NavegadorMock, registro: RegistroAcao,
                 analisador: AnalisadorExecucao):
        self.navegador = navegador
        self.registro = registro
        self.analisador = analisador
        self.etapas_executadas_por_linha: dict[int, list[str]] = {}
        self.erros: list[dict] = []
        self._estado_filtro_limpo = False

    def executar_loop(self, nomes_tabelas: list[str]) -> dict:
        """Executa o loop completo para todas as linhas."""
        total = len(nomes_tabelas)

        for indice, nome in enumerate(nomes_tabelas, start=1):
            self._estado_filtro_limpo = False
            etapas_linha = []
            t_inicio_linha = time.time()

            try:
                # 1. Acessar pagina
                t0 = time.time()
                self._acessar_pagina()
                dt = (time.time() - t0) * 1000
                etapas_linha.append("acessar_pagina")
                self.analisador.registrar_etapa(LogEtapa(
                    step="acessar_pagina", status="success",
                    tempo_ms=dt, linha=indice, valor=nome,
                ))
                self.registro.registrar("acessar_pagina", f"Navegou para listagem", indice, nome)

                # 2. Desmarcar filial
                t0 = time.time()
                self._desmarcar_filial()
                dt = (time.time() - t0) * 1000
                etapas_linha.append("desmarcar_filial")
                self.analisador.registrar_etapa(LogEtapa(
                    step="desmarcar_filial", status="success",
                    tempo_ms=dt, linha=indice,
                ))
                self.registro.registrar("desmarcar_filial", "Filial desmarcada", indice)

                # 3. Filtrar Ativa = Sim
                t0 = time.time()
                self._filtrar_ativa_sim()
                dt = (time.time() - t0) * 1000
                etapas_linha.append("filtrar_ativa_sim")
                self.analisador.registrar_etapa(LogEtapa(
                    step="filtrar_ativa_sim", status="success",
                    tempo_ms=dt, linha=indice,
                ))
                self.registro.registrar("filtrar_ativa_sim", "Filtro Ativa=Sim aplicado", indice)

                # 4. Ler nome do Excel
                t0 = time.time()
                nome_lido = self._ler_nome_excel(nome)
                dt = (time.time() - t0) * 1000
                etapas_linha.append("ler_nome_excel")
                assert nome_lido == nome, f"Nome lido '{nome_lido}' != esperado '{nome}'"
                self.analisador.registrar_etapa(LogEtapa(
                    step="ler_nome_excel", status="success",
                    tempo_ms=dt, linha=indice, valor=nome_lido,
                ))
                self.registro.registrar("ler_nome_excel", f"Lido: {nome_lido}", indice, nome_lido)

                # 5. Inserir nome no campo de busca
                t0 = time.time()
                self._inserir_nome_busca(nome)
                dt = (time.time() - t0) * 1000
                etapas_linha.append("inserir_nome_busca")
                assert self.navegador._input_pesquisa.valor == nome, (
                    f"Campo busca: '{self.navegador._input_pesquisa.valor}' != '{nome}'"
                )
                self.analisador.registrar_etapa(LogEtapa(
                    step="inserir_nome_busca", status="success",
                    tempo_ms=dt, linha=indice, valor=nome,
                ))
                self.registro.registrar("inserir_nome_busca", f"Digitado: {nome}", indice, nome)

                # 6. Executar pesquisa
                t0 = time.time()
                self._executar_pesquisa(nome)
                dt = (time.time() - t0) * 1000
                etapas_linha.append("executar_pesquisa")
                self.analisador.registrar_etapa(LogEtapa(
                    step="executar_pesquisa", status="success",
                    tempo_ms=dt, linha=indice, valor=nome,
                ))
                self.registro.registrar("executar_pesquisa", "Pesquisa executada", indice, nome)

                # 7. Validar resultado
                t0 = time.time()
                self._validar_pesquisa(nome)
                dt = (time.time() - t0) * 1000
                etapas_linha.append("validar_pesquisa")
                self.analisador.registrar_etapa(LogEtapa(
                    step="validar_pesquisa", status="success",
                    tempo_ms=dt, linha=indice, valor=nome,
                ))
                self.registro.registrar("validar_pesquisa", "Resultado validado", indice, nome)

                # 8. Refresh da pagina
                t0 = time.time()
                self._refresh_pagina()
                dt = (time.time() - t0) * 1000
                etapas_linha.append("refresh_pagina")
                assert not self._estado_filtro_limpo, "Estado deve ser resetado apos refresh"
                self.analisador.registrar_etapa(LogEtapa(
                    step="refresh_pagina", status="success",
                    tempo_ms=dt, linha=indice,
                ))
                self.registro.registrar("refresh_pagina", "Pagina recarregada", indice)

            except Exception as erro:
                etapa_falhou = self.ETAPAS[len(etapas_linha)] if len(etapas_linha) < len(self.ETAPAS) else "desconhecida"
                self.analisador.registrar_etapa(LogEtapa(
                    step=etapa_falhou, status="error",
                    tempo_ms=0, linha=indice, erro=str(erro),
                ))
                self.erros.append({
                    "linha": indice,
                    "nome": nome,
                    "etapa": etapa_falhou,
                    "erro": str(erro),
                })

            self.etapas_executadas_por_linha[indice] = etapas_linha

        self.analisador.finalizar_loop(total)
        return self.analisador.gerar_relatorio_completo()

    def _acessar_pagina(self):
        """Simula navegacao para pagina de tabelas."""
        self.navegador.get("https://rodogarcia.eslcloud.com.br/customer_price_tables")
        self.navegador.execute_script("return document.readyState")
        # Reset estado a cada iteracao (nao reutilizar estado anterior)
        self._estado_filtro_limpo = False

    def _desmarcar_filial(self):
        """Simula desmarcar filtro de filial."""
        # Simula busca e clique no botao de remover
        self._estado_filtro_limpo = False

    def _filtrar_ativa_sim(self):
        """Simula aplicar filtro Ativa = Sim."""
        self._estado_filtro_limpo = True

    def _ler_nome_excel(self, nome_esperado: str) -> str:
        """Simula leitura do nome da tabela do Excel."""
        return nome_esperado

    def _inserir_nome_busca(self, nome: str):
        """Simula insercao do nome no campo de busca."""
        # Limpa campo anterior
        self.navegador._input_pesquisa.clear()
        # Digita novo nome
        self.navegador._input_pesquisa.send_keys(nome)

    def _executar_pesquisa(self, nome: str):
        """Simula clique no botao pesquisar."""
        self.navegador.configurar_linhas([nome])

    def _validar_pesquisa(self, nome: str):
        """Valida que a pesquisa retornou resultados."""
        linhas = self.navegador._linhas_tabela
        assert len(linhas) > 0, f"Nenhuma linha encontrada para '{nome}'"
        # Valida que a linha correta esta presente
        nomes_encontrados = [l._nome for l in linhas]
        assert nome in nomes_encontrados, f"'{nome}' nao encontrado em {nomes_encontrados}"

    def _refresh_pagina(self):
        """Simula refresh da pagina (reset completo do estado)."""
        self.navegador.configurar_linhas([])
        self.navegador._input_pesquisa.clear()
        self._estado_filtro_limpo = False


# ---------------------------------------------------------------------------
# TESTES
# ---------------------------------------------------------------------------

class TestFluxoLoopCompleto:
    """Teste principal: loop completo com massa limitada."""

    def test_loop_todas_etapas(self, tmp_excel, navegador_mock, registro, analisador):
        """Todas as linhas limitadas devem ser processadas com todas as etapas."""
        from src.servicos.leitor_excel import LeitorExcel

        leitor = LeitorExcel(tmp_excel)
        tabelas = leitor.ler_aba_um()
        assert len(tabelas) == LIMITE_TESTE_FASE_1, (
            f"Esperado {LIMITE_TESTE_FASE_1} linhas, obteve {len(tabelas)}"
        )

        nomes = [t.nome for t in tabelas]

        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        relatorio = simulador.executar_loop(nomes)

        # Valida completude do loop
        assert relatorio["log_loop"]["total_linhas"] == LIMITE_TESTE_FASE_1
        assert relatorio["log_loop"]["linhas_processadas"] == LIMITE_TESTE_FASE_1
        assert relatorio["log_loop"]["falhas"] == 0

        # Valida autoavaliacao
        assert relatorio["autoavaliacao"]["status_geral"] == "ok"
        assert relatorio["autoavaliacao"]["confiabilidade_fluxo"] >= 0.95

        # Valida que CADA linha executou TODAS as etapas
        for i in range(1, LIMITE_TESTE_FASE_1 + 1):
            assert i in simulador.etapas_executadas_por_linha, f"Linha {i} nao processada"
            etapas = simulador.etapas_executadas_por_linha[i]
            assert etapas == SimuladorFluxoLoop.ETAPAS, (
                f"Linha {i}: etapas executadas {etapas} != esperadas {SimuladorFluxoLoop.ETAPAS}"
            )

        # Valida metricas
        metricas = relatorio["metricas"]
        assert metricas["taxa_sucesso"] == 1.0
        assert metricas["taxa_erro"] == 0.0
        assert metricas["consistencia_loop"] == 1.0

    def test_nao_reutiliza_estado_entre_linhas(self, tmp_excel, navegador_mock, registro, analisador):
        """O estado dos filtros deve ser resetado a cada iteracao."""
        from src.servicos.leitor_excel import LeitorExcel

        leitor = LeitorExcel(tmp_excel)
        tabelas = leitor.ler_aba_um()
        nomes = [t.nome for t in tabelas]

        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        simulador.executar_loop(nomes)

        # Verificar que para cada linha houve refresh (estado limpo)
        refreshes = registro.obter_por_tipo("refresh_pagina")
        assert len(refreshes) == len(nomes), (
            f"Esperado {len(nomes)} refreshes, obteve {len(refreshes)}"
        )

        # Verificar que filtros foram reaplicados a cada iteracao
        filtros = registro.obter_por_tipo("filtrar_ativa_sim")
        assert len(filtros) == len(nomes), (
            f"Esperado {len(nomes)} aplicacoes de filtro, obteve {len(filtros)}"
        )

    def test_campo_busca_limpo_a_cada_iteracao(self, tmp_excel, navegador_mock, registro, analisador):
        """O campo de busca deve ser limpo antes de cada nova pesquisa."""
        from src.servicos.leitor_excel import LeitorExcel

        leitor = LeitorExcel(tmp_excel)
        tabelas = leitor.ler_aba_um()
        nomes = [t.nome for t in tabelas]

        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        simulador.executar_loop(nomes)

        insercoes = registro.obter_por_tipo("inserir_nome_busca")
        assert len(insercoes) == len(nomes)

        # Cada insercao deve ter o nome correto (nao residuo do anterior)
        for i, insercao in enumerate(insercoes):
            assert insercao["valor"] == nomes[i], (
                f"Linha {i+1}: valor '{insercao['valor']}' != esperado '{nomes[i]}'"
            )

    def test_pesquisa_validada_para_cada_linha(self, tmp_excel, navegador_mock, registro, analisador):
        """A pesquisa deve ser validada individualmente para cada linha."""
        from src.servicos.leitor_excel import LeitorExcel

        leitor = LeitorExcel(tmp_excel)
        tabelas = leitor.ler_aba_um()
        nomes = [t.nome for t in tabelas]

        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        simulador.executar_loop(nomes)

        validacoes = registro.obter_por_tipo("validar_pesquisa")
        assert len(validacoes) == len(nomes), "Cada linha deve ter validacao de pesquisa"

        for validacao in validacoes:
            assert validacao["valor"] != "", "Validacao nao deve ter valor vazio"


class TestFluxoLoopResiliencia:
    """Testes de resiliencia do loop (falhas parciais)."""

    def test_loop_continua_apos_falha_isolada(self, navegador_mock, registro, analisador):
        """Loop deve continuar processando apos falha em uma linha."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]

        class SimuladorComFalha(SimuladorFluxoLoop):
            def _validar_pesquisa(self, nome):
                if nome == "Tabela 2":
                    raise RuntimeError("Erro simulado na validacao")
                super()._validar_pesquisa(nome)

        simulador = SimuladorComFalha(navegador_mock, registro, analisador)
        relatorio = simulador.executar_loop(nomes)

        assert relatorio["log_loop"]["linhas_processadas"] == LIMITE_TESTE_FASE_1
        assert relatorio["log_loop"]["falhas"] == 1

        # Linhas apos a falha devem ter sido processadas
        assert 2 in simulador.etapas_executadas_por_linha
        assert 3 in simulador.etapas_executadas_por_linha

    def test_detecta_falhas_consecutivas(self, navegador_mock, registro, analisador):
        """Analisador deve detectar falhas consecutivas como problema critico."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]

        class SimuladorFalhasConsecutivas(SimuladorFluxoLoop):
            def _executar_pesquisa(self, nome):
                raise RuntimeError("Falha simulada consecutiva")

        simulador = SimuladorFalhasConsecutivas(navegador_mock, registro, analisador)
        relatorio = simulador.executar_loop(nomes)

        assert relatorio["log_loop"]["falhas"] == LIMITE_TESTE_FASE_1
        assert relatorio["autoavaliacao"]["status_geral"] == "critical"

        problemas = relatorio["autoavaliacao"]["problemas_detectados"]
        tem_falha_consecutiva = any("consecutiva" in p.lower() for p in problemas)
        assert tem_falha_consecutiva, f"Nao detectou falha consecutiva: {problemas}"

    def test_loop_incompleto_detectado(self, navegador_mock, registro, analisador):
        """Analisador deve detectar quando nem todas as linhas foram processadas."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]

        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        simulador.executar_loop(nomes[:2])
        analisador.log_loop.total_linhas = LIMITE_TESTE_FASE_1
        avaliacao = analisador.analisar()

        assert avaliacao.status_geral == "critical"
        tem_incompleto = any(p.tipo == "loop_incompleto" for p in avaliacao.problemas_detectados)
        assert tem_incompleto, "Deveria detectar loop incompleto"


class TestFluxoLoopValidacaoEtapas:
    """Testes que validam cada etapa individual do loop."""

    def test_etapa_acessar_pagina(self, navegador_mock):
        """Deve navegar para URL correta a cada iteracao."""
        simulador = SimuladorFluxoLoop(navegador_mock, RegistroAcao(), AnalisadorExecucao())
        simulador._acessar_pagina()
        assert "customer_price_tables" in navegador_mock.url_atual

    def test_etapa_inserir_nome_limpa_campo_anterior(self, navegador_mock):
        """Deve limpar o campo antes de inserir novo nome."""
        navegador_mock._input_pesquisa.valor = "Nome Anterior"
        simulador = SimuladorFluxoLoop(navegador_mock, RegistroAcao(), AnalisadorExecucao())

        simulador._inserir_nome_busca("Novo Nome")
        assert navegador_mock._input_pesquisa.valor == "Novo Nome"

    def test_etapa_refresh_reseta_estado(self, navegador_mock):
        """Refresh deve limpar linhas e campo de busca."""
        navegador_mock.configurar_linhas(["Tabela A"])
        navegador_mock._input_pesquisa.valor = "Tabela A"

        simulador = SimuladorFluxoLoop(navegador_mock, RegistroAcao(), AnalisadorExecucao())
        simulador._refresh_pagina()

        assert len(navegador_mock._linhas_tabela) == 0
        assert navegador_mock._input_pesquisa.valor == ""

    def test_etapa_executar_pesquisa_configura_linhas(self, navegador_mock):
        """Pesquisa deve configurar linhas correspondentes no mock."""
        simulador = SimuladorFluxoLoop(navegador_mock, RegistroAcao(), AnalisadorExecucao())
        simulador._executar_pesquisa("Tabela XYZ")
        assert len(navegador_mock._linhas_tabela) == 1
        assert navegador_mock._linhas_tabela[0]._nome == "Tabela XYZ"

    def test_etapa_validar_pesquisa_falha_sem_resultado(self, navegador_mock):
        """Validacao deve falhar se nenhuma linha foi encontrada."""
        navegador_mock.configurar_linhas([])
        simulador = SimuladorFluxoLoop(navegador_mock, RegistroAcao(), AnalisadorExecucao())

        with pytest.raises(AssertionError, match="Nenhuma linha encontrada"):
            simulador._validar_pesquisa("Tabela Inexistente")


class TestLogsInteligentes:
    """Testes do sistema de logs estruturados."""

    def test_log_por_etapa_formato_correto(self, analisador):
        """Log por etapa deve ter formato JSON correto."""
        log = analisador.gerar_log_etapa(
            step="aplicar_filtro_ativa",
            status="success",
            tempo_ms=120.5,
            linha=23,
            valor="Tabela XPTO",
        )
        assert log["step"] == "aplicar_filtro_ativa"
        assert log["status"] == "success"
        assert log["tempo_ms"] == 120.5
        assert log["linha"] == 23
        assert log["valor"] == "Tabela XPTO"

    def test_log_fluxo_completo_formato_correto(self, analisador):
        """Log de fluxo completo deve ter formato JSON correto."""
        fluxo = LogFluxoLinha(
            linha=23,
            etapas_executadas=[
                LogEtapa(step="acessar_pagina", status="success", tempo_ms=100, linha=23),
                LogEtapa(step="inserir_nome_busca", status="success", tempo_ms=50, linha=23),
            ],
            tempo_total_ms=150,
            status="success",
        )
        log = analisador.gerar_log_fluxo(fluxo)
        assert log["linha"] == 23
        assert len(log["etapas_executadas"]) == 2
        assert log["tempo_total_ms"] == 150
        assert log["status"] == "success"

    def test_log_loop_formato_correto(self, navegador_mock, registro, analisador):
        """Log do loop deve ter formato JSON correto."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]
        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        simulador.executar_loop(nomes)

        log = analisador.gerar_log_loop()
        assert log["total_linhas"] == LIMITE_TESTE_FASE_1
        assert log["linhas_processadas"] == LIMITE_TESTE_FASE_1
        assert log["falhas"] == 0
        assert "tempo_total" in log

    def test_relatorio_completo_serializavel_json(self, navegador_mock, registro, analisador):
        """Relatorio completo deve ser serializavel para JSON."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]
        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        relatorio = simulador.executar_loop(nomes)

        # Deve serializar sem erros
        json_str = json.dumps(relatorio, ensure_ascii=False, indent=2)
        assert len(json_str) > 0

        # Deve deserializar corretamente
        parsed = json.loads(json_str)
        assert parsed["log_loop"]["total_linhas"] == LIMITE_TESTE_FASE_1


class TestAutoavaliacao:
    """Testes do sistema de autoavaliacao neuronal."""

    def test_fluxo_perfeito_retorna_ok(self, navegador_mock, registro, analisador):
        """Fluxo sem erros deve retornar status 'ok'."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]
        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        relatorio = simulador.executar_loop(nomes)

        assert relatorio["autoavaliacao"]["status_geral"] == "ok"
        assert relatorio["autoavaliacao"]["confiabilidade_fluxo"] >= 0.95

    def test_confiabilidade_cai_com_falhas(self, navegador_mock, registro, analisador):
        """Confiabilidade deve diminuir quando ha falhas."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]

        class SimuladorComFalhas(SimuladorFluxoLoop):
            def _executar_pesquisa(self, nome):
                if nome == "Tabela 2":
                    raise RuntimeError("Falha simulada")
                super()._executar_pesquisa(nome)

        simulador = SimuladorComFalhas(navegador_mock, registro, analisador)
        relatorio = simulador.executar_loop(nomes)

        confiabilidade = relatorio["autoavaliacao"]["confiabilidade_fluxo"]
        assert confiabilidade < 1.0, "Confiabilidade deveria ser < 1.0 com falhas"
        assert confiabilidade > 0.5, f"Confiabilidade muito baixa: {confiabilidade}"

    def test_metricas_tempo_calculadas(self, navegador_mock, registro, analisador):
        """Metricas de tempo devem ser calculadas corretamente."""
        nomes = [f"Tabela {i}" for i in range(1, LIMITE_TESTE_FASE_1 + 1)]
        simulador = SimuladorFluxoLoop(navegador_mock, registro, analisador)
        relatorio = simulador.executar_loop(nomes)

        metricas = relatorio["metricas"]
        assert "tempo_total_ms" in metricas
        assert "tempo_medio_por_linha_ms" in metricas
        assert "tempo_por_etapa" in metricas
        assert metricas["tempo_total_ms"] >= 0
        assert metricas["tempo_medio_por_linha_ms"] >= 0

    def test_detecta_etapas_faltantes(self, analisador):
        """Deve detectar quando uma etapa obrigatoria nao foi executada."""
        # Registrar apenas algumas etapas (faltando refresh_pagina)
        etapas_parciais = [
            "acessar_pagina", "desmarcar_filial", "filtrar_ativa_sim",
            "ler_nome_excel", "inserir_nome_busca", "executar_pesquisa",
            "validar_pesquisa",
            # faltando: refresh_pagina
        ]
        for etapa in etapas_parciais:
            analisador.registrar_etapa(LogEtapa(
                step=etapa, status="success", tempo_ms=10, linha=1,
            ))

        analisador.finalizar_loop(1)
        avaliacao = analisador.analisar()

        tem_faltante = any(p.tipo == "etapa_faltante" for p in avaliacao.problemas_detectados)
        assert tem_faltante, "Deveria detectar etapa faltante"
