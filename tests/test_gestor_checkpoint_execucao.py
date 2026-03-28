from pathlib import Path

import src.aplicacao.gestor_checkpoint as gestor_checkpoint_mod
from src.aplicacao.fase_execucao import FaseExecucao, StatusExecucao
from src.servicos.leitor_excel import DadosTabelaExcel


def _tabela(nome: str) -> DadosTabelaExcel:
    return DadosTabelaExcel(
        nome=nome,
        data_inicio="01/04/2026",
        data_fim="31/03/2027",
        percentual=9.8,
    )


def _checkpoint(tmp_path, monkeypatch):
    caminho_excel = tmp_path / "dados.xlsx"
    caminho_excel.write_bytes(b"excel-fake")
    caminho_checkpoint = tmp_path / "checkpoint.json"
    monkeypatch.setattr(gestor_checkpoint_mod, "_CAMINHO_CHECKPOINT", caminho_checkpoint)
    return gestor_checkpoint_mod.GestorCheckpoint.carregar_ou_criar(caminho_excel)


def test_obter_tabelas_para_execucao_fase_dois_nao_depende_da_fase_um_local(tmp_path, monkeypatch):
    checkpoint = _checkpoint(tmp_path, monkeypatch)
    tabelas = [_tabela("T1"), _tabela("T2"), _tabela("T3")]
    checkpoint.sincronizar_tabelas(tabelas)

    checkpoint.registrar_resultado(FaseExecucao.FASE_1, 1, "T1", StatusExecucao.SUCESSO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_1, 2, "T2", StatusExecucao.ERRO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_1, 3, "T3", StatusExecucao.SUCESSO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_2, 1, "T1", StatusExecucao.SUCESSO.value)

    itens = checkpoint.obter_tabelas_para_execucao(FaseExecucao.FASE_2, tabelas)

    assert [(indice, tabela.nome) for indice, tabela in itens] == [(2, "T2"), (3, "T3")]


def test_obter_tabelas_para_execucao_fase_dois_somente_falhas_retorna_itens_com_erro(tmp_path, monkeypatch):
    checkpoint = _checkpoint(tmp_path, monkeypatch)
    tabelas = [_tabela("T1"), _tabela("T2"), _tabela("T3")]
    checkpoint.sincronizar_tabelas(tabelas)

    checkpoint.registrar_resultado(FaseExecucao.FASE_2, 1, "T1", StatusExecucao.ERRO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_2, 2, "T2", StatusExecucao.SUCESSO.value)

    itens = checkpoint.obter_tabelas_para_execucao(
        FaseExecucao.FASE_2,
        tabelas,
        somente_falhas=True,
    )

    assert [(indice, tabela.nome) for indice, tabela in itens] == [(1, "T1")]


def test_pode_marcar_fase_completa_respeita_itens_elegiveis(tmp_path, monkeypatch):
    checkpoint = _checkpoint(tmp_path, monkeypatch)
    tabelas = [_tabela("T1"), _tabela("T2"), _tabela("T3")]
    checkpoint.sincronizar_tabelas(tabelas)

    checkpoint.registrar_resultado(FaseExecucao.FASE_1, 1, "T1", StatusExecucao.SUCESSO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_1, 2, "T2", StatusExecucao.ERRO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_1, 3, "T3", StatusExecucao.SUCESSO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_2, 1, "T1", StatusExecucao.SUCESSO.value)

    assert checkpoint.pode_marcar_fase_completa(1) is False
    assert checkpoint.pode_marcar_fase_completa(2) is False

    checkpoint.registrar_resultado(FaseExecucao.FASE_1, 2, "T2", StatusExecucao.SUCESSO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_2, 2, "T2", StatusExecucao.SUCESSO.value)
    checkpoint.registrar_resultado(FaseExecucao.FASE_2, 3, "T3", StatusExecucao.SUCESSO.value)

    assert checkpoint.pode_marcar_fase_completa(1) is True
    assert checkpoint.pode_marcar_fase_completa(2) is True


def test_ja_processada_sincroniza_linhas_legadas_com_estado_granular(tmp_path, monkeypatch):
    checkpoint = _checkpoint(tmp_path, monkeypatch)
    tabelas = [_tabela("T1"), _tabela("T2"), _tabela("T3"), _tabela("T4")]
    checkpoint.sincronizar_tabelas(tabelas)

    checkpoint._estado["fase1"]["linhas_processadas"] = {
        "1": "T1",
        "2": "T2",
    }
    checkpoint._estado["fase1"]["status"] = "parcial"

    assert checkpoint.ja_processada(1, 1, "T1") is True
    assert checkpoint.obter_estado_item(1, "T1")["fase_1"] == StatusExecucao.SUCESSO.value

    assert checkpoint.ja_processada(1, 3, "T3") is False
    assert checkpoint.obter_estado_item(3, "T3")["fase_1"] == StatusExecucao.PENDENTE.value
