"""
Script de validação completa do ambiente e configuração do projeto.

Verifica em ordem:
1. Versão do Python (>= 3.9)
2. Pacotes Python instalados (requirements.txt)
3. Arquivo .env e variáveis de ambiente obrigatórias
4. Arquivos de dados e configuração (prompts, datasets, src)
5. Estrutura e conteúdo do prompt v2 (YAML)
6. Dataset de avaliação (JSONL com 15 exemplos válidos)
7. Conectividade com LangSmith (opcional)

Uso:
    python src/validate.py            # Todas as verificações
    python src/validate.py --no-api   # Pula verificação de conectividade
"""

import sys
import os
import json
import importlib
import importlib.metadata
import argparse
from pathlib import Path
from typing import List, Tuple

# Garante que podemos importar de src/ mesmo rodando de outro diretório
SRC_DIR = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))

# Carrega .env antes de qualquer check
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass  # será detectado na checagem de pacotes


# ─────────────────────────────────────────────
# Helpers de formatação
# ─────────────────────────────────────────────

def _ok(msg: str) -> str:
    return f"   ✅ {msg}"


def _warn(msg: str) -> str:
    return f"   ⚠️  {msg}"


def _fail(msg: str) -> str:
    return f"   ❌ {msg}"


def _header(title: str) -> None:
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


# ─────────────────────────────────────────────
# Verificações
# ─────────────────────────────────────────────

def check_python_version() -> List[str]:
    """Verifica se a versão do Python é >= 3.9."""
    _header("1/7 — Versão do Python")
    errors = []
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version >= (3, 9):
        print(_ok(f"Python {version_str} — OK (mínimo: 3.9)"))
    else:
        msg = f"Python {version_str} é muito antigo. Versão mínima: 3.9"
        print(_fail(msg))
        errors.append(msg)

    return errors


def check_packages() -> List[str]:
    """Verifica se todos os pacotes do requirements.txt estão instalados."""
    _header("2/7 — Pacotes Python (requirements.txt)")
    errors = []

    requirements_file = ROOT_DIR / "requirements.txt"
    if not requirements_file.exists():
        msg = "requirements.txt não encontrado"
        print(_fail(msg))
        errors.append(msg)
        return errors

    # Mapeia "nome-do-pacote" para o nome do módulo importável
    package_import_map = {
        "langchain": "langchain",
        "langchain-core": "langchain_core",
        "langchain-community": "langchain_community",
        "langsmith": "langsmith",
        "langchain-openai": "langchain_openai",
        "langchain-google-genai": "langchain_google_genai",
        "python-dotenv": "dotenv",
        "pyyaml": "yaml",
        "pydantic": "pydantic",
        "pytest": "pytest",
    }

    with open(requirements_file, "r") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    for line in lines:
        # Separa nome==versão
        pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
        import_name = package_import_map.get(pkg_name, pkg_name.replace("-", "_"))

        try:
            importlib.import_module(import_name)
            # Tenta obter versão instalada
            try:
                installed_ver = importlib.metadata.version(pkg_name)
                print(_ok(f"{pkg_name} {installed_ver}"))
            except importlib.metadata.PackageNotFoundError:
                print(_ok(f"{pkg_name} (versão não detectada)"))
        except ImportError:
            msg = f"Pacote não instalado: {pkg_name}  →  pip install {pkg_name}"
            print(_fail(msg))
            errors.append(msg)

    return errors


