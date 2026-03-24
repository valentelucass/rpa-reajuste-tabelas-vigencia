"""
Rastreamento estruturado de etapas de execução.
Grava execution_trace.json e current_step.json a cada etapa.
"""

import json
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

from src.infraestrutura.caminhos import LOGS_DIR, SCREENSHOTS_DIR


@dataclass
class ContextoEtapa:
    nome: str
    descricao: str
    status: str = "em_andamento"
    contexto: dict[str, Any] = field(default_factory=dict)
    timestamp_inicio: str = field(default_factory=lambda: datetime.now().isoformat())
    timestamp_fim: Optional[str] = None
    screenshot: Optional[str] = None
    traceback: Optional[str] = None


class RastreadorEtapas:
    """
    Registra o início, sucesso e erro de cada etapa nomeada.
    Compatible com uso via context manager.
    """

    def __init__(self, run_id: str, driver=None) -> None:
        self.run_id = run_id
        self.driver = driver

    @contextmanager
    def etapa(
        self,
        nome: str,
        descricao: str,
        contexto: Optional[dict[str, Any]] = None
    ) -> Generator[ContextoEtapa, None, None]:
        """Context manager que registra início, sucesso ou erro da etapa."""
        ctx = ContextoEtapa(
            nome=nome,
            descricao=descricao,
            contexto=contexto or {}
        )
        self._gravar_current_step(ctx)
        try:
            yield ctx
            ctx.status = "sucesso"
            ctx.timestamp_fim = datetime.now().isoformat()
        except Exception as erro:
            ctx.status = "erro"
            ctx.timestamp_fim = datetime.now().isoformat()
            ctx.traceback = traceback.format_exc()
            ctx.screenshot = self._capturar_screenshot(nome)
            raise
        finally:
            self._gravar_trace(ctx)
            self._gravar_current_step(ctx)

    def registrar_erro(
        self,
        erro: Exception,
        screenshot: Optional[str] = None,
        tb: Optional[str] = None
    ) -> None:
        ctx = ContextoEtapa(
            nome="erro_generico",
            descricao=str(erro),
            status="erro",
            timestamp_fim=datetime.now().isoformat(),
            screenshot=screenshot,
            traceback=tb or traceback.format_exc()
        )
        self._gravar_trace(ctx)
        self._gravar_current_step(ctx)

    def _capturar_screenshot(self, nome_etapa: str) -> Optional[str]:
        if self.driver is None:
            return None
        try:
            nome_arquivo = f"erro_{nome_etapa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            caminho = SCREENSHOTS_DIR / nome_arquivo
            self.driver.save_screenshot(str(caminho))
            return str(caminho)
        except Exception:
            return None

    def _gravar_trace(self, ctx: ContextoEtapa) -> None:
        caminho = LOGS_DIR / "execution_trace.json"
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {"execucoes": []}
            registro = asdict(ctx)
            registro["run_id"] = self.run_id
            dados["execucoes"].append(registro)
            caminho.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _gravar_current_step(self, ctx: ContextoEtapa) -> None:
        caminho = LOGS_DIR / "current_step.json"
        try:
            dados = {
                "run_id": self.run_id,
                "etapa": ctx.nome,
                "descricao": ctx.descricao,
                "status": ctx.status,
                "timestamp": ctx.timestamp_inicio,
                "contexto": ctx.contexto
            }
            caminho.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass
