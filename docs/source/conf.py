# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.abspath("../../src"))


pyproject: dict[str, Any] = tomllib.loads(
    Path("../../pyproject.toml").read_text(encoding="utf-8")
)
project: str = pyproject["project"]["name"]
version: str = pyproject["project"]["version"]

# Extract authors as "Name <email>" format
authors = pyproject["project"].get("authors", [])
author_strings = [
    f'{a["name"]} <{a["email"]}>' if "email" in a else a["name"] for a in authors
]

# Join into single author string (as expected by Sphinx)
author: str = ", ".join(author_strings)
copyright = "2025, Roland Axel Richter"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions: list[str] = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

templates_path: list[str] = ["_templates"]
exclude_patterns = []

# autodoc settings
autodoc_member_order = "bysource"
autodoc_default_flags: list[str] = [
    "members",
    "undoc-members",
    "show-inheritance",
    "inherited-members",
    "private-members",
    "special-members",
    "exclude-members=__weakref__,__dict__,__module__,__init_subclass__,__new__,__class__",
]

# Add this to handle line breaks
napoleon_google_docstring = True  # Use Google-style docstrings
napoleon_numpy_docstring = False  # Optionally use NumPy-style docstrings

autodoc_typehints = "both"  # Show type hints in the description
autodoc_typehints_format = "short"  # Use short format for type hints
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = ["_static"]
