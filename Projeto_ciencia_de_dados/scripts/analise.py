"""Pipeline didático do Pescadores Web. Todos os registros são simulados."""
from pathlib import Path
import argparse
import json
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix,
                             f1_score, mean_absolute_error, precision_score,
                             r2_score, recall_score, roc_auc_score, silhouette_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
NUMERICAS = ["estoque_final", "demanda_media_3m", "doacao_media_3m", "faltas_3m",
             "mes_seno", "mes_cosseno"]
FEATURES = NUMERICAS + ["item_id"]


def salvar(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")


def gerar_dados(root=ROOT):
    """Simula demanda registrada, recebimentos e ações; sem dados pessoais."""
    raw = root / "dados/brutos"
    rng = np.random.default_rng(SEED)
    specs = [
        ("I01", "Arroz", "alimentacao", "kg", .075, 40),
        ("I02", "Feijao", "alimentacao", "kg", .055, 30),
        ("I03", "Macarrao", "alimentacao", "kg", .035, 25),
        ("I04", "Proteina", "alimentacao", "kg", .095, 50),
        ("I05", "Legumes", "alimentacao", "kg", .080, 40),
        ("I06", "Oleo", "alimentacao", "litro", .008, 8),
        ("I07", "Embalagem", "material", "unidade", 1., 600),
        ("I08", "Talher", "material", "unidade", 1., 600),
        ("I09", "Agua", "alimentacao", "litro", .450, 250),
        ("I10", "Camiseta", "vestuario", "unidade", .120, 80),
        ("I11", "Agasalho", "vestuario", "unidade", .070, 40),
        ("I12", "Brinquedo", "recreacao", "unidade", .100, 60),
    ]
    itens = pd.DataFrame(specs, columns=["item_id", "nome", "categoria", "unidade",
                                        "consumo_por_atendimento", "estoque_minimo"])
    acoes, doacoes, demandas = [], [], []
    meses = pd.period_range("2023-01", "2025-12", freq="M")
    for t, mes in enumerate(meses):
        # Tendência e sazonalidade são hipóteses do simulador, não achados reais.
        n = int(rng.integers(3, 6))
        total = 0
        for a in range(n):
            pessoas = int(max(60, rng.normal(155 + .8*t, 24)))
            total += pessoas
            acoes.append([f"A{t:02d}{a:02d}", str(mes), pessoas,
                          int(max(4, rng.normal(pessoas/17, 2)))])
        choque_doacoes = float(rng.lognormal(-.10, .28))
        for row in itens.itertuples():
            saz = 1.
            if row.nome == "Agasalho":
                saz = 1.8 if mes.month in [5, 6, 7] else .65
            if row.nome == "Brinquedo":
                saz = 1.9 if mes.month in [10, 12] else .70
            demanda = round(total * row.consumo_por_atendimento * saz * rng.uniform(.88, 1.12), 2)
            # A oferta tem dinâmica própria: não é calculada da demanda futura observada.
            esperado = 650 * row.consumo_por_atendimento
            oferta = round(esperado * choque_doacoes * rng.uniform(.60, 1.25), 2)
            if row.nome in ["Brinquedo", "Agasalho"]:
                oferta = round(oferta * (1.35 if mes.month == 12 else .85), 2)
            if row.unidade == "unidade":
                demanda, oferta = float(round(demanda)), float(round(oferta))
            doacoes.append([f"D{t:02d}{row.item_id}", str(mes), row.item_id, oferta])
            demandas.append([str(mes), row.item_id, demanda])
    doacoes = pd.DataFrame(doacoes, columns=["doacao_id", "mes", "item_id", "quantidade"])
    # Cinco problemas conhecidos para demonstrar regras auditáveis de qualidade.
    erros = pd.DataFrame([
        doacoes.iloc[0].tolist(),
        ["ERRO_NEGATIVO", "2023-02", "I01", -5],
        ["ERRO_ITEM", "2023-02", "I99", 10],
        ["ERRO_DATA", "2030-01", "I01", 10],
        ["ERRO_NULO", "2023-02", "I01", np.nan],
    ], columns=doacoes.columns)
    salvar(itens, raw / "itens.csv")
    salvar(pd.DataFrame(acoes, columns=["acao_id", "mes", "atendimentos", "voluntarios_presentes"]), raw / "acoes.csv")
    salvar(pd.concat([doacoes, erros], ignore_index=True), raw / "doacoes.csv")
    salvar(pd.DataFrame(demandas, columns=["mes", "item_id", "demanda"]), raw / "demandas.csv")
    return {"itens": len(itens), "acoes": len(acoes), "doacoes_brutas": len(doacoes)+len(erros)}


def preparar_dados(root=ROOT):
    raw, proc = root / "dados/brutos", root / "dados/tratados"
    itens = pd.read_csv(raw / "itens.csv")
    acoes = pd.read_csv(raw / "acoes.csv")
    doacoes = pd.read_csv(raw / "doacoes.csv")
    demanda = pd.read_csv(raw / "demandas.csv")
    regras = [
        ("duplicata_doacao_id", lambda d: d.duplicated("doacao_id")),
        ("quantidade_nula", lambda d: d.quantidade.isna()),
        ("quantidade_nao_positiva", lambda d: d.quantidade.le(0)),
        ("item_inexistente", lambda d: ~d.item_id.isin(itens.item_id)),
        ("mes_fora_do_periodo", lambda d: ~d.mes.isin(acoes.mes)),
    ]
    audit = []
    for nome, regra in regras:
        mask = regra(doacoes)
        audit.append({"regra": nome, "removidas": int(mask.sum())})
        doacoes = doacoes.loc[~mask].copy()
    salvar(pd.DataFrame(audit), proc / "qualidade.csv")
    salvar(doacoes, proc / "doacoes_limpas.csv")
    # A unidade de análise é item-mês; nunca somar kg, litros e unidades num KPI.
    base = demanda.merge(doacoes.groupby(["mes", "item_id"], as_index=False).quantidade.sum(),
                         on=["mes", "item_id"], validate="one_to_one")
    base = base.rename(columns={"quantidade": "doado"}).merge(itens, on="item_id", validate="many_to_one")
    base = base.merge(acoes.groupby("mes", as_index=False).agg(
        atendimentos=("atendimentos", "sum"), acoes=("acao_id", "count")), on="mes", validate="many_to_one")
    partes = []
    for _, grupo in base.groupby("item_id", sort=True):
        grupo = grupo.sort_values("mes").copy()
        estoque = float(grupo.estoque_minimo.iloc[0])
        registros = []
        for row in grupo.itertuples():
            disponivel = round(estoque + row.doado, 2)
            consumo = round(min(disponivel, row.demanda), 2)
            final = round(disponivel - consumo, 2)
            falta = round(row.demanda - consumo, 2)
            registros.append([estoque, consumo, final, falta, int(falta > 0)])
            estoque = final
        grupo[["estoque_inicial", "consumido", "estoque_final", "demanda_nao_atendida", "houve_falta"]] = registros
        grupo["demanda_media_3m"] = grupo.demanda.rolling(3).mean()
        grupo["doacao_media_3m"] = grupo.doado.rolling(3).mean()
        grupo["faltas_3m"] = grupo.houve_falta.rolling(3).sum()
        # Cada linha em t prevê t+1. As características terminam em t.
        grupo["mes_alvo"] = grupo.mes.shift(-1)
        grupo["alvo_falta_proximo_mes"] = grupo.houve_falta.shift(-1)
        prox_mes = pd.PeriodIndex(grupo.mes, freq="M") + 1
        grupo["mes_seno"] = np.sin(2*np.pi*prox_mes.month/12)
        grupo["mes_cosseno"] = np.cos(2*np.pi*prox_mes.month/12)
        partes.append(grupo)
    base = pd.concat(partes, ignore_index=True).sort_values(["mes", "item_id"]).reset_index(drop=True)
    salvar(base, proc / "item_mes.csv")
    return base, acoes, itens, doacoes, pd.DataFrame(audit)


def separar_temporal(base):
    dados = base.dropna(subset=FEATURES + ["mes_alvo", "alvo_falta_proximo_mes"]).copy()
    # Corte pelo mês do alvo, não somente pelo mês das características.
    treino = dados[dados.mes_alvo <= "2024-12"]
    validacao = dados[(dados.mes_alvo >= "2025-01") & (dados.mes_alvo <= "2025-06")]
    teste = dados[(dados.mes_alvo >= "2025-07") & (dados.mes_alvo <= "2025-12")]
    return treino, validacao, teste


def medir(y, pred, prob):
    return {"acuracia": float(accuracy_score(y, pred)),
            "precisao": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)),
            "auc_roc": float(roc_auc_score(y, prob)) if len(np.unique(y)) == 2 else None,
            "pr_auc_ap": float(average_precision_score(y, prob)) if np.sum(y) else None}


