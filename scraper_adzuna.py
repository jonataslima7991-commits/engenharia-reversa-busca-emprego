"""
╔══════════════════════════════════════════════════════════════════╗
║         COLETOR DE VAGAS — ADZUNA.COM.BR                        ║
║         Projeto: Engenharia Reversa da Busca de Emprego         ║
║         Autor: Jonatas Oliveira de Lima                         ║
║         Curso: Ciência de Dados — FATEC Santana de Parnaíba     ║
║         Ano: 2025                                               ║
╚══════════════════════════════════════════════════════════════════╝

OBJETIVO:
    Coletar títulos e links de vagas da Adzuna.com.br
    usando o termo de busca "Dados", salvando tudo em CSV.

BIBLIOTECAS UTILIZADAS:
    - undetected_chromedriver : abre o Chrome sem ser bloqueado pelo site
    - selenium                : navega nas páginas e extrai dados do HTML
    - pandas                  : organiza e salva os dados em CSV
    - json / os               : gerencia o checkpoint (retomada de progresso)
    - time / random           : pausas entre requisições (simula humano)
"""

# ============================================================
# 1. IMPORTAÇÕES
# ============================================================
import os
import json
import time
import random

import pandas as pd
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# ============================================================
# 2. CONFIGURAÇÕES GERAIS
# ============================================================

# Quantas abas abrimos ao mesmo tempo (coleta paralela)
NUM_ABAS = 5

# Quantas vagas aparecem por página na Adzuna
VAGAS_POR_PAGINA = 10

# Estimativa máxima de vagas disponíveis (define o limite de páginas)
TOTAL_VAGAS_ESPERADO = 75_000
TOTAL_PAGINAS = TOTAL_VAGAS_ESPERADO // VAGAS_POR_PAGINA  # = 7500 páginas

# Nomes dos arquivos gerados
ARQUIVO_CHECKPOINT = "checkpoint.json"   # salva o progresso
ARQUIVO_CSV        = "vagas_coletadas.csv"  # resultado final


# ============================================================
# 3. FUNÇÕES DE APOIO
# ============================================================

def fechar_driver(driver):
    """
    Fecha o navegador com segurança.
    O try/except evita erro do Windows quando o Chrome
    já foi encerrado antes do Python tentar fechar.
    """
    try:
        driver.quit()
    except Exception:
        pass
    finally:
        time.sleep(1)


def salvar_checkpoint(pagina, total):
    """
    Salva o progresso atual em um arquivo JSON.
    Permite retomar a coleta de onde parou caso o script
    seja interrompido (queda de internet, fechamento acidental etc).
    """
    dados = {
        "proxima_pagina": pagina,
        "total_vagas_coletadas": total,
        "salvo_em": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(ARQUIVO_CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    print(f"  💾 Checkpoint salvo — próxima página: {pagina} | total coletado: {total}")


def carregar_checkpoint():
    """
    Lê o checkpoint salvo anteriormente.
    Se não existir, começa do zero (página 1, 0 vagas).
    """
    if os.path.exists(ARQUIVO_CHECKPOINT):
        with open(ARQUIVO_CHECKPOINT, "r", encoding="utf-8") as f:
            dados = json.load(f)
        pagina = dados["proxima_pagina"]
        total  = dados["total_vagas_coletadas"]
        print(f"🔄 Retomando da página {pagina} ({total} vagas já coletadas)")
        return pagina, total

    print("🆕 Nenhum checkpoint encontrado. Iniciando do zero.")
    return 1, 0


def salvar_vagas(novas_vagas):
    """
    Adiciona as vagas coletadas no CSV.
    Se o arquivo ainda não existe, cria com cabeçalho.
    Se já existe, apenas adiciona as linhas novas (modo append).
    """
    if not novas_vagas:
        return

    df = pd.DataFrame(novas_vagas)

    if not os.path.exists(ARQUIVO_CSV):
        # Primeira vez: cria o arquivo com cabeçalho
        df.to_csv(ARQUIVO_CSV, index=False, encoding="utf-8-sig")
    else:
        # Próximas vezes: adiciona sem repetir o cabeçalho
        df.to_csv(ARQUIVO_CSV, mode="a", header=False, index=False, encoding="utf-8-sig")


def extrair_vagas_da_pagina(driver):
    """
    Lê o HTML da página atual e extrai título e link de cada vaga.

    Como funciona:
        A Adzuna marca cada link de vaga com o atributo data-js='jobLink'.
        Usamos esse atributo como "endereço" para o Selenium encontrar
        os elementos certos na página, sem depender de classes CSS
        que podem mudar a qualquer atualização do site.

    Retorna:
        Lista de dicionários: [{"Titulo": "...", "Link": "..."}, ...]
        Lista vazia se não encontrar nada.
    """
    vagas_encontradas = []

    try:
        # Aguarda até 8 segundos para os links de vaga aparecerem na página
        wait = WebDriverWait(driver, 8)
        elementos = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//a[@data-js='jobLink']")
            )
        )
    except TimeoutException:
        # Se demorar mais de 8s, tenta pegar o que já carregou
        elementos = driver.find_elements(By.XPATH, "//a[@data-js='jobLink']")

    for elemento in elementos:
        titulo = elemento.text.strip()
        link   = elemento.get_attribute("href")

        # Só salva se tiver título E link (evita registros incompletos)
        if titulo and link:
            vagas_encontradas.append({"Titulo": titulo, "Link": link})

    return vagas_encontradas


