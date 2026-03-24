# Identidade Visual — Design System do Painel RPA

**Fonte da verdade:** este documento foi gerado diretamente a partir do código-fonte.
Se houver conflito entre este documento e o código, o código prevalece.

Arquivos de referência:
- [`src/ui/componentes.py`](../src/ui/componentes.py)
- [`src/ui/ui_main.py`](../src/ui/ui_main.py)
- [`main.py`](../main.py)
- `public/logo.png`
- `public/fonts/Manrope-Variable.ttf`

---

## 1. Stack e dependências

### Dependências de produção

```
PySide6>=6.8
selenium>=4.29
```

### Módulos Qt utilizados

| Módulo | Uso |
|--------|-----|
| `PySide6.QtWidgets` | Todos os widgets visuais |
| `PySide6.QtCore` | `Qt`, alinhamento, políticas |
| `PySide6.QtGui` | `QFont`, `QFontDatabase`, `QPixmap`, `QColor`, `QBrush`, `QIcon` |
| `QGraphicsDropShadowEffect` | Sombras nos cards |
| `QMainWindow` | Janela principal |
| `QScrollArea` | Container scrollável principal |
| `QFrame` | Cards, divisores, badges |
| `QTableWidget` | Tabela de logs |
| `QProgressBar` | Barra de progresso |
| `QGridLayout` | Grade de estatísticas |
| `QVBoxLayout` / `QHBoxLayout` | Layouts compostos |
| `QHeaderView` | Controle do cabeçalho da tabela |
| `QAbstractItemView` | Configuração de comportamento da tabela |

### Estilo global Qt

```python
app.setStyle("Fusion")  # aplicado em main.py antes de qualquer widget
```

> **Por que Fusion?** Remove decorações nativas do SO (Windows Aero, macOS Aqua) e entrega uma base neutra sobre a qual o QSS funciona de forma previsível em qualquer plataforma.

---

## 2. Paleta de cores

Definida em `src/ui/componentes.py` como dicionário `PALETA_CORES`.

```python
PALETA_CORES = {
    "primaria":             "#21478A",
    "secundaria":           "#2B89D9",
    "fundo":                "#F3F7FB",
    "sucesso":              "#1F7A63",
    "perigo":               "#B55045",
    "branco":               "#FFFFFF",
    "texto_padrao":         "#0F172A",
    "texto_mutado":         "#64748B",
    "texto_sutil":          "#94A3B8",
    "borda":                "#D9E4F0",
    "borda_forte":          "#C6D6E7",
    "superficie_secundaria":"#F7FAFD",
    "info":                 "#2B89D9",
}
```

### Regras de uso

| Token | Uso correto |
|-------|-------------|
| `fundo` `#F3F7FB` | Fundo geral da aplicação e da scroll area |
| `branco` `#FFFFFF` | Fundo de todos os cards e tabela |
| `primaria` `#21478A` | Botão principal, textos de destaque, marcadores azuis, logo fallback |
| `secundaria` `#2B89D9` | Extremidade do gradiente da progress bar |
| `sucesso` `#1F7A63` | Marcador do card de sucessos |
| `perigo` `#B55045` | Cor do texto do botão de parar; marcador do card de falhas |
| `texto_padrao` `#0F172A` | Texto principal de leitura |
| `texto_mutado` `#64748B` | Rótulos secundários, timestamps, placeholders |
| `texto_sutil` `#94A3B8` | Detalhe de apoio, texto desabilitado |
| `borda` `#D9E4F0` | Borda padrão de cards, tabela, inputs |
| `borda_forte` `#C6D6E7` | Borda do painel de status lateral, botões secundários |
| `superficie_secundaria` `#F7FAFD` | Fundo do painel de status lateral no cabeçalho |

### Cores adicionais (definidas inline no QSS)

```
#EAF2FC  — fundo do selo "PAINEL OPERACIONAL"
#F6F9FC  — fundo do cabeçalho da tabela
#52627A  — cor do texto do cabeçalho da tabela
#E6EDF5  — separador inferior de linhas da tabela
#EEF4FB  — linha selecionada da tabela
#EFF5FD  — fundo do botão de tabela (reprocessar)
#E4EEFA  — hover do botão de tabela
#E2E8F0  — trilho da progress bar / borda de botão desabilitado
#EEF3F8  — trilho da scrollbar
#D9E4EF  — borda da scrollbar
#8FA6BE  — handle normal da scrollbar
#7D95AE  — borda do handle da scrollbar
#6F87A2  — handle hover da scrollbar
#5E7690  — handle pressed da scrollbar
#1A3970  — hover do botão primário
#15315E  — pressed do botão primário
#FFF7F5  — hover do botão de perigo
#E4BDB8  — borda do botão de perigo
#F1F5F9  — fundo do botão de tabela desabilitado
#F8FBFF  — hover dos botões secundário e de paginação
```

---

## 3. Tipografia

### Carregamento da fonte

```python
# main.py — _configurar_fonte_aplicacao()
identificador = QFontDatabase.addApplicationFont("public/fonts/Manrope-Variable.ttf")
familias = QFontDatabase.applicationFontFamilies(identificador)
app.setFont(QFont(familias[0], 10))  # fonte padrão global: 10pt
```

### Fonte principal

| Propriedade | Valor |
|-------------|-------|
| Família | `Manrope` (variável) |
| Arquivo | `public/fonts/Manrope-Variable.ttf` |
| Tamanho padrão | `10pt` |
| Fallbacks (em ordem) | `Aptos`, `Bahnschrift`, `Segoe UI` |

### Fonte técnica (monospace)

```python
self.fonte_mono = QFont("Consolas", 10)
self.fonte_mono.setStyleHint(QFont.Monospace)
```

