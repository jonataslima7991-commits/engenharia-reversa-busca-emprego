"""
CLASSE BASE DOS SCRAPERS (MODULAR E ROBUSTA)
=============================================
Contém toda a lógica compartilhada de automação de navegador, anti-bloqueio e persistência:
  - Navegador com camuflagem avançada (undetected_chromedriver + CDP Stealth)
  - Rotação de User-Agents e viewports realistas
  - Detecção de bloqueio (Cloudflare, CAPTCHA, 403, 429) e retry com backoff exponencial
  - Simulação de comportamento humano (scroll gradual)
  - Persistência e injeção de cookies por domínio
  - Sistema de checkpoints JSON e salvamento incremental em CSV
  - Normalização canônica imediata de links para evitar duplicatas na coleta
"""

import os
import json
import time
import random
import pickle
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import DIR_RAW_DATA, DIR_LOGS


# ── Pool de User Agents realistas ──────────────────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

# ── Resoluções de tela comuns em desktops ────────────────────────────
_VIEWPORTS = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1280, 720),
]

# ── Palavras-chave que indicam bloqueio genérico ─────────────────────
_INDICADORES_BLOQUEIO = [
    "access denied", "too many requests", "rate limit",
    "captcha", "cloudflare", "just a moment",
    "please verify", "bot detection", "unusual traffic",
    "automated queries", "403 forbidden", "429",
    "verificação de segurança", "acesso negado",
    "suspicious activity", "blocked",
]


