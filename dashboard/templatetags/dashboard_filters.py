import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)


@register.filter
def percentage(total, count):
    """Calculate percentage of count out of total"""
    if total == 0:
        return 0
    return int((count / total) * 100)


# Characters that must never appear raw inside an inline <script> block: `</`
# could close the tag early, and U+2028/U+2029 are valid JSON string content
# but line terminators in older JavaScript parsers.
_JSON_SCRIPT_REPLACEMENTS = (
    ('<', '\\u003C'),
    ('>', '\\u003E'),
    ('&', '\\u0026'),
    ('\u2028', '\\u2028'),
    ('\u2029', '\\u2029'),
)


@register.filter
def to_json(value):
    """Serialize ``value`` as a JavaScript literal safe to embed in an inline
    ``<script>`` block.

    Replacement for ``{{ value|safe }}``, which dumped a Python ``repr`` and
    disabled escaping entirely. This emits proper JSON (e.g. ``["Jan", "Feb"]``)
    with ``<``, ``>`` and ``&`` unicode-escaped, so a value that reaches the
    context from a user-editable model field (a court name, say) can no longer
    break out of the surrounding script. Unlike Django's ``json_script`` filter
    it returns the bare literal rather than a ``<script>`` tag, so it can be
    assigned directly to a ``var`` without rewriting the surrounding JS.
    """
    if isinstance(value, str):
        # A view may hand us an already-serialized payload (e.g. json.dumps
        # output). Pass it through instead of double-encoding it.
        try:
            json.loads(value)
        except (TypeError, ValueError):
            serialized = json.dumps(value)
        else:
            serialized = value
    else:
        serialized = json.dumps(value)

    for char, escape in _JSON_SCRIPT_REPLACEMENTS:
        serialized = serialized.replace(char, escape)
    return mark_safe(serialized)
