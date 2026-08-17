"""
GERADOR DE DADOS PARA OS DASHBOARDS
=====================================
Lê os CSVs coletados, processa os dados com deduplicação avançada em 3 camadas,
classificação multidimensional, extração de skills e parsing salarial, gerando:

  live_data.json
      KPIs consolidados, métricas de deduplicação, evolução temporal,
      salários médios e top tecnologias demandadas.
      Consumido pelo index.html.

  oportunidades_data.json
      Feed completo de vagas com filtros por área, senioridade,
      modalidade, empresa e tecnologias.
      Consumido pelo oportunidades.html.

Execute a qualquer momento com:
  python gerar_dashboard.py
"""

import sys
from core.pipeline import executar_pipeline

sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    print("\nExecutando Pipeline de Dados do Projeto...")
    executar_pipeline()
    print("\n[OK] Dashboards atualizados com sucesso! Abra index.html ou oportunidades.html.")