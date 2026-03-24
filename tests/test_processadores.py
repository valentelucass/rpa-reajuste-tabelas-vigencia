"""
Testes unitarios para ProcessadorFaseUm e ProcessadorFaseDois.
Usa mocks para isolar totalmente a logica de iteracao e controle.
"""

from unittest.mock import MagicMock, patch
import pytest
from selenium.common.exceptions import InvalidSessionIdException

from src.monitoramento.observador_execucao import (
    ContratoObservadorExecucao,
)
from src.servicos.leitor_excel import DadosTabelaExcel, ComponenteReajuste
from src.servicos.processador_fase_um import ProcessadorFaseUm
from src.servicos.processador_fase_dois import ProcessadorFaseDois


def _tabela(nome: str = "T") -> DadosTabelaExcel:
    return DadosTabelaExcel(
        nome=nome,
        data_inicio="01/04/2026",
        data_fim="31/03/2027",
        percentual=9.8,
    )


def _componente(nome: str = "Taxa A", aba: str = "fee") -> ComponenteReajuste:
    return ComponenteReajuste(aba=aba, nome_taxa=nome)


def _mock_observador() -> MagicMock:
    obs = MagicMock(spec=ContratoObservadorExecucao)
    obs.validar_continuacao.return_value = True
    return obs


class TestProcessadorFaseUm:
    def _processador(self, criador=None, gestor=None, observador=None):
        criador = criador or MagicMock()
        gestor = gestor or MagicMock()
        observador = observador or _mock_observador()
        logger = MagicMock()
        return ProcessadorFaseUm(criador, gestor, observador, logger)

    def test_processa_todas_as_tabelas(self):
        tabelas = [_tabela("T1"), _tabela("T2"), _tabela("T3")]
        observador = _mock_observador()
        p = self._processador(observador=observador)
        p.processar(tabelas, run_id="abc")
        assert observador.registrar_processando.call_count == 3
        assert observador.registrar_sucesso.call_count == 3

    def test_define_total_fase_um(self):
        tabelas = [_tabela("T1"), _tabela("T2")]
        observador = _mock_observador()
        p = self._processador(observador=observador)
        p.processar(tabelas, run_id="abc")
        observador.definir_total_fase_um.assert_called_once_with(2)

    def test_continua_apos_falha_individual(self):
        criador = MagicMock()
        criador.criar_copia.side_effect = [RuntimeError("falha"), None]
        tabelas = [_tabela("T1"), _tabela("T2")]
        observador = _mock_observador()
        p = self._processador(criador=criador, observador=observador)
        p.processar(tabelas, run_id="abc")
        assert observador.registrar_falha.call_count == 1
        assert observador.registrar_sucesso.call_count == 1

    def test_para_quando_validar_continuacao_false(self):
        observador = _mock_observador()
        # True (item 1 loop check), False (item 2 loop check), False (post-loop check)
        observador.validar_continuacao.side_effect = [True, False, False]
        tabelas = [_tabela("T1"), _tabela("T2")]
        p = self._processador(observador=observador)
        p.processar(tabelas, run_id="abc")
        assert observador.registrar_processando.call_count == 1

    def test_tabela_vazia(self):
        observador = _mock_observador()
        p = self._processador(observador=observador)
        p.processar([], run_id="abc")
        observador.definir_total_fase_um.assert_called_once_with(0)
        observador.registrar_processando.assert_not_called()

    def test_filtros_reaplicados_antes_de_cada_tabela(self):
        criador = MagicMock()
        criador.pagina_tabelas = MagicMock()
        tabelas = [_tabela("T1"), _tabela("T2"), _tabela("T3")]
        observador = _mock_observador()
        p = self._processador(criador=criador, observador=observador)
        p.processar(tabelas, run_id="abc")
        assert criador.pagina_tabelas.preparar_estado_listagem.call_count == 3

    def test_interrompe_quando_navegador_e_encerrado(self):
        criador = MagicMock()
        criador.criar_copia.side_effect = InvalidSessionIdException("invalid session id")
        criador.pagina_tabelas = MagicMock()
        criador.pagina_tabelas.acoes.salvar_screenshot.side_effect = InvalidSessionIdException(
            "invalid session id"
        )

        observador = _mock_observador()
        p = self._processador(criador=criador, observador=observador)

        with pytest.raises(RuntimeError, match="Navegador encerrado"):
            p.processar([_tabela("T1"), _tabela("T2")], run_id="abc")

        observador.registrar_processando.assert_called_once()
        observador.registrar_sistema.assert_called()

    def test_preserva_indice_original_do_excel_quando_recebe_tuplas(self):
        observador = _mock_observador()
        p = self._processador(observador=observador)

        p.processar([(5, _tabela("T5"))], run_id="abc")

        contexto = observador.registrar_processando.call_args.args[0]
        assert contexto.indice == 5


