"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture
def prompt_data():
    """Carrega e retorna os dados do prompt v2."""
    data = load_prompts(str(PROMPT_FILE))
    assert "bug_to_user_story_v2" in data, "Chave 'bug_to_user_story_v2' não encontrada no YAML"
    return data["bug_to_user_story_v2"]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data, "Campo 'system_prompt' não encontrado"
        assert prompt_data["system_prompt"] is not None, "Campo 'system_prompt' é None"
        assert prompt_data["system_prompt"].strip() != "", "Campo 'system_prompt' está vazio"

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: 'Você é um Product Manager')."""
        system_prompt = prompt_data["system_prompt"].lower()
        role_keywords = [
            "você é um",
            "você é uma",
            "você é o",
            "você é a",
            "product manager",
            "especialista",
            "assistente especializado",
        ]
        found = any(kw in system_prompt for kw in role_keywords)
        assert found, (
            "O system_prompt deve definir uma persona/role. "
            f"Palavras-chave esperadas (qualquer uma): {role_keywords}"
        )

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt_data["system_prompt"].lower()
        format_keywords = [
            "markdown",
            "user story",
            "como um",
            "critérios de aceitação",
            "dado que",
        ]
        found = any(kw in system_prompt for kw in format_keywords)
        assert found, (
            "O prompt deve mencionar o formato esperado de saída. "
            f"Palavras-chave esperadas (qualquer uma): {format_keywords}"
        )

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt_data["system_prompt"]
        # Procura por padrões como "Exemplo 1", "Exemplo 2", "Example 1", etc.
        examples = re.findall(r'(?i)exemplo\s+\d+', system_prompt)
        assert len(examples) >= 2, (
            f"O prompt deve conter pelo menos 2 exemplos numerados (ex: 'Exemplo 1', 'Exemplo 2'). "
            f"Encontrados: {len(examples)} — {examples}"
        )

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum [TODO] no texto."""
        fields_to_check = ["system_prompt", "user_prompt", "description"]
        full_text = ""
        for field in fields_to_check:
            value = prompt_data.get(field, "")
            if value:
                full_text += str(value)

        assert "[TODO]" not in full_text, (
            "O prompt contém '[TODO]' não preenchido. "
            "Revise os campos system_prompt, user_prompt e description."
        )

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list), (
            "O campo 'techniques_applied' deve ser uma lista"
        )
        assert len(techniques) >= 2, (
            f"Mínimo de 2 técnicas requeridas em 'techniques_applied', "
            f"encontradas: {len(techniques)} — {techniques}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
