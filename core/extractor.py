"""
MÓDULO DE EXTRAÇÃO DE TECH STACK E PARSER SALARIAL
===================================================
1. Extração de palavras-chave e ferramentas de tecnologia no título / descrição
2. Normalização e parsing de faixas salariais declaradas
"""

import re
import pandas as pd
from typing import List, Dict, Any, Optional
from config import SKILLS_MAP


class ExtratorSkillsSalario:
    """
    Identifica tecnologias demandadas e realiza o parsing numérico de salários.
    """

    @staticmethod
    def extrair_skills(texto: str) -> List[str]:
        """
        Retorna uma lista de tecnologias e habilidades identificadas no texto.
        Ex: 'Engenheiro de Dados Python AWS SQL' -> ['Python', 'SQL', 'AWS']
        """
        if not isinstance(texto, str) or not texto.strip():
            return []

        t = texto.lower()
        skills_encontradas = []

        for skill_nome, regexes in SKILLS_MAP.items():
            for regex in regexes:
                if re.search(regex, t, re.IGNORECASE):
                    skills_encontradas.append(skill_nome)
                    break

        return skills_encontradas

    @staticmethod
    def parser_salario(texto: str) -> Dict[str, Optional[float]]:
        """
        Identifica valores salariais em reais.
        Exemplos suportados:
          - 'R$ 5.000' -> min: 5000, max: 5000, medio: 5000
          - 'R$ 4.500 a R$ 7.000' -> min: 4500, max: 7000, medio: 5750
          - '6k - 9k' -> min: 6000, max: 9000, medio: 7500
        """
        resultado = {
            "salario_min": None,
            "salario_max": None,
            "salario_medio": None,
            "tem_salario": False,
        }

        if not isinstance(texto, str) or not texto.strip():
            return resultado

        # 1. Padrão k (ex: 6k, 8.5k)
        padrao_k = re.findall(r"(\d+(?:[\.,]\d+)?)\s*k\b", texto, re.IGNORECASE)
        if padrao_k:
            valores = [float(v.replace(",", ".")) * 1000 for v in padrao_k]
            if valores:
                resultado["salario_min"] = min(valores)
                resultado["salario_max"] = max(valores)
                resultado["salario_medio"] = sum(valores) / len(valores)
                resultado["tem_salario"] = True
                return resultado

        # 2. Padrão R$ com números (ex: R$ 5.500,00 ou 5000)
        padrao_moeda = re.findall(r"R\$\s*([\d\.,]+)", texto, re.IGNORECASE)
        if not padrao_moeda:
            padrao_moeda = re.findall(r"\b(\d{1,2}\.\d{3}(?:,\d{2})?)\b", texto)

        valores_limpos = []
        for val in padrao_moeda:
            v_str = val.replace(".", "").replace(",", ".")
            try:
                v_float = float(v_str)
                if 800 <= v_float <= 60000:
                    valores_limpos.append(v_float)
            except ValueError:
                continue

        if valores_limpos:
            resultado["salario_min"] = min(valores_limpos)
            resultado["salario_max"] = max(valores_limpos)
            resultado["salario_medio"] = sum(valores_limpos) / len(valores_limpos)
            resultado["tem_salario"] = True

        return resultado

    @classmethod
    def aplicar(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica extração de skills e parsing de salários ao DataFrame."""
        if df.empty:
            return df

        df = df.copy()

        # Extração de skills no título + descrição com Series segura
        desc_col = df["Descricao"].astype(str) if "Descricao" in df.columns else pd.Series([""] * len(df), index=df.index)
        texto_completo = df["Titulo"].astype(str) + " " + desc_col

        df["Skills"] = texto_completo.apply(cls.extrair_skills)
        df["Skills_Str"] = df["Skills"].apply(lambda s: ", ".join(s) if s else "Não especificado")

        # Parsing de salário
        salario_col = df["Salario"].astype(str) if "Salario" in df.columns else pd.Series([""] * len(df), index=df.index)
        parsed_salarios = [
            cls.parser_salario(f"{t} {s}") 
            for t, s in zip(df["Titulo"], salario_col)
        ]

        df["Salario_Min"] = [p["salario_min"] for p in parsed_salarios]
        df["Salario_Max"] = [p["salario_max"] for p in parsed_salarios]
        df["Salario_Medio"] = [p["salario_medio"] for p in parsed_salarios]
        df["Tem_Salario_Declarado"] = [p["tem_salario"] for p in parsed_salarios]

        return df
