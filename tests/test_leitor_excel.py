"""
Testes unitários para LeitorExcel.
Usa openpyxl para criar workbooks em memória, sem depender de arquivos reais.
"""

import io
import pytest
import openpyxl

from src.servicos.leitor_excel import LeitorExcel, DadosTabelaExcel, ComponenteReajuste


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _criar_excel_memoria(aba1_linhas: list[list], aba2_linhas: list[list]) -> str:
    """
    Cria um Excel em memória e salva em arquivo temporário.
    Retorna o caminho do arquivo.
    """
    import tempfile, os
    wb = openpyxl.Workbook()

    # Aba 1
    ws1 = wb.active
    ws1.title = "Aba1"
    ws1.append(["NOME DA TABELA", "DATA VIGÊNCIA", "PERCENTUAL"])
    for linha in aba1_linhas:
        ws1.append(linha)

    # Aba 2
    ws2 = wb.create_sheet("Aba2")
    ws2.append(["ABA", "NOME DA TAXA"])
    for linha in aba2_linhas:
        ws2.append(linha)

    caminho = tempfile.mktemp(suffix=".xlsx")
    wb.save(caminho)
    return caminho


# ---------------------------------------------------------------------------
# Testes — ler_aba_um
# ---------------------------------------------------------------------------

class TestLerAbaUm:
    def test_leitura_basica(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[["Tabela Teste", "01/04/2026 - 31/03/2027", "9,80%"]],
            aba2_linhas=[["Taxas", "Taxa Básica"]],
        )
        leitor = LeitorExcel(caminho)
        tabelas = leitor.ler_aba_um()
        assert len(tabelas) == 1
        t = tabelas[0]
        assert t.nome == "Tabela Teste"
        assert t.data_inicio == "01/04/2026"
        assert t.data_fim == "31/03/2027"
        assert t.percentual == pytest.approx(9.8)

    def test_percentual_sem_simbolo(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[["Tabela A", "01/01/2026 - 31/12/2026", "5.5"]],
            aba2_linhas=[["Taxas", "Taxa X"]],
        )
        leitor = LeitorExcel(caminho)
        tabelas = leitor.ler_aba_um()
        assert tabelas[0].percentual == pytest.approx(5.5)

    def test_percentual_virgula_americana(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[["Tabela B", "01/01/2026 - 31/12/2026", "12,50%"]],
            aba2_linhas=[["Taxas", "Taxa X"]],
        )
        leitor = LeitorExcel(caminho)
        tabelas = leitor.ler_aba_um()
        assert tabelas[0].percentual == pytest.approx(12.5)

    def test_linha_vazia_ignorada(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[
                ["Tabela C", "01/01/2026 - 31/12/2026", "5%"],
                [None, None, None],
                ["Tabela D", "01/01/2026 - 31/12/2026", "3%"],
            ],
            aba2_linhas=[["Taxas", "Taxa X"]],
        )
        leitor = LeitorExcel(caminho)
        tabelas = leitor.ler_aba_um()
        assert len(tabelas) == 2
        assert tabelas[0].nome == "Tabela C"
        assert tabelas[1].nome == "Tabela D"

    def test_multiplas_tabelas(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[
                ["Tabela 1", "01/04/2026 - 31/03/2027", "9,80%"],
                ["Tabela 2", "01/04/2026 - 31/03/2027", "9,80%"],
                ["Tabela 3", "01/04/2026 - 31/03/2027", "9,80%"],
            ],
            aba2_linhas=[["Taxas", "Taxa X"]],
        )
        leitor = LeitorExcel(caminho)
        tabelas = leitor.ler_aba_um()
        assert len(tabelas) == 3


# ---------------------------------------------------------------------------
# Testes — ler_aba_dois
# ---------------------------------------------------------------------------

class TestLerAbaDois:
    def test_leitura_basica(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[["Tabela A", "01/01/2026 - 31/12/2026", "5%"]],
            aba2_linhas=[
                ["Taxas", "Taxa Básica"],
                ["Excessos", "Taxa Excesso"],
            ],
        )
        leitor = LeitorExcel(caminho)
        componentes = leitor.ler_aba_dois()
        assert len(componentes) == 2
        assert componentes[0].nome_taxa == "Taxa Básica"
        assert componentes[1].nome_taxa == "Taxa Excesso"

    def test_linha_vazia_ignorada(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[["Tabela A", "01/01/2026 - 31/12/2026", "5%"]],
            aba2_linhas=[
                ["Taxas", "Taxa A"],
                [None, None],
                ["Adicionais", "Taxa B"],
            ],
        )
        leitor = LeitorExcel(caminho)
        componentes = leitor.ler_aba_dois()
        assert len(componentes) == 2


# ---------------------------------------------------------------------------
# Testes — validar
# ---------------------------------------------------------------------------

class TestValidar:
    def test_arquivo_inexistente(self):
        leitor = LeitorExcel("/caminho/que/nao/existe.xlsx")
        with pytest.raises(FileNotFoundError):
            leitor.validar()

    def test_excel_valido_nao_lanca(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[["Tabela A", "01/01/2026 - 31/12/2026", "5%"]],
            aba2_linhas=[["Taxas", "Taxa A"]],
        )
        leitor = LeitorExcel(caminho)
        leitor.validar()  # não deve lançar


# ---------------------------------------------------------------------------
# Testes — parsear_vigencia
# ---------------------------------------------------------------------------

class TestParsearVigencia:
    def _leitor(self):
        caminho = _criar_excel_memoria(
            aba1_linhas=[["T", "01/01/2026 - 31/12/2026", "5%"]],
            aba2_linhas=[["Taxas", "X"]],
        )
        return LeitorExcel(caminho)

    def test_formato_padrao(self):
        leitor = self._leitor()
        inicio, fim = leitor._parsear_vigencia("01/04/2026 - 31/03/2027")
        assert inicio == "01/04/2026"
        assert fim == "31/03/2027"

    def test_formato_invalido_lanca(self):
        leitor = self._leitor()
        with pytest.raises(ValueError):
            leitor._parsear_vigencia("data invalida sem separador")
