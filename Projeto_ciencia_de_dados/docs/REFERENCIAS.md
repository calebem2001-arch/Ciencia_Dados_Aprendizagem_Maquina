# Referências e origem dos dados

## Contextualização

KIPPER, Marina. **Panorama das ONGs no Brasil: desafios e perspectivas do Terceiro
Setor.** HYB, 9 abr. 2026. Disponível em:
<https://blog.hyb.com.br/panorama-das-ongs-no-brasil-desafios-e-perspectivas-do-terceiro-setor/>.
Acesso em: 4 nov. 2026. Artigo de divulgação e ponto de partida do tema; não é uma
base de registros de doações, estoque ou ações.

IDIS. **Panorama das ONGs: estudo revela resiliência do terceiro setor no Brasil
diante do aumento de demandas e desafios de sustentabilidade.** 20 jan. 2026.
Disponível em:
<https://www.idis.org.br/panorama-das-ongs-estudo-revela-resiliencia-do-terceiro-setor-no-brasil/>.
Acesso em: 4 nov. 2026. Fonte institucional do parceiro brasileiro da pesquisa CAF/IDIS.
A página informa 170 organizações respondentes no Brasil, em questionário online
realizado de março a junho de 2025. O resumo destaca desafios de sustentabilidade,
gestão e transparência. Esses achados contextualizam o tema e não descrevem a ONG
do TCC. O relatório integral não foi utilizado; a página pública foi a fonte consultada.

## Projeto de referência

VIEIRA, Felipe Barbosa; BEZERRA, Calebe Mendes. **Definição do Projeto Pescadores Web.**
Versão 2.0, set. 2026. Documento presente na raiz deste repositório.

## Dados e método

A base foi produzida por `scripts/analise.py`, com gerador NumPy e semente 42.
Todas as taxas, sazonalidades e erros são premissas didáticas documentadas no código.
Nenhuma linha foi extraída dos artigos ou coletada com a organização.

A estrutura segue as seis fases do CRISP-DM. A implementação utiliza pandas,
NumPy, Matplotlib, SQLite e scikit-learn. As dependências ficam registradas em
`requirements.txt` e `requirements-lock.txt`. Não há alegação de levantamento
empírico, revisão sistemática ou validação com gestores nesta entrega.
