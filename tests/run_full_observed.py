import traceback

from src.aplicacao.automacao_tabela_cliente import AutomacaoTabelaCliente
from tests.constantes_teste import LIMITE_TESTE_FASE_1, LIMITE_TESTE_FASE_2
from tests.utils.excel_limitado_teste import criar_excel_limitado

caminho_excel = criar_excel_limitado("REAJUSTE.xlsx")
inst = AutomacaoTabelaCliente(caminho_excel)
print(f"RUN_ID={inst.run_id}", flush=True)
print("MODO_TESTE=true", flush=True)
print(f"LIMITE_FASE_1={LIMITE_TESTE_FASE_1}", flush=True)
print(f"LIMITE_FASE_2={LIMITE_TESTE_FASE_2}", flush=True)
print(f"EXCEL_TESTE={caminho_excel}", flush=True)
try:
    inst.executar()
    print("STATUS=SUCCESS", flush=True)
except Exception as exc:
    print(f"STATUS=ERROR:{exc!r}", flush=True)
    traceback.print_exc()
    raise
finally:
    caminho_excel.unlink(missing_ok=True)
