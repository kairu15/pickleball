from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def notification_url(context, url_name, *args, **kwargs):
    """
    Returns the role-appropriate URL for notification routes.
    
    Usage: {% notification_url 'notification_list' %}
           {% notification_url 'notification_detail' notification.id %}
    
    For a regular user, uses the base name as-is.
    For staff, prepends 'staff_' prefix.
    For super admin, prepends 'super_admin_' prefix.
    """
    request = context.get('request')
    user = request.user if request and request.user.is_authenticated else None

    if user and user.is_super_admin():
        prefixed = f'super_admin_{url_name}'
    elif user and user.is_staff_member():
        prefixed = f'staff_{url_name}'
    else:
        prefixed = url_name

    return reverse(prefixed, args=args, kwargs=kwargs)
