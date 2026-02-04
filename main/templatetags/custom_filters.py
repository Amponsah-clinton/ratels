from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key.
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return []
    return dictionary.get(key, [])


@register.filter
def strip_newlines(value):
    """
    Remove newline codes (\\n, \\r\\n, and actual newline chars) and replace with space.
    Usage: {{ text|strip_newlines }}
    """
    if value is None:
        return ""
    import re
    s = str(value)
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    s = s.replace("\\n", " ").replace("\\r", " ")
    s = re.sub(r"\s+", " ", s)  # collapse multiple spaces
    return s.strip()
