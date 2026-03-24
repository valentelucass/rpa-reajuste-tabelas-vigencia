"""Simula comportamento humano com delays aleatorios entre acoes."""

import random
import time


def atraso_humano(minimo: float = 0.3, maximo: float = 1.2) -> None:
    """Pausa por um tempo aleatorio entre minimo e maximo segundos."""
    time.sleep(random.uniform(minimo, maximo))
