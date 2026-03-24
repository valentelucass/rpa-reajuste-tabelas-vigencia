"""
Testes do sistema de retencao de execucoes por contagem.
Valida registro, limpeza, e protecao da execucao atual.
"""

import csv
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from src.infraestrutura.registro_execucoes import (
    _CAMINHO_MANIFESTO,
    _carregar_manifesto,
    _remover_artefatos_execucao,
    _salvar_manifesto,
    limpar_execucoes_antigas,
    registrar_execucao,
)


@pytest.fixture
def dir_logs(tmp_path, monkeypatch):
    """Redireciona LOGS_DIR, REPORTS_DIR e SCREENSHOTS_DIR para tmp."""
    logs = tmp_path / "logs"
    reports = tmp_path / "reports"
    screenshots = reports / "screenshots"
    logs.mkdir()
    reports.mkdir()
    screenshots.mkdir()

    monkeypatch.setattr(
        "src.infraestrutura.registro_execucoes.LOGS_DIR", logs
    )
    monkeypatch.setattr(
        "src.infraestrutura.registro_execucoes.REPORTS_DIR", reports
    )
    monkeypatch.setattr(
        "src.infraestrutura.registro_execucoes.SCREENSHOTS_DIR", screenshots
    )
    monkeypatch.setattr(
        "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
        logs / "execucoes.json",
    )

    return {"logs": logs, "reports": reports, "screenshots": screenshots}


@pytest.fixture
def logger():
    return logging.getLogger("teste_retencao")


class TestRegistroExecucao:
    def test_registrar_primeira_execucao(self, dir_logs):
        manifesto = dir_logs["logs"] / "execucoes.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ):
            registrar_execucao("run_001")
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            assert len(dados) == 1
            assert dados[0]["run_id"] == "run_001"

    def test_nao_duplica_execucao(self, dir_logs):
        manifesto = dir_logs["logs"] / "execucoes.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ):
            registrar_execucao("run_001")
            registrar_execucao("run_001")
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            assert len(dados) == 1

    def test_registrar_multiplas_execucoes(self, dir_logs):
        manifesto = dir_logs["logs"] / "execucoes.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ):
            for i in range(5):
                registrar_execucao(f"run_{i:03d}")
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            assert len(dados) == 5


