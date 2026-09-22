"""Contact page CMS.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import admin_required
from dashboard.models import BusinessHour
from dashboard.models import ContactContent
from dashboard.models import ContactFAQ
from dashboard.models import ContactInfo as CI
from dashboard.models import SocialLink
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render


@login_required
@admin_required
def contact_management(request):
    """Contact page content management"""
    
    
    content = ContactContent.objects.filter(is_active=True).order_by('section')
    contact_info = CI.objects.first()
    business_hours = BusinessHour.objects.all().order_by('display_order')
    faqs = ContactFAQ.objects.all().order_by('display_order')
    social_links = SocialLink.objects.all().order_by('display_order')
    
    context = {
        'content': content,
        'contact_info': contact_info,
        'business_hours': business_hours,
        'faqs': faqs,
        'social_links': social_links,
        'page_title': 'Contact Page Management'
    }
    return render(request, 'admin/contact/contact_management.html', context)


@login_required
@admin_required
def contact_edit_content(request, content_id=None):
    """Edit or create contact page content"""
    
    
    content_item = None
    if content_id:
        content_item = get_object_or_404(ContactContent, id=content_id)
    
    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        is_active = request.POST.get('is_active') == 'on'
        
        if content_item:
            content_item.section = section
            content_item.content = content_text
            content_item.is_active = is_active
            content_item.save()
            messages.success(request, 'Content updated successfully!')
        else:
            ContactContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Content created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'content_item': content_item,
        'section_choices': ContactContent.SECTION_CHOICES,
        'page_title': 'Edit Contact Content' if content_item else 'New Contact Content'
    }
    return render(request, 'admin/contact/contact_edit_content.html', context)


@login_required
@admin_required
def contact_delete_content(request, content_id):
    """Delete contact content"""
    
    content = get_object_or_404(ContactContent, id=content_id)
    content.delete()
    messages.success(request, 'Content deleted successfully!')
    return redirect('super_admin_contact')


@login_required
@admin_required
def contact_edit_info(request):
    """Edit contact information"""
    
    
    contact_info = CI.objects.first()
    
    if request.method == 'POST':
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        city_country = request.POST.get('city_country')
        google_maps_url = request.POST.get('google_maps_url', '')
        
        if contact_info:
            contact_info.phone = phone
            contact_info.email = email
            contact_info.address = address
            contact_info.city_country = city_country
            contact_info.google_maps_url = google_maps_url
            contact_info.save()
            messages.success(request, 'Contact information updated successfully!')
        else:
            CI.objects.create(
                phone=phone,
                email=email,
                address=address,
                city_country=city_country,
                google_maps_url=google_maps_url
            )
            messages.success(request, 'Contact information created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'contact_info': contact_info,
        'page_title': 'Edit Contact Information'
    }
    return render(request, 'admin/contact/contact_edit_info.html', context)


@login_required
@admin_required
def contact_edit_business_hour(request, hour_id=None):
    """Edit or create business hour"""
    
    
    hour = None
    if hour_id:
        hour = get_object_or_404(BusinessHour, id=hour_id)
    
    if request.method == 'POST':
        day_range = request.POST.get('day_range')
        hours = request.POST.get('hours')
        icon_color = request.POST.get('icon_color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if hour:
            hour.day_range = day_range
            hour.hours = hours
            hour.icon_color = icon_color
            hour.is_active = is_active
            hour.display_order = display_order
            hour.save()
            messages.success(request, 'Business hour updated successfully!')
        else:
            BusinessHour.objects.create(
                day_range=day_range,
                hours=hours,
                icon_color=icon_color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Business hour created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'hour': hour,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Business Hour' if hour else 'New Business Hour'
    }
    return render(request, 'admin/contact/contact_edit_business_hour.html', context)


@login_required
@admin_required
def contact_delete_business_hour(request, hour_id):
    """Delete business hour"""
    
    hour = get_object_or_404(BusinessHour, id=hour_id)
    hour.delete()
    messages.success(request, 'Business hour deleted successfully!')
    return redirect('super_admin_contact')


@login_required
@admin_required
def contact_edit_faq(request, faq_id=None):
    """Edit or create contact FAQ"""
    
    
    faq = None
    if faq_id:
        faq = get_object_or_404(ContactFAQ, id=faq_id)
    
    if request.method == 'POST':
        question = request.POST.get('question')
        answer = request.POST.get('answer')
        icon_color = request.POST.get('icon_color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if faq:
            faq.question = question
            faq.answer = answer
            faq.icon_color = icon_color
            faq.is_active = is_active
            faq.display_order = display_order
            faq.save()
            messages.success(request, 'FAQ updated successfully!')
        else:
            ContactFAQ.objects.create(
                question=question,
                answer=answer,
                icon_color=icon_color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'FAQ created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'faq': faq,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Contact FAQ' if faq else 'New Contact FAQ'
    }
    return render(request, 'admin/contact/contact_edit_faq.html', context)


@login_required
@admin_required
def contact_delete_faq(request, faq_id):
    """Delete contact FAQ"""
    
    faq = get_object_or_404(ContactFAQ, id=faq_id)
    faq.delete()
    messages.success(request, 'FAQ deleted successfully!')
    return redirect('super_admin_contact')


@login_required
@admin_required
def contact_edit_social_link(request, link_id=None):
    """Edit or create social link"""
    
    
    link = None
    if link_id:
        link = get_object_or_404(SocialLink, id=link_id)
    
    if request.method == 'POST':
        platform = request.POST.get('platform')
        url = request.POST.get('url')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if link:
            link.platform = platform
            link.url = url
            link.is_active = is_active
            link.display_order = display_order
            link.save()
            messages.success(request, 'Social link updated successfully!')
        else:
            SocialLink.objects.create(
                platform=platform,
                url=url,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Social link created successfully!')
        
        return redirect('super_admin_contact')
    
    context = {
        'link': link,
        'platform_choices': SocialLink._meta.get_field('platform').choices,
        'page_title': 'Edit Social Link' if link else 'New Social Link'
    }
    return render(request, 'admin/contact/contact_edit_social_link.html', context)


@login_required
@admin_required
def contact_delete_social_link(request, link_id):
    """Delete social link"""
    
    link = get_object_or_404(SocialLink, id=link_id)
    link.delete()
    messages.success(request, 'Social link deleted successfully!')
    return redirect('super_admin_contact')
