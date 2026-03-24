TABELA REAJUSTE.xlsx para consultar, mas ela pode mudar a cada execucao da automacao, vai depender da demanda do financeiro, mas basicamente o que vai se manter no geral sao as colunas e componentes, mas sempre tem que ler ate o final das linhas

Você vai receber um **Excel com duas abas**.

---

## 📄 Aba 1 — Dados principais

Essa aba contém:

* **DATA VIGÊNCIA**
  Exemplo: `01/04/2026 - 31/03/2027`
  Esse intervalo será usado para definir a vigência das tabelas.

* **NOME DA TABELA**
  Lista com todos os nomes das tabelas que precisam ser copiadas.

* **PERCENTUAL**
  Exemplo: `9,80%`
  Esse valor será utilizado no reajuste dos campos.

---

## 📄 Aba 2 — Componentes de reajuste

Essa aba define onde aplicar o reajuste, dividida em três tipos:

* **Reajustar Taxas**
* **Reajustar Excedentes**
* **Reajustar Adicionais**

Cada linha contém:

* **ABA** → indica o tipo (Taxa, Excedente ou Adicional)
* **NOME DA TAXA** → campo específico que será reajustado
  Exemplo:

  * Min. frete peso
  * Valor p/ Kg
  * TAR PESO
  * etc.

---

## 🔄 Fluxo do robô

### 1. Login

* Acessar o sistema e realizar login

---

### 2. Loop de criação das cópias

Para cada linha da **Aba 1**:

1. Ler:

   * Nome da tabela
2. Criar uma cópia da tabela
3. Ajustar o nome da cópia:

   * Remover “- cópia”
   * Manter o nome igual ao do Excel

---

### 3. Aplicar vigência

Ainda dentro do loop de cada tabela:

1. Ler a **DATA VIGÊNCIA**
2. Separar:

   * Data inicial
   * Data final
3. Aplicar essas datas na tabela copiada

Objetivo: fazer a tabela aparecer corretamente na listagem de clientes.

---

### 4. Reajuste de valores

Para cada tabela copiada:

1. Clicar na opção de **reajustar valores**

2. Ler o **PERCENTUAL** da Aba 1

---

### 5. Loop de reajuste por tipo

Para cada grupo da **Aba 2**:

#### 5.1 Reajustar Taxas

* Acessar a aba **Taxas**
* Para cada campo listado como “Reajustar Taxas”:

  * Localizar o campo na tela
  * Aplicar o percentual

---

#### 5.2 Reajustar Excedentes

* Acessar a aba **Excedentes**
* Para cada campo listado como “Reajustar Excedentes”:

  * Localizar o campo
  * Aplicar o percentual

---

#### 5.3 Reajustar Adicionais

* Acessar a aba **Adicionais**
* Para cada campo listado como “Reajustar Adicionais”:

  * Localizar o campo
  * Aplicar o percentual

---

## 📌 Resumo do fluxo completo

1. Login no sistema
2. Ler Excel
3. Para cada tabela:

   * Criar cópia
   * Ajustar nome
   * Aplicar vigência
   * Entrar em reajuste
   * Aplicar percentual em:

     * Taxas
     * Excedentes
     * Adicionais

---



fazer login na plataforma
https://rodogarcia.eslcloud.com.br/users/sign_in

**IMPORTANTE:** Credenciais devem ser configuradas no arquivo `.env`, nunca no código ou na documentação.
<input type="submit" name="commit" value="Entrar" class="btn btn-primary" data-disable-with="Entrar">


1 - clicar em cadastros

<a href="javascript:;" tabindex="-1">Cadastros</a>


2 - clicar em tabelas de preço

<a class="" href="javascript:;" tabindex="-1"><i class="fa fa-money-bill-alt"></i><span class="text-icon ">Tabelas de preço</span></a>

3 - clicar em tabelas de cliente

<a class="" href="/customer_price_tables" tabindex="-1">Tabelas de cliente</a>

4 - desmarcar a opcao que está dentro do input Filial Responsável

<ul class="select2-selection__rendered"><span class="select2-selection__clear">×</span><li class="select2-selection__choice" title="SPO - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA"><span class="select2-selection__choice__remove" role="presentation">×</span>SPO - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA</li><li class="select2-search select2-search--inline"><input class="select2-search__field" type="search" tabindex="0" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" role="textbox" aria-autocomplete="list" placeholder="" style="width: 0.75em;"></li></ul>


5 - em ativa

<div class="form-group select optional search_price_tables_active"><label class="select optional" for="search_price_tables_active">Ativa</label><select class="form-control select optional input-sm select2-base select2-hidden-accessible" name="search[price_tables][active]" id="search_price_tables_active" tabindex="-1" aria-hidden="true"><option value="" label=" "></option>
<option value="true">Sim</option>
<option value="false">Não</option></select><span class="select2 select2-container select2-container--default" dir="ltr" style="width: 166px;"><span class="selection"><span class="select2-selection select2-selection--single" role="combobox" aria-haspopup="true" aria-expanded="false" tabindex="0" aria-labelledby="select2-search_price_tables_active-container"><span class="select2-selection__rendered" id="select2-search_price_tables_active-container"><span class="select2-selection__placeholder">Selecione</span></span><span class="select2-selection__arrow" role="presentation"><b role="presentation"></b></span></span></span><span class="dropdown-wrapper" aria-hidden="true"></span></span></div>


