"""
Sistema de autoavaliacao "neuronal" para testes RPA.
Analisa logs de execucao, detecta anomalias, padroes de falha e gera diagnostico.
"""

import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LogEtapa:
    """Log de uma etapa individual."""
    step: str
    status: str  # "success" | "error"
    tempo_ms: float
    linha: int
    valor: str = ""
    erro: str = ""


@dataclass
class LogFluxoLinha:
    """Log completo de processamento de uma linha."""
    linha: int
    etapas_executadas: list[LogEtapa] = field(default_factory=list)
    tempo_total_ms: float = 0.0
    status: str = "success"  # "success" | "error"
    erro: str = ""


@dataclass
class LogLoop:
    """Log consolidado do loop inteiro."""
    total_linhas: int = 0
    linhas_processadas: int = 0
    falhas: int = 0
    tempo_total_ms: float = 0.0
    linhas_log: list[LogFluxoLinha] = field(default_factory=list)


@dataclass
class ProblemaDetectado:
    """Problema identificado pela autoavaliacao."""
    tipo: str  # "tempo_alto", "falha_consecutiva", "etapa_faltante", "loop_incompleto", "travamento"
    descricao: str
    severidade: str = "warning"  # "info", "warning", "critical"
    linhas_afetadas: list[int] = field(default_factory=list)


@dataclass
class ResultadoAutoavaliacao:
    """Resultado completo da autoavaliacao."""
    status_geral: str = "ok"  # "ok", "warning", "critical"
    problemas_detectados: list[ProblemaDetectado] = field(default_factory=list)
    confiabilidade_fluxo: float = 1.0
    metricas: dict = field(default_factory=dict)