Aplicada apenas em:
- Coluna **Linha** (id_linha) da tabela
- Coluna **Horário** da tabela

### Escala tipográfica

| Elemento | Tamanho | Peso | Cor |
|----------|---------|------|-----|
| Título principal (cabeçalho) | `28px` | `800` | `texto_padrao` |
| Título de seção | `18px` | `700` | `texto_padrao` |
| Número do CartaoEstatistica | `30px` | `800` | `texto_padrao` |
| Número do mini-card de log | `20px` | `800` | `texto_padrao` |
| Percentual de progresso | `28px` | `800` | `primaria` |
| Logo fallback | `24px` | `800` | `primaria` |
| Subtítulo / texto descritivo | `13px` | `400` | `texto_mutado` |
| Rótulo de input / contexto | `12px` | `600` | variável |
| Detalhe do CartaoEstatistica | `12px` | `400` | `texto_sutil` |
| Rótulo mini-card (título) | `11px` | `700` | `texto_mutado` |
| Detalhe mini-card (subtítulo) | `11px` | `400` | `texto_sutil` |
| Cabeçalho da tabela | `12px` | `700` | `#52627A` |
| Badge de status na tabela | `11px` | `700` | variável semântico |
| Paginação | `12px` | `600` | `texto_mutado` |
| Selo topo | `11px` | `700` | `primaria` |

### Letter-spacing

Usado **somente** em elementos de micro-rótulo (não em texto corrido):

```css
letter-spacing: 0.4px;
```

Aplicado em:
- Selo `PAINEL OPERACIONAL` (`QLabel#etiquetaTopo`)
- Título do `CartaoEstatistica` (`rotulo_titulo` no topo do card)

---

## 4. Dimensões da janela

```python
self.resize(1450, 960)          # tamanho inicial
self.setMinimumSize(1240, 820)  # tamanho mínimo
janela.showMaximized()          # abre maximizado
```

---

## 5. Layout principal

### Estrutura hierárquica

```
QMainWindow
└── QScrollArea#scrollPrincipal (sem borda, sem scroll horizontal)
    └── QWidget#widgetCentral
        └── QVBoxLayout  ← layout_principal
            ├── margins: 30px H, 26px V
            ├── spacing: 20px
            ├── [1] QFrame#cabecalhoPainel     — cabeçalho institucional
            ├── [2] QFrame#cartaoPadrao        — controles de execução
            ├── [3] QGridLayout                — grade de 4 estatísticas
            ├── [4] QFrame#cartaoPadrao        — progresso
            ├── [5] QFrame#cartaoPadrao        — histórico de logs (stretch=1)
            └── [6] QFrame#rodapePainel        — assinatura e suporte
```

### Ordem obrigatória das seções

1. Cabeçalho institucional
2. Controles de execução
3. Grade de estatísticas (4 colunas iguais)
4. Progresso
5. Histórico de execução (ocupa o espaço restante)
6. Footer institucional com autoria e suporte

---

## 6. Sistema de sombras

Implementado via `QGraphicsDropShadowEffect`. Método reutilizável:

```python
def _aplicar_sombra(self, widget, blur=32, deslocamento_y=8):
    sombra = QGraphicsDropShadowEffect(self)
    sombra.setBlurRadius(blur)
    sombra.setOffset(0, deslocamento_y)
    sombra.setColor(QColor(15, 23, 42, 24))  # rgba(15,23,42,0.094)
    widget.setGraphicsEffect(sombra)
```

### Valores por componente

| Componente | `blur` | `offset_y` | Offset X |
|------------|--------|------------|----------|
| `#cabecalhoPainel` | `34` | `10` | `0` |
| `#cartaoPadrao` (todos) | `24` | `5` | `0` |
| `CartaoEstatistica` | `24` | `5` | `0` |

> **Regra crítica:** a cor da sombra é sempre `QColor(15, 23, 42, 24)` — azul-petróleo quase opaco, alpha baixíssimo. Sombra preta ou cinza destrói o efeito.

---

## 7. Cards

### QSS aplicado a todos os cards

```css
QFrame#cartaoPadrao,
QFrame#cartaoEstatistica,
QFrame#resumoLogCard,
QFrame#containerTabelaLogs {
    background: #FFFFFF;
    border: 1px solid #D9E4F0;
    border-radius: 20px;
}
```

### Cabeçalho (`#cabecalhoPainel`)

```css
QFrame#cabecalhoPainel {
    background: #FFFFFF;
    border: 1px solid #D9E4F0;
    border-radius: 24px;  /* único card com raio maior */
}
```

Padding interno: `28px 24px` (contentsMargins do layout)

### Card padrão (controles / progresso / logs)

- `border-radius: 20px`
- Padding interno: `22px 20px`
- Sombra: blur `24`, offsetY `5`

### CartaoEstatistica

```python
# src/ui/componentes.py
self.setMinimumHeight(138)
conteudo.setContentsMargins(18, 18, 18, 18)
conteudo.setSpacing(12)
```

Anatomia interna:
```
QVBoxLayout (18px padding, 12px spacing)
├── QHBoxLayout (topo)
│   ├── QFrame marcador — 10×10, border-radius 5px, cor de destaque
│   └── QLabel título   — 12px, 700, texto_mutado, letter-spacing 0.4px
├── QLabel valor        — 30px, 800, texto_padrao
└── QLabel detalhe      — 12px, 400, texto_sutil
```

Cores de marcador por card:
- Total: `primaria` (`#21478A`)
- Processados: `secundaria` (`#2B89D9`)
- Sucessos: `sucesso` (`#1F7A63`)
- Falhas: `perigo` (`#B55045`)

### Mini-card de resumo de log (`#resumoLogCard`)

```python
cartao.setMinimumWidth(180)
cartao.setMinimumHeight(96)
layout.setContentsMargins(16, 14, 16, 14)
layout.setSpacing(6)
```

