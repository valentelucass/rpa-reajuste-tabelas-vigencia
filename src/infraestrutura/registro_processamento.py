"""
Modelos do registro estruturado de processamento.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.aplicacao.fase_execucao import FaseExecucao, StatusExecucao, TipoExecucao


@dataclass
class RegistroProcessamento:
    run_id: str
    fase: FaseExecucao
    tipo_execucao: TipoExecucao
    pagina: int
    linha: int
    nome_tabela: str
    status: StatusExecucao
    mensagem: str
    timestamp_inicio: str
    timestamp_fim: str
    duracao_ms: int
    tentativas: int
    erro_tipo: str
    reprocessado: bool
    status_fase_1: str = StatusExecucao.PENDENTE.value
    status_fase_2: str = StatusExecucao.PENDENTE.value
    screenshot: str = ""
    acao_recomendada: str = ""
    etapa_falha: str = ""

    def to_dict(self) -> dict[str, str | int | bool]:
        return {
            "run_id": self.run_id,
            "fase": self.fase.value,
            "tipo_execucao": self.tipo_execucao.value,
            "pagina": self.pagina,
            "linha": self.linha,
            "nome_tabela": self.nome_tabela,
            "status": self.status.value,
            "mensagem": self.mensagem,
            "timestamp_inicio": self.timestamp_inicio,
            "timestamp_fim": self.timestamp_fim,
            "duracao_ms": self.duracao_ms,
            "tentativas": self.tentativas,
            "erro_tipo": self.erro_tipo,
            "reprocessado": self.reprocessado,
            "status_fase_1": self.status_fase_1,
            "status_fase_2": self.status_fase_2,
            "screenshot": self.screenshot,
            "acao_recomendada": self.acao_recomendada,
            "etapa_falha": self.etapa_falha,
        }


@dataclass
class AlertaAnaliseExecucao:
    alerta: str
    motivo: str
    run_id: str = ""
    fase: str = ""
    severidade: str = "warning"


def agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_iso(valor: str) -> Optional[datetime]:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None
