# Plano de análise do Pescadores Web

Este plano complementa a definição do sistema de gestão do TCC com um recorte de
Ciência de Dados. Não substitui o documento original nem comprova requisitos da
aplicação, testes com usuários ou implantação.

## Problema e decisão

A equipe gestora precisa comparar os itens recebidos com a demanda registrada nas
ações e priorizar a revisão de possíveis faltas. A pergunta central é: como as
doações se comparam à demanda, e é possível antecipar falta no mês seguinte?

Unidade de análise: um item em um mês. Usuário dos resultados: gestor de estoque e
organizador de campanhas. Decisão: revisar um item e considerar uma campanha ou
reposição, respeitando a avaliação humana e os recursos disponíveis.

## Hipóteses de trabalho

| Hipótese | Como examinar | Limitação |
|---|---|---|
| Meses com mais atendimentos exigem mais arroz | Dispersão e regressão; MAE e R² no período final | A relação foi inserida no simulador |
| Cobertura e variabilidade diferenciam os itens | K-means, silhueta e interpretação das características | Só 12 itens; grupos instáveis em outra base |
| Histórico de doações, demanda e estoque pode antecipar falta | Comparação temporal com maioria e regra de estoque | Base sintética não valida desempenho real |

Uma correlação na simulação não confirma uma hipótese sobre a ONG. O resultado
de um algoritmo abaixo do baseline é um resultado válido e deve ser comunicado.

## Construção dos dados

36 meses completos (jan./2023 a dez./2025). São gerados itens, ações, demandas e
doações com semente fixa 42. Taxas de consumo e níveis mínimos são ilustrativos,
sem orçamento real, entrevistas adicionais ou parâmetros estimados da ONG.
Os estoques iniciais do primeiro mês são os níveis mínimos ilustrativos.

O simulador pressupõe recebimentos disponíveis antes do consumo mensal, estoque
sem perdas e demanda registrada independentemente do que foi atendido. A demanda
não atendida é a diferença entre solicitado e consumido. Uma futura base precisa
registrar pedidos não atendidos; usar só saídas esconderia a falta.

## Preparação e avaliação

Remover duplicata de ID, quantidade nula/não positiva, item inexistente e mês fora
do período. Registrar quantas linhas cada regra removeu. Conferir identidades de
estoque e demanda. Calcular médias móveis de três meses por item, sempre usando
apenas meses disponíveis no instante da previsão.

Cada linha no fim de t prevê falta em t+1. Cortes pelo **mês do alvo**: treino até
dez./2024; validação jan.–jun./2025; teste jul.–dez./2025. O último mês não tem alvo
observado e só serve ao protótipo de alertas. Selecionar por F1 da validação, com
limiar fixo de 0,5; depois reajustar em treino + validação. Os números do teste não
guiam ajustes. Reportar precisão, recall, F1, acurácia, ROC-AUC, AP e matriz.

## Critérios de conclusão desta demonstração

- Código executável, saídas registradas e testes de consistência aprovados.
- SQL, dispersão, regressão, K-means, classificadores e dashboard apresentados.
- Escolha do modelo justificável pela validação, mesmo que vença uma regra.
- Métricas e limitações comunicadas sem transformar simulação em evidência real.

Para uso real, a equipe e os gestores precisam definir custos dos erros, horizonte,
dados disponíveis e metas. Não há uma meta de desempenho real validada neste trabalho.

## Implementação e próxima iteração

O arquivo de alertas é uma prova de conceito para revisão humana. Coletar movimentações
diárias, validade e perdas; verificar lacunas; acompanhar métricas por item e mês;
testar janelas temporais adicionais. Comparar novamente com a regra de estoque antes
de integrar a análise ao Laravel. A avaliação pode levar de volta às fases de dados
e preparação, principalmente quando houver ausência de demanda não atendida.
