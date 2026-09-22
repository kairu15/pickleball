"""Home page CMS (sections, testimonials, amenities, gallery).

Moved verbatim out of the legacy ``dashboard.views`` /
``dashboard.cms_views`` modules (pure code motion).
"""

from accounts.decorators import admin_required
from dashboard.models import Amenity
from dashboard.models import GalleryImage
from dashboard.models import HomePageContent
from dashboard.models import Rating
from dashboard.models import Testimonial
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render


@login_required
@admin_required
def homepage_management(request):
    """Homepage content management page"""


    amenities = Amenity.objects.filter(is_active=True).order_by('display_order')
    gallery_images = GalleryImage.objects.filter(is_active=True).order_by('display_order')
    homepage_content = HomePageContent.objects.filter(is_active=True)

    context = {
        'amenities': amenities,
        'gallery_images': gallery_images,
        'homepage_content': homepage_content,
        'page_title': 'Homepage Management'
    }
    return render(request, 'admin/homepage/homepage_management.html', context)


@login_required
@admin_required
def homepage_edit_content(request, content_id=None):
    """Edit a single homepage text content item"""


    content_item = None
    if content_id:
        content_item = get_object_or_404(HomePageContent, id=content_id)

    if request.method == 'POST':
        section = request.POST.get('section')
        content_text = request.POST.get('content')
        is_active = request.POST.get('is_active') == 'on'

        if content_item:
            content_item.section = section
            content_item.content = content_text
            content_item.is_active = is_active
            content_item.save()
            messages.success(request, 'Homepage content updated successfully!')
        else:
            HomePageContent.objects.create(
                section=section,
                content=content_text,
                is_active=is_active
            )
            messages.success(request, 'Homepage content created successfully!')

        return redirect('super_admin_homepage')

    context = {
        'content_item': content_item,
        'section_choices': HomePageContent.SECTION_CHOICES,
        'page_title': 'Edit Homepage Content' if content_item else 'New Homepage Content'
    }
    return render(request, 'admin/homepage/homepage_edit_content.html', context)