Anatomia:
```
QVBoxLayout (16/14px padding, 6px spacing)
├── QLabel título  — 11px, 700, texto_mutado
├── QLabel valor   — 20px, 800, texto_padrao (min-height 30px)
└── QLabel detalhe — 11px, 400, texto_sutil (word wrap)
```

### Painel de status lateral (no cabeçalho)

```css
QFrame#cabecalhoStatus {
    background: #F7FAFD;
    border: 1px solid #C6D6E7;
    border-radius: 20px;
}
```

```python
painel_status.setMinimumWidth(300)
layout_status.setContentsMargins(18, 18, 18, 18)
layout_status.setSpacing(8)
```

---

## 8. Cabeçalho institucional

### Estrutura

```
QFrame#cabecalhoPainel (border-radius 24px, shadow blur=34 y=10)
└── QHBoxLayout (28px H, 24px V padding, 24px spacing)
    ├── QWidget marca (flex 1)
    │   └── QHBoxLayout (0px padding, 18px spacing)
    │       ├── QLabel logo (pixmap 48px height, SmoothTransformation)
    │       ├── QFrame divisor (1px wide, cor borda_forte)
    │       └── QVBoxLayout bloco_titulo (6px spacing)
    │           ├── QLabel#etiquetaTopo "PAINEL OPERACIONAL"
    │           ├── QLabel título (28px, 800, texto_padrao)
    │           └── QLabel subtítulo (13px, texto_mutado)
    └── QFrame#cabecalhoStatus (min-width 300px, AlignTop)
        └── QVBoxLayout (18px padding, 8px spacing)
            ├── QLabel "Status do robo" (12px, 600, texto_mutado)
            ├── EtiquetaStatus (badge de status)
            ├── QLabel detalhe do status (13px, 600, texto_padrao)
            └── QLabel horário da atualização (12px, texto_mutado)
```

### Selo superior (`#etiquetaTopo`)

```css
QLabel#etiquetaTopo {
    background: #EAF2FC;
    color: #21478A;
    border-radius: 11px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.4px;
}
```

---

## 9. Badges de status

### EtiquetaStatus (badge principal do robô)

```python
# src/ui/componentes.py
self.setAlignment(Qt.AlignCenter)
self.setMinimumWidth(118)
self.setFixedHeight(34)
# border-radius: 17px  (= altura/2)
# padding: 6px 14px
# font-size: 12px, font-weight: 700
```

### Badge de status na tabela

```python
# _criar_widget_status_tabela()
badge.setMinimumWidth(LARGURA_COLUNA_LOG_STATUS - 18)  # 138px
# border-radius: 11px
# padding interno: 12px 6px (contentsMargins)

marcador.setFixedSize(8, 8)
# border-radius: 4px
# cor = cor_texto do status

rotulo — 11px, 700, border: none
```

### Mapa semântico de cores

```python
MAPA_CORES_STATUS = {
    "Parado":      ("#F8FAFC", "#475569", "#CBD5E1"),  # fundo, texto, borda
    "Executando":  ("#E8F1FF", "#1D4ED8", "#BFDBFE"),
    "Erro":        ("#FEF2F2", "#B42318", "#FECACA"),
    "Sucesso":     ("#ECFDF3", "#166534", "#BBF7D0"),
    "Processando": ("#EFF6FF", "#1E40AF", "#BFDBFE"),
}
# fallback: ("#F8FAFC", "#0F172A", "#D9E4F0")
```

> **Regra:** saturação baixa, borda visível, fundo claro. Nunca cores cheias.

---

## 10. Botões

### Botão primário (`#botaoPrimario`)

```css
QPushButton#botaoPrimario {
    background: #21478A;
    color: white;
    border: none;
    border-radius: 14px;
    padding: 13px 20px;
    font-weight: 700;
    min-width: 168px;
}
QPushButton#botaoPrimario:hover   { background: #1A3970; }
QPushButton#botaoPrimario:pressed { background: #15315E; }
```

### Botão de perigo (`#botaoPerigo`)

```css
QPushButton#botaoPerigo {
    background: white;
    color: #B55045;
    border: 1px solid #E4BDB8;
    border-radius: 14px;
    padding: 13px 20px;
    font-weight: 700;
    min-width: 168px;
}
QPushButton#botaoPerigo:hover { background: #FFF7F5; }
```

> Não tem estado `pressed` definido. O fundo permanece branco — esse botão nunca deve dominar visualmente.

### Botão secundário (`#botaoSecundario`)

```css
QPushButton#botaoSecundario {
    background: white;
    color: #21478A;
    border: 1px solid #C6D6E7;
    border-radius: 12px;
    padding: 10px 16px;
    font-weight: 700;
    min-width: 148px;
}
QPushButton#botaoSecundario:hover { background: #F8FBFF; }
```

### Botão de tabela (`#botaoTabela`)

```css
QPushButton#botaoTabela {
    background: #EFF5FD;
    color: #21478A;
    border: 1px solid #C6D6E7;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 700;
}
QPushButton#botaoTabela:hover    { background: #E4EEFA; }
QPushButton#botaoTabela:disabled {
    background: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}
```

Tamanho mínimo dentro da tabela:
```python
botao.setMinimumHeight(34)
botao.setMinimumWidth(LARGURA_COLUNA_LOG_ACAO - 22)  # 114px
```

### Botão de paginação (`#botaoPaginacao`)

```css
QPushButton#botaoPaginacao {
    background: white;
    color: #21478A;
    border: 1px solid #C6D6E7;
    border-radius: 10px;
    min-width: 38px;
    max-width: 38px;
    min-height: 34px;
    max-height: 34px;
    font-weight: 800;
}
QPushButton#botaoPaginacao:hover { background: #F8FBFF; }
```