def check_env_vars() -> Tuple[List[str], List[str]]:
    """Verifica arquivo .env e variáveis de ambiente obrigatórias."""
    _header("3/7 — Arquivo .env e Variáveis de Ambiente")
    errors = []
    warnings = []

    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        msg = ".env não encontrado. Execute: cp .env.example .env"
        print(_fail(msg))
        errors.append(msg)
        return errors, warnings

    print(_ok(".env encontrado"))

    # Variáveis sempre obrigatórias
    always_required = [
        "LANGSMITH_API_KEY",
        "USERNAME_LANGSMITH_HUB",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "EVAL_MODEL",
    ]

    for var in always_required:
        value = os.getenv(var, "").strip()
        if value:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(_ok(f"{var} = {masked}"))
        else:
            msg = f"{var} não configurada no .env"
            print(_fail(msg))
            errors.append(msg)

    # Variáveis condicionais por provider
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if key:
            print(_ok(f"OPENAI_API_KEY = {key[:8]}..."))
        else:
            msg = "OPENAI_API_KEY não configurada (obrigatória quando LLM_PROVIDER=openai)"
            print(_fail(msg))
            errors.append(msg)
    elif provider in ("google", "gemini"):
        key = os.getenv("GOOGLE_API_KEY", "").strip()
        if key:
            print(_ok(f"GOOGLE_API_KEY = {key[:8]}..."))
        else:
            msg = "GOOGLE_API_KEY não configurada (obrigatória quando LLM_PROVIDER=google)"
            print(_fail(msg))
            errors.append(msg)
    elif provider:
        msg = f"LLM_PROVIDER='{provider}' não reconhecido. Use 'openai' ou 'google'"
        print(_fail(msg))
        errors.append(msg)

    # Variáveis opcionais com valores padrão
    project = os.getenv("LANGSMITH_PROJECT", "")
    if project:
        print(_ok(f"LANGSMITH_PROJECT = {project}"))
    else:
        msg = "LANGSMITH_PROJECT não configurada — usará default: prompt-optimization-challenge-resolved"
        print(_warn(msg))
        warnings.append(msg)

    return errors, warnings


def check_files() -> List[str]:
    """Verifica se todos os arquivos obrigatórios do projeto existem."""
    _header("4/7 — Arquivos de Configuração e Dados")
    errors = []

    required_files = {
        ".env.example":                          "Template de variáveis de ambiente",
        "requirements.txt":                      "Dependências Python",
        "prompts/bug_to_user_story_v1.yml":      "Prompt original (baixa qualidade)",
        "prompts/bug_to_user_story_v2.yml":      "Prompt otimizado (v2)",
        "datasets/bug_to_user_story.jsonl":      "Dataset de avaliação (15 exemplos)",
        "src/evaluate.py":                       "Script de avaliação",
        "src/metrics.py":                        "Métricas LLM-as-Judge",
        "src/utils.py":                          "Funções auxiliares",
        "src/pull_prompts.py":                   "Script de pull",
        "src/push_prompts.py":                   "Script de push",
        "tests/test_prompts.py":                 "Testes de validação do prompt",
    }

    optional_files = {
        "CLAUDE.md":   "Contexto técnico para o Claude Code",
        "AGENTS.md":   "Instruções de manutenção para agentes de IA",
        "README.md":   "Documentação do projeto",
    }

    for rel_path, description in required_files.items():
        full_path = ROOT_DIR / rel_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(_ok(f"{rel_path}  ({size:,} bytes) — {description}"))
        else:
            msg = f"Arquivo obrigatório não encontrado: {rel_path}  ({description})"
            print(_fail(msg))
            errors.append(msg)

    for rel_path, description in optional_files.items():
        full_path = ROOT_DIR / rel_path
        if full_path.exists():
            print(_ok(f"{rel_path} — {description}"))
        else:
            print(_warn(f"{rel_path} não encontrado (opcional) — {description}"))

    return errors


