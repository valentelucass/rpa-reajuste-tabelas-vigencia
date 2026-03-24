"""
Componentes visuais reutilizáveis da interface.
Paleta de cores, EtiquetaStatus e CartaoEstatistica.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


# ---------------------------------------------------------------------------
# Paleta de cores
# ---------------------------------------------------------------------------

PALETA_CORES: dict[str, str] = {
    "primaria":              "#21478A",
    "secundaria":            "#2B89D9",
    "fundo":                 "#F3F7FB",
    "sucesso":               "#1F7A63",
    "perigo":                "#B55045",
    "branco":                "#FFFFFF",
    "texto_padrao":          "#0F172A",
    "texto_mutado":          "#64748B",
    "texto_sutil":           "#94A3B8",
    "borda":                 "#D9E4F0",
    "borda_forte":           "#C6D6E7",
    "superficie_secundaria": "#F7FAFD",
    "info":                  "#2B89D9",
}


# ---------------------------------------------------------------------------
# Mapa de cores por status
# ---------------------------------------------------------------------------

MAPA_CORES_STATUS: dict[str, tuple[str, str, str]] = {
    # (fundo, texto, borda)
    "Parado":      ("#F8FAFC", "#475569", "#CBD5E1"),
    "Parando":     ("#FFF7ED", "#9A3412", "#FDBA74"),
    "Executando":  ("#E8F1FF", "#1D4ED8", "#BFDBFE"),
    "Erro":        ("#FEF2F2", "#B42318", "#FECACA"),
    "Sucesso":     ("#ECFDF3", "#166534", "#BBF7D0"),
    "Processando": ("#EFF6FF", "#1E40AF", "#BFDBFE"),
    "Interrompido": ("#FFF7ED", "#9A3412", "#FED7AA"),
}

_COR_STATUS_FALLBACK = ("#F8FAFC", "#0F172A", "#D9E4F0")


# ---------------------------------------------------------------------------
# Cores por tipo de erro (para badges na tabela de logs)
# ---------------------------------------------------------------------------

MAPA_CORES_TIPO_ERRO: dict[str, tuple[str, str, str]] = {
    # tipo_erro: (fundo, texto, borda)
    "nao_encontrado":   ("#FEF2F2", "#B42318", "#FECACA"),
    "timeout":          ("#FFFBEB", "#92400E", "#FDE68A"),
    "erro_clique":      ("#FFFBEB", "#92400E", "#FDE68A"),
    "erro_dom":         ("#FFFBEB", "#92400E", "#FDE68A"),
    "sessao_invalida":  ("#FEF2F2", "#991B1B", "#FECACA"),
    "erro_desconhecido": ("#F8FAFC", "#475569", "#CBD5E1"),
}

ICONES_TIPO_ERRO: dict[str, str] = {
    "nao_encontrado":   "\u274C",   # ❌
    "timeout":          "\u26A0\uFE0F",   # ⚠️
    "erro_clique":      "\u26A0\uFE0F",
    "erro_dom":         "\u26A0\uFE0F",
    "sessao_invalida":  "\u26A0\uFE0F",
    "erro_desconhecido": "\u2753",  # ❓
}


# ---------------------------------------------------------------------------
# EtiquetaStatus
# ---------------------------------------------------------------------------

class EtiquetaStatus(QLabel):
    """Badge arredondado de status com cor semântica."""

    def __init__(self, texto: str = "Parado") -> None:
        super().__init__(texto)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(118)
        self.setFixedHeight(34)
        self.atualizar(texto)

    def atualizar(self, texto: str) -> None:
        fundo, cor_texto, borda = MAPA_CORES_STATUS.get(texto, _COR_STATUS_FALLBACK)
        self.setText(texto)
        self.setStyleSheet(
            f"QLabel {{"
            f"  background: {fundo};"
            f"  color: {cor_texto};"
            f"  border: 1px solid {borda};"
            f"  border-radius: 17px;"
            f"  padding: 6px 14px;"
            f"  font-size: 12px;"
            f"  font-weight: 700;"
            f"}}"
        )


# ---------------------------------------------------------------------------
# CartaoEstatistica
# ---------------------------------------------------------------------------

class CartaoEstatistica(QFrame):
    """Card de KPI com marcador colorido, número grande e rótulo de apoio."""

    def __init__(
        self,
        titulo: str,
        cor_destaque: str,
        valor_inicial: int | str = 0,
        detalhe: str = ""
    ) -> None:
        super().__init__()
        self.setObjectName("cartaoEstatistica")
        self.setMinimumHeight(138)

        conteudo = QVBoxLayout(self)
        conteudo.setContentsMargins(18, 18, 18, 18)
        conteudo.setSpacing(12)

        # Topo: marcador + título
        topo = QHBoxLayout()
        topo.setSpacing(8)

        marcador = QFrame()
        marcador.setFixedSize(10, 10)
        marcador.setStyleSheet(
            f"QFrame {{ background: {cor_destaque}; border-radius: 5px; border: none; }}"
        )

        rotulo_titulo = QLabel(titulo.upper())
        rotulo_titulo.setStyleSheet(
            f"color: {PALETA_CORES['texto_mutado']}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 0.4px;"
        )

        topo.addWidget(marcador, 0, Qt.AlignVCenter)
        topo.addWidget(rotulo_titulo, 1, Qt.AlignVCenter)
        conteudo.addLayout(topo)

        # Valor
        self._rotulo_valor = QLabel(self._formatar_valor(valor_inicial))
        self._rotulo_valor.setStyleSheet(
            f"color: {PALETA_CORES['texto_padrao']}; font-size: 30px; font-weight: 800;"
        )
        conteudo.addWidget(self._rotulo_valor)

        # Detalhe
        self._rotulo_detalhe = QLabel(detalhe)
        self._rotulo_detalhe.setStyleSheet(
            f"color: {PALETA_CORES['texto_sutil']}; font-size: 12px; font-weight: 400;"
        )
        conteudo.addWidget(self._rotulo_detalhe)
        conteudo.addStretch()
        self._rotulo_titulo = rotulo_titulo

    def atualizar_valor(self, valor: int | str) -> None:
        self._rotulo_valor.setText(self._formatar_valor(valor))

    def atualizar_titulo(self, titulo: str) -> None:
        self._rotulo_titulo.setText(titulo.upper())

    def atualizar_detalhe(self, detalhe: str) -> None:
        self._rotulo_detalhe.setText(detalhe)

    @staticmethod
    def _formatar_valor(valor: int | str) -> str:
        if isinstance(valor, int):
            return f"{valor:,}".replace(",", ".")
        return str(valor)