vai clicar no option

<span class="select2-selection__arrow" role="presentation"><b role="presentation"></b></span>

e vai selecionar SIM e marcar

<li class="select2-results__option" id="select2-search_price_tables_active-result-4k43-true" role="treeitem" aria-selected="false">Sim</li>



9 - após isso, novamente no excel que recebe no inicio da operacao, na coluna NOME DA TABELA, vai pegar o primeiro nome da primeira linha (atencao para um loop que pode surgir aqui)

e vai jogar esse nome dentro desse input abaixo

<input class="form-control string optional input-sm" type="text" name="search[price_tables][name]" id="search_price_tables_name">

10 - ao jogar o nome dentro vai clicar aqui para pesquisar

<button tabindex="-1" id="submit" class="btn btn-primary vue-button btn-sm" type="submit"><i class="fa fa-search"></i></button>


11 - agora dentro dessa tabela abaixo vai aparecer algumas linhas

<div class="vue-paginated-table col-sm-12"> <div class="no-margin-top no-margin-bottom lbl-overflow-auto"> <table cellspacing="0" class="table table-condensed table-hover table-striped no-margin-bottom table-bordered"> <thead>  <tr>  <th style="width: 200px;"> <div class="cursor-pointer pull-right"><i style="" class="fa fa-sort-up"></i></div> <div class="table-text" title="Nome" style="width: 180px;">Nome</div> </th><th style="width: 65px;"> <div class="cursor-pointer pull-right"><i style="" class="fa fa-sort font-grey-silver"></i></div> <div class="table-text" title="Código" style="width: 45px;">Código</div> </th><th style="width: 180px;">  <div class="table-text" title="Filial Responsável" style="width: 180px;">Filial Responsável</div> </th><th style="width: 80px;">  <div class="table-text" title="Modal" style="width: 80px;">Modal</div> </th><th style="width: 100px;">  <div class="table-text" title="Faixa principal" style="width: 100px;">Faixa principal</div> </th><th style="width: 130px;">  <div class="table-text" title="Validade" style="width: 130px;">Validade</div> </th><th style="width: 80px;">  <div class="table-text" title="Tipo" style="width: 80px;">Tipo</div> </th><th class="text-right">  <div title="Clientes">Clientes</div> </th><th class="lbl-icon-column">  <div title="Ativa">Ativa</div> </th> <th class="vue-actions-column text-center"> <a class="green-dark btn-outline btn vue-button" style="padding: 2px 5px" title="Exportar" id="btn-export-xlsx" tabindex="-1"> <i class="fa fa-file-excel"></i> </a> </th> </tr> </thead> <tbody> <tr class="vue-item" data-id="56506" row_key="0" style="height: 30px;">  <td> <div class="table-text" title="FRANCHINI" style="width: 200px;">FRANCHINI</div> </td><td> <div class="table-text" title="" style="width: 65px;"></div> </td><td> <div class="table-text" title="MTZ - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA" style="width: 180px;">MTZ - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA</div> </td><td> <div class="table-text" title="Rodoviário" style="width: 80px;">Rodoviário</div> </td><td> <div class="table-text" title="Peso taxado" style="width: 100px;">Peso taxado</div> </td><td> <div class="table-text" title="01/04/25 - 31/03/26" style="width: 130px;">01/04/25 - 31/03/26</div> </td><td> <div class="table-text" title="Normal" style="width: 80px;">Normal</div> </td><td class="text-right"> <div title="3">3</div> </td><td class="lbl-icon-column"> <div><i class="fa fa-check-circle font-green-meadow" title="Ativada"></i></div> </td>   <td class="no-padding-bottom" style="padding-top: 2px"> <div class="vue-dropdown-group"> <div class="btn-group"> <a class="blue-chambray btn-outline btn-xs no-margin-right btn vue-button" title="Editar" href="customer_price_tables/56506/edit"><i class="fa fa-pencil-alt"></i></a> <button type="button" style="max-width: 25px;" class="btn blue-chambray btn-outline btn-xs dropdown-toggle more-actions vue-dropdown-item no-margin-right" data-toggle="dropdown"><i class="fa fa-angle-down"></i></button> <ul class="dropdown-menu vue-dropdown-menu pull-right" role="menu"> <li title="Arquivos anexos"> <a class="dropdown-link"><i class="fa fa-paperclip"></i><span class="text-icon ">Anexos</span></a> </li><li title="Duplicar tabela"> <a class="dropdown-link"><i class="fa fa-clone font-blue-steel"></i><span class="text-icon ">Duplicar tabela</span></a> </li><li title="Exportar"> <a class="dropdown-link"><i class="fa fa-file-excel font-green-dark"></i><span class="text-icon ">Exportar</span></a> </li><li title="Exportar"> <a class="dropdown-link"><i class="fa fa-file-excel font-green-dark"></i><span class="text-icon ">Exportar C/ Negociação</span></a> </li><li> <a class="dropdown-link"><i class="fa fa-upload font-purple-sharp"></i><span class="text-icon ">Importar Dados</span></a> </li><li title="Reajuste"> <a class="dropdown-link"><i class="fa fa-chart-line font-yellow-gold"></i><span class="text-icon ">Reajuste</span></a> </li><li title="Histórico de reajustes"> <a class="dropdown-link"><i class="fa fa-list"></i><span class="text-icon ">Histórico de reajustes</span></a> </li><li title="Reajuste Negociação"> <a class="dropdown-link"><i class="fa fa-handshake font-yellow-gold"></i><span class="text-icon ">Reajuste Negociação</span></a> </li><li> <a class="dropdown-link"><i class="fa fa-history font-blue-madison"></i><span class="text-icon ">Histórico</span></a> </li><li title="Excluir"> <a class="dropdown-link"><i class="fa fa-trash-alt font-red-soft"></i><span class="text-icon ">Excluir</span></a> </li> </ul> </div> </div>  </td> </tr><tr class="vue-item" data-id="44338" row_key="1" style="height: 30px;">  <td> <div class="table-text" title="FRANCHINI " style="width: 200px;">FRANCHINI </div> </td><td> <div class="table-text" title="" style="width: 65px;"></div> </td><td> <div class="table-text" title="MTZ - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA" style="width: 180px;">MTZ - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA</div> </td><td> <div class="table-text" title="Rodoviário" style="width: 80px;">Rodoviário</div> </td><td> <div class="table-text" title="Peso taxado" style="width: 100px;">Peso taxado</div> </td><td> <div class="table-text" title="01/04/24 - 31/03/25" style="width: 130px;">01/04/24 - 31/03/25</div> </td><td> <div class="table-text" title="Normal" style="width: 80px;">Normal</div> </td><td class="text-right"> <div title="2">2</div> </td><td class="lbl-icon-column"> <div><i class="fa fa-times-circle font-red-soft" title="Desativada"></i></div> </td>   <td class="no-padding-bottom" style="padding-top: 2px"> <div class="vue-dropdown-group"> <div class="btn-group"> <a class="blue-chambray btn-outline btn-xs no-margin-right btn vue-button" title="Editar" href="customer_price_tables/44338/edit"><i class="fa fa-pencil-alt"></i></a> <button type="button" style="max-width: 25px;" class="btn blue-chambray btn-outline btn-xs dropdown-toggle more-actions vue-dropdown-item no-margin-right" data-toggle="dropdown"><i class="fa fa-angle-down"></i></button> <ul class="dropdown-menu vue-dropdown-menu pull-right" role="menu"> <li title="Arquivos anexos"> <a class="dropdown-link"><i class="fa fa-paperclip"></i><span class="text-icon ">Anexos</span></a> </li><li title="Duplicar tabela"> <a class="dropdown-link"><i class="fa fa-clone font-blue-steel"></i><span class="text-icon ">Duplicar tabela</span></a> </li><li title="Exportar"> <a class="dropdown-link"><i class="fa fa-file-excel font-green-dark"></i><span class="text-icon ">Exportar</span></a> </li><li title="Exportar"> <a class="dropdown-link"><i class="fa fa-file-excel font-green-dark"></i><span class="text-icon ">Exportar C/ Negociação</span></a> </li><li> <a class="dropdown-link"><i class="fa fa-upload font-purple-sharp"></i><span class="text-icon ">Importar Dados</span></a> </li><li title="Reajuste"> <a class="dropdown-link"><i class="fa fa-chart-line font-yellow-gold"></i><span class="text-icon ">Reajuste</span></a> </li><li title="Histórico de reajustes"> <a class="dropdown-link"><i class="fa fa-list"></i><span class="text-icon ">Histórico de reajustes</span></a> </li><li title="Reajuste Negociação"> <a class="dropdown-link"><i class="fa fa-handshake font-yellow-gold"></i><span class="text-icon ">Reajuste Negociação</span></a> </li><li> <a class="dropdown-link"><i class="fa fa-history font-blue-madison"></i><span class="text-icon ">Histórico</span></a> </li><li title="Excluir"> <a class="dropdown-link"><i class="fa fa-trash-alt font-red-soft"></i><span class="text-icon ">Excluir</span></a> </li> </ul> </div> </div>  </td> </tr> <tr class="vue-blank-item" style="height: 510px;"> <td colspan="10">&nbsp;</td> </tr> </tbody>    <tbody style="border-top: 0px" class="footer"> <tr> <td class="vue-footer no-padding" colspan="10">  <div class="vue-paginated-table-footer vue-text-right"> <span class="margin-right"> <span>Qtd:&nbsp;</span> <select class="bg-white select input-sm"> <option value="auto">Auto</option> <option value="10">10</option> <option value="20">20</option> <option value="30">30</option> <option value="50">50</option> </select> </span> <span class="entries-info"> Exibindo 1 - 2 de 2 </span>  <span class="btn-group vue-pagination-buttons margin-left"> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-double-left"></i></button> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-left"></i></button> <button type="button" class="vue-page-item btn btn-default blue-chambray"> 1 </button> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-right"></i></button> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-double-right"></i></button> </span>   </div> </td> </tr> </tbody> </table> </div> </div>



