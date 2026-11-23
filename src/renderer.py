"""
Markdown and Jinja2 rendering engine.
Merges templates with context variables and compiles markdown to styled HTML.
"""
import re
from typing import Tuple, Dict, Any

try:
    import jinja2
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

def render_email(subject_tmpl: str, body_md_tmpl: str, context: Dict[str, Any]) -> Tuple[str, str]:
    """
    Renders subject and markdown body with context dictionary,
    converting markdown to sanitized HTML with an optional unsubscribe footer.
    """
    if JINJA_AVAILABLE:
        env = jinja2.Environment(autoescape=True)
        subj = env.from_string(subject_tmpl).render(**context)
        body_md = env.from_string(body_md_tmpl).render(**context)
    else:
        # Fallback substitution if jinja2 is not installed
        subj = subject_tmpl
        body_md = body_md_tmpl
        for k, v in context.items():
            subj = subj.replace(f"{{{{ {k} }}}}", str(v)).replace(f"{{{{{k}}}}}", str(v))
            body_md = body_md.replace(f"{{{{ {k} }}}}", str(v)).replace(f"{{{{{k}}}}}", str(v))

    if MARKDOWN_AVAILABLE:
        html = markdown.markdown(body_md, extensions=["extra"])
    else:
        # Simple markdown to HTML fallback (bold, paragraphs, links)
        html_formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', body_md)
        html_formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html_formatted)
        paragraphs = html_formatted.split("\n\n")
        html = "".join([f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip()])

    # Professional email footer & unsubscribe banner
    footer = (
        '<hr style="border: none; border-top: 1px solid #e2e8f0; margin-top: 24px; opacity: 0.6;">'
        '<div style="font-size: 11px; color: #718096; line-height: 1.5; text-align: center;">'
        'This is an automated notification from the Email Automation &amp; Reminder System.<br>'
        'To update your notification preferences or unsubscribe, reply with <strong>STOP</strong>.'
        '</div>'
    )
    return subj, html + footer
