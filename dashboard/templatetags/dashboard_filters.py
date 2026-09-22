from django import template

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