12 - voce vai clicar nessa seta aqui

<button type="button" style="max-width: 25px;" class="btn blue-chambray btn-outline btn-xs dropdown-toggle more-actions vue-dropdown-item no-margin-right" data-toggle="dropdown"><i class="fa fa-angle-down"></i></button>

13 - procurar por dupplicar tabbela

<a class="dropdown-link"><i class="fa fa-clone font-blue-steel"></i><span class="text-icon ">Duplicar tabela</span></a>

14 - ao abrir um card vc vai clicar em 
<span class="switchery switchery-default" style="box-shadow: rgb(223, 223, 223) 0px 0px 0px 0px inset; border-color: rgb(223, 223, 223); background-color: rgb(255, 255, 255); transition: border 0.4s, box-shadow 0.4s;"><small style="left: 0px; transition: background-color 0.4s, left 0.2s;"></small></span>

15 - depois que clicou vai clicar em SIM
<button type="button" class="swal2-confirm swal2-styled" aria-label="" style="display: inline-block; background-color: rgb(70, 117, 149); border-left-color: rgb(70, 117, 149); border-right-color: rgb(70, 117, 149);" id="swal-confirm">Sim</button>

16 - depois dessa etapa em alguns instantes vai aparecer outro card escrito: Cópia finaliza e se deseja editar a copia,

