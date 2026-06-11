"""
PONTO DE ENTRADA
================
Para adicionar um novo site no futuro:
  1. Crie scrapers/<site>.py com a classe ScraperXxx(ScraperBase)
  2. Importe e adicione ao dicionário SCRAPERS abaixo
  3. Passe o nome como argumento: python main.py gupy
"""

import sys
from scrapers.adzuna import ScraperAdzuna
from scrapers.gupy   import ScraperGupy

SCRAPERS = {
    "adzuna": ScraperAdzuna,
    "gupy":   ScraperGupy,
}


def main():
    # Se nenhum argumento for passado, roda todos os scrapers disponíveis
    alvos = sys.argv[1:] if len(sys.argv) > 1 else list(SCRAPERS.keys())

    for nome in alvos:
        if nome not in SCRAPERS:
            print(f"❌ Scraper '{nome}' não encontrado. Disponíveis: {list(SCRAPERS.keys())}")
            continue

        print(f"\n{'=' * 60}")
        print(f"  INICIANDO: {nome.upper()}")
        print(f"{'=' * 60}\n")

        scraper = SCRAPERS[nome]()
        scraper.coletar()


if __name__ == "__main__":
    main()