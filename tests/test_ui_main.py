import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel

from src.auto_delete_clientes import (
    ModoExecucaoAutoDelete,
    OrdemExecucaoAutoDelete,
    RegistroAutoDelete,
)
from src.monitoramento.observador_execucao import ContextoTabelaProcessamento
from src.ui.logger_ui import EntradaLog
from src.ui.ui_main import JanelaPainelAutomacao


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _configurar_persistencia_auto_delete(monkeypatch, tmp_path, registros=None):
    import src.auto_delete_clientes.persistencia as persistencia

    registros = registros or []
    base = tmp_path / "logs" / "auto_delete"
    execucoes = base / "execucoes"
    screenshots = base / "screenshots"
    historico = base / "execucoes.json"
    falhas = base / "falhas_pendentes.json"
    reprocessar = base / "reprocessar.xlsx"

    monkeypatch.setattr(persistencia, "AUTO_DELETE_DIR", base)
    monkeypatch.setattr(persistencia, "EXECUCOES_DIR", execucoes)
    monkeypatch.setattr(persistencia, "SCREENSHOTS_DIR", screenshots)
    monkeypatch.setattr(persistencia, "HISTORICO_EXECUCOES_PATH", historico)
    monkeypatch.setattr(persistencia, "FALHAS_PENDENTES_PATH", falhas)
    monkeypatch.setattr(persistencia, "REPROCESSAMENTO_XLSX_PATH", reprocessar)

    base.mkdir(parents=True, exist_ok=True)
    execucoes.mkdir(parents=True, exist_ok=True)
    screenshots.mkdir(parents=True, exist_ok=True)
    historico.write_text("[]", encoding="utf-8")
    falhas.write_text(
        json.dumps(
            {
                "run_id": "teste",
                "timestamp": "2026-03-21T09:03:22",
                "caminho_excel": "",
                "ordem_execucao": "normal",
                "modo_execucao": "execucao_completa",
                "quantidade_ciclos": 1,
                "total_falhas": len(registros),
                "registros": [registro.to_reprocessamento_dict() for registro in registros],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_janela_exibe_titulo_e_footer_institucional():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        assert janela.windowTitle() == "RPA REAJUSTE TABELAS VIGÊNCIA"

        titulo = janela.findChild(QLabel, "tituloPainel")
        assert titulo is not None
        assert titulo.text() == "RPA REAJUSTE TABELAS VIGÊNCIA"

        rodape_titulo = janela.findChild(QLabel, "rodapeTitulo")
        assert rodape_titulo is not None
        assert rodape_titulo.text() == "RPA REAJUSTE TABELAS VIGÊNCIA"

        desenvolvedor = janela.findChild(QLabel, "rodapeDesenvolvedor")
        assert desenvolvedor is not None
        assert "@valentelucass" in desenvolvedor.text()
        assert "linkedin.com/in/dev-lucasandrade" in desenvolvedor.text()

        suporte = janela.findChild(QLabel, "rodapeSuporte")
        assert suporte is not None
        assert "lucasmac.dev@gmail.com" in suporte.text()
    finally:
        janela.close()
        app.processEvents()


class _SinalFake:
    def __init__(self):
        self.callbacks = []

    def connect(self, _callback):
        self.callbacks.append(_callback)
        return None

    def emit(self, *args, **kwargs):
        for callback in list(self.callbacks):
            callback(*args, **kwargs)


class _WorkerFake:
    def __init__(self, *args, **kwargs):
        self.sinal_total_fase_um = _SinalFake()
        self.sinal_total_fase_dois = _SinalFake()
        self.sinal_processando = _SinalFake()
        self.sinal_sucesso = _SinalFake()
        self.sinal_falha = _SinalFake()
        self.sinal_sistema = _SinalFake()
        self.sinal_concluido = _SinalFake()
        self.sinal_parado = _SinalFake()
        self.sinal_erro_critico = _SinalFake()
        self.finished = _SinalFake()
        self._running = False
        self.parada_solicitada = False

    def start(self):
        self._running = True
        return None

    def isRunning(self):
        return self._running

    def solicitar_parada(self):
        self.parada_solicitada = True

    def deleteLater(self):
        return None


class _WorkerAutoDeleteFake(_WorkerFake):
    last_init_kwargs = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _WorkerAutoDeleteFake.last_init_kwargs = {
            "args": args,
            "kwargs": kwargs,
        }


def test_janela_nao_limpa_logs_ao_iniciar_nova_execucao(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        monkeypatch.setattr("src.ui.ui_main.TrabalhadorExecucaoRpa", _WorkerFake)
        arquivo = tmp_path / "teste.xlsx"
        arquivo.write_text("ok", encoding="utf-8")
        janela._caminho_excel = arquivo

        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(fase=1, indice=1, nome_tabela="Tabela X", status="Sucesso")
        )

        janela._iniciar_automacao()

        assert janela._gerenciador_logs.total_registros == 1
        assert janela._execucao_ui_atual == 1
    finally:
        janela.close()
        app.processEvents()


def test_janela_inicia_auto_delete_com_worker_correto(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        arquivo = tmp_path / "auto_delete.xlsx"
        arquivo.write_text("ok", encoding="utf-8")
        janela._caminho_excel = arquivo
        janela._combo_auto_delete_ordem.setCurrentIndex(1)
        janela._combo_auto_delete_modo.setCurrentIndex(2)
        janela._input_auto_delete_ciclos.setText("5")
        monkeypatch.setattr("src.ui.ui_main.TrabalhadorAutoDeleteClientes", _WorkerAutoDeleteFake)

        janela._iniciar_auto_delete_clientes()

        assert janela._processo_ativo == "auto_delete_clientes"
        assert janela._botao_parar.isEnabled() is True
        assert janela._cartao_total_f1._rotulo_titulo.text() == "TOTAL AUTO DELETE"
        assert janela._cartao_sucesso_f1._rotulo_titulo.text() == "SUCESSO AUTO DELETE"
        assert janela._cartao_total_f2.isHidden() is True
        assert _WorkerAutoDeleteFake.last_init_kwargs["kwargs"]["ordem_execucao"] == OrdemExecucaoAutoDelete.REVERSA
        assert _WorkerAutoDeleteFake.last_init_kwargs["kwargs"]["modo_execucao"] == ModoExecucaoAutoDelete.REPROCESSAR_TUDO
        assert _WorkerAutoDeleteFake.last_init_kwargs["kwargs"]["quantidade_ciclos"] == 5
    finally:
        janela.close()
        app.processEvents()


def test_janela_bloqueia_auto_delete_com_quantidade_ciclos_invalida(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        arquivo = tmp_path / "auto_delete.xlsx"
        arquivo.write_text("ok", encoding="utf-8")
        janela._caminho_excel = arquivo
        janela._input_auto_delete_ciclos.setText("0")
        monkeypatch.setattr("src.ui.ui_main.TrabalhadorAutoDeleteClientes", _WorkerAutoDeleteFake)
        _WorkerAutoDeleteFake.last_init_kwargs = None

        janela._iniciar_auto_delete_clientes()

        assert _WorkerAutoDeleteFake.last_init_kwargs is None
        assert "quantidade de ciclos valida" in janela._rotulo_detalhe_status.text()
        assert janela._etiqueta_status.text() == "Erro"
    finally:
        janela.close()
        app.processEvents()


def test_reprocessar_entrada_auto_delete_usa_payload_do_log(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        _configurar_persistencia_auto_delete(
            monkeypatch,
            tmp_path,
            registros=[
                RegistroAutoDelete(
                    linha_excel=4,
                    nome_cliente="Cliente X",
                    data_inicio="",
                    data_fim="",
                )
            ],
        )
        arquivo = tmp_path / "auto_delete_atual.xlsx"
        arquivo.write_text("ok", encoding="utf-8")
        janela._caminho_excel = arquivo
        monkeypatch.setattr("src.ui.ui_main.TrabalhadorAutoDeleteClientes", _WorkerAutoDeleteFake)
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=4,
                nome_tabela="Cliente X",
                status="Erro",
                processo="auto_delete_clientes",
                chave="exec1_auto_delete_clientes_f1_idx4_Cliente X",
                dados_reprocessamento={
                    "linha_excel": 4,
                    "nome_cliente": "Cliente X",
                },
            )
        )

        janela._reprocessar_entrada_log("exec1_auto_delete_clientes_f1_idx4_Cliente X")

        kwargs = _WorkerAutoDeleteFake.last_init_kwargs["kwargs"]
        assert kwargs["modo_execucao"] == ModoExecucaoAutoDelete.REPROCESSAMENTO_INDIVIDUAL
        assert kwargs["quantidade_ciclos"] == 1
        assert kwargs["registro_individual"].nome_cliente == "Cliente X"
    finally:
        janela.close()
        app.processEvents()


def test_reprocessar_falhas_auto_delete_preserva_ciclos_configurados(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        arquivo = tmp_path / "auto_delete_atual.xlsx"
        arquivo.write_text("ok", encoding="utf-8")
        janela._caminho_excel = arquivo
        janela._input_auto_delete_ciclos.setText("4")
        indice_processo = janela._combo_filtro_processo.findData("auto_delete_clientes")
        janela._combo_filtro_processo.setCurrentIndex(indice_processo)
        monkeypatch.setattr("src.ui.ui_main.TrabalhadorAutoDeleteClientes", _WorkerAutoDeleteFake)

        janela._reprocessar_falhas()

        kwargs = _WorkerAutoDeleteFake.last_init_kwargs["kwargs"]
        assert kwargs["modo_execucao"] == ModoExecucaoAutoDelete.REPROCESSAR_FALHAS
        assert kwargs["quantidade_ciclos"] == 4
        assert janela._processo_ativo == "auto_delete_clientes"
    finally:
        janela.close()
        app.processEvents()


def test_tabela_logs_auto_delete_marca_falha_historica_sem_botao(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        _configurar_persistencia_auto_delete(monkeypatch, tmp_path, registros=[])
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=3,
                indice=4,
                nome_tabela="Cliente X",
                status="Erro",
                processo="auto_delete_clientes",
                chave="exec1_auto_delete_clientes_f3_idx4_Cliente X",
                dados_reprocessamento={
                    "linha_excel": 4,
                    "nome_cliente": "Cliente X",
                },
            )
        )

        janela._atualizar_tabela_logs()

        assert janela._tabela_logs.cellWidget(0, 5) is None
        assert janela._tabela_logs.item(0, 5).text() == "Historico"
    finally:
        janela.close()
        app.processEvents()


def test_tabela_logs_auto_delete_mantem_botao_quando_falha_esta_pendente(
    monkeypatch,
    tmp_path,
):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        _configurar_persistencia_auto_delete(
            monkeypatch,
            tmp_path,
            registros=[
                RegistroAutoDelete(
                    linha_excel=4,
                    nome_cliente="Cliente X",
                    data_inicio="",
                    data_fim="",
                )
            ],
        )
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=3,
                indice=4,
                nome_tabela="Cliente X",
                status="Erro",
                processo="auto_delete_clientes",
                chave="exec1_auto_delete_clientes_f3_idx4_Cliente X",
                dados_reprocessamento={
                    "linha_excel": 4,
                    "nome_cliente": "Cliente X",
                },
            )
        )

        janela._atualizar_tabela_logs()

        assert janela._tabela_logs.cellWidget(0, 5) is not None
    finally:
        janela.close()
        app.processEvents()


def test_reprocessar_entrada_auto_delete_historica_nao_inicia_worker(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        _configurar_persistencia_auto_delete(monkeypatch, tmp_path, registros=[])
        arquivo = tmp_path / "auto_delete_atual.xlsx"
        arquivo.write_text("ok", encoding="utf-8")
        janela._caminho_excel = arquivo
        monkeypatch.setattr("src.ui.ui_main.TrabalhadorAutoDeleteClientes", _WorkerAutoDeleteFake)
        _WorkerAutoDeleteFake.last_init_kwargs = None
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=3,
                indice=4,
                nome_tabela="Cliente X",
                status="Erro",
                processo="auto_delete_clientes",
                chave="exec1_auto_delete_clientes_f3_idx4_Cliente X",
                dados_reprocessamento={
                    "linha_excel": 4,
                    "nome_cliente": "Cliente X",
                },
            )
        )

        janela._reprocessar_entrada_log("exec1_auto_delete_clientes_f3_idx4_Cliente X")

        assert _WorkerAutoDeleteFake.last_init_kwargs is None
        assert "historico" in janela._rotulo_detalhe_status.text().lower()
    finally:
        janela.close()
        app.processEvents()


def test_janela_preserva_logs_de_ciclos_diferentes_no_auto_delete():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        janela._execucao_ui_atual = 3
        contexto_ciclo_1 = ContextoTabelaProcessamento(
            fase=1,
            indice=4,
            nome_tabela="Cliente XPTO",
            dados_extras={
                "processo": "auto_delete_clientes",
                "ciclo_execucao": 1,
                "total_ciclos_execucao": 2,
            },
        )
        contexto_ciclo_2 = ContextoTabelaProcessamento(
            fase=1,
            indice=4,
            nome_tabela="Cliente XPTO",
            dados_extras={
                "processo": "auto_delete_clientes",
                "ciclo_execucao": 2,
                "total_ciclos_execucao": 2,
            },
        )

        janela._ao_sucesso(contexto_ciclo_1, "Cliente excluido com sucesso")
        janela._ao_sucesso(contexto_ciclo_2, "Cliente excluido com sucesso")

        assert janela._gerenciador_logs.total_registros == 2
        for entrada in janela._gerenciador_logs.pagina_atual():
            assert entrada.fase_execucao == "auto_delete"
            assert entrada.status_fase_1 == "nao_aplicavel"
    finally:
        janela.close()
        app.processEvents()


def test_janela_preserva_logs_de_execucoes_diferentes_da_mesma_tabela():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        contexto = ContextoTabelaProcessamento(
            fase=2,
            indice=1,
            nome_tabela="Tabela XPTO",
        )

        janela._execucao_ui_atual = 1
        janela._ao_sucesso(contexto, "Execucao 1")

        janela._execucao_ui_atual = 2
        janela._ao_sucesso(contexto, "Execucao 2")

        assert janela._gerenciador_logs.total_registros == 2
    finally:
        janela.close()
        app.processEvents()


def test_log_de_validacao_fase2_nao_incrementa_contadores_de_processamento():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        contexto = ContextoTabelaProcessamento(
            fase=2,
            indice=4,
            nome_tabela="Tabela Validada",
            dados_extras={
                "tipo_registro": "validacao",
                "fase_execucao_ui": "validacao_fase_2",
                "contabilizar_progresso": False,
                "decisao_elegibilidade": "elegivel",
                "motivo_decisao": "Item confirmado no site",
                "status_site": "pronto_para_fase_2",
                "status_ui": "Validado",
            },
        )

        janela._ao_sucesso(contexto, "Elegivel na validacao do site")

        entrada = janela._gerenciador_logs.pagina_atual()[0]
        assert entrada.tipo_registro == "validacao"
        assert entrada.fase_execucao == "validacao_fase_2"
        assert entrada.status == "Validado"
        assert janela._sucessos_fase_dois == 0
        assert janela._processados_fase_dois == 0
    finally:
        janela.close()
        app.processEvents()


def test_tooltip_de_validacao_exibe_status_site_e_decisao():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=2,
                indice=8,
                nome_tabela="Tabela Divergente",
                status="Alerta",
                detalhe="Vigencia divergente no site",
                fase_execucao="validacao_fase_2",
                tipo_registro="validacao",
                decisao_elegibilidade="vigencia_divergente",
                motivo_decisao="Esperado 01/04/2026 - 31/03/2027",
                status_site="vigencia_divergente",
                janela_validacao="amostra_inicial",
                origem_decisao="site",
                amostrado=True,
            )
        )

        janela._atualizar_tabela_logs()

        item = janela._tabela_logs.item(0, 3)
        assert item is not None
        tooltip = item.toolTip()
        assert "Decisao elegibilidade: Vigencia Divergente" in tooltip
        assert "Status site: vigencia_divergente" in tooltip
    finally:
        janela.close()
        app.processEvents()


