from django.template import Library

register = Library()


@register.simple_tag(takes_context=True)
def update_context(context, new_context):
    """
    Updates the current context with the given context dict
    """
    context.update(new_context)
    return ''
