from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException, WebDriverException

from src.infraestrutura.diagnostico_navegador import erro_indica_navegador_encerrado


def test_retorna_true_para_invalid_session():
    assert erro_indica_navegador_encerrado(InvalidSessionIdException("invalid session id"))


def test_retorna_true_para_no_such_window():
    assert erro_indica_navegador_encerrado(NoSuchWindowException("no such window"))


def test_retorna_true_para_mensagem_de_sessao_perdida():
    erro = WebDriverException("chrome not reachable")
    assert erro_indica_navegador_encerrado(erro)


def test_retorna_false_para_excecao_comum():
    assert not erro_indica_navegador_encerrado(RuntimeError("falha comum"))


def test_retorna_false_para_webdriver_sem_sinal_de_sessao_perdida():
    erro = WebDriverException("element click intercepted")
    assert not erro_indica_navegador_encerrado(erro)
