# Engenharia Reversa da Busca de Emprego

> Uma análise quantitativa do mercado de trabalho em Ciência de Dados no Brasil —
> desmascarando vagas, bolsas e assimetrias de informação.

Projeto desenvolvido para a **2ª Amostra Acadêmica da Fatec Santana de Parnaíba**,
curso de Ciência de Dados.

**Autores:** Jonatas Oliveira de Lima e Guilherme Soares Santos

---

## Sobre o Projeto

O mercado de trabalho em Ciência de Dados no Brasil é marcado por uma profunda
**opacidade estrutural**: cargos analíticos são anunciados sob títulos genéricos e
a forma como o candidato pesquisa determina as oportunidades que aparecem para ele.

Este projeto aplica **engenharia reversa** sobre plataformas de vagas brasileiras para
mapear quantitativamente o mercado de dados, separar bolsas acadêmicas das oportunidades
reais e revelar padrões de remuneração por cargo.

---

## Principais Descobertas (base: 9.360 vagas · Adzuna · Mar/2026)

| Categoria | Qtd. | % |
|---|---|---|
| Bolsas de Mestrado / Doutorado | 3.137 | 33,51% |
| Vagas Efetivas CLT/PJ | 2.655 | 28,37% |
| Bolsas de Pesquisa | 2.342 | 25,02% |
| Estágios Corporativos | 1.226 | 13,10% |

- Buscar por **"Dados"** abre **6,3× mais portas** do que buscar por "Cientista de Dados"
- **93,2% das vagas** não divulgam remuneração (assimetria de informação — Akerlof, 1970)
- Bolsas acadêmicas correspondem a **58,53%** do total

### Remuneração média por cargo (vagas com salário declarado)

| Cargo | Salário Médio |
|---|---|
| Especialista em Dados | R$ 9.150 |
| Cientista de Dados | R$ 7.000 |
| Engenheiro de Dados | R$ 5.500 |
| Analista de Dados | R$ 3.561 |

---

## Estrutura do Projeto

```
Amostra Acadêmica/
│
├── scrapers/                  # Pacote de coletores (um por site)
│   ├── __init__.py
│   ├── base.py                # ScraperBase: lógica comum, anti-detecção, retry
│   ├── adzuna.py              # ScraperAdzuna
│   └── gupy.py                # ScraperGupy
│
├── main.py                    # Ponto de entrada — roda um ou todos os scrapers
├── gerar_dashboard.py         # Lê os CSVs e gera os JSONs para os dashboards
│
├── index.html                 # Dashboard de análise (TCC)
├── oportunidades.html         # Feed semanal de vagas com filtros
│
├── analise_vagas.ipynb        # Notebook de limpeza e análise exploratória
│
├── executar_coleta.bat        # Pipeline completo: coleta + dashboard (agendável)
├── agendar_coleta.ps1         # Registra a tarefa no Windows Task Scheduler
│
├── vagas_adzuna.csv           # Dados coletados — Adzuna
├── vagas_gupy.csv             # Dados coletados — Gupy
├── live_data.json             # Gerado automaticamente — alimenta index.html
├── oportunidades_data.json    # Gerado automaticamente — alimenta oportunidades.html
│
└── logs/                      # Log de cada execução agendada
    └── coleta_YYYY-MM-DD.log
```

---

## Pré-requisitos

- Python 3.10+
- Google Chrome instalado
- Dependências Python:

```bash
pip install selenium undetected-chromedriver pandas
```

---

## Como Usar

### 1. Coletar vagas

```bash
# Coleta todos os sites configurados (Adzuna + Gupy)
python main.py

# Coleta apenas um site
python main.py adzuna
python main.py gupy
```

O Chrome abre automaticamente. Se interromper com `Ctrl+C`, o progresso é salvo
em `checkpoint_<site>.json` e a coleta retoma do mesmo ponto na próxima execução.

---

### 2. Gerar os dashboards

```bash
python gerar_dashboard.py
```

Lê os CSVs, categoriza as vagas e gera:
- `live_data.json` → atualiza KPIs e gráficos do `index.html`
- `oportunidades_data.json` → alimenta o `oportunidades.html`

---

### 3. Visualizar

Abra os arquivos no navegador:

| Arquivo | Conteúdo |
|---|---|
| `index.html` | Análise completa: KPIs, gráficos, mapa, salários |
| `oportunidades.html` | Vagas da última semana com busca e filtros por categoria/fonte |

