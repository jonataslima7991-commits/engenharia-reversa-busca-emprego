"""
MÓDULO DE DEDUPLICAÇÃO INTELIGENTE DE VAGAS (3 CAMADAS)
========================================================
1. Camada 1: Normalização e Limpeza Canônica de URLs (remoção de tracking, session ids, utm)
2. Camada 2: Desduplicação Estrutural (Título normalizado + Empresa + Local)
3. Camada 3: Desduplicação Difusa / Fuzzy (Similaridade textual com SequenceMatcher)
"""

import re
import unicodedata
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from difflib import SequenceMatcher
import pandas as pd
from typing import Dict, Any, Tuple


class Deduplicador:
    """
    Executa a limpeza de links e remoção de duplicatas em múltiplos níveis.
    """

    @staticmethod
    def normalizar_url(url: str) -> str:
        """
        Remove parâmetros de tracking (utm, se, v, title, etc.) e normaliza a URL.
        Exemplo:
          https://www.adzuna.com.br/land/ad/1234?se=abc&title=xyz -> https://www.adzuna.com.br/land/ad/1234
        """
        if not isinstance(url, str) or not url.strip():
            return ""

        url = url.strip()

        # Tratamento especial para Adzuna (isolar o ID da vaga)
        if "adzuna.com.br/land/ad/" in url:
            match = re.search(r"adzuna\.com\.br/land/ad/(\d+)", url)
            if match:
                return f"https://www.adzuna.com.br/land/ad/{match.group(1)}"

        # Tratamento para Gupy (remover query strings irrelevantes)
        if "gupy.io" in url:
            parsed = urlparse(url)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))

        # Tratamento genérico para outras fontes: remove query params de tracking comuns
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            params_limpos = {
                k: v for k, v in params.items()
                if not (k.startswith("utm_") or k in {"se", "v", "title", "fbclid", "gclid", "ref"})
            }
            nova_query = urlencode(params_limpos, doseq=True)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), parsed.params, nova_query, ""))
        except Exception:
            return url

    @staticmethod
    def normalizar_texto(texto: str) -> str:
        """
        Remove acentuação, pontuação e ruídos para comparação estrita.
        Ex: 'Engenheiro (a) de Dados - Jr.' -> 'engenheiro de dados jr'
        """
        if not isinstance(texto, str) or not texto.strip():
            return ""

        # Remove acentos
        nfkd = unicodedata.normalize('NFKD', texto.lower())
        sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])

        # Remove parênteses como (a), (m/f), [remoto], etc.
        sem_parenteses = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", sem_acento)

        # Remove pontuações e caracteres especiais
        limpo = re.sub(r"[^\w\s]", " ", sem_parenteses)

        # Remove espaços múltiplos
        return re.sub(r"\s+", " ", limpo).strip()

    @classmethod
    def executar(cls, df: pd.DataFrame, similaridade_minima: float = 0.88) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Executa a deduplicação completa no DataFrame e retorna o DataFrame limpo
        juntamente com o relatório de métricas.
        """
        if df.empty:
            return df, {
                "total_inicial": 0, "total_final": 0, "removidas_total": 0,
                "removidas_url": 0, "removidas_estrutural": 0, "removidas_fuzzy": 0,
                "taxa_duplicatas_pct": 0.0
            }

        total_inicial = len(df)
        df = df.copy()

        # ── 1. Limpeza de URLs ─────────────────────────────────────────
        if "Link" in df.columns:
            df["Link_Normalizado"] = df["Link"].apply(cls.normalizar_url)
            df = df.drop_duplicates(subset=["Link_Normalizado"], keep="first")
        total_apos_url = len(df)

        # ── 2. Chave Estrutural ───────────────────────────────────────
        df["Titulo_Normalizado"] = df["Titulo"].apply(cls.normalizar_texto)
        
        empresa_series = df["Empresa"].astype(str).str.lower().str.strip() if "Empresa" in df.columns else pd.Series([""] * len(df), index=df.index)
        local_series = df["Localizacao"].astype(str).str.lower().str.strip() if "Localizacao" in df.columns else pd.Series([""] * len(df), index=df.index)
        
        df["Chave_Estrutural"] = (
            df["Titulo_Normalizado"].astype(str) + " | " +
            empresa_series + " | " +
            local_series
        )

        df = df.drop_duplicates(subset=["Chave_Estrutural"], keep="first")
        total_apos_estrutural = len(df)

        # ── 3. Deduplicação Difusa (Fuzzy Matching) ───────────────────
        indices_para_remover = set()
        titulos_unicos = df[["Titulo_Normalizado"]].drop_duplicates()
        titulos_lista = titulos_unicos["Titulo_Normalizado"].tolist()

        # Se houver até 5000 registros únicos, roda fuzzy matching
        if len(titulos_lista) <= 5000:
            for i in range(len(titulos_lista)):
                if i in indices_para_remover:
                    continue
                t1 = titulos_lista[i]
                if len(t1) < 5:
                    continue
                for j in range(i + 1, len(titulos_lista)):
                    if j in indices_para_remover:
                        continue
                    t2 = titulos_lista[j]
                    if abs(len(t1) - len(t2)) > 10:
                        continue
                    sim = SequenceMatcher(None, t1, t2).ratio()
                    if sim >= similaridade_minima:
                        indices_para_remover.add(j)

            titulos_validos = [t for idx, t in enumerate(titulos_lista) if idx not in indices_para_remover]
            df = df[df["Titulo_Normalizado"].isin(titulos_validos)]

        total_apos_fuzzy = len(df)
        total_removidas = total_inicial - total_apos_fuzzy

        # Remove colunas auxiliares antes de devolver
        df = df.drop(columns=["Titulo_Normalizado", "Chave_Estrutural"], errors="ignore")
        if "Link_Normalizado" in df.columns:
            df["Link"] = df["Link_Normalizado"]
            df = df.drop(columns=["Link_Normalizado"], errors="ignore")

        metricas = {
            "total_inicial": total_inicial,
            "total_apos_url": total_apos_url,
            "total_apos_estrutural": total_apos_estrutural,
            "total_final": total_apos_fuzzy,
            "removidas_total": total_removidas,
            "removidas_url": total_inicial - total_apos_url,
            "removidas_estrutural": total_apos_url - total_apos_estrutural,
            "removidas_fuzzy": total_apos_estrutural - total_apos_fuzzy,
            "taxa_duplicatas_pct": round((total_removidas / total_inicial * 100), 2) if total_inicial > 0 else 0.0
        }

        return df, metricas
