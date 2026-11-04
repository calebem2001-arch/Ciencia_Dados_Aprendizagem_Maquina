# Dicionário dos dados

Todos os dados são simulados. Decimais usam ponto, CSVs usam vírgula, textos usam UTF-8.
Não há nomes, contatos, CPFs, informações de doadores ou beneficiários identificáveis.

| Arquivo | Unidade e chave | Campos |
|---|---|---|
| `brutos/itens.csv` | Um item; `item_id` | nome, categoria, unidade, consumo ilustrativo por atendimento, estoque mínimo |
| `brutos/acoes.csv` | Uma ação; `acao_id` | mes (AAAA-MM), atendimentos, voluntarios_presentes |
| `brutos/doacoes.csv` | Um recebimento; `doacao_id` | mes, item_id, quantidade; inclui 5 linhas inválidas conhecidas |
| `brutos/demandas.csv` | Um item-mês; mes + item_id | demanda solicitada, inclusive a parcela não atendida |
| `tratados/doacoes_limpas.csv` | Um recebimento válido | Mesmas colunas após validações |
| `tratados/item_mes.csv` | Um item-mês | Dados reunidos, estoque, características e alvo |

## Campos analíticos de item_mes

| Campo | Definição |
|---|---|
| mes | Mês das observações usadas como características |
| nome, categoria, unidade | Atributos do cadastro do item |
| consumo_por_atendimento | Taxa usada pelo gerador; não entra no classificador |
| estoque_minimo | Limite ilustrativo; também define o estoque inicial em jan./2023 |
| atendimentos | Soma de participações nas ações do mês, não pessoas únicas |
| acoes | Número de ações no mês |
| doado | Quantidade válida recebida do item no mês |
| demanda | Quantidade solicitada do item no mês |
| estoque_inicial | Saldo final do mês anterior; no primeiro mês, mínimo ilustrativo |
| consumido | Menor valor entre estoque disponível e demanda |
| estoque_final | estoque_inicial + doado − consumido |
| demanda_nao_atendida | demanda − consumido |
| houve_falta | 1 se demanda_nao_atendida > 0; caso contrário, 0 |
| demanda_media_3m | Média da demanda de t−2, t−1 e t |
| doacao_media_3m | Média de doado de t−2, t−1 e t |
| faltas_3m | Número de meses com falta em t−2, t−1 e t |
| mes_seno, mes_cosseno | Codificação sazonal do mês t+1, conhecido no fim de t |
| mes_alvo | Mês t+1; ausente no último mês observado |
| alvo_falta_proximo_mes | houve_falta em t+1; ausente no último mês |

Dois primeiros meses não têm média móvel completa. O último mês não tem rótulo
futuro. Essas linhas ficam fora da avaliação supervisionada. CSVs preservam esses
campos ausentes; o código filtra explicitamente antes do treinamento.

## Saídas

- `qualidade.csv`: remoções sequenciais por regra.
- `metricas_validacao.csv` e `metricas_teste.csv`: uma linha por modelo.
- `predicoes_teste.csv`: rótulos e previsões do modelo escolhido, por item e mês-alvo.
- `perfis_itens.csv`: variação da demanda (desvio/média), cobertura (doado/solicitado),
  fração de meses com falta e cluster; calculados retrospectivamente nos 36 meses.
- `avaliacao_kmeans.csv`: silhueta por k.
- `regressao.json`: coeficientes, MAE, R² e tamanhos de treino/teste para arroz.
- `alertas_prototipo.csv`: alerta binário para jan./2026, sem rótulo observado futuro.

Quantidades só podem ser somadas dentro da mesma unidade e com interpretação
compatível. Mesmo uma soma de unidades de brinquedos e talheres seria pouco útil;
por isso os indicadores de volume são apresentados por item.
