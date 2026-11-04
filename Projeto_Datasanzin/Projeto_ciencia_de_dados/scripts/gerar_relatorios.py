"""Gera os dois PDFs a partir das saídas existentes de analise.py."""
from pathlib import Path
from xml.sax.saxutils import escape
import csv
import json
import textwrap

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, PageBreak, Image, Preformatted)

ROOT = Path(__file__).resolve().parents[1]
PAGE = landscape(A4)
INK = colors.HexColor("#16324f")
TEAL = colors.HexColor("#157f82")
STYLES = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=INK, spaceAfter=18),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=TEAL, spaceBefore=10, spaceAfter=9),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=11, leading=16, alignment=TA_LEFT, spaceAfter=10),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=9, leading=12, spaceAfter=7),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9, leading=12),
}


def p(text, style="body"):
    return Paragraph(escape(text).replace("\n", "<br/>"), STYLES[style])


def title(text):
    return p(text, "title")


def tabela(rows, widths=None):
    data = [[p(str(v), "cell") for v in row] for row in rows]
    tab = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#deedf0")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f2f5f8")]),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 9),
        ("RIGHTPADDING", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LINEBELOW", (0,0), (-1,0), 1, TEAL),
    ]))
    return tab


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(TEAL)
    canvas.line(42, 32, PAGE[0]-42, 32)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(INK)
    canvas.drawString(42, 19, "Pescadores Web | Demonstracao academica com dados simulados")
    canvas.drawRightString(PAGE[0]-42, 19, str(doc.page))
    canvas.restoreState()


def pdf(path, story):
    path.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(path), pagesize=PAGE, leftMargin=42, rightMargin=42,
                      topMargin=32, bottomMargin=44, title=path.stem.replace("_", " "),
                      author="Projeto Pescadores Web").build(story, onFirstPage=rodape, onLaterPages=rodape)


