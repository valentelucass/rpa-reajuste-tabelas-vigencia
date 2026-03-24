"""Integracao do modulo auto delete clientes."""

from .executor import ExecutorAutoDeleteClientes
from .modelos import (
    ModoExecucaoAutoDelete,
    OrdemExecucaoAutoDelete,
    RegistroAutoDelete,
)

__all__ = [
    "ExecutorAutoDeleteClientes",
    "ModoExecucaoAutoDelete",
    "OrdemExecucaoAutoDelete",
    "RegistroAutoDelete",
]
