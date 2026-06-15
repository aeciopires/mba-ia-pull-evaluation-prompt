"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt de baixa qualidade do LangSmith Hub e salva localmente.

    Returns:
        True se sucesso, False caso contrário
    """
    prompt_hub_name = "leonanluppi/bug_to_user_story_v1"
    output_path = "prompts/bug_to_user_story_v1.yml"

    print(f"Fazendo pull do prompt: {prompt_hub_name}")

    try:
        prompt = hub.pull(prompt_hub_name)
        print("   ✓ Prompt carregado do LangSmith Hub")

        system_prompt = ""
        user_prompt = ""

        for message in prompt.messages:
            class_name = type(message).__name__
            if "System" in class_name:
                system_prompt = message.prompt.template
            elif "Human" in class_name:
                user_prompt = message.prompt.template

        data = {
            "bug_to_user_story_v1": {
                "description": "Prompt para converter relatos de bugs em User Stories",
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "version": "v1",
                "tags": ["bug-analysis", "user-story", "product-management"],
            }
        }

        if save_yaml(data, output_path):
            print(f"   ✓ Prompt salvo em: {output_path}")
            return True
        else:
            print(f"   ❌ Erro ao salvar prompt em: {output_path}")
            return False

    except Exception as e:
        print(f"   ❌ Erro ao fazer pull do prompt '{prompt_hub_name}': {e}")
        print("\n   Verifique:")
        print("   - LANGSMITH_API_KEY está configurada corretamente no .env")
        print("   - Você tem acesso ao workspace do LangSmith")
        print("   - Sua conexão com a internet está funcionando")
        return False


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    success = pull_prompts_from_langsmith()

    if success:
        print_section_header("PULL CONCLUÍDO COM SUCESSO")
        print("Próximos passos:")
        print("1. Analise o prompt em prompts/bug_to_user_story_v1.yml")
        print("2. Crie a versão otimizada em prompts/bug_to_user_story_v2.yml")
        print("3. Execute: python src/push_prompts.py")
        return 0
    else:
        print("\n❌ Falha ao fazer pull dos prompts. Verifique as credenciais no .env")
        return 1


if __name__ == "__main__":
    sys.exit(main())