def test_parar_automacao_marca_status_como_parando():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        worker = _WorkerFake()
        worker._running = True
        janela._worker = worker

        janela._parar_automacao()

        assert worker.parada_solicitada is True
        assert janela._etiqueta_status.text() == "Parando"
        assert "Parada solicitada" in janela._rotulo_detalhe_status.text()
    finally:
        janela.close()
        app.processEvents()


def test_ao_parado_marca_logs_processando_como_interrompidos():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        janela._execucao_ui_atual = 7
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=2,
                nome_tabela="Tabela X",
                status="Processando",
                chave="exec7_f1_idx2_Tabela X",
            )
        )

        janela._ao_parado("Execução interrompida pelo operador.")

        entrada = janela._gerenciador_logs.buscar_entrada_reprocessavel(
            "Tabela X",
            fase=1,
        )
        assert entrada is not None
        assert entrada.status == "Interrompido"
        assert janela._etiqueta_status.text() == "Parado"
        assert janela._tabela_logs.cellWidget(0, 5) is not None
    finally:
        janela.close()
        app.processEvents()


def test_ao_worker_principal_finalizado_libera_interface():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        janela._worker = _WorkerFake()
        janela._botao_iniciar.setEnabled(False)
        janela._botao_parar.setEnabled(True)

        janela._ao_worker_principal_finalizado()

        assert janela._worker is None
        assert janela._botao_iniciar.isEnabled() is True
        assert janela._botao_parar.isEnabled() is False
    finally:
        janela.close()
        app.processEvents()


