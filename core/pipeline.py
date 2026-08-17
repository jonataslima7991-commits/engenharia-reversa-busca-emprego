"""
PIPELINE DE CONSOLIDAÇÃO, ENRIQUECIMENTO E GERAÇÃO DOS DASHBOARDS
==================================================================
Orquestra o ciclo completo de ETL:
1. Extração: Carrega datasets brutos de múltiplos scrapers
2. Transformação:
   - Limpeza e Deduplicação em 3 camadas
   - Classificação multidimensional (Área, Senioridade, Modalidade, Tipo Macro)
   - Extração de Tech Stack / Skills
   - Parser e modelagem estatística salarial
3. Carga:
   - Gera live_data.json (para index.html)
   - Gera oportunidades_data.json (para oportunidades.html)
   - Salva dataset consolidado em CSV
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List

from config import (
    ARQUIVOS_FONTES,
    ARQUIVO_LIVE_JSON,
    ARQUIVO_OPORTUNIDADES_JSON,
    ARQUIVO_CONSOLIDADO_CSV,
    DIR_PROCESSED_DATA,
)
from core.deduplication import Deduplicador
from core.classifier import Classificador
from core.extractor import ExtratorSkillsSalario


class PipelineDados:
    """
    Orquestrador do processamento de dados do projeto.
    """

    def __init__(self):
        self.metricas_dedup: Dict[str, Any] = {}
        self.df_consolidado: pd.DataFrame = pd.DataFrame()

    def carregar_dados_brutos(self) -> pd.DataFrame:
        """Lê todos os CSVs disponíveis nas pastas configuradas."""
        dfs = []

        for fonte, caminhos in ARQUIVOS_FONTES.items():
            for caminho in caminhos:
                if os.path.exists(caminho):
                    try:
                        df_temp = pd.read_csv(caminho, low_memory=False)
                        if not df_temp.empty:
                            if "Fonte" not in df_temp.columns:
                                df_temp["Fonte"] = fonte
                            dfs.append(df_temp)
                            print(f"  [OK] Dataset carregado: {caminho} ({len(df_temp):,} registros)")
                            break  # Carregou a primeira opção válida desta fonte
                    except Exception as e:
                        print(f"  [!] Erro ao carregar {caminho}: {e}")

        if not dfs:
            print("  [!] Nenhum arquivo CSV de vagas encontrado.")
            return pd.DataFrame()

        df_total = pd.concat(dfs, ignore_index=True)
        print(f"\n  -> Total bruto carregado: {len(df_total):,} registros de {len(dfs)} fonte(s)")
        return df_total

    def processar(self) -> pd.DataFrame:
        """Executa todas as etapas de transformação e enriquecimento."""
        print("\n" + "=" * 60)
        print("  INICIANDO PIPELINE DE TRATAMENTO E ENRIQUECIMENTO")
        print("=" * 60)

        # 1. Carregamento
        df_raw = self.carregar_dados_brutos()
        if df_raw.empty:
            return pd.DataFrame()

        # Garante colunas mínimas
        for col in ["Titulo", "Link", "Fonte", "Data_Coleta"]:
            if col not in df_raw.columns:
                df_raw[col] = ""

        # 2. Deduplicação em 3 camadas
        print("\n[1/4] Executando Deduplicação Inteligente (3 Camadas)...")
        df_limpo, self.metricas_dedup = Deduplicador.executar(df_raw)
        print(f"      - Registros iniciais: {self.metricas_dedup['total_inicial']:,}")
        print(f"      - Removidas por URL canônica: {self.metricas_dedup['removidas_url']:,}")
        print(f"      - Removidas por Chave estrutural: {self.metricas_dedup['removidas_estrutural']:,}")
        print(f"      - Removidas por Similaridade difusa: {self.metricas_dedup['removidas_fuzzy']:,}")
        print(f"      - Total consolidado: {self.metricas_dedup['total_final']:,} ({self.metricas_dedup['taxa_duplicatas_pct']}% duplicadas)")

        # 3. Classificação Multidimensional
        print("\n[2/4] Aplicando Classificação Multidimensional...")
        df_classificado = Classificador.aplicar(df_limpo)

        # 4. Extração de Skills e Salários
        print("\n[3/4] Extraindo Tech Stack e Parsing Salarial...")
        df_final = ExtratorSkillsSalario.aplicar(df_classificado)

        self.df_consolidado = df_final
        return df_final

    def gerar_payload_live_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Gera a estrutura de dados consumida pelo dashboard principal (index.html)."""
        # Distribuições
        dist_areas = df["Area_Atuacao"].value_counts().to_dict()
        dist_senioridade = df["Senioridade"].value_counts().to_dict()
        dist_modalidade = df["Modalidade_Trabalho"].value_counts().to_dict()
        dist_macro = df["Tipo_Macro"].value_counts().to_dict()
        dist_fontes = df["Fonte"].value_counts().to_dict()

        # Top 15 Tech Stack demandada
        all_skills = [skill for sublist in df["Skills"] for skill in sublist]
        skills_series = pd.Series(all_skills).value_counts().head(15)
        top_skills = skills_series.to_dict()

        # Análise Salarial
        df_salarios = df[df["Tem_Salario_Declarado"] & df["Salario_Medio"].notnull()]
        total_com_salario = len(df_salarios)
        taxa_transparencia_salario = round((total_com_salario / len(df) * 100), 2) if len(df) > 0 else 0.0

        # Salários médios por Área
        salarios_por_area = {}
        if not df_salarios.empty:
            salarios_por_area = (
                df_salarios.groupby("Area_Atuacao")["Salario_Medio"]
                .mean()
                .round(2)
                .sort_values(ascending=False)
                .to_dict()
            )

        # Salários médios por Senioridade
        salarios_por_senioridade = {}
        if not df_salarios.empty:
            salarios_por_senioridade = (
                df_salarios.groupby("Senioridade")["Salario_Medio"]
                .mean()
                .round(2)
                .sort_values(ascending=False)
                .to_dict()
            )

        # Média salarial geral (com fallback para média de mercado do estudo caso base local seja pequena)
        salario_medio_geral = (
            round(float(df_salarios["Salario_Medio"].mean()), 2)
            if not df_salarios.empty
            else 6300.00
        )

        # Evolução temporal
        evolucao = {}
        if "Data_Coleta" in df.columns:
            df["Data_Coleta_Str"] = df["Data_Coleta"].astype(str).str[:10]
            evo_serie = df.groupby("Data_Coleta_Str").size().sort_index()
            for dt_str, qtd in evo_serie.items():
                if dt_str and dt_str != "nan":
                    try:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d")
                        chave = dt.strftime("%b/%y").capitalize()
                    except Exception:
                        chave = dt_str
                    evolucao[chave] = evolucao.get(chave, 0) + int(qtd)

        # Payload consolidado
        payload = {
            "total": int(len(df)),
            "titulos_unicos": int(df["Titulo"].nunique()),
            "metricas_deduplicacao": self.metricas_dedup,
            "distribuicao_areas": {k: int(v) for k, v in dist_areas.items()},
            "distribuicao_senioridade": {k: int(v) for k, v in dist_senioridade.items()},
            "distribuicao_modalidade": {k: int(v) for k, v in dist_modalidade.items()},
            "distribuicao_tipo_macro": {k: int(v) for k, v in dist_macro.items()},
            "top_skills": {k: int(v) for k, v in top_skills.items()},
            "salario_medio_geral": salario_medio_geral,
            "salarios_por_area": salarios_por_area,
            "salarios_por_senioridade": salarios_por_senioridade,
            "taxa_transparencia_salario": taxa_transparencia_salario,
            "total_com_salario": total_com_salario,
            "fontes": {k: int(v) for k, v in dist_fontes.items()},
            "evolucao": evolucao,
            # Compatibilidade legada
            "categorias": {k: int(v) for k, v in dist_areas.items()},
            "top10": {k: int(v) for k, v in df["Titulo"].value_counts().head(10).to_dict().items()},
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

        return payload

    def gerar_payload_oportunidades(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Gera a lista enriquecida de oportunidades para o feed dinâmico (oportunidades.html)."""
        df_feed = df.copy()

        # Tratamento de datas
        if "Data_Coleta" in df_feed.columns:
            df_feed["Data_Formatada"] = pd.to_datetime(df_feed["Data_Coleta"], errors="coerce").dt.strftime("%d/%m/%Y")
        else:
            df_feed["Data_Formatada"] = datetime.now().strftime("%d/%m/%Y")

        # Seleciona campos relevantes
        campos = [
            "Titulo", "Link", "Area_Atuacao", "Senioridade", 
            "Modalidade_Trabalho", "Tipo_Macro", "Skills", 
            "Fonte", "Data_Formatada", "Salario_Medio"
        ]

        for c in ["Empresa", "Localizacao"]:
            if c in df_feed.columns:
                campos.append(c)

        campos_existentes = [c for c in campos if c in df_feed.columns]
        df_export = df_feed[campos_existentes].copy()

        # Converte para lista de dicionários
        vagas_lista = []
        for _, row in df_export.iterrows():
            salario_str = f"R$ {row['Salario_Medio']:,.2f}" if pd.notnull(row.get("Salario_Medio")) else "Não informado"
            vaga_item = {
                "Titulo": str(row.get("Titulo", "Vaga sem título")),
                "Link": str(row.get("Link", "#")),
                "Categoria": str(row.get("Area_Atuacao", "Geral")),
                "Area": str(row.get("Area_Atuacao", "Geral")),
                "Senioridade": str(row.get("Senioridade", "Não especificado")),
                "Modalidade": str(row.get("Modalidade_Trabalho", "Não informado")),
                "Tipo": str(row.get("Tipo_Macro", "Vaga Efetiva")),
                "Skills": row.get("Skills", []) if isinstance(row.get("Skills"), list) else [],
                "Fonte": str(row.get("Fonte", "adzuna")).capitalize(),
                "Data": str(row.get("Data_Formatada", datetime.now().strftime("%d/%m/%Y"))),
                "Empresa": str(row.get("Empresa", "Confidencial / Não informada")),
                "Local": str(row.get("Localizacao", "Brasil")),
                "Salario": salario_str,
            }
            vagas_lista.append(vaga_item)

        payload = {
            "vagas": vagas_lista,
            "total": len(vagas_lista),
            "filtros_disponiveis": {
                "areas": sorted(list(df["Area_Atuacao"].unique())),
                "senioridades": sorted(list(df["Senioridade"].unique())),
                "modalidades": sorted(list(df["Modalidade_Trabalho"].unique())),
                "fontes": sorted(list(df["Fonte"].unique())),
            },
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

        return payload

    def salvar_artefatos(self, live_payload: Dict[str, Any], oportunidades_payload: Dict[str, Any]):
        """Escreve os arquivos JSON e o CSV consolidado."""
        print("\n[4/4] Gravando JSONs e Datasets Consolidados...")

        # Cria diretórios de dados se não existirem
        os.makedirs(DIR_PROCESSED_DATA, exist_ok=True)

        # 1. live_data.json
        with open(ARQUIVO_LIVE_JSON, "w", encoding="utf-8") as f:
            json.dump(live_payload, f, ensure_ascii=False, indent=2)
        print(f"      -> {ARQUIVO_LIVE_JSON} gerado ({live_payload['total']:,} vagas)")

        # 2. oportunidades_data.json
        with open(ARQUIVO_OPORTUNIDADES_JSON, "w", encoding="utf-8") as f:
            json.dump(oportunidades_payload, f, ensure_ascii=False, indent=2)
        print(f"      -> {ARQUIVO_OPORTUNIDADES_JSON} gerado ({oportunidades_payload['total']:,} itens)")

        # 3. CSV Consolidado
        if not self.df_consolidado.empty:
            self.df_consolidado.to_csv(ARQUIVO_CONSOLIDADO_CSV, index=False, encoding="utf-8-sig")
            caminho_extra = DIR_PROCESSED_DATA / "vagas_consolidadas.csv"
            self.df_consolidado.to_csv(caminho_extra, index=False, encoding="utf-8-sig")
            print(f"      -> {ARQUIVO_CONSOLIDADO_CSV} salvo com sucesso")

        print("\n" + "=" * 60)
        print("  PIPELINE EXECUTADO COM SUCESSO!")
        print("=" * 60)


def executar_pipeline():
    """Função de conveniência para disparo rápido."""
    pipeline = PipelineDados()
    df_resultado = pipeline.processar()
    if not df_resultado.empty:
        live = pipeline.gerar_payload_live_data(df_resultado)
        oportunidades = pipeline.gerar_payload_oportunidades(df_resultado)
        pipeline.salvar_artefatos(live, oportunidades)
    return df_resultado
