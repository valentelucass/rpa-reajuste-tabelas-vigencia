"""
Janela principal do painel operacional RPA Tabela Cliente Por Nome.
Arquitetura: QMainWindow com QScrollArea, montada por seções independentes.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.aplicacao.modo_execucao import ModoExecucao
from src.auto_delete_clientes import (
    ModoExecucaoAutoDelete,
    OrdemExecucaoAutoDelete,
    RegistroAutoDelete,
)
from src.auto_delete_clientes.persistencia import RepositorioAutoDeleteClientes

from src.monitoramento.observador_execucao import ContextoTabelaProcessamento
from src.ui.componentes import (
    ICONES_TIPO_ERRO,
    MAPA_CORES_TIPO_ERRO,
    PALETA_CORES,
    CartaoEstatistica,
    EtiquetaStatus,
)
from src.ui.logger_ui import EntradaLog, GerenciadorLogsUi
from src.infraestrutura.caminhos import PUBLIC_DIR
from src.ui.worker import (
    TrabalhadorAutoDeleteClientes,
    TrabalhadorExecucaoRpa,
    TrabalhadorReprocessamento,
    TrabalhadorReprocessamentoFalhas,
)


# ---------------------------------------------------------------------------
# Constantes de layout da tabela de logs
# ---------------------------------------------------------------------------

LINHAS_LOGS_POR_PAGINA = 8
ALTURA_LINHA_LOG = 60
ALTURA_CABECALHO_TABELA_LOG = 44
LARGURA_COLUNA_FASE = 70
LARGURA_COLUNA_NOME = 240
LARGURA_COLUNA_STATUS = 146
LARGURA_COLUNA_HORARIO = 90
LARGURA_COLUNA_ACAO = 136
PROCESSO_PRINCIPAL = "reajuste_tabelas"
PROCESSO_AUTO_DELETE = "auto_delete_clientes"
FASE_EXECUCAO_AUTO_DELETE = "auto_delete"


class JanelaPainelAutomacao(QMainWindow):
    """Painel operacional principal da automação de tabelas por nome."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RPA REAJUSTE TABELAS VIGÊNCIA")
        self.resize(1450, 960)
        self.setMinimumSize(1240, 820)

        # Estado
        self._worker: Optional[TrabalhadorExecucaoRpa] = None
        self._worker_auto_delete: Optional[TrabalhadorAutoDeleteClientes] = None
        self._worker_reprocessamento: Optional[TrabalhadorReprocessamento] = None
        self._worker_reprocessamento_falhas: Optional[TrabalhadorReprocessamentoFalhas] = None
        self._gerenciador_logs = GerenciadorLogsUi(LINHAS_LOGS_POR_PAGINA)
        self._status_filtro_logs: Optional[str] = None
        self._execucao_ui_atual: int = 0
        self._processo_ativo: Optional[str] = None
        self._total_fase_um = 0
        self._total_fase_dois = 0
        self._processados_fase_um = 0
        self._processados_fase_dois = 0
        self._sucessos_fase_um = 0
        self._falhas_fase_um = 0
        self._sucessos_fase_dois = 0
        self._falhas_fase_dois = 0
        self._caminho_excel: Optional[Path] = None

        self._aplicar_estilo_global()
        self._montar_interface()

    # ------------------------------------------------------------------
    # Estilo global QSS
    # ------------------------------------------------------------------

    def _aplicar_estilo_global(self) -> None:
        p = PALETA_CORES
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {p['fundo']};
            }}
            QWidget#widgetCentral {{
                background: {p['fundo']};
            }}
            QScrollArea#scrollPrincipal {{
                background: {p['fundo']};
                border: none;
            }}
            QScrollArea#scrollPrincipal > QWidget > QWidget {{
                background: {p['fundo']};
            }}
            QFrame#cabecalhoPainel {{
                background: {p['branco']};
                border: 1px solid {p['borda']};
                border-radius: 24px;
            }}
            QFrame#cabecalhoStatus {{
                background: {p['superficie_secundaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 20px;
            }}
            QFrame#rodapePainel {{
                background: {p['superficie_secundaria']};
                border: 1px solid {p['borda']};
                border-radius: 18px;
            }}
            QLabel#etiquetaTopo {{
                background: #EAF2FC;
                color: {p['primaria']};
                border-radius: 11px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QLabel#logoFallback {{
                color: {p['primaria']};
                font-size: 24px;
                font-weight: 800;
            }}
            QLabel#tituloPainel {{
                color: {p['texto_padrao']};
                font-size: 28px;
                font-weight: 800;
            }}
            QLabel#subtituloPainel {{
                color: {p['texto_mutado']};
                font-size: 13px;
                font-weight: 400;
            }}
            QLabel#rodapeTitulo {{
                color: {p['texto_padrao']};
                font-size: 12px;
                font-weight: 800;
            }}
            QLabel#rodapeTexto, QLabel#rodapeSuporte, QLabel#rodapeDesenvolvedor {{
                color: {p['texto_mutado']};
                font-size: 12px;
            }}
            QLabel#rotuloPercentual {{
                color: {p['primaria']};
                font-size: 28px;
                font-weight: 800;
            }}
            QFrame#cartaoPadrao, QFrame#cartaoEstatistica,
            QFrame#resumoLogCard, QFrame#containerTabelaLogs {{
                background: {p['branco']};
                border: 1px solid {p['borda']};
                border-radius: 20px;
            }}
            QPushButton#botaoPrimario {{
                background: {p['primaria']};
                color: white;
                border: none;
                border-radius: 14px;
                padding: 13px 20px;
                font-weight: 700;
                min-width: 168px;
            }}
            QPushButton#botaoPrimario:hover   {{ background: #1A3970; }}
            QPushButton#botaoPrimario:pressed {{ background: #15315E; }}
            QPushButton#botaoPerigo {{
                background: white;
                color: {p['perigo']};
                border: 1px solid #E4BDB8;
                border-radius: 14px;
                padding: 13px 20px;
                font-weight: 700;
                min-width: 168px;
            }}
            QPushButton#botaoPerigo:hover {{ background: #FFF7F5; }}
            QPushButton#botaoSecundario {{
                background: white;
                color: {p['primaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 700;
                min-width: 148px;
            }}
            QPushButton#botaoSecundario:hover {{ background: #F8FBFF; }}
            QPushButton#botaoPaginacao {{
                background: white;
                color: {p['primaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 10px;
                min-width: 38px; max-width: 38px;
                min-height: 34px; max-height: 34px;
                font-weight: 800;
            }}
            QPushButton#botaoPaginacao:hover {{ background: #F8FBFF; }}
            QPushButton#botaoTabela {{
                background: #EFF5FD;
                color: {p['primaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 700;
            }}
            QPushButton#botaoTabela:hover    {{ background: #E4EEFA; }}
            QPushButton#botaoTabela:disabled {{
                background: #F1F5F9;
                color: {p['texto_sutil']};
                border-color: #E2E8F0;
            }}
            QPushButton:disabled {{
                background: #E2E8F0;
                color: {p['texto_sutil']};
                border-color: #E2E8F0;
            }}
            QLabel#rotuloPaginacaoLogs {{
                color: {p['texto_mutado']};
                font-size: 12px;
                font-weight: 600;
            }}
            QTableWidget#tabelaLogs {{
                background: white;
                border: none;
                outline: none;
                gridline-color: transparent;
                color: {p['texto_padrao']};
            }}
            QTableWidget#tabelaLogs::item {{
                border-bottom: 1px solid #E6EDF5;
                padding: 6px 8px;
            }}
            QTableWidget#tabelaLogs::item:selected {{
                background: #EEF4FB;
                color: {p['texto_padrao']};
            }}
            QHeaderView::section {{
                background: #F6F9FC;
                color: #52627A;
                border: none;
                border-bottom: 1px solid {p['borda']};
                padding: 12px 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QProgressBar#barraProgresso {{
                border: none;
                border-radius: 7px;
                background: #E2E8F0;
            }}
            QProgressBar#barraProgresso::chunk {{
                border-radius: 7px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p['primaria']},
                    stop:1 {p['secundaria']}
                );
            }}
            QLineEdit {{
                background-color: {p['branco']};
                border: 1px solid {p['borda']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                font-weight: 600;
                color: {p['texto_padrao']};
            }}
            QLineEdit:focus {{ border-color: {p['primaria']}; }}
            QComboBox#comboFiltroLogs {{
                background-color: {p['branco']};
                border: 1px solid {p['borda_forte']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                color: {p['texto_padrao']};
                min-width: 140px;
                outline: none;
            }}
            QComboBox#comboFiltroLogs:hover {{ border-color: #A0B3C6; }}
            QComboBox#comboFiltroLogs:focus {{ border-color: {p['primaria']}; }}
            QComboBox#comboFiltroLogs::drop-down {{
                border: none;
                padding-right: 12px;
            }}
            QComboBox#comboFiltroLogs QAbstractItemView {{
                background: {p['branco']};
                border: 1px solid {p['borda_forte']};
                border-radius: 0px;
                selection-background-color: #EEF4FB;
                selection-color: {p['primaria']};
                padding: 0px;
                margin: 0px;
                outline: none;
            }}
            QComboBox#comboFiltroLogs QAbstractItemView::item {{
                min-height: 32px;
                padding: 4px 12px;
                border-radius: 4px;
                background-color: transparent;
                color: {p['texto_padrao']};
            }}
            QComboBox#comboFiltroLogs QAbstractItemView::item:hover {{
                background-color: #F6F9FC;
                color: {p['primaria']};
            }}
            QComboBox#comboFiltroLogs QAbstractItemView::item:selected {{
                background-color: #EEF4FB;
                color: {p['primaria']};
                font-weight: 700;
            }}
            QScrollBar:vertical {{
                background: #EEF3F8;
                width: 14px;
                margin: 6px 2px 6px 2px;
                border: 1px solid #D9E4EF;
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical {{
                background: #8FA6BE;
                border: 1px solid #7D95AE;
                border-radius: 6px;
                min-height: 42px;
            }}
            QScrollBar::handle:vertical:hover   {{ background: #6F87A2; border-color: #617996; }}
            QScrollBar::handle:vertical:pressed {{ background: #5E7690; border-color: #516880; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent; border: none; height: 0px;
            }}
        """)

    # ------------------------------------------------------------------
    # Montagem da interface
    # ------------------------------------------------------------------

    def _montar_interface(self) -> None:
        scroll = QScrollArea()
        scroll.setObjectName("scrollPrincipal")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(scroll)

        widget_central = QWidget()
        widget_central.setObjectName("widgetCentral")
        scroll.setWidget(widget_central)

        self._layout_principal = QVBoxLayout(widget_central)
        self._layout_principal.setContentsMargins(30, 26, 30, 26)
        self._layout_principal.setSpacing(20)

        self._layout_principal.addWidget(self._criar_cabecalho())
        self._layout_principal.addWidget(self._criar_secao_controles())
        self._layout_principal.addLayout(self._criar_grade_estatisticas())
        self._layout_principal.addWidget(self._criar_secao_progresso())
        self._layout_principal.addWidget(self._criar_secao_logs(), stretch=1)
        self._layout_principal.addWidget(self._criar_rodape())

    # ------------------------------------------------------------------
    # Cabeçalho
    # ------------------------------------------------------------------

    def _criar_cabecalho(self) -> QFrame:
        cabecalho = QFrame()
        cabecalho.setObjectName("cabecalhoPainel")
        self._aplicar_sombra(cabecalho, blur=34, deslocamento_y=10)

        layout = QHBoxLayout(cabecalho)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)

        # Bloco de marca
        bloco_marca = QWidget()
        layout_marca = QHBoxLayout(bloco_marca)
        layout_marca.setContentsMargins(0, 0, 0, 0)
        layout_marca.setSpacing(18)

        # Logo
        rotulo_logo = self._obter_logo()
        layout_marca.addWidget(rotulo_logo, 0, Qt.AlignVCenter)

        # Divisor
        divisor = QFrame()
        divisor.setFixedWidth(1)
        divisor.setStyleSheet(f"background: {PALETA_CORES['borda_forte']};")
        divisor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout_marca.addWidget(divisor)

        # Bloco de título
        bloco_titulo = QVBoxLayout()
        bloco_titulo.setSpacing(6)

        etiqueta_topo = QLabel("PAINEL OPERACIONAL")
        etiqueta_topo.setObjectName("etiquetaTopo")
        etiqueta_topo.setAlignment(Qt.AlignLeft)

        titulo = QLabel("RPA REAJUSTE TABELAS VIGÊNCIA")
        titulo.setObjectName("tituloPainel")

        subtitulo = QLabel("Painel operacional para cópia, vigência e reajuste em lote no ESL Cloud")
        subtitulo.setObjectName("subtituloPainel")

        bloco_titulo.addWidget(etiqueta_topo, 0, Qt.AlignLeft)
        bloco_titulo.addWidget(titulo)
        bloco_titulo.addWidget(subtitulo)
        layout_marca.addLayout(bloco_titulo, 1)

        layout.addWidget(bloco_marca, 1)

        # Painel de status
        painel_status = self._criar_painel_status()
        layout.addWidget(painel_status, 0, Qt.AlignTop)

        return cabecalho

    def _obter_logo(self) -> QLabel:
        rotulo = QLabel()
        caminho_logo = PUBLIC_DIR / "logo.png"
        if caminho_logo.exists():
            pixmap = QPixmap(str(caminho_logo))
            rotulo.setPixmap(pixmap.scaledToHeight(48, Qt.SmoothTransformation))
        else:
            rotulo.setObjectName("logoFallback")
            rotulo.setText("Rodogarcia")
        return rotulo

    def _criar_painel_status(self) -> QFrame:
        painel = QFrame()
        painel.setObjectName("cabecalhoStatus")
        painel.setMinimumWidth(300)

        layout = QVBoxLayout(painel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        rotulo_titulo = QLabel("Status do robô")
        rotulo_titulo.setStyleSheet(
            f"color: {PALETA_CORES['texto_mutado']}; font-size: 12px; font-weight: 600;"
        )

        self._etiqueta_status = EtiquetaStatus("Parado")

        self._rotulo_detalhe_status = QLabel("Aguardando início")
        self._rotulo_detalhe_status.setStyleSheet(
            f"color: {PALETA_CORES['texto_padrao']}; font-size: 13px; font-weight: 600;"
        )
        self._rotulo_detalhe_status.setWordWrap(True)

        self._rotulo_horario = QLabel("")
        self._rotulo_horario.setStyleSheet(
            f"color: {PALETA_CORES['texto_mutado']}; font-size: 12px;"
        )

        layout.addWidget(rotulo_titulo)
        layout.addWidget(self._etiqueta_status, 0, Qt.AlignLeft)
        layout.addWidget(self._rotulo_detalhe_status)
        layout.addWidget(self._rotulo_horario)

        return painel

    # ------------------------------------------------------------------
    # Seção de controles
    # ------------------------------------------------------------------

    def _criar_secao_controles(self) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("cartaoPadrao")
        self._aplicar_sombra(cartao)

        # Layout principal em VStack
        layout_principal = QVBoxLayout(cartao)
        layout_principal.setContentsMargins(22, 20, 22, 20)
        layout_principal.setSpacing(20)

        # Cabeçalho (Título e Descrição)
        cabecalho = QVBoxLayout()
        cabecalho.setSpacing(6)
        titulo_ctrl = QLabel("Controles de Execução")
        titulo_ctrl.setStyleSheet(
            f"color: {PALETA_CORES['texto_padrao']}; font-size: 18px; font-weight: 700;"
        )
        texto_ctrl = QLabel(
            "Selecione o arquivo Excel e execute o fluxo principal de reajuste "
            "ou o módulo independente de auto delete clientes."
        )
        texto_ctrl.setStyleSheet(
            f"color: {PALETA_CORES['texto_mutado']}; font-size: 13px;"
        )
        texto_ctrl.setWordWrap(True)
        cabecalho.addWidget(titulo_ctrl)
        cabecalho.addWidget(texto_ctrl)
        
        layout_principal.addLayout(cabecalho)

        # Corpo (Conteiner 3 Blocos: Config -> Divisor -> Ações)
        corpo = QHBoxLayout()
        corpo.setSpacing(32)

        # --- Bloco Esquerda (Configuração) ---
        bloco_config = QVBoxLayout()
        bloco_config.setSpacing(20)

        # Modo de Execução (Radio buttons)
        bloco_modo = QVBoxLayout()
        bloco_modo.setSpacing(8)
        rotulo_modo = QLabel("Modo de execução:")
        rotulo_modo.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")
        
        radios_layout = QHBoxLayout()
        radios_layout.setSpacing(16)
        
        self._radio_completo = QRadioButton("Completo (Fase 1 + 2)")
        self._radio_completo.setChecked(True)
        self._radio_fase1 = QRadioButton("Apenas Fase 1")
        self._radio_fase2 = QRadioButton("Apenas Fase 2")
        
        radio_style = f"""
            QRadioButton {{ color: {PALETA_CORES['texto_padrao']}; font-size: 13px; font-weight: 500; outline: none; }}
            QRadioButton::indicator {{ width: 12px; height: 12px; border-radius: 8px; border: 2px solid {PALETA_CORES['borda_forte']}; background-color: white; }}
            QRadioButton::indicator:checked {{ width: 6px; height: 6px; border-radius: 8px; border: 5px solid {PALETA_CORES['primaria']}; background-color: white; }}
        """
        self._radio_completo.setStyleSheet(radio_style)
        self._radio_fase1.setStyleSheet(radio_style)
        self._radio_fase2.setStyleSheet(radio_style)
        
        radios_layout.addWidget(self._radio_completo)
        radios_layout.addWidget(self._radio_fase1)
        radios_layout.addWidget(self._radio_fase2)
        radios_layout.addStretch()

        bloco_modo.addWidget(rotulo_modo)
        bloco_modo.addLayout(radios_layout)

        # Caminho do Excel
        bloco_arquivo = QVBoxLayout()
        bloco_arquivo.setSpacing(8)
        rotulo_arquivo = QLabel("Caminho do Excel:")
        rotulo_arquivo.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")
        
        bloco_arquivo_input = QHBoxLayout()
        bloco_arquivo_input.setSpacing(8)
        self._input_excel = QLineEdit()
        self._input_excel.setPlaceholderText("Caminho do arquivo Excel...")
        self._input_excel.setFixedHeight(38)
        self._input_excel.setMinimumWidth(300)
        self._input_excel.setReadOnly(True)

        botao_selecionar = QPushButton("Selecionar Excel")
        botao_selecionar.setObjectName("botaoSecundario")
        botao_selecionar.setFixedHeight(38)
        botao_selecionar.clicked.connect(self._selecionar_excel)

        bloco_arquivo_input.addWidget(self._input_excel, 1)
        bloco_arquivo_input.addWidget(botao_selecionar)
        
        bloco_arquivo.addWidget(rotulo_arquivo)
        bloco_arquivo.addLayout(bloco_arquivo_input)

        bloco_auto_delete = QVBoxLayout()
        bloco_auto_delete.setSpacing(8)
        rotulo_auto_delete = QLabel("Auto delete clientes:")
        rotulo_auto_delete.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")

        linha_auto_delete = QHBoxLayout()
        linha_auto_delete.setSpacing(8)

        self._combo_auto_delete_ordem = QComboBox()
        self._combo_auto_delete_ordem.setObjectName("comboFiltroLogs")
        self._combo_auto_delete_ordem.setView(QListView())
        self._combo_auto_delete_ordem.addItem(
            "Normal (de cima para baixo)",
            OrdemExecucaoAutoDelete.NORMAL.value,
        )
        self._combo_auto_delete_ordem.addItem(
            "Reversa (de baixo para cima)",
            OrdemExecucaoAutoDelete.REVERSA.value,
        )

        self._combo_auto_delete_modo = QComboBox()
        self._combo_auto_delete_modo.setObjectName("comboFiltroLogs")
        self._combo_auto_delete_modo.setView(QListView())
        self._combo_auto_delete_modo.addItem(
            "Execução completa",
            ModoExecucaoAutoDelete.EXECUCAO_COMPLETA.value,
        )
        self._combo_auto_delete_modo.addItem(
            "Reprocessar apenas falhas",
            ModoExecucaoAutoDelete.REPROCESSAR_FALHAS.value,
        )
        self._combo_auto_delete_modo.addItem(
            "Reprocessar tudo",
            ModoExecucaoAutoDelete.REPROCESSAR_TUDO.value,
        )

        self._input_auto_delete_ciclos = QLineEdit()
        self._input_auto_delete_ciclos.setPlaceholderText("Ciclos")
        self._input_auto_delete_ciclos.setText("1")
        self._input_auto_delete_ciclos.setFixedHeight(38)
        self._input_auto_delete_ciclos.setMaximumWidth(110)
        self._input_auto_delete_ciclos.setToolTip(
            "Quantidade de ciclos completos para repetir o auto delete."
        )
        rotulo_ciclos = QLabel("Ciclos:")
        rotulo_ciclos.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")

        linha_auto_delete.addWidget(self._combo_auto_delete_ordem, 1)
        linha_auto_delete.addWidget(self._combo_auto_delete_modo, 1)
        linha_auto_delete.addWidget(rotulo_ciclos, 0)
        linha_auto_delete.addWidget(self._input_auto_delete_ciclos, 0)

        bloco_auto_delete.addWidget(rotulo_auto_delete)
        bloco_auto_delete.addLayout(linha_auto_delete)

        bloco_config.addLayout(bloco_modo)
        bloco_config.addLayout(bloco_arquivo)
        bloco_config.addLayout(bloco_auto_delete)
        bloco_config.addStretch()
        
        corpo.addLayout(bloco_config, 1) # stretch 1

        # --- Divisor Vertical ---
        divisor = QFrame()
        divisor.setFrameShape(QFrame.VLine)
        divisor.setStyleSheet(f"color: {PALETA_CORES['borda_forte']}; background-color: {PALETA_CORES['borda_forte']};")
        divisor.setFixedWidth(1)
        corpo.addWidget(divisor)

        # --- Bloco Direita (Ações) ---
        bloco_acoes = QVBoxLayout()
        bloco_acoes.setSpacing(12)
        bloco_acoes.setAlignment(Qt.AlignCenter)

        self._botao_iniciar = QPushButton("Iniciar Automação")
        self._botao_iniciar.setObjectName("botaoPrimario")
        self._botao_iniciar.clicked.connect(self._iniciar_automacao)

        self._botao_auto_delete = QPushButton("Executar Auto Delete")
        self._botao_auto_delete.setObjectName("botaoSecundario")
        self._botao_auto_delete.clicked.connect(self._iniciar_auto_delete_clientes)

        self._botao_parar = QPushButton("Parar")
        self._botao_parar.setObjectName("botaoPerigo")
        self._botao_parar.clicked.connect(self._parar_automacao)
        self._botao_parar.setEnabled(False)

        bloco_acoes.addWidget(self._botao_iniciar)
        bloco_acoes.addWidget(self._botao_auto_delete)
        bloco_acoes.addWidget(self._botao_parar)
        
        bloco_acoes.addStretch() # maintain buttons grouped at center
        bloco_acoes.insertStretch(0)

        corpo.addLayout(bloco_acoes, 0) # stretch 0

        layout_principal.addLayout(corpo)

        return cartao

    # ------------------------------------------------------------------
    # Grade de estatísticas
    # ------------------------------------------------------------------

    def _criar_grade_estatisticas(self) -> QGridLayout:
        grade = QGridLayout()
        grade.setSpacing(18)

        self._cartao_total_f1 = CartaoEstatistica(
            "Total Fase 1", PALETA_CORES["primaria"], 0, "Cópias a criar"
        )
        self._cartao_sucesso_f1 = CartaoEstatistica(
            "Sucesso Fase 1", PALETA_CORES["sucesso"], 0, "Cópias criadas"
        )
        self._cartao_total_f2 = CartaoEstatistica(
            "Total Fase 2", PALETA_CORES["secundaria"], 0, "Reajustes a aplicar"
        )
        self._cartao_sucesso_f2 = CartaoEstatistica(
            "Sucesso Fase 2", PALETA_CORES["sucesso"], 0, "Reajustes aplicados"
        )

        for cartao in [
            self._cartao_total_f1, self._cartao_sucesso_f1,
            self._cartao_total_f2, self._cartao_sucesso_f2
        ]:
            self._aplicar_sombra(cartao)

        grade.addWidget(self._cartao_total_f1, 0, 0)
        grade.addWidget(self._cartao_sucesso_f1, 0, 1)
        grade.addWidget(self._cartao_total_f2, 0, 2)
        grade.addWidget(self._cartao_sucesso_f2, 0, 3)

        return grade

    # ------------------------------------------------------------------
    # Seção de progresso
    # ------------------------------------------------------------------

    def _criar_secao_progresso(self) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("cartaoPadrao")
        self._aplicar_sombra(cartao)

        layout = QVBoxLayout(cartao)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        topo = QHBoxLayout()
        topo.setSpacing(18)

        bloco_texto = QVBoxLayout()
        bloco_texto.setSpacing(6)

        titulo_prog = QLabel("Progresso da Execução")
        titulo_prog.setStyleSheet(
            f"color: {PALETA_CORES['texto_padrao']}; font-size: 18px; font-weight: 700;"
        )

        self._rotulo_progresso = QLabel("Aguardando início...")
        self._rotulo_progresso.setStyleSheet(
            f"color: {PALETA_CORES['texto_mutado']}; font-size: 13px;"
        )

        bloco_texto.addWidget(titulo_prog)
        bloco_texto.addWidget(self._rotulo_progresso)

        self._rotulo_percentual = QLabel("0%")
        self._rotulo_percentual.setObjectName("rotuloPercentual")

        topo.addLayout(bloco_texto, 1)
        topo.addWidget(self._rotulo_percentual, 0, Qt.AlignRight | Qt.AlignVCenter)

        self._barra_progresso = QProgressBar()
        self._barra_progresso.setObjectName("barraProgresso")
        self._barra_progresso.setFixedHeight(14)
        self._barra_progresso.setMinimum(0)
        self._barra_progresso.setMaximum(100)
        self._barra_progresso.setValue(0)
        self._barra_progresso.setTextVisible(False)

        layout.addLayout(topo)
        layout.addWidget(self._barra_progresso)

        return cartao

    # ------------------------------------------------------------------
    # Seção de logs
    # ------------------------------------------------------------------

    def _criar_secao_logs(self) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("cartaoPadrao")
        cartao.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._aplicar_sombra(cartao)

        layout = QVBoxLayout(cartao)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)

        # Cabeçalho dos logs
        cabecalho = QHBoxLayout()
        cabecalho.setSpacing(18)

        bloco_titulos = QVBoxLayout()
        bloco_titulos.setSpacing(6)

        titulo_logs = QLabel("Histórico de Execução")
        titulo_logs.setStyleSheet(
            f"color: {PALETA_CORES['texto_padrao']}; font-size: 18px; font-weight: 700;"
        )
        subtitulo_logs = QLabel("Registro em tempo real de cada tabela processada")
        subtitulo_logs.setStyleSheet(
            f"color: {PALETA_CORES['texto_mutado']}; font-size: 13px;"
        )

        bloco_titulos.addWidget(titulo_logs)
        bloco_titulos.addWidget(subtitulo_logs)
        cabecalho.addLayout(bloco_titulos, 1)

        # Mini-cards de resumo
        resumo = QHBoxLayout()
        resumo.setSpacing(12)

        self._mini_sucesso_f1 = self._criar_mini_card("Sucesso F1", "0", PALETA_CORES["sucesso"])
        self._mini_falha_f1 = self._criar_mini_card("Falha F1", "0", PALETA_CORES["perigo"])
        self._mini_sucesso_f2 = self._criar_mini_card("Sucesso F2", "0", PALETA_CORES["sucesso"])
        self._mini_falha_f2 = self._criar_mini_card("Falha F2", "0", PALETA_CORES["perigo"])

        for mini in [self._mini_sucesso_f1, self._mini_falha_f1,
                     self._mini_sucesso_f2, self._mini_falha_f2]:
            resumo.addWidget(mini)

        cabecalho.addLayout(resumo)
        layout.addLayout(cabecalho)

        # Barra de ações dos logs (filtros + reprocessamento + exportar)
        barra_acoes = QHBoxLayout()
        barra_acoes.setSpacing(10)

        self._botao_filtro_todos = QPushButton("Todos")
        self._botao_filtro_todos.setObjectName("botaoTabela")
        self._botao_filtro_todos.clicked.connect(lambda: self._aplicar_filtro_logs(None))

        self._botao_filtro_erros = QPushButton("Apenas Erros")
        self._botao_filtro_erros.setObjectName("botaoTabela")
        self._botao_filtro_erros.clicked.connect(lambda: self._aplicar_filtro_logs("Erro"))

        self._botao_filtro_sucesso = QPushButton("Apenas Sucesso")
        self._botao_filtro_sucesso.setObjectName("botaoTabela")
        self._botao_filtro_sucesso.clicked.connect(lambda: self._aplicar_filtro_logs("Sucesso"))

        self._combo_filtro_fase = QComboBox()
        self._combo_filtro_fase.setObjectName("comboFiltroLogs")
        self._combo_filtro_fase.setView(QListView())
        self._combo_filtro_fase.addItem("Todas as fases", None)
        self._combo_filtro_fase.addItem("Fase 1", "fase_1")
        self._combo_filtro_fase.addItem("Fase 2", "fase_2")
        self._combo_filtro_fase.addItem("Auto Delete", FASE_EXECUCAO_AUTO_DELETE)
        self._combo_filtro_fase.currentIndexChanged.connect(self._aplicar_filtros_logs_avancados)

        self._combo_filtro_tipo = QComboBox()
        self._combo_filtro_tipo.setObjectName("comboFiltroLogs")
        self._combo_filtro_tipo.setView(QListView())
        self._combo_filtro_tipo.addItem("Todos os tipos", None)
        self._combo_filtro_tipo.addItem("Processamento normal", "normal")
        self._combo_filtro_tipo.addItem("Reprocessamento", "reprocessamento")
        self._combo_filtro_tipo.currentIndexChanged.connect(self._aplicar_filtros_logs_avancados)

        self._combo_filtro_processo = QComboBox()
        self._combo_filtro_processo.setObjectName("comboFiltroLogs")
        self._combo_filtro_processo.setView(QListView())
        self._combo_filtro_processo.addItem("Todos os processos", None)
        self._combo_filtro_processo.addItem("Reajuste Tabelas", PROCESSO_PRINCIPAL)
        self._combo_filtro_processo.addItem("Auto Delete Clientes", PROCESSO_AUTO_DELETE)
        self._combo_filtro_processo.currentIndexChanged.connect(self._aplicar_filtros_logs_avancados)

        self._combo_filtro_reprocessamento = QComboBox()
        self._combo_filtro_reprocessamento.setObjectName("comboFiltroLogs")
        self._combo_filtro_reprocessamento.setView(QListView())
        self._combo_filtro_reprocessamento.addItem("Todos os registros", None)
        self._combo_filtro_reprocessamento.addItem("Apenas falhas (reprocessar)", "apenas_falhas")
        self._combo_filtro_reprocessamento.addItem("Reprocessados com sucesso", "reprocessados_sucesso")
        self._combo_filtro_reprocessamento.addItem("Reprocessados com erro", "reprocessados_erro")
        self._combo_filtro_reprocessamento.currentIndexChanged.connect(self._aplicar_filtros_logs_avancados)

        self._botao_reprocessar_falhas = QPushButton("Reprocessar Falhas")
        self._botao_reprocessar_falhas.setObjectName("botaoSecundario")
        self._botao_reprocessar_falhas.setFixedHeight(34)
        self._botao_reprocessar_falhas.clicked.connect(self._reprocessar_falhas)

        self._botao_exportar_falhas = QPushButton("Exportar Falhas")
        self._botao_exportar_falhas.setObjectName("botaoSecundario")
        self._botao_exportar_falhas.setFixedHeight(34)
        self._botao_exportar_falhas.clicked.connect(self._exportar_falhas)

        barra_acoes.addWidget(self._botao_filtro_todos)
        barra_acoes.addWidget(self._botao_filtro_erros)
        barra_acoes.addWidget(self._botao_filtro_sucesso)
        barra_acoes.addWidget(self._combo_filtro_fase)
        barra_acoes.addWidget(self._combo_filtro_tipo)
        barra_acoes.addWidget(self._combo_filtro_processo)
        barra_acoes.addWidget(self._combo_filtro_reprocessamento)
        barra_acoes.addStretch()
        barra_acoes.addWidget(self._botao_reprocessar_falhas)
        barra_acoes.addWidget(self._botao_exportar_falhas)
        layout.addLayout(barra_acoes)

        # Tabela de logs (6 colunas)
        container_tabela = QWidget()
        container_tabela.setObjectName("containerTabelaLogs")
        altura_tabela = ALTURA_CABECALHO_TABELA_LOG + (LINHAS_LOGS_POR_PAGINA * ALTURA_LINHA_LOG) + 4
        container_tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        container_tabela.setMinimumHeight(altura_tabela + 16)
        container_tabela.setMaximumHeight(altura_tabela + 16)

        layout_container = QVBoxLayout(container_tabela)
        layout_container.setContentsMargins(8, 8, 8, 8)

        self._tabela_logs = QTableWidget(0, 6)
        self._tabela_logs.setObjectName("tabelaLogs")
        self._tabela_logs.setHorizontalHeaderLabels([
            "Fase", "Tabela", "Status", "Detalhe / Motivo", "Horário", "Ação"
        ])
        self._tabela_logs.setShowGrid(False)
        self._tabela_logs.setAlternatingRowColors(False)
        self._tabela_logs.setSelectionMode(QAbstractItemView.NoSelection)
        self._tabela_logs.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabela_logs.setFocusPolicy(Qt.NoFocus)
        self._tabela_logs.setWordWrap(False)
        self._tabela_logs.setTextElideMode(Qt.ElideRight)
        self._tabela_logs.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tabela_logs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tabela_logs.verticalHeader().setVisible(False)
        self._tabela_logs.verticalHeader().setDefaultSectionSize(ALTURA_LINHA_LOG)
        self._tabela_logs.setFixedHeight(altura_tabela)
        self._tabela_logs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        cabecalho_tabela = self._tabela_logs.horizontalHeader()
        cabecalho_tabela.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cabecalho_tabela.setHighlightSections(False)
        cabecalho_tabela.setFixedHeight(ALTURA_CABECALHO_TABELA_LOG)
        cabecalho_tabela.setSectionResizeMode(0, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(1, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(2, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(3, QHeaderView.Stretch)
        cabecalho_tabela.setSectionResizeMode(4, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(5, QHeaderView.Fixed)
        self._tabela_logs.setColumnWidth(0, LARGURA_COLUNA_FASE)
        self._tabela_logs.setColumnWidth(1, LARGURA_COLUNA_NOME)
        self._tabela_logs.setColumnWidth(2, LARGURA_COLUNA_STATUS)
        self._tabela_logs.setColumnWidth(4, LARGURA_COLUNA_HORARIO)
        self._tabela_logs.setColumnWidth(5, LARGURA_COLUNA_ACAO)

        layout_container.addWidget(self._tabela_logs)
        layout.addWidget(container_tabela)

        # Paginação
        self._criar_paginacao(layout)

        return cartao

    def _criar_rodape(self) -> QFrame:
        rodape = QFrame()
        rodape.setObjectName("rodapePainel")

        layout = QHBoxLayout(rodape)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        bloco_contexto = QVBoxLayout()
        bloco_contexto.setSpacing(4)

        titulo = QLabel("RPA REAJUSTE TABELAS VIGÊNCIA")
        titulo.setObjectName("rodapeTitulo")

        descricao = QLabel("Automação desktop para cópia, vigência e reajuste de tabelas.")
        descricao.setObjectName("rodapeTexto")
        descricao.setWordWrap(True)

        bloco_contexto.addWidget(titulo)
        bloco_contexto.addWidget(descricao)

        bloco_contato = QVBoxLayout()
        bloco_contato.setSpacing(4)

        desenvolvedor = QLabel(
            "Desenvolvido por "
            "<a href=\"https://www.linkedin.com/in/dev-lucasandrade/\" "
            "style=\"color: #21478A; text-decoration: none; font-weight: 700;\">"
            "@valentelucass</a>"
        )
        desenvolvedor.setObjectName("rodapeDesenvolvedor")
        desenvolvedor.setOpenExternalLinks(True)
        desenvolvedor.setTextInteractionFlags(Qt.TextBrowserInteraction)
        desenvolvedor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        suporte = QLabel("Suporte: lucasmac.dev@gmail.com")
        suporte.setObjectName("rodapeSuporte")
        suporte.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        suporte.setTextInteractionFlags(Qt.TextSelectableByMouse)

        bloco_contato.addWidget(desenvolvedor, 0, Qt.AlignRight)
        bloco_contato.addWidget(suporte, 0, Qt.AlignRight)

        layout.addLayout(bloco_contexto, 1)
        layout.addLayout(bloco_contato, 0)

        return rodape

    def _criar_mini_card(self, titulo: str, valor: str, cor: str) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("resumoLogCard")
        cartao.setMinimumWidth(160)
        cartao.setMinimumHeight(80)

        layout = QVBoxLayout(cartao)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        rotulo_titulo = QLabel(titulo)
        rotulo_titulo.setStyleSheet(
            f"color: {PALETA_CORES['texto_mutado']}; font-size: 11px; font-weight: 700;"
        )

        rotulo_valor = QLabel(valor)
        rotulo_valor.setStyleSheet(
            f"color: {PALETA_CORES['texto_padrao']}; font-size: 20px; font-weight: 800;"
        )
        rotulo_valor.setMinimumHeight(30)
        rotulo_valor.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(rotulo_titulo)
        layout.addWidget(rotulo_valor)

        cartao._rotulo_titulo = rotulo_titulo
        cartao._rotulo_valor = rotulo_valor
        return cartao

    def _criar_paginacao(self, layout: QVBoxLayout) -> None:
        self._widget_paginacao = QWidget()
        pag_layout = QHBoxLayout(self._widget_paginacao)
        pag_layout.setContentsMargins(0, 0, 0, 0)
        pag_layout.setSpacing(10)
        pag_layout.addStretch()

        self._botao_pagina_anterior = QPushButton("‹")
        self._botao_pagina_anterior.setObjectName("botaoPaginacao")
        self._botao_pagina_anterior.clicked.connect(self._pagina_anterior_logs)

        self._rotulo_pagina = QLabel("Página 1 de 1")
        self._rotulo_pagina.setObjectName("rotuloPaginacaoLogs")

        self._botao_proxima_pagina = QPushButton("›")
        self._botao_proxima_pagina.setObjectName("botaoPaginacao")
        self._botao_proxima_pagina.clicked.connect(self._proxima_pagina_logs)

        pag_layout.addWidget(self._botao_pagina_anterior)
        pag_layout.addWidget(self._rotulo_pagina)
        pag_layout.addWidget(self._botao_proxima_pagina)

        self._widget_paginacao.setVisible(False)
        layout.addWidget(self._widget_paginacao, 0, Qt.AlignRight)

    # ------------------------------------------------------------------
    # Sombra
    # ------------------------------------------------------------------

    def _aplicar_sombra(self, widget: QWidget, blur: int = 24, deslocamento_y: int = 5) -> None:
        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(blur)
        sombra.setOffset(0, deslocamento_y)
        sombra.setColor(QColor(15, 23, 42, 24))
        widget.setGraphicsEffect(sombra)

    # ------------------------------------------------------------------
    # Ações dos controles
    # ------------------------------------------------------------------

    def _selecionar_excel(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo Excel",
            str(Path.home()),
            "Arquivos Excel (*.xlsx *.xls)"
        )
        if caminho:
            self._caminho_excel = Path(caminho)
            self._input_excel.setText(caminho)

    def _ha_execucao_principal_ativa(self) -> bool:
        return bool(self._worker and self._worker.isRunning())

    def _ha_execucao_auto_delete_ativa(self) -> bool:
        return bool(self._worker_auto_delete and self._worker_auto_delete.isRunning())

    def _ha_reprocessamento_principal_ativo(self) -> bool:
        return bool(
            (self._worker_reprocessamento and self._worker_reprocessamento.isRunning())
            or (
                self._worker_reprocessamento_falhas
                and self._worker_reprocessamento_falhas.isRunning()
            )
        )

    def _preparar_execucao_ui(self, processo: str, mensagem: str) -> None:
        self._execucao_ui_atual += 1
        self._processo_ativo = processo
        self._resetar_contadores()
        self._atualizar_tabela_logs()
        self._botao_iniciar.setEnabled(False)
        self._botao_auto_delete.setEnabled(False)
        self._botao_parar.setEnabled(True)
        self._etiqueta_status.atualizar("Executando")
        self._rotulo_detalhe_status.setText(mensagem)
        self._atualizar_horario()

    def _configurar_resumo_principal(self) -> None:
        self._cartao_total_f1.atualizar_titulo("Total Fase 1")
        self._cartao_total_f1.atualizar_detalhe("Copias a criar")
        self._cartao_sucesso_f1.atualizar_titulo("Sucesso Fase 1")
        self._cartao_sucesso_f1.atualizar_detalhe("Copias criadas")
        self._cartao_total_f2.atualizar_titulo("Total Fase 2")
        self._cartao_total_f2.atualizar_detalhe("Reajustes a aplicar")
        self._cartao_sucesso_f2.atualizar_titulo("Sucesso Fase 2")
        self._cartao_sucesso_f2.atualizar_detalhe("Reajustes aplicados")
        self._cartao_total_f2.setVisible(True)
        self._cartao_sucesso_f2.setVisible(True)

        self._mini_sucesso_f1._rotulo_titulo.setText("Sucesso F1")
        self._mini_falha_f1._rotulo_titulo.setText("Falha F1")
        self._mini_sucesso_f2._rotulo_titulo.setText("Sucesso F2")
        self._mini_falha_f2._rotulo_titulo.setText("Falha F2")
        self._mini_sucesso_f2.setVisible(True)
        self._mini_falha_f2.setVisible(True)

    def _configurar_resumo_auto_delete(self) -> None:
        self._cartao_total_f1.atualizar_titulo("Total Auto Delete")
        self._cartao_total_f1.atualizar_detalhe("Clientes a processar")
        self._cartao_sucesso_f1.atualizar_titulo("Sucesso Auto Delete")
        self._cartao_sucesso_f1.atualizar_detalhe("Clientes concluidos")
        self._cartao_total_f2.setVisible(False)
        self._cartao_sucesso_f2.setVisible(False)

        self._mini_sucesso_f1._rotulo_titulo.setText("Sucesso AD")
        self._mini_falha_f1._rotulo_titulo.setText("Falha AD")
        self._mini_sucesso_f2.setVisible(False)
        self._mini_falha_f2.setVisible(False)

    def _iniciar_automacao(self) -> None:
        if self._ha_execucao_principal_ativa() or self._ha_execucao_auto_delete_ativa():
            self._rotulo_detalhe_status.setText(
                "Ainda existe uma execução em andamento. Aguarde finalizar."
            )
            self._atualizar_horario()
            return
        if self._worker_reprocessamento and self._worker_reprocessamento.isRunning():
            self._rotulo_detalhe_status.setText(
                "Aguarde o reprocessamento individual atual terminar."
            )
            self._atualizar_horario()
            return
        if (
            self._worker_reprocessamento_falhas
            and self._worker_reprocessamento_falhas.isRunning()
        ):
            self._rotulo_detalhe_status.setText(
                "Aguarde o reprocessamento global atual terminar."
            )
            self._atualizar_horario()
            return
        if not self._caminho_excel or not self._caminho_excel.exists():
            self._rotulo_detalhe_status.setText("Selecione o arquivo Excel primeiro")
            self._etiqueta_status.atualizar("Erro")
            return

        self._preparar_execucao_ui(PROCESSO_PRINCIPAL, "Iniciando automação...")

        # Cria e conecta o worker
        if self._radio_fase1.isChecked():
            modo = ModoExecucao.MODO_FASE1
        elif self._radio_fase2.isChecked():
            modo = ModoExecucao.MODO_FASE2
        else:
            modo = ModoExecucao.MODO_COMPLETO

        self._worker = TrabalhadorExecucaoRpa(self._caminho_excel, modo=modo)
        self._worker.sinal_total_fase_um.connect(self._ao_definir_total_fase_um)
        self._worker.sinal_total_fase_dois.connect(self._ao_definir_total_fase_dois)
        self._worker.sinal_processando.connect(self._ao_processando)
        self._worker.sinal_sucesso.connect(self._ao_sucesso)
        self._worker.sinal_falha.connect(self._ao_falha)
        self._worker.sinal_sistema.connect(
            lambda mensagem: self._ao_sistema(mensagem, PROCESSO_PRINCIPAL)
        )
        self._worker.sinal_concluido.connect(self._ao_concluido)
        self._worker.sinal_parado.connect(self._ao_parado)
        self._worker.sinal_erro_critico.connect(self._ao_erro_critico)
        self._worker.finished.connect(self._ao_worker_principal_finalizado)
        self._worker.start()

    def _iniciar_auto_delete_clientes(self) -> None:
        if self._ha_execucao_principal_ativa() or self._ha_execucao_auto_delete_ativa():
            self._rotulo_detalhe_status.setText(
                "Ainda existe uma execução em andamento. Aguarde finalizar."
            )
            self._atualizar_horario()
            return
        if self._ha_reprocessamento_principal_ativo():
            self._rotulo_detalhe_status.setText(
                "Aguarde o reprocessamento atual terminar antes de iniciar o auto delete."
            )
            self._atualizar_horario()
            return

        modo_auto_delete = ModoExecucaoAutoDelete(
            self._combo_auto_delete_modo.currentData()
        )
        if not self._caminho_excel or not self._caminho_excel.exists():
            self._rotulo_detalhe_status.setText(
                "Selecione o arquivo Excel primeiro para executar o auto delete."
            )
            self._etiqueta_status.atualizar("Erro")
            self._atualizar_horario()
            return

        ordem_execucao = OrdemExecucaoAutoDelete(
            self._combo_auto_delete_ordem.currentData()
        )
        try:
            quantidade_ciclos = int((self._input_auto_delete_ciclos.text() or "1").strip())
        except ValueError:
            quantidade_ciclos = 0
        if quantidade_ciclos <= 0:
            self._rotulo_detalhe_status.setText(
                "Informe uma quantidade de ciclos valida para o auto delete."
            )
            self._etiqueta_status.atualizar("Erro")
            self._atualizar_horario()
            return
        self._preparar_execucao_ui(
            PROCESSO_AUTO_DELETE,
            "Iniciando auto delete clientes...",
        )

        self._worker_auto_delete = TrabalhadorAutoDeleteClientes(
            self._caminho_excel,
            ordem_execucao=ordem_execucao,
            modo_execucao=modo_auto_delete,
            quantidade_ciclos=quantidade_ciclos,
        )
        self._worker_auto_delete.sinal_total_fase_um.connect(self._ao_definir_total_fase_um)
        self._worker_auto_delete.sinal_total_fase_dois.connect(self._ao_definir_total_fase_dois)
        self._worker_auto_delete.sinal_processando.connect(self._ao_processando)
        self._worker_auto_delete.sinal_sucesso.connect(self._ao_sucesso)
        self._worker_auto_delete.sinal_falha.connect(self._ao_falha)
        self._worker_auto_delete.sinal_sistema.connect(
            lambda mensagem: self._ao_sistema(mensagem, PROCESSO_AUTO_DELETE)
        )
        self._worker_auto_delete.sinal_concluido.connect(self._ao_concluido)
        self._worker_auto_delete.sinal_parado.connect(self._ao_parado)
        self._worker_auto_delete.sinal_erro_critico.connect(self._ao_erro_critico)
        self._worker_auto_delete.finished.connect(self._ao_worker_auto_delete_finalizado)
        self._worker_auto_delete.start()

    def _parar_automacao(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.solicitar_parada()
            self._rotulo_detalhe_status.setText(
                "Parada solicitada. Encerrando execução atual..."
            )
            self._etiqueta_status.atualizar("Parando")
            self._botao_parar.setEnabled(False)
            self._atualizar_horario()
            return
        if self._worker_auto_delete and self._worker_auto_delete.isRunning():
            self._worker_auto_delete.solicitar_parada()
            self._rotulo_detalhe_status.setText(
                "Parada solicitada. Encerrando auto delete clientes..."
            )
            self._etiqueta_status.atualizar("Parando")
            self._botao_parar.setEnabled(False)
            self._atualizar_horario()

    def _resetar_contadores(self) -> None:
        self._total_fase_um = 0
        self._total_fase_dois = 0
        self._processados_fase_um = 0
        self._processados_fase_dois = 0
        self._sucessos_fase_um = 0
        self._falhas_fase_um = 0
        self._sucessos_fase_dois = 0
        self._falhas_fase_dois = 0
        if self._processo_ativo == PROCESSO_AUTO_DELETE:
            self._configurar_resumo_auto_delete()
        else:
            self._configurar_resumo_principal()
        self._cartao_total_f1.atualizar_valor(0)
        self._cartao_sucesso_f1.atualizar_valor(0)
        self._cartao_total_f2.atualizar_valor(0)
        self._cartao_sucesso_f2.atualizar_valor(0)
        self._mini_sucesso_f1._rotulo_valor.setText("0")
        self._mini_falha_f1._rotulo_valor.setText("0")
        self._mini_sucesso_f2._rotulo_valor.setText("0")
        self._mini_falha_f2._rotulo_valor.setText("0")
        self._barra_progresso.setValue(0)
        self._rotulo_percentual.setText("0%")
        self._rotulo_progresso.setText("Aguardando início...")

    # ------------------------------------------------------------------
    # Slots — sinais do worker
    # ------------------------------------------------------------------

    def _ao_definir_total_fase_um(self, total: int) -> None:
        self._total_fase_um = total
        self._cartao_total_f1.atualizar_valor(total)
        if self._processo_ativo == PROCESSO_AUTO_DELETE:
            self._rotulo_progresso.setText(f"Auto Delete: 0/{total} cliente(s)")
        else:
            self._rotulo_progresso.setText(f"Fase 1: {total} tabela(s) a copiar")

    def _ao_definir_total_fase_dois(self, total: int) -> None:
        self._total_fase_dois = total
        self._cartao_total_f2.atualizar_valor(total)

    def _ao_processando(self, contexto: ContextoTabelaProcessamento) -> None:
        extras = contexto.dados_extras
        processo = extras.get("processo", PROCESSO_PRINCIPAL)
        fase_execucao_log = self._fase_execucao_log(contexto, processo)
        status_fase_1, status_fase_2 = self._status_fases_log(contexto, processo)
        detalhe = self._formatar_detalhe_auto_delete(
            (
                "Auto delete em andamento..."
                if processo == PROCESSO_AUTO_DELETE
                else f"Fase {contexto.fase} em andamento..."
            ),
            extras,
        )
        entrada = EntradaLog(
            fase=contexto.fase,
            indice=contexto.indice,
            nome_tabela=contexto.nome_tabela,
            chave=self._chave_log_contexto(contexto),
            status="Processando",
            detalhe=detalhe,
            fase_execucao=fase_execucao_log,
            tipo_execucao=contexto.tipo_execucao.value,
            reprocessado=contexto.reprocessado,
            status_fase_1=status_fase_1,
            status_fase_2=status_fase_2,
            processo=processo,
            dados_reprocessamento=extras.get("reprocessamento_dados", {}),
        )
        self._gerenciador_logs.adicionar_ou_atualizar(entrada)
        self._atualizar_tabela_logs()
        if processo == PROCESSO_AUTO_DELETE:
            self._rotulo_detalhe_status.setText(
                self._formatar_detalhe_auto_delete(
                    f"[AUTO_DELETE_CLIENTES] {contexto.nome_tabela}",
                    extras,
                )
            )
        else:
            self._rotulo_detalhe_status.setText(f"[Fase {contexto.fase}] {contexto.nome_tabela}")
        self._atualizar_horario()
        self._etiqueta_status.atualizar("Processando")

    def _ao_sucesso(self, contexto: ContextoTabelaProcessamento, mensagem: str) -> None:
        extras = contexto.dados_extras
        processo = extras.get("processo", PROCESSO_PRINCIPAL)
        fase_execucao_log = self._fase_execucao_log(contexto, processo)
        status_fase_1, status_fase_2 = self._status_fases_log(contexto, processo)
        entrada = EntradaLog(
            fase=contexto.fase,
            indice=contexto.indice,
            nome_tabela=contexto.nome_tabela,
            chave=self._chave_log_contexto(contexto),
            status="Sucesso",
            detalhe=self._formatar_detalhe_auto_delete(
                mensagem or "Concluido com sucesso",
                extras,
            ),
            fase_execucao=fase_execucao_log,
            tipo_execucao=contexto.tipo_execucao.value,
            reprocessado=contexto.reprocessado,
            status_fase_1=status_fase_1,
            status_fase_2=status_fase_2,
            processo=processo,
            dados_reprocessamento=extras.get("reprocessamento_dados", {}),
        )
        self._gerenciador_logs.adicionar_ou_atualizar(entrada)

        if processo == PROCESSO_AUTO_DELETE or contexto.fase == 1:
            self._sucessos_fase_um += 1
            self._processados_fase_um += 1
            self._cartao_sucesso_f1.atualizar_valor(self._sucessos_fase_um)
            self._mini_sucesso_f1._rotulo_valor.setText(str(self._sucessos_fase_um))
        else:
            self._sucessos_fase_dois += 1
            self._processados_fase_dois += 1
            self._cartao_sucesso_f2.atualizar_valor(self._sucessos_fase_dois)
            self._mini_sucesso_f2._rotulo_valor.setText(str(self._sucessos_fase_dois))

        self._atualizar_progresso()
        self._atualizar_tabela_logs()

    def _ao_falha(self, contexto: ContextoTabelaProcessamento, mensagem: str) -> None:
        extras = contexto.dados_extras
        processo = extras.get("processo", PROCESSO_PRINCIPAL)
        fase_execucao_log = self._fase_execucao_log(contexto, processo)
        status_fase_1, status_fase_2 = self._status_fases_log(contexto, processo)
        tipo_erro = extras.get("tipo_erro", "")
        tipo_legivel = extras.get("tipo_erro_legivel", "")
        motivo = extras.get("motivo", mensagem[:200])
        acao = extras.get("acao_recomendada", "")
        screenshot = extras.get("screenshot", "")

        # Detalhe enriquecido: tipo + motivo
        if tipo_legivel:
            detalhe = f"[{tipo_legivel}] {motivo}"
        else:
            detalhe = mensagem[:200]
        detalhe = self._formatar_detalhe_auto_delete(detalhe, extras)

        entrada = EntradaLog(
            fase=contexto.fase,
            indice=contexto.indice,
            nome_tabela=contexto.nome_tabela,
            chave=self._chave_log_contexto(contexto),
            status="Erro",
            detalhe=detalhe,
            tipo_erro=tipo_erro,
            tipo_erro_legivel=tipo_legivel,
            motivo=motivo,
            acao_recomendada=acao,
            screenshot=screenshot,
            fase_execucao=fase_execucao_log,
            tipo_execucao=contexto.tipo_execucao.value,
            reprocessado=contexto.reprocessado,
            status_fase_1=status_fase_1,
            status_fase_2=status_fase_2,
            processo=processo,
            dados_reprocessamento=extras.get("reprocessamento_dados", {}),
        )
        self._gerenciador_logs.adicionar_ou_atualizar(entrada)

        if processo == PROCESSO_AUTO_DELETE or contexto.fase == 1:
            self._falhas_fase_um += 1
            self._processados_fase_um += 1
            if processo == PROCESSO_AUTO_DELETE:
                self._cartao_total_f2.atualizar_valor(self._falhas_fase_um)
            self._mini_falha_f1._rotulo_valor.setText(str(self._falhas_fase_um))
        else:
            self._falhas_fase_dois += 1
            self._processados_fase_dois += 1
            self._mini_falha_f2._rotulo_valor.setText(str(self._falhas_fase_dois))

        self._atualizar_progresso()
        self._atualizar_tabela_logs()

    def _ao_sistema(self, mensagem: str, processo: str = PROCESSO_PRINCIPAL) -> None:
        self._gerenciador_logs.adicionar_sistema(mensagem, processo=processo)
        self._atualizar_tabela_logs()
        self._rotulo_detalhe_status.setText(mensagem[:80])
        self._atualizar_horario()

    def _ao_concluido(self) -> None:
        self._etiqueta_status.atualizar("Sucesso")
        if self._processo_ativo == PROCESSO_AUTO_DELETE:
            self._rotulo_detalhe_status.setText("Auto delete clientes concluído com sucesso")
        else:
            self._rotulo_detalhe_status.setText("Automação concluída com sucesso")
        self._barra_progresso.setValue(100)
        self._rotulo_percentual.setText("100%")
        self._botao_parar.setEnabled(False)
        self._atualizar_horario()

    def _ao_parado(self, mensagem: str) -> None:
        self._gerenciador_logs.marcar_processando_como_interrompido(
            self._prefixo_logs_execucao_atual(),
            detalhe=mensagem,
        )
        self._atualizar_tabela_logs()
        self._etiqueta_status.atualizar("Parado")
        self._rotulo_detalhe_status.setText(mensagem[:80])
        self._botao_parar.setEnabled(False)
        self._atualizar_horario()

    def _ao_erro_critico(self, mensagem: str) -> None:
        self._etiqueta_status.atualizar("Erro")
        self._rotulo_detalhe_status.setText(f"Erro crítico: {mensagem[:80]}")
        self._botao_parar.setEnabled(False)
        self._atualizar_horario()

    def _ao_worker_principal_finalizado(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None
        self._botao_iniciar.setEnabled(True)
        self._botao_auto_delete.setEnabled(True)
        self._botao_parar.setEnabled(False)
        if not self._ha_execucao_auto_delete_ativa():
            self._processo_ativo = None

    def _ao_worker_auto_delete_finalizado(self) -> None:
        if self._worker_auto_delete is not None:
            self._worker_auto_delete.deleteLater()
        self._worker_auto_delete = None
        self._botao_iniciar.setEnabled(True)
        self._botao_auto_delete.setEnabled(True)
        self._botao_parar.setEnabled(False)
        if not self._ha_execucao_principal_ativa():
            self._processo_ativo = None

    def _ao_worker_reprocessamento_finalizado(self) -> None:
        if self._worker_reprocessamento is not None:
            self._worker_reprocessamento.deleteLater()
        self._worker_reprocessamento = None

    def _ao_worker_reprocessamento_falhas_finalizado(self) -> None:
        if self._worker_reprocessamento_falhas is not None:
            self._worker_reprocessamento_falhas.deleteLater()
        self._worker_reprocessamento_falhas = None

    # ------------------------------------------------------------------
    # Atualização da interface
    # ------------------------------------------------------------------

    def _atualizar_progresso(self) -> None:
        total = self._total_fase_um + self._total_fase_dois
        processados = self._processados_fase_um + self._processados_fase_dois
        if total > 0:
            pct = int((processados / total) * 100)
        else:
            pct = 0
        self._barra_progresso.setValue(pct)
        self._rotulo_percentual.setText(f"{pct}%")
        if self._processo_ativo == PROCESSO_AUTO_DELETE:
            self._rotulo_progresso.setText(
                f"Auto Delete: {self._processados_fase_um}/{self._total_fase_um} | "
                f"Falhas: {self._falhas_fase_um}"
            )
        else:
            self._rotulo_progresso.setText(
                f"Fase 1: {self._processados_fase_um}/{self._total_fase_um} | "
                f"Fase 2: {self._processados_fase_dois}/{self._total_fase_dois}"
            )

    def _atualizar_tabela_logs(self) -> None:
        registros = self._gerenciador_logs.pagina_atual()
        self._tabela_logs.setRowCount(len(registros))
        falhas_pendentes_auto_delete = self._obter_falhas_pendentes_auto_delete()

        fonte_mono = QFont("Consolas", 10)
        fonte_mono.setStyleHint(QFont.Monospace)

        for linha_idx, entrada in enumerate(registros):
            # Coluna Fase
            if entrada.processo == PROCESSO_AUTO_DELETE:
                texto_fase = "AutoDel" if entrada.fase > 0 else "Sistema"
            else:
                texto_fase = f"Fase {entrada.fase}" if entrada.fase > 0 else "Sistema"
            item_fase = QTableWidgetItem(texto_fase)
            item_fase.setForeground(QColor(PALETA_CORES["texto_mutado"]))
            item_fase.setFont(fonte_mono)
            item_fase.setToolTip(
                "Auto Delete Clientes"
                if entrada.processo == PROCESSO_AUTO_DELETE
                else "Reajuste de Tabelas"
            )
            self._tabela_logs.setItem(linha_idx, 0, item_fase)

            # Coluna Nome da tabela
            item_nome = QTableWidgetItem(entrada.nome_tabela)
            item_nome.setForeground(QColor(PALETA_CORES["texto_padrao"]))
            if entrada.indice > 0:
                tooltip_nome = [f"Linha Excel: {entrada.indice}", f"Nome: {entrada.nome_tabela}"]
                item_nome.setToolTip("\n".join(tooltip_nome))
            self._tabela_logs.setItem(linha_idx, 1, item_nome)

            # Coluna Status (com ícone de tipo de erro)
            texto_status = entrada.status
            if entrada.status == "Sucesso" and entrada.reprocessado:
                texto_status = "OK - REPROCESSADO"
            elif entrada.status == "Erro" and entrada.reprocessado:
                texto_status = "ERRO - REPROCESSADO"
            elif entrada.status == "Erro" and entrada.tipo_erro:
                icone = ICONES_TIPO_ERRO.get(entrada.tipo_erro, "")
                tipo_legivel = entrada.tipo_erro_legivel or entrada.tipo_erro
                texto_status = f"{icone} {tipo_legivel}" if icone else tipo_legivel
            cor_status = self._cor_para_status(entrada.status)
            item_status = QTableWidgetItem(texto_status)
            item_status.setForeground(QColor(cor_status))
            if entrada.tipo_erro:
                item_status.setToolTip(
                    f"Tipo: {entrada.tipo_erro_legivel or entrada.tipo_erro}\n"
                    f"Ação: {entrada.acao_recomendada}\n"
                    f"Tipo execução: {entrada.tipo_execucao}"
                )
            self._tabela_logs.setItem(linha_idx, 2, item_status)

            # Coluna Detalhe / Motivo
            item_detalhe = QTableWidgetItem(entrada.detalhe)
            item_detalhe.setForeground(QColor(PALETA_CORES["texto_padrao"]))
            tooltip_detalhe = [f"Detalhe: {entrada.detalhe or '-'}"]
            if entrada.motivo:
                tooltip_detalhe.append(f"Motivo: {entrada.motivo}")
            if entrada.acao_recomendada:
                tooltip_detalhe.append(f"Ação recomendada: {entrada.acao_recomendada}")
            tooltip_detalhe.append(f"Processo: {entrada.processo}")
            if entrada.processo == PROCESSO_AUTO_DELETE:
                tooltip_detalhe.append("Execucao: auto_delete")
            else:
                tooltip_detalhe.append(
                    f"F1: {entrada.status_fase_1} | F2: {entrada.status_fase_2}"
                )
            item_detalhe.setToolTip("\n".join(tooltip_detalhe))
            self._tabela_logs.setItem(linha_idx, 3, item_detalhe)

            # Coluna Horário
            item_horario = QTableWidgetItem(entrada.horario)
            item_horario.setForeground(QColor(PALETA_CORES["texto_mutado"]))
            item_horario.setFont(fonte_mono)
            self._tabela_logs.setItem(linha_idx, 4, item_horario)

            # Coluna Ação (botão para falhas ou itens interrompidos)
            auto_delete_pendente = self._entrada_auto_delete_pendente(
                entrada,
                falhas_pendentes_auto_delete,
            )
            if entrada.status in {"Erro", "Interrompido"} and entrada.nome_tabela != "Sistema":
                if entrada.processo == PROCESSO_AUTO_DELETE and not auto_delete_pendente:
                    self._tabela_logs.setCellWidget(linha_idx, 5, None)
                    item_historico = QTableWidgetItem("Historico")
                    item_historico.setForeground(QColor(PALETA_CORES["texto_mutado"]))
                    item_historico.setToolTip(
                        "Falha mantida apenas no historico. "
                        "Ela nao esta mais pendente no auto delete."
                    )
                    self._tabela_logs.setItem(linha_idx, 5, item_historico)
                else:
                    botao_reprocessar = QPushButton("Reprocessar")
                    botao_reprocessar.setObjectName("botaoTabela")
                    botao_reprocessar.setFixedHeight(32)
                    botao_reprocessar.setToolTip(
                        f"Reprocessar '{entrada.nome_tabela}'"
                    )
                    botao_reprocessar.clicked.connect(
                        lambda checked=False, c=entrada.chave: self._reprocessar_entrada_log(c)
                    )
                    self._tabela_logs.setCellWidget(linha_idx, 5, botao_reprocessar)
            else:
                self._tabela_logs.setCellWidget(linha_idx, 5, None)
                item_vazio = QTableWidgetItem("")
                self._tabela_logs.setItem(linha_idx, 5, item_vazio)

        # Paginação
        total_pag = self._gerenciador_logs.total_paginas()
        mostrar_pag = total_pag > 1
        self._widget_paginacao.setVisible(mostrar_pag)
        if mostrar_pag:
            self._rotulo_pagina.setText(
                f"Página {self._gerenciador_logs.numero_pagina} de {total_pag}"
            )

    def _cor_para_status(self, status: str) -> str:
        mapa = {
            "Sucesso": PALETA_CORES["sucesso"],
            "Erro": PALETA_CORES["perigo"],
            "Processando": PALETA_CORES["secundaria"],
            "Interrompido": PALETA_CORES["perigo"],
            "Parando": PALETA_CORES["perigo"],
            "Sistema": PALETA_CORES["texto_mutado"],
        }
        return mapa.get(status, PALETA_CORES["texto_padrao"])

    def _atualizar_horario(self) -> None:
        self._rotulo_horario.setText(
            f"Atualizado: {datetime.now().strftime('%H:%M:%S')}"
        )

    def _chave_log_contexto(self, contexto: ContextoTabelaProcessamento) -> str:
        processo = contexto.dados_extras.get("processo", PROCESSO_PRINCIPAL)
        sufixo_ciclo = self._sufixo_ciclo_contexto(contexto.dados_extras)
        return (
            f"exec{self._execucao_ui_atual}_"
            f"{processo}_"
            f"{sufixo_ciclo}"
            f"f{contexto.fase}_"
            f"idx{contexto.indice}_"
            f"{contexto.nome_tabela}"
        )

    @staticmethod
    def _sufixo_ciclo_contexto(dados_extras: dict) -> str:
        try:
            ciclo = int(dados_extras.get("ciclo_execucao") or 0)
            total_ciclos = int(dados_extras.get("total_ciclos_execucao") or 0)
        except (TypeError, ValueError):
            return ""
        if ciclo > 0 and total_ciclos > 1:
            return f"c{ciclo}de{total_ciclos}_"
        return ""

    def _fase_execucao_log(
        self,
        contexto: ContextoTabelaProcessamento,
        processo: str,
    ) -> str:
        if processo == PROCESSO_AUTO_DELETE:
            return str(
                contexto.dados_extras.get("fase_execucao_ui") or FASE_EXECUCAO_AUTO_DELETE
            )
        return contexto.fase_execucao.value if contexto.fase_execucao else ""

    def _status_fases_log(
        self,
        contexto: ContextoTabelaProcessamento,
        processo: str,
    ) -> tuple[str, str]:
        if processo == PROCESSO_AUTO_DELETE:
            return "nao_aplicavel", "nao_aplicavel"
        return contexto.status_fase_1, contexto.status_fase_2

    def _formatar_detalhe_auto_delete(self, detalhe: str, dados_extras: dict) -> str:
        if dados_extras.get("processo") != PROCESSO_AUTO_DELETE:
            return detalhe
        try:
            ciclo = int(dados_extras.get("ciclo_execucao") or 0)
            total_ciclos = int(dados_extras.get("total_ciclos_execucao") or 0)
        except (TypeError, ValueError):
            return detalhe
        if ciclo > 0 and total_ciclos > 1:
            return f"{detalhe} | ciclo {ciclo}/{total_ciclos}"
        return detalhe

    def _prefixo_logs_execucao_atual(self) -> str:
        return f"exec{self._execucao_ui_atual}_"

    @staticmethod
    def _normalizar_nome_auto_delete(valor: str) -> str:
        return " ".join((valor or "").strip().upper().split())

    def _chave_falha_auto_delete(self, linha_excel: int, nome_cliente: str) -> str:
        return f"{int(linha_excel or 0)}|{self._normalizar_nome_auto_delete(nome_cliente)}"

    def _obter_falhas_pendentes_auto_delete(self) -> dict[str, RegistroAutoDelete]:
        try:
            _, registros = RepositorioAutoDeleteClientes().carregar_falhas_pendentes()
        except Exception:
            return {}

        return {
            self._chave_falha_auto_delete(registro.linha_excel, registro.nome_cliente): registro
            for registro in registros
            if registro.nome_cliente
        }

    def _entrada_auto_delete_pendente(
        self,
        entrada: EntradaLog,
        falhas_pendentes: Optional[dict[str, RegistroAutoDelete]] = None,
    ) -> bool:
        if entrada.processo != PROCESSO_AUTO_DELETE:
            return True

        falhas_pendentes = falhas_pendentes or self._obter_falhas_pendentes_auto_delete()
        dados = entrada.dados_reprocessamento or {}
        linha_excel = dados.get("linha_excel") or entrada.indice
        nome_cliente = str(dados.get("nome_cliente") or entrada.nome_tabela or "").strip()
        if not nome_cliente:
            return False

        chave = self._chave_falha_auto_delete(linha_excel, nome_cliente)
        if chave in falhas_pendentes:
            return True

        nome_normalizado = self._normalizar_nome_auto_delete(nome_cliente)
        return any(
            self._normalizar_nome_auto_delete(registro.nome_cliente) == nome_normalizado
            for registro in falhas_pendentes.values()
        )

    # ------------------------------------------------------------------
    # Filtragem e exportação de logs
    # ------------------------------------------------------------------

    def _aplicar_filtro_logs(self, status: Optional[str]) -> None:
        """Filtra a tabela de logs por status."""
        self._status_filtro_logs = status
        self._aplicar_filtros_logs_avancados()

        # Destaque visual no botão ativo
        estilo_ativo = (
            f"background: {PALETA_CORES['primaria']}; color: white; "
            f"border: 1px solid {PALETA_CORES['primaria']}; "
            f"border-radius: 10px; padding: 8px 12px; font-weight: 700;"
        )
        estilo_normal = ""  # volta ao QSS global

        self._botao_filtro_todos.setStyleSheet(estilo_ativo if status is None else estilo_normal)
        self._botao_filtro_erros.setStyleSheet(estilo_ativo if status == "Erro" else estilo_normal)
        self._botao_filtro_sucesso.setStyleSheet(estilo_ativo if status == "Sucesso" else estilo_normal)

    def _aplicar_filtros_logs_avancados(self) -> None:
        fase = self._combo_filtro_fase.currentData() if hasattr(self, "_combo_filtro_fase") else None
        tipo_execucao = (
            self._combo_filtro_tipo.currentData() if hasattr(self, "_combo_filtro_tipo") else None
        )
        processo = (
            self._combo_filtro_processo.currentData()
            if hasattr(self, "_combo_filtro_processo")
            else None
        )
        filtro_reprocessamento = (
            self._combo_filtro_reprocessamento.currentData()
            if hasattr(self, "_combo_filtro_reprocessamento")
            else None
        )
        self._gerenciador_logs.definir_filtros(
            status=self._status_filtro_logs,
            fase=fase,
            tipo_execucao=tipo_execucao,
            filtro_reprocessamento=filtro_reprocessamento,
            processo=processo,
        )
        self._atualizar_tabela_logs()

    def _exportar_falhas(self) -> None:
        """Exporta a lista de falhas para JSON."""
        falhas = self._gerenciador_logs.obter_falhas_exportaveis(aplicar_filtros=True)
        if not falhas:
            self._rotulo_detalhe_status.setText(
                "Nenhuma falha visível para exportar com os filtros atuais."
            )
            self._atualizar_horario()
            return

        import json

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pasta_downloads = Path.home() / "Downloads"
        pasta_downloads.mkdir(parents=True, exist_ok=True)
        caminho_padrao = pasta_downloads / f"falhas_reprocessar_{timestamp}.json"
        caminho_salvar, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Falhas",
            str(caminho_padrao),
            "Arquivos JSON (*.json)",
        )
        if not caminho_salvar:
            self._rotulo_detalhe_status.setText("Exportação de falhas cancelada.")
            self._atualizar_horario()
            return

        dados = []
        for e in falhas:
            dados.append({
                "linha_excel": e.indice,
                "nome_tabela": e.nome_tabela,
                "fase": e.fase,
                "fase_execucao": e.fase_execucao,
                "status": e.status.lower(),
                "tipo_erro": e.tipo_erro,
                "tipo_erro_legivel": e.tipo_erro_legivel,
                "motivo": e.motivo or e.detalhe,
                "detalhe": e.detalhe,
                "acao_recomendada": e.acao_recomendada,
                "screenshot": e.screenshot,
                "horario": e.horario,
                "tipo_execucao": e.tipo_execucao,
                "reprocessado": e.reprocessado,
                "processo": e.processo,
                "dados_reprocessamento": e.dados_reprocessamento,
                "status_fase_1": e.status_fase_1,
                "status_fase_2": e.status_fase_2,
            })

        caminho = Path(caminho_salvar)
        if caminho.suffix.lower() != ".json":
            caminho = caminho.with_suffix(".json")
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._rotulo_detalhe_status.setText(
            f"Exportadas {len(dados)} falha(s) para {caminho}"
        )
        self._atualizar_horario()

    def _reprocessar_linha(self, nome_tabela: str, fase: Optional[int] = None) -> None:
        """Reprocessa imediatamente uma tabela com erro."""
        # Bloqueia se há execução principal em andamento
        if self._ha_execucao_principal_ativa() or self._ha_execucao_auto_delete_ativa():
            self._rotulo_detalhe_status.setText(
                "Aguarde a execucao atual terminar antes de reprocessar."
            )
            self._atualizar_horario()
            return

        # Bloqueia se já existe reprocessamento rodando
        if (
            self._worker_reprocessamento
            and self._worker_reprocessamento.isRunning()
        ):
            self._rotulo_detalhe_status.setText(
                "Ja existe um reprocessamento em andamento."
            )
            self._atualizar_horario()
            return

        if (
            self._worker_reprocessamento_falhas
            and self._worker_reprocessamento_falhas.isRunning()
        ):
            self._rotulo_detalhe_status.setText(
                "Ja existe um reprocessamento global em andamento."
            )
            self._atualizar_horario()
            return

        entrada = self._gerenciador_logs.buscar_entrada_reprocessavel(
            nome_tabela,
            fase=fase,
        )
        if not entrada:
            self._rotulo_detalhe_status.setText(
                f"'{nome_tabela}': entrada reprocessável não encontrada nos logs."
            )
            self._atualizar_horario()
            return

        if not self._caminho_excel:
            self._rotulo_detalhe_status.setText("Nenhum arquivo Excel selecionado.")
            self._atualizar_horario()
            return

        self._worker_reprocessamento = TrabalhadorReprocessamento(
            caminho_excel=self._caminho_excel,
            nome_tabela=nome_tabela,
            fase=entrada.fase,
            indice=entrada.indice,
        )
        self._worker_reprocessamento.sinal_sucesso.connect(
            self._ao_reprocessamento_sucesso
        )
        self._worker_reprocessamento.sinal_erro.connect(
            self._ao_reprocessamento_erro
        )
        self._worker_reprocessamento.sinal_sistema.connect(
            lambda mensagem: self._ao_sistema(mensagem, PROCESSO_PRINCIPAL)
        )
        self._worker_reprocessamento.finished.connect(
            self._ao_worker_reprocessamento_finalizado
        )
        self._worker_reprocessamento.start()

        self._rotulo_detalhe_status.setText(f"Reprocessando '{nome_tabela}'...")
        self._atualizar_horario()

    def _reprocessar_entrada_log(self, chave: str) -> None:
        entrada = self._gerenciador_logs.buscar_por_chave(chave)
        if not entrada:
            self._rotulo_detalhe_status.setText("Entrada de log não encontrada.")
            self._atualizar_horario()
            return

        if entrada.processo == PROCESSO_AUTO_DELETE:
            self._reprocessar_auto_delete_individual(entrada)
            return

        self._reprocessar_linha(entrada.nome_tabela, entrada.fase)

    def _reprocessar_auto_delete_individual(self, entrada: EntradaLog) -> None:
        if self._ha_execucao_principal_ativa() or self._ha_execucao_auto_delete_ativa():
            self._rotulo_detalhe_status.setText(
                "Aguarde a execução atual terminar antes de reprocessar."
            )
            self._atualizar_horario()
            return
        if self._ha_reprocessamento_principal_ativo():
            self._rotulo_detalhe_status.setText(
                "Aguarde o reprocessamento atual terminar antes de iniciar o auto delete."
            )
            self._atualizar_horario()
            return
        if not self._entrada_auto_delete_pendente(entrada):
            self._rotulo_detalhe_status.setText(
                "Essa falha esta apenas no historico. "
                "Reprocesse pelas falhas pendentes do auto delete."
            )
            self._atualizar_horario()
            return
        if not entrada.dados_reprocessamento:
            self._rotulo_detalhe_status.setText(
                "Registro do auto delete sem dados suficientes para reprocessar."
            )
            self._atualizar_horario()
            return

        registro = RegistroAutoDelete.from_dict(entrada.dados_reprocessamento)
        self._preparar_execucao_ui(
            PROCESSO_AUTO_DELETE,
            f"Reprocessando auto delete para '{registro.nome_cliente}'...",
        )

        self._worker_auto_delete = TrabalhadorAutoDeleteClientes(
            self._caminho_excel,
            ordem_execucao=OrdemExecucaoAutoDelete.NORMAL,
            modo_execucao=ModoExecucaoAutoDelete.REPROCESSAMENTO_INDIVIDUAL,
            quantidade_ciclos=1,
            registro_individual=registro,
        )
        self._worker_auto_delete.sinal_total_fase_um.connect(self._ao_definir_total_fase_um)
        self._worker_auto_delete.sinal_total_fase_dois.connect(self._ao_definir_total_fase_dois)
        self._worker_auto_delete.sinal_processando.connect(self._ao_processando)
        self._worker_auto_delete.sinal_sucesso.connect(self._ao_sucesso)
        self._worker_auto_delete.sinal_falha.connect(self._ao_falha)
        self._worker_auto_delete.sinal_sistema.connect(
            lambda mensagem: self._ao_sistema(mensagem, PROCESSO_AUTO_DELETE)
        )
        self._worker_auto_delete.sinal_concluido.connect(self._ao_concluido)
        self._worker_auto_delete.sinal_parado.connect(self._ao_parado)
        self._worker_auto_delete.sinal_erro_critico.connect(self._ao_erro_critico)
        self._worker_auto_delete.finished.connect(self._ao_worker_auto_delete_finalizado)
        self._worker_auto_delete.start()

    def _reprocessar_falhas(self) -> None:
        """Dispara reprocessamento automatico de todas as falhas."""
        if self._ha_execucao_principal_ativa() or self._ha_execucao_auto_delete_ativa():
            self._rotulo_detalhe_status.setText(
                "Aguarde a execucao atual terminar antes de reprocessar falhas."
            )
            self._atualizar_horario()
            return
        if self._worker_reprocessamento and self._worker_reprocessamento.isRunning():
            self._rotulo_detalhe_status.setText(
                "Ja existe um reprocessamento individual em andamento."
            )
            self._atualizar_horario()
            return
        if self._worker_reprocessamento_falhas and self._worker_reprocessamento_falhas.isRunning():
            self._rotulo_detalhe_status.setText(
                "Ja existe um reprocessamento global em andamento."
            )
            self._atualizar_horario()
            return

        if self._combo_filtro_processo.currentData() == PROCESSO_AUTO_DELETE:
            indice_modo = self._combo_auto_delete_modo.findData(
                ModoExecucaoAutoDelete.REPROCESSAR_FALHAS.value
            )
            if indice_modo >= 0:
                self._combo_auto_delete_modo.setCurrentIndex(indice_modo)
            self._iniciar_auto_delete_clientes()
            return

        if not self._caminho_excel:
            self._rotulo_detalhe_status.setText("Nenhum arquivo Excel selecionado.")
            self._atualizar_horario()
            return

        self._worker_reprocessamento_falhas = TrabalhadorReprocessamentoFalhas(
            caminho_excel=self._caminho_excel
        )
        self._worker_reprocessamento_falhas.sinal_sistema.connect(
            lambda mensagem: self._ao_sistema(mensagem, PROCESSO_PRINCIPAL)
        )
        self._worker_reprocessamento_falhas.sinal_concluido.connect(
            self._ao_reprocessamento_falhas_concluido
        )
        self._worker_reprocessamento_falhas.sinal_erro.connect(
            self._ao_reprocessamento_falhas_erro
        )
        self._worker_reprocessamento_falhas.finished.connect(
            self._ao_worker_reprocessamento_falhas_finalizado
        )
        self._worker_reprocessamento_falhas.start()
        self._rotulo_detalhe_status.setText("Reprocessando falhas registradas...")
        self._atualizar_horario()

    def _ao_reprocessamento_sucesso(self, nome_tabela: str) -> None:
        self._rotulo_detalhe_status.setText(
            f"'{nome_tabela}' reprocessada com sucesso!"
        )
        self._atualizar_horario()

    def _ao_reprocessamento_erro(self, nome_tabela: str, mensagem: str) -> None:
        self._rotulo_detalhe_status.setText(
            f"Erro ao reprocessar '{nome_tabela}': {mensagem[:100]}"
        )
        self._atualizar_horario()

    def _ao_reprocessamento_falhas_concluido(self) -> None:
        self._rotulo_detalhe_status.setText("Reprocessamento global de falhas concluido.")
        self._atualizar_horario()

    def _ao_reprocessamento_falhas_erro(self, mensagem: str) -> None:
        self._rotulo_detalhe_status.setText(
            f"Erro no reprocessamento global: {mensagem[:100]}"
        )
        self._atualizar_horario()

    # ------------------------------------------------------------------
    # Paginação dos logs
    # ------------------------------------------------------------------

    def _pagina_anterior_logs(self) -> None:
        self._gerenciador_logs.pagina_anterior()
        self._atualizar_tabela_logs()

    def _proxima_pagina_logs(self) -> None:
        self._gerenciador_logs.proxima_pagina()
        self._atualizar_tabela_logs()
