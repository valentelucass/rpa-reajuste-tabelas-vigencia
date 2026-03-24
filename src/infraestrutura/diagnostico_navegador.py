"""
Helpers para identificar falhas fatais relacionadas ao navegador/WebDriver.
"""

from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException, WebDriverException


# Nomes de tipos de excecao que indicam perda de conexao com o navegador.
# Usa nomes (strings) para evitar importar urllib3/requests diretamente.
_TIPOS_CONEXAO_PERDIDA = frozenset({
    "ConnectionRefusedError",
    "MaxRetryError",
    "NewConnectionError",
    "RemoteDisconnected",
    "ProtocolError",
})

# Fragmentos de mensagem que indicam navegador encerrado.
_SINAIS_MENSAGEM = (
    "invalid session id",
    "no such window",
    "target window already closed",
    "web view not found",
    "chrome not reachable",
    "session deleted because of page crash",
    "disconnected",
    "connection refused",
    "failed to establish a new connection",
    "max retries exceeded",
    "remotedisconnected",
    "an existing connection was forcibly closed",
    "no connection could be made",
)


def erro_indica_navegador_encerrado(erro: Exception) -> bool:
    """Retorna True quando a excecao indica sessao perdida ou janela fechada."""
    # 1. Checagem direta de tipo Selenium
    if isinstance(erro, (InvalidSessionIdException, NoSuchWindowException)):
        return True

    # 2. Checagem por nome de tipo (conexao perdida)
    if type(erro).__name__ in _TIPOS_CONEXAO_PERDIDA:
        return True

    # 3. Checar cadeia de excecoes (__cause__ / __context__)
    causa = getattr(erro, "__cause__", None) or getattr(erro, "__context__", None)
    if causa is not None and type(causa).__name__ in _TIPOS_CONEXAO_PERDIDA:
        return True

    # 4. Checagem por mensagem
    mensagem = str(erro).lower()
    if any(sinal in mensagem for sinal in _SINAIS_MENSAGEM):
        return True

    # 5. WebDriverException com mensagem generica
    if isinstance(erro, WebDriverException):
        return any(sinal in mensagem for sinal in _SINAIS_MENSAGEM)

    return False