### Estado global desabilitado

```css
QPushButton:disabled {
    background: #E2E8F0;
    color: #94A3B8;
    border-color: #E2E8F0;
}
```

### Campo de input (`QLineEdit`)

```css
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #D9E4F0;
    border-radius: 8px;
    padding: 0 12px;
    font-size: 14px;
    font-weight: 600;
    color: #0F172A;
}
QLineEdit:focus {
    border-color: #21478A;
}
```

Dimensões fixas no painel de controles:
```python
self.input_valor_reajuste.setFixedWidth(120)
self.input_valor_reajuste.setFixedHeight(38)
```

---

## 11. Progresso

### Seção

```
QFrame#cartaoPadrao
└── QVBoxLayout (22/20px padding, 14px spacing)
    ├── QHBoxLayout topo (18px spacing)
    │   ├── QVBoxLayout bloco_texto (6px spacing)
    │   │   ├── QLabel título (18px, 700)
    │   │   └── QLabel rotulo_progresso (13px, texto_mutado)
    │   ├── QStretch
    │   └── QLabel#rotuloPercentual (28px, 800, primaria)
    └── QProgressBar#barraProgresso (altura fixa 14px)
```

### QSS da barra

```css
QProgressBar#barraProgresso {
    border: none;
    border-radius: 7px;
    background: #E2E8F0;  /* trilho */
}
QProgressBar#barraProgresso::chunk {
    border-radius: 7px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #21478A,
        stop:1 #2B89D9
    );
}
```

> O gradiente horizontal é o **único** local da interface onde gradiente é usado.

---

## 12. Tabela de logs

### Constantes de dimensão

```python
LINHAS_LOGS_POR_PAGINA         = 8
ALTURA_LINHA_LOG               = 60
ALTURA_CABECALHO_TABELA_LOG    = 44
LARGURA_COLUNA_LOG_LINHA       = 92
LARGURA_COLUNA_LOG_CLIENTE     = 240
LARGURA_COLUNA_LOG_STATUS      = 156
LARGURA_COLUNA_LOG_HORARIO     = 112
LARGURA_COLUNA_LOG_ACAO        = 136
# coluna Detalhe: QHeaderView.Stretch (ocupa o restante)
```

### Configuração do widget

```python
self.tabela_logs = QTableWidget(0, 6)
self.tabela_logs.setShowGrid(False)
self.tabela_logs.setAlternatingRowColors(False)
self.tabela_logs.setSelectionMode(QAbstractItemView.NoSelection)
self.tabela_logs.setEditTriggers(QAbstractItemView.NoEditTriggers)
self.tabela_logs.setFocusPolicy(Qt.NoFocus)
self.tabela_logs.setWordWrap(False)
self.tabela_logs.setTextElideMode(Qt.ElideRight)
self.tabela_logs.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
self.tabela_logs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
self.tabela_logs.verticalHeader().setVisible(False)
self.tabela_logs.verticalHeader().setDefaultSectionSize(ALTURA_LINHA_LOG)
self.tabela_logs.verticalScrollBar().setSingleStep(24)
```

Altura calculada e fixada:
```python
altura_tabela = ALTURA_CABECALHO_TABELA_LOG + (LINHAS_LOGS_POR_PAGINA * ALTURA_LINHA_LOG) + 4
# = 44 + 480 + 4 = 528px
self.tabela_logs.setFixedHeight(altura_tabela)
```

### Cabeçalho da tabela

```python
cabecalho.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
cabecalho.setHighlightSections(False)
cabecalho.setFixedHeight(44)
# Linha:    Fixed (92px)
# Cliente:  Fixed (240px)
# Status:   Fixed (156px)
# Detalhe:  Stretch
# Horario:  Fixed (112px)
# Acao:     Fixed (136px)
```

```css
QHeaderView::section {
    background: #F6F9FC;
    color: #52627A;
    border: none;
    border-bottom: 1px solid #D9E4F0;
    padding: 12px 14px;
    font-size: 12px;
    font-weight: 700;
}
```

### QSS da tabela

```css
QTableWidget#tabelaLogs {
    background: white;
    border: none;
    outline: none;
    gridline-color: transparent;
    color: #0F172A;
}
QTableWidget#tabelaLogs::item {
    border-bottom: 1px solid #E6EDF5;
    padding: 6px 8px;
}
QTableWidget#tabelaLogs::item:selected {
    background: #EEF4FB;
    color: #0F172A;
}
```

### Distribuição de conteúdo por coluna

| Col | Nome | Modo | Largura | Fonte | Cor |
|-----|------|------|---------|-------|-----|
| 0 | Linha | Fixed | 92px | Consolas 10 | `texto_mutado` |
| 1 | Cliente | Fixed | 240px | Manrope | `texto_padrao` / `primaria` se sistema |
| 2 | Status | Fixed | 156px | — (widget) | semântica |
| 3 | Detalhe | Stretch | restante | Manrope | `texto_padrao` (elide right) |
| 4 | Horario | Fixed | 112px | Consolas 10 | `texto_mutado` |
| 5 | Acao | Fixed | 136px | — (widget) | — |

### Paginação

```python
# Visível apenas quando há mais de 1 página
self.botao_pagina_anterior_logs.setVisible(mostrar_navegacao)
self.botao_pagina_seguinte_logs.setVisible(mostrar_navegacao)
self.rotulo_pagina_logs.setVisible(mostrar_navegacao)
```

```css
QLabel#rotuloPaginacaoLogs {
    color: #64748B;
    font-size: 12px;
    font-weight: 600;
}
```

---

## 13. Scrollbar