<button type="button" class="swal2-confirm swal2-styled" aria-label="" style="display: inline-block; background-color: rgb(70, 117, 149); border-left-color: rgb(70, 117, 149); border-right-color: rgb(70, 117, 149);" id="swal-confirm">Sim</button>

necessario tert um tempo para aguardar esse card pois pode levar alguns instantes

17 - vai abrir uma tela de edicao, onde nesse campo

<div class="form-group string required customer_price_table_name"><label class="string required" for="customer_price_table_name"><abbr title="obrigatório">*</abbr> Nome</label><input class="form-control string required input-sm" type="text" name="customer_price_table[name]" id="customer_price_table_name"><p class="help-block"></p></div>

vai ter o nome que vc pegou no excel, exemplo que estamos usando agora é o FRANCHINI, mas pode ser qualquer nome, pq vai depender de qual linha vc já esta, e vai estar ao lado do nome  - Cópia

ou seja, FRANCHINI - Cópia

<input class="form-control string required input-sm" type="text" name="customer_price_table[name]" id="customer_price_table_name">

dentro desse input vc vai colocar o nome novamente, ate para apgar esse - Cópia, entao melhor apagar tudo la e colocar o nome apenas FRANCHINI

18 - em parametrizacao

<a class="accordion-toggle collapsed" data-toggle="collapse" href="#parameters-list" id="parameters_accordion" tabindex="-1">Parametrizações</a>

vai clicar na seta para mostrar mais informacoes

<::after></::after>


19 - nas datas que irei enviar, vc vai colocar as datas que recebeu no excel

<div class="form-group calendar optional customer_price_table_effective_since"><label class="calendar optional" for="customer_price_table_effective_since">Válida de</label><span class="input-group date input-icon right"><i class="far fa-calendar-alt"></i><input class="form-control calendar optional date-picker form-control input-sm input-sm masked" type="text" name="customer_price_table[effective_since]" id="customer_price_table_effective_since"></span><p class="help-block"></p></div>

01/04/2026


e


<div class="form-group calendar optional customer_price_table_effective_until"><label class="calendar optional" for="customer_price_table_effective_until">Válida até</label><span class="input-group date input-icon right"><i class="far fa-calendar-alt"></i><input class="form-control calendar optional date-picker form-control input-sm input-sm masked" type="text" name="customer_price_table[effective_until]" id="customer_price_table_effective_until"></span><p class="help-block"></p></div>


31/03/2027


que tem no excel


20 - apos ter feito essa copia vai clicar em salvar

<a id="submit" class="btn btn-primary" tabindex="-1"><i class="fa fa-save"></i><span class="text-icon ">Salvar</span></a>

vai aparecer um card para clicar sim depois disso

<button type="button" class="swal2-confirm swal2-styled" aria-label="" style="display: inline-block; background-color: rgb(70, 117, 149); border-left-color: rgb(70, 117, 149); border-right-color: rgb(70, 117, 149);" id="swal-confirm">Sim</button>