# ============================================================
# 4. INICIALIZAÇÃO DO NAVEGADOR
# ============================================================

print("🚀 Iniciando o navegador Chrome...")

# undetected_chromedriver abre o Chrome de forma que o site
# não detecte que é uma automação (evita bloqueios)
driver = uc.Chrome(version_main=149)

# Pega a aba que já existe ao abrir o Chrome
abas = [driver.current_window_handle]

# Abre mais abas até chegar em NUM_ABAS (total = 5 abas)
for _ in range(NUM_ABAS - 1):
    driver.execute_script("window.open('');")
    abas.append(driver.window_handles[-1])

print(f"✅ {len(abas)} abas abertas e prontas.\n")


# ============================================================
# 5. CARREGAR PROGRESSO ANTERIOR
# ============================================================

pagina_atual, total_vagas = carregar_checkpoint()

# Se o CSV já existe, usa a contagem real de linhas como referência
if os.path.exists(ARQUIVO_CSV):
    df_existente = pd.read_csv(ARQUIVO_CSV)
    total_vagas  = len(df_existente)
    print(f"📂 CSV encontrado com {total_vagas} vagas. Continuando...\n")


# ============================================================
# 6. LOOP PRINCIPAL DE COLETA
# ============================================================

# Contador de páginas seguidas sem nenhuma vaga
# Se chegar a 100, assumimos que acabaram as vagas disponíveis
paginas_vazias_seguidas = 0
LIMITE_PAGINAS_VAZIAS   = 100

print("=" * 60)
print("  INICIANDO COLETA DE VAGAS")
print("=" * 60)