def test_resetar_contadores_reseta_minicards_e_rotulo_progresso():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        janela._mini_sucesso_f1._rotulo_valor.setText("7")
        janela._mini_falha_f1._rotulo_valor.setText("3")
        janela._mini_sucesso_f2._rotulo_valor.setText("5")
        janela._mini_falha_f2._rotulo_valor.setText("2")
        janela._rotulo_progresso.setText("Fase 1: 3/10 | Fase 2: 2/8")

        janela._resetar_contadores()

        assert janela._mini_sucesso_f1._rotulo_valor.text() == "0"
        assert janela._mini_falha_f1._rotulo_valor.text() == "0"
        assert janela._mini_sucesso_f2._rotulo_valor.text() == "0"
        assert janela._mini_falha_f2._rotulo_valor.text() == "0"
        assert janela._rotulo_progresso.text() == "Aguardando início..."
    finally:
        janela.close()
        app.processEvents()


def test_exportar_falhas_grava_json_escolhido(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        destino = tmp_path / "falhas_ui.json"
        monkeypatch.setattr(
            "src.ui.ui_main.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (str(destino), "Arquivos JSON (*.json)"),
        )
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="Tabela Erro",
                status="Erro",
                detalhe="Falha de teste",
            )
        )

        janela._exportar_falhas()

        assert destino.exists() is True
        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert dados[0]["nome_tabela"] == "Tabela Erro"
        assert dados[0]["status"] == "erro"
        assert "Exportadas 1 falha(s)" in janela._rotulo_detalhe_status.text()
    finally:
        janela.close()
        app.processEvents()


def test_exportar_falhas_sugere_downloads_por_padrao(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        capturado = {}
        destino = tmp_path / "saida.json"

        def _fake_save_file_name(*args, **kwargs):
            capturado["args"] = args
            return str(destino), "Arquivos JSON (*.json)"

        monkeypatch.setattr(
            "src.ui.ui_main.QFileDialog.getSaveFileName",
            _fake_save_file_name,
        )
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(fase=1, indice=1, nome_tabela="Tabela Erro", status="Erro")
        )

        janela._exportar_falhas()

        caminho_sugerido = Path(capturado["args"][2])
        assert caminho_sugerido.parent == Path.home() / "Downloads"
        assert caminho_sugerido.name.startswith("falhas_reprocessar_")
        assert caminho_sugerido.suffix == ".json"
    finally:
        janela.close()
        app.processEvents()


def test_exportar_falhas_inclui_item_interrompido(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        destino = tmp_path / "falhas_interrompidas.json"
        monkeypatch.setattr(
            "src.ui.ui_main.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (str(destino), "Arquivos JSON (*.json)"),
        )
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=2,
                indice=2,
                nome_tabela="Tabela Interrompida",
                status="Interrompido",
                detalhe="Execução interrompida pelo operador.",
            )
        )

        janela._exportar_falhas()

        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert dados[0]["status"] == "interrompido"
        assert dados[0]["nome_tabela"] == "Tabela Interrompida"
    finally:
        janela.close()
        app.processEvents()


