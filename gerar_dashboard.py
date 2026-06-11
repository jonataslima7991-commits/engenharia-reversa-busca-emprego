"""
GERADOR DE DADOS PARA OS DASHBOARDS
=====================================
Lê os CSVs coletados, processa os dados e gera dois JSONs:

  live_data.json
      KPIs ao vivo, evolução temporal e distribuição por categoria.
      Consumido pelo index.html para atualizar os contadores.

  oportunidades_data.json
      Vagas coletadas nos últimos 7 dias com título, link, fonte e data.
      Consumido pelo oportunidades.html.

Execute manualmente ou automaticamente após cada coleta:
  python gerar_dashboard.py
"""

import os
import sys
import json
import time

import pandas as pd
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")


# ── Categorização (mesma lógica do notebook) ─────────────────────────

def categorizar(titulo: str) -> str:
    t = str(titulo).lower()
    if any(p in t for p in ["bolsista", "bolsa", "graduando", "graduado"]):
        return "Bolsa de Pesquisa"
    if any(p in t for p in ["estágio", "estagio", "trainee", "aprendiz"]):
        return "Estágio / Trainee"
    if any(p in t for p in ["sênior", "senior", "sr.", " sr "]):
        return "Sênior"
    if any(p in t for p in ["pleno", "pl.", " pl "]):
        return "Pleno"
    if any(p in t for p in ["júnior", "junior", "jr.", " jr "]):
        return "Júnior"
    if any(p in t for p in ["gerente", "coordenador", "diretor", "head", "líder"]):
        return "Liderança"
    if any(p in t for p in ["analista", "cientista", "engenheiro", "especialista", "arquiteto"]):
        return "Técnico (sem nível)"
    return "Outros"


# ── Carregar CSVs ─────────────────────────────────────────────────────

ARQUIVOS = {
    "adzuna": "vagas_adzuna.csv",
    "gupy":   "vagas_gupy.csv",
    # fallback: CSV gerado pelo scraper original antes da refatoração
    "adzuna_legado": "vagas_completas.csv",
}

dfs = []
for fonte, arquivo in ARQUIVOS.items():
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo, low_memory=False)
        if "Fonte" not in df.columns:
            df["Fonte"] = fonte
        dfs.append(df)
        print(f"  Carregado: {arquivo} ({len(df):,} linhas)")
    else:
        print(f"  Nao encontrado: {arquivo} (pulando)")

if not dfs:
    print("\nNenhum CSV encontrado. Execute main.py primeiro.")
    sys.exit(1)

df = pd.concat(dfs, ignore_index=True)
df = df.drop_duplicates(subset=["Titulo", "Link"])
df["Titulo"] = df["Titulo"].str.strip().str.title()
df["Categoria"] = df["Titulo"].apply(categorizar)

print(f"\n  Total apos deduplicacao: {len(df):,} vagas")


# ── live_data.json ────────────────────────────────────────────────────

categorias = df["Categoria"].value_counts().to_dict()
top10       = df["Titulo"].value_counts().head(10).to_dict()
fontes      = df["Fonte"].value_counts().to_dict()

# Evolução por data de coleta
evolucao = {}
if "Data_Coleta" in df.columns:
    evo = (
        df.dropna(subset=["Data_Coleta"])
          .groupby(df["Data_Coleta"].astype(str).str[:10])
          .size()
          .sort_index()
    )
    for data, qtd in evo.items():
        # Converte YYYY-MM-DD → MMM/YY para exibição
        try:
            dt = datetime.strptime(data, "%Y-%m-%d")
            chave = dt.strftime("%b/%y").lower()
        except Exception:
            chave = data
        evolucao[chave] = int(qtd)

live_data = {
    "total":         int(len(df)),
    "titulos":       int(df["Titulo"].nunique()),
    "categorias":    {k: int(v) for k, v in categorias.items()},
    "top10":         {k: int(v) for k, v in top10.items()},
    "fontes":        {k: int(v) for k, v in fontes.items()},
    "evolucao":      evolucao,
    "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
}

with open("live_data.json", "w", encoding="utf-8") as f:
    json.dump(live_data, f, ensure_ascii=False, indent=2)

print(f"  live_data.json gerado    ({len(df):,} vagas · {len(evolucao)} datas)")


# ── oportunidades_data.json ───────────────────────────────────────────

if "Data_Coleta" in df.columns:
    df["Data_Coleta"] = pd.to_datetime(df["Data_Coleta"], errors="coerce")
    cutoff   = datetime.now() - timedelta(days=7)
    recentes = df[df["Data_Coleta"] >= cutoff].copy()
    recentes["Data"] = recentes["Data_Coleta"].dt.strftime("%d/%m/%Y")
else:
    # Fallback: usa as últimas 500 linhas se não houver coluna de data
    recentes = df.tail(500).copy()
    recentes["Data"] = datetime.now().strftime("%d/%m/%Y")

recentes = recentes.sort_values("Data", ascending=False)

vagas_lista = (
    recentes[["Titulo", "Link", "Categoria", "Fonte", "Data"]]
    .fillna("—")
    .to_dict(orient="records")
)

oportunidades_data = {
    "vagas":         vagas_lista,
    "total":         len(vagas_lista),
    "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
}

with open("oportunidades_data.json", "w", encoding="utf-8") as f:
    json.dump(oportunidades_data, f, ensure_ascii=False, indent=2)

print(f"  oportunidades_data.json  ({len(vagas_lista):,} vagas dos últimos 7 dias)")

print("\nPronto! Abra index.html ou oportunidades.html no navegador.")