```css
QScrollBar:vertical {
    background: #EEF3F8;
    width: 14px;
    margin: 6px 2px 6px 2px;
    border: 1px solid #D9E4EF;
    border-radius: 7px;
}
QScrollBar::handle:vertical {
    background: #8FA6BE;
    border: 1px solid #7D95AE;
    border-radius: 6px;
    min-height: 42px;
}
QScrollBar::handle:vertical:hover   { background: #6F87A2; border-color: #617996; }
QScrollBar::handle:vertical:pressed { background: #5E7690; border-color: #516880; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
    height: 0px;
}
```

---

## 14. QSS global completo

O QSS completo é aplicado em `_aplicar_estilo_global()` via `self.setStyleSheet(...)`.
Estrutura de seletores utilizados:

```
QMainWindow
QWidget#widgetCentral
QScrollArea#scrollPrincipal
QScrollArea#scrollPrincipal > QWidget > QWidget
QFrame#cabecalhoPainel
QFrame#cabecalhoStatus
QLabel#etiquetaTopo
QLabel#logoFallback
QLabel#rotuloPercentual
QFrame#cartaoPadrao
QFrame#cartaoEstatistica
QFrame#resumoLogCard
QFrame#containerTabelaLogs
QPushButton#botaoPrimario       (+ :hover, :pressed)
QPushButton#botaoPerigo         (+ :hover)
QPushButton#botaoSecundario     (+ :hover)
QPushButton#botaoPaginacao      (+ :hover)
QPushButton#botaoTabela         (+ :hover, :disabled)
QPushButton:disabled
QLabel#rotuloPaginacaoLogs
QTableWidget#tabelaLogs
QTableWidget#tabelaLogs::item   (+ :selected)
QHeaderView::section
QProgressBar#barraProgresso
QProgressBar#barraProgresso::chunk
QScrollBar:vertical
QScrollBar::handle:vertical     (+ :hover, :pressed)
QScrollBar::add-line:vertical
QScrollBar::sub-line:vertical
QScrollBar::add-page:vertical
QScrollBar::sub-page:vertical
```

---

## 15. Componentes reutilizáveis

### `EtiquetaStatus` — `src/ui/componentes.py`

**Herda de:** `QLabel`

**Função:** badge arredondado de status com cor semântica. Usado no cabeçalho e na tabela (via `_criar_widget_status_tabela`).

```python
class EtiquetaStatus(QLabel):
    MAPA_CORES_STATUS = { ... }  # ver seção 9

    def __init__(self, texto: str) -> None: ...
    def atualizar(self, texto: str) -> None: ...
```

**Dimensões:** min-width `118px`, height fixo `34px`, border-radius `17px`.

**Uso:**
```python
self.etiqueta_status = EtiquetaStatus("Parado")
self.etiqueta_status.atualizar("Executando")
```

---

### `CartaoEstatistica` — `src/ui/componentes.py`

**Herda de:** `QFrame`

**Função:** card de KPI com marcador colorido, número grande e rótulo de apoio.

```python
class CartaoEstatistica(QFrame):
    def __init__(self, titulo: str, cor_destaque: str, valor_inicial: int | str = 0): ...
    def atualizar_valor(self, valor: int) -> None: ...

    @staticmethod
    def _formatar_valor(valor: int | str) -> str:
        # formata inteiro com ponto como separador de milhares
        return f"{valor:,}".replace(",", ".")
```

**objectName:** `"cartaoEstatistica"` — necessário para o QSS funcionar.

**Uso:**
```python
self.cartao_total = CartaoEstatistica("Total de registros", PALETA_CORES["primaria"])
self.cartao_total.atualizar_valor(1500)
```

---

### Métodos visuais da janela principal

| Método | Responsabilidade |
|--------|-----------------|
| `_aplicar_estilo_global()` | Define o QSS completo da aplicação |
| `_aplicar_sombra(widget, blur, deslocamento_y)` | Aplica `QGraphicsDropShadowEffect` em qualquer widget |
| `_criar_cabecalho()` | Monta o `QFrame#cabecalhoPainel` com logo, título e painel de status |
| `_criar_secao_controles()` | Card com input de parâmetro e botões primário/perigo |
| `_criar_grade_estatisticas()` | `QGridLayout` 1×4 com `CartaoEstatistica` |
| `_criar_secao_progresso()` | Card com título, percentual e barra de progresso |
| `_criar_secao_logs()` | Card com mini-cards, tabela paginada e controles de página |
| `_criar_cartao_resumo_log()` | Retorna `QFrame#resumoLogCard` com valor e detalhe |
| `_criar_widget_status_tabela()` | Widget de badge inline para célula da tabela |
| `_criar_widget_acao_tabela()` | Container com botão alinhado à direita |
| `_setar_item_texto()` | Helper para popular célula com texto, cor e fonte |

---

## 16. Arquitetura da interface

```
main.py
├── QApplication (Fusion style)
├── QFontDatabase.addApplicationFont (Manrope)
├── app.setFont(QFont(familias[0], 10))
└── JanelaPainelAutomacao (QMainWindow)
    ├── _aplicar_estilo_global() → QSS global
    ├── _montar_interface()
    │   ├── QScrollArea (wrapper principal)
    │   └── QVBoxLayout (30/26px margins, 20px spacing)
    │       ├── _criar_cabecalho()
    │       ├── _criar_secao_controles()
    │       ├── _criar_grade_estatisticas() → 4× CartaoEstatistica
    │       ├── _criar_secao_progresso()
    │       └── _criar_secao_logs()
    │           ├── 3× _criar_cartao_resumo_log()
    │           ├── QTableWidget (paginado, 8 linhas/página)
    │           └── controles de paginação
    └── TrabalhadorExecucaoRpa (QThread)
        └── sinais → slots de atualização da UI
```

---

## 17. Boas práticas implementadas

### Por que essa UI parece melhor

