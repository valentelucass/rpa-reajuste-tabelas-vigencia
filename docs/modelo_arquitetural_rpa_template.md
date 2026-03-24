# Modelo Arquitetural Definitivo do Projeto `rpa-tabela-cliente`

Este documento foi produzido por engenharia reversa do projeto real, com base no código-fonte, testes, artefatos de execução, empacotamento e documentação auxiliar do repositório.

Ele não descreve um “RPA genérico”; descreve o padrão arquitetural efetivamente implementado neste projeto e o traduz para um template reutilizável para novas automações.

## Escopo da análise

Foram analisados, principalmente:

- `main.py`
- `config.py`
- `src/aplicacao/robo_reajuste_taxas.py`
- `src/paginas/*.py`
- `src/servicos/*.py`
- `src/infraestrutura/*.py`
- `src/monitoramento/observador_execucao.py`
- `src/ui/*.py`
- `tests/*.py`
- `build.spec`, `build.bat`, `installer/RPA-Tabela-cliente.iss`
- `logs/`, `reports/` e `docs/`

## Resumo executivo

Este projeto não é um script linear de Selenium com alguns `clicks`. A arquitetura vigente é uma combinação de:

- `desktop app` em `PySide6` para operação humana;
- `Application Service` para orquestração do caso de uso;
- `Page Objects` para superfícies da aplicação web;
- `Service Layer` para processamento de linhas e regras operacionais;
- `Infrastructure Layer` para Selenium, logging, rastreamento e preparo de artefatos;
- `Observer Pattern` para desacoplar o robô da interface e permitir monitoramento em tempo real.

O resultado é um robô com três características fortes:

1. Ele separa navegação, processamento e observabilidade.
2. Ele continua após falhas isoladas de registros.
3. Ele foi preparado para distribuição desktop, não apenas para execução de desenvolvedor.

---

## 1. Arquitetura Geral

### Classificação arquitetural

O projeto pode ser classificado como:

- RPA de automação web orientado a DOM, implementado com Selenium.
- Aplicação desktop que hospeda e monitora o robô.
- Arquitetura modular em camadas, com composição manual de dependências.

Não é:

- automação por imagem;
- automação por coordenadas;
- automação OCR-first;
- script procedural monolítico;
- arquitetura com container de DI formal.

### Camadas identificadas

| Camada | Papel | Arquivos principais |
|---|---|---|
| Bootstrap desktop | Sobe o app Qt, configura fonte e ícone | `main.py` |
| Configuração central | Carrega `.env`, define paths, rótulos e seletores | `config.py` |
| Aplicação | Orquestra o caso de uso fim a fim | `src/aplicacao/robo_reajuste_taxas.py` |
| Páginas | Encapsulam telas e navegação do sistema alvo | `src/paginas/*.py` |
| Serviços | Implementam regras operacionais do loop e do reajuste | `src/servicos/*.py` |
| Infraestrutura | Selenium, waits, logs, screenshots, traces, retenção | `src/infraestrutura/*.py` |
| Monitoramento | Contrato de observação do processamento | `src/monitoramento/observador_execucao.py` |
| UI | Dashboard, thread de execução e log visual | `src/ui/*.py` |
| Testes | Garantem invariantes de comportamento | `tests/*.py` |
| Build/Distribuição | Geração de executável e instalador | `build.spec`, `build.bat`, `installer/*.iss` |

### Ponto de entrada

Existem dois entrypoints práticos:

1. `main.py`
   Papel: entrypoint operacional da aplicação desktop.
   Responsabilidade: criar `QApplication`, carregar fonte, definir ícone e abrir `JanelaPainelAutomacao`.

2. `AutomacaoReajusteTaxas.executar()`
   Papel: entrypoint lógico do robô.
   Responsabilidade: validar configuração, criar dependências, fazer login, navegar, aplicar filtros, processar páginas e encerrar.

### Fluxo principal de execução

Fluxo alto nível real:

```text
main.py
  -> JanelaPainelAutomacao
    -> TrabalhadorExecucaoRpa (QThread)
      -> AutomacaoReajusteTaxas
        -> PreparadorArquivosExecucao
        -> FabricaRegistradorExecucao
        -> FabricaNavegador
        -> AcoesNavegador
        -> PaginaLogin
        -> PaginaTabelasCliente
        -> ReajustadorTaxas
        -> GestorOcorrenciasProcessamento
        -> ProcessadorTabelaClientes
          -> loop de páginas
            -> loop de linhas
              -> reajuste por linha
              -> sucesso ou falha
```

### Como os módulos se comunicam

O acoplamento foi mantido relativamente baixo por injeção de dependências via construtor.

Padrão observado:

- `AutomacaoReajusteTaxas` monta o grafo de objetos.
- `PaginaLogin` e `PaginaTabelasCliente` dependem de `AcoesNavegador`.
- `ReajustadorTaxas` depende de `AcoesNavegador`, `PaginaTabelasCliente` e `RastreadorEtapas`.
- `ProcessadorTabelaClientes` depende de `PaginaTabelasCliente`, `ReajustadorTaxas`, `GestorOcorrenciasProcessamento` e observador.
- `TrabalhadorExecucaoRpa` implementa o contrato de observador e injeta a si próprio no robô.

Esse desenho é importante porque evita que:

- a UI saiba detalhes de Selenium;
- as páginas conheçam regras de negócio do loop;
- os serviços precisem conhecer Qt;
- o código operacional espalhe seletores pelo projeto inteiro.

### Pseudocódigo do caso de uso principal

```python
def executar():
    recarregar_configuracoes()
    validar_credenciais()
    preparar_artefatos()
    iniciar_logger()
    iniciar_navegador()
    montar_paginas_e_servicos()

    abrir_login()
    fazer_login()
    acessar_tabelas_cliente()
    aplicar_filtros_iniciais()
    total = obter_total_registros()
    observador.definir_total_registros(total)

    while existir_pagina():
        for linha in linhas_visiveis_da_pagina():
            try:
                processar_linha(linha)
                registrar_sucesso()
            except Exception:
                registrar_falha()
                recuperar_interface()
            finally:
                aguardar_tela_estavel()

        if not ir_para_proxima_pagina():
            break
```

### Tipo de arquitetura em uma frase

Se for necessário resumir este projeto em um template conceitual, a melhor definição é:

> Aplicação desktop de RPA web baseada em Selenium, organizada em camadas, com Page Objects, serviços de domínio operacional, observabilidade estruturada e empacotamento para distribuição.

---

## 2. Estrutura de Pastas

### Estrutura relevante do repositório

