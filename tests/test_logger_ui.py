"""
Testes unitários para GerenciadorLogsUi e EntradaLog.
Sem dependências externas — apenas lógica pura.
"""

import pytest
from src.ui.logger_ui import EntradaLog, GerenciadorLogsUi


# ---------------------------------------------------------------------------
# Testes — EntradaLog
# ---------------------------------------------------------------------------

class TestEntradaLog:
    def test_chave_automatica(self):
        entrada = EntradaLog(fase=1, indice=1, nome_tabela="Tabela X", status="Sucesso")
        assert entrada.chave == "f1_Tabela X"

    def test_chave_customizada(self):
        entrada = EntradaLog(fase=1, indice=1, nome_tabela="T", status="Erro", chave="minha_chave")
        assert entrada.chave == "minha_chave"

    def test_horario_preenchido(self):
        entrada = EntradaLog(fase=1, indice=1, nome_tabela="T", status="Processando")
        assert len(entrada.horario) == 8  # HH:MM:SS


# ---------------------------------------------------------------------------
# Testes — GerenciadorLogsUi
# ---------------------------------------------------------------------------

class TestGerenciadorLogsUi:
    def _gerenciador(self, por_pagina: int = 8):
        return GerenciadorLogsUi(linhas_por_pagina=por_pagina)

    def _entrada(self, nome: str, fase: int = 1, status: str = "Processando") -> EntradaLog:
        return EntradaLog(fase=fase, indice=1, nome_tabela=nome, status=status)

    def test_adicionar_nova_entrada(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1"))
        assert g.total_registros == 1

    def test_atualiza_entrada_existente(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1", status="Processando"))
        g.adicionar_ou_atualizar(self._entrada("T1", status="Sucesso"))
        assert g.total_registros == 1
        assert g.pagina_atual()[0].status == "Sucesso"

    def test_novas_entradas_no_topo(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1"))
        g.adicionar_ou_atualizar(self._entrada("T2"))
        pagina = g.pagina_atual()
        assert pagina[0].nome_tabela == "T2"
        assert pagina[1].nome_tabela == "T1"

    def test_adicionar_sistema(self):
        g = self._gerenciador()
        g.adicionar_sistema("Mensagem de sistema")
        assert g.total_registros == 1
        assert g.pagina_atual()[0].status == "Sistema"
        assert g.pagina_atual()[0].nome_tabela == "Sistema"

    def test_limpar(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1"))
        g.limpar()
        assert g.total_registros == 0
        assert g.numero_pagina == 1

    def test_paginacao_total_paginas(self):
        g = self._gerenciador(por_pagina=3)
        for i in range(7):
            g.adicionar_ou_atualizar(self._entrada(f"Tabela {i}", fase=i + 1))
        assert g.total_paginas() == 3

    def test_paginacao_navegar(self):
        g = self._gerenciador(por_pagina=3)
        for i in range(6):
            g.adicionar_ou_atualizar(self._entrada(f"Tabela {i}", fase=i + 1))
        assert g.numero_pagina == 1
        g.proxima_pagina()
        assert g.numero_pagina == 2
        g.proxima_pagina()
        assert g.numero_pagina == 2  # não ultrapassa o total
        g.pagina_anterior()
        assert g.numero_pagina == 1
        g.pagina_anterior()
        assert g.numero_pagina == 1  # não vai abaixo de 1

    def test_pagina_atual_retorna_slice(self):
        g = self._gerenciador(por_pagina=3)
        for i in range(5):
            g.adicionar_ou_atualizar(self._entrada(f"T{i}", fase=i + 1))
        pagina = g.pagina_atual()
        assert len(pagina) == 3

    def test_contar_por_status(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1", status="Sucesso"))
        g.adicionar_ou_atualizar(self._entrada("T2", status="Sucesso"))
        g.adicionar_ou_atualizar(self._entrada("T3", status="Erro"))
        assert g.contar_por_status("Sucesso") == 2
        assert g.contar_por_status("Erro") == 1
        assert g.contar_por_status("Processando") == 0

    def test_total_paginas_vazio(self):
        g = self._gerenciador()
        assert g.total_paginas() == 1

    def test_ir_para_pagina_invalida(self):
        g = self._gerenciador(por_pagina=2)
        for i in range(4):
            g.adicionar_ou_atualizar(self._entrada(f"T{i}", fase=i + 1))
        g.ir_para_pagina(99)
        assert g.numero_pagina == g.total_paginas()
        g.ir_para_pagina(-5)
        assert g.numero_pagina == 1

    def test_filtra_por_fase_tipo_execucao_e_reprocessamento(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="T1",
                status="Erro",
                fase_execucao="fase_1",
                tipo_execucao="normal",
                reprocessado=False,
            )
        )
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=2,
                indice=2,
                nome_tabela="T2",
                status="Sucesso",
                fase_execucao="fase_2",
                tipo_execucao="reprocessamento",
                reprocessado=True,
            )
        )
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=2,
                indice=3,
                nome_tabela="T3",
                status="Erro",
                fase_execucao="fase_2",
                tipo_execucao="reprocessamento",
                reprocessado=True,
            )
        )

        g.definir_filtros(
            fase="fase_2",
            tipo_execucao="reprocessamento",
            filtro_reprocessamento="reprocessados_erro",
        )

        pagina = g.pagina_atual()
        assert len(pagina) == 1
        assert pagina[0].nome_tabela == "T3"

    def test_filtro_apenas_falhas_inclui_interrompido(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1", fase=1, status="Erro"))
        g.adicionar_ou_atualizar(self._entrada("T2", fase=1, status="Interrompido"))
        g.adicionar_ou_atualizar(self._entrada("T3", fase=1, status="Sucesso"))

        g.definir_filtros(filtro_reprocessamento="apenas_falhas")

        nomes = {entrada.nome_tabela for entrada in g.pagina_atual()}
        assert nomes == {"T1", "T2"}

    def test_busca_entrada_erro_considera_fase_quando_informada(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1", fase=1, status="Erro"))
        g.adicionar_ou_atualizar(self._entrada("T1", fase=2, status="Erro"))

        entrada = g.buscar_entrada_erro("T1", fase=2)

        assert entrada is not None
        assert entrada.fase == 2

    def test_busca_entrada_reprocessavel_aceita_status_interrompido(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1", fase=1, status="Interrompido"))

        entrada = g.buscar_entrada_reprocessavel("T1", fase=1)

        assert entrada is not None
        assert entrada.status == "Interrompido"

    def test_marcar_processando_como_interrompido_atualiza_apenas_execucao_alvo(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="T1",
                status="Processando",
                chave="exec7_f1_idx1_T1",
            )
        )
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=2,
                nome_tabela="T2",
                status="Processando",
                chave="exec8_f1_idx2_T2",
            )
        )

        total = g.marcar_processando_como_interrompido("exec7_")

        assert total == 1
        entrada_alvo = next(r for r in g.pagina_atual() if r.chave == "exec7_f1_idx1_T1")
        entrada_outra = next(r for r in g.pagina_atual() if r.chave == "exec8_f1_idx2_T2")
        assert entrada_alvo.status == "Interrompido"
        assert entrada_outra.status == "Processando"

    def test_obter_falhas_exportaveis_retorna_erros_e_interrompidos(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(self._entrada("T1", fase=1, status="Erro"))
        g.adicionar_ou_atualizar(self._entrada("T2", fase=1, status="Interrompido"))
        g.adicionar_ou_atualizar(self._entrada("T3", fase=1, status="Sucesso"))

        falhas = g.obter_falhas_exportaveis()

        nomes = {entrada.nome_tabela for entrada in falhas}
        assert nomes == {"T1", "T2"}

    def test_obter_falhas_exportaveis_respeita_filtros_quando_solicitado(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="T1",
                status="Erro",
                fase_execucao="fase_1",
            )
        )
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=2,
                indice=2,
                nome_tabela="T2",
                status="Interrompido",
                fase_execucao="fase_2",
            )
        )

        g.definir_filtros(fase="fase_2", filtro_reprocessamento="apenas_falhas")

        falhas = g.obter_falhas_exportaveis(aplicar_filtros=True)

        assert len(falhas) == 1
        assert falhas[0].nome_tabela == "T2"

    def test_filtra_por_processo(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="Tabela Principal",
                status="Sucesso",
                processo="reajuste_tabelas",
            )
        )
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=2,
                nome_tabela="Cliente Auto Delete",
                status="Erro",
                processo="auto_delete_clientes",
            )
        )

        g.definir_filtros(processo="auto_delete_clientes")

        pagina = g.pagina_atual()
        assert len(pagina) == 1
        assert pagina[0].nome_tabela == "Cliente Auto Delete"

    def test_entrada_auto_delete_define_fase_execucao_separada(self):
        entrada = EntradaLog(
            fase=3,
            indice=2,
            nome_tabela="Cliente Auto Delete",
            status="Sucesso",
            processo="auto_delete_clientes",
        )

        assert entrada.fase_execucao == "auto_delete"

    def test_filtra_por_fase_auto_delete(self):
        g = self._gerenciador()
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=3,
                indice=2,
                nome_tabela="Cliente Auto Delete",
                status="Sucesso",
                processo="auto_delete_clientes",
            )
        )
        g.adicionar_ou_atualizar(
            EntradaLog(
                fase=1,
                indice=1,
                nome_tabela="Tabela Principal",
                status="Sucesso",
                processo="reajuste_tabelas",
            )
        )

        g.definir_filtros(fase="auto_delete")

        pagina = g.pagina_atual()
        assert len(pagina) == 1
        assert pagina[0].nome_tabela == "Cliente Auto Delete"