def modelar(base, root=ROOT):
    treino, validacao, teste = separar_temporal(base)
    def preprocessar():
        return ColumnTransformer([
            ("numericas", StandardScaler(), NUMERICAS),
            ("item", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["item_id"]),
        ])
    modelos = {
        "Maioria": DummyClassifier(strategy="most_frequent"),
        "Regressao logistica": make_pipeline(preprocessar(), LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=SEED)),
        "Arvore": make_pipeline(preprocessar(), DecisionTreeClassifier(
            max_depth=4, min_samples_leaf=8, class_weight="balanced", random_state=SEED)),
        "Random Forest": make_pipeline(preprocessar(), RandomForestClassifier(
            n_estimators=200, max_depth=5, min_samples_leaf=6, class_weight="balanced", random_state=SEED, n_jobs=1)),
    }
    # Regra operacional sem treino: estoque abaixo da demanda média recente.
    def prever(nome, frame):
        if nome == "Regra estoque":
            pred = (frame.estoque_final < frame.demanda_media_3m).astype(int).to_numpy()
            return pred, pred.astype(float)
        mod = modelos[nome]
        return mod.predict(frame[FEATURES]), mod.predict_proba(frame[FEATURES])[:, 1]
    ytrain = treino.alvo_falta_proximo_mes.astype(int)
    for mod in modelos.values():
        mod.fit(treino[FEATURES], ytrain)
    nomes = ["Maioria", "Regra estoque", "Regressao logistica", "Arvore", "Random Forest"]
    registros = []
    for nome in nomes:
        pred, prob = prever(nome, validacao)
        registros.append({"modelo": nome, **medir(validacao.alvo_falta_proximo_mes, pred, prob)})
    val = pd.DataFrame(registros)
    # Melhor F1 na validação. Empates preservam o modelo mais simples da lista.
    escolhido = val.loc[val.f1.idxmax(), "modelo"]
    validacao_mais_treino = pd.concat([treino, validacao])
    for mod in modelos.values():
        mod.fit(validacao_mais_treino[FEATURES], validacao_mais_treino.alvo_falta_proximo_mes.astype(int))
    resultados, predictions = [], []
    for nome in nomes:
        pred, prob = prever(nome, teste)
        resultados.append({"modelo": nome, **medir(teste.alvo_falta_proximo_mes, pred, prob)})
        if nome == escolhido:
            predictions = pred
    met = pd.DataFrame(resultados)
    proc = root / "dados/tratados"
    salvar(val, proc / "metricas_validacao.csv")
    salvar(met, proc / "metricas_teste.csv")
    predicoes = teste[["item_id", "nome", "mes", "mes_alvo", "alvo_falta_proximo_mes"]].copy()
    predicoes["previsto"] = predictions
    salvar(predicoes, proc / "predicoes_teste.csv")
    # Protótipo para janeiro/2026. Não existe rótulo para avaliar esse mês.
    ultimo = base[base.mes == base.mes.max()].copy()
    alerta, _ = prever(escolhido, ultimo)
    saida = ultimo[["item_id", "nome", "unidade", "estoque_final", "demanda_media_3m"]].copy()
    saida["mes_previsto"] = str(pd.Period(base.mes.max(), freq="M") + 1)
    saida["alerta_falta"] = alerta
    saida["modelo"] = escolhido
    salvar(saida, proc / "alertas_prototipo.csv")
    return val, met, escolhido, predicoes