class TestLimpezaExecucoes:
    def _popular_manifesto(self, manifesto: Path, qtd: int) -> list[str]:
        """Cria manifesto com N execucoes e retorna os run_ids."""
        execucoes = []
        for i in range(qtd):
            rid = f"20260318_{170000 + i * 100:06d}_{i:06x}"
            execucoes.append({
                "run_id": rid,
                "timestamp": f"2026-03-18T{17 + i // 60:02d}:{i % 60:02d}:00",
            })
        manifesto.write_text(
            json.dumps(execucoes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return [e["run_id"] for e in execucoes]

    def _criar_artefatos(self, dir_logs: dict, run_id: str) -> None:
        """Cria artefatos fake para um run_id."""
        reports = dir_logs["reports"]
        (reports / f"fase2_relatorio_{run_id}.json").write_text("{}", encoding="utf-8")
        (reports / f"fase2_relatorio_{run_id}.md").write_text("# R", encoding="utf-8")

        prefixo = run_id[:15]
        screenshots = dir_logs["screenshots"]
        (screenshots / f"erro_test_{prefixo}.png").write_bytes(b"PNG")

    def test_nao_limpa_quando_dentro_do_limite(self, dir_logs, logger):
        manifesto = dir_logs["logs"] / "execucoes.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ), patch("src.infraestrutura.registro_execucoes.config") as mock_config:
            mock_config.MAX_EXECUCOES_LOG = 20
            run_ids = self._popular_manifesto(manifesto, 5)
            limpar_execucoes_antigas(run_ids[-1], logger)
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            assert len(dados) == 5

    def test_limpa_execucoes_excedentes(self, dir_logs, logger):
        manifesto = dir_logs["logs"] / "execucoes.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ), patch("src.infraestrutura.registro_execucoes.config") as mock_config:
            mock_config.MAX_EXECUCOES_LOG = 3
            run_ids = self._popular_manifesto(manifesto, 5)

            for rid in run_ids:
                self._criar_artefatos(dir_logs, rid)

            limpar_execucoes_antigas(run_ids[-1], logger)
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            assert len(dados) == 3

            # As 3 mais recentes devem ter sobrevivido
            ids_restantes = {e["run_id"] for e in dados}
            assert run_ids[-1] in ids_restantes
            assert run_ids[-2] in ids_restantes
            assert run_ids[-3] in ids_restantes

            # As 2 mais antigas devem ter sido removidas
            assert run_ids[0] not in ids_restantes
            assert run_ids[1] not in ids_restantes

    def test_artefatos_removidos(self, dir_logs, logger):
        manifesto = dir_logs["logs"] / "execucoes.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ), patch("src.infraestrutura.registro_execucoes.config") as mock_config:
            mock_config.MAX_EXECUCOES_LOG = 2
            run_ids = self._popular_manifesto(manifesto, 4)

            for rid in run_ids:
                self._criar_artefatos(dir_logs, rid)

            limpar_execucoes_antigas(run_ids[-1], logger)

            reports = dir_logs["reports"]
            # Removidos (run_ids[0] e run_ids[1])
            assert not (reports / f"fase2_relatorio_{run_ids[0]}.json").exists()
            assert not (reports / f"fase2_relatorio_{run_ids[0]}.md").exists()
            assert not (reports / f"fase2_relatorio_{run_ids[1]}.json").exists()

            # Mantidos (run_ids[2] e run_ids[3])
            assert (reports / f"fase2_relatorio_{run_ids[2]}.json").exists()
            assert (reports / f"fase2_relatorio_{run_ids[3]}.json").exists()

    def test_nunca_remove_execucao_atual(self, dir_logs, logger):
        manifesto = dir_logs["logs"] / "execucoes.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ), patch("src.infraestrutura.registro_execucoes.config") as mock_config:
            mock_config.MAX_EXECUCOES_LOG = 1
            run_ids = self._popular_manifesto(manifesto, 3)

            for rid in run_ids:
                self._criar_artefatos(dir_logs, rid)

            # Passa o PRIMEIRO (mais antigo) como atual — ele deve sobreviver
            limpar_execucoes_antigas(run_ids[0], logger)

            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            ids_restantes = {e["run_id"] for e in dados}

            # A execucao atual (run_ids[0]) DEVE sobreviver
            assert run_ids[0] in ids_restantes
            # A mais recente tambem sobrevive (dentro do limite)
            assert run_ids[-1] in ids_restantes

    def test_limpa_entradas_csv(self, dir_logs, logger):
        manifesto = dir_logs["logs"] / "execucoes.json"
        logs = dir_logs["logs"]

        # Criar CSV com entradas de varias execucoes
        caminho_csv = logs / "processamento.csv"
        cabecalho = ["timestamp", "run_id", "fase", "indice", "nome_tabela", "status"]
        with open(caminho_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cabecalho)
            writer.writeheader()
            writer.writerow({"timestamp": "t1", "run_id": "run_old", "fase": "1",
                             "indice": "1", "nome_tabela": "T1", "status": "ok"})
            writer.writerow({"timestamp": "t2", "run_id": "run_new", "fase": "1",
                             "indice": "1", "nome_tabela": "T2", "status": "ok"})

        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ), patch("src.infraestrutura.registro_execucoes.config") as mock_config, \
             patch("src.infraestrutura.registro_execucoes.LOGS_DIR", logs):
            mock_config.MAX_EXECUCOES_LOG = 1

            execucoes = [
                {"run_id": "run_old", "timestamp": "2026-03-18T10:00:00"},
                {"run_id": "run_new", "timestamp": "2026-03-18T11:00:00"},
            ]
            manifesto.write_text(json.dumps(execucoes), encoding="utf-8")

            limpar_execucoes_antigas("run_new", logger)

            with open(caminho_csv, "r", encoding="utf-8", newline="") as f:
                reader = list(csv.DictReader(f))
            assert len(reader) == 1
            assert reader[0]["run_id"] == "run_new"

    def test_limpa_entradas_trace(self, dir_logs, logger):
        manifesto = dir_logs["logs"] / "execucoes.json"
        logs = dir_logs["logs"]

        caminho_trace = logs / "execution_trace.json"
        caminho_trace.write_text(
            json.dumps({
                "execucoes": [
                    {"run_id": "run_old", "nome": "etapa1"},
                    {"run_id": "run_old", "nome": "etapa2"},
                    {"run_id": "run_new", "nome": "etapa1"},
                ]
            }),
            encoding="utf-8",
        )

        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ), patch("src.infraestrutura.registro_execucoes.config") as mock_config, \
             patch("src.infraestrutura.registro_execucoes.LOGS_DIR", logs):
            mock_config.MAX_EXECUCOES_LOG = 1

            execucoes = [
                {"run_id": "run_old", "timestamp": "2026-03-18T10:00:00"},
                {"run_id": "run_new", "timestamp": "2026-03-18T11:00:00"},
            ]
            manifesto.write_text(json.dumps(execucoes), encoding="utf-8")

            limpar_execucoes_antigas("run_new", logger)

            dados = json.loads(caminho_trace.read_text(encoding="utf-8"))
            assert len(dados["execucoes"]) == 1
            assert dados["execucoes"][0]["run_id"] == "run_new"


class TestManifestoCorreto:
    def test_manifesto_corrompido_retorna_vazio(self, dir_logs):
        manifesto = dir_logs["logs"] / "execucoes.json"
        manifesto.write_text("INVALIDO{{{", encoding="utf-8")
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ):
            dados = _carregar_manifesto()
            assert dados == []

    def test_manifesto_inexistente_retorna_vazio(self, dir_logs):
        manifesto = dir_logs["logs"] / "nao_existe.json"
        with patch(
            "src.infraestrutura.registro_execucoes._CAMINHO_MANIFESTO",
            manifesto,
        ):
            dados = _carregar_manifesto()
            assert dados == []