@login_required
@admin_required
def populate_homepage_content(request):
    """Create or reactivate the default homepage text content."""

    if request.method != 'POST':
        return redirect('super_admin_homepage')


    default_content = {
        'hero_title': 'Welcome to PickleSphere',
        'hero_subtitle': 'The all-in-one platform connecting pickleball players with courts, tournaments, and equipment rentals nationwide. Find, book, and play — all in one place.',
        'about_title': 'Your Pickleball Journey Starts Here',
        'about_text': 'PickleSphere is a comprehensive platform that connects pickleball enthusiasts with courts, equipment, and tournaments across the country. Whether you are a beginner looking to learn or a seasoned pro seeking competition, we make it easy to find, book, and play.',
        'cta_title': 'Ready to Play?',
        'cta_text': 'Join thousands of pickleball players. Find courts, join tournaments, and be part of the community!',
    }

    created_count = 0
    updated_count = 0
    for section, content in default_content.items():
        item, created = HomePageContent.objects.update_or_create(
            section=section,
            defaults={
                'content': content,
                'is_active': True,
            }
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    if created_count:
        messages.success(request, f'Default homepage text content added ({created_count} new, {updated_count} refreshed).')
    else:
        messages.success(request, 'Homepage text content refreshed with default values.')

    return redirect('super_admin_homepage')


@login_required
@admin_required
def toggle_featured_rating(request, rating_id):
    """Toggle featured status of a rating for homepage display"""
    
    rating = get_object_or_404(Rating, id=rating_id)
    
    # Toggle featured status
    rating.is_featured = not rating.is_featured
    rating.save()
    
    if rating.is_featured:
        messages.success(request, f'Rating from {rating.user.username} is now featured on the homepage.')
    else:
        messages.success(request, f'Rating from {rating.user.username} has been removed from featured.')
    
    return redirect('super_admin_homepage')


@login_required
@admin_required
def homepage_edit_testimonial(request, testimonial_id=None):
    """Edit or create a testimonial"""
    
    
    testimonial = None
    if testimonial_id:
        testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        role = request.POST.get('role')
        rating = request.POST.get('rating', 5)
        text = request.POST.get('text')
        display_order = request.POST.get('display_order', 0)
        
        if testimonial:
            testimonial.name = name
            testimonial.role = role
            testimonial.rating = rating
            testimonial.text = text
            testimonial.display_order = display_order
            # If admin is editing, ensure it's approved
            if not testimonial.is_approved:
                testimonial.is_approved = True
            testimonial.save()
            messages.success(request, 'Testimonial updated successfully!')
        else:
            # Admin-created testimonials are auto-approved
            Testimonial.objects.create(
                name=name,
                role=role,
                rating=rating,
                text=text,
                display_order=display_order,
                is_active=True,
                is_approved=True  # Auto-approve admin-created testimonials
            )
            messages.success(request, 'Testimonial created and approved successfully!')
        
        return redirect('super_admin_homepage')
    
    context = {
        'testimonial': testimonial,
        'page_title': 'Edit Testimonial' if testimonial else 'New Testimonial'
    }
    return render(request, 'admin/homepage/homepage_edit_testimonial.html', context)


@login_required
@admin_required
def homepage_edit_amenity(request, amenity_id=None):
    """Edit or create an amenity"""
    
    
    amenity = None
    if amenity_id:
        amenity = get_object_or_404(Amenity, id=amenity_id)
    
    if request.method == 'POST':
        icon = request.POST.get('icon')
        title = request.POST.get('title')
        description = request.POST.get('description')
        display_order = request.POST.get('display_order', 0)
        
        if amenity:
            amenity.icon = icon
            amenity.title = title
            amenity.description = description
            amenity.display_order = display_order
            amenity.save()
            messages.success(request, 'Amenity updated successfully!')
        else:
            Amenity.objects.create(
                icon=icon,
                title=title,
                description=description,
                display_order=display_order,
                is_active=True
            )
            messages.success(request, 'Amenity created successfully!')
        
        return redirect('super_admin_homepage')
    
    context = {
        'amenity': amenity,
        'page_title': 'Edit Amenity' if amenity else 'New Amenity'
    }
    return render(request, 'admin/homepage/homepage_edit_amenity.html', context)


@login_required
@admin_required
def homepage_edit_gallery(request, gallery_id=None):
    """Edit or create a gallery image"""
    
    
    gallery = None
    if gallery_id:
        gallery = get_object_or_404(GalleryImage, id=gallery_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        alt_text = request.POST.get('alt_text')
        display_order = request.POST.get('display_order', 0)
        
        if gallery:
            gallery.title = title
            gallery.alt_text = alt_text
            gallery.display_order = display_order
            if request.FILES.get('image'):
                gallery.image = request.FILES['image']
            gallery.save()
            messages.success(request, 'Gallery image updated successfully!')
        else:
            if request.FILES.get('image'):
                GalleryImage.objects.create(
                    image=request.FILES['image'],
                    title=title,
                    alt_text=alt_text,
                    display_order=display_order,
                    is_active=True
                )
                messages.success(request, 'Gallery image created successfully!')
            else:
                messages.error(request, 'Please upload an image.')
                context = {
                    'gallery': gallery,
                    'page_title': 'Edit Gallery Image' if gallery else 'New Gallery Image'
                }
                return render(request, 'admin/homepage/homepage_edit_gallery.html', context)
        
        return redirect('super_admin_homepage')
    
    context = {
        'gallery': gallery,
        'page_title': 'Edit Gallery Image' if gallery else 'New Gallery Image'
    }
    return render(request, 'admin/homepage/homepage_edit_gallery.html', context)


@login_required
@admin_required
def homepage_delete_testimonial(request, testimonial_id):
    """Delete a testimonial"""
    
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    testimonial.delete()
    messages.success(request, 'Testimonial deleted successfully!')
    return redirect('super_admin_homepage')


@login_required
@admin_required
def homepage_delete_amenity(request, amenity_id):
    """Delete an amenity"""
    
    amenity = get_object_or_404(Amenity, id=amenity_id)
    amenity.delete()
    messages.success(request, 'Amenity deleted successfully!')
    return redirect('super_admin_homepage')


@login_required
@admin_required
def homepage_delete_gallery(request, gallery_id):
    """Delete a gallery image"""
    
    gallery = get_object_or_404(GalleryImage, id=gallery_id)
    gallery.delete()
    messages.success(request, 'Gallery image deleted successfully!')
    return redirect('super_admin_homepage')
