# 🔍 Engenharia Reversa da Busca de Emprego

> Uma análise quantitativa do mercado de trabalho em Ciência de Dados no Brasil — desmascarando vagas, bolsas e assimetrias de informação.

Projeto desenvolvido para a **2ª Amostra Acadêmica da Faculdade de Tecnologia de Santana de Parnaíba (Fatec)**, curso de Ciência de Dados.

**Autores:** Jonatas Oliveira de Lima e Guilherme Soares Santos

---

## 📌 Sobre o Projeto

O mercado de trabalho em Ciência de Dados no Brasil é marcado por uma profunda **opacidade estrutural**: cargos que exigem habilidades analíticas avançadas são frequentemente anunciados sob títulos genéricos, e a forma como o candidato pesquisa determina drasticamente as oportunidades que aparecem para ele.

Este projeto aplica **engenharia reversa** sobre o banco de dados de vagas da plataforma [Adzuna.com.br](https://www.adzuna.com.br) — maior agregador de vagas do mundo — para mapear quantitativamente o mercado de dados brasileiro, separar ruídos (bolsas acadêmicas) das oportunidades reais e revelar os padrões de remuneração por cargo.

---

## 🔑 Principais Descobertas

| Categoria | Qtd. | % |
|---|---|---|
| Bolsas de Mestrado / Doutorado | 3.137 | 33,51% |
| Vagas Efetivas CLT/PJ | 2.655 | 28,37% |
| Bolsas de Pesquisa | 2.342 | 25,02% |
| Estágios Corporativos | 1.226 | 13,10% |

- 🔎 Buscar por **"Dados"** abre **6,3x mais portas** no mercado corporativo do que buscar por "Cientista de Dados"
- 💰 **93,2% das vagas** não divulgam remuneração — confirmando a assimetria de informação de Akerlof (1970)
- 🎓 Bolsas de Mestrado/Doutorado/Pesquisa correspondem a **58,53%** do total de vagas encontradas sob o termo "Dados"

### Remuneração Média por Cargo (vagas com salário exposto)

| Cargo | Salário Médio |
|---|---|
| Especialista em Dados | R$ 9.150 |
| Cientista de Dados | R$ 7.000 |
| Engenheiro de Dados | R$ 5.500 |
| Analista de Dados | R$ 3.561 |

---

## 🛠️ Tecnologias Utilizadas

- **Python** — linguagem principal
- **Selenium + undetected_chromedriver** — web scraping com simulação de navegação humana
- **Pandas** — limpeza, transformação e análise exploratória dos dados
- **Expressões Regulares (re)** — categorização e extração de salários
- **Power BI** — dashboard interativo final
- **HTML + JavaScript** — dashboard de validação gerado via IA

---

## 🔄 Pipeline do Projeto

```
Coleta (Selenium) → CSV bruto → Limpeza (Pandas) → Categorização (Regex) → Análise → Dashboard (Power BI)
```

**Metodologia:** [CRISP-DM](https://en.wikipedia.org/wiki/Cross-industry_standard_process_for_data_mining) — Cross-Industry Standard Process for Data Mining

1. **Entendimento do Negócio** — mapeamento do problema de mascaramento de vagas
2. **Coleta de Dados** — scraping automatizado da Adzuna (centenas de páginas)
3. **Preparação dos Dados** — remoção de duplicatas, normalização, categorização
4. **Análise e Visualização** — frequências, médias salariais, dashboard interativo

---

## 📁 Estrutura do Repositório

```
📦 engenharia-reversa-busca-emprego
 ┣ 📄 scraper.py               # Script de coleta com Selenium
 ┣ 📄 analise.py               # Limpeza e análise com Pandas
 ┣ 📄 dashboard.html           # Dashboard interativo em HTML
 ┣ 📊 dados/
 ┃ ┗ 📄 vagas_raw.csv          # Base de dados coletada
 ┣ 📄 requirements.txt         # Dependências do projeto
 ┗ 📄 README.md
```

---

## ▶️ Como Executar

### Pré-requisitos

- Python 3.10+
- Google Chrome instalado
- Instalar as dependências:

```bash
pip install -r requirements.txt
```

### Executar o scraper

```bash
python scraper.py
```

### Executar a análise

```bash
python analise.py
```

---

## 📦 Dependências

```
selenium
undetected-chromedriver
pandas
```

> Gere o `requirements.txt` com: `pip freeze > requirements.txt`

---

## 🌱 Alinhamento ao ODS 08

Este projeto contribui para o **Objetivo de Desenvolvimento Sustentável 08 da ONU** (Trabalho Decente e Crescimento Econômico), ao democratizar o acesso à informação sobre o mercado de trabalho, reduzindo a assimetria de oportunidades causada pela falta de padronização nas publicações de vagas digitais.

---

## 🔭 Trabalhos Futuros

- Automação do pipeline para monitoramento semanal
- Expansão do scraping para LinkedIn e Gupy
- Cruzamento geográfico com dados regionais do CAGED
- Análise de sazonalidade por período do ano

---

## 📚 Referências

- Akerlof, G. A. (1970). The Market for "Lemons". *The Quarterly Journal of Economics*, 84(3).
- Brasscom (2025). *Relatório de Perspectivas do Mercado de Trabalho do Macrossetor TIC 2025*.
- Chapman et al. (2000). *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS.
- McKinney, W. (2023). *Python para análise de dados*. Novatec.
- Mitchell, R. (2018). *Web Scraping with Python*. O'Reilly Media.
- MTE (2023). *Classificação Brasileira de Ocupações (CBO)*.

---

## 👥 Autores

| Nome | Contato |
|---|---|
| Guilherme Soares Santos | contatogui14@gmail.com |
| Jonatas Oliveira de Lima | jonatas.lima7991@gmail.com |

**Fatec Santana de Parnaíba — Ciência de Dados — 2026**