def check_prompt_v2() -> List[str]:
    """Valida a estrutura e conteúdo do prompt v2 (YAML)."""
    _header("5/7 — Estrutura do Prompt v2 (YAML)")
    errors = []

    prompt_path = ROOT_DIR / "prompts" / "bug_to_user_story_v2.yml"
    if not prompt_path.exists():
        msg = "prompts/bug_to_user_story_v2.yml não encontrado"
        print(_fail(msg))
        errors.append(msg)
        return errors

    try:
        import yaml
        with open(prompt_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        msg = f"Erro ao parsear YAML: {e}"
        print(_fail(msg))
        errors.append(msg)
        return errors

    root_key = "bug_to_user_story_v2"
    if root_key not in data:
        msg = f"Chave raiz '{root_key}' não encontrada no YAML"
        print(_fail(msg))
        errors.append(msg)
        return errors

    print(_ok(f"Chave raiz '{root_key}' encontrada"))
    prompt = data[root_key]

    # Campos obrigatórios
    required_fields = ["description", "system_prompt", "version"]
    for field in required_fields:
        if field in prompt and prompt[field]:
            print(_ok(f"Campo '{field}' presente e não vazio"))
        else:
            msg = f"Campo obrigatório ausente ou vazio: '{field}'"
            print(_fail(msg))
            errors.append(msg)

    # Sem [TODO]
    full_text = " ".join(str(v) for v in prompt.values() if isinstance(v, str))
    if "[TODO]" in full_text:
        msg = "Prompt contém '[TODO]' não preenchido"
        print(_fail(msg))
        errors.append(msg)
    else:
        print(_ok("Sem '[TODO]' no conteúdo"))

    # Variável {bug_report} no user_prompt
    user_prompt = prompt.get("user_prompt", "")
    if "{bug_report}" in user_prompt:
        print(_ok("Variável {bug_report} presente no user_prompt"))
    else:
        msg = "Variável {bug_report} ausente no user_prompt — o evaluate.py não conseguirá substituir o bug"
        print(_fail(msg))
        errors.append(msg)

    # Técnicas aplicadas
    techniques = prompt.get("techniques_applied", [])
    if isinstance(techniques, list) and len(techniques) >= 2:
        print(_ok(f"techniques_applied: {', '.join(techniques)}"))
    else:
        msg = f"techniques_applied deve ter >= 2 itens, encontrados: {len(techniques) if isinstance(techniques, list) else 0}"
        print(_fail(msg))
        errors.append(msg)

    # Exemplos few-shot no system_prompt
    import re
    system_prompt = prompt.get("system_prompt", "")
    examples = re.findall(r"(?i)exemplo\s+\d+", system_prompt)
    if len(examples) >= 2:
        print(_ok(f"Few-shot: {len(examples)} exemplo(s) numerado(s) encontrados"))
    else:
        msg = f"Few-shot: mínimo 2 exemplos numerados esperados, encontrados: {len(examples)}"
        print(_fail(msg))
        errors.append(msg)

    return errors


def check_dataset() -> List[str]:
    """Valida o dataset JSONL (15 exemplos com campos obrigatórios)."""
    _header("6/7 — Dataset de Avaliação (JSONL)")
    errors = []

    dataset_path = ROOT_DIR / "datasets" / "bug_to_user_story.jsonl"
    if not dataset_path.exists():
        msg = "datasets/bug_to_user_story.jsonl não encontrado"
        print(_fail(msg))
        errors.append(msg)
        return errors

    examples = []
    parse_errors = []

    with open(dataset_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                examples.append(obj)

                # Verifica campos obrigatórios
                if "inputs" not in obj or "bug_report" not in obj.get("inputs", {}):
                    parse_errors.append(f"Linha {i}: campo 'inputs.bug_report' ausente")
                if "outputs" not in obj or "reference" not in obj.get("outputs", {}):
                    parse_errors.append(f"Linha {i}: campo 'outputs.reference' ausente")

            except json.JSONDecodeError as e:
                parse_errors.append(f"Linha {i}: JSON inválido — {e}")

    total = len(examples)
    if total == 15:
        print(_ok(f"{total} exemplos carregados (esperado: 15)"))
    elif total > 0:
        msg = f"Dataset tem {total} exemplos (esperado: 15)"
        print(_warn(msg))
    else:
        msg = "Dataset vazio ou inválido"
        print(_fail(msg))
        errors.append(msg)

    if parse_errors:
        for pe in parse_errors:
            print(_fail(pe))
            errors.append(pe)
    else:
        print(_ok("Todos os exemplos têm 'inputs.bug_report' e 'outputs.reference'"))

    # Distribuição de complexidade
    complexities = {}
    for ex in examples:
        c = ex.get("metadata", {}).get("complexity", "unknown")
        complexities[c] = complexities.get(c, 0) + 1

    if complexities:
        dist = ", ".join(f"{k}: {v}" for k, v in sorted(complexities.items()))
        print(_ok(f"Complexidade — {dist}"))

    return errors


def check_langsmith_connection() -> Tuple[List[str], List[str]]:
    """Testa a conectividade com o LangSmith (listagem de datasets)."""
    _header("7/7 — Conectividade com LangSmith (opcional)")
    errors = []
    warnings = []

    api_key = os.getenv("LANGSMITH_API_KEY", "").strip()
    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()

    if not api_key:
        msg = "LANGSMITH_API_KEY não configurada — pulando verificação de conectividade"
        print(_warn(msg))
        warnings.append(msg)
        return errors, warnings

    try:
        from langsmith import Client
        client = Client(api_key=api_key)
        # Tenta listar datasets (operação leve)
        datasets = list(client.list_datasets(limit=1))
        print(_ok("Conexão com LangSmith estabelecida com sucesso"))
    except Exception as e:
        msg = f"Falha ao conectar com LangSmith: {e}"
        print(_fail(msg))
        errors.append(msg)
        return errors, warnings

    # Verifica se o prompt v2 existe no Hub
    if username:
        prompt_name = f"{username}/bug_to_user_story_v2"
        try:
            from langchain import hub
            hub.pull(prompt_name)
            print(_ok(f"Prompt '{prompt_name}' encontrado no LangSmith Hub"))
        except Exception:
            msg = f"Prompt '{prompt_name}' não encontrado no Hub — execute: python src/push_prompts.py"
            print(_warn(msg))
            warnings.append(msg)
    else:
        msg = "USERNAME_LANGSMITH_HUB não configurado — não foi possível verificar o prompt no Hub"
        print(_warn(msg))
        warnings.append(msg)

    return errors, warnings


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida o ambiente, dependências e configuração do projeto."
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Pula a verificação de conectividade com LangSmith (mais rápido, sem chamadas de rede)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  VALIDAÇÃO DO AMBIENTE — Pull, Otimização e Avaliação de Prompts")
    print("=" * 60)

    all_errors: List[str] = []
    all_warnings: List[str] = []

    # 1. Python
    all_errors += check_python_version()

    # 2. Pacotes
    all_errors += check_packages()

    # 3. Variáveis de ambiente
    env_errors, env_warnings = check_env_vars()
    all_errors += env_errors
    all_warnings += env_warnings

    # 4. Arquivos
    all_errors += check_files()

    # 5. Prompt v2
    all_errors += check_prompt_v2()

    # 6. Dataset
    all_errors += check_dataset()

    # 7. LangSmith (opcional)
    if args.no_api:
        _header("7/7 — Conectividade com LangSmith (opcional)")
        print(_warn("Pulado via --no-api"))
    else:
        api_errors, api_warnings = check_langsmith_connection()
        all_errors += api_errors
        all_warnings += api_warnings

    # ── Resumo Final ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  RESUMO FINAL")
    print("=" * 60)

    if all_warnings:
        print(f"\n⚠️  Avisos ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"   • {w}")

    if all_errors:
        print(f"\n❌ Erros encontrados ({len(all_errors)}):")
        for e in all_errors:
            print(f"   • {e}")
        print("\n🔴 STATUS: AMBIENTE COM PROBLEMAS — corrija os erros acima antes de prosseguir.\n")
        return 1

    print("\n✅ STATUS: AMBIENTE OK — todos os requisitos estão satisfeitos.")
    print("\nPróximos passos:")
    print("  1. python src/pull_prompts.py   # Baixar prompt v1")
    print("  2. python src/push_prompts.py   # Publicar prompt v2")
    print("  3. python src/evaluate.py       # Avaliar métricas")
    print("  4. pytest tests/test_prompts.py # Rodar testes\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