```text
.
|-- main.py
|-- config.py
|-- requirements.txt
|-- README.md
|-- .env
|-- .env.example
|-- build.spec
|-- build.bat
|-- docs/
|   |-- fluxo.md
|   |-- identidade_visual.md
|   `-- modelo_arquitetural_rpa_template.md
|-- src/
|   |-- aplicacao/
|   |-- infraestrutura/
|   |-- monitoramento/
|   |-- paginas/
|   |-- servicos/
|   `-- ui/
|-- tests/
|-- public/
|-- assets/
|-- logs/
|-- reports/
|-- installer/
|-- tools/
|-- build/
`-- dist/
```

### Leitura arquitetural da estrutura

#### `src/aplicacao`

Responsabilidade:

- orquestra o caso de uso;
- monta dependências;
- define o fluxo oficial do robô;
- centraliza validação inicial.

Por que faz sentido:

- evita que o fluxo principal fique espalhado entre UI, páginas e serviços;
- cria um “composition root” manual, simples e legível;
- facilita reuso do mesmo robô por interface, CLI futura ou testes integrados.

#### `src/paginas`

Responsabilidade:

- modelar as superfícies navegáveis da aplicação alvo;
- encapsular elementos e microfluxos de tela;
- esconder o DOM específico do ESL Cloud das camadas superiores.

Por que faz sentido:

- aproxima o projeto do padrão `Page Object`;
- evita duplicação de navegação e waits;
- mantém a semântica do sistema alvo em arquivos previsíveis.

#### `src/servicos`

Responsabilidade:

- processar lotes e linhas;
- executar reajuste por registro;
- tratar sucesso, erro, screenshot e recuperação.

Por que faz sentido:

- isola a lógica operacional da descrição de páginas;
- permite reuso da mesma página em fluxos diferentes;
- separa “como encontrar um elemento” de “o que fazer com o registro”.

#### `src/infraestrutura`

Responsabilidade:

- encapsular Selenium e seus detalhes;
- preparar logger, paths, screenshots e JSON de rastreio;
- limitar crescimento de artefatos;
- resolver diferenças entre execução local e empacotada.

Por que faz sentido:

- Selenium é detalhe de infraestrutura, não regra de negócio;
- sem essa camada o código de páginas e serviços ficaria tomado por boilerplate de `WebDriverWait`, `find_elements`, `save_screenshot`, `execute_script`, etc.

#### `src/monitoramento`

Responsabilidade:

- definir contrato e objetos de observação;
- padronizar como o robô reporta progresso;
- permitir parada controlada sem acoplar o robô à UI.

Por que faz sentido:

- o robô pode emitir eventos para qualquer observador;
- a thread Qt é só uma implementação concreta desse contrato;
- isso transforma o monitoramento em recurso arquitetural, não em efeito colateral.

#### `src/ui`

Responsabilidade:

- interface operacional;
- execução em thread separada;
- visualização de status, progresso e logs;
- reprocessamento individual.

Por que faz sentido:

- evita travar o loop de eventos do Qt;
- transforma o robô em produto operacional, não apenas script técnico;
- reduz dependência de console e melhora adoção por usuários de negócio.

### Outras pastas importantes

#### `tests/`

Papel:

- proteger invariantes importantes;
- validar paginação dinâmica, fallbacks, logs e navegador.

O que isso sinaliza arquiteturalmente:

- o autor testou comportamento, não só funções utilitárias;
- os testes espelham decisões importantes do design.

#### `public/`

Papel:

- recursos de runtime efetivamente usados pela aplicação;
- ícones, logotipo, fonte e manifest.

Observação:

- `main.py` e `build.spec` consomem `public/`, então esta é a pasta “oficial” de assets de execução.

#### `assets/`

Papel:

- artefatos auxiliares de branding.

Observação arquitetural:

- no estado atual, `assets/` parece secundária; `public/` é a origem consumida em runtime.

#### `tools/`

Papel:

- scripts de apoio ao repositório.

Exemplo:

- `tools/generate_brand_icons.py` gera ícones e manifest a partir de SVG via `PySide6`.

Isso é bom porque:

- evita edição manual de múltiplas variantes de ícone;
- padroniza a identidade visual do executável.

#### `logs/` e `reports/`

Papel:

- armazenar estado operacional e técnico.

Separação semântica:

- `logs/` guarda artefatos de execução contínua e estruturada;
- `reports/` guarda evidências e erros técnicos.

Essa separação é correta, porque:

- “log operacional” e “relatório de falha” têm públicos diferentes;
- facilita suporte e troubleshooting.

#### `build/`, `dist/`, `installer/`

Papel:

- ciclo de distribuição.

Importância:

- mostra que a automação foi pensada para entrega a usuários finais;
- a arquitetura não para no código-fonte: inclui empacotamento, recursos, instalador e cópia de `.env`.

### Convenções de nomeação

Convenções observadas:

- nomes em português;
- camadas explícitas por pasta;
- classes com semântica de negócio, não nomes genéricos;
- `DOC-FILE` no topo de arquivos importantes;
- módulos orientados por responsabilidade e não por tipo técnico genérico.

Exemplos bons:

- `PaginaTabelasCliente`
- `ProcessadorTabelaClientes`
- `GestorOcorrenciasProcessamento`
- `RastreadorEtapas`
- `TrabalhadorExecucaoRpa`

### Resíduos e artefatos legados

O repositório contém resíduos que não fazem parte da arquitetura ativa:

- `__pycache__/` na raiz, inclusive com bytecode de módulos antigos;
- `src/interface/__pycache__/`, sugerindo uma estrutura anterior renomeada para `src/ui`;
- zips do projeto na raiz.

Isso não quebra a execução, mas é importante registrar no template:

- não copie resíduos de build para novas automações;
- trate `src/ui` como a estrutura vigente;
- limpe artefatos legados ao transformar este projeto em base oficial.

---

## 3. Padrões de Abstração

### 3.1 Registro de seletores por nome

O projeto evita espalhar `xpath` e `css selector` pelo código. Em vez disso:

- `config.py` mantém um dicionário `SELETORES`;
- o código pede elementos por nomes semânticos;
- `AcoesNavegador` resolve o seletor real.

Exemplo conceitual:

```python
campo_email = acoes.aguardar_seletor("campo_email_login", condicao="visivel")
```

Por que isso é forte:

- centraliza manutenção quando o front muda;
- permite múltiplos seletores alternativos por elemento;
- torna o código de fluxo legível.

### 3.2 `Page Object` pragmático

As classes em `src/paginas` não tentam representar toda a aplicação. Elas encapsulam:

- navegação;
- filtros;
- leitura da tabela;
- controle de modal;
- paginação.

Isso é um `Page Object` pragmático, não cerimonial.

Benefícios:

- reduz acoplamento ao DOM;
- facilita leitura do fluxo;
- melhora reutilização em diferentes serviços.

### 3.3 `Service Layer`

Os serviços foram divididos por responsabilidade real:

- `ReajustadorTaxas`: sabe ajustar uma linha;
- `ProcessadorTabelaClientes`: sabe iterar páginas e linhas;
- `GestorOcorrenciasProcessamento`: sabe registrar e recuperar após erro.

Esse desenho evita um erro clássico de automações:

> colocar navegação, regra de negócio, tratamento de erro e logging tudo dentro de um único loop `for`.

### 3.4 `Observer Pattern`

O contrato em `src/monitoramento/observador_execucao.py` é uma peça-chave.

Ele define:

- total de registros;
- linha em processamento;
- sucesso;
- falha;
- mensagem de sistema;
- interrupção controlada.

Por que isso importa:

- o robô não precisa conhecer Qt;
- a UI pode reagir a eventos sem controlar a lógica do robô;
- outra implementação de observador poderia enviar logs para API, banco ou fila.

### 3.5 Façade de infraestrutura

`AcoesNavegador` funciona como uma façade sobre Selenium.

Ele concentra:

- waits;
- localização por nome de seletor;
- clique com segurança;
- digitação limpa;
- seleção em Select2;
- utilidades de texto e visibilidade.

Isso reduz drasticamente duplicação e torna o código de negócio mais estável.

### 3.6 Composition root explícito

`AutomacaoReajusteTaxas._criar_componentes_execucao()` monta manualmente o grafo de dependências.

Vantagens:

- a ordem de criação fica explícita;
- o ponto de integração é único;
- troca de implementação fica simples.

Desvantagem atual:

- cresce manualmente conforme o projeto cresce.

Ainda assim, para um RPA desse porte, é uma solução excelente.

### 3.7 Rastreamento estruturado por etapa

`RastreadorEtapas` adiciona um padrão pouco comum em RPAs pequenos:

- cada etapa gera `start`, `success` ou `error`;
- o registro é JSON estruturado;
- existe um `current_step.json` com a última etapa conhecida.

Esse padrão é valioso porque:

- aproxima a automação de observabilidade de sistema distribuído;
- facilita análise por IA ou por ferramentas;
- permite saber “onde parou” sem abrir stacktrace completo.

---

## 4. Engine de Automação

### Biblioteca principal

A engine real é baseada em:

- `selenium>=4.29`

Logo, o robô interage com:

- DOM;
- elementos HTML;
- JavaScript do navegador;
- waits explícitas.

### O que a engine não usa

Este projeto não usa:

- `pyautogui`
- `playwright`
- `seleniumbase`
- OCR
- coordenadas fixas
- reconhecimento por imagem

Isso é importante porque a solicitação original fala em automação de interface em sentido amplo, mas a implementação real é `DOM-first`.

### Estratégia de localização

A estratégia é híbrida dentro do DOM:

1. seletores nomeados em `config.py`;
2. múltiplos localizadores por elemento;
3. priorização implícita por ordem;
4. fallback entre `id`, `css selector` e `xpath`.

Exemplo conceitual:

```python
"campo_email_login": [
    ("id", "user_email"),
    ("css selector", "input[name='user[email]']"),
    ("css selector", "input[type='email']"),
]
```

Por que isso é melhor que um seletor único:

- reduz fragilidade contra pequenas mudanças do front;
- permite sobreviver a diferenças entre versões ou ambientes;
- evita refatorações grandes quando um atributo muda.

### Estratégia para elementos complexos

#### Select2

O projeto possui lógica específica para Select2:

- clica no container;
- procura opções por texto;
- usa múltiplas expressões XPath para resultados.

Isso resolve um problema clássico:

- o `select` original costuma estar oculto;
- o componente clicável real é um `span`/`div` renderizado por JS.

#### Botões não diretamente clicáveis

`resolver_alvo_clicavel()` tenta subir para ancestrais clicáveis:

- `button`
- `a`
- `label`
- elementos com `role='button'`

Isso é um hack elegante porque muitos componentes modernos têm o texto em um filho, mas o clique válido está no ancestral.

### Pipeline de clique

O clique seguro foi projetado em camadas:

1. `scrollIntoView` para centralizar o elemento;
2. destaque visual opcional;
3. tentativa de `element.click()`;
4. fallback para `execute_script("arguments[0].click()")`.

Por que isso é importante:

- Selenium falha com frequência em elementos fora da viewport;
- overlays temporários podem quebrar o clique nativo;
- o clique JS reduz falsos negativos operacionais.

### Pipeline de digitação

`limpar_e_digitar()` faz:

1. clique no campo;
2. `CTRL+A`;
3. `BACKSPACE`;
4. digitação do novo valor;
5. remoção do destaque visual.

Isso é melhor que `clear()` puro porque:

- máscaras JS nem sempre respondem bem a `clear()`;
- `CTRL+A + BACKSPACE` simula comportamento humano e tende a ser mais confiável.

### Controle de tempo

O projeto privilegia waits explícitas:

- `WebDriverWait`
- checagem de `document.readyState`
- espera por ausência de overlays

Os timeouts são parametrizados por:

- `TIMEOUT`
- `PAGE_LOAD_TIMEOUT`

### Uso pontual de `sleep`

Há `sleep` em apenas dois contextos:

1. `debug_visual.py`
   Motivo: exibir highlight/pulso visível ao humano.

2. `processador_tabela_clientes.py`
   Motivo: aguardar estabilização de assinaturas de linha após re-renderização do Vue.

Leitura arquitetural:

- o projeto evita `sleep` como regra;
- onde ele aparece, é por motivo visual ou como workaround consciente de renderização.

### Sistema de fallback

Fallbacks implementados:

- múltiplos seletores por elemento;
- clique JS após falha do clique nativo;
- busca do botão de fechar do modal por diferentes caminhos;
- Chrome como navegador primário e Edge como fallback;
- leitura de total por `.entries-info`, com fallback para contagem real das linhas;
- fechamento de modal por texto ou seletor específico.

### Headless e debug visual

O robô suporta:

- `HEADLESS=true/false`
- `DEBUG_VISUAL=true/false`

Esse par de flags é arquiteturalmente muito bom:

- `HEADLESS` serve para execução silenciosa;
- `DEBUG_VISUAL` serve para estabilização, troubleshooting e demonstração.

O `DEBUG_VISUAL` injeta CSS/JS no navegador e não depende do desktop real. Isso é mais estável que desenhar overlay fora do browser.

---

## 5. Controle de Fluxo

### Orquestração macro

`AutomacaoReajusteTaxas` define um pipeline fixo:

1. recarregar configuração;
2. validar credenciais;
3. preparar artefatos;
4. iniciar navegador e logger;
5. login;
6. navegação;
7. filtros;
8. leitura do total;
9. processamento de páginas;
10. encerramento e limpeza.

### Loop mestre da tabela

`ProcessadorTabelaClientes` é o cérebro operacional do lote.

Ele:

- processa páginas até não haver próxima;
- processa todas as linhas visíveis da página;
- não assume quantidade fixa de linhas;
- continua após falha isolada.

### Estratégia contra re-renderização

Essa é uma das decisões mais valiosas do projeto.

Problema:

- Vue pode re-renderizar a tabela após cada ação;
- referências antigas de `WebElement` podem ficar inválidas;
- índices absolutos de linha deixam de ser confiáveis.

Solução implementada:

1. extrair uma assinatura textual da linha;
2. armazenar as assinaturas da página;
3. relocalizar a linha antes de processá-la;
4. usar contador de ocorrências para distinguir linhas com texto idêntico.

Em outras palavras:

- o loop não confia no `WebElement` original;
- ele confia em uma “identidade funcional” derivada do conteúdo.

Isso é um padrão de ouro para automações em grids reativas.

### Checkpoints

O projeto não tem checkpoint de retomada transacional completa, mas tem checkpoints de diagnóstico:

- `current_step.json`
- `execution_trace.json`
- `logs/processamento.csv`

Esses arquivos não retomam a execução automaticamente, mas tornam a retomada manual muito mais precisa.

### Retries

Retries explícitos formais são poucos, mas existem estratégias equivalentes:

- múltiplos localizadores;
- repetição controlada de busca em waits;
- re-leitura da tabela até obter assinaturas estáveis;
- tentativa de relocalizar linha após re-render.

Ou seja, a resiliência foi construída mais por `re-observação do estado` do que por `for tentativa in range(n)` indiscriminado.

### Tratamento de erro

O tratamento ocorre em níveis:

#### Nível de linha

- falha gera screenshot;
- grava CSV;
- informa observador/UI;
- escreve stacktrace técnico;
- tenta recuperar a interface;
- segue para a próxima linha.

#### Nível de execução

- falhas críticas sobem até `AutomacaoReajusteTaxas`;
- o logger registra `Falha critica na execucao principal`;
- a thread atualiza o painel para `Erro`.

### Limite real da resiliência atual

Os artefatos em `logs/execution_trace.json` mostram falhas reais como:

- `invalid session id`
- `no such window`
- timeout de seletor em modal

Isso revela um ponto importante:

- falhas isoladas de registro são bem tratadas;
- falhas de saúde do browser/sessão ainda podem escalar e interromper o lote.

Esse limite precisa aparecer no template, porque ele define a fronteira da resiliência atual.

---

## 6. Configuração e Parametrização

### Fonte de configuração

O projeto usa `.env` para:

- credenciais;
- URL;
- headless;
- debug visual;
- confirmação final;
- timeouts;
- retenção de artefatos.

### Carregamento

`config.py` implementa o carregamento manual do `.env`, sem depender de `python-dotenv`.

Vantagens:

- dependência externa a menos;
- controle simples e explícito;
- reduz acoplamento a bibliotecas auxiliares.

Desvantagens:

- parsing é básico;
- não há validação tipada sofisticada;
- não há namespaces ou profiles.

### Configuração recarregada a cada execução

`AutomacaoReajusteTaxas.executar()` e `reprocessar_registro()` chamam:

```python
config.recarregar_configuracoes(sobrescrever_env=True)
```

Isso é excelente porque:

- o usuário pode ajustar `.env` entre execuções sem reiniciar a aplicação;
- o robô não fica preso ao estado de import inicial.

### Parametrização por injeção de valor de negócio

O valor do reajuste não vem da camada de configuração central em runtime.

Na implementação real, ele vem de:

- `QLineEdit` na UI;
- conversão para `float`;
- injeção via construtor em `TrabalhadorExecucaoRpa`;
- repasse para `AutomacaoReajusteTaxas`;
- repasse para `ReajustadorTaxas`.

Isso é uma decisão arquitetural importante:

- credenciais e flags ficam no ambiente;
- o parâmetro operacional principal fica visível e editável pelo operador na UI.

### Divergência documental atual

Há uma inconsistência relevante no repositório:

- `.env.example`, `README.md` e `docs/fluxo.md` ainda mencionam `VALOR_REAJUSTE`;
- o código atual não carrega `VALOR_REAJUSTE` de `config.py`;
- o valor real usado na execução vem da UI.

Leitura correta:

- a arquitetura atual migrou o parâmetro de negócio para a interface;
- a documentação ainda preserva parte do modelo antigo.

Isso deve virar ação corretiva em qualquer template derivado.

### Configuração de retenção

O projeto parametriza crescimento de artefatos por ambiente:

- `MAX_SCREENSHOTS_ARMAZENADOS`
- `MAX_REGISTROS_PROCESSAMENTO`
- `MAX_REGISTROS_TRACE`
- `MAX_BYTES_LOG_ERROS`
- `MAX_BACKUPS_LOG_ERROS`

Essa é uma maturidade rara em RPAs pequenos e deve ser copiada para qualquer nova automação.

---

## 7. Estratégias Inteligentes e Hacks de Estabilidade

Esta é a seção mais valiosa para template.

### 7.1 Não confiar em índice de linha

O sistema não processa “linha 1, linha 2, linha 3” como posições fixas. Ele:

- captura assinatura textual;
- relocaliza a linha;
- trata duplicidade por ocorrência.

Isso elimina uma classe inteira de bugs em grids reativas.

### 7.2 Deduplicação de elementos encontrados por múltiplos seletores

`buscar_todos_por_nome_seletor()` deduplica elementos por `id` interno do Selenium.

Motivo:

- o mesmo elemento pode ser encontrado por mais de um seletor alternativo;
- sem deduplicação, o robô poderia processar ou clicar o mesmo item duas vezes.

### 7.3 Espera por ausência de overlay

`aguardar_carregamento_finalizar()` não espera um elemento específico; espera a ausência de possíveis camadas de carregamento.

Isso é mais robusto porque:

- carrega bem com UI dinâmica;
- não depende de um único spinner;
- aceita variações de framework visual.

### 7.4 Safe mode funcional

`CONFIRMAR_REAJUSTE_FINAL=false` não só “não clica em Sim”.

Na prática, ele:

- cancela o SweetAlert;
- fecha o modal;
- continua o loop.

Isso permite validar o fluxo completo sem alterar dados reais.

É uma técnica muito boa de antifragilidade operacional.

### 7.5 Rastreamento em JSON estruturado

Em vez de depender apenas de texto livre em log:

- cada etapa carrega nome, descrição, status e contexto;
- erros recebem screenshot e traceback;
- a última etapa fica disponível em arquivo separado.

Isso é útil para:

- suporte;
- pós-morte de falha;
- auditoria;
- futura observabilidade automatizada.

### 7.6 Retenção automática de evidências

O projeto evita “falha por sucesso acumulado”.

Sem retenção, uma automação estável pode:

- lotar disco com screenshots;
- inflar CSV de processamento;
- tornar lento abrir logs.

O projeto já previne isso com:

- corte por quantidade;
- rotação de arquivo;
- manutenção dos artefatos mais recentes.

### 7.7 Debug visual injetado no browser

O `DEBUG_VISUAL` faz highlight dentro do DOM com CSS/JS.

Por que isso é um hack bom:

- não depende do sistema operacional;
- não exige captura de tela externa;
- funciona até em contexto web complexo;
- ajuda a entender onde o robô clicou de fato.

### 7.8 Recuperação leve após falha

Após erro de linha, o sistema tenta:

- clicar em botão de fechar modal;
- enviar `ESC` para o elemento ativo;
- aguardar estabilização.

É uma recuperação simples, mas eficaz para muitos casos de modal preso.

### 7.9 Fallback de navegador

`FabricaNavegador` tenta:

1. Chrome
2. Edge

Isso reduz dependência do ambiente local e aumenta chance de execução em máquinas corporativas.

### 7.10 Uso de artefatos reais como feedback arquitetural

Os logs do próprio repositório registram falhas reais de sessão e janela.

Isso indica uma prática boa, ainda que implícita:

- o projeto aprende com produção;
- as melhorias de rastreamento surgiram de dores operacionais concretas.

---

## 8. Otimizações

### 8.1 Leitura dinâmica do total

`obter_total_registros()` tenta ler `Exibindo X - Y de Z`.

Impacto:

- UI mostra progresso real;
- operador ganha previsibilidade;
- o sistema evita supor um total fixo.

### 8.2 Consolidação de logs na UI

A UI não cria sempre uma nova linha para o mesmo registro.

Ela:

- calcula uma chave de consolidação;
- atualiza o registro existente quando o status muda.

Efeito:

- o painel não explode em volume;
- a linha de um registro reflete o estado mais recente;
- o botão de reprocessar acompanha o status atual.

### 8.3 Páginas de log na interface

`LINHAS_LOGS_POR_PAGINA = 8`

Isso parece detalhe de UI, mas é otimização operacional:

- renderização fica previsível;
- tabela não cresce indefinidamente;
- leitura humana melhora.

### 8.4 Reuso do mesmo grafo de abstrações

O reprocessamento não cria um “fluxo alternativo improvisado”.

Ele reaproveita:

- login;
- navegação;
- filtros;
- busca do registro;
- reajuste por linha.

Isso reduz custo de manutenção e evita bugs de divergência entre fluxo normal e fluxo de suporte.

### 8.5 Fallback de seletor em ordem de probabilidade

Elementos mais estáveis tendem a aparecer primeiro, com alternativas depois.

Isso melhora:

- manutenção;
- chance de sucesso;
- tempo de evolução quando o front muda pouco.

### 8.6 Empacotamento com hidden imports explícitos

No `build.spec`, Selenium recebe `hiddenimports` porque faz lazy imports.

Isso evita uma classe comum de bugs:

- funcionar no ambiente do dev;
- quebrar no executável gerado.

### 8.7 Build limpo automatizado

`build.bat` remove:

- `build/`
- `dist/...`
- instalador anterior

Antes de rebuild.

Isso reduz bugs de empacotamento por artefato residual.

---

## 9. Bibliotecas e Dependências

### Dependências externas de produção

#### `selenium`

Uso:

- automação web baseada em DOM;
- WebDriverWait;
- interação com elementos;
- execução JS.

Por que foi escolhido:

- ótimo para aplicações corporativas web tradicionais;
- fácil de distribuir;
- compatível com Chrome e Edge;
- suficiente para fluxo orientado a formulário e tabela.

Quando usar:

- sistemas com DOM acessível;
- ambientes Windows corporativos;
- quando Playwright não é requisito.

Alternativas:

- `playwright`: melhor auto-wait e isolamento, excelente para apps JS modernos;
- `pyautogui`: quando não há DOM;
- `robotframework` com SeleniumLibrary: quando o time quer maior declaratividade;
- `RPA Framework`: quando já existe ecossistema UiPath-like simplificado.

#### `PySide6`

Uso:

- interface desktop;
- thread de execução;
- painel operacional.

Por que foi escolhido:

- stack Qt robusta;
- boa experiência visual;
- suporte a app desktop real;
- facilita empacotamento.

Quando usar:

- quando operadores humanos precisam iniciar, parar, acompanhar e reprocessar;
- quando a automação precisa parecer produto, não script.

Alternativas:

- `tkinter`: mais simples, menos refinado;
- `customtkinter`: melhor visual, menos robusto que Qt;
- app web local: bom para times acostumados a web, mas adiciona complexidade operacional.

### Dependências de build/distribuição

#### `PyInstaller`

Uso:

- gerar executável desktop.

Por que é importante:

- elimina dependência de Python instalado na máquina do usuário;
- empacota recursos e módulos.

#### `Inno Setup`

Uso:

- gerar instalador Windows.

Por que é importante:

- entrega profissional;
- criação de atalhos;
- instalação em `Program Files`.

### Bibliotecas padrão relevantes

| Biblioteca | Papel |
|---|---|
| `logging` | log técnico |
| `csv` | log operacional |
| `json` | trace estruturado |
| `pathlib` | paths portáveis |
| `dataclasses` | objetos leves de contexto e log |
| `contextlib` | context manager para rastreamento |
| `traceback` | stacktrace estruturado |
| `datetime` | timestamps |
| `os` | leitura de ambiente |
| `unittest` | testes automatizados |
| `time` | espera pontual consciente |

### Ferramentas auxiliares

#### `pyright`

O repositório possui `pyrightconfig.json`.

Leitura arquitetural:

- há preocupação com tipagem e análise estática;
- o alvo principal de desenvolvimento é Python 3.12.

---

## 10. Debug e Logging

### Canais de observabilidade

O projeto tem quatro canais principais:

1. `logs/processamento.csv`
2. `reports/errors.log`
3. `logs/execution_trace.json`
4. `logs/current_step.json`

Além disso:

- a UI exibe um espelho operacional em tempo real;
- screenshots são gravadas em `reports/screenshots/`.

### `logs/processamento.csv`

Função:

- histórico funcional por registro.

Campos:

- timestamp
- página
- linha
- identificador
- status
- mensagem
- screenshot

Uso ideal:

- auditoria operacional;
- suporte;
- reprocessamento manual ou automatizado futuro.

### `reports/errors.log`

Função:

- log técnico persistente com `RotatingFileHandler`.

Uso ideal:

- stacktraces;
- exceções críticas;
- eventos de infraestrutura.

### `execution_trace.json`

Função:

- trilha estruturada de etapas com contexto.

Valor arquitetural:

- muito mais útil que log textual para saber “em que passo exato falhou”.

### `current_step.json`

Função:

- foto do último estado conhecido.

Valor:

- resposta rápida para operador ou suporte;
- útil até sem abrir o JSON grande.

### Screenshots em erro

Geradas em:

- falhas de linha via `GestorOcorrenciasProcessamento`;
- falhas de etapa via `RastreadorEtapas`.

Isso cria dois níveis de evidência:

- evidência operacional do registro;
- evidência técnica da etapa.

### Como reproduzir bugs com os artefatos atuais

O fluxo de reprodução recomendado a partir desta arquitetura é:

1. abrir `current_step.json` para ver a última etapa;
2. abrir `execution_trace.json` e filtrar pelo `status = error`;
3. correlacionar `context.pagina`, `context.linha`, `cliente` e `id_registro`;
4. abrir screenshot correspondente;
5. usar `processamento.csv` para saber se o erro foi isolado ou recorrente;
6. abrir `errors.log` para stacktrace completo.

Esse pipeline de suporte é muito superior ao padrão “deu erro no meio e ninguém sabe onde”.

---

## 11. Resiliência e Segurança Operacional

### O que o robô faz bem

#### Continua após erro de registro

Esse é o principal sinal de robustez.

O lote não morre por erro unitário.

#### Permite parada controlada

`validar_continuacao()` é chamado no loop de páginas e no loop de linhas.

Isso evita:

- interrupção abrupta no meio de uma transação de UI;
- fechamento bruto de navegador sem contexto.

#### Valida estados antes de agir

O projeto verifica:

- visibilidade;
- clicabilidade;
- ausência de `disabled`;
- ausência de overlays;
- presença do modal esperado.

#### Tem modo seguro sem confirmação final

Isso reduz risco de dano em homologação e troubleshooting.

### Limites de segurança/resiliência atuais

#### Sem retomada automática por checkpoint

Se o browser morrer:

- os artefatos ajudam a entender o ponto;
- mas não há retomada automática do lote no mesmo ponto.

#### Sem health-check de sessão antes de cada ciclo

Falhas de sessão do navegador ainda podem explodir dentro do loop.

#### Sem política explícita de retry por tipo de exceção

Hoje a resiliência é forte em observação do estado, mas moderada em retries formais classificados.

### Segurança de credenciais

As credenciais ficam no `.env`, não no código.

Isso é correto.

Entretanto:

- o `.env` é copiado para o diretório distribuído pelo `build.bat`;
- isso facilita uso operacional;
- mas exige política de proteção da máquina e do diretório instalado.

### Safe execution

O modo mais seguro atual é:

- `HEADLESS=false`
- `DEBUG_VISUAL=true` para calibração
- `CONFIRMAR_REAJUSTE_FINAL=false`

Essa combinação deveria ser a etapa obrigatória antes de produção em novas automações.

---

## 12. Reutilização e Escalabilidade

### O que já é genérico o bastante para virar template

#### `AcoesNavegador`

Quase todo projeto de Selenium corporativo reaproveitaria:

- waits;
- clique seguro;
- seleção por texto;
- seleção de Select2;
- utilidades de visibilidade e texto.

#### `FabricaNavegador`

Pode ser reaproveitada quase sem alterações.

#### `PreparadorArquivosExecucao`

Estrutura base de logs, relatórios e retenção é altamente reutilizável.

#### `RastreadorEtapas`

Excelente candidato a componente comum entre RPAs.

#### `ContratoObservadorExecucao`

Deveria virar contrato padrão para qualquer robô com monitoramento ou integração externa.

#### `TrabalhadorExecucaoRpa`

A ideia de thread + observador + central de logs é altamente reutilizável em qualquer desktop RPA.

### O que é específico deste projeto

#### `PaginaLogin`

Genérica na forma, específica no conteúdo.

#### `PaginaTabelasCliente`

Específica do ESL Cloud e do fluxo de tabelas de cliente.

#### `ReajustadorTaxas`

Específico do caso de uso de reajuste.

### Como escalar a partir daqui

O caminho natural de evolução para outras automações é:

1. manter `infraestrutura`, `monitoramento` e grande parte de `ui`;
2. trocar `paginas` conforme o sistema alvo;
3. trocar ou estender `servicos` conforme o processo de negócio;
4. manter `aplicacao` como orquestrador do caso de uso.

### O padrão real deste projeto

O template implícito não é “um script que faz login e clica”. O template implícito é:

> um robô como produto operacional, com núcleo de automação desacoplado, observável, empacotável e com suporte a execução assistida.

---

## 13. Fluxo Arquitetural Detalhado

### Fluxo completo

```python
def fluxo_completo(valor_reajuste):
    automacao = AutomacaoReajusteTaxas(valor_reajuste, observador)

    preparar_arquivos()
    logger = criar_logger()
    browser = criar_browser()
    acoes = AcoesNavegador(browser, logger)

    login = PaginaLogin(acoes)
    tabela = PaginaTabelasCliente(acoes)
    reajustador = ReajustadorTaxas(acoes, tabela, valor_reajuste, rastreador)
    ocorrencias = GestorOcorrenciasProcessamento(acoes)
    processador = ProcessadorTabelaClientes(
        acoes, tabela, reajustador, ocorrencias, observador, rastreador
    )

    login.abrir()
    login.fazer_login()
    tabela.acessar()
    tabela.preparar_filtros_iniciais()
    observador.definir_total_registros(tabela.obter_total_registros())
    processador.processar_todas_paginas()
