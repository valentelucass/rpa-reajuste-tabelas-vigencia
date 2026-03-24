"""
Registra sucesso e falha por tabela, grava CSV estruturado e tenta recuperar
a interface apos erro.
"""

import csv
import json
import logging
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from selenium.webdriver.common.keys import Keys

from src.aplicacao.fase_execucao import FaseExecucao, StatusExecucao, TipoExecucao
from src.infraestrutura.caminhos import LOGS_DIR
from src.infraestrutura.preparador_arquivos_execucao import CABECALHO_CSV
from src.infraestrutura.registro_processamento import (
    AlertaAnaliseExecucao,
    RegistroProcessamento,
    agora_iso,
)


TIPOS_ERRO = {
    "nao_encontrado": "Nao encontrado",
    "timeout": "Timeout",
    "elemento": "Elemento",
    "sessao": "Sessao invalida",
    "desconhecido": "Erro desconhecido",
}

ACOES_POR_TIPO = {
    "nao_encontrado": "Verificar nome no Excel ou confirmar cadastro manualmente no sistema",
    "timeout": "Verificar conectividade e tentar reprocessar",
    "elemento": "Tentar recuperar a interface e reprocessar",
    "sessao": "Sessao invalida; reiniciar a automacao com novo login",
    "desconhecido": "Verificar logs detalhados e screenshot para diagnostico manual",
}

_PADROES_CLASSIFICACAO: list[tuple[str, list[str]]] = [
    ("nao_encontrado", ["nao encontrad", "not found", "nenhum resultado", "nenhuma linha"]),
    ("timeout", ["timeout", "timed out", "tempo esgotado", "aguardando", "timeoutexception"]),
    (
        "elemento",
        [
            "not clickable",
            "not interactable",
            "staleelementreferenceexception",
            "nosuchelementexception",
            "move target out of bounds",
            "seletor",
        ],
    ),
    ("sessao", ["session", "sessao", "disconnected", "invalidsessionidexception", "navegador encerrado"]),
]


@dataclass
class ErroClassificado:
    tipo: str
    tipo_legivel: str
    mensagem: str
    acao_recomendada: str
    mensagem_operador: str


def classificar_erro(mensagem_erro: str, nome_tabela: str = "", indice: int = 0) -> ErroClassificado:
    texto = (mensagem_erro or "").lower()
    tipo = "desconhecido"

    for tipo_candidato, padroes in _PADROES_CLASSIFICACAO:
        if any(padrao in texto for padrao in padroes):
            tipo = tipo_candidato
            break

    tipo_legivel = TIPOS_ERRO[tipo]
    acao = ACOES_POR_TIPO[tipo]
    prefixo = f"Linha {indice} - Nome '{nome_tabela}': " if nome_tabela else ""
    return ErroClassificado(
        tipo=tipo,
        tipo_legivel=tipo_legivel,
        mensagem=(mensagem_erro or "")[:500],
        acao_recomendada=acao,
        mensagem_operador=f"{prefixo}{(mensagem_erro or '')[:200]}",
    )


