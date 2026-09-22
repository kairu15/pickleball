"""
PickleSphere Utilities

Reusable mixins and base classes to reduce code duplication across the project.

Contents:
    - SoftDeleteMixin: Standardizes is_active soft-delete pattern
    - BaseAdminCRUDViewMixin: Reduces repetitive CRUD boilerplate in admin views
"""

from django.db import models
from django.shortcuts import redirect
from django.contrib import messages


# ============================================================================
# SoftDeleteMixin
# ============================================================================

class SoftDeleteMixin:
    """
    Mixin that standardizes the is_active / soft-delete pattern.

    To use, add `deleted_at = models.DateTimeField(null=True, blank=True)`
    to your model if you want timestamp tracking, or just rely on the
    existing `is_active` / `is_deleted` boolean fields.

    Usage:
        class MyModel(models.Model, SoftDeleteMixin):
            is_active = models.BooleanField(default=True)
            deleted_at = models.DateTimeField(null=True, blank=True)

        # my_model.soft_delete()  → sets is_active=False
        # my_model.restore()      → sets is_active=True
    """

    def soft_delete(self, using=None):
        """Mark the object as deleted (inactive) instead of removing it."""
        if not hasattr(self, 'is_active'):
            raise AttributeError(
                f"{self.__class__.__name__} must have an 'is_active' field "
                f"to use SoftDeleteMixin.soft_delete()"
            )
        from django.utils import timezone
        self.is_active = False
        update_fields = ['is_active']
        if hasattr(self, 'deleted_at'):
            self.deleted_at = timezone.now()
            update_fields.append('deleted_at')
        if hasattr(self, 'updated_at'):
            update_fields.append('updated_at')
        self.save(update_fields=update_fields, using=using)

    def restore(self, using=None):
        """Restore a soft-deleted object."""
        if not hasattr(self, 'is_active'):
            raise AttributeError(
                f"{self.__class__.__name__} must have an 'is_active' field "
                f"to use SoftDeleteMixin.restore()"
            )
        self.is_active = True
        update_fields = ['is_active']
        if hasattr(self, 'deleted_at'):
            self.deleted_at = None
            update_fields.append('deleted_at')
        if hasattr(self, 'updated_at'):
            update_fields.append('updated_at')
        self.save(update_fields=update_fields, using=using)

    @property
    def is_deleted(self):
        """Convenience property that checks if the object is inactive."""
        return not getattr(self, 'is_active', True)


# ============================================================================
# Base Admin CRUD Helpers
# ============================================================================

def admin_crud_create(request, model_class, form_class, redirect_url, 
                      template_name, extra_context=None, commit_hook=None,
                      success_message=None, title='Create'):
    """
    Handles the create flow for a simple admin CRUD pattern.

    Args:
        request: Django request
        model_class: The Django model
        form_class: The Django ModelForm
        redirect_url: URL name to redirect to on success
        template_name: Template to render
        extra_context: Additional template context dict
        commit_hook: Optional callable(form, object) called after save
        success_message: Custom success message
        title: Page title
    """
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES or None)
        if form.is_valid():
            obj = form.save()
            if commit_hook:
                commit_hook(form, obj)
            messages.success(
                request,
                success_message or f'{model_class._meta.verbose_name} created successfully!'
            )
            return redirect(redirect_url)
    else:
        form = form_class()

    context = {
        'form': form,
        'page_title': title,
        'is_create': True,
    }
    if extra_context:
        context.update(extra_context)
    return render(request, template_name, context)


def admin_crud_update(request, model_class, form_class, object_id, redirect_url,
                      template_name, extra_context=None, commit_hook=None,
                      success_message=None, title='Edit', queryset=None):
    """
    Handles the update flow for a simple admin CRUD pattern.

    Args:
        request: Django request
        model_class: The Django model
        form_class: The Django ModelForm
        object_id: Primary key of object to edit
        redirect_url: URL name to redirect to on success
        template_name: Template to render
        extra_context: Additional template context dict
        commit_hook: Optional callable(form, object) called after save
        success_message: Custom success message
        title: Page title
        queryset: Optional custom queryset for object lookup (for org-scoping)
    """
    from django.shortcuts import get_object_or_404
    qs = queryset if queryset is not None else model_class.objects.all()
    obj = get_object_or_404(qs, pk=object_id)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES or None, instance=obj)
        if form.is_valid():
            obj = form.save()
            if commit_hook:
                commit_hook(form, obj)
            messages.success(
                request,
                success_message or f'{model_class._meta.verbose_name} updated successfully!'
            )
            return redirect(redirect_url)
    else:
        form = form_class(instance=obj)

    context = {
        'form': form,
        'object': obj,
        'page_title': title,
        'is_create': False,
    }
    if extra_context:
        context.update(extra_context)
    return render(request, template_name, context)


def admin_crud_delete(request, model_class, object_id, redirect_url,
                      success_message=None, queryset=None):
    """
    Handles the delete flow for a simple admin CRUD pattern using soft-delete.

    Args:
        request: Django request (must be POST)
        model_class: The Django model
        object_id: Primary key of object to delete
        redirect_url: URL name to redirect to on success
        success_message: Custom success message
        queryset: Optional custom queryset for object lookup
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect(redirect_url)

    from django.shortcuts import get_object_or_404
    qs = queryset if queryset is not None else model_class.objects.all()
    obj = get_object_or_404(qs, pk=object_id)

    # Try soft-delete first; fall back to hard delete if no is_active field
    if hasattr(obj, 'is_active') and hasattr(obj, 'soft_delete'):
        obj.soft_delete()
    elif hasattr(obj, 'is_active'):
        obj.is_active = False
        obj.save(update_fields=['is_active'])
    else:
        obj.delete()

    messages.success(
        request,
        success_message or f'{model_class._meta.verbose_name} deleted successfully!'
    )
    return redirect(redirect_url)


from django.shortcuts import render