```

### Fluxo de processamento de uma linha

```python
def processar_linha(linha):
    abrir_menu_da_linha(linha)
    clicar_reajuste()
    modal = aguardar_modal()
    marcar_todos_os_trechos(modal)
    selecionar_taxa_administrativa(modal)
    marcar_valor_fixo(modal)
    preencher_valor(modal)
    clicar_adicionar(modal)
    clicar_salvar(modal)

    if confirmar_reajuste_final:
        confirmar_swal()
        tratar_popup_de_sucesso()
        fechar_modal()
    else:
        cancelar_swal()
        fechar_modal_sem_salvar()

    aguardar_modal_fechar()
```

### Fluxo de falha isolada

```python
def tratar_falha_de_registro(contexto, erro):
    screenshot = gerar_screenshot(contexto)
    registrar_csv(status="ERRO", mensagem=str(erro), screenshot=screenshot)
    observador.registrar_falha(contexto, str(erro))
    logger.error(stacktrace_completo)
    recuperar_interface_apos_erro()
    continuar_para_proxima_linha()
```

---

## 14. Padrões e Boas Práticas Implícitas

### Boas práticas já presentes

- Separação real entre UI, aplicação, páginas, serviços e infraestrutura.
- Seletores centralizados.
- Logging funcional e técnico separados.
- Captura de screenshot em erro.
- Observador desacoplado da UI.
- Build e distribuição automatizados.
- Suporte a modo seguro.
- Tipagem e testes automatizados.
- Recursos preparados para PyInstaller.

### Boas práticas implícitas que merecem ser formalizadas no template

- Sempre manter um `composition root`.
- Nunca iterar `WebElement` antigo em grid reativa sem relocalizar.
- Todo passo importante de negócio deve ter nome de etapa.
- Todo lote longo precisa de retenção de artefatos.
- Todo robô com UI deve executar em thread separada.

---

## 15. Template Base Para Nova Automação

### Estrutura recomendada

```text
nova_automacao/
|-- main.py
|-- config.py
|-- requirements.txt
|-- .env.example
|-- README.md
|-- build.spec
|-- build.bat
|-- docs/
|   `-- arquitetura.md
|-- src/
|   |-- aplicacao/
|   |   `-- automacao_principal.py
|   |-- infraestrutura/
|   |   |-- acoes_navegador.py
|   |   |-- fabrica_navegador.py
|   |   |-- caminhos.py
|   |   |-- registrador_execucao.py
|   |   |-- rastreador_etapas.py
|   |   |-- arquivos_execucao.py
|   |   `-- retencao_artefatos.py
|   |-- monitoramento/
|   |   `-- observador_execucao.py
|   |-- paginas/
|   |   |-- pagina_login.py
|   |   `-- pagina_operacao.py
|   |-- servicos/
|   |   |-- executor_operacao.py
|   |   |-- processador_lote.py
|   |   `-- gestor_ocorrencias.py
|   `-- ui/
|       |-- componentes.py
|       |-- logger.py
|       |-- worker.py
|       `-- ui_main.py
|-- tests/
|   |-- test_config.py
|   |-- test_acoes_navegador.py
|   |-- test_processador_lote.py
|   `-- test_ui_logs.py
|-- logs/
|-- reports/
|-- public/
`-- installer/
```

### Arquivos iniciais recomendados

#### `config.py`

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"

def _load_env() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_env()

URL_LOGIN = os.getenv("URL_LOGIN", "")
EMAIL_LOGIN = os.getenv("EMAIL_LOGIN", "")
SENHA_LOGIN = os.getenv("SENHA_LOGIN", "")
HEADLESS = os.getenv("HEADLESS", "false").lower() in {"1", "true", "sim", "yes"}
CONFIRMAR_FINAL = os.getenv("CONFIRMAR_FINAL", "false").lower() in {"1", "true", "sim", "yes"}
TIMEOUT = int(os.getenv("TIMEOUT", "30"))

SELETORES = {
    "campo_email": [
        ("id", "user_email"),
        ("css selector", "input[type='email']"),
    ],
    "campo_senha": [
        ("id", "user_password"),
        ("css selector", "input[type='password']"),
    ],
    "botao_login": [
        ("css selector", "button[type='submit']"),
        ("xpath", "//input[@type='submit']"),
    ],
}
```

