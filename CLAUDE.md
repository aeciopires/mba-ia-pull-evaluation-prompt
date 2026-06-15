# CLAUDE.md — Contexto do Projeto para Claude Code

## O que este projeto faz

Pipeline de otimização de prompts usando LangChain e LangSmith:

1. **Pull**: baixa prompt ruim (`leonanluppi/bug_to_user_story_v1`) do LangSmith Hub
2. **Otimização**: aplica técnicas avançadas de prompt engineering para criar v2
3. **Push**: publica o prompt otimizado (`{username}/bug_to_user_story_v2`) no Hub como público
4. **Avaliação**: roda 15 exemplos de bugs contra o prompt e calcula 5 métricas
5. **Iteração**: refina o prompt até todas as métricas >= 0.8

## Arquitetura

```
YAML (prompts/)  →  push_prompts.py  →  LangSmith Hub  →  evaluate.py
                                                                ↓
                                               15 exemplos (datasets/)
                                                                ↓
                                              metrics.py (F1, Clarity, Precision)
                                                                ↓
                                              Helpfulness = (Clarity + Precision) / 2
                                              Correctness  = (F1 + Precision) / 2
```

## Cálculo das Métricas

O arquivo `src/evaluate.py` calcula 3 métricas base e 2 derivadas:

| Métrica | Tipo | Fórmula |
|---|---|---|
| F1-Score | Base | 2 * (Precision_overlap * Recall_overlap) / (P + R) — via LLM judge |
| Clarity | Base | Média de 4 critérios (organização, linguagem, concisão, ausência de ambiguidade) |
| Precision | Base | Média de 3 critérios (sem alucinações, foco na pergunta, correção factual) |
| Helpfulness | Derivada | (Clarity + Precision) / 2 |
| Correctness | Derivada | (F1 + Precision) / 2 |

Critério de aprovação: **TODAS as 5 métricas >= 0.8**.

## Variáveis de Ambiente Críticas

| Variável | Obrigatória | Descrição |
|---|---|---|
| `LANGSMITH_API_KEY` | Sim | Chave de API do LangSmith |
| `USERNAME_LANGSMITH_HUB` | Sim | Username para publicar prompts no Hub |
| `LANGSMITH_PROJECT` | Não | Default: `prompt-optimization-challenge-resolved` |
| `LLM_PROVIDER` | Sim | `google` ou `openai` |
| `LLM_MODEL` | Sim | Modelo para geração (ex: `gemini-2.5-flash`) |
| `EVAL_MODEL` | Sim | Modelo para avaliação (ex: `gemini-2.5-flash` ou `gpt-4o`) |
| `GOOGLE_API_KEY` | Se `LLM_PROVIDER=google` | Chave do Google AI Studio |
| `OPENAI_API_KEY` | Se `LLM_PROVIDER=openai` | Chave da OpenAI |

## Fluxo de Dados do evaluate.py

```python
# 1. Cria dataset no LangSmith a partir do JSONL local
create_evaluation_dataset(client, dataset_name, "datasets/bug_to_user_story.jsonl")

# 2. Puxa prompt do Hub (fonte única de verdade — não lê do YAML!)
prompt = hub.pull(f"{username}/bug_to_user_story_v2")

# 3. Para cada um dos 15 exemplos:
#    inputs = {"bug_report": "..."}, outputs = {"reference": "..."}
chain = prompt | llm
answer = chain.invoke(inputs)

# 4. Calcula métricas via LLM-as-Judge
f1 = evaluate_f1_score(question, answer, reference)
clarity = evaluate_clarity(question, answer, reference)
precision = evaluate_precision(question, answer, reference)
```

**IMPORTANTE**: O `evaluate.py` puxa o prompt diretamente do LangSmith Hub. Editar o YAML local **não tem efeito** — é necessário fazer push antes de avaliar.

## Estrutura de Arquivos

```
src/
├── validate.py        # Implementado: validação completa do ambiente (7 categorias)
├── pull_prompts.py    # Implementado: pull do Hub, salva YAML local
├── push_prompts.py    # Implementado: push do YAML para o Hub (público)
├── evaluate.py        # PRONTO — não alterar
├── metrics.py         # PRONTO — não alterar
└── utils.py           # PRONTO — não alterar

prompts/
├── bug_to_user_story_v1.yml  # Prompt de baixa qualidade (referência)
└── bug_to_user_story_v2.yml  # Prompt otimizado (ESTE é o que importa)

datasets/
└── bug_to_user_story.jsonl   # 15 exemplos: 5 simples, 7 médios, 3 complexos

tests/
└── test_prompts.py    # Implementado: 6 testes do prompt v2
```

## Estrutura do YAML de Prompt

```yaml
bug_to_user_story_v2:
  description: "..."        # obrigatório
  system_prompt: |          # obrigatório — instruções para o LLM
    ...
  user_prompt: |            # template com variável {bug_report}
    Bug Report:
    {bug_report}
    ...
  version: "v2"             # obrigatório
  techniques_applied:       # obrigatório — mínimo 2 itens
    - "few-shot-learning"
    - "role-prompting"
  tags:
    - "bug-analysis"
```

A validação de estrutura é feita por `utils.validate_prompt_structure()`, que verifica:
- Campos obrigatórios: `description`, `system_prompt`, `version`
- `system_prompt` não vazio
- Sem `TODO` no `system_prompt`
- `techniques_applied` com >= 2 itens

## Comandos de Execução

```bash
# Setup (primeira vez)
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Validação do ambiente (sempre rodar antes do pipeline)
python src/validate.py          # Completa (com teste de conectividade)
python src/validate.py --no-api # Sem chamadas de rede (mais rápida)

# Pipeline completo
python src/pull_prompts.py    # Fase 1: baixar prompt v1
python src/push_prompts.py    # Fase 3: publicar prompt v2
python src/evaluate.py        # Fase 5: avaliar métricas

# Testes
pytest tests/test_prompts.py -v
```

## validate.py — O que verifica

O script `src/validate.py` cobre 7 categorias em sequência:

| # | Categoria | Detalhes |
|---|---|---|
| 1 | Python | Versão >= 3.9 |
| 2 | Pacotes | Todos os itens de `requirements.txt` importáveis |
| 3 | Variáveis `.env` | Campos obrigatórios preenchidos, provider correto, chave de API presente |
| 4 | Arquivos | Prompts, dataset, scripts `src/`, testes existem |
| 5 | Prompt v2 YAML | Campos obrigatórios, `{bug_report}`, techniques, exemplos few-shot |
| 6 | Dataset JSONL | 15 exemplos com `inputs.bug_report` e `outputs.reference` |
| 7 | LangSmith | Conexão API + prompt no Hub (pulável via `--no-api`) |

Retorna exit code `0` se tudo OK, `1` se há erros.

## O que NÃO alterar

- `src/evaluate.py` — lógica de avaliação completa
- `src/metrics.py` — implementação das 5 métricas
- `src/utils.py` — funções auxiliares (get_llm, validate_prompt_structure, etc.)
- `datasets/bug_to_user_story.jsonl` — 15 exemplos de avaliação
- `requirements.txt` — dependências do projeto
