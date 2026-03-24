# Padrao DOM-First e Resposta Visual para RPAs Selenium

## Objetivo

Este documento registra a melhoria aplicada no fluxo de exclusao do modulo `auto_delete_clientes` e transforma essa correcao em um padrao reaproveitavel para proximos RPAs.

A ideia central e simples:

- o RPA nao deve reagir ao tempo;
- o RPA deve reagir ao que o DOM mostra;
- depois que uma acao critica e iniciada, a mesma unidade visual nao pode receber a mesma acao de novo sem uma nova evidencia do DOM.

Esse ajuste melhorou o "reflexo" da automacao porque o robô passou a responder ao estado real da tela, e nao a suposicoes baseadas em `sleep`.

---

## Problema original

No fluxo antigo, o script clicava em `Excluir`, confirmava o modal e, se a tela demorasse a responder, podia entrar em uma nova tentativa na mesma linha.

Isso gerava um efeito perigoso:

1. a primeira solicitacao ainda estava em processamento no servidor;
2. a linha ainda continuava visivel por alguns segundos;
3. o robô interpretava isso como "nao aconteceu nada";
4. um novo clique era disparado;
5. o sistema respondia com mensagens como `Essa solicitacao ja esta em andamento`.

O erro nao estava apenas no clique em si.

O erro real estava no modelo mental do fluxo:

- o codigo tratava ausencia imediata de mudanca como falha;
- a interface ainda nao tinha dado resposta visual final;
- a automacao tentava adivinhar o estado do sistema antes do DOM concluir a transicao.

---

## O que mudou

O fluxo corrigido passou a usar um contrato claro entre automacao e interface.

### 1. Uma tentativa por linha

Cada linha recebe no maximo uma tentativa de exclusao.

Depois que a exclusao daquela linha comeca:

- nao existe segundo clique;
- nao existe repeticao da mesma acao;
- nao existe "nova tentativa" na mesma linha por timeout ou por popup de erro.

Isso elimina a origem do erro de concorrencia visual.

### 2. O DOM virou a fonte de verdade

Depois do clique, o script nao decide mais pelo tempo.

Ele monitora o DOM continuamente e espera um dos tres estados finais:

- `sucesso`: a linha sumiu da tabela;
- `erro`: apareceu popup de erro;
- `ja_processado`: apareceu popup informando que a solicitacao ja foi tratada;
- `timeout`: nada mudou visualmente dentro do prazo.

### 3. Espera real por resposta do sistema

Em vez de confiar em `sleep` fixo, o fluxo usa uma janela de observacao de ate `90s`.

Durante essa janela, ele observa:

- existencia da linha original;
- popup `swal2`;
- mudanca estrutural da tabela;
- desaparecimento de feedbacks visuais residuais.

### 4. Identidade da linha no DOM

Para evitar que a automacao "perca a referencia" da linha em tabelas dinamicas, o fluxo cria uma chave estavel baseada em atributos como:

- `data-id`;
- `row_key`;
- `row-key`;
- fallback por nome/texto/indice.

Isso e importante porque, em grids reativas, o indice visual pode mudar apos renderizacao parcial.

### 5. Tratamento explicito da resposta visual

A automacao passou a distinguir:

- popup de erro de negocio;
- popup de item ja processado;
- remocao real da linha;
- ausencia de resposta visual.

Ou seja: o robô nao apenas "espera".
Ele interpreta a resposta da tela.

---

## Leitura do DOM como sinal operacional

Uma boa automacao Selenium nao deve pensar em "passos", e sim em "sinais".

No caso desta melhoria, os sinais relevantes foram:

### Sinal de sucesso

O sucesso nao e "eu cliquei".

O sucesso e:

- a linha realmente nao existe mais na grid;
- essa ausencia se mantem por um pequeno periodo de estabilidade;
- o sistema deixou de apresentar resposta pendente para aquele item.

### Sinal de erro

O erro nao e "lancou excecao Python".

O erro funcional pode estar no proprio front:

- popup `swal2` com texto de erro;
- mensagem de solicitacao em andamento;
- mensagem pedindo para aguardar retorno;
- aviso de processamento ja existente.

### Sinal de timeout

Timeout nao significa necessariamente que o backend falhou.

Significa:

- o front nao entregou sinal suficiente para decisao;
- a linha nao sumiu;
- nenhum popup util apareceu;
- a automacao nao pode assumir sucesso nem tentar repetir a acao.

Essa diferenca e valiosa para diagnostico.

---

## Por que isso melhorou o reflexo do RPA

O ganho principal foi comportamental.

Antes:

- o robô executava;
- esperava um tempo;
- nao via mudanca imediata;
- tentava de novo.

Agora:

- o robô executa uma vez;
- entra em observacao;
- deixa a tela "responder";
- toma decisao usando evidencia visual.

Na pratica, isso torna o RPA:

- menos ansioso;
- menos destrutivo;
- menos dependente de tempo fixo;
- mais alinhado ao ciclo real do sistema;
- mais previsivel em sistemas lentos.