#### `src/paginas/pagina_login.py`

```python
import config

class PaginaLogin:
    def __init__(self, acoes):
        self.acoes = acoes

    def abrir(self):
        self.acoes.navegador.get(config.URL_LOGIN)
        self.acoes.aguardar_documento_pronto()

    def autenticar(self):
        email = self.acoes.aguardar_seletor("campo_email", "visivel")
        senha = self.acoes.aguardar_seletor("campo_senha", "visivel")
        entrar = self.acoes.aguardar_seletor("botao_login", "clicavel")
        self.acoes.limpar_e_digitar(email, config.EMAIL_LOGIN)
        self.acoes.limpar_e_digitar(senha, config.SENHA_LOGIN)
        self.acoes.clicar_com_seguranca(entrar)
```

#### `src/servicos/executor_operacao.py`

```python
class ExecutorOperacao:
    def __init__(self, acoes, pagina_operacao, rastreador=None):
        self.acoes = acoes
        self.pagina_operacao = pagina_operacao
        self.rastreador = rastreador

    def executar_item(self, item, contexto):
        with self.rastreador.etapa("abrir_item", "Abrindo item", contexto):
            self.pagina_operacao.abrir_item(item)

        with self.rastreador.etapa("executar_acao", "Executando acao no item", contexto):
            self.pagina_operacao.executar_acao(item)
```

