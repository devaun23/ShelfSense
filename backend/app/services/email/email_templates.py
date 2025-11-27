"""
Email template rendering using Jinja2.
Loads templates from app/templates/email directory.
"""

import os
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Template directory path
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "templates",
    "email"
)

# Jinja2 environment with autoescape for HTML
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)


def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """
    Render an email template with the given context.

    Args:
        template_name: Name of the template file (e.g., "welcome.html")
        context: Dictionary of variables to pass to the template

    Returns:
        Rendered HTML string
    """
    template = _env.get_template(template_name)
    return template.render(**context)
