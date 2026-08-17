"""
SCRAPER ENRIQUECIDO — GUPY (portal.gupy.io)
===========================================
Extrai oportunidades de dados publicadas no ecossistema Gupy com dados completos:
  - Título da vaga
  - Link normalizado
  - Nome da Empresa contratante
  - Modalidade (Remoto / Presencial / Híbrido)
  - Localização geográfica
  - Tipo de Contratação (Efetivo, Estágio, etc.)
"""

from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scrapers.base import ScraperBase, _INDICADORES_BLOQUEIO
from core.deduplication import Deduplicador


_SEL_CARD = "article[data-testid='job-card'], div[data-testid='job-card']"
_SEL_TITULO = "h2, h3"
_SEL_LINK = "a[href]"
_URL_BASE = "https://portal.gupy.io"

_BLOQUEIO_GUPY = _INDICADORES_BLOQUEIO + [
    "faça login",
    "criar conta",
    "sign in",
    "nenhuma vaga",
    "no jobs",
]


class ScraperGupy(ScraperBase):
    """
    Coletor para vagas de tecnologia no portal Gupy.
    """

    DELAY_CARREGAMENTO = (8, 20)
    DELAY_ENTRE_LOTES = (6, 12)
    TOTAL_VAGAS_ESPERADO = 20_000

    def __init__(self, headless: bool = False):
        super().__init__(nome_site="gupy", headless=headless)

    def construir_url(self, pagina: int) -> str:
        return (
            f"{_URL_BASE}/job-search/term=Dados"
            f"&jobType=&state=&city=&page={pagina}"
        )

    def _aguardar_carregamento(self):
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, _SEL_CARD))
        )

    def _esta_bloqueado(self) -> bool:
        try:
            fonte = self.driver.page_source.lower()
            titulo = self.driver.title.lower()
            return any(ind in fonte or ind in titulo for ind in _BLOQUEIO_GUPY)
        except Exception:
            return False

    def extrair_vagas_da_pagina(self) -> List[Dict[str, str]]:
        vagas = []

        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, _SEL_CARD)
        except Exception:
            cards = []

        for card in cards:
            try:
                # Título
                titulo_el = card.find_element(By.CSS_SELECTOR, _SEL_TITULO)
                titulo = titulo_el.text.strip()

                # Link
                link_el = card.find_element(By.CSS_SELECTOR, _SEL_LINK)
                raw_link = link_el.get_attribute("href") or ""
                if raw_link.startswith("/"):
                    raw_link = _URL_BASE + raw_link
                link = Deduplicador.normalizar_url(raw_link)

                # Texto completo do card para extração de atributos
                texto_card = card.text

                # Empresa
                empresa = "Confidencial"
                try:
                    # Gupy frequentemente coloca a empresa em parágrafos ou spans
                    p_elems = card.find_elements(By.TAG_NAME, "p")
                    if p_elems:
                        empresa = p_elems[0].text.strip()
                except Exception:
                    pass

                # Modalidade / Localização
                modalidade = "Não informado"
                if "remoto" in texto_card.lower():
                    modalidade = "Remoto"
                elif "híbrido" in texto_card.lower() or "hibrido" in texto_card.lower():
                    modalidade = "Híbrido"
                elif "presencial" in texto_card.lower():
                    modalidade = "Presencial"

                if titulo and link:
                    vagas.append({
                        "Titulo": titulo,
                        "Link": link,
                        "Empresa": empresa,
                        "Localizacao": "Brasil",
                        "Salario": "",
                        "Descricao": texto_card,
                        "Modalidade": modalidade
                    })
            except Exception:
                continue

        return vagas