#### `src/servicos/processador_lote.py`

```python
class ProcessadorLote:
    def __init__(self, pagina_operacao, executor_operacao, gestor_ocorrencias, observador):
        self.pagina_operacao = pagina_operacao
        self.executor_operacao = executor_operacao
        self.gestor_ocorrencias = gestor_ocorrencias
        self.observador = observador

    def processar(self):
        pagina = 1
        while True:
            itens = self.pagina_operacao.obter_itens()
            for indice, item in enumerate(itens, start=1):
                contexto = self.pagina_operacao.extrair_contexto(item, pagina, indice)
                self.observador.registrar_processando(contexto)
                try:
                    self.executor_operacao.executar_item(item, contexto.__dict__)
                    self.gestor_ocorrencias.registrar_sucesso(
                        pagina, indice, contexto.identificador, "Item processado com sucesso."
                    )
                    self.observador.registrar_sucesso(contexto, "Item processado com sucesso.")
                except Exception as erro:
                    self.gestor_ocorrencias.registrar_falha(
                        pagina, indice, contexto.identificador, str(erro)
                    )
                    self.observador.registrar_falha(contexto, str(erro))
                    self.gestor_ocorrencias.recuperar_interface_apos_erro()
            if not self.pagina_operacao.ir_para_proxima_pagina():
                break
            pagina += 1
```