class GestorOcorrenciasProcessamento:
    """Gerencia registros estruturados de processamento e recuperacao de interface."""

    def __init__(self, acoes, logger: Optional[logging.Logger] = None) -> None:
        self.acoes = acoes
        self.logger = logger or logging.getLogger("rpa")
        self._caminho_csv = LOGS_DIR / "processamento.csv"

    def registrar_sucesso(
        self,
        run_id: str,
        fase: int | FaseExecucao,
        indice: int,
        nome_tabela: str,
        mensagem: str = "Processado com sucesso",
        *,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
        pagina: int = 1,
        tentativas: int = 1,
        timestamp_inicio: str = "",
        timestamp_fim: str = "",
        duracao_ms: float = 0.0,
        reprocessado: bool = False,
        status_fase_1: str = StatusExecucao.PENDENTE.value,
        status_fase_2: str = StatusExecucao.PENDENTE.value,
    ) -> None:
        registro = RegistroProcessamento(
            run_id=run_id,
            fase=FaseExecucao.from_valor(fase),
            tipo_execucao=tipo_execucao,
            pagina=pagina,
            linha=indice,
            nome_tabela=nome_tabela,
            status=StatusExecucao.SUCESSO,
            mensagem=mensagem[:500],
            timestamp_inicio=timestamp_inicio or agora_iso(),
            timestamp_fim=timestamp_fim or agora_iso(),
            duracao_ms=int(round(duracao_ms or 0.0)),
            tentativas=tentativas,
            erro_tipo="",
            reprocessado=reprocessado,
            status_fase_1=status_fase_1,
            status_fase_2=status_fase_2,
        )
        self._gravar_csv(registro)
        self.logger.info(
            f"[{registro.fase.value}][sucesso] linha={indice} tabela={nome_tabela} "
            f"tipo_execucao={tipo_execucao.value} tentativas={tentativas}"
        )

    def registrar_falha(
        self,
        run_id: str,
        fase: int | FaseExecucao,
        indice: int,
        nome_tabela: str,
        mensagem: str,
        screenshot: str = "",
        etapa_falha: str = "",
        tempo_ms: float = 0.0,
        *,
        tipo_execucao: TipoExecucao = TipoExecucao.NORMAL,
        pagina: int = 1,
        tentativas: int = 1,
        timestamp_inicio: str = "",
        timestamp_fim: str = "",
        reprocessado: bool = False,
        status_fase_1: str = StatusExecucao.PENDENTE.value,
        status_fase_2: str = StatusExecucao.PENDENTE.value,
    ) -> ErroClassificado:
        erro = classificar_erro(mensagem, nome_tabela, indice)
        registro = RegistroProcessamento(
            run_id=run_id,
            fase=FaseExecucao.from_valor(fase),
            tipo_execucao=tipo_execucao,
            pagina=pagina,
            linha=indice,
            nome_tabela=nome_tabela,
            status=StatusExecucao.ERRO,
            mensagem=erro.mensagem,
            timestamp_inicio=timestamp_inicio or agora_iso(),
            timestamp_fim=timestamp_fim or agora_iso(),
            duracao_ms=int(round(tempo_ms or 0.0)),
            tentativas=tentativas,
            erro_tipo=erro.tipo,
            reprocessado=reprocessado,
            status_fase_1=status_fase_1,
            status_fase_2=status_fase_2,
            screenshot=screenshot,
            acao_recomendada=erro.acao_recomendada,
            etapa_falha=etapa_falha,
        )
        self._gravar_csv(registro)
        self.logger.error(
            f"[{registro.fase.value}][erro] linha={indice} tabela={nome_tabela} "
            f"tipo={erro.tipo_legivel} tipo_execucao={tipo_execucao.value} "
            f"tentativas={tentativas} mensagem={erro.mensagem}"
        )
        self.logger.error(traceback.format_exc())
        return erro

    def _gravar_csv(self, registro: RegistroProcessamento) -> None:
        try:
            with open(self._caminho_csv, "a", newline="", encoding="utf-8") as arquivo:
                writer = csv.DictWriter(arquivo, fieldnames=CABECALHO_CSV)
                writer.writerow(registro.to_dict())
        except Exception as erro:
            self.logger.warning(f"Nao foi possivel gravar no CSV: {erro}")

    def buscar_registros(
        self,
        *,
        run_id: str = "",
        status: str = "",
        fase: str = "",
        tipo_execucao: str = "",
        reprocessado: Optional[bool] = None,
    ) -> list[dict]:
        registros: list[dict] = []
        try:
            with open(self._caminho_csv, "r", encoding="utf-8", newline="") as arquivo:
                reader = csv.DictReader(arquivo)
                for row in reader:
                    if run_id and row.get("run_id") != run_id:
                        continue
                    if status and row.get("status") != status:
                        continue
                    if fase and row.get("fase") != fase:
                        continue
                    if tipo_execucao and row.get("tipo_execucao") != tipo_execucao:
                        continue
                    if reprocessado is not None:
                        valor = str(row.get("reprocessado", "")).lower() == "true"
                        if valor != reprocessado:
                            continue
                    registros.append(row)
        except FileNotFoundError:
            pass
        return registros

    def exportar_falhas_json(self, run_id: str = "") -> Path:
        falhas = self.buscar_registros(run_id=run_id, status=StatusExecucao.ERRO.value)
        caminho_json = LOGS_DIR / "falhas_reprocessar.json"
        caminho_json.write_text(json.dumps(falhas, ensure_ascii=False, indent=2), encoding="utf-8")
        self.logger.info(f"Exportadas {len(falhas)} falha(s) para {caminho_json}")
        return caminho_json

    def obter_nomes_com_falha(self, run_id: str = "") -> list[str]:
        nomes: list[str] = []
        for row in self.buscar_registros(run_id=run_id, status=StatusExecucao.ERRO.value):
            nome = row.get("nome_tabela", "")
            if nome and nome not in nomes:
                nomes.append(nome)
        return nomes

    def analisar_execucao(self, run_id: str = "") -> list[AlertaAnaliseExecucao]:
        registros = self.buscar_registros(run_id=run_id)
        alertas: list[AlertaAnaliseExecucao] = []
        erros_consecutivos = 0
        ultima_fase = ""
        maior_duracao = 0

        for row in registros:
            duracao = int(float(row.get("duracao_ms") or 0))
            maior_duracao = max(maior_duracao, duracao)
            if row.get("status") == StatusExecucao.ERRO.value:
                if row.get("fase") == ultima_fase:
                    erros_consecutivos += 1
                else:
                    erros_consecutivos = 1
                    ultima_fase = row.get("fase", "")
                if erros_consecutivos >= 5:
                    alertas.append(
                        AlertaAnaliseExecucao(
                            alerta="possivel_travamento",
                            motivo=f"{erros_consecutivos} falhas seguidas na mesma fase",
                            run_id=run_id,
                            fase=ultima_fase,
                            severidade="critical",
                        )
                    )
                    break
            else:
                erros_consecutivos = 0
                ultima_fase = row.get("fase", "")

        if maior_duracao >= 30000:
            alertas.append(
                AlertaAnaliseExecucao(
                    alerta="lentidao",
                    motivo=f"duracao maxima observada de {maior_duracao}ms",
                    run_id=run_id,
                    severidade="warning",
                )
            )

        return alertas

    def recuperar_interface(self) -> None:
        tentativas = [
            self._tentar_fechar_modal_botao,
            self._tentar_fechar_swal,
            self._tentar_enviar_esc,
        ]
        for tentativa in tentativas:
            try:
                tentativa()
            except Exception:
                pass
        try:
            self.acoes.aguardar_carregamento_finalizar(timeout=5)
        except Exception:
            pass

    def recuperar_interface_apos_erro(self) -> None:
        self.recuperar_interface()

    def _tentar_fechar_modal_botao(self) -> None:
        from selenium.webdriver.common.by import By

        for css in ("button.close", "a[data-dismiss='modal']", "button[data-dismiss='modal']"):
            try:
                botao = self.acoes.driver.find_element(By.CSS_SELECTOR, css)
                if botao.is_displayed():
                    self.acoes.clicar_com_seguranca(botao)
                    return
            except Exception:
                pass

    def _tentar_fechar_swal(self) -> None:
        from selenium.webdriver.common.by import By

        for css in ("button.swal2-cancel", "button.swal2-confirm", "#swal-confirm"):
            try:
                botao = self.acoes.driver.find_element(By.CSS_SELECTOR, css)
                if botao.is_displayed():
                    self.acoes.clicar_com_seguranca(botao)
                    return
            except Exception:
                pass

    def _tentar_enviar_esc(self) -> None:
        self.acoes.enviar_tecla(Keys.ESCAPE)