1. **Estilo Fusion como base neutra** — elimina ruído nativo do SO antes de aplicar QSS.
2. **Fonte customizada via QFontDatabase** — Manrope carregada antes do primeiro widget ser criado.
3. **Paleta centralizada em dicionário** — uma única fonte de verdade, sem hex hardcoded espalhado.
4. **Sombra com alpha baixo e cor fria** — `rgba(15,23,42,24)` cria profundidade sem peso visual.
5. **Raio de borda alto e consistente** — 20px em todos os cards, 24px no cabeçalho, 14px nos botões principais. Cria linguagem visual coesa.
6. **objectName obrigatório** — todos os widgets estilizáveis têm `setObjectName()` para QSS por ID, evitando contaminação de seletores genéricos.
7. **Sem grid pesada na tabela** — `setShowGrid(False)`, separação apenas por `border-bottom` nas células.
8. **Paginação discreta** — controles de navegação aparecem somente quando há mais de uma página.
9. **Elide right na coluna Detalhe** — previne quebra de layout com textos longos.
10. **Gradiente restrito à progress bar** — não vaza para outros componentes.
11. **Scrollbar estilizada** — sem setas, trilho com borda, handle azul-acinzentado suave.
12. **Thread separada para o robô** — `QThread` via `TrabalhadorExecucaoRpa`, UI nunca trava.
13. **Badges com saturação baixa** — fundo pastel, borda semântica, texto colorido — sem blocos sólidos de cor.
14. **Tipografia monospace só onde faz sentido** — Consolas apenas em ID e horário, mantendo leitura técnica sem poluir o visual.

---

## 18. Regras para replicar em outro projeto

### Estrutura mínima de arquivos

```
src/
└── ui/
    ├── __init__.py
    ├── componentes.py   ← PALETA_CORES, EtiquetaStatus, CartaoEstatistica
    └── ui_main.py       ← JanelaPainelAutomacao (QMainWindow)
main.py                  ← bootstrap: QApplication, Fusion, fonte, showMaximized
public/
├── fonts/
│   └── Manrope-Variable.ttf
├── logo.png
└── app-icon.ico
```

### Sequência obrigatória no bootstrap (`main.py`)

```python
app = QApplication(sys.argv)
app.setStyle("Fusion")          # 1. estilo base ANTES de qualquer widget
_configurar_fonte_aplicacao(app) # 2. fonte global ANTES de qualquer widget
janela = MinhaJanela()           # 3. janela (já usa font e style)
janela.showMaximized()           # 4. abre maximizado
app.exec()
```

### Sequência obrigatória na janela

```python
def __init__(self):
    super().__init__()
    self._aplicar_estilo_global()  # QSS PRIMEIRO
    self._montar_interface()        # depois monta widgets
```

### Regras de QSS

- Sempre usar seletores por `#objectName`, nunca por classe genérica (`QFrame`, `QPushButton`)
- Definir o QSS completo em um único `setStyleSheet()` na janela raiz
- Não aplicar QSS parcial dentro de widgets filhos (conflita com o global)
- Exceção: `EtiquetaStatus.atualizar()` aplica QSS diretamente no label para troca dinâmica de cor

### Regras de sombra

```python
# Sempre usar este padrão — nunca modificar a cor da sombra
sombra = QGraphicsDropShadowEffect(parent)
sombra.setBlurRadius(blur)   # 24 para cards, 34 para cabeçalho
sombra.setOffset(0, y)       # 5 para cards, 10 para cabeçalho
sombra.setColor(QColor(15, 23, 42, 24))
widget.setGraphicsEffect(sombra)
```

### Regras de layout

- Margins externas da janela: `30px` H, `26px` V
- Spacing entre blocos principais: `20px`
- Padding interno dos cards: `22px 20px`
- Gap da grade de estatísticas: `18px`
- Gap entre mini-cards de resumo: `12px`
- Alinhamento: majoritariamente à esquerda

---

## 19. Checklist de implementação

### Setup

- [ ] Instalar `PySide6>=6.8`
- [ ] Criar estrutura de pastas `src/ui/`, `public/fonts/`
- [ ] Baixar `Manrope-Variable.ttf` e colocar em `public/fonts/`
- [ ] Criar `public/logo.png` e `public/app-icon.ico`

### Bootstrap

- [ ] `main.py` chama `app.setStyle("Fusion")` antes de qualquer widget
- [ ] `main.py` carrega Manrope via `QFontDatabase` e define `app.setFont(QFont(..., 10))`
- [ ] `main.py` abre a janela com `showMaximized()`

### Componentes base

- [ ] Criar `PALETA_CORES` em `componentes.py`
- [ ] Implementar `EtiquetaStatus` com `MAPA_CORES_STATUS` e método `atualizar()`
- [ ] Implementar `CartaoEstatistica` com marcador colorido, número grande e detalhe

### Janela principal

- [ ] Chamar `_aplicar_estilo_global()` no `__init__` ANTES de montar widgets
- [ ] QSS global com todos os seletores por `#objectName`
- [ ] Layout principal: `QScrollArea` → `QVBoxLayout` com margins `30/26px` e spacing `20px`
- [ ] Implementar `_aplicar_sombra()` com `QColor(15, 23, 42, 24)`

### Cards e seções

- [ ] Cabeçalho: `border-radius: 24px`, sombra blur=34, logo + divisor + título + painel status
- [ ] Cards padrão: `border-radius: 20px`, sombra blur=24
- [ ] Grade de estatísticas: `QGridLayout` 1×4, spacing `18px`, `CartaoEstatistica` em cada coluna
- [ ] Barra de progresso: gradiente horizontal `primaria → secundaria`, trilho `#E2E8F0`

### Tabela

