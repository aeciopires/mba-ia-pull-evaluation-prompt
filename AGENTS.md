# AGENTS.md — Instruções para Agentes de IA

Este arquivo contém instruções e contexto para agentes de IA que mantêm ou evoluem este projeto.

## Contexto do Projeto

Pipeline de otimização de prompts com LangChain e LangSmith para converter relatos de bugs em User Stories. O objetivo é manter o prompt `bug_to_user_story_v2` com todas as métricas de avaliação acima de 0.8.

## Regras Gerais

1. **Nunca altere** `src/evaluate.py`, `src/metrics.py`, `src/utils.py` ou `datasets/bug_to_user_story.jsonl`
2. **O único arquivo de prompt que importa** para avaliação é `prompts/bug_to_user_story_v2.yml`
3. **Antes de qualquer execução**, valide o ambiente:
   ```bash
   python src/validate.py --no-api   # rápido, sem rede
   python src/validate.py            # completo, testa LangSmith
   ```
4. **Após qualquer edição no YAML**, é obrigatório fazer push antes de avaliar:
   ```bash
   python src/push_prompts.py && python src/evaluate.py
   ```
5. **O critério de sucesso** é: TODAS as 5 métricas >= 0.8 (helpfulness, correctness, f1_score, clarity, precision)

## Estrutura do Prompt v2

O prompt em `prompts/bug_to_user_story_v2.yml` deve sempre conter:

```yaml
bug_to_user_story_v2:
  description: "..."           # string descritiva
  system_prompt: |             # bloco YAML literal
    # Persona                  # obrigatório: define role
    Você é um Product Manager...
    
    # Exemplos (Few-shot)      # obrigatório: >= 2 exemplos numerados
    ## Exemplo 1 — ...
    ## Exemplo 2 — ...
    
  user_prompt: |
    Bug Report:
    {bug_report}               # variável obrigatória — não renomear
    
  version: "v2"
  techniques_applied:          # obrigatório: >= 2 técnicas
    - "few-shot-learning"
    - "role-prompting"
  tags: [...]
```

## Como Iterar no Prompt

### Diagnóstico por Métrica

| Métrica baixa | Causa provável | Ação sugerida |
|---|---|---|
| **Clarity** | Resposta mal estruturada | Reforçar headers Markdown, seções obrigatórias |
| **Precision** | Resposta imprecisa/genérica | Melhorar exemplos, instruir conservadorismo |
| **F1-Score** | Termos-chave ausentes vs referência | Instruir uso de "Critérios de Aceitação:", "Dado que", "Quando", "Então" |
| **Helpfulness** | Resposta pouco útil | Reforçar persona e objetivo do PM |
| **Correctness** | Conteúdo incorreto | Instruir não inventar detalhes não mencionados no bug |

### Ciclo de Melhoria

```
1. Editar prompts/bug_to_user_story_v2.yml
2. python src/push_prompts.py
3. python src/evaluate.py
4. Se alguma métrica < 0.8: voltar ao passo 1
5. Se todas >= 0.8: commit e push para o GitHub
```

## Como Adicionar Novas Versões do Prompt

Para criar uma v3 (por exemplo):

1. Criar `prompts/bug_to_user_story_v3.yml` com chave raiz `bug_to_user_story_v3`
2. Em `push_prompts.py`, adicionar referência ao novo arquivo
3. Em `evaluate.py`, adicionar `f"{username}/bug_to_user_story_v3"` à lista `prompts_to_evaluate`
4. Manter a v2 como referência para comparação

## Convenções de Código

- Scripts em `src/` usam `sys.exit(main())` como ponto de entrada
- Imports de `utils` são feitos sem path manipulation (Python adiciona `src/` ao path ao executar `python src/script.py`)
- Credenciais NUNCA são hardcoded — sempre via `os.getenv()` ou `load_dotenv()`
- Todas as funções retornam bool ou None em caso de falha, não levantam exceções diretamente
- Mensagens de log usam emojis: `✓` para sucesso, `❌` para erro, `⚠️` para aviso

## Interpretando Resultados do LangSmith

O `evaluate.py` calcula médias simples dos scores por exemplo:
- `avg_f1 = sum(f1_scores) / len(f1_scores)` — se não houver respostas, retorna 0.0
- `helpfulness = (clarity + precision) / 2`
- `correctness = (f1 + precision) / 2`

Scores de 0.0 em todas as métricas geralmente indicam:
- Erro de conexão com o LLM (credenciais inválidas)
- Prompt não encontrado no Hub (username errado ou push não realizado)
- Variável `{bug_report}` ausente ou renomeada no template

## Variáveis de Template

A única variável de template do prompt é `{bug_report}`. O dataset passa:
```json
{"inputs": {"bug_report": "..."}, "outputs": {"reference": "..."}}
```

O `evaluate.py` faz:
```python
chain.invoke({"bug_report": example.inputs["bug_report"]})
```

Qualquer variável entre `{` e `}` no `system_prompt` ou `user_prompt` será interpretada como variável de template pelo LangChain. **Evite usar `{}` no system_prompt** exceto como sintaxe Python/JSON dentro de blocos de código (onde o contexto deixa claro que não é uma variável de template).

## Testes

Os 6 testes em `tests/test_prompts.py` validam o arquivo `prompts/bug_to_user_story_v2.yml`:

```bash
pytest tests/test_prompts.py -v
```

Todos os 6 testes devem passar antes de considerar o prompt pronto para push. Os testes verificam:
- `system_prompt` existe e não está vazio
- Role/persona definida ("você é um", "product manager", etc.)
- Formato de saída mencionado ("markdown", "user story", etc.)
- Pelo menos 2 exemplos numerados ("Exemplo 1", "Exemplo 2")
- Sem `[TODO]` não preenchidos
- `techniques_applied` com >= 2 técnicas

## Segurança

- O arquivo `.env` está no `.gitignore` — nunca commitar credenciais
- `openai.yaml` e `gemini.yaml` também estão no `.gitignore`
- Credenciais são lidas exclusivamente via `python-dotenv` (`load_dotenv()`)
