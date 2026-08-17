"""
SCRAPER ENRIQUECIDO — ADZUNA (adzuna.com.br)
============================================
Extrai vagas de dados na Adzuna com campos enriquecidos:
  - Título da vaga
  - Link normalizado / canônico
  - Empresa anunciante
  - Localização (Cidade / Estado / Remoto)
  - Salário declarado (se houver)
  - Resumo / Snippet da vaga
"""

import re
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scrapers.base import ScraperBase, _INDICADORES_BLOQUEIO
from core.deduplication import Deduplicador


_BLOQUEIO_ADZUNA = _INDICADORES_BLOQUEIO + [
    "página não encontrada",
    "nenhuma vaga encontrada",
    "no jobs found",
]


class ScraperAdzuna(ScraperBase):
    """
    Coletor para a plataforma Adzuna Brasil.
    """

    def __init__(self, headless: bool = False):
        super().__init__(nome_site="adzuna", headless=headless)

    def construir_url(self, pagina: int) -> str:
        return f"https://www.adzuna.com.br/search?loc=109016&q=Dados&p={pagina}"

    def _aguardar_carregamento(self):
        WebDriverWait(self.driver, 14).until(
            EC.presence_of_element_located((By.XPATH, "//a[@data-js='jobLink'] | //article[contains(@class, 'ui-search-result')]"))
        )

    def _esta_bloqueado(self) -> bool:
        try:
            fonte = self.driver.page_source.lower()
            titulo = self.driver.title.lower()
            return any(ind in fonte or ind in titulo for ind in _BLOQUEIO_ADZUNA)
        except Exception:
            return False

    def extrair_vagas_da_pagina(self) -> List[Dict[str, str]]:
        """
        Extrai os dados estruturados de cada card de vaga na Adzuna.
        """
        vagas = []

        try:
            # Tenta pegar os cards completos de resultados
            cards = self.driver.find_elements(By.XPATH, "//article[contains(@class, 'ui-search-result')] | //div[contains(@class, 'ui-search-result')]")
        except Exception:
            cards = []

        # Se encontrou containers de cards, extrai dados ricos
        if cards:
            for card in cards:
                try:
                    # Link e Título
                    link_el = card.find_element(By.XPATH, ".//a[@data-js='jobLink'] | .//h2//a")
                    titulo = link_el.text.strip()
                    raw_link = link_el.get_attribute("href") or ""
                    link_canonica = Deduplicador.normalizar_url(raw_link)

                    # Empresa
                    empresa = "Confidencial"
                    try:
                        empresa_el = card.find_element(By.XPATH, ".//*[contains(@class, 'ui-company') or contains(@class, 'company')]")
                        empresa = empresa_el.text.strip()
                    except NoSuchElementException:
                        pass

                    # Localização
                    localizacao = "Brasil"
                    try:
                        loc_el = card.find_element(By.XPATH, ".//*[contains(@class, 'ui-location') or contains(@class, 'location')]")
                        localizacao = loc_el.text.strip()
                    except NoSuchElementException:
                        pass

                    # Salário
                    salario = ""
                    try:
                        sal_el = card.find_element(By.XPATH, ".//*[contains(@class, 'ui-salary') or contains(@class, 'salary')]")
                        salario = sal_el.text.strip()
                    except NoSuchElementException:
                        pass

                    # Descrição / Snippet
                    descricao = ""
                    try:
                        desc_el = card.find_element(By.XPATH, ".//*[contains(@class, 'ui-snippet') or contains(@class, 'snippet')]")
                        descricao = desc_el.text.strip()
                    except NoSuchElementException:
                        pass

                    if titulo and link_canonica:
                        vagas.append({
                            "Titulo": titulo,
                            "Link": link_canonica,
                            "Empresa": empresa,
                            "Localizacao": localizacao,
                            "Salario": salario,
                            "Descricao": descricao,
                            "Modalidade": "Remoto" if "remoto" in (localizacao + " " + titulo).lower() else "Não informado"
                        })
                except Exception:
                    continue

        # Fallback se a estrutura do card não tiver sido encontrada
        if not vagas:
            elementos = self.driver.find_elements(By.XPATH, "//a[@data-js='jobLink']")
            for el in elementos:
                try:
                    titulo = el.text.strip()
                    link = Deduplicador.normalizar_url(el.get_attribute("href") or "")
                    if titulo and link:
                        vagas.append({
                            "Titulo": titulo,
                            "Link": link,
                            "Empresa": "Confidencial",
                            "Localizacao": "Brasil",
                            "Salario": "",
                            "Descricao": "",
                            "Modalidade": "Remoto" if "remoto" in titulo.lower() else "Não informado"
                        })
                except Exception:
                    continue

        return vagas