- [ ] `setShowGrid(False)`, sem scroll visível, sem alternância de cores
- [ ] Cabeçalho fixo 44px, linhas fixas 60px, 8 linhas por página
- [ ] Coluna Detalhe com `QHeaderView.Stretch`
- [ ] Badge de status como widget na célula (não texto simples)
- [ ] Fonte Consolas nas colunas Linha e Horário
- [ ] Paginação visível apenas quando `total_páginas > 1`

### Scrollbar

- [ ] QSS da scrollbar vertical com trilho `#EEF3F8`, handle `#8FA6BE`, sem setas

### Badges

- [ ] Usar `MAPA_CORES_STATUS` para todos os estados semânticos
- [ ] Saturação baixa, fundo pastel, borda colorida
- [ ] Nunca colorir o fundo inteiro com cor sólida forte

---

## 20. DPI Scaling

### Status no projeto atual

O projeto **não configura DPI scaling explicitamente**. O Qt aplica o comportamento padrão da plataforma.

### Por que isso importa

Em monitores com escala 125% / 150% / 200% (comum no Windows 11), sem configuração explícita:
- layouts podem ficar maiores ou menores que o esperado
- bordas de 1px podem virar 2px
- sombras podem parecer mais pesadas
- fontes podem não coincidir com os tamanhos documentados

### Configuração recomendada (adicionar em `main.py` antes de `QApplication`)

```python
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Opção 1 — via código (recomendado para distribuição)
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

app = QApplication(sys.argv)
```

```bash
# Opção 2 — via variáveis de ambiente (desenvolvimento)
QT_ENABLE_HIGHDPI_SCALING=1
QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough
```

### Quando aplicar

| Cenário | Ação |
|---------|------|
| Desenvolver em monitor 100% | Sem necessidade imediata |
| Distribuir para usuários com 125%/150% | Obrigatório |
| UI parecer maior/menor que o esperado | Verificar primeiro |

> `PassThrough` preserva o fator de escala exato do SO sem arredondamentos, mantendo a fidelidade pixel dos valores documentados neste design system.

---

## 21. Renderização da logo

### Como está implementado

```python
# ui_main.py — _criar_cabecalho()
pixmap_logo = self._obter_logo_empresa()
if pixmap_logo is not None:
    rotulo_logo.setPixmap(
        pixmap_logo.scaledToHeight(48, Qt.SmoothTransformation)
    )
```

### Diferença crítica: `scaledToHeight` vs `scaled`

O projeto usa `scaledToHeight(48, Qt.SmoothTransformation)` — não o `scaled(w, h, ...)`.

| Método | Comportamento |
|--------|--------------|
| `scaledToHeight(48, Qt.SmoothTransformation)` | Mantém proporção, fixa altura em 48px, largura calculada automaticamente |
| `scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)` | Cabe em caixa, pode variar altura |
| `scaled(w, h)` sem SmoothTransformation | Imagem pixelizada/borrada |

### Regra

Sempre usar `Qt.SmoothTransformation`. Sem ele, logos ficam borradas em qualquer escala diferente de 1:1.

### Fallback textual

```python
# Se logo.png não existir:
rotulo_logo.setObjectName("logoFallback")
rotulo_logo.setText("Rodogarcia")

# QSS do fallback:
# QLabel#logoFallback { color: #21478A; font-size: 24px; font-weight: 800; }
```

---

## 22. Políticas de tamanho (QSizePolicy)

Definições críticas que controlam como cada widget cresce ou encolhe.

### Mapa completo por widget

| Widget | Política horizontal | Política vertical | Notas |
|--------|--------------------|--------------------|-------|
| `QScrollArea` (wrapper) | — | — | `setWidgetResizable(True)` |
| `QFrame#cartaoPadrao` (logs) | `Expanding` | `Expanding` | único card que cresce verticalmente |
| `container_tabela` | `Expanding` | `Fixed` | altura travada em `altura_tabela + 16` |
| `QTableWidget#tabelaLogs` | `Expanding` | `Expanding` | dentro do container fixo |
| Badge de status na tabela | `Fixed` | `Fixed` | não estica |
| `QFrame divisor` (cabeçalho) | — | — | `setFixedWidth(1)` |

### Código exato

```python
# Card de logs ocupa o espaço vertical restante
cartao.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

# Container da tabela: largura livre, altura travada
container_tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
container_tabela.setMinimumHeight(altura_tabela + 16)
container_tabela.setMaximumHeight(altura_tabela + 16)

# Tabela interna: cresce dentro do container
self.tabela_logs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

# Badge de status: tamanho fixo, não estica
badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
```

### Por que isso importa

Sem `Expanding` no card de logs, ele não ocupa o espaço restante da janela.
Sem `Fixed` no container da tabela, a altura da tabela varia com o conteúdo e quebra a paginação.

### `addLayout` com stretch

```python
layout_principal.addWidget(self._criar_secao_logs(), 1)
# stretch=1 → essa seção recebe todo o espaço vertical sobrando
```

---

## 23. Alinhamentos de layout

Mapa completo dos alinhamentos usados no código.

### Por widget/contexto

| Elemento | Alinhamento |
|----------|-------------|
| Logo no cabeçalho | `Qt.AlignVCenter` |
| Selo "PAINEL OPERACIONAL" | `Qt.AlignLeft` |
| Badge de status (EtiquetaStatus) | `Qt.AlignLeft` |
| Painel de status (lateral) | `Qt.AlignTop` |
| Botões primário/perigo | `Qt.AlignBottom` |
| Layout do badge de status na tabela | `Qt.AlignLeft | Qt.AlignVCenter` |
| Layout do botão de ação | `Qt.AlignRight | Qt.AlignVCenter` |
| Marcador e rótulo dentro do badge | `Qt.AlignVCenter` |
| Valor do mini-card de resumo | `Qt.AlignLeft | Qt.AlignVCenter` |
| Cabeçalho da tabela | `Qt.AlignLeft | Qt.AlignVCenter` |
| Itens de texto na tabela | `Qt.AlignLeft | Qt.AlignVCenter` (padrão) |
| Coluna Acao (célula vazia) | `Qt.AlignRight | Qt.AlignVCenter` |
| `EtiquetaStatus` (QLabel) | `Qt.AlignCenter` |

