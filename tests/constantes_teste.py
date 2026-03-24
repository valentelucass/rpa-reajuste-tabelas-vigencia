"""
Constantes centrais para limitar volume de dados em testes.
Todos os testes devem respeitar esses limites para evitar
poluicao de dados e manter execucoes rapidas.
"""

import os

LIMITE_TESTE_FASE_1: int = 3
LIMITE_TESTE_FASE_2: int = 3
LIMITE_EXCEL_TESTE: int = 3

MODO_TESTE: bool = os.environ.get("RPA_MODO_TESTE", "1") != "0"


def aplicar_limite(dados: list, limite: int = LIMITE_EXCEL_TESTE) -> list:
    """Aplica corte de seguranca nos dados se MODO_TESTE estiver ativo."""
    if MODO_TESTE and len(dados) > limite:
        return dados[:limite]
    return dados
