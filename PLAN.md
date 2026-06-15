# Plano de Execução — Pull, Otimização e Avaliação de Prompts

## Visão Geral

O objetivo é implementar um pipeline completo de otimização de prompts usando LangChain e LangSmith:
fazer pull de um prompt ruim (v1), refatorá-lo com técnicas avançadas (v2), fazer push de volta ao Hub,
e iterar até todas as 5 métricas atingirem >= 0.8.

---

## Fase 0 — Configuração do Ambiente

**Pré-condição:** Credenciais disponíveis em `openai.yaml` e `gemini.yaml`.

### 0.1 Criar o arquivo `.env`

Copiar `.env.example` para `.env` e preencher as variáveis:

| Variável | Valor |
|---|---|
| `LANGSMITH_API_KEY` | Chave do LangSmith |
| `LANGSMITH_PROJECT` | Nome do projeto (ex: `prompt-optimization-challenge-resolved`) |
| `USERNAME_LANGSMITH_HUB` | Username do LangSmith Hub |
| `OPENAI_API_KEY` | Chave da OpenAI (retirada de `openai.yaml`) |
| `GOOGLE_API_KEY` | Chave do Gemini (retirada de `gemini.yaml`) |
| `LLM_PROVIDER` | `google` (Gemini) ou `openai` |
| `LLM_MODEL` | `gemini-2.5-flash` ou `gpt-4o-mini` |
| `EVAL_MODEL` | `gemini-2.5-flash` ou `gpt-4o` |

### 0.2 Criar e ativar virtualenv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Arquivos envolvidos:** `.env`, `requirements.txt`
**Status:** Pré-requisito para tudo que vem depois.

---

## Fase 1 — Implementar `src/pull_prompts.py`

**Objetivo:** Conectar ao LangSmith e fazer pull do prompt `leonanluppi/bug_to_user_story_v1`,
salvando-o em `prompts/bug_to_user_story_v1.yml`.

### Funções a implementar

**`pull_prompts_from_langsmith()`**
1. Verificar variáveis de ambiente obrigatórias: `LANGSMITH_API_KEY`
2. Usar `hub.pull("leonanluppi/bug_to_user_story_v1")` para baixar o prompt
3. Extrair `system_prompt` e `user_prompt` do objeto `ChatPromptTemplate` retornado
4. Montar dicionário com campos: `description`, `system_prompt`, `user_prompt`, `version`, `tags`
5. Chamar `save_yaml(data, "prompts/bug_to_user_story_v1.yml")`

**`main()`**
1. Chamar `check_env_vars(["LANGSMITH_API_KEY"])`
2. Chamar `pull_prompts_from_langsmith()`
3. Imprimir mensagem de sucesso com `print_section_header()`
4. Retornar `0` (sucesso) ou `1` (falha)

### Execução e validação

```bash
python src/pull_prompts.py
# Verificar se prompts/bug_to_user_story_v1.yml foi criado/atualizado
```

**Arquivos envolvidos:** `src/pull_prompts.py`, `prompts/bug_to_user_story_v1.yml`

---

## Fase 2 — Criar o Prompt Otimizado `prompts/bug_to_user_story_v2.yml`

**Objetivo:** Criar manualmente um prompt que supere 0.8 em todas as 5 métricas.

### Problemas no v1 (a corrigir)

- `{bug_report}` duplicado no `system_prompt` e `user_prompt` — confusão semântica
- Sem persona definida para o modelo
- Sem instruções específicas de formato de saída
- Sem exemplos de entrada/saída (nenhuma técnica aplicada)
- Sem tratamento de edge cases
- Instruções vagas e genéricas

### Técnicas a aplicar (obrigatórias)

1. **Few-shot Learning** (obrigatório): 2-3 exemplos completos de bug → user story
2. **Role Prompting** (escolhido): definir persona como "Product Manager Sênior com 10+ anos de experiência"
3. **Chain of Thought** (escolhido): instruir o modelo a raciocinar passo a passo antes de gerar a user story

### Estrutura YAML v2

```yaml
bug_to_user_story_v2:
  description: "..."
  system_prompt: |
    # Persona
    Você é um Product Manager Sênior...

    # Contexto e Objetivo
    Sua tarefa é converter relatos de bugs em User Stories...

    # Formato de Saída (Markdown obrigatório)
    ## User Story
    **Como** [persona]...

    # Exemplos (Few-shot)
    ## Exemplo 1
    Bug: ...
    User Story: ...

    ## Exemplo 2
    Bug: ...
    User Story: ...

    # Raciocínio (Chain of Thought)
    Antes de gerar a user story, pense passo a passo:
    1. Quem é afetado pelo bug?
    2. Qual é o comportamento esperado?
    3. Qual é o critério de aceite?

    # Edge Cases
    - Se o bug for vago, assuma o contexto mais provável...
    - Se houver múltiplos usuários afetados...

  user_prompt: |
    Bug Report:
    {bug_report}

    Gere a User Story seguindo as instruções acima.

  # Metadados
  version: "v2"
  techniques_applied:
    - "few-shot-learning"
    - "role-prompting"
    - "chain-of-thought"
  tags: ["bug-analysis", "user-story", "product-management", "few-shot", "cot"]
```

**Arquivos envolvidos:** `prompts/bug_to_user_story_v2.yml`

---

## Fase 3 — Implementar `src/push_prompts.py`

**Objetivo:** Ler o prompt v2 do YAML e publicá-lo no LangSmith Hub como `{username}/bug_to_user_story_v2` (público).

### Funções a implementar

**`validate_prompt(prompt_data: dict) -> tuple[bool, list]`**
- Delegar para `validate_prompt_structure()` de `utils.py`
- Retornar `(is_valid, errors)`

**`push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool`**
1. Extrair `system_prompt` e `user_prompt` do dicionário
2. Criar `ChatPromptTemplate` com `[("system", system_prompt), ("human", user_prompt)]`
3. Usar `hub.push(prompt_name, prompt_template, new_repo_is_public=True)` para publicar
4. Adicionar tags e descrição via metadados do YAML
5. Retornar `True` se sucesso

**`main()`**
1. Verificar env vars: `LANGSMITH_API_KEY`, `USERNAME_LANGSMITH_HUB`
2. Carregar `prompts/bug_to_user_story_v2.yml` com `load_yaml()`
3. Validar estrutura com `validate_prompt()`
4. Montar o nome do prompt: `{username}/bug_to_user_story_v2`
5. Chamar `push_prompt_to_langsmith()`
6. Confirmar URL pública no dashboard LangSmith

### Execução e validação

```bash
python src/push_prompts.py
# Verificar em https://smith.langchain.com/prompts que o prompt aparece como público
```

**Arquivos envolvidos:** `src/push_prompts.py`

---

## Fase 4 — Implementar `tests/test_prompts.py`

**Objetivo:** Escrever os 6 testes usando pytest para validar o prompt v2.

### Testes a implementar na classe `TestPrompts`

| Teste | O que verifica | Como implementar |
|---|---|---|
| `test_prompt_has_system_prompt` | Campo `system_prompt` existe e não está vazio | Carregar YAML, assertar `system_prompt` != `""` |
| `test_prompt_has_role_definition` | Prompt define persona (ex: "Você é um Product Manager") | Buscar substring no `system_prompt` |
| `test_prompt_mentions_format` | Prompt exige Markdown ou User Story padrão | Buscar "Markdown" ou "User Story" no `system_prompt` |
| `test_prompt_has_few_shot_examples` | Contém exemplos de entrada/saída | Buscar "Exemplo" ou "Example" no `system_prompt`, contar ocorrências >= 2 |
| `test_prompt_no_todos` | Não contém `[TODO]` | Assertar que `"[TODO]"` não aparece em nenhum campo de texto |
| `test_minimum_techniques` | Metadados listam >= 2 técnicas | Verificar `len(prompt_data['techniques_applied']) >= 2` |

### Fixture sugerida

```python
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"

@pytest.fixture
def prompt_data():
    data = load_prompts(str(PROMPT_FILE))
    return data["bug_to_user_story_v2"]
```

### Execução e validação

```bash
pytest tests/test_prompts.py -v
# Todos os 6 testes devem passar com OK
```

**Arquivos envolvidos:** `tests/test_prompts.py`

---

## Fase 5 — Ciclo de Avaliação e Iteração

**Objetivo:** Atingir todas as métricas >= 0.8. Estima-se 3-5 iterações.

### Pré-condições

- `.env` configurado com `LANGSMITH_API_KEY`, `USERNAME_LANGSMITH_HUB` e credenciais do LLM
- `prompts/bug_to_user_story_v2.yml` criado (Fase 2)
- Push feito ao LangSmith (Fase 3)

### Ciclo por iteração

```
1. Editar prompts/bug_to_user_story_v2.yml (melhorar prompt)
2. python src/push_prompts.py     → publicar nova versão no Hub
3. python src/evaluate.py          → rodar avaliação (15 exemplos × 3 métricas)
4. Analisar métricas abaixo de 0.8 → identificar o problema
5. Repetir até STATUS: APROVADO
```

### Estratégia de diagnóstico por métrica baixa

| Métrica baixa | Causa provável | Ação corretiva |
|---|---|---|
| **Clarity** | Resposta confusa ou mal estruturada | Reforçar instrução de formato (headers, seções obrigatórias) |
| **Precision** | Resposta imprecisa ou genérica | Adicionar contexto mais específico, melhorar exemplos |
| **F1-Score** | Termos-chave ausentes em relação à referência | Instruir o modelo a incluir termos técnicos do bug |
| **Helpfulness** | Resposta não útil ao desenvolvedor | Reforçar persona e objetivo, adicionar critérios de aceite |
| **Correctness** | Conteúdo errado ou inventado | Reduzir temperatura implícita, instruir conservadorismo |

### Critério de aprovação final

- Helpfulness >= 0.8
- Correctness >= 0.8
- F1-Score >= 0.8
- Clarity >= 0.8
- Precision >= 0.8
- Média das 5 métricas >= 0.8

---

## Fase 6 — Documentação

### 6.1 Atualizar `README.md`

O README deve conter as seguintes seções:

- **Objetivos** — o que o projeto faz
- **Features** — capacidades implementadas
- **Arquitetura** — descrição dos componentes e fluxo
- **Fluxograma Mermaid** — diagrama do pipeline (pull → otimizar → push → avaliar → iterar)
- **Estrutura do Projeto** — árvore de arquivos com descrições
- **Tabela de Variáveis de Ambiente** — nome, descrição, obrigatório/opcional, exemplo
- **Requisitos de Software** — Python 3.9+, dependências
- **Como Executar** — comandos para cada fase (venv, pull, push, evaluate, test)
- **Técnicas Aplicadas (Fase 2)** — quais, por quê, exemplos práticos
- **Resultados Finais** — tabela comparativa v1 vs v2 com métricas

### 6.2 Criar `CLAUDE.md`

Arquivo de contexto para o Claude sobre o projeto:

- Arquitetura e decisões técnicas
- Fluxo de dados (YAML → LangSmith Hub → evaluate → metrics)
- Como `evaluate.py` calcula as métricas (helpfulness = média de clarity + precision)
- Variáveis de ambiente críticas
- Comandos de execução
- O que NÃO alterar (`evaluate.py`, `metrics.py`, `utils.py`, `datasets/`)

### 6.3 Criar `AGENTS.md`

Instruções para IAs que forem manutentar o código:

- Convenções de código do projeto
- Como estender as métricas
- Como adicionar novos prompts
- Regras de versionamento dos prompts (v1, v2, v3...)
- Como interpretar resultados do LangSmith
- Alertas sobre edge cases do `evaluate.py`

**Arquivos envolvidos:** `README.md`, `CLAUDE.md`, `AGENTS.md`

---

## Ordem de Execução Resumida

```
Fase 0  →  Configurar .env e instalar dependências
Fase 1  →  Implementar e rodar pull_prompts.py
Fase 2  →  Criar bug_to_user_story_v2.yml (prompt otimizado)
Fase 3  →  Implementar e rodar push_prompts.py
Fase 4  →  Implementar e rodar tests/test_prompts.py
Fase 5  →  Ciclo: push → evaluate → refinar (3-5x)
Fase 6  →  Documentar README.md, CLAUDE.md, AGENTS.md
```

---

## Arquivos a Criar ou Modificar

| Arquivo | Ação | Fase |
|---|---|---|
| `.env` | Criar (baseado em `.env.example`) | 0 |
| `src/pull_prompts.py` | Implementar corpo das funções | 1 |
| `prompts/bug_to_user_story_v2.yml` | Criar do zero | 2 |
| `src/push_prompts.py` | Implementar corpo das funções | 3 |
| `tests/test_prompts.py` | Implementar 6 testes | 4 |
| `README.md` | Reescrever com seções obrigatórias | 6 |
| `CLAUDE.md` | Criar | 6 |
| `AGENTS.md` | Criar | 6 |

## Arquivos que NÃO devem ser alterados

- `src/evaluate.py` — script de avaliação completo (pronto)
- `src/metrics.py` — 5 métricas implementadas (pronto)
- `src/utils.py` — funções auxiliares (pronto)
- `datasets/bug_to_user_story.jsonl` — 15 exemplos de avaliação (pronto)
- `requirements.txt` — dependências (pronto)

## Melhorias

- Validar que tudo esta funcionando conforme a especificacao e corrigir os erros que houverem
- Criar checagens de requisitos e exibir mensanges de erro claras quando algo estiver errado ou faltando
- Criar casos de teste
