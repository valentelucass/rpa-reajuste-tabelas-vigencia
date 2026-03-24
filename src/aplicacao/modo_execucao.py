"""
Modos de execucao da automacao RPA.
"""

from enum import Enum


class ModoExecucao(Enum):
    MODO_COMPLETO = "completo"   # Fase 1 + Fase 2
    MODO_FASE1 = "fase1"         # Apenas Fase 1
    MODO_FASE2 = "fase2"         # Apenas Fase 2
