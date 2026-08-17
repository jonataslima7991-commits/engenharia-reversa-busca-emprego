# Engenharia Reversa da Busca de Emprego

> Uma análise quantitativa do mercado de trabalho em Ciência de Dados no Brasil —
> desmascarando vagas, bolsas e assimetrias de informação.

Projeto desenvolvido para a **2ª Amostra Acadêmica da Fatec Santana de Parnaíba**,
curso de Ciência de Dados.

**Autores:** Jonatas Oliveira de Lima e Guilherme Soares Santos

---

## 🎯 Sobre o Projeto

O mercado de trabalho em Ciência de Dados no Brasil é marcado por uma profunda
**opacidade estrutural**: cargos analíticos são anunciados sob títulos genéricos e
a forma como o candidato pesquisa determina as oportunidades que aparecem para ele.

Este projeto aplica **engenharia reversa** sobre plataformas de vagas brasileiras para:
1. Mapear quantitativamente o mercado de dados e sua distribuição real.
2. Separar **bolsas acadêmicas** (que inflacionam os dados) de **vagas corporativas reais**.
3. Revelar a disparidade salarial e o nível de transparência das empresas.
4. Identificar as **habilidades e tecnologias (Tech Stack)** mais exigidas pelas empresas.

---

## 📊 Principais Descobertas (base: 9.360 vagas · Adzuna · Mar/2026)

| Categoria | Qtd. | % |
|---|---|---|
| Bolsas de Mestrado / Doutorado | 3.137 | 33,51% |
| Vagas Efetivas CLT/PJ | 2.655 | 28,37% |
| Bolsas de Pesquisa | 2.342 | 25,02% |
| Estágios Corporativos | 1.226 | 13,10% |

- Buscar por **"Dados"** abre **6,3× mais portas** do que buscar por "Cientista de Dados"
- **93,2% das vagas** não divulgam remuneração (assimetria de informação — Akerlof, 1970)
- Bolsas acadêmicas correspondem a **58,53%** do total de anúncios

### Remuneração média por cargo (vagas com salário declarado)

| Cargo | Salário Médio |
|---|---|
| Especialista em Dados | R$ 9.150 |
| Cientista de Dados | R$ 7.000 |
| Engenheiro de Dados | R$ 5.500 |
| Analista de Dados | R$ 3.561 |

---

## 🏗️ Estrutura Modular do Projeto

O projeto foi reestruturado de forma modular para facilitar edições, expansão para novas plataformas e demonstração em apresentações acadêmicas e técnicas:

```
engenharia-reversa-busca-emprego/
│
├── config.py                  # Configurações globais (skills, regex de áreas, senioridade, caminhos)
│
├── core/                      # Módulos centrais de processamento e dados (Data Science)
│   ├── __init__.py
│   ├── deduplication.py       # Deduplicação inteligente em 3 camadas (URL, Estrutural, Fuzzy)
│   ├── classifier.py          # Classificação multidimensional (Área, Nível, Modalidade)
│   ├── extractor.py           # Mineração de Tech Stack (Python, SQL, AWS...) e Parser Salarial
│   └── pipeline.py            # Orquestrador de ETL e geração de JSONs dos dashboards
│
├── scrapers/                  # Coletores de dados orientados a objetos
│   ├── __init__.py
│   ├── base.py                # ScraperBase: camuflagem anti-bloqueio, stealth CDP, checkpoints
│   ├── adzuna.py              # Scraper Adzuna enriquecido
│   └── gupy.py                # Scraper Gupy enriquecido
│
├── index.html                 # Dashboard Analítico Executivo (KPIs, Gráficos Chart.js, D3 Map)
├── oportunidades.html         # Feed Interativo com filtros rápidos, busca e exportação CSV/JSON
│
├── main.py                    # CLI unificada (coleta, processamento, status, all)
├── gerar_dashboard.py         # Atalho para reprocessar datasets e atualizar dashboards
├── teste_estrutura.py         # Suíte de verificação arquitetural e testes unitários
├── analise_vagas.ipynb        # Jupyter Notebook para análise exploratória
│
├── vagas_adzuna.csv           # Dados brutos coletados — Adzuna
├── vagas_gupy.csv             # Dados brutos coletados — Gupy
├── live_data.json             # Alimenta os gráficos e KPIs de index.html
├── oportunidades_data.json    # Alimenta o feed de oportunidades.html
└── vagas_consolidadas.csv     # Dataset limpo, sem duplicatas e enriquecido
```

