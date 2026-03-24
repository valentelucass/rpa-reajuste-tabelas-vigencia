"""
Ponto de entrada da aplicação desktop RPA Tabela Cliente Por Nome.
Responsabilidade: subir o Qt, configurar fonte e ícone, abrir o painel.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from src.infraestrutura.caminhos import PUBLIC_DIR
from src.ui.ui_main import JanelaPainelAutomacao


def _configurar_fonte_aplicacao(app: QApplication) -> None:
    """Carrega a fonte Manrope e define como fonte padrão do app."""
    caminho_fonte = PUBLIC_DIR / "fonts" / "Manrope-Variable.ttf"
    if caminho_fonte.exists():
        identificador = QFontDatabase.addApplicationFont(str(caminho_fonte))
        familias = QFontDatabase.applicationFontFamilies(identificador)
        if familias:
            app.setFont(QFont(familias[0], 10))
            return
    # Fallback para fontes do sistema
    for fonte_fallback in ["Aptos", "Bahnschrift", "Segoe UI"]:
        app.setFont(QFont(fonte_fallback, 10))
        break


def _configurar_icone_aplicacao(app: QApplication) -> None:
    """Define o ícone da aplicação a partir do arquivo em public/."""
    caminho_icone = PUBLIC_DIR / "app-icon.ico"
    if caminho_icone.exists():
        app.setWindowIcon(QIcon(str(caminho_icone)))


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    _configurar_fonte_aplicacao(app)
    _configurar_icone_aplicacao(app)

    janela = JanelaPainelAutomacao()
    janela.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