def ler_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def gerar():
    r = json.loads((ROOT / "resultados/resumo.json").read_text(encoding="utf-8"))
    story = [title("Pescadores Web\nDoações, demanda e falta de itens"),
             p("Relatório de Ciência de Dados com CRISP-DM", "h2"),
             p("Pergunta: como as doações recebidas se comparam à demanda das ações sociais, e é possível antecipar falta de itens no mês seguinte?"),
             p("A análise demonstra um fluxo reproduzível para apoiar a revisão de estoque e o planejamento de campanhas. Toda a base foi simulada; não representa a operação, o impacto ou os resultados de uma ONG real."),
             tabela([["Itens", "Meses", "Item-meses", "Ações", "Atendimentos"],
                     [r["itens"], 36, r["item_meses"], r["acoes"], r["atendimentos"]]], [151]*5),
             Spacer(1,16),
             p("TCC de referência: Felipe Barbosa Vieira e Calebe Mendes Bezerra. Código e documentação preparados com auxílio de IA; revisão e compreensão pela equipe são necessárias.", "small"),
             p("Contexto: a fonte institucional IDIS/CAF destaca desafios de sustentabilidade e gestão. O levantamento e o artigo HYB contextualizam o problema; não forneceram os dados operacionais utilizados aqui.", "small"),
             PageBreak(), title("Método e qualidade dos dados"),
             tabela([["Fase CRISP-DM", "Aplicação"],
                     ["1. Negócio", "Revisão de estoque e planejamento de campanhas; decisão humana."],
                     ["2. Dados", "Itens, ações, doações e demanda; 36 meses simulados, semente 42."],
                     ["3. Preparação", "Cinco erros conhecidos removidos; balanço de estoque e médias móveis."],
                     ["4. Modelagem", "Regressão, K-means, classificadores e duas referências simples."],
                     ["5. Avaliação", "Validação temporal seleciona o modelo; teste final reservado."],
                     ["6. Implementação", "Arquivo de alertas de exemplo, sem integração ao sistema do TCC."]], [150,605]),
             Spacer(1,12),
             p("A unidade de análise é item-mês. Não se somam kg, litros e unidades. Atendimentos podem contar a mesma pessoa em ações distintas. Demanda solicitada é registrada mesmo quando não atendida."),
             p("O simulador pressupõe recebimentos antes do consumo mensal e ausência de perdas ou validade. A aplicação real precisa de movimentação por data e registro de demanda não atendida.", "small"),
             PageBreak(), title("Doações e disponibilidade"),
             Image(str(ROOT / "Dashboard/01_visao_geral.png"), width=715, height=440),
             PageBreak(), title("Dispersão e regressão linear"),
             Image(str(ROOT / "Dashboard/02_dispersao_regressao.png"), width=755, height=337),
             p(f"Arroz: {r['regressao']['coeficiente']:.4f} kg por atendimento + {r['regressao']['intercepto']:.2f} kg. Teste em seis meses: R² {r['regressao']['r2_teste']:.3f}; MAE {r['regressao']['mae_teste_kg']:.2f} kg. A ligação entre atendimentos e demanda é uma premissa do simulador, sem evidência causal sobre a ONG.", "small"),
             PageBreak(), title("Avaliação temporal e escolha do modelo"),
             p("Características disponíveis no fim de t preveem falta em t+1. O corte usa o mês do alvo: treino até dez./2024; validação jan.-jun./2025; teste jul.-dez./2025. O último mês, sem alvo futuro observado, não entra na avaliação."),
             p(f"Modelo escolhido pelo F1 da validação: {r['modelo_escolhido_na_validacao']}. Depois, os algoritmos são reajustados em treino + validação. O teste contém {r['n_teste']} item-meses, com {r['positivos_teste']} casos de falta. Resultados no teste:"),
    ]
    rows = ler_csv(ROOT / "dados/tratados/metricas_teste.csv")
    rows[0] = ["Modelo", "Acurácia", "Precisão", "Recall", "F1", "ROC-AUC", "AP"]
    story += [tabela([[v if i == 0 or j == 0 else f"{float(v):.3f}" for j,v in enumerate(row)] for i,row in enumerate(rows)], [170]+[97.5]*6),
              Spacer(1,14),
              p("A regra simples venceu na validação. A diferença para a previsão pela classe majoritária é pequena no teste; não foi realizado teste de superioridade estatística. Uma pontuação alta de recall isolada não demonstra boa discriminação."),
              p("Recall: faltas detectadas entre as faltas reais. Precisão: alertas corretos entre os alertas emitidos. F1 combina ambos. AP é average precision. O teste tem apenas seis meses e observações repetidas por item.", "small"),
              PageBreak(), title("Classificação e perfis dos itens"),
              Image(str(ROOT / "Dashboard/03_modelos.png"), width=715, height=440),
              PageBreak(), title("Interpretação, limites e próximos passos"),
              p(f"K-means: k = {r['k_escolhido']}, silhueta {r['silhueta']:.3f}. Os grupos resumem 12 itens no período inteiro e são retrospectivos. Não alimentam o classificador nem demonstram estabilidade em outra base."),
              p("O protótipo gera alertas para jan./2026 com observações até dez./2025. Sem dados observados de janeiro, esses alertas não podem ser avaliados. A saída serve para revisão humana, sem compra, envio de mensagens ou integração ao Laravel."),
              p("Próxima iteração: obter registros operacionais, registrar perdas e demanda não atendida, revisar sazonalidades e níveis mínimos com os gestores e repetir a avaliação temporal. Definir custos de falso alerta e falta não detectada antes de uso real."),
              p("Monitoramento proposto: completude, duplicatas, balanço de estoque, mudanças de demanda e doações; após cada mês previsto, precisão, recall e F1 por item e no conjunto. Comparar continuamente com a regra operacional."),
              p("Fontes consultadas", "h2"),
              p("HYB, 9 abr. 2026. Panorama das ONGs no Brasil: desafios e perspectivas do Terceiro Setor. Artigo sugerido como ponto de partida do tema.", "small"),
              p("IDIS, 20 jan. 2026: Panorama das ONGs: estudo revela resiliência do terceiro setor no Brasil. Acesso às fontes em 4 nov. 2026. Endereços completos em docs/REFERENCIAS.md.", "small"),
              p("Documento original: Definição do Projeto Pescadores Web, versão 2.0, set. 2026. Resultados completos, tabelas e regras em resultados/RESULTADOS.md e no notebook.", "small")]
    pdf(ROOT / "docs/Pescadores_Web_Analise.pdf", story)

    story = [title("Pescadores Web\nConsultas SQL e resultados"),
             p("Oito consultas em SQLite, executadas sobre dados simulados tratados. O banco MySQL da aplicação do TCC não é acessado nem alterado."),
             p("Os resultados completos de cada consulta estão em resultados/sql/. Nas páginas seguintes, tabelas extensas são exibidas parcialmente para manter a legibilidade. Código de origem: sql/consultas.sql."),
             p("As verificações de qualidade da base bruta ficam em dados/tratados/qualidade.csv; estas consultas usam a base após a limpeza. Os balanços conferem a conservação do estoque e a decomposição da demanda."),
             PageBreak()]
    blocos = (ROOT / "sql/consultas.sql").read_text(encoding="utf-8").split("-- CONSULTA ")[1:]
    for i, bloco in enumerate(blocos):
        nome, query = bloco.split("\n", 1)
        nome = nome.strip()
        story += [title(nome.replace("_", " ")),
                  Preformatted("\n".join(textwrap.fill(line, 110, subsequent_indent="    ") for line in query.strip().splitlines()),
                               ParagraphStyle("code", fontName="Courier-Bold", fontSize=9, leading=12, textColor=INK)),
                  Spacer(1,16)]
        rows = ler_csv(ROOT / f"resultados/sql/{nome}.csv")
        story.append(tabela(rows[:11], [755/len(rows[0])]*len(rows[0])))
        story.append(Spacer(1,8))
        story.append(p(f"Exibidas {min(10,len(rows)-1)} de {len(rows)-1} linhas. Arquivo completo: resultados/sql/{nome}.csv", "small"))
        if i < len(blocos)-1:
            story.append(PageBreak())
    pdf(ROOT / "docs/Pescadores_Web_Consultas_SQL.pdf", story)


if __name__ == "__main__":
    gerar()
    print("Relatórios gerados em docs/.")
