import importlib


def test_auto_delete_config_carrega_env_da_raiz_do_projeto(monkeypatch):
    monkeypatch.delenv("URL_LOGIN", raising=False)
    monkeypatch.delenv("EMAIL_LOGIN", raising=False)
    monkeypatch.delenv("SENHA_LOGIN", raising=False)

    modulo = importlib.import_module("src.auto_delete_clientes.config")
    modulo = importlib.reload(modulo)

    assert modulo.PROJETO_PAI_DIR.name == "rpa-reajuste-tabelas-vigencia"
    assert modulo.LOGS_DIR.name == "auto_delete"
    assert modulo.LOGS_DIR.parent.name == "logs"
    assert modulo.EXECUCOES_LOG_DIR.parent == modulo.LOGS_DIR
    assert modulo.SCREENSHOTS_DIR.parent == modulo.LOGS_DIR
    assert modulo.ARQUIVO_REPROCESSAMENTO.parent == modulo.LOGS_DIR
    assert modulo.URL_LOGIN == "https://rodogarcia.eslcloud.com.br/users/sign_in"
    assert modulo.EMAIL_LOGIN
