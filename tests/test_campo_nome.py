"""
Teste 2 — Teste Isolado (Campo Nome da Tabela)
Testa o comportamento do campo de busca por nome de forma unitaria:
  - Insercao de valor no campo
  - Validacao de limpeza do campo anterior
  - Validacao de envio correto
  - Cenarios de borda: string vazia, string longa, caracteres especiais
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from tests.utils.mock_navegador import ElementoDOM, NavegadorMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def navegador():
    return NavegadorMock()


@pytest.fixture
def input_pesquisa(navegador):
    """Retorna o elemento input de pesquisa do mock."""
    return navegador._input_pesquisa


@pytest.fixture
def acoes_mock(navegador):
    """Cria um mock de AcoesNavegador com driver real mockado."""
    acoes = MagicMock()
    acoes.driver = navegador

    def limpar_e_digitar(elemento, texto):
        elemento.clear()
        elemento.send_keys(texto)

    acoes.limpar_e_digitar = limpar_e_digitar
    acoes.aguardar_seletor = MagicMock(return_value=navegador._input_pesquisa)
    acoes.aguardar_carregamento_finalizar = MagicMock()
    acoes.clicar_com_seguranca = MagicMock()
    return acoes


# ---------------------------------------------------------------------------
# Teste: Insercao de valor no campo
# ---------------------------------------------------------------------------

class TestInsercaoValorCampo:
    """Testa a insercao de valores no campo de busca."""

    def test_insercao_nome_simples(self, input_pesquisa):
        """Inserir nome simples deve funcionar."""
        input_pesquisa.send_keys("Tabela ABC")
        assert input_pesquisa.valor == "Tabela ABC"

    def test_insercao_nome_com_espacos(self, input_pesquisa):
        """Inserir nome com espacos deve preservar os espacos."""
        input_pesquisa.send_keys("Tabela   Com   Espacos")
        assert input_pesquisa.valor == "Tabela   Com   Espacos"

    def test_insercao_nome_com_numeros(self, input_pesquisa):
        """Inserir nome com numeros deve funcionar."""
        input_pesquisa.send_keys("Tabela 001 Norte")
        assert input_pesquisa.valor == "Tabela 001 Norte"

    def test_insercao_via_acoes_navegador(self, acoes_mock, navegador):
        """Insercao via AcoesNavegador deve limpar e digitar."""
        elemento = navegador._input_pesquisa
        elemento.valor = "valor antigo"

        acoes_mock.limpar_e_digitar(elemento, "Tabela Nova")
        assert elemento.valor == "Tabela Nova"


# ---------------------------------------------------------------------------
# Teste: Limpeza do campo anterior
# ---------------------------------------------------------------------------

class TestLimpezaCampoAnterior:
    """Testa que o campo e limpo corretamente antes de nova insercao."""

    def test_campo_limpo_antes_de_nova_insercao(self, input_pesquisa):
        """Campo deve ser limpo antes de inserir novo valor."""
        input_pesquisa.send_keys("Tabela Antiga")
        assert input_pesquisa.valor == "Tabela Antiga"

        input_pesquisa.clear()
        assert input_pesquisa.valor == ""

        input_pesquisa.send_keys("Tabela Nova")
        assert input_pesquisa.valor == "Tabela Nova"

    def test_limpar_e_digitar_substitui_valor(self, acoes_mock, navegador):
        """limpar_e_digitar deve substituir o valor anterior completamente."""
        elem = navegador._input_pesquisa
        elem.valor = "Valor Residual"

        acoes_mock.limpar_e_digitar(elem, "Novo Valor")
        assert elem.valor == "Novo Valor"
        assert "Residual" not in elem.valor

    def test_limpar_campo_vazio_nao_causa_erro(self, input_pesquisa):
        """Limpar campo ja vazio nao deve causar erro."""
        input_pesquisa.clear()
        assert input_pesquisa.valor == ""

    def test_multiplas_limpezas_consecutivas(self, input_pesquisa):
        """Multiplas limpezas consecutivas devem funcionar."""
        for _ in range(5):
            input_pesquisa.send_keys("Teste")
            input_pesquisa.clear()
            assert input_pesquisa.valor == ""

    def test_nao_mistura_valores_entre_iteracoes(self, acoes_mock, navegador):
        """Valores nao devem vazar entre iteracoes do loop."""
        elem = navegador._input_pesquisa
        nomes = ["Tabela A", "Tabela B", "Tabela C", "Tabela D"]

        for nome in nomes:
            acoes_mock.limpar_e_digitar(elem, nome)
            assert elem.valor == nome, f"Esperado '{nome}', obteve '{elem.valor}'"


# ---------------------------------------------------------------------------
# Teste: Envio correto do valor
# ---------------------------------------------------------------------------

class TestEnvioCorretoValor:
    """Testa que o valor e enviado corretamente para pesquisa."""

    def test_valor_enviado_corresponde_ao_digitado(self, input_pesquisa):
        """O valor no campo deve ser exatamente o que foi digitado."""
        input_pesquisa.send_keys("Tabela Exata 001")
        assert input_pesquisa.valor == "Tabela Exata 001"
        assert input_pesquisa.get_attribute("value") == "Tabela Exata 001"

    def test_valor_preserva_case(self, input_pesquisa):
        """O campo deve preservar maiusculas e minusculas."""
        input_pesquisa.send_keys("TABELA maiuscula")
        assert input_pesquisa.valor == "TABELA maiuscula"

    def test_valor_preserva_acentos(self, input_pesquisa):
        """O campo deve preservar caracteres acentuados."""
        input_pesquisa.send_keys("Tabela São Paulo")
        assert input_pesquisa.valor == "Tabela São Paulo"


# ---------------------------------------------------------------------------
# Teste: String vazia
# ---------------------------------------------------------------------------

class TestStringVazia:
    """Testa comportamento com string vazia."""

    def test_insercao_string_vazia(self, input_pesquisa):
        """Inserir string vazia deve deixar campo vazio."""
        input_pesquisa.send_keys("")
        assert input_pesquisa.valor == ""

    def test_limpar_e_digitar_string_vazia(self, acoes_mock, navegador):
        """limpar_e_digitar com string vazia deve limpar o campo."""
        elem = navegador._input_pesquisa
        elem.valor = "Valor Existente"
        acoes_mock.limpar_e_digitar(elem, "")
        assert elem.valor == ""

    def test_campo_vazio_apos_clear(self, input_pesquisa):
        """Campo deve estar vazio apos clear()."""
        input_pesquisa.send_keys("Algo")
        input_pesquisa.clear()
        assert input_pesquisa.valor == ""
        assert input_pesquisa.get_attribute("value") == ""


# ---------------------------------------------------------------------------
# Teste: String longa
# ---------------------------------------------------------------------------

class TestStringLonga:
    """Testa comportamento com strings longas."""

    def test_insercao_nome_200_caracteres(self, input_pesquisa):
        """Inserir nome com 200 caracteres deve funcionar."""
        nome_longo = "A" * 200
        input_pesquisa.send_keys(nome_longo)
        assert input_pesquisa.valor == nome_longo
        assert len(input_pesquisa.valor) == 200

    def test_insercao_nome_500_caracteres(self, input_pesquisa):
        """Inserir nome com 500 caracteres deve funcionar."""
        nome_longo = "Tabela " + "X" * 493
        input_pesquisa.send_keys(nome_longo)
        assert input_pesquisa.valor == nome_longo

    def test_insercao_nome_1000_caracteres(self, input_pesquisa):
        """Inserir nome com 1000 caracteres (extremo) deve funcionar."""
        nome_longo = "T" * 1000
        input_pesquisa.send_keys(nome_longo)
        assert len(input_pesquisa.valor) == 1000

    def test_limpeza_apos_string_longa(self, input_pesquisa):
        """Campo deve ser completamente limpo apos string longa."""
        input_pesquisa.send_keys("X" * 500)
        input_pesquisa.clear()
        assert input_pesquisa.valor == ""


# ---------------------------------------------------------------------------
# Teste: Caracteres especiais
# ---------------------------------------------------------------------------

class TestCaracteresEspeciais:
    """Testa comportamento com caracteres especiais."""

    @pytest.mark.parametrize("nome", [
        "Tabela São Paulo — Especial",
        "Tabela C&A / Logística",
        "Tabela (Teste) [Brackets]",
        "Tabela <HTML> Tags",
        'Tabela "Aspas Duplas"',
        "Tabela 'Aspas Simples'",
        "Tabela Com Acentuação: éèêë",
        "Tabela @ # $ % &",
        "Tabela ñ ü ö ä",
        "Tabela 日本語",  # caracteres CJK
        "Tabela\tCom\tTab",
        "Tabela\nCom\nNewline",
    ])
    def test_insercao_caracteres_especiais(self, input_pesquisa, nome):
        """Campo deve aceitar e preservar caracteres especiais."""
        input_pesquisa.send_keys(nome)
        assert input_pesquisa.valor == nome

    def test_limpeza_apos_caracteres_especiais(self, input_pesquisa):
        """Campo deve ser limpo corretamente apos caracteres especiais."""
        input_pesquisa.send_keys("Tabela São Paulo — ñ ü")
        input_pesquisa.clear()
        assert input_pesquisa.valor == ""

    def test_substituicao_especial_por_normal(self, acoes_mock, navegador):
        """Substituir valor com caracteres especiais por normal deve funcionar."""
        elem = navegador._input_pesquisa
        acoes_mock.limpar_e_digitar(elem, "Tabela <HTML> &amp;")
        assert elem.valor == "Tabela <HTML> &amp;"

        acoes_mock.limpar_e_digitar(elem, "Tabela Normal")
        assert elem.valor == "Tabela Normal"

    def test_substituicao_normal_por_especial(self, acoes_mock, navegador):
        """Substituir valor normal por caracteres especiais deve funcionar."""
        elem = navegador._input_pesquisa
        acoes_mock.limpar_e_digitar(elem, "Tabela Normal")
        assert elem.valor == "Tabela Normal"

        acoes_mock.limpar_e_digitar(elem, "Tabela São Paulo — ñ")
        assert elem.valor == "Tabela São Paulo — ñ"


# ---------------------------------------------------------------------------
# Teste: Ciclo completo (limpar -> inserir -> validar) repetido
# ---------------------------------------------------------------------------

class TestCicloCompleto:
    """Testa o ciclo completo de uso do campo repetidamente."""

    def test_ciclo_100_iteracoes(self, acoes_mock, navegador):
        """Campo deve funcionar corretamente em 100 iteracoes consecutivas."""
        elem = navegador._input_pesquisa
        nomes = [f"Tabela Loop {i:04d}" for i in range(100)]

        for nome in nomes:
            acoes_mock.limpar_e_digitar(elem, nome)
            assert elem.valor == nome

    def test_ciclo_alternando_tipos(self, acoes_mock, navegador):
        """Campo deve funcionar alternando entre tipos de input."""
        elem = navegador._input_pesquisa
        entradas = [
            "Normal",
            "",
            "A" * 300,
            "Especial ñ ü <>&",
            "123456",
            "   Espacos   ",
            "",
            "Final",
        ]

        for entrada in entradas:
            acoes_mock.limpar_e_digitar(elem, entrada)
            assert elem.valor == entrada
