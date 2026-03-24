"""Helpers de import seguro para execucao standalone do auto delete."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def carregar_modulo_local(nome: str):
    """Carrega um modulo local sem poluir nomes globais do projeto."""
    nome_modulo = f"auto_delete_clientes_{nome}"
    if nome_modulo in sys.modules:
        return sys.modules[nome_modulo]

    caminho = BASE_DIR / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(nome_modulo, caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"Nao foi possivel carregar o modulo local '{nome}'.")

    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome_modulo] = modulo
    spec.loader.exec_module(modulo)
    return modulo
