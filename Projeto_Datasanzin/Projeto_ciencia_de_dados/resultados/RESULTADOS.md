# Resultados da análise do Pescadores Web

Todos os números abaixo vêm de dados simulados com semente 42. Não são
registros da ONG, nem foram extraídos do levantamento do IDIS ou do artigo HYB.

## Pergunta e unidade de análise

Como as doações recebidas se comparam à demanda das ações sociais, e é possível
antecipar falta de itens? A unidade de análise é item-mês. Há 12 itens,
36 meses, 432 item-meses, 143 ações e 24004 atendimentos.
Atendimentos podem incluir a mesma pessoa em ações diferentes.

## Qualidade dos dados

| regra | removidas |
| --- | --- |
| duplicata_doacao_id | 1 |
| quantidade_nula | 1 |
| quantidade_nao_positiva | 1 |
| item_inexistente | 1 |
| mes_fora_do_periodo | 1 |

Os erros foram inseridos de propósito. Cada registro é removido na primeira regra
que viola; as contagens são sequenciais. Ausência de doação não pode ser confundida
com dado perdido em uma futura base real.

## Análise exploratória e regressão

54.9% dos item-meses apresentaram demanda não
atendida. Esse percentual conta item-meses, sem somar kg, litros e unidades.
Para arroz: demanda = 0.0737 × atendimentos + 1.41 kg.
O ajuste usa 30 meses; nos 6 meses finais, MAE =
2.66 kg e R² = 0.898. O simulador já liga demanda a
atendimentos: o resultado ilustra a técnica, sem constituir descoberta sobre a ONG.

## Classificação de falta no mês seguinte

As variáveis terminam no mês t e o alvo pertence a t+1. O corte é pelo mês do alvo:
treino até dez./2024 (252 linhas), validação jan.–jun./2025 (72),
teste jul.–dez./2025 (72, 50 positivos). Não há divisão aleatória.
Os mesmos itens aparecem ao longo do tempo: avalia-se previsão futura para itens
conhecidos, não generalização para outras ONGs ou novos itens.

Validação usada para selecionar por F1, com limiar fixo de 0,5:

| modelo | acuracia | precisao | recall | f1 | auc_roc | pr_auc_ap |
| --- | --- | --- | --- | --- | --- | --- |
| Maioria | 0.514 | 0.514 | 1.000 | 0.679 | 0.500 | 0.514 |
| Regra estoque | 0.569 | 0.545 | 0.973 | 0.699 | 0.558 | 0.545 |
| Regressao logistica | 0.597 | 0.577 | 0.811 | 0.674 | 0.581 | 0.584 |
| Arvore | 0.583 | 0.578 | 0.703 | 0.634 | 0.572 | 0.547 |
| Random Forest | 0.611 | 0.596 | 0.757 | 0.667 | 0.649 | 0.584 |

Modelo selecionado antes de consultar o teste: **Regra estoque**. Os modelos são
reajustados em treino + validação e o teste final é usado apenas para avaliação:

| modelo | acuracia | precisao | recall | f1 | auc_roc | pr_auc_ap |
| --- | --- | --- | --- | --- | --- | --- |
| Maioria | 0.694 | 0.694 | 1.000 | 0.820 | 0.500 | 0.694 |
| Regra estoque | 0.736 | 0.731 | 0.980 | 0.838 | 0.581 | 0.731 |
| Regressao logistica | 0.681 | 0.865 | 0.640 | 0.736 | 0.803 | 0.904 |
| Arvore | 0.736 | 0.782 | 0.860 | 0.819 | 0.743 | 0.854 |
| Random Forest | 0.694 | 0.833 | 0.700 | 0.761 | 0.786 | 0.902 |

Precisão mede a proporção dos alertas que se confirmam; recall mede a proporção das
faltas detectadas. F1 combina ambos. Acurácia pode esconder a classe minoritária.
PR-AUC é apresentada como average precision (AP). O período de teste é curto, com
observações repetidas por item; diferenças pequenas não demonstram superioridade
estatística. Se uma regra simples vencer, ela permanece como escolha do protótipo.

## Perfis de itens

K-means compara k = 2, 3 e 4 após padronização de três atributos adimensionais.
Escolhido k = 2, silhueta = 0.603. São apenas 12
itens. Os grupos são exploratórios e retrospectivos, calculados sobre 2023–2025;
não entram nas características do classificador e não são previsão validada.

## Uso proposto e limitações

`dados/tratados/alertas_prototipo.csv` demonstra alertas para jan./2026 usando dados
até dez./2025. Não há resultados observados de janeiro para avaliar esses alertas.
Um gestor poderia revisar os itens sinalizados e decidir sobre campanhas; o
protótipo não compra itens, não envia mensagens e não está integrado ao Laravel.

A simulação assume que todas as doações do mês estão disponíveis antes do consumo,
estoque sem perdas ou validade e demanda solicitada registrada mesmo quando não
atendida. Uma aplicação real exige movimentação por data, registro de perdas,
histórico suficiente e validação com os gestores. Não inferimos aumento de doações,
redução de desperdício ou impacto social a partir deste exercício.

## Monitoramento proposto

Acompanhar mensalmente completude, duplicatas, integridade dos itens e balanço de
estoque; comparar distribuição de demanda e doações com o histórico; após o mês
previsto, calcular precisão, recall, F1 e taxa de alertas por item. Investigar duas
quedas consecutivas de F1 abaixo da regra operacional, sem retreino automático.
Definir com os gestores custo de falso alerta e de falta não detectada antes de
escolher um limiar de uso real.