#### `src/aplicacao/automacao_principal.py`

```python
class AutomacaoPrincipal:
    def __init__(self, observador=None):
        self.observador = observador
        self.navegador = None

    def executar(self):
        # composition root simplificado
        ...
```

### Exemplo de fluxo mínimo para nova automação

Fluxo sugerido:

1. abrir login;
2. autenticar;
3. navegar até a tela alvo;
4. aplicar filtros;
5. iterar tabela;
6. executar ação por item;
7. registrar sucesso/falha;
8. encerrar.

### Boas regras para o template base

- A camada `paginas` nunca deve decidir o que fazer com o lote.
- A camada `servicos` nunca deve conhecer seletor bruto quando isso puder ficar em `config.py`.
- O `main.py` nunca deve conter regra de negócio.
- Todo robô deve ter ao menos CSV, erro técnico, screenshot e trace de etapa.

---

## 16. Checklist de Nova Automação

- [ ] Definir fluxo principal.
- [ ] Identificar ponto de entrada operacional e ponto de entrada lógico.
- [ ] Mapear telas em classes de página.
- [ ] Mapear elementos da tela em seletores nomeados.
- [ ] Criar camada de ações reutilizáveis.
- [ ] Separar processamento de lote da ação unitária.
- [ ] Implementar observador de execução.
- [ ] Implementar retries por observação de estado.
- [ ] Adicionar logging funcional em CSV.
- [ ] Adicionar logging técnico com rotação.
- [ ] Adicionar screenshots em erro.
- [ ] Adicionar rastreador estruturado de etapas.
- [ ] Validar estados antes de ações.
- [ ] Implementar modo seguro sem confirmação final.
- [ ] Implementar parada controlada.
- [ ] Implementar retenção de artefatos.
- [ ] Criar testes para paginação, erros isolados e atualização de logs.
- [ ] Preparar build e distribuição.
- [ ] Revisar divergência entre documentação e comportamento real antes de entregar.

---

## 17. Melhorias Sugeridas

### Arquiteturais

#### 1. Unificar a fonte de verdade do valor de reajuste

Hoje há drift entre:

- `.env.example`
- `README.md`
- `docs/fluxo.md`
- UI real

Melhoria:

- decidir oficialmente se `valor_reajuste` vem da UI, do `.env` ou de ambos com precedência definida;
- refletir isso no código e na documentação.

#### 2. Introduzir estratégia formal de retry por categoria de erro

Exemplo:

- retry curto para `StaleElementReferenceException`;
- retry médio para overlay/intercept;
- retry com reinício de navegador para `invalid session id`.

#### 3. Criar `HealthMonitor` de sessão do navegador

Hoje falhas de janela/sessão ainda rompem o fluxo.

Melhoria:

- validar saúde do browser antes de processar próxima linha;
- reinicializar sessão quando possível.

#### 4. Extrair mais contratos

Exemplos:

- contrato de logger operacional;
- contrato de captura de evidência;
- contrato de navegador.

Isso facilitaria testes e evolução.

### Performance

#### 5. Reduzir re-leituras integrais da página quando possível

Hoje a relocalização por assinatura é correta, mas pode custar caro em grids muito grandes.

Melhoria:

- combinar assinatura textual com `data-id` sempre que disponível;
- priorizar `data-id` estável para lookup.

#### 6. Cache leve de contexto da página

Exemplo:

- número da página atual;
- total lido;
- assinatura dos primeiros itens;
- presença de modal.

Não para eliminar validação, mas para reduzir reprocessamento redundante.

### Manutenibilidade

#### 7. Limpar artefatos legados do repositório

Remover ou ignorar de vez:

- `src/interface/__pycache__`
- bytecode antigo na raiz
- zips de snapshot

#### 8. Adicionar testes para falhas reais vistas em produção

Os artefatos mostram falhas concretas de:

- `invalid session id`
- `no such window`
- timeout de modal

Esses cenários devem virar testes de comportamento ou ao menos testes de política de recuperação.

#### 9. Corrigir desalinhamento entre testes e fluxo atual de confirmação

Ao validar a suíte, foi observado:

- `17` testes passaram;
- `1` teste falhou por esperar apenas uma chamada de confirmação, enquanto o fluxo atual suporta confirmação adicional de sucesso.

Isso é sinal de drift entre teste e comportamento vigente.

### Observabilidade

#### 10. Adicionar `run_id` único por execução

Hoje há timestamp, mas não um identificador forte de rodada.

Com `run_id`, seria fácil correlacionar:

- CSV;
- errors.log;
- JSON trace;
- screenshots;
- UI.

#### 11. Persistir métricas agregadas por execução

Exemplo:

- duração total;
- falhas por tipo;
- linhas por minuto;
- páginas por minuto.

#### 12. Exportar relatório final consolidado

Ao fim do lote, gerar um JSON ou CSV resumo contendo:

