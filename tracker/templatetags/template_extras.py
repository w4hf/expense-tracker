# tracker/templatetags/template_extras.py
from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)

# Create an empty __init__.py in tracker/templatetags/ if it doesn't exist:
# tracker/templatetags/__init__.py