### Padrão dominante

```python
# Alinhamento padrão de item de tabela (helper _setar_item_texto)
alinhamento: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter
```

> A interface é majoritariamente alinhada à esquerda. `AlignCenter` aparece apenas no badge de status. `AlignRight` aparece apenas em ações e na coluna de ação vazia.

---

## 24. Mapa completo de spacing e margins

Todos os valores de `setSpacing()` e `setContentsMargins()` extraídos do código.

### `setContentsMargins` (padding interno dos layouts)

| Layout / Contexto | L | T | R | B |
|-------------------|---|---|---|---|
| `layout_principal` (janela) | 30 | 26 | 30 | 26 |
| Layout do cabeçalho (`#cabecalhoPainel`) | 28 | 24 | 28 | 24 |
| `layout_marca` (logo + título) | 0 | 0 | 0 | 0 |
| `layout_status` (painel de status lateral) | 18 | 18 | 18 | 18 |
| Layout de controles (`#cartaoPadrao`) | 22 | 20 | 22 | 20 |
| Layout de progresso (`#cartaoPadrao`) | 22 | 20 | 22 | 20 |
| Layout de logs (`#cartaoPadrao`) | 22 | 20 | 22 | 20 |
| `container_layout` (container da tabela) | 8 | 8 | 8 | 8 |
| Layout do badge de status na tabela | 0 | 6 | 0 | 6 |
| `layout_badge` (marcador + texto) | 12 | 6 | 12 | 6 |
| Layout do botão de ação | 0 | 4 | 0 | 4 |
| Mini-card de resumo (`#resumoLogCard`) | 16 | 14 | 16 | 14 |
| `CartaoEstatistica` (componentes.py) | 18 | 18 | 18 | 18 |

### `setSpacing` (gap entre filhos do layout)

| Layout / Contexto | Valor |
|-------------------|-------|
| `layout_principal` (entre blocos principais) | `20px` |
| Layout externo do cabeçalho | `24px` |
| `layout_marca` (logo, divisor, bloco_titulo) | `18px` |
| `bloco_titulo` (selo, título, subtítulo) | `6px` |
| `layout_status` (rótulos dentro do painel lateral) | `8px` |
| Layout de controles | `18px` |
| `descricao` (título + texto + contexto) | `6px` |
| `bloco_botoes` (input + botões) | `12px` |
| `bloco_valor` (rótulo + input) | `4px` |
| Grade de estatísticas (`QGridLayout`) | `18px` |
| `CartaoEstatistica` layout interno | `12px` |
| Layout de progresso | `14px` |
| `topo` (progresso: texto + percentual) | `18px` |
| `bloco_texto` (progresso: título + rótulo) | `6px` |
| Layout de logs | `16px` |
| `cabecalho` (logs: título + stretch) | `18px` |
| `bloco_titulos` (título + subtítulo dos logs) | `6px` |
| `resumo_logs` (mini-cards) | `12px` |
| `paginacao` (botões + rótulos) | `10px` |
| `layout_badge` (marcador + texto no badge) | `7px` |
| Mini-card de resumo | `6px` |

### Padrão identificável

| Categoria | Spacing |
|-----------|---------|
| Entre blocos maiores (seções) | `20px` |
| Entre elementos de um mesmo card | `14–18px` |
| Entre campos de um formulário / grupo | `12px` |
| Entre sub-elementos de um componente | `6–8px` |
| Entre marcador e texto (micro) | `4–7px` |

---

## 25. Resumo dos valores críticos

| Propriedade | Valor |
|-------------|-------|
| Fundo geral | `#F3F7FB` |
| Fundo de card | `#FFFFFF` + borda `#D9E4F0` |
| Border-radius card | `20px` |
| Border-radius cabeçalho | `24px` |
| Border-radius botão primário | `14px` |
| Sombra cor | `rgba(15, 23, 42, 0.094)` = `QColor(15,23,42,24)` |
| Sombra card | blur=24, offsetY=5 |
| Sombra cabeçalho | blur=34, offsetY=10 |
| Fonte principal | Manrope Variable, 10pt global |
| Fonte técnica | Consolas, 10pt |
| Cor primária | `#21478A` |
| Spacing blocos | `20px` |
| Margins janela | `30px` H / `26px` V |
| Linhas por página | `8` |
| Altura de linha tabela | `60px` |
| Altura cabeçalho tabela | `44px` |

---

## 26. Título e Footer Institucional

### Título oficial da aplicação

- Janela principal: `RPA REAJUSTE TABELAS VIGÊNCIA`
- Título visível do cabeçalho: `RPA REAJUSTE TABELAS VIGÊNCIA`
- Subtítulo do cabeçalho: `Painel operacional para cópia, vigência e reajuste em lote no ESL Cloud`

### Footer institucional

O rodapé deve permanecer discreto, legível e sempre no fim do painel principal.

- Bloco esquerdo:
  `RPA REAJUSTE TABELAS VIGÊNCIA`
  `Automação desktop para cópia, vigência e reajuste de tabelas.`
- Bloco direito:
  `Desenvolvido por @valentelucass`
  `Suporte: lucasmac.dev@gmail.com`

### Link oficial de autoria

- O texto `@valentelucass` no footer deve abrir:
  `https://www.linkedin.com/in/dev-lucasandrade/`
