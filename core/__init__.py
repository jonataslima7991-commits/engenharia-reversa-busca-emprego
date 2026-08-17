"""
Módulos centrais de processamento, desduplicação, classificação e extração.
"""
from core.deduplication import Deduplicador
from core.classifier import Classificador
from core.extractor import ExtratorSkillsSalario
from core.pipeline import PipelineDados, executar_pipeline

__all__ = [
    "Deduplicador",
    "Classificador",
    "ExtratorSkillsSalario",
    "PipelineDados",
    "executar_pipeline",
]