---

## 🚀 Como Executar

### 1. Instalar Pré-requisitos

- Python 3.10+
- Google Chrome instalado

```bash
pip install selenium undetected-chromedriver pandas
```

---

### 2. Comandos da CLI (`main.py`)

A interface de linha de comando oferece controle total sobre as etapas:

```bash
# 📌 Ver status atual dos dados coletados e artefatos
python main.py status

# ⚙️ Executar apenas o Pipeline de Tratamento, Deduplicação e Atualização dos Dashboards
python main.py process

# 🌐 Executar a coleta de vagas de todas as fontes
python main.py

# 🔍 Executar scraper de uma fonte específica
python main.py adzuna
python main.py gupy

# 🚀 Executar coleta completa + processamento de ponta a ponta
python main.py all
```

---

### 3. Validação Arquitetural e Testes

Para demonstrar a integridade do código e dos algoritmos em uma apresentação:

```bash
python teste_estrutura.py
```

---

### 4. Visualizar os Dashboards

Basta abrir os arquivos HTML no seu navegador:

| Página | Descrição |
|---|---|
| [`index.html`](file:///c:/Users/Irmãos/Desktop/engenharia-reversa-busca-emprego-main/index.html) | Dashboard acadêmico: KPIs, gráficos analíticos, mapa de vagas e métricas de desduplicação |
| [`oportunidades.html`](file:///c:/Users/Irmãos/Desktop/engenharia-reversa-busca-emprego-main/oportunidades.html) | Feed interativo de vagas com filtros por Área, Nível, Modalidade, Tech Stack e exportador CSV/JSON |

---

## 🛡️ Mecanismo de Deduplicação em 3 Camadas

O módulo [`core/deduplication.py`](file:///c:/Users/Irmãos/Desktop/engenharia-reversa-busca-emprego-main/core/deduplication.py) implementa um pipeline rigoroso de qualidade de dados:

1. **Camada 1 (URL Canônica):** Remove parâmetros de rastreamento de campanhas (`utm_*`, tokens de sessão Adzuna `se`, `v`, etc.), isolando a URL real da vaga.
2. **Camada 2 (Chave Estrutural):** Normaliza títulos (remoção de ruídos ortográficos, acentos, caracteres como "(a)" ou "Jr/Pl/Sr") combinados com Empresa e Localização.
3. **Camada 3 (Similaridade Difusa / Fuzzy Matching):** Utiliza o algoritmo `SequenceMatcher` para identificar repostagens com pequenas variações textuais.

---

## 🧩 Adicionar um Novo Scraper

1. Crie `scrapers/novosite.py` herdando `ScraperBase`:
```python
from scrapers.base import ScraperBase

class ScraperNovoSite(ScraperBase):
    def __init__(self):
        super().__init__(nome_site="novosite")

    def construir_url(self, pagina: int) -> str:
        return f"https://novosite.com.br/vagas?q=dados&p={pagina}"

    def extrair_vagas_da_pagina(self) -> list[dict]:
        # retorna lista com Titulo, Link, Empresa, Localizacao, etc.
        ...
```

2. Registre no dicionário `SCRAPERS` em [`main.py`](file:///c:/Users/Irmãos/Desktop/engenharia-reversa-busca-emprego-main/main.py):
```python
from scrapers.novosite import ScraperNovoSite

SCRAPERS = {
    "adzuna":   ScraperAdzuna,
    "gupy":     ScraperGupy,
    "novosite": ScraperNovoSite,
}
```

---

## 📚 Referências Bibliográficas

- Akerlof, G. A. (1970). The Market for "Lemons": Quality Uncertainty and the Market Mechanism. *The Quarterly Journal of Economics*, 84(3).
- Brasscom (2025). *Relatório de Perspectivas do Mercado de Trabalho do Macrossetor TIC 2025*.
- Chapman et al. (2000). *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS.
- McKinney, W. (2023). *Python para análise de dados*. Novatec.
- Mitchell, R. (2018). *Web Scraping with Python*. O'Reilly Media.
- MTE (2023). *Classificação Brasileira de Ocupações (CBO)*.

---

## 👥 Autores

| Nome | E-mail |
|---|---|
| **Guilherme Soares Santos** | contatogui14@gmail.com |
| **Jonatas Oliveira de Lima** | jonatas.lima7991@gmail.com |

**Fatec Santana de Parnaíba — Curso Superior de Ciência de Dados — 2026**