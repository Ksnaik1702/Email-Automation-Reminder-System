"""
Templating engine: Loads HTML and text templates, replaces placeholders,
and produces personalized email subjects and bodies.
"""
from pathlib import Path
from typing import Dict, Any, Tuple
import re
from src.logger import logger
from src.config import TEMPLATES_DIR

try:
    from jinja2 import Template as JinjaTemplate
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False

def load_template_file(template_name: str) -> str:
    """Reads template file from templates directory."""
    path = TEMPLATES_DIR / template_name
    if not path.exists():
        logger.error(f"Template not found: {path}")
        raise FileNotFoundError(f"Template '{template_name}' not found at {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def simple_substitute(content: str, context: Dict[str, Any]) -> str:
    """Fallback variable replacement supporting {{ var }} and {var}."""
    rendered = content
    for key, val in context.items():
        val_str = str(val) if val is not None else ""
        rendered = rendered.replace(f"{{{{ {key} }}}}", val_str)
        rendered = rendered.replace(f"{{{{{key}}}}}", val_str)
        rendered = rendered.replace(f"{{{key}}}", val_str)
    return rendered

def render_email_content(template_name: str, context: Dict[str, Any]) -> Tuple[str, str]:
    """
    Renders personalized subject and HTML content based on job context.
    Returns: (subject, html_body)
    """
    raw_template = load_template_file(template_name)

    if JINJA_AVAILABLE:
        try:
            jinja_tmpl = JinjaTemplate(raw_template)
            html_body = jinja_tmpl.render(**context)
        except Exception as e:
            logger.warning(f"Jinja rendering warning ({e}). Falling back to simple substitution.")
            html_body = simple_substitute(raw_template, context)
    else:
        html_body = simple_substitute(raw_template, context)

    # Dynamic personalized subject line based on reminder category and title
    title = context.get("title", "Important Update")
    category = context.get("category", "Reminder")
    priority = context.get("priority", "Normal")
    
    prefix = "🚨 [URGENT]" if priority.lower() == "critical" else "🔔"
    subject = f"{prefix} [{category}] {title} - {context.get('name', 'Valued Member')}"

    return subject, html_body