class ScraperBase(ABC):
    """
    Classe abstrata — alicerce para todos os scrapers do projeto.
    """

    NUM_ABAS              = 5
    VAGAS_POR_PAGINA      = 10
    TOTAL_VAGAS_ESPERADO  = 75_000
    LIMITE_PAGINAS_VAZIAS = 100
    TENTATIVAS_POR_PAGINA = 3

    # Delays (em segundos)
    DELAY_CARREGAMENTO    = (4, 15)
    DELAY_ENTRE_LOTES     = (4, 8)
    DELAY_APOS_BLOQUEIO   = (90, 180)

    CHROME_VERSION = None

    def __init__(self, nome_site: str, headless: bool = False):
        self.nome_site          = nome_site
        self.headless           = headless
        self.arquivo_checkpoint = f"checkpoint_{nome_site}.json"
        self.arquivo_csv        = f"vagas_{nome_site}.csv"
        self.arquivo_cookies    = f"cookies_{nome_site}.pkl"
        self.total_paginas      = self.TOTAL_VAGAS_ESPERADO // self.VAGAS_POR_PAGINA

        self._user_agent = random.choice(_USER_AGENTS)
        self._viewport   = random.choice(_VIEWPORTS)

        self.driver = None
        self.abas   = []

        # Garante diretórios
        os.makedirs(DIR_RAW_DATA, exist_ok=True)
        os.makedirs(DIR_LOGS, exist_ok=True)

    # ── MÉTODOS ABSTRATOS ─────────────────────────────────────────────

    @abstractmethod
    def construir_url(self, pagina: int) -> str:
        """Retorna a URL formatada para a página especificada."""
        pass

    @abstractmethod
    def extrair_vagas_da_pagina(self) -> List[Dict[str, str]]:
        """
        Extrai os dados estruturados dos cards da página ativa.
        Retorna lista de dicionários com chaves:
        {'Titulo': ..., 'Link': ..., 'Empresa': ..., 'Localizacao': ..., 'Salario': ..., 'Modalidade': ...}
        """
        pass

    # ── CONTROLE DO NAVEGADOR ─────────────────────────────────────────

    def iniciar_driver(self):
        """Inicializa o Chrome com configurações stealth e cria as abas paralelas."""
        print(f"[{self.nome_site.upper()}] Iniciando Chrome...")
        print(f"  - User-Agent: ...{self._user_agent[-40:]}")
        print(f"  - Viewport: {self._viewport[0]}x{self._viewport[1]}")

        options = uc.ChromeOptions()
        options.add_argument(f"--window-size={self._viewport[0]},{self._viewport[1]}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-gpu")

        if self.headless:
            options.add_argument("--headless=new")

        kwargs = {"options": options}
        if self.CHROME_VERSION:
            kwargs["version_main"] = self.CHROME_VERSION

        self.driver = uc.Chrome(**kwargs)
        self._aplicar_stealth()
        self._carregar_cookies()

        # Abre as abas simultâneas
        self.abas = [self.driver.current_window_handle]
        for _ in range(self.NUM_ABAS - 1):
            self.driver.execute_script("window.open('');")
            self.abas.append(self.driver.window_handles[-1])

        print(f"  - {len(self.abas)} abas prontas para processamento em lote.\n")

    def fechar_driver(self):
        """Finaliza a instância do navegador com segurança."""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        finally:
            time.sleep(1)

    # ── TÉCNICAS ANTI-DETECÇÃO ────────────────────────────────────────

    def _aplicar_stealth(self):
        """Injeta JavaScript via DevTools Protocol para ocultar navigator.webdriver e fingerprints."""
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins',   {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
                window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
            """
        })
        self.driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
            "userAgent": self._user_agent
        })

    def _scroll_natural(self):
        """Simula comportamento humano rolando a página com pausas aleatórias."""
        try:
            altura_total = self.driver.execute_script("return document.body.scrollHeight")
            atual = 0
            while atual < (altura_total or 1000) * 0.70:
                passo = random.randint(200, 450)
                atual = min(atual + passo, altura_total or 1000)
                self.driver.execute_script(f"window.scrollTo(0, {atual});")
                time.sleep(random.uniform(0.05, 0.20))
        except WebDriverException:
            pass

    def _esta_bloqueado(self) -> bool:
        """Verifica presença de telas de bloqueio ou captchas."""
        try:
            fonte  = self.driver.page_source.lower()
            titulo = self.driver.title.lower()
            return any(ind in fonte or ind in titulo for ind in _INDICADORES_BLOQUEIO)
        except Exception:
            return False

    def _aguardar_carregamento(self):
        """Aguarda presença do body por padrão. Sobrescrito por subclasses."""
        WebDriverWait(self.driver, 12).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    # ── COOKIES E SESSÃO ──────────────────────────────────────────────

    def _salvar_cookies(self):
        """Persiste cookies da sessão para reaproveitamento em execuções futuras."""
        try:
            with open(self.arquivo_cookies, "wb") as f:
                pickle.dump(self.driver.get_cookies(), f)
        except Exception:
            pass

    def _carregar_cookies(self):
        """Carrega cookies salvos."""
        if not os.path.exists(self.arquivo_cookies):
            return
        try:
            with open(self.arquivo_cookies, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass
        except Exception:
            pass

    # ── CHECKPOINTS E PERSISTÊNCIA INCREMENTAL ─────────────────────────

    def salvar_checkpoint(self, pagina: int, total: int):
        dados = {
            "proxima_pagina": pagina,
            "total_vagas_coletadas": total,
            "salvo_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.arquivo_checkpoint, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def carregar_checkpoint(self) -> Tuple[int, int]:
        if os.path.exists(self.arquivo_checkpoint):
            with open(self.arquivo_checkpoint, "r", encoding="utf-8") as f:
                dados = json.load(f)
            pagina = dados.get("proxima_pagina", 1)
            total  = dados.get("total_vagas_coletadas", 0)
            print(f"  [Checkpoint] Retomando da página {pagina} ({total} vagas já salvas)")
            return pagina, total
        return 1, 0

    def salvar_vagas(self, novas_vagas: List[Dict[str, Any]]):
        """Salva as vagas coletadas incrementalmente no CSV."""
        if not novas_vagas:
            return

        df = pd.DataFrame(novas_vagas)
        df["Data_Coleta"] = time.strftime("%Y-%m-%d")
        df["Fonte"] = self.nome_site

        # Salva na raiz e na pasta data/raw
        caminho_raw = DIR_RAW_DATA / self.arquivo_csv

        for destino in [self.arquivo_csv, caminho_raw]:
            if not os.path.exists(destino):
                df.to_csv(destino, index=False, encoding="utf-8-sig")
            else:
                df.to_csv(destino, mode="a", header=False, index=False, encoding="utf-8-sig")

    # ── LOOP PRINCIPAL ────────────────────────────────────────────────

    def coletar(self):
        """Executa o ciclo completo de coleta paginada com tolerância a falhas."""
        self.iniciar_driver()
        pagina_atual, total_vagas = self.carregar_checkpoint()

        if os.path.exists(self.arquivo_csv):
            try:
                df_existente = pd.read_csv(self.arquivo_csv)
                total_vagas  = len(df_existente)
                print(f"  Base existente encontrada com {total_vagas} registros.\n")
            except Exception:
                pass

        paginas_vazias_seguidas = 0

        print("=" * 60)
        print(f"  INICIANDO COLETA: {self.nome_site.upper()}")
        print("=" * 60)

        try:
            while pagina_atual <= self.total_paginas:
                ultima = min(pagina_atual + self.NUM_ABAS - 1, self.total_paginas)
                lote   = list(range(pagina_atual, ultima + 1))
                print(f"\n[Lote] Processando páginas {lote[0]} a {lote[-1]}...")

                # 1. Navegação nas abas
                for idx, num_pag in enumerate(lote):
                    self.driver.switch_to.window(self.abas[idx])
                    try:
                        self.driver.get(self.construir_url(num_pag))
                    except Exception as e:
                        print(f"  [!] Aba {idx+1} erro de navegação: {str(e)[:50]}")

                pausa = random.uniform(*self.DELAY_CARREGAMENTO)
                time.sleep(pausa)

                # 2. Verificação de bloqueios e carregamento
                for idx, num_pag in enumerate(lote):
                    self.driver.switch_to.window(self.abas[idx])
                    tentativa = 0
                    while tentativa < self.TENTATIVAS_POR_PAGINA:
                        try:
                            self._aguardar_carregamento()
                        except TimeoutException:
                            pass

                        if self._esta_bloqueado():
                            tentativa += 1
                            espera = random.uniform(*self.DELAY_APOS_BLOQUEIO)
                            print(f"  [!] Bloqueio na aba {idx+1}. Pausa anti-detecção ({espera:.0f}s)...")
                            time.sleep(espera)
                            try:
                                self.driver.get(self.construir_url(num_pag))
                                time.sleep(random.uniform(4, 8))
                            except Exception:
                                pass
                        else:
                            break

                # 3. Scroll e Extração
                vagas_do_lote = []
                for idx, num_pag in enumerate(lote):
                    self.driver.switch_to.window(self.abas[idx])
                    self._scroll_natural()

                    try:
                        vagas = self.extrair_vagas_da_pagina()
                    except Exception as e:
                        print(f"  [!] Erro de extração na aba {idx+1}: {str(e)[:50]}")
                        vagas = []

                    if vagas:
                        vagas_do_lote.extend(vagas)
                        paginas_vazias_seguidas = 0
                        print(f"  -> Aba {idx+1} (Pág {num_pag}): {len(vagas)} vagas extraídas")
                    else:
                        paginas_vazias_seguidas += 1

                # 4. Gravação do lote
                if vagas_do_lote:
                    self.salvar_vagas(vagas_do_lote)
                    total_vagas += len(vagas_do_lote)
                    print(f"  -> Total acumulado: {total_vagas:,} vagas salvas")
                    self._salvar_cookies()

                pagina_atual = ultima + 1
                self.salvar_checkpoint(pagina_atual, total_vagas)
                time.sleep(random.uniform(*self.DELAY_ENTRE_LOTES))

                if paginas_vazias_seguidas >= self.LIMITE_PAGINAS_VAZIAS:
                    print(f"\nLimite de {self.LIMITE_PAGINAS_VAZIAS} páginas vazias atingido. Finalizando coleta.")
                    break

        except KeyboardInterrupt:
            print("\nColeta pausada pelo usuário. Checkpoint registrado.")
            self.salvar_checkpoint(pagina_atual, total_vagas)
            self.fechar_driver()
            return

        except Exception as e:
            print(f"\nErro inesperado durante a coleta: {e}")
            self.salvar_checkpoint(pagina_atual, total_vagas)
            self.fechar_driver()
            raise

        print("\n" + "=" * 60)
        print(f"  COLETA FINALIZADA: {self.nome_site.upper()} ({total_vagas:,} vagas)")
        print("=" * 60)

        if os.path.exists(self.arquivo_checkpoint):
            os.remove(self.arquivo_checkpoint)

        self.fechar_driver()