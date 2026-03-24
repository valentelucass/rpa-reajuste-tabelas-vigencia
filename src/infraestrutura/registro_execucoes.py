"""
Manifesto de execucoes para controle de retencao.
Registra cada run_id e seus artefatos, permite limpeza das mais antigas.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from src.infraestrutura.caminhos import LOGS_DIR, REPORTS_DIR, SCREENSHOTS_DIR


_CAMINHO_MANIFESTO = LOGS_DIR / "execucoes.json"


def _carregar_manifesto() -> list[dict]:
    """Carrega o manifesto de execucoes do disco."""
    if not _CAMINHO_MANIFESTO.exists():
        return []
    try:
        dados = json.loads(_CAMINHO_MANIFESTO.read_text(encoding="utf-8"))
        if isinstance(dados, list):
            return dados
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _salvar_manifesto(execucoes: list[dict]) -> None:
    """Persiste o manifesto no disco."""
    _CAMINHO_MANIFESTO.parent.mkdir(parents=True, exist_ok=True)
    _CAMINHO_MANIFESTO.write_text(
        json.dumps(execucoes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def registrar_execucao(run_id: str) -> None:
    """
    Registra uma nova execucao no manifesto.
    Chamado no inicio de cada execucao pelo PreparadorArquivosExecucao.
    """
    execucoes = _carregar_manifesto()

    # Evitar duplicatas (caso de reinicio)
    if any(e.get("run_id") == run_id for e in execucoes):
        return

    execucoes.append({
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    _salvar_manifesto(execucoes)


def limpar_execucoes_antigas(
    run_id_atual: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Remove artefatos de execucoes que excedem MAX_EXECUCOES_LOG.
    Nunca remove a execucao atual.
    """
    _log = logger or logging.getLogger("rpa")
    maximo = config.MAX_EXECUCOES_LOG

    execucoes = _carregar_manifesto()
    if len(execucoes) <= maximo:
        return

    _log.info(
        f"[LOG][LIMPEZA_INICIADA] total_execucoes={len(execucoes)} "
        f"maximo={maximo}"
    )

    # Ordenar por timestamp (mais antiga primeiro) — o manifesto ja esta em ordem
    # mas garante caso tenha sido editado manualmente
    execucoes.sort(key=lambda e: e.get("timestamp", ""))

    # Identificar execucoes a remover (as mais antigas, preservando as N mais recentes)
    a_manter = execucoes[-maximo:]
    a_remover = [e for e in execucoes if e not in a_manter]

    # Nunca remover a execucao atual
    a_remover = [e for e in a_remover if e.get("run_id") != run_id_atual]

    removidas = 0
    for execucao in a_remover:
        rid = execucao.get("run_id", "")
        if not rid:
            continue

        arquivos_removidos = _remover_artefatos_execucao(rid, _log)
        if arquivos_removidos >= 0:
            _log.info(
                f"[LOG][REMOVIDO] run_id={rid} "
                f"arquivos={arquivos_removidos}"
            )
            removidas += 1

    # Atualizar manifesto (manter apenas as que sobreviveram)
    ids_removidos = {e.get("run_id") for e in a_remover}
    execucoes_restantes = [e for e in execucoes if e.get("run_id") not in ids_removidos]
    _salvar_manifesto(execucoes_restantes)

    _log.info(
        f"[LOG][TOTAL_RESTANTE] execucoes={len(execucoes_restantes)} "
        f"removidas={removidas}"
    )


def _remover_artefatos_execucao(run_id: str, logger: logging.Logger) -> int:
    """
    Remove todos os artefatos associados a um run_id.
    Retorna quantidade de arquivos removidos.
    """
    removidos = 0

    # 1. Relatorios da Fase 2 (reports/fase2_relatorio_{run_id}.json e .md)
    for ext in ("json", "md"):
        caminho = REPORTS_DIR / f"fase2_relatorio_{run_id}.{ext}"
        if caminho.exists():
            try:
                caminho.unlink()
                removidos += 1
            except OSError as e:
                logger.warning(f"[LOG][LIMPEZA] Falha ao remover {caminho.name}: {e}")

    # 2. Screenshots com timestamp do run_id
    #    run_id formato: 20260318_171824_3742f8
    #    screenshots formato: erro_*_20260318_171824.png
    #    Extrair a parte de data/hora (primeiros 15 chars: YYYYMMDD_HHMMSS)
    prefixo_tempo = run_id[:15] if len(run_id) >= 15 else ""
    if prefixo_tempo and SCREENSHOTS_DIR.exists():
        for screenshot in SCREENSHOTS_DIR.glob("*.png"):
            # Verificar se o timestamp do screenshot corresponde ao run_id
            if prefixo_tempo in screenshot.name:
                try:
                    screenshot.unlink()
                    removidos += 1
                except OSError:
                    pass

    # 3. Entradas no execution_trace.json (filtrar por run_id)
    caminho_trace = LOGS_DIR / "execution_trace.json"
    if caminho_trace.exists():
        try:
            dados = json.loads(caminho_trace.read_text(encoding="utf-8"))
            etapas = dados.get("execucoes", [])
            antes = len(etapas)
            dados["execucoes"] = [e for e in etapas if e.get("run_id") != run_id]
            depois = len(dados["execucoes"])
            if depois < antes:
                caminho_trace.write_text(
                    json.dumps(dados, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                removidos += antes - depois
        except (json.JSONDecodeError, OSError):
            pass

    # 4. Entradas no processamento.csv (filtrar por run_id)
    caminho_csv = LOGS_DIR / "processamento.csv"
    if caminho_csv.exists():
        try:
            import csv
            with open(caminho_csv, "r", encoding="utf-8", newline="") as f:
                reader = list(csv.DictReader(f))
            if reader:
                antes = len(reader)
                filtrado = [r for r in reader if r.get("run_id") != run_id]
                if len(filtrado) < antes:
                    cabecalho = list(reader[0].keys())
                    with open(caminho_csv, "w", encoding="utf-8", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=cabecalho)
                        writer.writeheader()
                        writer.writerows(filtrado)
                    removidos += antes - len(filtrado)
        except (OSError, KeyError):
            pass

    return removidos
