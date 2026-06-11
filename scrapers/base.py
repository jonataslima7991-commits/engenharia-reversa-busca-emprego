"""
CLASSE BASE DOS SCRAPERS
========================
Contém toda a lógica que é COMUM a qualquer site:
  - navegador com camuflagem anti-detecção
  - detecção de bloqueio + retry com backoff
  - simulação de comportamento humano (scroll)
  - persistência de cookies por site
  - checkpoint e CSV
  - loop principal de coleta

Cada site herda esta classe e implementa apenas:
  - construir_url(pagina)        → URL da página N
  - extrair_vagas_da_pagina()    → como ler o HTML daquele site
  - _aguardar_carregamento()     → qual elemento esperar
  - _esta_bloqueado()            → padrão de bloqueio do site (opcional)
"""

import os
import json
import time
import random
import pickle
from abc import ABC, abstractmethod

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


# ── Pool de User Agents realistas (Chrome / Firefox / Safari) ────────
_USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
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
    Classe abstrata — base de todos os scrapers.
    Não pode ser usada diretamente.
    """

    # ── Configurações padrão (sobrescrevíveis nas subclasses) ─────────
    NUM_ABAS              = 5
    VAGAS_POR_PAGINA      = 10
    TOTAL_VAGAS_ESPERADO  = 75_000
    LIMITE_PAGINAS_VAZIAS = 100
    TENTATIVAS_POR_PAGINA = 3      # quantas vezes tenta antes de desistir

    # Faixas de delay (segundos) — ajuste para sites mais defensivos
    DELAY_CARREGAMENTO  = (5, 25)   # pausa após abrir as abas
    DELAY_ENTRE_LOTES   = (5, 10)   # pausa entre lotes de páginas
    DELAY_APOS_BLOQUEIO = (90, 180) # pausa quando detecta bloqueio

    # None = undetected_chromedriver detecta automaticamente
    CHROME_VERSION = None

    # ── Init ──────────────────────────────────────────────────────────

    def __init__(self, nome_site: str):
        self.nome_site          = nome_site
        self.arquivo_checkpoint = f"checkpoint_{nome_site}.json"
        self.arquivo_csv        = f"vagas_{nome_site}.csv"
        self.arquivo_cookies    = f"cookies_{nome_site}.pkl"
        self.total_paginas      = self.TOTAL_VAGAS_ESPERADO // self.VAGAS_POR_PAGINA

        # Sorteia UA e viewport na criação — fixos durante a sessão
        self._user_agent = random.choice(_USER_AGENTS)
        self._viewport   = random.choice(_VIEWPORTS)

        self.driver = None
        self.abas   = []

    # ================================================================
    # MÉTODOS ABSTRATOS — obrigatórios nas subclasses
    # ================================================================

    @abstractmethod
    def construir_url(self, pagina: int) -> str:
        """Retorna a URL da página `pagina` para este site."""

    @abstractmethod
    def extrair_vagas_da_pagina(self) -> list[dict]:
        """
        Lê o HTML da aba ativa e retorna:
        [{"Titulo": "...", "Link": "..."}, ...]
        """

    # ================================================================
    # NAVEGADOR
    # ================================================================

    def iniciar_driver(self):
        """Abre o Chrome com configurações de camuflagem e cria as abas."""
        print(f"Iniciando Chrome  |  UA: ...{self._user_agent[-40:]}")
        print(f"                     Viewport: {self._viewport[0]}x{self._viewport[1]}")

        options = uc.ChromeOptions()
        options.add_argument(f"--window-size={self._viewport[0]},{self._viewport[1]}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-infobars")

        kwargs = {"options": options}
        if self.CHROME_VERSION:
            kwargs["version_main"] = self.CHROME_VERSION

        self.driver = uc.Chrome(**kwargs)

        # CDP: remove traces of automation no nível do navegador
        self._aplicar_stealth()

        # Carrega cookies salvos de sessões anteriores (se existirem)
        self._carregar_cookies()

        # Abre as abas paralelas
        self.abas = [self.driver.current_window_handle]
        for _ in range(self.NUM_ABAS - 1):
            self.driver.execute_script("window.open('');")
            self.abas.append(self.driver.window_handles[-1])

        print(f"{len(self.abas)} abas prontas.\n")

    def fechar_driver(self):
        """Fecha o navegador com segurança."""
        try:
            self.driver.quit()
        except Exception:
            pass
        finally:
            time.sleep(1)

    # ================================================================
    # ANTI-DETECÇÃO
    # ================================================================

    def _aplicar_stealth(self):
        """
        Injeta JS via CDP para remover assinaturas de automação.
        Funciona em sites que verificam navigator.webdriver,
        plugins, linguagens e outros fingerprints.
        """
        # Remove navigator.webdriver e falsifica outras propriedades
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins',   {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
                window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
            """
        })

        # Sobrescreve o User-Agent no protocolo (não só no header HTTP)
        self.driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
            "userAgent": self._user_agent
        })

    def _scroll_natural(self):
        """
        Rola a página gradualmente como um humano faria ao ler.
        Reduz a chance de bloqueio em sites que monitoram
        padrões de interação (LinkedIn, Glassdoor, etc.).
        """
        try:
            altura_total = self.driver.execute_script("return document.body.scrollHeight")
            atual = 0
            # Rola até ~70% da página em passos variáveis
            while atual < altura_total * 0.70:
                passo = random.randint(200, 500)
                atual = min(atual + passo, altura_total)
                self.driver.execute_script(f"window.scrollTo(0, {atual});")
                time.sleep(random.uniform(0.08, 0.35))
        except WebDriverException:
            pass  # tab pode ter sido fechada ou navegação ocorreu

    # ================================================================
    # DETECÇÃO DE BLOQUEIO (pode ser sobrescrito por site)
    # ================================================================

    def _esta_bloqueado(self) -> bool:
        """
        Verifica se a página atual é uma tela de bloqueio/CAPTCHA.
        Cobre: Cloudflare, 403/429, páginas de verificação genéricas.

        Subclasses podem sobrescrever para adicionar padrões específicos
        do site (ex: página de login forçado no LinkedIn).
        """
        try:
            fonte  = self.driver.page_source.lower()
            titulo = self.driver.title.lower()
            return any(ind in fonte or ind in titulo for ind in _INDICADORES_BLOQUEIO)
        except Exception:
            return False

    # ================================================================
    # COOKIES (persistência de sessão entre execuções)
    # ================================================================

    def _salvar_cookies(self):
        """Persiste os cookies da sessão atual para reutilizar depois."""
        try:
            with open(self.arquivo_cookies, "wb") as f:
                pickle.dump(self.driver.get_cookies(), f)
            print(f"  Cookies salvos -> {self.arquivo_cookies}")
        except Exception as e:
            print(f"  Aviso: nao foi possivel salvar cookies ({e})")

    def _carregar_cookies(self):
        """
        Injeta cookies de sessão anterior no driver.
        O driver precisa ter visitado o domínio antes de aceitar cookies,
        então isso é chamado automaticamente pelo loop antes da coleta.
        """
        if not os.path.exists(self.arquivo_cookies):
            return
        try:
            with open(self.arquivo_cookies, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass  # alguns cookies expirados são rejeitados — normal
            print(f"  {len(cookies)} cookies carregados de sessao anterior.")
        except Exception as e:
            print(f"  Aviso: nao foi possivel carregar cookies ({e})")

    # ================================================================
    # CHECKPOINT
    # ================================================================

    def salvar_checkpoint(self, pagina: int, total: int):
        dados = {
            "proxima_pagina":        pagina,
            "total_vagas_coletadas": total,
            "salvo_em":              time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.arquivo_checkpoint, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        print(f"  Checkpoint salvo -> pagina {pagina} | total {total}")

    def carregar_checkpoint(self) -> tuple[int, int]:
        if os.path.exists(self.arquivo_checkpoint):
            with open(self.arquivo_checkpoint, "r", encoding="utf-8") as f:
                dados = json.load(f)
            pagina = dados["proxima_pagina"]
            total  = dados["total_vagas_coletadas"]
            print(f"Retomando da pagina {pagina} ({total} vagas ja coletadas)")
            return pagina, total
        print("Nenhum checkpoint. Iniciando do zero.")
        return 1, 0

    # ================================================================
    # CSV
    # ================================================================

    def salvar_vagas(self, novas_vagas: list[dict]):
        if not novas_vagas:
            return
        df = pd.DataFrame(novas_vagas)
        df["Data_Coleta"] = time.strftime("%Y-%m-%d")
        df["Fonte"]       = self.nome_site
        if not os.path.exists(self.arquivo_csv):
            df.to_csv(self.arquivo_csv, index=False, encoding="utf-8-sig")
        else:
            df.to_csv(self.arquivo_csv, mode="a", header=False, index=False, encoding="utf-8-sig")

    # ================================================================
    # LOOP PRINCIPAL
    # ================================================================

    def coletar(self):
        """Executa a coleta completa para este site."""
        self.iniciar_driver()
        pagina_atual, total_vagas = self.carregar_checkpoint()

        if os.path.exists(self.arquivo_csv):
            df_existente = pd.read_csv(self.arquivo_csv)
            total_vagas  = len(df_existente)
            print(f"CSV encontrado com {total_vagas} vagas. Continuando...\n")

        paginas_vazias_seguidas = 0

        print("=" * 60)
        print(f"  COLETANDO: {self.nome_site.upper()}")
        print("=" * 60)

        try:
            while pagina_atual <= self.total_paginas:

                ultima = min(pagina_atual + self.NUM_ABAS - 1, self.total_paginas)
                lote   = list(range(pagina_atual, ultima + 1))
                print(f"\nLote: paginas {lote[0]}-{lote[-1]}")

                # ── Passo A: abrir páginas nas abas ──────────────────
                for idx, num_pag in enumerate(lote):
                    self.driver.switch_to.window(self.abas[idx])
                    try:
                        self.driver.get(self.construir_url(num_pag))
                        print(f"  Aba {idx+1} -> pagina {num_pag}")
                    except Exception as e:
                        print(f"  Aba {idx+1} falhou: {str(e)[:60]}")

                pausa = random.uniform(*self.DELAY_CARREGAMENTO)
                print(f"  Aguardando {pausa:.0f}s...")
                time.sleep(pausa)

                # ── Passo B: aguardar carregamento + detectar bloqueio ─
                for idx, num_pag in enumerate(lote):
                    self.driver.switch_to.window(self.abas[idx])
                    tentativa = 0
                    while tentativa < self.TENTATIVAS_POR_PAGINA:
                        try:
                            self._aguardar_carregamento()
                        except TimeoutException:
                            pass  # pode estar vazia ou lenta — verifica mesmo assim

                        if self._esta_bloqueado():
                            tentativa += 1
                            espera = random.uniform(*self.DELAY_APOS_BLOQUEIO)
                            print(f"  [!] Bloqueio detectado na aba {idx+1} "
                                  f"(tentativa {tentativa}/{self.TENTATIVAS_POR_PAGINA}). "
                                  f"Aguardando {espera:.0f}s...")
                            time.sleep(espera)
                            # Recarrega a página e tenta novamente
                            try:
                                self.driver.get(self.construir_url(num_pag))
                                time.sleep(random.uniform(5, 10))
                            except Exception:
                                pass
                        else:
                            print(f"  Aba {idx+1} OK (pag {num_pag})")
                            break
                    else:
                        print(f"  Aba {idx+1} continua bloqueada apos {self.TENTATIVAS_POR_PAGINA} tentativas — pulando.")

                # ── Passo C: scroll + extração ───────────────────────
                vagas_do_lote = []
                for idx, num_pag in enumerate(lote):
                    self.driver.switch_to.window(self.abas[idx])

                    # Scroll natural antes de extrair (anti-detecção)
                    self._scroll_natural()

                    try:
                        vagas = self.extrair_vagas_da_pagina()
                    except Exception as e:
                        print(f"  Erro na extracao aba {idx+1}: {str(e)[:60]}")
                        vagas = []

                    if vagas:
                        vagas_do_lote.extend(vagas)
                        paginas_vazias_seguidas = 0
                        print(f"  Aba {idx+1} -> {len(vagas)} vagas")
                    else:
                        paginas_vazias_seguidas += 1
                        print(f"  Aba {idx+1} -> sem vagas (pag {num_pag})")

                # ── Salvar resultado do lote ─────────────────────────
                if vagas_do_lote:
                    self.salvar_vagas(vagas_do_lote)
                    total_vagas += len(vagas_do_lote)
                    print(f"  Total acumulado: {total_vagas} vagas")

                    # Salva cookies após lote bem-sucedido
                    self._salvar_cookies()

                pagina_atual = ultima + 1
                self.salvar_checkpoint(pagina_atual, total_vagas)
                time.sleep(random.uniform(*self.DELAY_ENTRE_LOTES))

                if paginas_vazias_seguidas >= self.LIMITE_PAGINAS_VAZIAS:
                    print(f"\n{self.LIMITE_PAGINAS_VAZIAS} paginas vazias seguidas. Encerrando.")
                    break

        except KeyboardInterrupt:
            print("\nInterrompido manualmente.")
            self.salvar_checkpoint(pagina_atual, total_vagas)
            self.fechar_driver()
            print("Progresso salvo.")
            return

        except Exception as e:
            print(f"\nErro inesperado: {e}")
            self.salvar_checkpoint(pagina_atual, total_vagas)
            self.fechar_driver()
            raise

        # ── Finalização ───────────────────────────────────────────────
        print("\n" + "=" * 60)
        print(f"  CONCLUIDO: {self.nome_site.upper()}")
        print("=" * 60)
        print(f"  Total de vagas : {total_vagas}")
        print(f"  Arquivo        : {self.arquivo_csv}")

        if os.path.exists(self.arquivo_checkpoint):
            os.remove(self.arquivo_checkpoint)
            print("  Checkpoint removido.")

        self.fechar_driver()
        print("\nTudo pronto!")

    # ================================================================
    # AUXILIAR — pode ser sobrescrito por site
    # ================================================================

    def _aguardar_carregamento(self):
        """
        Aguarda o <body> ficar visível.
        Subclasses devem sobrescrever para esperar um elemento mais específico.
        """
        WebDriverWait(self.driver, 12).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )