"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt no formato username/nome
        prompt_data: Dados do prompt extraídos do YAML

    Returns:
        True se sucesso, False caso contrário
    """
    print(f"\nFazendo push do prompt: {prompt_name}")

    system_prompt = prompt_data.get("system_prompt", "")
    user_prompt = prompt_data.get("user_prompt", "")
    description = prompt_data.get("description", "")
    tags = prompt_data.get("tags", [])

    try:
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        hub.push(
            prompt_name,
            prompt_template,
            new_repo_is_public=True,
            new_repo_description=description,
            tags=tags if isinstance(tags, list) else [],
        )

        print(f"   ✓ Prompt publicado com sucesso!")
        print(f"   ✓ Visibilidade: PÚBLICO")
        print(f"   ✓ URL: https://smith.langchain.com/hub/{prompt_name}")
        return True

    except Exception as e:
        print(f"   ❌ Erro ao fazer push do prompt '{prompt_name}': {e}")
        print("\n   Verifique:")
        print("   - LANGSMITH_API_KEY está configurada corretamente no .env")
        print("   - USERNAME_LANGSMITH_HUB corresponde ao seu username no LangSmith")
        print("   - Você tem acesso ao workspace do LangSmith")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    return validate_prompt_structure(prompt_data)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    if not username:
        print("❌ USERNAME_LANGSMITH_HUB está vazio no .env")
        return 1

    prompt_file = "prompts/bug_to_user_story_v2.yml"
    print(f"Carregando prompt de: {prompt_file}")

    data = load_yaml(prompt_file)
    if not data:
        print(f"❌ Não foi possível carregar: {prompt_file}")
        print("   Certifique-se de ter criado o arquivo prompts/bug_to_user_story_v2.yml")
        return 1

    prompt_key = "bug_to_user_story_v2"
    if prompt_key not in data:
        print(f"❌ Chave '{prompt_key}' não encontrada no YAML")
        print(f"   O arquivo deve ter a chave raiz: {prompt_key}")
        return 1

    prompt_data = data[prompt_key]

    print("Validando estrutura do prompt...")
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for err in errors:
            print(f"   - {err}")
        return 1

    techniques = prompt_data.get("techniques_applied", [])
    print(f"   ✓ Estrutura válida")
    print(f"   ✓ Técnicas aplicadas: {', '.join(techniques)}")

    prompt_name = f"{username}/bug_to_user_story_v2"

    if push_prompt_to_langsmith(prompt_name, prompt_data):
        print_section_header("PUSH CONCLUÍDO COM SUCESSO")
        print("Próximos passos:")
        print("1. Acesse o LangSmith Hub para confirmar a publicação")
        print("2. Execute a avaliação: python src/evaluate.py")
        print("3. Se métricas < 0.8: edite o YAML, repita push e avaliação")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
