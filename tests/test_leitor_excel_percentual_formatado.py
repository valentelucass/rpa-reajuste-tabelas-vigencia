import tempfile

import openpyxl
import pytest

from src.servicos.leitor_excel import LeitorExcel


def test_percentual_em_celula_formatada_como_porcentagem():
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Aba1"
    ws1.append(["NOME DA TABELA", "DATA VIGENCIA", "PERCENTUAL"])
    ws1.append(["Tabela Percentual", "01/04/2026 - 31/03/2027", 0.098])
    ws1["C2"].number_format = "0.00%"

    ws2 = wb.create_sheet("Aba2")
    ws2.append(["ABA", "NOME DA TAXA"])
    ws2.append(["Taxas", "Min. frete peso"])

    caminho = tempfile.mktemp(suffix=".xlsx")
    wb.save(caminho)

    leitor = LeitorExcel(caminho)
    tabelas = leitor.ler_aba_um()

    assert tabelas[0].percentual == pytest.approx(9.8)
