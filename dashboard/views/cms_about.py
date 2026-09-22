"""About page CMS.

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import admin_required
from dashboard.models import AboutContent
from dashboard.models import AboutGalleryImage
from dashboard.models import Facility
from dashboard.models import Milestone
from dashboard.models import TeamMember
from dashboard.models import WhyChooseItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render


@login_required
@admin_required
def about_management(request):
    """About page content management"""


    content = AboutContent.objects.filter(is_active=True).order_by('section')
    milestones = Milestone.objects.all().order_by('display_order', 'year')
    team_members = TeamMember.objects.all().order_by('display_order')
    facilities = Facility.objects.all().order_by('display_order')
    why_items = WhyChooseItem.objects.all().order_by('display_order')
    gallery_images = AboutGalleryImage.objects.filter(is_active=True).order_by('display_order')

    context = {
        'content': content,
        'milestones': milestones,
        'team_members': team_members,
        'facilities': facilities,
        'why_items': why_items,
        'gallery_images': gallery_images,
        'page_title': 'About Page Management'
    }
    return render(request, 'admin/about/about_management.html', context)


@login_required
@admin_required
def about_edit_content(request, content_id=None):
    """Edit or create about page content"""
    
    
    content_item = None
    if content_id:
        content_item = get_object_or_404(AboutContent, id=content_id)
    
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
            AboutContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Content created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'content_item': content_item,
        'section_choices': AboutContent.SECTION_CHOICES,
        'page_title': 'Edit About Content' if content_item else 'New About Content'
    }
    return render(request, 'admin/about/about_edit_content.html', context)


@login_required
@admin_required
def about_delete_content(request, content_id):
    """Delete about content"""
    
    content = get_object_or_404(AboutContent, id=content_id)
    content.delete()
    messages.success(request, 'Content deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_milestone(request, milestone_id=None):
    """Edit or create milestone"""
    
    
    milestone = None
    if milestone_id:
        milestone = get_object_or_404(Milestone, id=milestone_id)
    
    if request.method == 'POST':
        year = request.POST.get('year')
        title = request.POST.get('title')
        description = request.POST.get('description')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if milestone:
            milestone.year = year
            milestone.title = title
            milestone.description = description
            milestone.color = color
            milestone.is_active = is_active
            milestone.display_order = display_order
            milestone.save()
            messages.success(request, 'Milestone updated successfully!')
        else:
            Milestone.objects.create(
                year=year,
                title=title,
                description=description,
                color=color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Milestone created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'milestone': milestone,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Milestone' if milestone else 'New Milestone'
    }
    return render(request, 'admin/about/about_edit_milestone.html', context)


@login_required
@admin_required
def about_delete_milestone(request, milestone_id):
    """Delete milestone"""
    
    milestone = get_object_or_404(Milestone, id=milestone_id)
    milestone.delete()
    messages.success(request, 'Milestone deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_team_member(request, member_id=None):
    """Edit or create team member"""
    
    
    member = None
    if member_id:
        member = get_object_or_404(TeamMember, id=member_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        role = request.POST.get('role')
        bio = request.POST.get('bio')
        linkedin_url = request.POST.get('linkedin_url', '')
        twitter_url = request.POST.get('twitter_url', '')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if member:
            member.name = name
            member.role = role
            member.bio = bio
            member.linkedin_url = linkedin_url
            member.twitter_url = twitter_url
            member.color = color
            member.is_active = is_active
            member.display_order = display_order
            if request.FILES.get('photo'):
                member.photo = request.FILES['photo']
            member.save()
            messages.success(request, 'Team member updated successfully!')
        else:
            TeamMember.objects.create(
                name=name,
                role=role,
                bio=bio,
                linkedin_url=linkedin_url,
                twitter_url=twitter_url,
                color=color,
                is_active=is_active,
                display_order=display_order,
                photo=request.FILES.get('photo')
            )
            messages.success(request, 'Team member created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'member': member,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Team Member' if member else 'New Team Member'
    }
    return render(request, 'admin/about/about_edit_team_member.html', context)


@login_required
@admin_required
def about_delete_team_member(request, member_id):
    """Delete team member"""
    
    member = get_object_or_404(TeamMember, id=member_id)
    member.delete()
    messages.success(request, 'Team member deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_facility(request, facility_id=None):
    """Edit or create facility"""
    
    
    facility = None
    if facility_id:
        facility = get_object_or_404(Facility, id=facility_id)
    
    if request.method == 'POST':
        icon = request.POST.get('icon')
        title = request.POST.get('title')
        description = request.POST.get('description')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if facility:
            facility.icon = icon
            facility.title = title
            facility.description = description
            facility.color = color
            facility.is_active = is_active
            facility.display_order = display_order
            facility.save()
            messages.success(request, 'Facility updated successfully!')
        else:
            Facility.objects.create(
                icon=icon,
                title=title,
                description=description,
                color=color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Facility created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'facility': facility,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger'), ('purple', 'Purple')],
        'page_title': 'Edit Facility' if facility else 'New Facility'
    }
    return render(request, 'admin/about/about_edit_facility.html', context)


@login_required
@admin_required
def about_delete_facility(request, facility_id):
    """Delete facility"""
    
    facility = get_object_or_404(Facility, id=facility_id)
    facility.delete()
    messages.success(request, 'Facility deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_edit_why_item(request, item_id=None):
    """Edit or create why choose item"""
    
    
    item = None
    if item_id:
        item = get_object_or_404(WhyChooseItem, id=item_id)
    
    if request.method == 'POST':
        icon = request.POST.get('icon')
        title = request.POST.get('title')
        description = request.POST.get('description')
        color = request.POST.get('color', 'primary')
        is_active = request.POST.get('is_active') == 'on'
        display_order = request.POST.get('display_order', 0)
        
        if item:
            item.icon = icon
            item.title = title
            item.description = description
            item.color = color
            item.is_active = is_active
            item.display_order = display_order
            item.save()
            messages.success(request, 'Item updated successfully!')
        else:
            WhyChooseItem.objects.create(
                icon=icon,
                title=title,
                description=description,
                color=color,
                is_active=is_active,
                display_order=display_order
            )
            messages.success(request, 'Item created successfully!')
        
        return redirect('super_admin_about')
    
    context = {
        'item': item,
        'color_choices': [('primary', 'Primary'), ('success', 'Success'), ('warning', 'Warning'), ('info', 'Info'), ('danger', 'Danger')],
        'page_title': 'Edit Why Choose Item' if item else 'New Why Choose Item'
    }
    return render(request, 'admin/about/about_edit_why_item.html', context)


@login_required
@admin_required
def about_delete_why_item(request, item_id):
    """Delete why choose item"""
    
    item = get_object_or_404(WhyChooseItem, id=item_id)
    item.delete()
    messages.success(request, 'Item deleted successfully!')
    return redirect('super_admin_about')


@login_required
@admin_required
def about_add_gallery_image(request):
    """Add gallery image for about page"""
    
    
    if request.method == 'POST':
        image = request.FILES.get('image')
        title = request.POST.get('title', '')
        alt_text = request.POST.get('alt_text', '')
        display_order = request.POST.get('display_order', 0)
        
        if image:
            AboutGalleryImage.objects.create(
                image=image,
                title=title,
                alt_text=alt_text,
                display_order=display_order
            )
            messages.success(request, 'Gallery image uploaded successfully!')
        else:
            messages.error(request, 'Please select an image to upload.')
        
        return redirect('super_admin_about')
    
    return redirect('super_admin_about')


@login_required
@admin_required
def about_delete_gallery_image(request, image_id):
    """Delete gallery image"""
    
    image = get_object_or_404(AboutGalleryImage, id=image_id)
    image.delete()
    messages.success(request, 'Gallery image deleted successfully!')
    return redirect('super_admin_about')


# ============================================================================
# CONTACT PAGE MANAGEMENT
# ============================================================================
