"""
╔══════════════════════════════════════════════════════════════════╗
║     AGREGADOR DE VAGAS ADZUNA — v6.2 (COM CHECKPOINT)           ║
║  Retoma de onde parou se interrompido.                          ║
╚══════════════════════════════════════════════════════════════════╝
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import undetected_chromedriver as uc
import random
import json
import os

# =========================================================
# CONFIGURAÇÕES
# =========================================================
NUM_ABAS = 5                         # abas simultâneas
VAGAS_POR_PAGINA = 10                # fixo do Adzuna
TOTAL_VAGAS_ESPERADO = 75000         # 75 mil vagas
TOTAL_PAGINAS = TOTAL_VAGAS_ESPERADO // VAGAS_POR_PAGINA  # 7500

# Arquivos de checkpoint e CSV incremental
CHECKPOINT_FILE = "checkpoint.json"
CSV_PARCIAL = "vagas_parcial.csv"

# =========================================================
# FUNÇÕES DE CHECKPOINT E SALVAMENTO INCREMENTAL
# =========================================================
def salvar_checkpoint(pagina_atual, total_vagas_coletadas):
    checkpoint = {
        "ultima_pagina_processada": pagina_atual - 1,
        "proxima_pagina": pagina_atual,
        "total_vagas_coletadas": total_vagas_coletadas,
        "timestamp": time.time()
    }
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)
    print(f"💾 Checkpoint: próxima página = {pagina_atual}, total vagas = {total_vagas_coletadas}")

def carregar_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            cp = json.load(f)
        print(f"🔄 Retomando da página {cp['proxima_pagina']} (já coletadas {cp['total_vagas_coletadas']} vagas)")
        return cp["proxima_pagina"], cp["total_vagas_coletadas"]
    else:
        return 1, 0

def salvar_vagas_incremental(novas_vagas):
    if not novas_vagas:
        return
    df_novo = pd.DataFrame(novas_vagas)
    if not os.path.exists(CSV_PARCIAL):
        df_novo.to_csv(CSV_PARCIAL, index=False, encoding="utf-8-sig")
    else:
        df_novo.to_csv(CSV_PARCIAL, mode='a', header=False, index=False, encoding="utf-8-sig")
    # Opcional: exibir total atual (pode ser lento se o CSV for grande)
    # total_atual = len(pd.read_csv(CSV_PARCIAL)) if os.path.exists(CSV_PARCIAL) else 0
    # print(f"   💾 Salvas {len(novas_vagas)} vagas (total no CSV: {total_atual})")

# =========================================================
# INICIALIZAÇÃO (UMA ÚNICA JANELA)
# =========================================================
driver = uc.Chrome(version_main=147)

# Abre a primeira aba (já existe)
abas = [driver.current_window_handle]

# Cria mais NUM_ABAS - 1 abas na mesma janela
for _ in range(NUM_ABAS - 1):
    driver.execute_script("window.open('');")
    abas.append(driver.window_handles[-1])

print(f"✅ {len(abas)} abas abertas na mesma janela do Chrome.\n")

# =========================================================
# FUNÇÃO: extrair vagas de uma página (já carregada)
# =========================================================
def extrair_vagas_da_aba_ativa():
    """Retorna lista de dicionários {'Titulo':..., 'Link':...} ou lista vazia."""
    try:
        wait = WebDriverWait(driver, 8)
        vagas = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[@data-js='jobLink']"))
        )
    except (TimeoutException, NoSuchElementException):
        vagas = driver.find_elements(By.XPATH, "//a[@data-js='jobLink']")
    
    dados = []
    for vaga in vagas:
        titulo = vaga.text.strip()
        link = vaga.get_attribute("href")
        if titulo and link:
            dados.append({"Titulo": titulo, "Link": link})
    return dados

# =========================================================
# CARREGAR PROGRESSO ANTERIOR
# =========================================================
pagina_atual, total_vagas_coletadas = carregar_checkpoint()
# Se já existir CSV parcial, podemos carregar a contagem real (opcional)
if os.path.exists(CSV_PARCIAL):
    df_existente = pd.read_csv(CSV_PARCIAL)
    total_vagas_coletadas = len(df_existente)
    print(f"📂 CSV parcial encontrado com {total_vagas_coletadas} vagas. Continuando...")
    # Atenção: a página atual veio do checkpoint, confie nele
else:
    total_vagas_coletadas = 0

# =========================================================
# LOOP PRINCIPAL (LOTES DE PÁGINAS)
# =========================================================
paginas_consecutivas_vazias = 0
LIMITE_CONSECUTIVO_VAZIO = 100   # 100 páginas vazias seguidas e para (ajuste opcional)

try:
    while pagina_atual <= TOTAL_PAGINAS:
        fim_lote = min(pagina_atual + NUM_ABAS - 1, TOTAL_PAGINAS)
        paginas_lote = list(range(pagina_atual, fim_lote + 1))
        
        print(f"\n📦 Processando lote: páginas {paginas_lote[0]} a {paginas_lote[-1]}...")
        
        # --- PASSO 1: Disparar navegações ---
        for idx, p in enumerate(paginas_lote):
            driver.switch_to.window(abas[idx])
            url = f'https://www.adzuna.com.br/search?loc=109016&q=Dados&p={p}'
            try:
                driver.get(url)
                print(f"   🔄 Aba {idx+1} carregando página {p}")
            except Exception as e:
                print(f"   ❌ Aba {idx+1} erro ao carregar pág {p}: {str(e)[:50]}")
        
        time.sleep(random.uniform(5, 25))
        
        # --- PASSO 2: Aguardar carregamento de cada aba ---
        for idx, p in enumerate(paginas_lote):
            driver.switch_to.window(abas[idx])
            try:
                WebDriverWait(driver, 12).until(
                    EC.presence_of_element_located((By.XPATH, "//a[@data-js='jobLink']"))
                )
                print(f"   ✅ Aba {idx+1} carregada (pág {p})")
            except TimeoutException:
                print(f"   ⚠️ Aba {idx+1} timeout na página {p}")
        
        # --- PASSO 3: Extrair dados e salvar incrementalmente ---
        vagas_do_lote = []
        for idx, p in enumerate(paginas_lote):
            driver.switch_to.window(abas[idx])
            try:
                vagas_extraidas = extrair_vagas_da_aba_ativa()
            except Exception as e:
                print(f"   ❌ Aba {idx+1} falha na extração pág {p}: {str(e)[:50]}")
                vagas_extraidas = []
            
            if vagas_extraidas:
                vagas_do_lote.extend(vagas_extraidas)
                paginas_consecutivas_vazias = 0
                print(f"   📝 Aba {idx+1} → {len(vagas_extraidas)} vagas")
            else:
                paginas_consecutivas_vazias += 1
                print(f"   ⏭️ Aba {idx+1} → SEM vagas na página {p}")
        
        # Salvar as vagas deste lote no CSV incremental
        if vagas_do_lote:
            salvar_vagas_incremental(vagas_do_lote)
            total_vagas_coletadas += len(vagas_do_lote)
        
        # Salvar checkpoint (página concluída)
        pagina_atual = fim_lote + 1
        salvar_checkpoint(pagina_atual, total_vagas_coletadas)
        
        # Pausa entre lotes
        time.sleep(random.uniform(5, 10))
        
        # Parada automática se muitas páginas vazias consecutivas (opcional)
        if paginas_consecutivas_vazias >= LIMITE_CONSECUTIVO_VAZIO:
            print(f"\n🛑 {LIMITE_CONSECUTIVO_VAZIO} páginas vazias seguidas. Encerrando coleta.")
            break

except KeyboardInterrupt:
    print("\n⚠️ Interrupção manual detectada. Salvando checkpoint antes de sair...")
    salvar_checkpoint(pagina_atual, total_vagas_coletadas)
    print("Progresso salvo. Você pode retomar depois executando o script novamente.")
    driver.quit()
    exit(0)
except Exception as e:
    print(f"\n❌ Erro fatal: {e}. Salvando checkpoint...")
    salvar_checkpoint(pagina_atual, total_vagas_coletadas)
    driver.quit()
    raise

# =========================================================
# FINALIZAÇÃO
# =========================================================
print(f"\n🔚 Coleta concluída. Total de vagas coletadas: {total_vagas_coletadas}")
if os.path.exists(CSV_PARCIAL):
    print(f"📁 Arquivo final: {CSV_PARCIAL}")

# Opcional: renomear o CSV parcial para um nome definitivo
if total_vagas_coletadas > 0:
    final_csv = "minhas_vagas_completas_definitiva.csv"
    os.rename(CSV_PARCIAL, final_csv)
    print(f"✅ Arquivo renomeado para '{final_csv}'")
    # Remove checkpoint após sucesso (opcional)
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

driver.quit()