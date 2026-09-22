"""Pricing page CMS.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import admin_required
from dashboard.models import PricingContent
from dashboard.models import PricingFAQ
from dashboard.models import PricingTier
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
import json


@login_required
@admin_required
def pricing_management(request):
    """Pricing page content management"""
    
    
    content = PricingContent.objects.filter(is_active=True).order_by('section')
    tiers = PricingTier.objects.all().order_by('display_order', 'price')
    faqs = PricingFAQ.objects.all().order_by('display_order')
    
    context = {
        'content': content,
        'tiers': tiers,
        'faqs': faqs,
        'page_title': 'Pricing Page Management'
    }
    return render(request, 'admin/pricing/pricing_management.html', context)


@login_required
@admin_required
def pricing_edit_content(request, content_id=None):
    """Edit or create pricing page content"""
    
    
    content_item = None
    if content_id:
        content_item = get_object_or_404(PricingContent, id=content_id)
    
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
            PricingContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Content created successfully!')
        
        return redirect('super_admin_pricing')
    
    context = {
        'content_item': content_item,
        'section_choices': PricingContent.SECTION_CHOICES,
        'page_title': 'Edit Pricing Content' if content_item else 'New Pricing Content'
    }
    return render(request, 'admin/pricing/pricing_edit_content.html', context)


@login_required
@admin_required
def pricing_delete_content(request, content_id):
    """Delete pricing content"""
    
    content = get_object_or_404(PricingContent, id=content_id)
    content.delete()
    messages.success(request, 'Content deleted successfully!')
    return redirect('super_admin_pricing')


@login_required
@admin_required
def pricing_edit_tier(request, tier_id=None):
    """Edit or create pricing tier"""
    
    
    tier = None
    if tier_id:
        tier = get_object_or_404(PricingTier, id=tier_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price', 0)
        period = request.POST.get('period', '')
        description = request.POST.get('description', '')
        features_json = request.POST.get('features', '[]')
        is_recommended = request.POST.get('is_recommended') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        try:
            features = json.loads(features_json)
        except json.JSONDecodeError:
            features = []
        
        if tier:
            tier.name = name
            tier.price = price
            tier.period = period
            tier.description = description
            tier.features = features
            tier.is_recommended = is_recommended
            tier.is_active = is_active
            tier.display_order = display_order
            tier.save()
            messages.success(request, 'Pricing tier updated successfully!')
        else:
            PricingTier.objects.create(
                name=name,
                price=price,
                period=period,
                description=description,
                features=features,
                is_recommended=is_recommended,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Pricing tier created successfully!')
        
        return redirect('super_admin_pricing')
    
    context = {
        'tier': tier,
        'page_title': 'Edit Pricing Tier' if tier else 'New Pricing Tier'
    }
    return render(request, 'admin/pricing/pricing_edit_tier.html', context)


@login_required
@admin_required
def pricing_delete_tier(request, tier_id):
    """Delete pricing tier"""
    
    tier = get_object_or_404(PricingTier, id=tier_id)
    tier.delete()
    messages.success(request, 'Pricing tier deleted successfully!')
    return redirect('super_admin_pricing')


@login_required
@admin_required
def pricing_edit_faq(request, faq_id=None):
    """Edit or create pricing FAQ"""
    
    
    faq = None
    if faq_id:
        faq = get_object_or_404(PricingFAQ, id=faq_id)
    
    if request.method == 'POST':
        question = request.POST.get('question')
        answer = request.POST.get('answer')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if faq:
            faq.question = question
            faq.answer = answer
            faq.is_active = is_active
            faq.display_order = display_order
            faq.save()
            messages.success(request, 'FAQ updated successfully!')
        else:
            PricingFAQ.objects.create(
                question=question,
                answer=answer,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'FAQ created successfully!')
        
        return redirect('super_admin_pricing')
    
    context = {
        'faq': faq,
        'page_title': 'Edit Pricing FAQ' if faq else 'New Pricing FAQ'
    }
    return render(request, 'admin/pricing/pricing_edit_faq.html', context)


@login_required
@admin_required
def pricing_delete_faq(request, faq_id):
    """Delete pricing FAQ"""
    
    faq = get_object_or_404(PricingFAQ, id=faq_id)
    faq.delete()
    messages.success(request, 'FAQ deleted successfully!')
    return redirect('super_admin_pricing')


# ============================================================================
# ABOUT PAGE MANAGEMENT
# ============================================================================