- total previsto;
- total processado;
- total sucesso;
- total falha;
- início;
- fim;
- duração;
- status final.

### Segurança operacional

#### 13. Proteger melhor a distribuição do `.env`

Como o build copia o `.env` para o diretório distribuído, vale considerar:

- criptografia em repouso;
- leitura via credential manager;
- ou pelo menos instrução formal de controle de acesso à pasta instalada.

---

## 18. Desafios Reais de Empacotamento, Distribuição e Execução em Produção

Esta seção documenta os problemas concretos enfrentados ao transformar o projeto `rpa-reajuste-tabelas-vigencia` de código-fonte em produto instalável. Cada desafio é descrito com causa raiz, sintoma, solução aplicada e lição para futuras automações.

### 18.1 Resolução dual de caminhos no PyInstaller

**Sintoma:** aplicação empacotada não encontra ícones, fontes ou não consegue criar logs.

**Causa raiz:** PyInstaller altera fundamentalmente o ambiente de execução. Quando empacotado:

- `sys._MEIPASS` aponta para `_internal/` (recursos somente leitura, bundled)
- `Path(sys.executable).parent` aponta para o diretório do `.exe` (gravável)
- `Path(__file__)` aponta para dentro de `_internal/` (errado para quase tudo)

O problema é que **recursos de leitura** (ícones, fontes, logo) e **diretórios graváveis** (logs, reports, screenshots) precisam de caminhos diferentes.

**Solução aplicada em `src/infraestrutura/caminhos.py`:**

```python
def _resolver_dir_recursos() -> Path:
    """Diretório dos recursos empacotados (public/, fonts)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent

def _resolver_dir_app() -> Path:
    """Diretório do aplicativo (onde ficam logs/, reports/, .env)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent

RESOURCES_DIR = _resolver_dir_recursos()
APP_DIR = _resolver_dir_app()

PUBLIC_DIR = RESOURCES_DIR / "public"   # leitura: ícones, fontes
LOGS_DIR = APP_DIR / "logs"             # escrita: logs operacionais
REPORTS_DIR = APP_DIR / "reports"       # escrita: relatórios e erros
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"  # escrita: evidências
```

**Lição para futuras automações:**

- Nunca usar `Path(__file__)` para paths em código que será empacotado.
- Sempre separar `RESOURCES_DIR` (somente leitura, bundled) de `APP_DIR` (gravável, ao lado do exe).
- Centralizar toda resolução de paths em um único módulo (`caminhos.py`) para evitar divergências.
- Todo módulo que precise de paths deve importar de `caminhos.py`, nunca resolver por conta própria.

**Arquivos que precisaram de correção:**

| Arquivo | Problema original | Correção |
|---------|-------------------|----------|
| `main.py` | `Path(__file__).parent / "public"` | Importar `PUBLIC_DIR` de `caminhos.py` |
| `src/ui/ui_main.py` | `Path(__file__).parent.parent.parent / "public" / "logo.png"` | Importar `PUBLIC_DIR` de `caminhos.py` |
| `config.py` | `Path(__file__).resolve().parent` para tudo | Usar `Path(sys.executable).parent` quando frozen |

### 18.2 Ordem de criação de diretórios vs. inicialização do logger

**Sintoma:** `[Errno 2] No such file or directory` ao iniciar a execução do robô na máquina do usuário.

**Causa raiz:** ordem de operações no `worker.py`:

```text
worker.run() linha 50:
    criar_logger("rpa")          ← tenta abrir reports/errors.log
        ↓ FALHA: reports/ não existe ainda

worker.run() linha 54:
    automacao.executar()
        ↓
    _preparar_artefatos()         ← AQUI cria logs/, reports/, screenshots/
        ↓
    _iniciar_logger()             ← agora sim funciona
```

O `RotatingFileHandler` do Python **não cria diretórios pai automaticamente**. Se `reports/` não existe, ele lança `FileNotFoundError`.

Em desenvolvimento isso nunca aparece porque os diretórios já existem de execuções anteriores. Na primeira execução em máquina limpa, falha imediatamente.

**Solução aplicada:**

1. **Em `caminhos.py`** — criar diretórios no momento da importação do módulo:

```python
for _dir in (LOGS_DIR, REPORTS_DIR, SCREENSHOTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
```

2. **Em `fabrica_registrador_execucao.py`** — defesa adicional antes do `RotatingFileHandler`:

```python
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
caminho_log = REPORTS_DIR / "errors.log"
handler_arquivo = RotatingFileHandler(caminho_log, ...)
```

**Lição para futuras automações:**

- Diretórios graváveis devem ser criados **no momento da importação** do módulo de caminhos, não depois.
- Qualquer código que abra arquivo para escrita deve garantir que o diretório pai existe.
- Nunca confiar que o `PreparadorArquivosExecucao` vai rodar antes de outros módulos que escrevem em disco.
- Testar sempre a **primeira execução em diretório vazio** — é onde esses bugs aparecem.

### 18.3 Proteção contra escrita em `Program Files`

**Sintoma:** `[Errno 2] No such file or directory: 'C:\\Program Files\\Rodogarcia\\RPA-Reajust...'`

