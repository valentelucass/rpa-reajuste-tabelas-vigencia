def test_importa_automacao_sem_erros():
    from src.aplicacao.automacao_tabela_cliente import AutomacaoTabelaCliente

    assert AutomacaoTabelaCliente is not None
