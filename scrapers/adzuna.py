"""
SCRAPER — ADZUNA.COM.BR
=======================
Implementa a coleta específica da Adzuna.
Herda todo o fluxo de ScraperBase e define apenas:
  - construir_url()             → URL paginada da Adzuna
  - extrair_vagas_da_pagina()   → seletor data-js='jobLink'
  - _aguardar_carregamento()    → espera pelo link de vaga
  - _esta_bloqueado()           → padrões específicos da Adzuna
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from scrapers.base import ScraperBase, _INDICADORES_BLOQUEIO


# Padrões que indicam bloqueio/redirecionamento na Adzuna especificamente
_BLOQUEIO_ADZUNA = _INDICADORES_BLOQUEIO + [
    "página não encontrada",
    "nenhuma vaga encontrada",
    "no jobs found",
]


class ScraperAdzuna(ScraperBase):

    def __init__(self):
        super().__init__(nome_site="adzuna")

    # ── URL ──────────────────────────────────────────────────────────

    def construir_url(self, pagina: int) -> str:
        return f"https://www.adzuna.com.br/search?loc=109016&q=Dados&p={pagina}"

    # ── Aguardar elemento específico ─────────────────────────────────

    def _aguardar_carregamento(self):
        WebDriverWait(self.driver, 12).until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[@data-js='jobLink']")
            )
        )

    # ── Detecção de bloqueio ─────────────────────────────────────────

    def _esta_bloqueado(self) -> bool:
        """Verifica bloqueios genéricos + padrões específicos da Adzuna."""
        try:
            fonte  = self.driver.page_source.lower()
            titulo = self.driver.title.lower()
            return any(ind in fonte or ind in titulo for ind in _BLOQUEIO_ADZUNA)
        except Exception:
            return False

    # ── Extração ─────────────────────────────────────────────────────

    def extrair_vagas_da_pagina(self) -> list[dict]:
        """
        A Adzuna marca cada link de vaga com data-js='jobLink'.
        Esse atributo é mais estável do que classes CSS.
        """
        vagas = []

        try:
            elementos = WebDriverWait(self.driver, 8).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//a[@data-js='jobLink']")
                )
            )
        except TimeoutException:
            elementos = self.driver.find_elements(By.XPATH, "//a[@data-js='jobLink']")

        for el in elementos:
            titulo = el.text.strip()
            link   = el.get_attribute("href")
            if titulo and link:
                vagas.append({"Titulo": titulo, "Link": link})

        return vagas