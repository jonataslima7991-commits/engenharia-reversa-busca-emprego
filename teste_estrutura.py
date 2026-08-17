"""
TESTE DE ESTRUTURA E INTEGRIDADE ARQUITETURAL
==============================================
Verifica todos os módulos, classes, métodos e pipeline sem abrir o navegador.
Executa a validação unitária do desduplicador, classificador e extrator de skills.

Execute com:
  python teste_estrutura.py
"""

import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SEP = "=" * 60


def checar(descricao: str, condicao: bool) -> bool:
    status = "  [OK]  " if condicao else "  [FAIL]"
    print(f"{status}  {descricao}")
    return condicao


def testar_tudo():
    print("\n" + SEP)
    print("  SUÍTE DE VERIFICAÇÃO ARQUITETURAL DO SISTEMA")
    print(SEP + "\n")

    resultados = []

    # 1. Arquivos Fundamentais
    print("[1] Verificação de Arquivos e Módulos")
    arquivos_esperados = [
        "config.py",
        "core/__init__.py",
        "core/deduplication.py",
        "core/classifier.py",
        "core/extractor.py",
        "core/pipeline.py",
        "scrapers/__init__.py",
        "scrapers/base.py",
        "scrapers/adzuna.py",
        "scrapers/gupy.py",
        "main.py",
        "gerar_dashboard.py",
        "index.html",
        "oportunidades.html",
    ]

    for arq in arquivos_esperados:
        resultados.append(checar(f"Arquivo presente: {arq}", os.path.exists(arq)))

    # 2. Teste Unitário do Core (Deduplicador, Classificador, Extrator)
    print("\n[2] Teste Unitário: Core Modules")
    try:
        from core.deduplication import Deduplicador
        from core.classifier import Classificador
        from core.extractor import ExtratorSkillsSalario
        from core.pipeline import PipelineDados

        # 2.1 Teste Deduplicador
        url_teste = "https://www.adzuna.com.br/land/ad/999999?se=tracking_123&title=Analista_de_Dados"
        url_limpa = Deduplicador.normalizar_url(url_teste)
        resultados.append(checar("Normalização Canônica de URL (Deduplicador)", url_limpa == "https://www.adzuna.com.br/land/ad/999999"))

        dados_simulados = [
            {"Titulo": "Engenheiro de Dados Python", "Link": "https://site.com/vaga/1?utm_source=fb", "Empresa": "Empresa A"},
            {"Titulo": "Engenheiro de Dados - Python", "Link": "https://site.com/vaga/1?utm_source=google", "Empresa": "Empresa A"},
            {"Titulo": "Cientista de Dados Senior", "Link": "https://site.com/vaga/2", "Empresa": "Empresa B"},
        ]
        df_sim = pd.DataFrame(dados_simulados)
        df_dedup, metricas = Deduplicador.executar(df_sim)
        resultados.append(checar("Remoção de Duplicatas Estruturais/URL", len(df_dedup) == 2))

        # 2.2 Teste Classificador
        area_bolsa = Classificador.classificar_area("Bolsista FAPESP de Mestrado em Ciência de Dados")
        area_eng = Classificador.classificar_area("Engenheiro de Dados Pleno AWS")
        area_ia = Classificador.classificar_area("Engenheiro de Machine Learning / IA Generativa")
        sen_jr = Classificador.classificar_senioridade("Analista de Dados Júnior")

        resultados.append(checar("Detecção de Bolsa Acadêmica (Classificador)", area_bolsa == "Bolsas de Pesquisa"))
        resultados.append(checar("Detecção de Engenharia de Dados (Classificador)", area_eng == "Engenharia de Dados"))
        resultados.append(checar("Detecção de IA & ML (Classificador)", area_ia == "IA & Machine Learning"))
        resultados.append(checar("Detecção de Senioridade Júnior (Classificador)", sen_jr == "Júnior"))

        # 2.3 Teste Extrator
        skills = ExtratorSkillsSalario.extrair_skills("Vaga para Engenheiro com Python, SQL, AWS e dbt")
        resultados.append(checar("Extração de Múltiplas Skills (Extrator)", set(["Python", "SQL", "AWS", "dbt"]).issubset(set(skills))))

        sal_parse = ExtratorSkillsSalario.parser_salario("Salário de R$ 6.000 a R$ 8.000")
        resultados.append(checar("Parsing Salarial Médio (Extrator)", sal_parse["salario_medio"] == 7000.0))

    except Exception as e:
        resultados.append(checar(f"Erro nos módulos core: {e}", False))

    # 3. Verificação dos Scrapers
    print("\n[3] Verificação dos Coletores (Scrapers)")
    try:
        from scrapers.base import ScraperBase
        from scrapers.adzuna import ScraperAdzuna
        from scrapers.gupy import ScraperGupy

        resultados.append(checar("ScraperAdzuna herda de ScraperBase", issubclass(ScraperAdzuna, ScraperBase)))
        resultados.append(checar("ScraperGupy herda de ScraperBase", issubclass(ScraperGupy, ScraperBase)))
        resultados.append(checar("Método ScraperBase.coletar presente", hasattr(ScraperBase, "coletar")))
    except Exception as e:
        resultados.append(checar(f"Scrapers dependem de Selenium: {e}", False))

    # Resumo Final
    print("\n" + SEP)
    total = len(resultados)
    sucessos = sum(1 for r in resultados if r)
    taxa = (sucessos / total * 100) if total > 0 else 0
    print(f"  RESULTADO DOS TESTES: {sucessos}/{total} aprovados ({taxa:.1f}%)")
    print(SEP + "\n")


if __name__ == "__main__":
    testar_tudo()