def agrupar(base, root=ROOT):
    # Clusters retrospectivos de itens, com atributos adimensionais.
    perfil = base.groupby(["item_id", "nome"], as_index=False).agg(
        media_demanda=("demanda", "mean"), desvio_demanda=("demanda", "std"),
        recebido=("doado", "sum"), solicitado=("demanda", "sum"),
        fracao_meses_falta=("houve_falta", "mean"))
    perfil["variacao_demanda"] = perfil.desvio_demanda / perfil.media_demanda
    perfil["cobertura_doacoes"] = perfil.recebido / perfil.solicitado
    attrs = ["variacao_demanda", "cobertura_doacoes", "fracao_meses_falta"]
    x = StandardScaler().fit_transform(perfil[attrs])
    avaliacoes, fits = [], {}
    for k in [2, 3, 4]:
        km = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(x)
        fits[k] = km
        avaliacoes.append({"k": k, "silhueta": float(silhouette_score(x, km.labels_))})
    aval = pd.DataFrame(avaliacoes)
    k = int(aval.loc[aval.silhueta.idxmax(), "k"])
    perfil["cluster"] = fits[k].labels_
    salvar(perfil, root / "dados/tratados/perfis_itens.csv")
    salvar(aval, root / "dados/tratados/avaliacao_kmeans.csv")
    return perfil, aval


