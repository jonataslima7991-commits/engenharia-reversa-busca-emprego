"""
╔══════════════════════════════════════════════════════════════════╗
║     AGREGADOR DE VAGAS ADZUNA — v6.1 (MULTI-ABA + TOLERANTE)    ║
║  Não para em páginas vazias/erro, apenas avança.                ║
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

# =========================================================
# CONFIGURAÇÕES
# =========================================================
NUM_ABAS = 10                         # abas simultâneas
VAGAS_POR_PAGINA = 10                # fixo do Adzuna
TOTAL_VAGAS_ESPERADO = 75000         # 75 mil vagas
TOTAL_PAGINAS = TOTAL_VAGAS_ESPERADO // VAGAS_POR_PAGINA  # 7500
# Se não souber o total, pode rodar até um número grande, ex: 10000
# TOTAL_PAGINAS = 10000

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
        # Aguarda os links de vaga aparecerem (máx 8s)
        wait = WebDriverWait(driver, 8)
        vagas = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[@data-js='jobLink']"))
        )
    except (TimeoutException, NoSuchElementException):
        # Se não encontrar, tenta uma busca simples (pode estar vazio)
        vagas = driver.find_elements(By.XPATH, "//a[@data-js='jobLink']")
    
    dados = []
    for vaga in vagas:
        titulo = vaga.text.strip()
        link = vaga.get_attribute("href")
        if titulo and link:           # só adiciona se tiver título e link
            dados.append({"Titulo": titulo, "Link": link})
    return dados

# =========================================================
# LOOP PRINCIPAL (LOTES DE PÁGINAS)
# =========================================================
lista_de_vagas = []
pagina_atual = 1
paginas_consecutivas_vazias = 0
LIMITE_CONSECUTIVO_VAZIO = 76000   # para parar só se muitas páginas seguidas vazias (opcional)

while pagina_atual <= TOTAL_PAGINAS:
    # Define as páginas deste lote (ex: 1..5, 6..10, ...)
    fim_lote = min(pagina_atual + NUM_ABAS - 1, TOTAL_PAGINAS)
    paginas_lote = list(range(pagina_atual, fim_lote + 1))
    
    print(f"\n📦 Processando lote: páginas {paginas_lote[0]} a {paginas_lote[-1]}...")
    
    # --- PASSO 1: Disparar todas as navegações (uma em cada aba) ---
    for idx, p in enumerate(paginas_lote):
        driver.switch_to.window(abas[idx])
        url = f'https://www.adzuna.com.br/search?loc=109016&q=Dados&p={p}'
        try:
            driver.get(url)
            print(f"   🔄 Aba {idx+1} carregando página {p}")
        except Exception as e:
            print(f"   ❌ Aba {idx+1} erro ao carregar pág {p}: {str(e)[:50]}")
    
    # Pequena pausa para não bombardear o servidor
    time.sleep(random.uniform(5, 25)) # Pausa entre 2 e 4 segundos
    
    # --- PASSO 2: Aguardar carregamento de cada aba (com timeout individual) ---
    for idx, p in enumerate(paginas_lote):
        driver.switch_to.window(abas[idx])
        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.XPATH, "//a[@data-js='jobLink']"))
            )
            print(f"   ✅ Aba {idx+1} carregada (pág {p})")
        except TimeoutException:
            print(f"   ⚠️ Aba {idx+1} timeout na página {p} (pode estar vazia ou lenta)")
        except Exception as e:
            print(f"   ⚠️ Aba {idx+1} erro inesperado: {str(e)[:50]}")
    
    # --- PASSO 3: Extrair dados de cada aba (mesmo se vazia) ---
    for idx, p in enumerate(paginas_lote):
        driver.switch_to.window(abas[idx])
        try:
            vagas_extraidas = extrair_vagas_da_aba_ativa()
        except Exception as e:
            print(f"   ❌ Aba {idx+1} falha na extração pág {p}: {str(e)[:50]}")
            vagas_extraidas = []
        
        if vagas_extraidas:
            lista_de_vagas.extend(vagas_extraidas)
            paginas_consecutivas_vazias = 0   # reset
            print(f"   📝 Aba {idx+1} → {len(vagas_extraidas)} vagas (total acumulado: {len(lista_de_vagas)})")
        else:
            paginas_consecutivas_vazias += 1
            print(f"   ⏭️ Aba {idx+1} → SEM vagas na página {p} (ignorando, continuando...)")
    
    # --- (OPCIONAL) Para automaticamente se muitas páginas seguidas vazias ---
    if paginas_consecutivas_vazias >= LIMITE_CONSECUTIVO_VAZIO:
        print(f"\n🛑 {LIMITE_CONSECUTIVO_VAZIO} páginas consecutivas sem vagas. Finalizando coleta.")
        break
    
    # Pequena pausa entre lotes (evita bloqueio)
    time.sleep(random.uniform(5, 15))   # pausa entre 5 e 10 segundos
    
    # Avança para o próximo lote
    pagina_atual = fim_lote + 1

# =========================================================
# SALVAR RESULTADOS
# =========================================================
if lista_de_vagas:
    tabela = pd.DataFrame(lista_de_vagas)
    nome_arquivo = "minhas_vagas_completas_definitiva.csv"
    tabela.to_csv(nome_arquivo, index=False, encoding="utf-8-sig")
    print(f"\n✅ Arquivo '{nome_arquivo}' salvo com {len(lista_de_vagas)} vagas!")
else:
    print("\n⚠️ Nenhuma vaga encontrada em nenhuma página.")

print(f"\n🔚 Total de páginas varridas: {pagina_atual-1} (de {TOTAL_PAGINAS} planejadas)")
input("Aperte Enter para fechar o navegador...")
driver.quit()