class TestProcessadorFaseDois:
    def _pagina_mock(self, nomes: list[str]) -> MagicMock:
        pagina = MagicMock()
        linhas = {nome: MagicMock(name=f"linha_{nome}") for nome in nomes}

        def _localizar(nome):
            return linhas[nome]

        def _assinatura(linha):
            return f"sig_{linha._mock_name.replace('linha_', '')}"

        pagina.garantir_contexto_fase_dois = MagicMock(return_value=False)
        pagina.pesquisar_por_nome = MagicMock()
        pagina.aguardar_resultado_pesquisa = MagicMock()
        pagina.validar_resultado_encontrado = MagicMock()
        pagina.validar_filtro_vigencia_aplicado = MagicMock(return_value=True)
        pagina.localizar_linha_por_nome_exato.side_effect = _localizar
        pagina.validar_linha_para_reajuste.side_effect = (
            lambda linha, nome, data_inicio="", data_fim="": _assinatura(linha)
        )
        pagina.preparar_filtros_fase_dois = MagicMock()
        pagina.limpar_pesquisa_nome = MagicMock()
        pagina.acoes = MagicMock()
        return pagina

    def _processador(self, pagina_tabelas=None, aplicador=None, gestor=None, observador=None):
        pagina_tabelas = pagina_tabelas or MagicMock()
        aplicador = aplicador or MagicMock()
        gestor = gestor or MagicMock()
        observador = observador or _mock_observador()
        logger = MagicMock()
        return ProcessadorFaseDois(pagina_tabelas, aplicador, gestor, observador, logger)

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_processa_todas_as_tabelas_em_ordem_do_excel(self, _sleep):
        tabelas = [_tabela("T1"), _tabela("T2")]
        pagina = self._pagina_mock(["T1", "T2"])
        observador = _mock_observador()
        p = self._processador(pagina_tabelas=pagina, observador=observador)

        p.processar(
            tabelas,
            [_componente()],
            run_id="abc",
            total_estimado=2,
            data_inicio="01/04/2026",
            data_fim="31/03/2027",
        )

        assert pagina.pesquisar_por_nome.call_args_list[0].args == ("T1",)
        assert pagina.pesquisar_por_nome.call_args_list[1].args == ("T2",)
        assert pagina.garantir_contexto_fase_dois.call_count == 2
        assert observador.registrar_sucesso.call_count == 2

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_define_total_fase_dois_pelo_total_do_excel(self, _sleep):
        pagina = self._pagina_mock(["T1"])
        observador = _mock_observador()
        p = self._processador(pagina_tabelas=pagina, observador=observador)

        p.processar([_tabela("T1")], [_componente()], run_id="abc", total_estimado=5)

        observador.definir_total_fase_dois.assert_called_once_with(1)

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_continua_apos_falha_individual(self, _sleep):
        tabelas = [_tabela("T1"), _tabela("T2")]
        pagina = self._pagina_mock(["T1", "T2"])

        aplicador = MagicMock()
        aplicador.aplicar.side_effect = [RuntimeError("erro aplicacao"), None]

        observador = _mock_observador()
        p = self._processador(pagina_tabelas=pagina, aplicador=aplicador, observador=observador)

        p.processar(tabelas, [_componente()], run_id="abc", total_estimado=2)

        assert observador.registrar_falha.call_count == 1
        assert observador.registrar_sucesso.call_count == 1

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_gera_logs_obrigatorios_no_relatorio(self, _sleep):
        pagina = self._pagina_mock(["T1"])
        observador = _mock_observador()

        aplicador = MagicMock()

        def _aplicar(**kwargs):
            kwargs["registrar_evento"]("REAJUSTE_APLICADO", "componentes=1")
            kwargs["registrar_evento"]("SALVO", "ok")

        aplicador.aplicar.side_effect = _aplicar

        p = self._processador(pagina_tabelas=pagina, aplicador=aplicador, observador=observador)
        relatorio = p.processar(
            [_tabela("T1")],
            [_componente()],
            run_id="abc",
            total_estimado=1,
            filtro_vigencia="01/04/2026 - 31/03/2027",
        )

        assert relatorio.total_encontradas == 1
        assert relatorio.total_processadas == 1
        assert relatorio.total_com_erro == 0
        assert relatorio.itens_sem_log == []
        assert relatorio.ordem_valida is True
        assert [evento.codigo for evento in relatorio.detalhamento[0].eventos] == [
            "INICIO",
            "FILTRO_APLICADO",
            "ABRINDO_TABELA",
            "REAJUSTE_APLICADO",
            "SALVO",
        ]

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_reaplica_contexto_e_registra_no_log(self, _sleep):
        pagina = self._pagina_mock(["T1"])
        pagina.garantir_contexto_fase_dois.return_value = True
        observador = _mock_observador()
        aplicador = MagicMock()
        aplicador.aplicar.side_effect = (
            lambda **kwargs: (
                kwargs["registrar_evento"]("REAJUSTE_APLICADO", "componentes=1"),
                kwargs["registrar_evento"]("SALVO", "ok"),
            )
        )
        p = self._processador(pagina_tabelas=pagina, aplicador=aplicador, observador=observador)

        relatorio = p.processar(
            [_tabela("T1")],
            [_componente()],
            run_id="abc",
            total_estimado=1,
            data_inicio="01/04/2026",
            data_fim="31/03/2027",
        )

        filtro = relatorio.detalhamento[0].eventos[1]
        assert filtro.codigo == "FILTRO_APLICADO"
        assert filtro.detalhes["filtro_reaplicado"] == "true"

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_registra_erro_quando_tabela_nao_e_encontrada(self, _sleep):
        pagina = self._pagina_mock(["T2"])
        pagina.validar_resultado_encontrado.side_effect = [
            RuntimeError("Tabela 'T1' nao encontrada na pesquisa."),
            None,
        ]
        observador = _mock_observador()

        aplicador = MagicMock()

        def _aplicar(**kwargs):
            kwargs["registrar_evento"]("REAJUSTE_APLICADO", "")
            kwargs["registrar_evento"]("SALVO", "")

        aplicador.aplicar.side_effect = _aplicar

        p = self._processador(pagina_tabelas=pagina, aplicador=aplicador, observador=observador)
        relatorio = p.processar(
            [_tabela("T1"), _tabela("T2")],
            [_componente()],
            run_id="abc",
            total_estimado=2,
            filtro_vigencia="01/04/2026 - 31/03/2027",
            data_inicio="01/04/2026",
            data_fim="31/03/2027",
        )

        assert relatorio.total_encontradas == 1
        assert relatorio.total_com_erro == 1
        assert relatorio.detalhamento[0].status == "ERRO"
        pagina.preparar_filtros_fase_dois.assert_called_once_with("01/04/2026", "31/03/2027")
        observador.registrar_sucesso.assert_called_once()

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_registra_erro_quando_vigencia_se_perde_apos_pesquisa(self, _sleep):
        pagina = self._pagina_mock(["T1"])
        pagina.validar_filtro_vigencia_aplicado.return_value = False
        observador = _mock_observador()
        p = self._processador(pagina_tabelas=pagina, observador=observador)

        relatorio = p.processar(
            [_tabela("T1")],
            [_componente()],
            run_id="abc",
            total_estimado=1,
            data_inicio="01/04/2026",
            data_fim="31/03/2027",
        )

        assert relatorio.total_com_erro == 1
        assert "Filtro de vigencia foi perdido apos pesquisar por nome" in relatorio.detalhamento[0].erro

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_para_quando_sem_tabelas_no_excel(self, _sleep):
        pagina = MagicMock()
        observador = _mock_observador()
        p = self._processador(pagina_tabelas=pagina, observador=observador)

        p.processar([], [_componente()], run_id="abc", total_estimado=0)

        observador.registrar_processando.assert_not_called()

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_interrompe_quando_navegador_e_encerrado(self, _sleep):
        pagina = self._pagina_mock(["T1", "T2"])
        pagina.acoes = MagicMock()
        pagina.acoes.salvar_screenshot.side_effect = InvalidSessionIdException("invalid session id")

        aplicador = MagicMock()
        aplicador.aplicar.side_effect = InvalidSessionIdException("invalid session id")

        observador = _mock_observador()
        p = self._processador(pagina_tabelas=pagina, aplicador=aplicador, observador=observador)

        with pytest.raises(RuntimeError, match="Navegador encerrado"):
            p.processar([_tabela("T1"), _tabela("T2")], [_componente()], run_id="abc", total_estimado=2)

        observador.registrar_processando.assert_called_once()
        observador.registrar_sistema.assert_called()

    @patch("src.servicos.processador_fase_dois.time.sleep")
    def test_preserva_indice_original_do_excel_quando_recebe_tuplas(self, _sleep):
        pagina = self._pagina_mock(["T5"])
        observador = _mock_observador()
        p = self._processador(pagina_tabelas=pagina, observador=observador)

        p.processar([(5, _tabela("T5"))], [_componente()], run_id="abc", total_estimado=1)

        contexto = observador.registrar_processando.call_args.args[0]
        assert contexto.indice == 5
