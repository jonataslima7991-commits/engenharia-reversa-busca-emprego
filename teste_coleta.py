"""
TESTE DE COLETA REAL
====================
Coleta apenas 1 pagina da Adzuna para verificar se o scraper
funciona de ponta a ponta (abre Chrome, acessa o site, extrai vagas).

Arquivos gerados:
  vagas_teste.csv          (nao toca no vagas_adzuna.csv real)
  checkpoint_teste.json    (removido ao final)

Execute com:  python teste_coleta.py
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from scrapers.adzuna import ScraperAdzuna


class ScraperAdzunaTeste(ScraperAdzuna):
    """
    Subclasse apenas para teste:
    - 1 aba, 1 pagina, delays curtos
    - arquivos separados (nao sobrescreve dados reais)
    """
    NUM_ABAS             = 1
    TOTAL_VAGAS_ESPERADO = 10   # = 1 pagina
    DELAY_CARREGAMENTO   = (4, 7)
    DELAY_ENTRE_LOTES    = (2, 3)

    def __init__(self):
        super().__init__()
        # Sobrescreve os caminhos para nao misturar com dados reais
        self.arquivo_csv        = "vagas_teste.csv"
        self.arquivo_checkpoint = "checkpoint_teste.json"
        self.arquivo_cookies    = "cookies_teste.pkl"


print()
print("=" * 55)
print("  TESTE DE COLETA — 1 pagina da Adzuna")
print("=" * 55)
print()
print("  O Chrome vai abrir automaticamente.")
print("  Nao feche a janela durante o teste.")
print()

inicio = time.time()
scraper = ScraperAdzunaTeste()
scraper.coletar()
duracao = time.time() - inicio

print()
print("-" * 55)

# Verifica o resultado
if os.path.exists("vagas_teste.csv"):
    import pandas as pd
    df = pd.read_csv("vagas_teste.csv")
    print(f"  Vagas coletadas : {len(df)}")
    print(f"  Duracao         : {duracao:.0f}s")
    print()
    print("  Amostra (primeiras 5):")
    print()
    for _, row in df.head(5).iterrows():
        print(f"    Titulo : {row['Titulo']}")
        print(f"    Link   : {row['Link'][:70]}...")
        print()

    # Remove arquivo de teste
    os.remove("vagas_teste.csv")
    print("  Arquivo de teste removido.")
    print()
    print("  [OK] Coleta funcionando corretamente!")
else:
    print("  [FAIL] Nenhum arquivo gerado. Verifique os erros acima.")

print("=" * 55)
print()