try:
    while pagina_atual <= TOTAL_PAGINAS:

        # Define quais páginas serão coletadas neste lote
        # Exemplo: páginas 1, 2, 3, 4, 5 (uma por aba)
        ultima_pagina_lote = min(pagina_atual + NUM_ABAS - 1, TOTAL_PAGINAS)
        paginas_do_lote    = list(range(pagina_atual, ultima_pagina_lote + 1))

        print(f"\n📦 Lote: páginas {paginas_do_lote[0]} até {paginas_do_lote[-1]}")

        # --- PASSO A: Abrir cada página em uma aba diferente ---
        for indice, numero_pagina in enumerate(paginas_do_lote):
            driver.switch_to.window(abas[indice])
            url = f"https://www.adzuna.com.br/search?loc=109016&q=Dados&p={numero_pagina}"
            try:
                driver.get(url)
                print(f"  🌐 Aba {indice + 1} → página {numero_pagina}")
            except Exception as erro:
                print(f"  ❌ Aba {indice + 1} falhou ao carregar: {str(erro)[:60]}")

        # Pausa aleatória entre 5 e 25 segundos
        # Simula comportamento humano e evita bloqueio automático do site
        pausa = random.uniform(5, 25)
        print(f"  ⏳ Aguardando {pausa:.0f}s para as páginas carregarem...")
        time.sleep(pausa)

        # --- PASSO B: Aguardar carregamento completo de cada aba ---
        for indice, numero_pagina in enumerate(paginas_do_lote):
            driver.switch_to.window(abas[indice])
            try:
                WebDriverWait(driver, 12).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//a[@data-js='jobLink']")
                    )
                )
                print(f"  ✅ Aba {indice + 1} carregada (pág {numero_pagina})")
            except TimeoutException:
                print(f"  ⚠️  Aba {indice + 1} timeout — página {numero_pagina} pode estar vazia")

        # --- PASSO C: Extrair vagas de cada aba e salvar ---
        vagas_do_lote = []

        for indice, numero_pagina in enumerate(paginas_do_lote):
            driver.switch_to.window(abas[indice])

            try:
                vagas = extrair_vagas_da_pagina(driver)
            except Exception as erro:
                print(f"  ❌ Erro na extração — aba {indice + 1}: {str(erro)[:60]}")
                vagas = []

            if vagas:
                vagas_do_lote.extend(vagas)
                paginas_vazias_seguidas = 0
                print(f"  📝 Aba {indice + 1} → {len(vagas)} vagas coletadas")
            else:
                paginas_vazias_seguidas += 1
                print(f"  ⏭️  Aba {indice + 1} → sem vagas na página {numero_pagina}")

        # Salva as vagas deste lote no CSV
        if vagas_do_lote:
            salvar_vagas(vagas_do_lote)
            total_vagas += len(vagas_do_lote)
            print(f"  💾 Total acumulado: {total_vagas} vagas")

        # Avança para o próximo lote e salva checkpoint
        pagina_atual = ultima_pagina_lote + 1
        salvar_checkpoint(pagina_atual, total_vagas)

        # Pausa entre lotes
        time.sleep(random.uniform(5, 10))

        # Para automaticamente se muitas páginas seguidas estiverem vazias
        if paginas_vazias_seguidas >= LIMITE_PAGINAS_VAZIAS:
            print(f"\n🛑 {LIMITE_PAGINAS_VAZIAS} páginas vazias seguidas. Encerrando.")
            break


# ============================================================
# 7. TRATAMENTO DE INTERRUPÇÕES
# ============================================================

except KeyboardInterrupt:
    # Ctrl+C pressionado pelo usuário
    print("\n⚠️  Coleta interrompida manualmente.")
    print("   Salvando progresso para retomar depois...")
    salvar_checkpoint(pagina_atual, total_vagas)
    fechar_driver(driver)
    print("✅ Progresso salvo. Execute o script novamente para continuar.")
    exit(0)

except Exception as erro_fatal:
    # Qualquer outro erro inesperado
    print(f"\n❌ Erro inesperado: {erro_fatal}")
    print("   Salvando checkpoint de emergência...")
    salvar_checkpoint(pagina_atual, total_vagas)
    fechar_driver(driver)
    raise


# ============================================================
# 8. FINALIZAÇÃO
# ============================================================

print("\n" + "=" * 60)
print("  COLETA CONCLUÍDA")
print("=" * 60)
print(f"  Total de vagas coletadas : {total_vagas}")
print(f"  Arquivo gerado           : {ARQUIVO_CSV}")

# Remove o checkpoint pois a coleta foi concluída com sucesso
if os.path.exists(ARQUIVO_CHECKPOINT):
    os.remove(ARQUIVO_CHECKPOINT)
    print("  🗑️  Checkpoint removido (coleta completa)")

fechar_driver(driver)
print("\n✅ Tudo pronto!")