class AnalisadorExecucao:
    """
    Modulo de autoavaliacao que analisa logs de execucao do teste.
    Detecta: loops incompletos, etapas faltantes, tempos anormais,
    falhas consecutivas e travamentos silenciosos.
    """

    ETAPAS_OBRIGATORIAS = [
        "acessar_pagina",
        "desmarcar_filial",
        "filtrar_ativa_sim",
        "ler_nome_excel",
        "inserir_nome_busca",
        "executar_pesquisa",
        "validar_pesquisa",
        "refresh_pagina",
    ]

    LIMIAR_TEMPO_ALTO_MS = 5000.0
    LIMIAR_FALHAS_CONSECUTIVAS = 3
    LIMIAR_CONFIABILIDADE_MINIMA = 0.85

    def __init__(self):
        self.log_loop = LogLoop()
        self._fluxos: list[LogFluxoLinha] = []

    def registrar_etapa(self, etapa: LogEtapa) -> None:
        """Registra uma etapa individual no fluxo corrente."""
        if not self._fluxos:
            self._fluxos.append(LogFluxoLinha(linha=etapa.linha))

        fluxo_atual = self._fluxos[-1]
        if fluxo_atual.linha != etapa.linha:
            fluxo_atual = LogFluxoLinha(linha=etapa.linha)
            self._fluxos.append(fluxo_atual)

        fluxo_atual.etapas_executadas.append(etapa)
        fluxo_atual.tempo_total_ms += etapa.tempo_ms

        if etapa.status == "error":
            fluxo_atual.status = "error"
            fluxo_atual.erro = etapa.erro

    def finalizar_loop(self, total_esperado: int) -> None:
        """Finaliza o loop e computa metricas consolidadas."""
        self.log_loop.total_linhas = total_esperado
        self.log_loop.linhas_processadas = len(self._fluxos)
        self.log_loop.falhas = sum(1 for f in self._fluxos if f.status == "error")
        self.log_loop.tempo_total_ms = sum(f.tempo_total_ms for f in self._fluxos)
        self.log_loop.linhas_log = self._fluxos.copy()

    def analisar(self) -> ResultadoAutoavaliacao:
        """Executa a autoavaliacao completa e retorna diagnostico."""
        resultado = ResultadoAutoavaliacao()
        problemas = []

        problemas.extend(self._verificar_loop_completo())
        problemas.extend(self._verificar_etapas_obrigatorias())
        problemas.extend(self._verificar_tempos_anormais())
        problemas.extend(self._verificar_falhas_consecutivas())
        problemas.extend(self._verificar_travamento_silencioso())

        resultado.problemas_detectados = problemas
        resultado.metricas = self._calcular_metricas()
        resultado.confiabilidade_fluxo = self._calcular_confiabilidade()

        if any(p.severidade == "critical" for p in problemas):
            resultado.status_geral = "critical"
        elif any(p.severidade == "warning" for p in problemas):
            resultado.status_geral = "warning"
        else:
            resultado.status_geral = "ok"

        return resultado

    def _verificar_loop_completo(self) -> list[ProblemaDetectado]:
        """Detecta se o loop processou todas as linhas esperadas."""
        problemas = []
        if self.log_loop.linhas_processadas < self.log_loop.total_linhas:
            faltantes = self.log_loop.total_linhas - self.log_loop.linhas_processadas
            problemas.append(ProblemaDetectado(
                tipo="loop_incompleto",
                descricao=(
                    f"Loop incompleto: {self.log_loop.linhas_processadas}/{self.log_loop.total_linhas} "
                    f"linhas processadas ({faltantes} faltantes)"
                ),
                severidade="critical",
            ))
        return problemas

    def _verificar_etapas_obrigatorias(self) -> list[ProblemaDetectado]:
        """Verifica se cada fluxo executou todas as etapas obrigatorias."""
        problemas = []
        for fluxo in self._fluxos:
            etapas_executadas = {e.step for e in fluxo.etapas_executadas}
            faltantes = set(self.ETAPAS_OBRIGATORIAS) - etapas_executadas

            if faltantes:
                problemas.append(ProblemaDetectado(
                    tipo="etapa_faltante",
                    descricao=f"Linha {fluxo.linha}: etapas nao executadas: {', '.join(sorted(faltantes))}",
                    severidade="warning",
                    linhas_afetadas=[fluxo.linha],
                ))
        return problemas

    def _verificar_tempos_anormais(self) -> list[ProblemaDetectado]:
        """Detecta etapas com tempo acima do limiar."""
        problemas = []
        tempos_por_etapa: dict[str, list[float]] = {}

        for fluxo in self._fluxos:
            for etapa in fluxo.etapas_executadas:
                tempos_por_etapa.setdefault(etapa.step, []).append(etapa.tempo_ms)

                if etapa.tempo_ms > self.LIMIAR_TEMPO_ALTO_MS:
                    problemas.append(ProblemaDetectado(
                        tipo="tempo_alto",
                        descricao=(
                            f"Tempo alto na etapa '{etapa.step}' "
                            f"(linha {etapa.linha}): {etapa.tempo_ms:.0f}ms "
                            f"(limiar: {self.LIMIAR_TEMPO_ALTO_MS:.0f}ms)"
                        ),
                        severidade="warning",
                        linhas_afetadas=[etapa.linha],
                    ))

        # Detectar outliers por desvio padrao (apenas se tempos significativos)
        limiar_minimo_outlier_ms = 500.0
        for nome_etapa, tempos in tempos_por_etapa.items():
            if len(tempos) < 5:
                continue
            media = statistics.mean(tempos)
            desvio = statistics.stdev(tempos)
            if desvio == 0 or media < 1.0:
                continue

            for fluxo in self._fluxos:
                for etapa in fluxo.etapas_executadas:
                    if etapa.step == nome_etapa and etapa.tempo_ms > limiar_minimo_outlier_ms:
                        z_score = (etapa.tempo_ms - media) / desvio
                        if z_score > 3.0:
                            problemas.append(ProblemaDetectado(
                                tipo="tempo_alto",
                                descricao=(
                                    f"Outlier detectado na etapa '{nome_etapa}' "
                                    f"(linha {etapa.linha}): {etapa.tempo_ms:.0f}ms "
                                    f"(media: {media:.0f}ms, z-score: {z_score:.1f})"
                                ),
                                severidade="warning",
                                linhas_afetadas=[etapa.linha],
                            ))
        return problemas

    def _verificar_falhas_consecutivas(self) -> list[ProblemaDetectado]:
        """Detecta sequencias de falhas consecutivas."""
        problemas = []
        consecutivas = 0
        inicio_sequencia = 0

        for fluxo in self._fluxos:
            if fluxo.status == "error":
                if consecutivas == 0:
                    inicio_sequencia = fluxo.linha
                consecutivas += 1
            else:
                if consecutivas >= self.LIMIAR_FALHAS_CONSECUTIVAS:
                    problemas.append(ProblemaDetectado(
                        tipo="falha_consecutiva",
                        descricao=(
                            f"{consecutivas} falhas consecutivas detectadas "
                            f"nas linhas {inicio_sequencia}-{fluxo.linha - 1}"
                        ),
                        severidade="critical",
                        linhas_afetadas=list(range(inicio_sequencia, fluxo.linha)),
                    ))
                consecutivas = 0

        # Verificar se terminou com sequencia de falhas
        if consecutivas >= self.LIMIAR_FALHAS_CONSECUTIVAS:
            ultimo = self._fluxos[-1].linha if self._fluxos else 0
            problemas.append(ProblemaDetectado(
                tipo="falha_consecutiva",
                descricao=(
                    f"{consecutivas} falhas consecutivas detectadas "
                    f"nas linhas {inicio_sequencia}-{ultimo}"
                ),
                severidade="critical",
                linhas_afetadas=list(range(inicio_sequencia, ultimo + 1)),
            ))

        return problemas

    def _verificar_travamento_silencioso(self) -> list[ProblemaDetectado]:
        """Detecta fluxos com tempo total muito alto (possivel travamento)."""
        problemas = []
        if not self._fluxos:
            return problemas

        tempos = [f.tempo_total_ms for f in self._fluxos if f.tempo_total_ms > 0]
        if len(tempos) < 3:
            return problemas

        media = statistics.mean(tempos)
        limiar_travamento = media * 5

        for fluxo in self._fluxos:
            if fluxo.tempo_total_ms > limiar_travamento and fluxo.tempo_total_ms > 10000:
                problemas.append(ProblemaDetectado(
                    tipo="travamento",
                    descricao=(
                        f"Possivel travamento na linha {fluxo.linha}: "
                        f"{fluxo.tempo_total_ms:.0f}ms "
                        f"(media: {media:.0f}ms, limiar: {limiar_travamento:.0f}ms)"
                    ),
                    severidade="critical",
                    linhas_afetadas=[fluxo.linha],
                ))

        return problemas

    def _calcular_metricas(self) -> dict:
        """Calcula metricas consolidadas."""
        if not self._fluxos:
            return {}

        tempos_linha = [f.tempo_total_ms for f in self._fluxos]
        tempos_etapa: dict[str, list[float]] = {}

        for fluxo in self._fluxos:
            for etapa in fluxo.etapas_executadas:
                tempos_etapa.setdefault(etapa.step, []).append(etapa.tempo_ms)

        total_ms = self.log_loop.tempo_total_ms
        segundos = total_ms / 1000
        minutos = int(segundos // 60)
        segs_resto = segundos % 60

        return {
            "tempo_total": f"{minutos}min{segs_resto:.0f}s" if minutos else f"{segs_resto:.1f}s",
            "tempo_total_ms": total_ms,
            "tempo_medio_por_linha_ms": statistics.mean(tempos_linha) if tempos_linha else 0,
            "tempo_min_linha_ms": min(tempos_linha) if tempos_linha else 0,
            "tempo_max_linha_ms": max(tempos_linha) if tempos_linha else 0,
            "taxa_sucesso": (
                (self.log_loop.linhas_processadas - self.log_loop.falhas)
                / max(self.log_loop.linhas_processadas, 1)
            ),
            "taxa_erro": self.log_loop.falhas / max(self.log_loop.linhas_processadas, 1),
            "total_linhas": self.log_loop.total_linhas,
            "linhas_processadas": self.log_loop.linhas_processadas,
            "falhas": self.log_loop.falhas,
            "consistencia_loop": self.log_loop.linhas_processadas / max(self.log_loop.total_linhas, 1),
            "tempo_por_etapa": {
                nome: {
                    "media_ms": round(statistics.mean(t), 1),
                    "min_ms": round(min(t), 1),
                    "max_ms": round(max(t), 1),
                }
                for nome, t in tempos_etapa.items()
            },
        }

    def _calcular_confiabilidade(self) -> float:
        """Calcula score de confiabilidade do fluxo (0.0 a 1.0)."""
        if not self._fluxos or self.log_loop.total_linhas == 0:
            return 0.0

        # Fatores de confiabilidade
        completude = self.log_loop.linhas_processadas / self.log_loop.total_linhas
        taxa_sucesso = (
            (self.log_loop.linhas_processadas - self.log_loop.falhas)
            / max(self.log_loop.linhas_processadas, 1)
        )

        # Penalidade por falhas consecutivas
        max_consecutivas = 0
        consecutivas = 0
        for fluxo in self._fluxos:
            if fluxo.status == "error":
                consecutivas += 1
                max_consecutivas = max(max_consecutivas, consecutivas)
            else:
                consecutivas = 0

        penalidade_consecutivas = min(max_consecutivas * 0.05, 0.3)

        confiabilidade = (
            completude * 0.4
            + taxa_sucesso * 0.5
            + (1 - penalidade_consecutivas) * 0.1
        )

        return round(max(0.0, min(1.0, confiabilidade)), 4)

    def gerar_log_etapa(self, step: str, status: str, tempo_ms: float,
                         linha: int, valor: str = "") -> dict:
        """Gera log formatado de uma etapa (formato JSON)."""
        return {
            "step": step,
            "status": status,
            "tempo_ms": round(tempo_ms, 1),
            "linha": linha,
            "valor": valor,
        }

    def gerar_log_fluxo(self, fluxo: LogFluxoLinha) -> dict:
        """Gera log formatado de um fluxo completo (formato JSON)."""
        return {
            "linha": fluxo.linha,
            "etapas_executadas": [e.step for e in fluxo.etapas_executadas],
            "tempo_total_ms": round(fluxo.tempo_total_ms, 1),
            "status": fluxo.status,
        }

    def gerar_log_loop(self) -> dict:
        """Gera log formatado do loop (formato JSON)."""
        metricas = self._calcular_metricas()
        return {
            "total_linhas": self.log_loop.total_linhas,
            "linhas_processadas": self.log_loop.linhas_processadas,
            "falhas": self.log_loop.falhas,
            "tempo_total": metricas.get("tempo_total", "0s"),
        }

    def gerar_relatorio_completo(self) -> dict:
        """Gera relatorio completo com logs e autoavaliacao."""
        avaliacao = self.analisar()
        return {
            "log_loop": self.gerar_log_loop(),
            "autoavaliacao": {
                "status_geral": avaliacao.status_geral,
                "problemas_detectados": [
                    p.descricao for p in avaliacao.problemas_detectados
                ],
                "confiabilidade_fluxo": avaliacao.confiabilidade_fluxo,
            },
            "metricas": avaliacao.metricas,
        }