---

### 4. Automação semanal

A coleta já está agendada para rodar toda **segunda-feira às 09:00** via
Windows Task Scheduler.

**Para forçar uma execução manual agora:**

```powershell
Start-ScheduledTask -TaskName "ColetaVagasDados"
```

**Para reconfigurar dia/hora**, edite as linhas `-DaysOfWeek` e `-At` no
`agendar_coleta.ps1` e rode:

```powershell
powershell -ExecutionPolicy Bypass -File agendar_coleta.ps1
```

**Para verificar logs:**

```
logs/coleta_YYYY-MM-DD.log
```

---

### 5. Adicionar um novo site

1. Crie `scrapers/novosite.py` herdando `ScraperBase`
2. Implemente os três métodos obrigatórios:

```python
from scrapers.base import ScraperBase

class ScraperNovoSite(ScraperBase):

    def __init__(self):
        super().__init__(nome_site="novosite")

    def construir_url(self, pagina: int) -> str:
        return f"https://novosite.com.br/vagas?q=dados&page={pagina}"

    def _aguardar_carregamento(self):
        # espera o elemento certo carregar
        ...

    def extrair_vagas_da_pagina(self) -> list[dict]:
        # retorna [{"Titulo": "...", "Link": "..."}, ...]
        ...
```

3. Adicione duas linhas no `main.py`:

```python
from scrapers.novosite import ScraperNovoSite

SCRAPERS = {
    "adzuna":   ScraperAdzuna,
    "gupy":     ScraperGupy,
    "novosite": ScraperNovoSite,   # ← nova linha
}
```

---

## Fluxo Completo

```
python main.py
      ↓  coleta vagas (Chrome automatizado)
      ↓  salva vagas_<site>.csv
      ↓
python gerar_dashboard.py
      ↓  lê CSVs, categoriza, gera JSONs
      ↓
index.html / oportunidades.html
      ↓  dashboards atualizados no navegador
```

*(Passos 1 e 2 acontecem automaticamente toda segunda-feira via Task Scheduler)*

---

## Recursos Anti-Detecção

O `ScraperBase` implementa as seguintes proteções contra bloqueio:

| Técnica | Como funciona |
|---|---|
| `undetected_chromedriver` | Remove flags de automação do Chrome |
| CDP Stealth | Injeta JS para ocultar `navigator.webdriver` |
| User-Agent aleatório | Sorteia entre Chrome, Firefox e Safari a cada sessão |
| Viewport aleatória | Simula resoluções reais de desktop |
| Scroll natural | Rola a página gradualmente antes de extrair |
| Detecção de bloqueio | Identifica Cloudflare, CAPTCHA, 403/429 |
| Retry com backoff | Aguarda 90–180s e tenta novamente ao detectar bloqueio |
| Persistência de cookies | Reutiliza sessões entre execuções |

---

## Metodologia

**CRISP-DM** (Cross-Industry Standard Process for Data Mining):

1. **Entendimento do Negócio** — mapeamento do problema de mascaramento de vagas
2. **Coleta de Dados** — scraping automatizado com Selenium
3. **Preparação dos Dados** — remoção de duplicatas, normalização, categorização por regex
4. **Análise e Visualização** — frequências, médias salariais, dashboards interativos

---

## Alinhamento ao ODS 08

Este projeto contribui para o **ODS 08 da ONU** (Trabalho Decente e Crescimento
Econômico) ao democratizar o acesso à informação sobre o mercado de trabalho,
reduzindo a assimetria de oportunidades gerada pela falta de padronização nas
publicações de vagas digitais.

---

## Referências

- Akerlof, G. A. (1970). The Market for "Lemons". *The Quarterly Journal of Economics*, 84(3).
- Brasscom (2025). *Relatório de Perspectivas do Mercado de Trabalho do Macrossetor TIC 2025*.
- Chapman et al. (2000). *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS.
- McKinney, W. (2023). *Python para análise de dados*. Novatec.
- Mitchell, R. (2018). *Web Scraping with Python*. O'Reilly Media.
- MTE (2023). *Classificação Brasileira de Ocupações (CBO)*.

---

## Autores

| Nome | Contato |
|---|---|
| Guilherme Soares Santos | contatogui14@gmail.com |
| Jonatas Oliveira de Lima | jonatas.lima7991@gmail.com |

**Fatec Santana de Parnaíba — Ciência de Dados — 2026**