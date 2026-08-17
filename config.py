"""
CONFIGURAÇÕES GLOBAIS DO PROJETO
=================================
Centraliza caminhos de arquivos, termos de busca, dicionários de classificação
e regras de negócio para facilitar manutenção e apresentações.
"""

from pathlib import Path

# ── DIRETÓRIOS E ARQUIVOS ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# Dados Brutos e Processados
DIR_DATA = BASE_DIR / "data"
DIR_RAW_DATA = DIR_DATA / "raw"
DIR_PROCESSED_DATA = DIR_DATA / "processed"
DIR_LOGS = BASE_DIR / "logs"

# Arquivos CSV de entrada (com fallback na raiz para compatibilidade)
ARQUIVOS_FONTES = {
    "adzuna": [DIR_RAW_DATA / "vagas_adzuna.csv", BASE_DIR / "vagas_adzuna.csv"],
    "gupy": [DIR_RAW_DATA / "vagas_gupy.csv", BASE_DIR / "vagas_gupy.csv"],
    "legado": [BASE_DIR / "vagas_completas.csv"],
}

# Arquivos de saída para o Frontend
ARQUIVO_LIVE_JSON = BASE_DIR / "live_data.json"
ARQUIVO_OPORTUNIDADES_JSON = BASE_DIR / "oportunidades_data.json"
ARQUIVO_CONSOLIDADO_CSV = BASE_DIR / "vagas_consolidadas.csv"

# ── DICIONÁRIO DE TECH STACK & SKILLS ──────────────────────────────────
# Mapeia nome canônico para lista de variações / regex
SKILLS_MAP = {
    "Python": [r"\bpython\b", r"\bpy\b"],
    "SQL": [r"\bsql\b", r"\bmysql\b", r"\bpostgres\b", r"\bpostgresql\b", r"\bsql server\b", r"\boracle\b"],
    "R": [r"\br\b", r"\blinguagem r\b", r"\brstudio\b"],
    "Power BI": [r"\bpower\s*bi\b", r"\bpbi\b"],
    "Tableau": [r"\btableau\b"],
    "Excel": [r"\bexcel\b", r"\bplanilhas\b"],
    "AWS": [r"\baws\b", r"\bamazon web services\b", r"\bredshift\b", r"\bs3\b"],
    "Azure": [r"\bazure\b", r"\bsynapse\b"],
    "GCP": [r"\bgcp\b", r"\bgoogle cloud\b", r"\bbigquery\b"],
    "Spark": [r"\bspark\b", r"\bpyspark\b"],
    "Databricks": [r"\bdatabricks\b"],
    "Airflow": [r"\bairflow\b"],
    "dbt": [r"\bdbt\b"],
    "Kafka": [r"\bkafka\b"],
    "Docker / K8s": [r"\bdocker\b", r"\bkubernetes\b", r"\bk8s\b"],
    "Machine Learning": [r"\bmachine learning\b", r"\bml\b", r"\baprendizado de m[aá]quina\b", r"\bdeep learning\b", r"\bia\b", r"\bai\b"],
    "NLP / LLM": [r"\bnlp\b", r"\bpln\b", r"\bllm\b", r"\bia generativa\b", r"\bgenai\b"],
    "NoSQL": [r"\bnosql\b", r"\bmongodb\b", r"\bcassandra\b", r"\bdynamodb\b"],
    "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "Estatística": [r"\bestat[ií]stica\b", r"\bestat[ií]stico\b", r"\bmodelagem\b"],
}

# ── DEFINIÇÃO DE PERFIS / ÁREAS DE DADOS ──────────────────────────────
PERFIS_DADOS = {
    "Bolsas de Pesquisa": [
        r"\bbolsista\b", r"\bbolsa\b", r"\bgraduando\b", r"\bmestrado\b", 
        r"\bdoutorado\b", r"\bp[oó]s-doutorado\b", r"\bfapesp\b", r"\bcnpq\b", r"\bcapes\b"
    ],
    "Engenharia de Dados": [
        r"\bengenheiro.*dados\b", r"\bdata engineer\b", r"\beng.*dados\b",
        r"\betl\b", r"\bpipeline.*dados\b", r"\bdata ops\b"
    ],
    "Ciência de Dados": [
        r"\bcientista.*dados\b", r"\bdata scientist\b", r"\bdecision scientist\b"
    ],
    "Análise de Dados / BI": [
        r"\banalista.*dados\b", r"\bdata analyst\b", r"\banalista.*bi\b",
        r"\bbusiness intelligence\b", r"\banalytics\b", r"\banalista.*analytics\b",
        r"\banalista.*neg[oó]cios.*dados\b"
    ],
    "IA & Machine Learning": [
        r"\bml engineer\b", r"\bengenheiro.*ia\b", r"\bengenheiro.*ml\b",
        r"\bprompt engineer\b", r"\bcomputa[cç][aã]o visual\b", r"\bpesquisador.*ia\b"
    ],
    "Governança & Arquitetura": [
        r"\barquiteto.*dados\b", r"\bdata architect\b", r"\bgovernan[cç]a.*dados\b",
        r"\bdata governance\b", r"\bdba\b", r"\badministrador.*banco.*dados\b"
    ],
    "Especialista / Lead": [
        r"\bespecialista.*dados\b", r"\bdata lead\b", r"\btech lead.*dados\b", r"\bdata product owner\b"
    ]
}

# ── SENIORIDADE ────────────────────────────────────────────────────────
SENIORIDADE_MAP = {
    "Estágio / Trainee": [r"\best[aá]gio\b", r"\bestagi[aá]ri[oa]\b", r"\btrainee\b", r"\baprendiz\b", r"\bintern\b"],
    "Júnior": [r"\bj[uú]nior\b", r"\bjr\b", r"\bjr\.", r"\bentry level\b", r"\bn[ií]vel i\b"],
    "Pleno": [r"\bpleno\b", r"\bpl\b", r"\bpl\.", r"\bmid level\b", r"\bn[ií]vel ii\b"],
    "Sênior": [r"\bs[eê]nior\b", r"\bsr\b", r"\bsr\.", r"\bsenior\b", r"\bn[ií]vel iii\b"],
    "Especialista": [r"\bespecialista\b", r"\bexpert\b", r"\blead\b", r"\bprincipal\b", r"\bconsultor\b"],
    "Liderança": [r"\bgerente\b", r"\bcoordenador\b", r"\bcoordenadora\b", r"\bdiretor\b", r"\bdiretora\b", r"\bhead\b", r"\bl[ií]der\b", r"\bmanager\b"]
}

# ── MODELO DE TRABALHO ────────────────────────────────────────────────
MODALIDADE_MAP = {
    "Remoto": [r"\bremoto\b", r"\bhome office\b", r"\b100% remoto\b", r"\bteletrabalho\b", r"\banywhere\b", r"\btrabalho remoto\b"],
    "Híbrido": [r"\bh[ií]brido\b", r"\bhybrid\b", r"\bmisto\b"],
    "Presencial": [r"\bpresencial\b", r"\bon-site\b", r"\bescrit[oó]rio\b", r"\balocado\b"]
}
