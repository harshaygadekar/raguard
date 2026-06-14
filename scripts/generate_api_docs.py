import inspect
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from raguard.adapters.fastapi import RAGuardFastAPIMiddleware
from raguard.adapters.langchain import RAGuardLangChainCallback
from raguard.adapters.llamaindex import RAGuardLlamaIndexPostprocessor
from raguard.config import RAGuardConfig
from raguard.core import CanaryMiddleware


def get_class_doc(cls):
    doc = f"## `class {cls.__name__}`\n\n"
    if cls.__doc__:
        doc += f"{inspect.cleandoc(cls.__doc__)}\n\n"

    # Methods
    methods = inspect.getmembers(cls, predicate=inspect.isfunction)
    if methods:
        doc += "### Methods\n\n"
        for name, func in methods:
            if name.startswith("_") and name != "__init__":
                continue
            sig = inspect.signature(func)
            doc += f"#### `{name}{sig}`\n\n"
            if func.__doc__:
                doc += f"{inspect.cleandoc(func.__doc__)}\n\n"
    return doc


output = """# API Reference

Auto-generated API documentation from codebase docstrings.

"""

output += get_class_doc(CanaryMiddleware)
output += "\n---\n\n"
output += get_class_doc(RAGuardConfig)
output += "\n---\n\n"
output += get_class_doc(RAGuardLangChainCallback)
output += "\n---\n\n"
output += get_class_doc(RAGuardLlamaIndexPostprocessor)
output += "\n---\n\n"
output += get_class_doc(RAGuardFastAPIMiddleware)

docs_dir = Path(__file__).resolve().parent.parent / "docs"
docs_dir.mkdir(exist_ok=True)
with open(docs_dir / "api.md", "w", encoding="utf-8") as f:
    f.write(output)
print("API docs generated at docs/api.md")
