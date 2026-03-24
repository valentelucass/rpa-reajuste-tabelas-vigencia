# RPA — Reajuste de Tabelas por Nome

Automação desktop para duplicação e reajuste em lote de tabelas de cliente no sistema ESL Cloud. Combina **Selenium** (automação web) com **PySide6** (interface gráfica) para oferecer um painel operacional completo com monitoramento em tempo real.

---

## Pré-requisitos

| Requisito | Versão mínima |
|-----------|--------------|
| Python | 3.12+ |
| Google Chrome ou Microsoft Edge | Qualquer versão recente |
| ChromeDriver / EdgeDriver | Compatível com o navegador instalado |

---

## Instalação

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd rpa-tabela-cliente-por-nome

# Instale as dependências
pip install -r requirements.txt
```

**Dependências principais:**
- `selenium>=4.29` — automação do navegador
- `PySide6>=6.8` — interface gráfica Qt
- `openpyxl>=3.1` — leitura do Excel

---

## Configuração

Copie o arquivo `.env.example` (ou crie o `.env`) na raiz do projeto:

```env
EMAIL_LOGIN=seu.email@empresa.com.br
SENHA_LOGIN=SuaSenha
URL_LOGIN=https://sistema.eslcloud.com.br/users/sign_in

# Comportamento
HEADLESS=false
DEBUG_VISUAL=true
CONFIRMAR_FINAL=false

# Timeouts (segundos)
TIMEOUT=30
PAGE_LOAD_TIMEOUT=60
TIMEOUT_COPIA_FINALIZADA=600
INTERVALO_LOG_PROGRESSO_POPUP=30
```

| Variável | Descrição |
|----------|-----------|
| `EMAIL_LOGIN` | E-mail de acesso ao ESL Cloud |
| `SENHA_LOGIN` | Senha de acesso ao ESL Cloud |
| `URL_LOGIN` | URL da página de login |
| `HEADLESS` | `true` para rodar sem abrir janela do navegador |
| `DEBUG_VISUAL` | `true` para exibir destaque vermelho nos cliques |
| `CONFIRMAR_FINAL` | `true` para exigir confirmação manual ao final |
| `TIMEOUT` | Tempo máximo de espera por elemento (segundos) |
| `PAGE_LOAD_TIMEOUT` | Tempo máximo de carregamento de página |
| `TIMEOUT_COPIA_FINALIZADA` | Tempo máximo para aguardar duplicação |
| `INTERVALO_LOG_PROGRESSO_POPUP` | Intervalo dos logs de progresso durante a espera do popup |

---

## Formato do Excel

O arquivo Excel deve ter **duas abas**:

### Aba 1 — Tabelas a processar

| NOME DA TABELA | DATA VIGÊNCIA | PERCENTUAL |
|----------------|--------------|------------|
| Tabela Cliente ABC | 01/04/2026 - 31/03/2027 | 9,80% |
| Tabela Cliente XYZ | 01/04/2026 - 31/03/2027 | 9,80% |

- **NOME DA TABELA**: nome exato da tabela original no sistema (sem "- Cópia")
- **DATA VIGÊNCIA**: intervalo no formato `DD/MM/AAAA - DD/MM/AAAA`
- **PERCENTUAL**: percentual de reajuste (ex: `9,80%` ou `9.8`)

### Aba 2 — Componentes de reajuste

| ABA | NOME DA TAXA |
|-----|-------------|
| Taxas | Taxa de Administração |
| Excessos | Excesso de Peso |
| Adicionais | Seguro |

- **ABA**: identifica o grupo — `Taxas`, `Excessos` ou `Adicionais`
- **NOME DA TAXA**: texto exato do item no Select2 do sistema

---

## Como usar

```bash
python main.py
```

A interface abre maximizada.

1. **Selecionar Excel** — clique para escolher o arquivo Excel de entrada
2. **Iniciar Automação** — dispara o robô em thread separada
3. **Parar** — solicita interrupção segura (aguarda a iteração atual terminar)

O painel exibe em tempo real:
- Contadores de Fase 1 (cópias criadas) e Fase 2 (reajustes aplicados)
- Barra de progresso geral
- Histórico paginado de cada tabela processada (status, horário, detalhe)


---

## O que o robô faz

### Fase 1 — Criação de cópias

Para cada linha da Aba 1:
1. Pesquisa a tabela original pelo nome
2. Abre o dropdown de ações e aciona "Duplicar"
3. Ativa o switch de vigência
4. Confirma a duplicação e aguarda a cópia aparecer
5. Edita o nome (remove o sufixo "- Cópia")
6. Define as datas de início e fim da vigência
7. Salva

### Fase 2 — Aplicação de reajuste

Para cada cópia criada (filtrada por intervalo de datas):
1. Localiza a linha pela assinatura textual (resistente a rerenders Vue)
2. Abre o modal de reajuste
3. Para cada componente da Aba 2, navega até a aba correta (Taxas / Excessos / Adicionais)
4. Seleciona a taxa via Select2
5. Informa o percentual
6. Adiciona o componente
7. Salva e fecha o modal

---

## Arquitetura

```
rpa-tabela-cliente-por-nome/
├── main.py                          # Ponto de entrada Qt
├── config.py                        # Configurações e seletores DOM
├── .env                             # Credenciais e flags (não versionado)
├── public/                          # Assets: logo, ícone, fontes
│   └── fonts/Manrope-Variable.ttf
└── src/
    ├── aplicacao/
    │   └── automacao_tabela_cliente.py  # Composition Root (orquestrador)
    ├── infraestrutura/
    │   ├── acoes_navegador.py           # Facade Selenium (cliques, waits, Select2)
    │   ├── debug_visual.py              # Highlight vermelho nos elementos
    │   ├── fabrica_navegador.py         # Chrome → Edge fallback
    │   ├── fabrica_registrador_execucao.py
    │   ├── preparador_arquivos_execucao.py
    │   ├── rastreador_etapas.py         # execution_trace.json
    │   └── retencao_artefatos.py
    ├── monitoramento/
    │   └── observador_execucao.py       # Contrato Observer + ObservadorNulo
    ├── paginas/
    │   ├── pagina_login.py
    │   ├── pagina_tabelas_cliente.py    # Page Object principal
    │   ├── pagina_edicao_tabela.py
    │   └── pagina_reajuste.py
    ├── servicos/
    │   ├── leitor_excel.py              # Parse Aba 1 e Aba 2
    │   ├── criador_copia_tabela.py      # Orquestra Fase 1
    │   ├── aplicador_reajuste.py        # Orquestra Fase 2
    │   ├── processador_fase_um.py       # Loop resiliente Fase 1
    │   ├── processador_fase_dois.py     # Loop resiliente Fase 2
    │   └── gestor_ocorrencias.py        # CSV + recuperação de erros
    └── ui/
        ├── ui_main.py                   # JanelaPainelAutomacao (QMainWindow)
        ├── worker.py                    # TrabalhadorExecucaoRpa (QThread)
        ├── componentes.py               # EtiquetaStatus, CartaoEstatistica
        └── logger_ui.py                 # GerenciadorLogsUi (paginação)