Esse e um padrao que vale para exclusao, aprovacao, envio, salvamento, importacao, geracao de relatorio e qualquer acao assincrona em interface web.

---

## Modelo reutilizavel para proximos RPAs

Sempre que houver uma acao critica na interface, use este roteiro.

### 1. Defina a unidade de trabalho visual

Exemplos:

- uma linha da tabela;
- um card;
- um pedido;
- um anexo;
- uma etapa de workflow.

Essa unidade precisa ter uma identidade observavel no DOM.

### 2. Defina a regra de irrepetibilidade

Pergunta obrigatoria:

`Depois que eu disparar esta acao, em que condicao fica proibido clicar de novo?`

Para fluxos assincronos, a resposta quase sempre sera:

- imediatamente apos o clique de confirmacao;
- ate o DOM devolver um estado final claro.

### 3. Mapeie os estados finais visuais

Para cada acao critica, liste:

- sucesso visual;
- erro visual;
- bloqueio visual;
- timeout sem resposta.

Se isso nao estiver mapeado, o RPA vai cair em tentativa cega.

### 4. Espere por sinais, nao por tempo

Substitua:

```python
click()
sleep(5)
```

por algo conceitualmente assim:

```python
click()
aguardar_ate_que(
    item_sumiu_do_dom
    or popup_erro_apareceu
    or popup_ja_processado_apareceu
    or timeout
)
```

### 5. Registre a transicao da acao

Boas automacoes deixam claro no log:

- quando a acao comecou;
- o que esta sendo observado;
- qual sinal apareceu;
- qual decisao foi tomada;
- que nao havera repeticao daquela unidade.

---

## Checklist para futuros RPAs

Antes de automatizar uma acao que muda estado no sistema, valide:

- Existe um identificador estavel para o item no DOM?
- Eu sei qual elemento some, muda ou aparece no sucesso?
- Eu sei qual popup, toast ou banner indica erro?
- Existe um estado de "ja esta em andamento" ou "ja foi processado"?
- O codigo impede segunda tentativa na mesma unidade?
- O wait observa o DOM de forma continua?
- O timeout leva a log e skip, e nao a reclick?

Se alguma resposta for "nao", o fluxo ainda esta fraco.

---

## Anti-padroes que esta melhoria evita

### 1. Retry impulsivo

Erro classico:

- clicou;
- nao mudou em poucos segundos;
- clicou de novo.

Esse comportamento cria duplicidade, concorrencia e estados incoerentes.

### 2. Sleep como controle principal

`sleep` pode ser apoio pequeno entre micro-acoes visuais, mas nao pode ser a base da decisao de negocio.

### 3. Sucesso inferido por ausencia de erro

Se nao houve erro visual, isso nao prova sucesso.

O correto e exigir evidencia positiva:

- linha sumiu;
- estado mudou;
- mensagem de sucesso apareceu.

### 4. Reprocessar o mesmo item sem nova leitura

Se a automacao nao reidentifica o item no DOM, ela pode atuar sobre referencia antiga, indice antigo ou elemento stale.

---

## Exemplo de maquina de estados

Este padrao pode ser pensado como uma maquina de estados simples:

```text
LINHA_ENCONTRADA
  -> clicar_excluir_uma_vez
  -> confirmar_modal
  -> OBSERVANDO_DOM

OBSERVANDO_DOM
  -> linha_sumiu ............. SUCESSO
  -> popup_erro .............. ERRO_TRATADO
  -> popup_ja_processado ..... JA_PROCESSADO
  -> 90s_sem_resposta ........ TIMEOUT

SUCESSO / ERRO_TRATADO / JA_PROCESSADO / TIMEOUT
  -> pular_para_proxima_linha
```

O ponto mais importante dessa maquina:

depois que entra em `OBSERVANDO_DOM`, nao volta para `clicar_excluir_uma_vez`.

---

## Aplicacao pratica alem deste modulo

Esse padrao pode ser reaproveitado quando voce for automatizar:

- exclusao de registros;
- aprovacao de pedidos;
- envio de formularios;
- geracao de documentos;
- upload e importacao;
- disparo de processamento batch;
- operacoes com modal de confirmacao;
- telas que usam `SweetAlert2`, `toast`, spinner ou grid reativa.

Sempre que existir atraso entre clique e resultado final, este modelo e preferivel ao retry direto.

---

## Resultado arquitetural

Esta melhoria nao foi apenas um ajuste de bug.

Ela consolidou um principio de arquitetura para RPAs web:

> acao critica deve ser unica, e a continuidade do fluxo deve ser guiada pela resposta visual do DOM.

Esse principio aumenta:

- confiabilidade;
- rastreabilidade;
- seguranca operacional;
- facilidade de diagnostico;
- reutilizacao de padroes em novos robos.

---

## Onde isso foi aplicado

Implementacao principal:

- `auto_delete_clientes/pagina_exclusao.py`

Ponto de configuracao do timeout:

- `auto_delete_clientes/config.py`

Esse material deve servir como referencia sempre que um novo RPA precisar interagir com interfaces lentas, assincronas ou com feedback visual tardio.