aqui temos o primeiro loop, ideal é tentar cadastrar todos os NOME DA TABELA primeiro aqui nessa etapa, quando todas as copias de cada um do excel estiver pronto, ai podemos sair desse loop e ir para o proximo

para voltar e fazer outro loop de copia, se quiser pode clicar aqui para voltar 

<a class="" href="/customer_price_tables" tabindex="-1">Tabelas de cliente</a>

21 - vai clicar na seta ara descer mais oppcoes e mostrar um calendario

<button tabindex="-1" class="btn btn-primary vue-button btn-sm" type="button"><i class="fa fa-angle-up"></i></button>

22 - em calendario

<span class="date-range right"><input class="form-control date_range optional date-range-picker form-control input-sm input-sm masked" type="text" name="search[price_tables][effective_until]" id="search_price_tables_effective_until"></span>

vai clicar no input


<input class="form-control date_range optional date-range-picker form-control input-sm input-sm masked" type="text" name="search[price_tables][effective_until]" id="search_price_tables_effective_until">


que vai abrir esse card aqui

<div class="daterangepicker dropdown-menu ltr show-calendar opensleft active" style="display: block; top: 246.609px; right: 325.5px; left: auto;"><div class="calendar left"><div class="daterangepicker_input"><input class="input-mini form-control active" type="text" name="daterangepicker_start" value=""><i class="fa fa-calendar glyphicon glyphicon-calendar"></i><div class="calendar-time" style="display: none;"><div></div><i class="fa fa-clock-o glyphicon glyphicon-time"></i></div></div><div class="calendar-table"><table class="table-condensed"><thead><tr><th class="prev available"><i class="fa fa-chevron-left glyphicon glyphicon-chevron-left"></i></th><th colspan="5" class="month">Março 2026</th><th></th></tr><tr><th>Se</th><th>Te</th><th>Qu</th><th>Qu</th><th>Se</th><th>Sá</th><th>Do</th></tr></thead><tbody><tr><td class="off available" data-title="r0c0">23</td><td class="off available" data-title="r0c1">24</td><td class="off available" data-title="r0c2">25</td><td class="off available" data-title="r0c3">26</td><td class="off available" data-title="r0c4">27</td><td class="weekend off available" data-title="r0c5">28</td><td class="weekend available" data-title="r0c6">1</td></tr><tr><td class="available" data-title="r1c0">2</td><td class="available" data-title="r1c1">3</td><td class="available" data-title="r1c2">4</td><td class="available" data-title="r1c3">5</td><td class="available" data-title="r1c4">6</td><td class="weekend available" data-title="r1c5">7</td><td class="weekend available" data-title="r1c6">8</td></tr><tr><td class="available" data-title="r2c0">9</td><td class="available" data-title="r2c1">10</td><td class="available" data-title="r2c2">11</td><td class="available" data-title="r2c3">12</td><td class="available" data-title="r2c4">13</td><td class="weekend available" data-title="r2c5">14</td><td class="weekend available" data-title="r2c6">15</td></tr><tr><td class="available" data-title="r3c0">16</td><td class="today active start-date active end-date available" data-title="r3c1">17</td><td class="available" data-title="r3c2">18</td><td class="available" data-title="r3c3">19</td><td class="available" data-title="r3c4">20</td><td class="weekend available" data-title="r3c5">21</td><td class="weekend available" data-title="r3c6">22</td></tr><tr><td class="available" data-title="r4c0">23</td><td class="available" data-title="r4c1">24</td><td class="available" data-title="r4c2">25</td><td class="available" data-title="r4c3">26</td><td class="available" data-title="r4c4">27</td><td class="weekend available" data-title="r4c5">28</td><td class="weekend available" data-title="r4c6">29</td></tr><tr><td class="available" data-title="r5c0">30</td><td class="available" data-title="r5c1">31</td><td class="off available" data-title="r5c2">1</td><td class="off available" data-title="r5c3">2</td><td class="off available" data-title="r5c4">3</td><td class="weekend off available" data-title="r5c5">4</td><td class="weekend off available" data-title="r5c6">5</td></tr></tbody></table></div></div><div class="calendar right"><div class="daterangepicker_input"><input class="input-mini form-control" type="text" name="daterangepicker_end" value=""><i class="fa fa-calendar glyphicon glyphicon-calendar"></i><div class="calendar-time" style="display: none;"><div></div><i class="fa fa-clock-o glyphicon glyphicon-time"></i></div></div><div class="calendar-table"><table class="table-condensed"><thead><tr><th></th><th colspan="5" class="month">Abril 2026</th><th class="next available"><i class="fa fa-chevron-right glyphicon glyphicon-chevron-right"></i></th></tr><tr><th>Se</th><th>Te</th><th>Qu</th><th>Qu</th><th>Se</th><th>Sá</th><th>Do</th></tr></thead><tbody><tr><td class="off available" data-title="r0c0">30</td><td class="off available" data-title="r0c1">31</td><td class="available" data-title="r0c2">1</td><td class="available" data-title="r0c3">2</td><td class="available" data-title="r0c4">3</td><td class="weekend available" data-title="r0c5">4</td><td class="weekend available" data-title="r0c6">5</td></tr><tr><td class="available" data-title="r1c0">6</td><td class="available" data-title="r1c1">7</td><td class="available" data-title="r1c2">8</td><td class="available" data-title="r1c3">9</td><td class="available" data-title="r1c4">10</td><td class="weekend available" data-title="r1c5">11</td><td class="weekend available" data-title="r1c6">12</td></tr><tr><td class="available" data-title="r2c0">13</td><td class="available" data-title="r2c1">14</td><td class="available" data-title="r2c2">15</td><td class="available" data-title="r2c3">16</td><td class="available" data-title="r2c4">17</td><td class="weekend available" data-title="r2c5">18</td><td class="weekend available" data-title="r2c6">19</td></tr><tr><td class="available" data-title="r3c0">20</td><td class="available" data-title="r3c1">21</td><td class="available" data-title="r3c2">22</td><td class="available" data-title="r3c3">23</td><td class="available" data-title="r3c4">24</td><td class="weekend available" data-title="r3c5">25</td><td class="weekend available" data-title="r3c6">26</td></tr><tr><td class="available" data-title="r4c0">27</td><td class="available" data-title="r4c1">28</td><td class="available" data-title="r4c2">29</td><td class="available" data-title="r4c3">30</td><td class="off available" data-title="r4c4">1</td><td class="weekend off available" data-title="r4c5">2</td><td class="weekend off available" data-title="r4c6">3</td></tr><tr><td class="off available" data-title="r5c0">4</td><td class="off available" data-title="r5c1">5</td><td class="off available" data-title="r5c2">6</td><td class="off available" data-title="r5c3">7</td><td class="off available" data-title="r5c4">8</td><td class="weekend off available" data-title="r5c5">9</td><td class="weekend off available" data-title="r5c6">10</td></tr></tbody></table></div></div><div class="ranges"><ul><li data-range-key="Hoje" class="active">Hoje</li><li data-range-key="Ontem">Ontem</li><li data-range-key="Últimos 7 dias">Últimos 7 dias</li><li data-range-key="Últimos 30 dias">Últimos 30 dias</li><li data-range-key="Este mês">Este mês</li><li data-range-key="Mês passado">Mês passado</li><li data-range-key="Últimos 3 meses">Últimos 3 meses</li><li data-range-key="Customizar">Customizar</li></ul><div class="range_inputs"><button class="applyBtn btn btn-sm btn-primary" type="button">Confirmar</button> <button class="cancelBtn btn btn-sm btn-default" type="button">Limpar</button></div></div></div>