```

---

## Artefatos gerados

Cada execução cria uma pasta `execucoes/<run_id>/`:

| Arquivo | Conteúdo |
|---------|---------|
| `execution_trace.json` | Rastreamento de todas as etapas (início, fim, erro) |
| `current_step.json` | Etapa atual (útil para monitoramento externo) |
| `processamento.csv` | Registro tabular de cada tabela (fase, status, mensagem, screenshot) |
| `reports/errors.log` | Log detalhado de erros com traceback |
| `screenshots/` | Capturas de tela em caso de erro |

A política de retenção limita automaticamente o número de execuções armazenadas.

---

## Testes

```bash
# Todos os testes
pytest tests/ -v

# Apenas testes do leitor de Excel
pytest tests/test_leitor_excel.py -v

# Apenas testes da interface de logs
pytest tests/test_logger_ui.py -v

# Apenas testes dos processadores
pytest tests/test_processadores.py -v
```

Os testes são unitários e não dependem de navegador, Excel real ou credenciais.

---

## Debug visual

Com `DEBUG_VISUAL=true`, cada elemento clicado pelo robô recebe um destaque vermelho temporário (`#E53935`) visível no navegador, facilitando o acompanhamento da automação em tempo real.

---

## Solução de problemas

**Navegador não abre:**
- Verifique se Chrome ou Edge está instalado
- Certifique-se de que `HEADLESS=false` no `.env`
- Confirme que as credenciais `EMAIL_LOGIN` e `SENHA_LOGIN` estão preenchidas

**"Selecione o arquivo Excel primeiro":**
- Clique em "Selecionar Excel" para escolher o arquivo

**Erro de timeout:**
- Aumente `TIMEOUT` e `PAGE_LOAD_TIMEOUT` no `.env`
- Verifique a estabilidade da conexão com o sistema ESL Cloud

**Cópia não encontrada na Fase 2:**
- Verifique se as datas de vigência na Aba 1 correspondem exatamente ao que foi configurado na Fase 1
