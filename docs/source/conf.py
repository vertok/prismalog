# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import re

sys.path.insert(0, os.path.abspath('../..'))

# Read version from pyproject.toml
with open(os.path.join(os.path.dirname(__file__), '..', '..', 'pyproject.toml'), 'r') as f:
    content = f.read()
    version = re.search(r'version = "(.*?)"', content).group(1)

# Set both version and release
release = version

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'prismalog'
copyright = '2025, Alexey Obukhov'
author = 'Alexey Obukhov'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',
    'sphinx_design',
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_with_keys': True,
    'logo_only': False,
    'style_nav_header_background': '#2980b9',
}

html_static_path = ['_static']

# Add custom CSS
html_css_files = [
    'custom.css',
]

# Add a logo if you have one
html_logo = "_static/prismalog_logo.png"  # Create or add your logo
html_favicon = "_static/favicon.ico"  # Add a favicon

# Add GitHub links
html_context = {
    "display_github": True,
    "github_user": "vertok",  # Replace with your GitHub username
    "github_repo": "prismalog",  # Replace with your GitHub repo name
    "github_version": "main",  # Replace with your GitHub branch
    "conf_py_path": "/docs/source/",
    'version': release,
    'display_version': True,
}

# -- Intersphinx mapping -----------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# -- Autodoc settings --------------------------------------------------------
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_default_options = {
    'members': True,
    'show-inheritance': True,
    'undoc-members': True,
}

# -- Napoleon settings -------------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False

# Add HTML title
html_title = f"prismalog {release}"