**Causa raiz:** o instalador original usava `{autopf}` (que resolve para `C:\Program Files\`), um diretório protegido contra escrita no Windows. Qualquer tentativa de criar `logs/`, `reports/` ou escrever `.csv`, `.json` falha sem elevação de privilégio.

Mesmo com a aplicação rodando, o Windows UAC bloqueia escritas em `Program Files` para processos não-admin.

**Solução aplicada no Inno Setup (`installer/*.iss`):**

```inno
; ANTES (quebrava):
DefaultDirName={autopf}\Rodogarcia\{#AppName}
PrivilegesRequired=admin

; DEPOIS (funciona):
DefaultDirName={localappdata}\Rodogarcia\{#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
```

Também foi necessário trocar `{commondesktop}` por `{userdesktop}` no atalho de desktop, porque sem admin não se pode escrever no desktop de todos os usuários.

**Lição para futuras automações:**

- RPAs que geram artefatos em runtime (logs, screenshots, CSV, JSON) **não devem ser instalados em `Program Files`**.
- Usar `{localappdata}` como destino padrão do instalador.
- Usar `PrivilegesRequired=lowest` para evitar necessidade de admin.
- Se for obrigatório instalar em `Program Files`, separar dados de runtime para `%APPDATA%` ou `%LOCALAPPDATA%`.

### 18.4 Hidden imports e módulos com lazy loading

**Sintoma:** `ModuleNotFoundError` para módulos Selenium ou internos ao rodar o `.exe`, mesmo funcionando perfeitamente no ambiente de desenvolvimento.

**Causa raiz:** PyInstaller faz análise estática de imports. Ele não detecta:

- Selenium usa `__getattr__` em pacotes para lazy loading de submodules.
- Imports dinâmicos via `importlib` ou `__import__`.
- Imports dentro de funções (como os `from src.aplicacao.automacao_tabela_cliente import ...` dentro de `worker.py.run()`).

**Solução aplicada no `build.spec`:**

```python
from PyInstaller.utils.hooks import collect_submodules

# Coleta automática de todos os submodules do Selenium
selenium_hiddenimports = collect_submodules("selenium")

hiddenimports=[
    *selenium_hiddenimports,
    # Lista explícita de TODOS os módulos internos do projeto
    "src.aplicacao.automacao_tabela_cliente",
    "src.aplicacao.gestor_checkpoint",
    "src.aplicacao.modo_execucao",
    "src.infraestrutura.acoes_navegador",
    "src.infraestrutura.caminhos",
    # ... todos os módulos listados individualmente
    "config",
]
```

**Lição para futuras automações:**

- Sempre usar `collect_submodules("selenium")` no `.spec`.
- Listar explicitamente **todos** os módulos do projeto em `hiddenimports`, mesmo que pareça redundante.
- Imports dentro de funções (pattern usado para evitar circular imports) **não são detectados** pelo PyInstaller — devem entrar na lista manual.
- Testar o `.exe` gerado em ambiente limpo (sem Python instalado) antes de distribuir.

### 18.5 Bundling de fontes e ícones com fallback gracioso

**Sintoma:** aplicação abre sem fonte customizada ou sem ícone, sem mensagem de erro.

**Causa raiz:** o `build.spec` precisa declarar explicitamente quais arquivos de `public/` devem ser empacotados na seção `datas`. Sem isso, o PyInstaller simplesmente não inclui os assets.

**Solução aplicada:**

No `build.spec`:

```python
datas=[
    (str(ROOT / "public" / "app-icon.ico"), "public"),
    (str(ROOT / "public" / "app-icon.png"), "public"),
    (str(ROOT / "public" / "logo.png"), "public"),
    (str(ROOT / "public" / "fonts" / "Manrope-Variable.ttf"), "public/fonts"),
    (str(ROOT / "public" / "fonts" / "OFL-Manrope.txt"), "public/fonts"),
]
```

No código, todo carregamento de asset tem fallback:

```python
# Fonte: fallback para fontes do sistema
if caminho_fonte.exists():
    # carrega Manrope
else:
    app.setFont(QFont("Segoe UI", 10))

# Logo: fallback para texto
if caminho_logo.exists():
    # carrega imagem
else:
    rotulo.setText("Rodogarcia")
```

**Lição para futuras automações:**

- O `.spec` é a única forma de dizer ao PyInstaller para incluir arquivos não-Python. Sem isso, fontes e ícones ficam de fora.
- Todo carregamento de recurso visual deve ter fallback para texto ou fonte do sistema.
- O segundo campo da tupla em `datas` define o caminho relativo dentro do bundle (`_internal/public/`).
- O ícone do `.exe` é definido separadamente no bloco `EXE(icon=...)`.

### 18.6 Distribuição segura do `.env`

**Sintoma:** aplicação abre mas não consegue fazer login (credenciais vazias).

**Causa raiz:** o `.env` não é empacotado pelo PyInstaller (e não deve ser, pois contém credenciais). Ele precisa ser distribuído separadamente e ficar ao lado do `.exe`.

**Solução aplicada:**

- `build.bat` copia automaticamente o `.env` para o `dist/`:

```batch
if exist .env (
    copy /Y .env "%DIST_DIR%\.env" >nul
)
```

- `config.py` trata `.env` ausente sem crash:

```python
if not arquivo_env.exists():
    return  # variáveis ficam com defaults vazios
```

- Todas as variáveis têm defaults seguros:

```python
URL_LOGIN = os.getenv("URL_LOGIN", "")
HEADLESS = os.getenv("HEADLESS", "false").lower() in {"1", "true"}
```

**Lição para futuras automações:**

- O `.env` nunca deve entrar no `build.spec`. Ele é específico por ambiente.
- O `build.bat` deve copiar o `.env` para o dist após o build.
- O instalador distribui o `.env` junto com o app, mas cada máquina pode ter o seu.
- Toda variável de ambiente deve ter default seguro para que a ausência do `.env` não cause crash.
- Considerar um primeiro-uso que solicite credenciais via UI quando `.env` não existe.

### 18.7 Automação do build e geração de instalador

**Sintoma:** builds manuais geram artefatos residuais, versões misturadas e instaladores desatualizados.

**Solução aplicada no `build.bat`:**

```text
1. Matar processo existente do .exe (evita arquivo em uso)
2. Remover build/, dist/, installer/ antigos
3. Executar PyInstaller com --clean --noconfirm
4. Copiar .env para dist/
5. Detectar Inno Setup (ISCC) em paths conhecidos
6. Se não encontrar, instalar via winget automaticamente
7. Gerar instalador .exe
8. Reportar resultado
```

**Lição para futuras automações:**

- Sempre ter um script de build que faça limpeza completa antes de rebuildar.
- O script deve matar instâncias em execução do app (senão `.exe` fica travado pelo Windows).
- Auto-detectar ferramentas de build (Inno Setup) e oferecer instalação automática via winget.
- O script não deve depender de estado anterior — cada build deve ser autocontido.

### 18.8 Arquitetura de duas fases com checkpoint

**Desafio arquitetural:** este projeto difere do template original (`rpa-tabela-cliente`) por ter processamento em duas fases:

- **Fase 1:** Criação de cópias de tabelas (operação de escrita no sistema alvo)
- **Fase 2:** Aplicação de reajustes nas cópias criadas (operação de modificação)

As fases são independentes e podem ser executadas separadamente via `ModoExecucao`:

```python
class ModoExecucao(Enum):
    MODO_COMPLETO = "completo"
    MODO_FASE1 = "fase1"
    MODO_FASE2 = "fase2"
```

**Impacto no empacotamento:**

- Ambos os processadores (`processador_fase_um.py`, `processador_fase_dois.py`) devem estar nos `hiddenimports`.
- O checkpoint (`gestor_checkpoint.py`) precisa persistir entre fases.
- A UI precisa mostrar progresso separado por fase.
- O Excel de entrada (`LeitorExcel`) tem duas abas — uma por fase.

**Lição para futuras automações:**

- Quando o fluxo tem fases distintas, modelar como classes separadas com processadores independentes.
- O checkpoint deve incluir hash do arquivo de entrada para invalidar execuções com dados diferentes.
- Modos de execução permitem reprocessar apenas uma fase sem refazer tudo.

### 18.9 Tabela consolidada de desafios e soluções

| # | Desafio | Sintoma | Arquivo afetado | Solução |
|---|---------|---------|-----------------|---------|
| 1 | Path resolution frozen vs. dev | Assets não encontrados | `caminhos.py`, `config.py`, `main.py`, `ui_main.py` | Dual-path: `RESOURCES_DIR` + `APP_DIR` |
| 2 | Ordem de criação de diretórios | `[Errno 2]` no logger | `caminhos.py`, `fabrica_registrador_execucao.py` | `mkdir` no import do módulo |
| 3 | Escrita em Program Files | `[Errno 2]` em qualquer escrita | `installer/*.iss` | Instalar em `{localappdata}` |
| 4 | Lazy imports não detectados | `ModuleNotFoundError` no exe | `build.spec` | `collect_submodules` + lista explícita |
| 5 | Assets não incluídos no bundle | App sem ícone ou fonte | `build.spec` | Seção `datas` com todos os assets |
| 6 | `.env` não distribuído | Login falha silenciosamente | `build.bat`, `config.py` | Copy automático + defaults seguros |
| 7 | Artefatos residuais de build | Versões misturadas | `build.bat` | Limpeza completa antes de rebuild |
| 8 | Duas fases com checkpoint | Reprocessamento parcial | `gestor_checkpoint.py`, `modo_execucao.py` | Hash de integridade + modos independentes |

### 18.10 Checklist de empacotamento para novas automações

- [ ] Criar `caminhos.py` com separação `RESOURCES_DIR` / `APP_DIR` desde o início.
- [ ] Garantir que **nenhum** módulo use `Path(__file__)` para acessar assets ou criar diretórios.
- [ ] Criar diretórios graváveis (`logs/`, `reports/`) no import de `caminhos.py`.
- [ ] Adicionar `mkdir` defensivo em qualquer código que abra arquivo para escrita.
- [ ] Listar **todos** os módulos internos em `hiddenimports` do `.spec`.
- [ ] Usar `collect_submodules("selenium")` para bibliotecas com lazy loading.
- [ ] Declarar todos os assets visuais na seção `datas` do `.spec`.
- [ ] Implementar fallback para fontes e ícones ausentes.
- [ ] Configurar instalador para `{localappdata}` com `PrivilegesRequired=lowest`.
- [ ] Automatizar cópia do `.env` no script de build.
- [ ] Testar **primeira execução em máquina limpa** (sem Python, sem diretórios pré-existentes).
- [ ] Testar com e sem `.env` presente.
- [ ] Verificar se o atalho de desktop aponta para o ícone correto (`_internal\public\app-icon.ico`).

---

## 19. Conclusão

O padrão mais valioso extraído deste projeto é o seguinte (somado agora aos aprendizados de distribuição real):

- o robô não foi organizado por “tipo de arquivo”, mas por responsabilidade operacional;
- o Selenium foi corretamente empurrado para infraestrutura;
- o fluxo foi modelado por caso de uso;
- a UI foi desacoplada via observador;
- a resiliência foi pensada em torno de grids reativas, erros por registro e evidência de execução;
- o repositório foi preparado para distribuição, suporte e operação contínua.

Se este projeto for usado como base definitiva para novas automações, a recomendação é preservar rigidamente:

1. `config.py` como registro central de seletores e flags;
2. `AcoesNavegador` como fachada de interação;
3. `paginas` para superfícies do sistema;
4. `servicos` para lógica operacional;
5. `aplicacao` para orquestração;
6. `monitoramento` para contrato de observação;
7. `infraestrutura` para logs, traces, screenshots e retenção;
8. UI em thread separada, quando houver operação humana.

Esse é o núcleo arquitetural que realmente merece virar template.
