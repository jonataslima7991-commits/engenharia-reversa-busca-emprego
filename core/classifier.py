"""
MÓDULO DE CLASSIFICAÇÃO MULTIDIMENSIONAL DE VAGAS
=================================================
Classifica cada oportunidade em múltiplos eixos:
1. Área de Atuação (Engenharia, Ciência, Análise/BI, IA/ML, Governança, Bolsas)
2. Nível de Senioridade (Estágio, Júnior, Pleno, Sênior, Especialista, Liderança)
3. Modalidade de Trabalho (Remoto, Híbrido, Presencial)
4. Tipo Macro de Oportunidade (Bolsa Acadêmica, Vaga Corporativa, Estágio)
"""

import re
import pandas as pd
from config import PERFIS_DADOS, SENIORIDADE_MAP, MODALIDADE_MAP


class Classificador:
    """
    Classificador baseado em regras semânticas e expressões regulares refinadas.
    """

    @staticmethod
    def classificar_area(titulo: str) -> str:
        """Determina a sub-área de dados ou categoria acadêmica."""
        if not isinstance(titulo, str):
            return "Outros"

        t = titulo.lower()

        # Verifica na ordem configurada (Bolsas primeiro para evitar falsos positivos)
        for area, regexes in PERFIS_DADOS.items():
            for padrao in regexes:
                if re.search(padrao, t, re.IGNORECASE):
                    return area

        # Fallbacks genéricos
        if any(p in t for p in ["analista", "bi", "analytics", "dashboard", "relat[oó]rios"]):
            return "Análise de Dados / BI"
        if any(p in t for p in ["dados", "data"]):
            return "Geral de Dados"

        return "Outros"

    @staticmethod
    def classificar_senioridade(titulo: str) -> str:
        """Determina o nível de senioridade da oportunidade."""
        if not isinstance(titulo, str):
            return "Não Especificado"

        t = titulo.lower()

        # Primeiro verifica se é bolsa/acadêmico
        if any(p in t for p in ["bolsista", "bolsa", "graduando", "mestrado", "doutorado", "fapesp", "cnpq"]):
            return "Pesquisa / Acadêmica"

        for senioridade, regexes in SENIORIDADE_MAP.items():
            for padrao in regexes:
                if re.search(padrao, t, re.IGNORECASE):
                    return senioridade

        return "Não Especificado"

    @staticmethod
    def classificar_modalidade(texto: str, campo_modalidade: str = "") -> str:
        """Determina se a oportunidade é Remota, Híbrida ou Presencial."""
        combinado = f"{texto} {campo_modalidade}".lower()

        for modalidade, regexes in MODALIDADE_MAP.items():
            for padrao in regexes:
                if re.search(padrao, combinado, re.IGNORECASE):
                    return modalidade

        return "Não Informado"

    @staticmethod
    def classificar_tipo_macro(area: str, senioridade: str) -> str:
        """Classifica em macro-categorias para o estudo acadêmico (Bolsas vs Efetivas vs Estágios)."""
        if area == "Bolsas de Pesquisa" or senioridade == "Pesquisa / Acadêmica":
            return "Bolsa de Pesquisa / Acadêmica"
        if senioridade == "Estágio / Trainee":
            return "Estágio Corporativo"
        return "Vaga Efetiva CLT/PJ"

    @classmethod
    def aplicar(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todas as classificações às colunas do DataFrame."""
        if df.empty:
            return df

        df = df.copy()
        
        # Colunas com tratamento seguro de Series
        modalidade_col = df["Modalidade"].astype(str) if "Modalidade" in df.columns else pd.Series([""] * len(df), index=df.index)
        local_col = df["Localizacao"].astype(str) if "Localizacao" in df.columns else pd.Series([""] * len(df), index=df.index)
        texto_busca = df["Titulo"].astype(str) + " " + local_col

        df["Area_Atuacao"] = df["Titulo"].apply(cls.classificar_area)
        df["Senioridade"] = df["Titulo"].apply(cls.classificar_senioridade)
        
        df["Modalidade_Trabalho"] = [
            cls.classificar_modalidade(t, m) 
            for t, m in zip(texto_busca, modalidade_col)
        ]
        
        df["Tipo_Macro"] = [
            cls.classificar_tipo_macro(a, s) 
            for a, s in zip(df["Area_Atuacao"], df["Senioridade"])
        ]

        # Mantém coluna Categoria legada para compatibilidade com versões anteriores
        df["Categoria"] = df["Area_Atuacao"]

        return df