def regressao(base, root=ROOT):
    # Um único item em kg: evita misturar unidades ou tratar 12 cópias do mês como independentes.
    dados = base[base.item_id == "I01"].copy()
    treino = dados[dados.mes < "2025-07"]
    teste = dados[dados.mes >= "2025-07"]
    modelo = LinearRegression().fit(treino[["atendimentos"]], treino.demanda)
    pred = modelo.predict(teste[["atendimentos"]])
    res = {"item": "Arroz", "coeficiente": float(modelo.coef_[0]),
           "intercepto": float(modelo.intercept_), "r2_teste": float(r2_score(teste.demanda, pred)),
           "mae_teste_kg": float(mean_absolute_error(teste.demanda, pred)),
           "n_treino": len(treino), "n_teste": len(teste)}
    (root / "dados/tratados/regressao.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return dados, modelo, res


def executar_sql(base, acoes, itens, doacoes, root=ROOT):
    """SQLite local, isolado do banco MySQL do TCC."""
    sql = (root / "sql/consultas.sql").read_text(encoding="utf-8")
    resultados = {}
    out = root / "resultados/sql"
    with sqlite3.connect(":memory:") as con:
        for nome, frame in [("item_mes", base), ("acoes", acoes), ("itens", itens), ("doacoes", doacoes)]:
            frame.to_sql(nome, con, index=False, if_exists="replace")
        for bloco in sql.split("-- CONSULTA ")[1:]:
            nome, query = bloco.split("\n", 1)
            frame = pd.read_sql_query(query.strip(), con)
            resultados[nome.strip()] = frame
            salvar(frame, out / f"{nome.strip()}.csv")
    return resultados


def graficos(base, acoes, met, predicoes, perfis, dispersao, root=ROOT):
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titlesize": 12,
                         "axes.labelsize": 10, "figure.facecolor": "#f4f7fa",
                         "axes.facecolor": "white", "savefig.facecolor": "#f4f7fa"})
    out = root / "Dashboard"
    out.mkdir(parents=True, exist_ok=True)
    def acabamento(fig, title, file):
        fig.suptitle(title, fontsize=19, fontweight="bold", x=.06, ha="left", y=.98, color="#16324f")
        fig.text(.06, .018, "PESCADORES WEB  |  DADOS SIMULADOS 2023–2025  |  Não representam resultados de uma ONG real", fontsize=9, color="#475569")
        fig.tight_layout(rect=[.04, .05, .98, .93], h_pad=3, w_pad=3)
        fig.savefig(out / file, dpi=160)
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    mensal = acoes.groupby("mes").atendimentos.sum()
    x = np.arange(len(mensal))
    ax = axes[0, 0]
    ax.plot(x, mensal, color="#157f82", linewidth=2)
    ax.set(title="Atendimentos por mês", ylabel="Atendimentos (não pessoas únicas)")
    ax.set_xticks(x[::6], mensal.index[::6], rotation=25)
    arroz = base[base.item_id == "I01"]
    ax = axes[0, 1]
    ax.plot(x, arroz.doado, label="Recebido", color="#157f82")
    ax.plot(x, arroz.demanda, label="Solicitado", color="#c86b38")
    ax.set(title="Arroz: recebido × solicitado", ylabel="kg")
    ax.set_xticks(x[::6], mensal.index[::6], rotation=25)
    ax.legend(frameon=False)
    falta = base.groupby("nome").houve_falta.mean().sort_values()
    axes[1, 0].barh(falta.index, falta*100, color="#c86b38")
    axes[1, 0].set(title="Frequência de falta por item", xlabel="% dos meses com demanda não atendida")
    atendido = base.groupby("mes").houve_falta.mean()
    axes[1, 1].plot(x, atendido*100, color="#725b9e", linewidth=2)
    axes[1, 1].set(title="Itens com falta em cada mês", ylabel="% dos 12 itens")
    axes[1, 1].set_xticks(x[::6], mensal.index[::6], rotation=25)
    acabamento(fig, "Doações, demanda e disponibilidade", "01_visao_geral.png")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8))
    dados, modelo, res = dispersao
    for label, mask, color in [("Treino (30 meses)", dados.mes < "2025-07", "#157f82"),
                                ("Teste (6 meses)", dados.mes >= "2025-07", "#c86b38")]:
        axes[0].scatter(dados.loc[mask, "atendimentos"], dados.loc[mask, "demanda"], label=label, color=color, alpha=.8)
    xx = np.linspace(dados.atendimentos.min(), dados.atendimentos.max(), 100)
    axes[0].plot(xx, modelo.predict(pd.DataFrame({"atendimentos": xx})), color="#16324f")
    axes[0].set(title="Atendimentos × demanda de arroz", xlabel="Atendimentos no mês", ylabel="Demanda de arroz (kg)")
    axes[0].legend(frameon=False)
    test = dados[dados.mes >= "2025-07"]
    previsto = modelo.predict(test[["atendimentos"]])
    axes[1].scatter(previsto, test.demanda-previsto, color="#c86b38", s=55)
    axes[1].axhline(0, color="#16324f", linestyle="--")
    axes[1].set(title=f"Resíduos no teste | MAE {res['mae_teste_kg']:.1f} kg", xlabel="Demanda prevista (kg)", ylabel="Observado − previsto (kg)")
    acabamento(fig, "Relação entre atendimentos e demanda", "02_dispersao_regressao.png")
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    pos = np.arange(len(met))
    axes[0, 0].barh(pos-.17, met.recall, height=.32, color="#157f82", label="Recall")
    axes[0, 0].barh(pos+.17, met.f1, height=.32, color="#725b9e", label="F1")
    axes[0, 0].set_yticks(pos, met.modelo)
    axes[0, 0].set(title="Comparação no teste temporal", xlim=(0, 1.05))
    axes[0, 0].legend(frameon=False)
    cm = confusion_matrix(predicoes.alvo_falta_proximo_mes, predicoes.previsto, labels=[0, 1])
    axes[0, 1].imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            axes[0, 1].text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=17,
                            color="white" if cm[i,j] > cm.max()/2 else "#16324f")
    axes[0, 1].set(title="Matriz do modelo selecionado na validação", xlabel="Previsto", ylabel="Real",
                   xticks=[0, 1], yticks=[0, 1], xticklabels=["Sem falta", "Falta"], yticklabels=["Sem falta", "Falta"])
    deslocamentos = {"I01": (-7, 7), "I04": (-7, -12), "I09": (-7, -10),
                     "I10": (7, -10), "I03": (7, 9), "I06": (-7, -12)}
    for cluster, grupo in perfis.groupby("cluster"):
        axes[1, 0].scatter(grupo.cobertura_doacoes, grupo.fracao_meses_falta*100, label=f"Grupo {cluster}", s=60)
        for row in grupo.itertuples():
            offset = deslocamentos.get(row.item_id, (5, 7))
            axes[1, 0].annotate(row.nome, (row.cobertura_doacoes, row.fracao_meses_falta*100),
                                fontsize=7, xytext=offset, textcoords="offset points",
                                ha="right" if offset[0] < 0 else "left")
    axes[1, 0].set(title="Perfis retrospectivos de itens (K-means)", xlabel="Doado / solicitado em 36 meses", ylabel="% dos meses com falta")
    axes[1, 0].margins(x=.15, y=.15)
    axes[1, 0].legend(frameon=False, fontsize=8, loc="lower left")
    por_item = predicoes.groupby("nome").agg(real=("alvo_falta_proximo_mes", "mean"), previsto=("previsto", "mean")).sort_values("real")
    axes[1, 1].plot(por_item.real*100, por_item.index, "o", label="Real", color="#157f82")
    axes[1, 1].plot(por_item.previsto*100, por_item.index, "x", label="Previsto", color="#c86b38")
    axes[1, 1].set(title="Falta por item no teste (6 meses)", xlabel="% dos meses")
    axes[1, 1].legend(frameon=False)
    acabamento(fig, "Modelos e perfis de risco", "03_modelos.png")


