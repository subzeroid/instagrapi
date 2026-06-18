import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TYPES_SOURCE = ROOT / "instagrapi" / "types.py"
MODEL_REFERENCE = ROOT / "docs" / "usage-guide" / "types.md"
MKDOCS_CONFIG = ROOT / "mkdocs.yml"


def _public_type_models() -> list[str]:
    tree = ast.parse(TYPES_SOURCE.read_text())
    bases_by_class = {
        node.name: [base.id if isinstance(base, ast.Name) else getattr(base, "attr", "") for base in node.bases]
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }

    def is_type_model(class_name: str) -> bool:
        bases = bases_by_class[class_name]
        return "TypesBaseModel" in bases or any(base in bases_by_class and is_type_model(base) for base in bases)

    return sorted(name for name in bases_by_class if name != "TypesBaseModel" and is_type_model(name))


def test_model_reference_lists_every_public_type_model():
    reference = MODEL_REFERENCE.read_text()
    missing = [name for name in _public_type_models() if f"::: instagrapi.types.{name}" not in reference]

    assert missing == []


def test_model_reference_is_linked_from_docs_navigation():
    mkdocs_config = MKDOCS_CONFIG.read_text()
    interactions = (ROOT / "docs" / "usage-guide" / "interactions.md").read_text()
    index = (ROOT / "docs" / "index.md").read_text()

    assert "Types: usage-guide/types.md" in mkdocs_config
    assert "[Types](types.md)" in interactions
    assert "[Types](usage-guide/types.md)" in index