e dentro dele vai selecionar a data que vai estar dentro do excel que falei no inicio que vai recebber, na coluna DATA VIGENCIA


vai depender do excel, mas normalmente vai ter que vir nesse formato 01/04/2026 - 31/03/2027, onde dentro desse input acima de data vai precisar colocar exatamente como está no excel que ele recebeu


23 - depois que colocou a data corretamente, vai clicar em confirmar

<button class="applyBtn btn btn-sm btn-primary" type="button">Confirmar</button>


essa data acima é justamente para filtrar apenas as coppias criadas agora nesse loop acima para n dar erro de ter dados de outras coisas, filtrando isso, vai aparecer na tabela abaixo a lista de todos os nomes do excel que vc criou coppias, com isso, vai em cada um, um por um fazer esse loop que irei mandar agora


24 - clicar nessa seta

<button type="button" style="max-width: 25px;" class="btn blue-chambray btn-outline btn-xs dropdown-toggle more-actions vue-dropdown-item no-margin-right" data-toggle="dropdown"><i class="fa fa-angle-down"></i></button>

25 - e depois em reajuste

<a class="dropdown-link"><i class="fa fa-chart-line font-yellow-gold"></i><span class="text-icon ">Reajuste</span></a>

26 - considerar todos o trechos e vai clicar

<button tabindex="-1" class="btn btn-primary vue-button btn-xs" type="button"><i class="fa fa-square"></i><span class="text-icon ">Considerar todos os trechos</span></button>

nessa caixa de selecao

<::before></::before>

26 - prestar atencao nessa etapa aqui

<ul class="nav nav-tabs"><li class="index active" data-toggle="tab" href="#tab-fee" id="fee"><a class="btn" tabindex="-1">Reajustar Taxas</a></li><li class="groups" data-toggle="tab" href="#tab-overweights" id="overweights"><a class="btn" tabindex="-1">Reajustar Excedentes</a></li><li class="groups" data-toggle="tab" href="#tab-additionals" id="additionals"><a class="btn" tabindex="-1">Reajustar Adicionais</a></li></ul>



primeiro iremos começar em Reajustar Taxas

nela vc vai clicar em taxa

<span class="select2-selection__rendered" id="select2-readjust_form_fee-container"><span class="select2-selection__placeholder">Selecione</span></span>

e vai colar aqui, com base nessa tabela do excel onde tem >>> ABA <<< e tambem >>> NOME DA TAXA  <<