def tabela_md(frame):
    cols = list(frame.columns)
    def fmt(v):
        return f"{v:.3f}" if isinstance(v, (float, np.floating)) else str(v)
    return "\n".join(["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"]*len(cols)) + " |"] +
                     ["| " + " | ".join(fmt(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None)])


def relatar(base, acoes, audit, val, met, escolhido, aval, reg, root=ROOT):
    treino, validacao, teste = separar_temporal(base)
    resumo = {"semente": SEED, "periodo": "2023-01 a 2025-12", "itens": int(base.item_id.nunique()),
              "acoes": len(acoes), "atendimentos": int(acoes.atendimentos.sum()),
              "item_meses": len(base), "registros_removidos": int(audit.removidas.sum()),
              "fracao_item_meses_com_falta": float(base.houve_falta.mean()),
              "modelo_escolhido_na_validacao": escolhido,
              "n_treino": len(treino), "n_validacao": len(validacao), "n_teste": len(teste),
              "positivos_teste": int(teste.alvo_falta_proximo_mes.sum()),
              "k_escolhido": int(aval.loc[aval.silhueta.idxmax(), "k"]),
              "silhueta": float(aval.silhueta.max()), "regressao": reg}
    out = root / "resultados"
    out.mkdir(parents=True, exist_ok=True)
    (out / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    texto = f"""# Resultados da análise do Pescadores Web

Todos os números abaixo vêm de dados simulados com semente {SEED}. Não são
registros da ONG, nem foram extraídos do levantamento do IDIS ou do artigo HYB.

## Pergunta e unidade de análise

Como as doações recebidas se comparam à demanda das ações sociais, e é possível
antecipar falta de itens? A unidade de análise é item-mês. Há {resumo['itens']} itens,
36 meses, {len(base)} item-meses, {len(acoes)} ações e {resumo['atendimentos']} atendimentos.
Atendimentos podem incluir a mesma pessoa em ações diferentes.

## Qualidade dos dados

{tabela_md(audit)}

Os erros foram inseridos de propósito. Cada registro é removido na primeira regra
que viola; as contagens são sequenciais. Ausência de doação não pode ser confundida
com dado perdido em uma futura base real.

## Análise exploratória e regressão

{100*resumo['fracao_item_meses_com_falta']:.1f}% dos item-meses apresentaram demanda não
atendida. Esse percentual conta item-meses, sem somar kg, litros e unidades.
Para arroz: demanda = {reg['coeficiente']:.4f} × atendimentos + {reg['intercepto']:.2f} kg.
O ajuste usa {reg['n_treino']} meses; nos {reg['n_teste']} meses finais, MAE =
{reg['mae_teste_kg']:.2f} kg e R² = {reg['r2_teste']:.3f}. O simulador já liga demanda a
atendimentos: o resultado ilustra a técnica, sem constituir descoberta sobre a ONG.

## Classificação de falta no mês seguinte

As variáveis terminam no mês t e o alvo pertence a t+1. O corte é pelo mês do alvo:
treino até dez./2024 ({len(treino)} linhas), validação jan.–jun./2025 ({len(validacao)}),
teste jul.–dez./2025 ({len(teste)}, {resumo['positivos_teste']} positivos). Não há divisão aleatória.
Os mesmos itens aparecem ao longo do tempo: avalia-se previsão futura para itens
conhecidos, não generalização para outras ONGs ou novos itens.

Validação usada para selecionar por F1, com limiar fixo de 0,5:

{tabela_md(val)}

Modelo selecionado antes de consultar o teste: **{escolhido}**. Os modelos são
reajustados em treino + validação e o teste final é usado apenas para avaliação:

{tabela_md(met)}

Precisão mede a proporção dos alertas que se confirmam; recall mede a proporção das
faltas detectadas. F1 combina ambos. Acurácia pode esconder a classe minoritária.
PR-AUC é apresentada como average precision (AP). O período de teste é curto, com
observações repetidas por item; diferenças pequenas não demonstram superioridade
estatística. Se uma regra simples vencer, ela permanece como escolha do protótipo.

## Perfis de itens

K-means compara k = 2, 3 e 4 após padronização de três atributos adimensionais.
Escolhido k = {resumo['k_escolhido']}, silhueta = {resumo['silhueta']:.3f}. São apenas 12
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
"""
    (out / "RESULTADOS.md").write_text(texto, encoding="utf-8")
    return resumo


def executar(root=ROOT):
    gerar_dados(root)
    base, acoes, itens, doacoes, audit = preparar_dados(root)
    val, met, escolhido, pred = modelar(base, root)
    perfis, aval = agrupar(base, root)
    reg = regressao(base, root)
    executar_sql(base, acoes, itens, doacoes, root)
    graficos(base, acoes, met, pred, perfis, reg, root)
    return relatar(base, acoes, audit, val, met, escolhido, aval, reg[2], root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=ROOT, help="Pasta alternativa para os resultados; deve conter sql/consultas.sql")
    args = parser.parse_args()
    print(json.dumps(executar(args.saida.resolve()), indent=2, ensure_ascii=False))
