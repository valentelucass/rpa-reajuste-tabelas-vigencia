"""
Script independente para exclusao de registros de tabelas de cliente.
Le um Excel com (nome_cliente, data_vigencia) e exclui registros correspondentes
no sistema ESL Cloud via Selenium.

Gera automaticamente reprocessar.xlsx com registros que falharam.

Uso:
    cd auto_delete_clientes
    python main.py
    python main.py --arquivo caminho/para/planilha.xlsx
    python main.py --headless
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from selenium.webdriver.common.by import By

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from auto_delete_compat import carregar_modulo_local

    config = carregar_modulo_local("config")
    from acoes_navegador import AcoesNavegador
    from leitor_excel import LeitorExcelExclusao, RegistroExclusao, detectar_arquivo_excel
    from logger_config import configurar_logger
    from navegador import FabricaNavegador
    from pagina_exclusao import NavegadorFechadoError, PaginaExclusao
    from pagina_login import PaginaLogin
    from utils.atraso_humano import atraso_humano
else:
    from . import config
    from .acoes_navegador import AcoesNavegador
    from .leitor_excel import LeitorExcelExclusao, RegistroExclusao, detectar_arquivo_excel
    from .logger_config import configurar_logger
    from .navegador import FabricaNavegador
    from .pagina_exclusao import NavegadorFechadoError, PaginaExclusao
    from .pagina_login import PaginaLogin
    from .utils.atraso_humano import atraso_humano


# ------------------------------------------------------------------
# Reprocessamento
# ------------------------------------------------------------------

@dataclass
class RegistroErro:
    """Registro que falhou e deve ir para reprocessar.xlsx."""
    nome_cliente: str
    data_vigencia: str
    motivo: str


def salvar_reprocessamento(erros: list[RegistroErro], caminho: Path, logger) -> None:
    """Gera reprocessar.xlsx com os registros que falharam."""
    if not erros:
        # Se nao ha erros, remover arquivo antigo se existir
        if caminho.exists():
            caminho.unlink()
        return

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Reprocessar"
    ws.append(["NOME DA TABELA", "DATA VIGENCIA", "MOTIVO"])

    for erro in erros:
        ws.append([erro.nome_cliente, erro.data_vigencia, erro.motivo])

    wb.save(str(caminho))
    wb.close()
    logger.info(f"Arquivo de reprocessamento gerado: {caminho} ({len(erros)} registros)")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    # Argumentos CLI
    parser = argparse.ArgumentParser(description="Exclusao automatica de tabelas de cliente")
    parser.add_argument(
        "--arquivo",
        default=None,
        help="Caminho para o arquivo Excel (padrao: auto-detecta primeiro .xlsx em data/)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executar o navegador em modo headless",
    )
    args = parser.parse_args()

    if args.headless:
        config.HEADLESS = True

    # Logger (novo log a cada execucao, apaga antigos)
    logger = configurar_logger()
    logger.info("=" * 60)
    logger.info("INICIO - Script de Exclusao de Tabelas de Cliente")
    logger.info("=" * 60)

    # Resolver caminho do Excel
    if args.arquivo:
        caminho_excel = Path(args.arquivo)
    else:
        try:
            caminho_excel = detectar_arquivo_excel(config.DATA_DIR)
            logger.info(f"Arquivo auto-detectado: {caminho_excel.name}")
        except FileNotFoundError as erro:
            logger.error(str(erro))
            sys.exit(1)

    # Ler Excel
    logger.info(f"Lendo arquivo: {caminho_excel}")
    leitor = LeitorExcelExclusao(caminho_excel, logger)
    try:
        leitor.validar()
        registros = leitor.ler()
    except Exception as erro:
        logger.error(f"Erro ao ler Excel: {erro}")
        sys.exit(1)

    if not registros:
        logger.warning("Nenhum registro encontrado no Excel. Encerrando.")
        sys.exit(0)

    total = len(registros)
    logger.info(f"Total de registros para processar: {total}")

    # Rastreamento de resultados
    resultados = {"sucesso": 0, "erro": 0}
    erros_reprocessar: list[RegistroErro] = []

    # Criar navegador
    driver = None
    try:
        logger.info("Iniciando navegador...")
        driver = FabricaNavegador.criar()
        acoes = AcoesNavegador(driver, logger)

        # Login
        pagina_login = PaginaLogin(acoes, logger)
        pagina_login.abrir()
        pagina_login.autenticar()

        # Navegar para tabelas de cliente
        pagina = PaginaExclusao(acoes, logger)
        pagina.acessar_tabelas_cliente()

        # Configurar filtros uma unica vez (filial, ativo=Sim, data vigencia)
        pagina.configurar_filtros_iniciais(
            registros[0].data_inicio, registros[0].data_fim
        )

        # Processar cada registro em ordem reversa (ultima linha primeiro)
        registros_ordenados = list(reversed(registros))
        for i, registro in enumerate(registros_ordenados, 1):
            # Verificar se o navegador ainda esta aberto
            try:
                pagina.verificar_navegador_aberto()
            except NavegadorFechadoError:
                # Marcar restantes como erro
                for r in registros_ordenados[i - 1:]:
                    erros_reprocessar.append(RegistroErro(
                        nome_cliente=r.nome_cliente,
                        data_vigencia=f"{r.data_inicio} - {r.data_fim}",
                        motivo="Navegador fechado",
                    ))
                    resultados["erro"] += 1
                break

            logger.info("-" * 40)
            logger.info(f"[{i}/{total}] Buscando cliente: {registro.nome_cliente}")

            try:
                resultado = pagina.excluir_registro(registro.nome_cliente)

                if resultado == "sucesso":
                    resultados["sucesso"] += 1
                elif resultado == "ja_processado":
                    resultados["sucesso"] += 1
                elif resultado == "nao_encontrado":
                    resultados["sucesso"] += 1
                    logger.info(
                        f"[{i}/{total}] Cliente '{registro.nome_cliente}' nao encontrado; "
                        "considerando como ja excluido"
                    )
                else:  # erro_exclusao
                    resultados["erro"] += 1
                    erros_reprocessar.append(RegistroErro(
                        nome_cliente=registro.nome_cliente,
                        data_vigencia=f"{registro.data_inicio} - {registro.data_fim}",
                        motivo="Erro ao excluir",
                    ))

            except NavegadorFechadoError:
                resultados["erro"] += 1
                erros_reprocessar.append(RegistroErro(
                    nome_cliente=registro.nome_cliente,
                    data_vigencia=f"{registro.data_inicio} - {registro.data_fim}",
                    motivo="Navegador fechado",
                ))
                break
            except Exception as erro:
                resultados["erro"] += 1
                logger.error(f"[{i}/{total}] ERRO: {registro.nome_cliente} - {erro}")
                acoes.salvar_screenshot(f"erro_{registro.nome_cliente}")
                erros_reprocessar.append(RegistroErro(
                    nome_cliente=registro.nome_cliente,
                    data_vigencia=f"{registro.data_inicio} - {registro.data_fim}",
                    motivo=f"Erro ao excluir",
                ))
            finally:
                # Bloqueio entre registros: fechar popups pendentes + aguardar estabilidade
                try:
                    logger.info("Aguardando finalizacao completa antes de continuar")
                    # Fechar qualquer SweetAlert pendente (sucesso ou erro)
                    try:
                        popup_pendente = pagina._encontrar_popup_swal_visivel()
                        if popup_pendente:
                            logger.warning("Popup SweetAlert pendente detectado entre registros, fechando...")
                            try:
                                botao = popup_pendente.find_element(
                                    By.CSS_SELECTOR, "button.swal2-confirm"
                                )
                                acoes.clicar_com_seguranca(botao)
                                acoes.aguardar_invisibilidade_css("div.swal2-popup", timeout=5)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    acoes.aguardar_tabela_estavel(timeout=10)
                except Exception:
                    pass
                try:
                    pagina.limpar_campo_nome()
                except Exception:
                    pass
                logger.info("Indo para proximo nome")
                atraso_humano()

        # Gerar arquivo de reprocessamento
        caminho_reprocessar = config.ARQUIVO_REPROCESSAMENTO
        salvar_reprocessamento(erros_reprocessar, caminho_reprocessar, logger)

        # Resumo final
        logger.info("=" * 60)
        logger.info("Processamento finalizado")
        logger.info(f"  Total processados: {total}")
        logger.info(f"  Total sucesso: {resultados['sucesso']}")
        logger.info(f"  Total erro: {resultados['erro']}")
        logger.info("=" * 60)

    except NavegadorFechadoError:
        # Gerar reprocessamento mesmo em parada por navegador fechado
        caminho_reprocessar = config.ARQUIVO_REPROCESSAMENTO
        salvar_reprocessamento(erros_reprocessar, caminho_reprocessar, logger)
    except Exception as erro:
        logger.critical(f"Erro critico: {erro}")
        if driver:
            try:
                AcoesNavegador(driver, logger).salvar_screenshot("erro_critico")
            except Exception:
                pass
        # Gerar reprocessamento com o que tem
        caminho_reprocessar = config.ARQUIVO_REPROCESSAMENTO
        salvar_reprocessamento(erros_reprocessar, caminho_reprocessar, logger)
        sys.exit(1)
    finally:
        if driver:
            try:
                logger.info("Fechando navegador...")
                driver.quit()
            except Exception:
                pass

    logger.info("Script finalizado com sucesso.")


if __name__ == "__main__":
    main()
