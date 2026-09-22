"""FAQ, terms, privacy, media library, content versions, hero CMS.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import super_admin_required
from dashboard.models import ContentVersion
from dashboard.models import HeroSectionSettings
from dashboard.views.shared import _log_version
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render


@login_required
@super_admin_required
def content_version_list(request):
    """View content version history."""
    content_type = request.GET.get('content_type', '')
    versions = ContentVersion.objects.select_related('changed_by').all()

    if content_type:
        versions = versions.filter(content_type=content_type)

    versions = versions[:100]

    return render(request, 'admin/cms/versions/list.html', {
        'versions': versions,
        'selected_type': content_type,
        'content_type_choices': ContentVersion.CONTENT_TYPE_CHOICES,
        'page_title': 'Content Version History',
    })


# ============================================================================
# FAQ PAGE CMS
# ============================================================================


@login_required
@super_admin_required
def faq_cms_settings(request):
    """FAQ page CMS management."""
    from dashboard.models import FAQPageContent, FAQCategory, FAQItem

    content = FAQPageContent.objects.filter(is_active=True).order_by('section')
    categories = FAQCategory.objects.filter(is_active=True).order_by('display_order')
    items = FAQItem.objects.select_related('category').filter(is_active=True).order_by('display_order')

    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        if section and content_text:
            obj, created = FAQPageContent.objects.update_or_create(
                section=section,
                defaults={'content': content_text, 'is_active': True}
            )
            _log_version('homepage', f'FAQ Content - {section}', '', content_text, request.user)
            messages.success(request, 'FAQ content updated!')
        return redirect('super_admin_faq_cms')

    return render(request, 'admin/cms/faq/settings.html', {
        'content': content,
        'categories': categories,
        'items': items,
        'section_choices': FAQPageContent.SECTION_CHOICES,
        'page_title': 'FAQ Page CMS',
    })


@login_required
@super_admin_required
def faq_category_add(request):
    from dashboard.models import FAQCategory
    if request.method == 'POST':
        FAQCategory.objects.create(
            name=request.POST.get('name'),
            icon=request.POST.get('icon', 'fa-question-circle'),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'FAQ category created!')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/faq/category_form.html', {
        'category': None,
        'page_title': 'Add FAQ Category',
    })


@login_required
@super_admin_required
def faq_category_edit(request, cat_id):
    from dashboard.models import FAQCategory
    cat = get_object_or_404(FAQCategory, id=cat_id)
    if request.method == 'POST':
        cat.name = request.POST.get('name')
        cat.icon = request.POST.get('icon', 'fa-question-circle')
        cat.display_order = request.POST.get('display_order', 0)
        cat.is_active = request.POST.get('is_active') == 'on'
        cat.save()
        messages.success(request, 'FAQ category updated!')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/faq/category_form.html', {
        'category': cat,
        'page_title': 'Edit FAQ Category',
    })


@login_required
@super_admin_required
def faq_category_delete(request, cat_id):
    from dashboard.models import FAQCategory
    cat = get_object_or_404(FAQCategory, id=cat_id)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'FAQ category deleted.')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': cat,
        'cancel_url': 'super_admin_faq_cms',
    })


@login_required
@super_admin_required
def faq_item_add(request):
    from dashboard.models import FAQCategory, FAQItem
    if request.method == 'POST':
        category_id = request.POST.get('category')
        FAQItem.objects.create(
            category=get_object_or_404(FAQCategory, id=category_id),
            question=request.POST.get('question'),
            answer=request.POST.get('answer'),
            display_order=request.POST.get('display_order', 0),
        )
        messages.success(request, 'FAQ item created!')
        return redirect('super_admin_faq_cms')
    categories = FAQCategory.objects.filter(is_active=True).order_by('display_order')
    return render(request, 'admin/cms/faq/item_form.html', {
        'item': None,
        'categories': categories,
        'page_title': 'Add FAQ Item',
    })


@login_required
@super_admin_required
def faq_item_edit(request, item_id):
    from dashboard.models import FAQCategory, FAQItem
    item = get_object_or_404(FAQItem, id=item_id)
    if request.method == 'POST':
        category_id = request.POST.get('category')
        item.category = get_object_or_404(FAQCategory, id=category_id)
        item.question = request.POST.get('question')
        item.answer = request.POST.get('answer')
        item.display_order = request.POST.get('display_order', 0)
        item.is_active = request.POST.get('is_active') == 'on'
        item.save()
        messages.success(request, 'FAQ item updated!')
        return redirect('super_admin_faq_cms')
    categories = FAQCategory.objects.filter(is_active=True).order_by('display_order')
    return render(request, 'admin/cms/faq/item_form.html', {
        'item': item,
        'categories': categories,
        'page_title': 'Edit FAQ Item',
    })


@login_required
@super_admin_required
def faq_item_delete(request, item_id):
    from dashboard.models import FAQItem
    item = get_object_or_404(FAQItem, id=item_id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'FAQ item deleted.')
        return redirect('super_admin_faq_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': item,
        'cancel_url': 'super_admin_faq_cms',
    })


# ============================================================================
# TERMS OF SERVICE CMS
# ============================================================================


@login_required
@super_admin_required
def terms_cms_settings(request):
    """Terms of Service page CMS."""
    from dashboard.models import TermsContent, TermsSection
    content = TermsContent.objects.filter(is_active=True).order_by('section')
    sections = TermsSection.objects.filter(is_active=True).order_by('section_number')

    if request.method == 'POST' and request.POST.get('section'):
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        obj, created = TermsContent.objects.update_or_create(
            section=section,
            defaults={'content': content_text, 'is_active': True}
        )
        _log_version('homepage', f'Terms Content - {section}', '', content_text, request.user)
        messages.success(request, 'Terms content updated!')
        return redirect('super_admin_terms_cms')

    return render(request, 'admin/cms/terms/settings.html', {
        'content': content,
        'sections': sections,
        'section_choices': TermsContent.SECTION_CHOICES,
        'page_title': 'Terms of Service CMS',
    })


@login_required
@super_admin_required
def terms_section_add(request):
    from dashboard.models import TermsSection
    if request.method == 'POST':
        TermsSection.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            icon=request.POST.get('icon', 'fa-file-contract'),
            icon_color=request.POST.get('icon_color', 'primary'),
            section_number=request.POST.get('section_number', 1),
        )
        messages.success(request, 'Terms section created!')
        return redirect('super_admin_terms_cms')
    return render(request, 'admin/cms/terms/section_form.html', {
        'section': None,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Add Terms Section',
    })


@login_required
@super_admin_required
def terms_section_edit(request, section_id):
    from dashboard.models import TermsSection
    sec = get_object_or_404(TermsSection, id=section_id)
    if request.method == 'POST':
        sec.title = request.POST.get('title')
        sec.content = request.POST.get('content')
        sec.icon = request.POST.get('icon', 'fa-file-contract')
        sec.icon_color = request.POST.get('icon_color', 'primary')
        sec.section_number = request.POST.get('section_number', 1)
        sec.is_active = request.POST.get('is_active') == 'on'
        sec.save()
        messages.success(request, 'Terms section updated!')
        return redirect('super_admin_terms_cms')
    return render(request, 'admin/cms/terms/section_form.html', {
        'section': sec,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Terms Section',
    })


@login_required
@super_admin_required
def terms_section_delete(request, section_id):
    from dashboard.models import TermsSection
    sec = get_object_or_404(TermsSection, id=section_id)
    if request.method == 'POST':
        sec.delete()
        messages.success(request, 'Terms section deleted.')
        return redirect('super_admin_terms_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': sec,
        'cancel_url': 'super_admin_terms_cms',
    })


# ============================================================================
# PRIVACY POLICY CMS
# ============================================================================


@login_required
@super_admin_required
def privacy_cms_settings(request):
    """Privacy Policy page CMS."""
    from dashboard.models import PrivacyContent, PrivacySection
    content = PrivacyContent.objects.filter(is_active=True).order_by('section')
    sections = PrivacySection.objects.filter(is_active=True).order_by('section_number')

    if request.method == 'POST' and request.POST.get('section'):
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        obj, created = PrivacyContent.objects.update_or_create(
            section=section,
            defaults={'content': content_text, 'is_active': True}
        )
        _log_version('homepage', f'Privacy Content - {section}', '', content_text, request.user)
        messages.success(request, 'Privacy content updated!')
        return redirect('super_admin_privacy_cms')

    return render(request, 'admin/cms/privacy/settings.html', {
        'content': content,
        'sections': sections,
        'section_choices': PrivacyContent.SECTION_CHOICES,
        'page_title': 'Privacy Policy CMS',
    })


@login_required
@super_admin_required
def privacy_section_add(request):
    from dashboard.models import PrivacySection
    if request.method == 'POST':
        PrivacySection.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            icon=request.POST.get('icon', 'fa-shield-alt'),
            icon_color=request.POST.get('icon_color', 'primary'),
            section_number=request.POST.get('section_number', 1),
        )
        messages.success(request, 'Privacy section created!')
        return redirect('super_admin_privacy_cms')
    return render(request, 'admin/cms/privacy/section_form.html', {
        'section': None,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Add Privacy Section',
    })


@login_required
@super_admin_required
def privacy_section_edit(request, section_id):
    from dashboard.models import PrivacySection
    sec = get_object_or_404(PrivacySection, id=section_id)
    if request.method == 'POST':
        sec.title = request.POST.get('title')
        sec.content = request.POST.get('content')
        sec.icon = request.POST.get('icon', 'fa-shield-alt')
        sec.icon_color = request.POST.get('icon_color', 'primary')
        sec.section_number = request.POST.get('section_number', 1)
        sec.is_active = request.POST.get('is_active') == 'on'
        sec.save()
        messages.success(request, 'Privacy section updated!')
        return redirect('super_admin_privacy_cms')
    return render(request, 'admin/cms/privacy/section_form.html', {
        'section': sec,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Privacy Section',
    })


@login_required
@super_admin_required
def privacy_section_delete(request, section_id):
    from dashboard.models import PrivacySection
    sec = get_object_or_404(PrivacySection, id=section_id)
    if request.method == 'POST':
        sec.delete()
        messages.success(request, 'Privacy section deleted.')
        return redirect('super_admin_privacy_cms')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': sec,
        'cancel_url': 'super_admin_privacy_cms',
    })


# ============================================================================
# MEDIA LIBRARY
# ============================================================================


@login_required
@super_admin_required
def media_library_view(request):
    """Media library management page."""
    from dashboard.models import MediaLibrary
    media_type = request.GET.get('type', '')
    q = request.GET.get('q', '')
    media = MediaLibrary.objects.all().order_by('-created_at')

    if media_type:
        media = media.filter(file_type=media_type)
    if q:
        media = media.filter(title__icontains=q)

    return render(request, 'admin/cms/media/list.html', {
        'media': media,
        'media_type': media_type,
        'q': q,
        'page_title': 'Media Library',
    })


@login_required
@super_admin_required
def media_library_upload(request):
    """Upload media file."""
    from dashboard.models import MediaLibrary
    if request.method == 'POST':
        title = request.POST.get('title')
        file = request.FILES.get('file')
        alt_text = request.POST.get('alt_text', '')
        caption = request.POST.get('caption', '')

        if title and file:
            media = MediaLibrary.objects.create(
                title=title,
                file=file,
                alt_text=alt_text,
                caption=caption,
                uploaded_by=request.user,
            )
            messages.success(request, f'"{media.title}" uploaded successfully!')
            return redirect('super_admin_media_library')
        else:
            messages.error(request, 'Please provide a title and select a file.')

    return render(request, 'admin/cms/media/upload.html', {
        'page_title': 'Upload Media',
    })


@login_required
@super_admin_required
def media_library_edit(request, media_id):
    """Edit media library item."""
    from dashboard.models import MediaLibrary
    media = get_object_or_404(MediaLibrary, id=media_id)
    if request.method == 'POST':
        media.title = request.POST.get('title')
        media.alt_text = request.POST.get('alt_text', '')
        media.caption = request.POST.get('caption', '')
        media.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('file'):
            media.file = request.FILES['file']
        media.save()
        messages.success(request, 'Media item updated!')
        return redirect('super_admin_media_library')
    return render(request, 'admin/cms/media/edit.html', {
        'media': media,
        'page_title': 'Edit Media',
    })


@login_required
@super_admin_required
def media_library_delete(request, media_id):
    """Delete media library item."""
    from dashboard.models import MediaLibrary
    media = get_object_or_404(MediaLibrary, id=media_id)
    if request.method == 'POST':
        media.delete()
        messages.success(request, 'Media item deleted.')
        return redirect('super_admin_media_library')
    return render(request, 'admin/cms/confirm_delete.html', {
        'object': media,
        'cancel_url': 'super_admin_media_library',
    })


# ============================================================================
# HERO SECTION CMS
# ============================================================================


@login_required
@super_admin_required
def hero_section_settings(request):
    """Hero section settings management (singleton)."""
    settings, _ = HeroSectionSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        settings.background_type = request.POST.get('background_type', 'gradient')
        settings.solid_color = request.POST.get('solid_color', '#1a3a42')
        settings.gradient_start = request.POST.get('gradient_start', '#1a3a42')
        settings.gradient_end = request.POST.get('gradient_end', '#0f172a')
        settings.gradient_direction = request.POST.get('gradient_direction', '135deg')
        settings.overlay_color = request.POST.get('overlay_color', '#000000')
        try:
            settings.overlay_opacity = float(request.POST.get('overlay_opacity', 0.6))
        except ValueError:
            settings.overlay_opacity = 0.6
        settings.badge_text = request.POST.get('badge_text', '')
        settings.title = request.POST.get('title', 'Welcome to PickleSphere')
        settings.subtitle = request.POST.get('subtitle', '')
        settings.show_search_widget = request.POST.get('show_search_widget') == 'on'
        settings.min_height = request.POST.get('min_height', '90vh')
        settings.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('background_image'):
            settings.background_image = request.FILES['background_image']
        settings.save()
        _log_version('hero', 'Hero Section', '', '', request.user)
        messages.success(request, 'Hero section settings updated!')
        return redirect('super_admin_hero_cms')

    return render(request, 'admin/cms/hero/settings.html', {
        'settings': settings,
        'page_title': 'Hero Section CMS',
    })


@login_required
@super_admin_required
def hero_section_preview(request):
    """Return JSON hero preview data for live preview."""
    from django.http import JsonResponse
    settings, _ = HeroSectionSettings.objects.get_or_create(pk=1)
    return JsonResponse({
        'background_style': settings.get_background_style(),
        'badge_text': settings.badge_text,
        'title': settings.title,
        'subtitle': settings.subtitle,
        'show_search_widget': settings.show_search_widget,
        'min_height': settings.min_height,
    })


# ============================================================================
# WEBSITE BRANDING CMS
# ============================================================================
