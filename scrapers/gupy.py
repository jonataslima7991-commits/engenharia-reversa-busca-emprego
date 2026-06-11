"""
SCRAPER — GUPY (portal.gupy.io)
================================
A Gupy é a maior plataforma de ATS (recrutamento) do Brasil.
Muitas empresas de tecnologia publicam vagas exclusivamente aqui.

DIFERENÇAS em relação à Adzuna:
  - SPA (Single Page Application) em React → o HTML é gerado pelo
    JavaScript após o carregamento, por isso precisamos de mais tempo
    de espera e de seletores CSS em vez de atributos customizados.
  - Paginação via query string: &page=N
  - Cada card de vaga tem o título em um <h2> dentro de um <article>

AVISO SOBRE SELETORES:
  A Gupy atualiza o frontend com frequência. Se a coleta parar de
  funcionar, inspecione o HTML com F12 e atualize os valores de
  _SEL_CARD, _SEL_TITULO e _SEL_LINK abaixo.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from scrapers.base import ScraperBase, _INDICADORES_BLOQUEIO


# ── Seletores CSS (ajuste aqui se o site mudar) ───────────────────────
_SEL_CARD   = "article[data-testid='job-card']"   # container de cada vaga
_SEL_TITULO = "h2"                                 # título dentro do card
_SEL_LINK   = "a[href]"                            # link dentro do card

# URL base para verificação de cookies
_URL_BASE = "https://portal.gupy.io"

# Padrões de bloqueio específicos da Gupy
_BLOQUEIO_GUPY = _INDICADORES_BLOQUEIO + [
    "faça login",
    "criar conta",
    "sign in",
    "nenhuma vaga",
    "no jobs",
]


class ScraperGupy(ScraperBase):
    """
    Coleta vagas de dados no portal.gupy.io.

    A Gupy renderiza o conteúdo via JavaScript, então:
      1. Aguardamos mais tempo (DELAY_CARREGAMENTO maior)
      2. Esperamos o elemento correto antes de extrair
      3. O scroll natural ajuda a garantir que todos os cards
         sejam renderizados (lazy loading)
    """

    # SPAs precisam de mais tempo para renderizar
    DELAY_CARREGAMENTO  = (10, 30)
    DELAY_ENTRE_LOTES   = (8, 15)
    TOTAL_VAGAS_ESPERADO = 15_000  # Gupy tem menos vagas que a Adzuna

    def __init__(self):
        super().__init__(nome_site="gupy")

    # ── URL ──────────────────────────────────────────────────────────

    def construir_url(self, pagina: int) -> str:
        return (
            f"{_URL_BASE}/job-search/term=Dados"
            f"&jobType=&state=&city=&page={pagina}"
        )

    # ── Aguardar renderização do React ───────────────────────────────

    def _aguardar_carregamento(self):
        """
        Aguarda até os cards de vaga aparecerem no DOM.
        O timeout é maior que na Adzuna porque o React precisa
        terminar de renderizar antes dos cards existirem.
        """
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, _SEL_CARD))
        )

    # ── Detecção de bloqueio ─────────────────────────────────────────

    def _esta_bloqueado(self) -> bool:
        try:
            fonte  = self.driver.page_source.lower()
            titulo = self.driver.title.lower()
            return any(ind in fonte or ind in titulo for ind in _BLOQUEIO_GUPY)
        except Exception:
            return False

    # ── Extração ─────────────────────────────────────────────────────

    def extrair_vagas_da_pagina(self) -> list[dict]:
        """
        Extrai título e link de cada card de vaga.

        Fluxo:
          1. Localiza todos os <article data-testid='job-card'>
          2. Dentro de cada card, pega o <h2> (título) e o <a> (link)
          3. Monta o link absoluto se o href for relativo
        """
        vagas = []

        try:
            cards = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, _SEL_CARD))
            )
        except TimeoutException:
            cards = self.driver.find_elements(By.CSS_SELECTOR, _SEL_CARD)

        for card in cards:
            try:
                # Título — primeiro <h2> dentro do card
                titulo_el = card.find_element(By.CSS_SELECTOR, _SEL_TITULO)
                titulo = titulo_el.text.strip()

                # Link — primeiro <a> dentro do card
                link_el = card.find_element(By.CSS_SELECTOR, _SEL_LINK)
                link = link_el.get_attribute("href") or ""

                # Garante URL absoluta
                if link.startswith("/"):
                    link = _URL_BASE + link

                if titulo and link:
                    vagas.append({"Titulo": titulo, "Link": link})

            except Exception:
                # Card sem título ou link — ignora sem interromper o loop
                continue

        return vagas