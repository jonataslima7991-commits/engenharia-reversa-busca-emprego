"""
PONTO DE ENTRADA PRINCIPAL DO SISTEMA
=====================================
Interface de linha de comando (CLI) modular e intuitiva.

Comandos disponíveis:
  python main.py              -> Executa a coleta em todos os scrapers ativos
  python main.py adzuna       -> Coleta apenas na Adzuna
  python main.py gupy         -> Coleta apenas na Gupy
  python main.py process      -> Executa apenas o pipeline de tratamento e dashboards
  python main.py all          -> Executa a coleta completa e em seguida o pipeline
  python main.py status       -> Exibe o resumo do estado atual dos dados e arquivos
"""

import sys
import os
import pandas as pd
from typing import Dict, Type

from scrapers.base import ScraperBase
from scrapers.adzuna import ScraperAdzuna
from scrapers.gupy import ScraperGupy
from core.pipeline import executar_pipeline
from config import ARQUIVOS_FONTES, ARQUIVO_LIVE_JSON, ARQUIVO_OPORTUNIDADES_JSON, ARQUIVO_CONSOLIDADO_CSV

sys.stdout.reconfigure(encoding="utf-8")

SCRAPERS: Dict[str, Type[ScraperBase]] = {
    "adzuna": ScraperAdzuna,
    "gupy": ScraperGupy,
}


def exibir_status():
    """Exibe um painel com o estado atual das coletas e artefatos."""
    print("\n" + "=" * 60)
    print("  STATUS DO PROJETO: ENGENHARIA REVERSA DA BUSCA DE EMPREGO")
    print("=" * 60)

    print("\n[Bases de Dados Brutas (CSVs)]")
    total_bruto = 0
    for fonte, caminhos in ARQUIVOS_FONTES.items():
        encontrado = False
        for c in caminhos:
            if os.path.exists(c):
                try:
                    df = pd.read_csv(c)
                    qtd = len(df)
                    total_bruto += qtd
                    print(f"  • {fonte.upper():<10} : {c.name} -> {qtd:,} vagas")
                    encontrado = True
                    break
                except Exception:
                    pass
        if not encontrado:
            print(f"  • {fonte.upper():<10} : Não encontrado")

    print(f"\n  Total de registros brutos: {total_bruto:,}")

    print("\n[Artefatos do Dashboard]")
    for nome, arq in [
        ("Live Data (JSON)", ARQUIVO_LIVE_JSON),
        ("Oportunidades (JSON)", ARQUIVO_OPORTUNIDADES_JSON),
        ("Dataset Consolidado", ARQUIVO_CONSOLIDADO_CSV),
    ]:
        status_arq = f"Existe ({arq.stat().st_size / 1024:.1f} KB)" if arq.exists() else "Pendente (execute 'python main.py process')"
        print(f"  • {nome:<22} : {status_arq}")

    print("=" * 60 + "\n")


def main():
    args = sys.argv[1:]

    # Se chamado com 'status'
    if args and args[0].lower() == "status":
        exibir_status()
        return

    # Se chamado com 'process' ou 'pipeline'
    if args and args[0].lower() in ["process", "pipeline", "dashboard", "dashboards"]:
        executar_pipeline()
        return

    # Se chamado com 'all'
    if args and args[0].lower() == "all":
        for nome, scraper_cls in SCRAPERS.items():
            print(f"\n[{nome.upper()}] Iniciando coleta...")
            scraper = scraper_cls()
            scraper.coletar()
        executar_pipeline()
        return

    # Se passar nomes de scrapers ou nenhum (roda todos os scrapers)
    alvos = args if args else list(SCRAPERS.keys())

    for nome in alvos:
        nome_limpo = nome.lower()
        if nome_limpo not in SCRAPERS:
            print(f"❌ Comando ou Scraper '{nome}' não reconhecido.")
            print(f"   Opções válidas: {list(SCRAPERS.keys())} | process | status | all")
            continue

        print(f"\n{'=' * 60}")
        print(f"  INICIANDO COLETA: {nome_limpo.upper()}")
        print(f"{'=' * 60}\n")

        scraper = SCRAPERS[nome_limpo]()
        scraper.coletar()

    # Pergunta ou roda o pipeline se rodou tudo
    print("\n💡 Dica: Para atualizar os gráficos e dashboards após a coleta, rode:")
    print("   python main.py process")


if __name__ == "__main__":
    main()