def test_exportar_falhas_respeita_filtros_atuais(monkeypatch, tmp_path):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        destino = tmp_path / "falhas_filtradas.json"
        monkeypatch.setattr(
            "src.ui.ui_main.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (str(destino), "Arquivos JSON (*.json)"),
        )
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="Tabela F1",
                status="Erro",
                fase_execucao="fase_1",
            )
        )
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=2,
                indice=2,
                nome_tabela="Tabela F2",
                status="Interrompido",
                fase_execucao="fase_2",
            )
        )
        janela._status_filtro_logs = None
        janela._combo_filtro_fase.setCurrentIndex(2)
        janela._combo_filtro_reprocessamento.setCurrentIndex(1)

        janela._exportar_falhas()

        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert len(dados) == 1
        assert dados[0]["nome_tabela"] == "Tabela F2"
    finally:
        janela.close()
        app.processEvents()


def test_exportar_falhas_informa_cancelamento(monkeypatch):
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        monkeypatch.setattr(
            "src.ui.ui_main.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: ("", ""),
        )
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(fase=1, indice=1, nome_tabela="Tabela Erro", status="Erro")
        )

        janela._exportar_falhas()

        assert janela._rotulo_detalhe_status.text() == "Exportação de falhas cancelada."
    finally:
        janela.close()
        app.processEvents()


def test_detalhe_truncado_tem_tooltip_completo():
    app = _app()
    janela = JanelaPainelAutomacao()

    try:
        detalhe = "Mensagem muito grande para tooltip completo do usuário"
        janela._gerenciador_logs.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="Tabela Tooltip",
                status="Erro",
                detalhe=detalhe,
            )
        )

        janela._atualizar_tabela_logs()

        item = janela._tabela_logs.item(0, 3)
        assert item is not None
        assert detalhe in item.toolTip()
        assert "F1:" in item.toolTip()
    finally:
        janela.close()
        app.processEvents()