em ABA vc vai ter justamente explicando em qual dessas paginas estara 
<ul class="nav nav-tabs"><li class="index active" data-toggle="tab" href="#tab-fee" id="fee"><a class="btn" tabindex="-1">Reajustar Taxas</a></li><li class="groups" data-toggle="tab" href="#tab-overweights" id="overweights"><a class="btn" tabindex="-1">Reajustar Excedentes</a></li><li class="groups" data-toggle="tab" href="#tab-additionals" id="additionals"><a class="btn" tabindex="-1">Reajustar Adicionais</a></li></ul>

e em NOME DA TAXA o que vc tem que colocar dentro daqui

<span class="select2-selection__rendered" id="select2-readjust_form_fee-container"><span class="select2-selection__placeholder">Selecione</span></span>

em taxa

<span class="select2-selection__arrow" role="presentation"><b role="presentation"></b></span>


27 - em valor, com bbase no que vc leu na coluna percentual do excel, vai adicionar o valor aqui

<input class="form-control string decimal optional input-sm allow-negative masked" data-precision="2" type="decimal" name="readjust_form[value]" id="readjust_form_value">

por exemplo, 9,8 se estiver no excel


28 - depois disso vai e clica em adicionar

<button tabindex="-1" class="btn btn-primary vue-button btn-align-input pull-right" name="add_fee" type="button" disabled="Selecione a taxa" title="Selecione a taxa"><i class="fa fa-plus"></i><span class="text-icon ">Adicionar</span></button>

primeira linha de componentes onde temos as duas colunas >>> ABA <<< e tambem >>> NOME DA TAXA  <<
concluida, mas temos que fazer novamente, ler a proxima linha, ver se é Reajustar Taxas
Reajustar Excedentes
Reajustar Adicionais


adicionar o nome da taxa, o valor e adicionar, ate chegar ao fim, concluindo componentes daquela copia, vc vai clicar em salvar

<button tabindex="-1" id="save-btn" type="submit" class="btn btn-primary vue-button"><i class="fa fa-save"></i><span class="text-icon ">Salvar</span></button>


normalmente, as duas ultimas serao essas aqui

<a class="btn" tabindex="-1">Reajustar Excedentes</a>

<span class="select2-selection__rendered" id="select2-readjust_form_fee-container"><span class="select2-selection__placeholder">Selecione</span></span>

<input class="form-control string decimal optional input-sm allow-negative masked" data-precision="2" type="decimal" name="readjust_form[value]" id="readjust_form_value">


e tambem 

<a class="btn" tabindex="-1">Reajustar Adicionais</a>

<span class="select2-selection__rendered" id="select2-readjust_form_fee-container"><span class="select2-selection__placeholder">Selecione</span></span>

<input class="form-control string decimal optional input-sm allow-negative masked" data-precision="2" type="decimal" name="readjust_form[value]" id="readjust_form_value">




ao clicar em salvar vai aparecer um card na cara pedindo para clicar em ok vc clica vai voltar para a anterior e vc vai clicar aqui

<button class="close" aria_label="Close" data-dismiss="modal" type="button"><span></span></button>

ou aqui


<a color="btn-default" data-dismiss="modal" name="close_modal_button" class="btn btn-default" tabindex="-1"><i class="fa fa-times"></i><span class="text-icon ">Fechar</span></a>


para fechar



29 - com isso vc terminou o loop de uma copia, precisa ir para a proxima linha para fazer outro loop em outra copia aqui dentro

