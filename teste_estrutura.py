"""
TESTE DE ESTRUTURA — PASSOS 1 e 2
==================================
Verifica arquivos, heranca, metodos e comportamento basico.
Nao abre o Chrome nem faz requisicoes.

Execute com:  python teste_estrutura.py
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

SEP = "-" * 58


def checar(descricao, condicao):
    status = "[OK]  " if condicao else "[FAIL]"
    print(f"  {status}  {descricao}")
    return condicao


resultados = []

print()
print("=" * 58)
print("  VERIFICACAO DA ESTRUTURA")
print("=" * 58)


# ── 1. Arquivos ───────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  1. Arquivos criados")
print(SEP)

resultados += [
    checar("scrapers/__init__.py",  os.path.isfile("scrapers/__init__.py")),
    checar("scrapers/base.py",      os.path.isfile("scrapers/base.py")),
    checar("scrapers/adzuna.py",    os.path.isfile("scrapers/adzuna.py")),
    checar("main.py",               os.path.isfile("main.py")),
    checar("scraper_adzuna.py (original preservado)", os.path.isfile("scraper_adzuna.py")),
]


# ── 2. Importacoes ────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  2. Importacoes")
print(SEP)

ScraperBase   = None
ScraperAdzuna = None

try:
    from scrapers.base import ScraperBase
    resultados.append(checar("ScraperBase importada", True))
except Exception as e:
    resultados.append(checar(f"ScraperBase importada: {e}", False))

try:
    from scrapers.adzuna import ScraperAdzuna
    resultados.append(checar("ScraperAdzuna importada", True))
except Exception as e:
    resultados.append(checar(f"ScraperAdzuna importada: {e}", False))


# ── 3. Heranca e metodos comuns ───────────────────────────────────────
print(f"\n{SEP}")
print("  3. Heranca e metodos comuns (ScraperBase)")
print(SEP)

if ScraperBase and ScraperAdzuna:
    resultados += [
        checar("ScraperAdzuna herda de ScraperBase",
               issubclass(ScraperAdzuna, ScraperBase)),

        # Loop e persistencia
        checar("metodo 'coletar' existe na base",
               hasattr(ScraperBase, "coletar")),
        checar("metodo 'salvar_checkpoint' existe na base",
               hasattr(ScraperBase, "salvar_checkpoint")),
        checar("metodo 'carregar_checkpoint' existe na base",
               hasattr(ScraperBase, "carregar_checkpoint")),
        checar("metodo 'salvar_vagas' existe na base",
               hasattr(ScraperBase, "salvar_vagas")),

        # Novos metodos do Passo 2
        checar("metodo '_aplicar_stealth' existe na base",
               hasattr(ScraperBase, "_aplicar_stealth")),
        checar("metodo '_scroll_natural' existe na base",
               hasattr(ScraperBase, "_scroll_natural")),
        checar("metodo '_esta_bloqueado' existe na base",
               hasattr(ScraperBase, "_esta_bloqueado")),
        checar("metodo '_salvar_cookies' existe na base",
               hasattr(ScraperBase, "_salvar_cookies")),
        checar("metodo '_carregar_cookies' existe na base",
               hasattr(ScraperBase, "_carregar_cookies")),
    ]
else:
    print("  [SKIP] Nao foi possivel importar as classes.")


# ── 4. Metodos abstratos e sobrescritos ───────────────────────────────
print(f"\n{SEP}")
print("  4. Metodos abstratos e implementacoes")
print(SEP)

if ScraperBase and ScraperAdzuna:
    resultados += [
        checar("'construir_url' e abstrato na base",
               getattr(getattr(ScraperBase, "construir_url"), "__isabstractmethod__", False)),

        checar("'extrair_vagas_da_pagina' e abstrato na base",
               getattr(getattr(ScraperBase, "extrair_vagas_da_pagina"), "__isabstractmethod__", False)),

        checar("ScraperAdzuna implementa 'construir_url'",
               "construir_url" in ScraperAdzuna.__dict__),

        checar("ScraperAdzuna implementa 'extrair_vagas_da_pagina'",
               "extrair_vagas_da_pagina" in ScraperAdzuna.__dict__),

        checar("ScraperAdzuna sobreescreve '_aguardar_carregamento'",
               "_aguardar_carregamento" in ScraperAdzuna.__dict__),

        checar("ScraperAdzuna sobreescreve '_esta_bloqueado'",
               "_esta_bloqueado" in ScraperAdzuna.__dict__),
    ]


# ── 5. Comportamento sem abrir o Chrome ───────────────────────────────
print(f"\n{SEP}")
print("  5. Comportamento basico (sem Chrome)")
print(SEP)

if ScraperBase and ScraperAdzuna:
    try:
        # Instancia sem chamar coletar() — nao abre Chrome
        scraper = object.__new__(ScraperAdzuna)
        ScraperBase.__init__(scraper, nome_site="adzuna")

        url1 = scraper.construir_url(1)
        url3 = scraper.construir_url(3)

        resultados += [
            checar(f"construir_url(1) contem p=1 e adzuna.com.br",
                   "p=1" in url1 and "adzuna.com.br" in url1),

            checar(f"construir_url(3) contem p=3",
                   "p=3" in url3),

            checar("checkpoint nomeado por site: checkpoint_adzuna.json",
                   scraper.arquivo_checkpoint == "checkpoint_adzuna.json"),

            checar("csv nomeado por site: vagas_adzuna.csv",
                   scraper.arquivo_csv == "vagas_adzuna.csv"),

            checar("cookies nomeado por site: cookies_adzuna.pkl",
                   scraper.arquivo_cookies == "cookies_adzuna.pkl"),

            checar("user_agent foi sortido (nao esta vazio)",
                   bool(scraper._user_agent)),

            checar("viewport foi sortido (tupla com 2 valores)",
                   isinstance(scraper._viewport, tuple) and len(scraper._viewport) == 2),

            checar("TENTATIVAS_POR_PAGINA definido e >= 1",
                   scraper.TENTATIVAS_POR_PAGINA >= 1),

            checar("DELAY_APOS_BLOQUEIO e maior que DELAY_CARREGAMENTO",
                   scraper.DELAY_APOS_BLOQUEIO[0] > scraper.DELAY_CARREGAMENTO[1]),
        ]

    except Exception as e:
        print(f"  [FAIL]  Erro ao instanciar ScraperAdzuna: {e}")


# ── 6. ScraperGupy ────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  6. ScraperGupy (passo 3)")
print(SEP)

ScraperGupy = None

try:
    from scrapers.gupy import ScraperGupy
    resultados.append(checar("ScraperGupy importada", True))
except Exception as e:
    resultados.append(checar(f"ScraperGupy importada: {e}", False))

if ScraperBase and ScraperGupy:
    resultados += [
        checar("ScraperGupy herda de ScraperBase",
               issubclass(ScraperGupy, ScraperBase)),

        checar("ScraperGupy implementa 'construir_url'",
               "construir_url" in ScraperGupy.__dict__),

        checar("ScraperGupy implementa 'extrair_vagas_da_pagina'",
               "extrair_vagas_da_pagina" in ScraperGupy.__dict__),

        checar("ScraperGupy sobreescreve '_aguardar_carregamento'",
               "_aguardar_carregamento" in ScraperGupy.__dict__),

        checar("ScraperGupy sobreescreve '_esta_bloqueado'",
               "_esta_bloqueado" in ScraperGupy.__dict__),
    ]

    try:
        g = object.__new__(ScraperGupy)
        ScraperBase.__init__(g, nome_site="gupy")

        url_g1 = g.construir_url(1)
        url_g2 = g.construir_url(2)

        resultados += [
            checar(f"construir_url(1) contem 'gupy.io' e 'page=1'",
                   "gupy.io" in url_g1 and "page=1" in url_g1),

            checar(f"construir_url(2) contem 'page=2'",
                   "page=2" in url_g2),

            checar("Gupy tem DELAY_CARREGAMENTO maior que Adzuna (SPA)",
                   g.DELAY_CARREGAMENTO[1] > 20),

            checar("csv nomeado por site: vagas_gupy.csv",
                   g.arquivo_csv == "vagas_gupy.csv"),
        ]
    except Exception as e:
        print(f"  [FAIL]  Erro ao instanciar ScraperGupy: {e}")


# ── 7. main.py ────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  7. main.py")
print(SEP)

try:
    import importlib.util
    spec   = importlib.util.spec_from_file_location("main", "main.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    resultados += [
        checar("main.py tem dicionario SCRAPERS",
               hasattr(modulo, "SCRAPERS")),
        checar("'adzuna' registrado em SCRAPERS",
               "adzuna" in getattr(modulo, "SCRAPERS", {})),
        checar("'gupy' registrado em SCRAPERS",
               "gupy" in getattr(modulo, "SCRAPERS", {})),
        checar("main.py tem funcao 'main'",
               hasattr(modulo, "main")),
    ]
except Exception as e:
    print(f"  [FAIL]  Erro ao carregar main.py: {e}")


# ── Resumo ─────────────────────────────────────────────────────────────
passou = sum(resultados)
total  = len(resultados)
status = "TUDO OK" if passou == total else f"ATENCAO -- {total - passou} falha(s)"

print(f"\n{'=' * 58}")
print(f"  RESULTADO: {passou}/{total} verificacoes  ->  {status}")
print("=" * 58)
print()