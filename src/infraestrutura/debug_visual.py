"""
Highlight visual de elementos no DOM para debug e demonstração.
Ativado apenas quando config.DEBUG_VISUAL = True.
"""

import time

import config


class DebugVisual:
    """Injeta CSS/JS no browser para destacar elementos interagidos."""

    def __init__(self, driver) -> None:
        self.driver = driver

    def destacar(self, elemento, cor: str = "#E53935", duracao: float = 0.4) -> None:
        if not config.DEBUG_VISUAL:
            return
        try:
            self.driver.execute_script(
                """
                var elem = arguments[0];
                var cor = arguments[1];
                var borda_original = elem.style.border;
                var fundo_original = elem.style.backgroundColor;
                elem.style.border = '3px solid ' + cor;
                elem.style.backgroundColor = 'rgba(229, 57, 53, 0.15)';
                setTimeout(function() {
                    elem.style.border = borda_original;
                    elem.style.backgroundColor = fundo_original;
                }, arguments[2]);
                """,
                elemento, cor, int(duracao * 1000)
            )
            time.sleep(duracao)
        except Exception:
            pass

    def pulsar(self, elemento, repeticoes: int = 2) -> None:
        if not config.DEBUG_VISUAL:
            return
        try:
            for _ in range(repeticoes):
                self.destacar(elemento, "#21478A", 0.2)
                time.sleep(0.1)
        except Exception:
            pass