<div class="vue-paginated-table col-sm-12"> <div class="no-margin-top no-margin-bottom lbl-overflow-auto"> <table cellspacing="0" class="table table-condensed table-hover table-striped no-margin-bottom table-bordered"> <thead>  <tr>  <th style="width: 200px;"> <div class="cursor-pointer pull-right"><i style="" class="fa fa-sort-up"></i></div> <div class="table-text" title="Nome" style="width: 180px;">Nome</div> </th><th style="width: 65px;"> <div class="cursor-pointer pull-right"><i style="" class="fa fa-sort font-grey-silver"></i></div> <div class="table-text" title="Código" style="width: 45px;">Código</div> </th><th style="width: 180px;">  <div class="table-text" title="Filial Responsável" style="width: 180px;">Filial Responsável</div> </th><th style="width: 80px;">  <div class="table-text" title="Modal" style="width: 80px;">Modal</div> </th><th style="width: 100px;">  <div class="table-text" title="Faixa principal" style="width: 100px;">Faixa principal</div> </th><th style="width: 130px;">  <div class="table-text" title="Validade" style="width: 130px;">Validade</div> </th><th style="width: 80px;">  <div class="table-text" title="Tipo" style="width: 80px;">Tipo</div> </th><th class="text-right">  <div title="Clientes">Clientes</div> </th><th class="lbl-icon-column">  <div title="Ativa">Ativa</div> </th> <th class="vue-actions-column text-center"> <a class="green-dark btn-outline btn vue-button" style="padding: 2px 5px" title="Exportar" id="btn-export-xlsx" tabindex="-1"> <i class="fa fa-file-excel"></i> </a> </th> </tr> </thead> <tbody> <tr class="vue-item" data-id="65781" row_key="0" style="height: 30px;">  <td> <div class="table-text" title="FRIGODELISS " style="width: 200px;">FRIGODELISS </div> </td><td> <div class="table-text" title="" style="width: 65px;"></div> </td><td> <div class="table-text" title="MTZ - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA" style="width: 180px;">MTZ - RODOGARCIA TRANSPORTES RODOVIARIOS LTDA</div> </td><td> <div class="table-text" title="Rodoviário" style="width: 80px;">Rodoviário</div> </td><td> <div class="table-text" title="Peso taxado" style="width: 100px;">Peso taxado</div> </td><td> <div class="table-text" title="01/04/25 - 31/03/26" style="width: 130px;">01/04/25 - 31/03/26</div> </td><td> <div class="table-text" title="Normal" style="width: 80px;">Normal</div> </td><td class="text-right"> <div title="2">2</div> </td><td class="lbl-icon-column"> <div><i class="fa fa-check-circle font-green-meadow" title="Ativada"></i></div> </td>   <td class="no-padding-bottom" style="padding-top: 2px"> <div class="vue-dropdown-group"> <div class="btn-group"> <a class="blue-chambray btn-outline btn-xs no-margin-right btn vue-button" title="Editar" href="customer_price_tables/65781/edit"><i class="fa fa-pencil-alt"></i></a> <button type="button" style="max-width: 25px;" class="btn blue-chambray btn-outline btn-xs dropdown-toggle more-actions vue-dropdown-item no-margin-right" data-toggle="dropdown" aria-expanded="false"><i class="fa fa-angle-down"></i></button> <ul class="dropdown-menu vue-dropdown-menu pull-right" role="menu"> <li title="Arquivos anexos"> <a class="dropdown-link"><i class="fa fa-paperclip"></i><span class="text-icon ">Anexos</span></a> </li><li title="Duplicar tabela"> <a class="dropdown-link"><i class="fa fa-clone font-blue-steel"></i><span class="text-icon ">Duplicar tabela</span></a> </li><li title="Exportar"> <a class="dropdown-link"><i class="fa fa-file-excel font-green-dark"></i><span class="text-icon ">Exportar</span></a> </li><li title="Exportar"> <a class="dropdown-link"><i class="fa fa-file-excel font-green-dark"></i><span class="text-icon ">Exportar C/ Negociação</span></a> </li><li> <a class="dropdown-link"><i class="fa fa-upload font-purple-sharp"></i><span class="text-icon ">Importar Dados</span></a> </li><li title="Reajuste"> <a class="dropdown-link"><i class="fa fa-chart-line font-yellow-gold"></i><span class="text-icon ">Reajuste</span></a> </li><li title="Histórico de reajustes"> <a class="dropdown-link"><i class="fa fa-list"></i><span class="text-icon ">Histórico de reajustes</span></a> </li><li title="Reajuste Negociação"> <a class="dropdown-link"><i class="fa fa-handshake font-yellow-gold"></i><span class="text-icon ">Reajuste Negociação</span></a> </li><li> <a class="dropdown-link"><i class="fa fa-history font-blue-madison"></i><span class="text-icon ">Histórico</span></a> </li><li title="Excluir"> <a class="dropdown-link"><i class="fa fa-trash-alt font-red-soft"></i><span class="text-icon ">Excluir</span></a> </li> </ul> </div> </div>  </td> </tr> <tr class="vue-blank-item" style="height: 540px;"> <td colspan="10">&nbsp;</td> </tr> </tbody>    <tbody style="border-top: 0px" class="footer"> <tr> <td class="vue-footer no-padding" colspan="10">  <div class="vue-paginated-table-footer vue-text-right"> <span class="margin-right"> <span>Qtd:&nbsp;</span> <select class="bg-white select input-sm"> <option value="auto">Auto</option> <option value="10">10</option> <option value="20">20</option> <option value="30">30</option> <option value="50">50</option> </select> </span> <span class="entries-info"> Exibindo 1 - 1 de 1 </span>  <span class="btn-group vue-pagination-buttons margin-left"> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-double-left"></i></button> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-left"></i></button> <button type="button" class="vue-page-item btn btn-default blue-chambray"> 1 </button> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-right"></i></button> <button type="button" class="btn btn-default" disabled=""><i class="fa fa-angle-double-right"></i></button> </span>   </div> </td> </tr> </tbody> </table> </div> </div>



clicar na seta da pproxima copia

<button type="button" style="max-width: 25px;" class="btn blue-chambray btn-outline btn-xs dropdown-toggle more-actions vue-dropdown-item no-margin-right" data-toggle="dropdown" aria-expanded="false"><i class="fa fa-angle-down"></i></button>


reajuste e etc, ate chegarmos ao fim da ultima linha da ultima copia