from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone

from accounts.decorators import admin_required, staff_or_admin_required, user_required
from notifications.email_utils import (
    send_equipment_rental_email,
    send_equipment_return_reminder_email,
)
from .models import Equipment, EquipmentRental
from .forms import EquipmentForm
from dashboard.cache_utils import pages_cache_get_or_set
from dashboard.models import EquipmentPageSettings, FeaturedEquipment, EquipmentCategory


@login_required
def equipment_list_view(request):

    equipment = Equipment.objects.filter(is_active=True)

    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        equipment = equipment.filter(type=type_filter)

    # Filter availability
    available_only = request.GET.get('available', '')
    if available_only:
        equipment = equipment.filter(quantity_available__gt=0)
    
    # CMS Data (cached; invalidated via dashboard.cache_signals)
    cms_settings = pages_cache_get_or_set('equipment_list_cms', lambda: EquipmentPageSettings.objects.first())
    featured_equipment = pages_cache_get_or_set('equipment_list_featured', lambda: list(
        FeaturedEquipment.objects.filter(is_active=True).select_related('equipment').order_by('display_order')[:6]
    ))
    categories = pages_cache_get_or_set('equipment_list_categories', lambda: list(
        EquipmentCategory.objects.filter(is_active=True).order_by('display_order')
    ))

    return render(request, 'user/equipment/equipment_list.html', {
        'equipment': equipment,
        'type_filter': type_filter,
        'available_only': available_only,
        'cms_settings': cms_settings,
        'featured_equipment': featured_equipment,
        'categories': categories,
    })


@login_required
@user_required
def equipment_rental_create_view(request):
    if request.method == 'POST':
        equipment_id = request.POST.get('equipment_id')
        rental_days = int(request.POST.get('rental_days', 1))
        quantity = int(request.POST.get('quantity', 1))

        equipment = get_object_or_404(Equipment, id=equipment_id, is_active=True)

        if equipment.quantity_available < quantity:
            messages.error(request, 'Not enough equipment available.')
            return redirect('equipment_detail', equipment_id=equipment_id)

        rental_fee = equipment.rental_price * rental_days * quantity
        reserved_date = timezone.now().date()

        rental = EquipmentRental.objects.create(
            equipment=equipment,
            rented_by=request.user,
            reserved_date=reserved_date,
            rental_fee=rental_fee,
            status='reserved',
            quantity=quantity
        )

        # Deduct quantity from available stock
        equipment.quantity_available -= quantity
        equipment.quantity_reserved += quantity
        equipment.save()

        messages.success(request, f'Successfully reserved {equipment.name}.')
        send_equipment_rental_email(request.user, equipment, 'reserved')
        return redirect('equipment_list')

    return redirect('equipment_list')


@login_required
def equipment_detail_view(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id, is_active=True)
    
    # Get rental history for staff/admin
    rental_history = None
    if request.user.is_staff_user() or request.user.is_admin():
        rental_history = EquipmentRental.objects.filter(equipment=equipment).order_by('-created_at')[:10]
    
    return render(request, 'user/equipment/equipment_detail.html', {
        'equipment': equipment,
        'rental_history': rental_history
    })


@login_required
@staff_or_admin_required
def staff_equipment_view(request):
    
    equipment = Equipment.objects.all().order_by('type', 'name')
    
    # Equipment statistics
    equip_base = Equipment.objects.filter(is_active=True)
    rental_base = EquipmentRental.objects.filter(status__in=['reserved', 'rented'])
    
    stats = {
        'total_items': equip_base.aggregate(
            total=Count('id')
        )['total'],
        'low_stock': equip_base.filter(quantity_available__lte=2).count(),
        'out_of_stock': equip_base.filter(quantity_available=0).count(),
        'active_rentals': rental_base.count(),
    }
    
    return render(request, 'staff/equipment.html', {
        'equipment': equipment,
        'stats': stats
    })


@login_required
@staff_or_admin_required
def check_out_equipment_view(request, rental_id):
    
    rental = get_object_or_404(EquipmentRental.objects.filter(status='reserved'), id=rental_id)
    
    if request.method == 'POST':
        rental.status = 'rented'
        rental.rented_at = timezone.now()
        rental.checked_out_by = request.user
        rental.condition_out = request.POST.get('condition_out', rental.equipment.condition)
        rental.save()
        
        # Update equipment quantity (move from reserved to rented)
        equipment = rental.equipment
        equipment.quantity_reserved -= rental.quantity
        equipment.save()
        
        messages.success(request, f'{rental.equipment.name} checked out successfully.')
        send_equipment_rental_email(rental.rented_by, rental.equipment, 'rented')
        send_equipment_return_reminder_email(rental.rented_by, rental.equipment, rental)
        return redirect('staff_equipment')
    
    return render(request, 'staff/equipment/check_out.html', {'rental': rental})


@login_required
@user_required
def cancel_equipment_rental_view(request, rental_id):
    """Cancel an equipment rental reservation and restore quantities."""
    rental = get_object_or_404(EquipmentRental, id=rental_id, rented_by=request.user, status='reserved')

    if request.method == 'POST':
        # Restore equipment quantities
        equipment = rental.equipment
        equipment.quantity_available += rental.quantity
        equipment.quantity_reserved -= rental.quantity
        equipment.save()

        # Delete the rental record
        rental.delete()

        messages.success(request, f'Reservation for {equipment.name} cancelled successfully.')
        return redirect('equipment_list')

    return render(request, 'user/equipment/cancel_rental.html', {'rental': rental})


@login_required
@staff_or_admin_required
def check_in_equipment_view(request, rental_id):

    rental = get_object_or_404(EquipmentRental.objects.filter(status='rented'), id=rental_id)
    
    if request.method == 'POST':
        rental.status = 'returned'
        rental.returned_at = timezone.now()
        rental.checked_in_by = request.user
        rental.condition_in = request.POST.get('condition_in', rental.condition_out)
        rental.notes = request.POST.get('notes', '')
        rental.save()
        
        # Update equipment quantity (return to available stock)
        equipment = rental.equipment
        equipment.quantity_available += rental.quantity
        equipment.save()
        
        # Check if equipment needs maintenance
        if rental.condition_in == 'poor' or rental.condition_in == 'fair':
            messages.warning(request, f'Equipment returned in {rental.condition_in} condition. Consider maintenance.')
        else:
            messages.success(request, f'{rental.equipment.name} checked in successfully.')
        send_equipment_rental_email(rental.rented_by, rental.equipment, 'returned')
        
        return redirect('staff_equipment')
    
    return render(request, 'staff/equipment/check_in.html', {'rental': rental})


# Admin CRUD Views

@login_required
@admin_required
def admin_equipment_list_view(request):

    equipment = Equipment.objects.all().order_by('-created_at')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        equipment = equipment.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(type__icontains=search_query)
        )

    type_filter = request.GET.get('type', '')
    if type_filter:
        equipment = equipment.filter(type=type_filter)

    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        equipment = equipment.filter(is_active=True)
    elif status_filter == 'inactive':
        equipment = equipment.filter(is_active=False)

    condition_filter = request.GET.get('condition', '')
    if condition_filter:
        equipment = equipment.filter(condition=condition_filter)

    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    allowed_sort_fields = ['name', 'type', 'quantity_available', 'rental_price', 'created_at']
    if sort_by.lstrip('-') in allowed_sort_fields:
        if sort_order == 'asc' and sort_by.startswith('-'):
            sort_by = sort_by[1:]
        elif sort_order == 'desc' and not sort_by.startswith('-'):
            sort_by = '-' + sort_by
        equipment = equipment.order_by(sort_by)

    # Stats
    equip_base = Equipment.objects.filter(is_active=True)
    rental_base = EquipmentRental.objects.filter(status__in=['reserved', 'rented'])

    stats = {
        'total': Equipment.objects.count(),
        'available': equip_base.filter(quantity_available__gt=0).count(),
        'rented': rental_base.count(),
        'maintenance': equip_base.filter(condition__in=['fair', 'poor']).count(),
        'out_of_stock': equip_base.filter(quantity_available=0).count(),
        'low_stock': equip_base.filter(quantity_available__lte=2, quantity_available__gt=0).count(),
    }

    # Pagination
    paginator = Paginator(equipment, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/equipment/equipment_list.html', {
        'equipment': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'condition_filter': condition_filter,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'stats': stats,
    })


@login_required
@admin_required
def admin_equipment_create_view(request):

    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, f'Equipment {equipment.name} created successfully.')
            return redirect('admin_equipment_list')
    else:
        form = EquipmentForm()

    return render(request, 'admin/equipment/equipment_form.html', {
        'form': form,
        'edit_mode': False,
    })


@login_required
@admin_required
def admin_equipment_edit_view(request, equipment_id):

    equipment = get_object_or_404(Equipment.objects.all(), id=equipment_id)
    
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Equipment {equipment.name} updated successfully.')
            return redirect('admin_equipment_list')
    else:
        form = EquipmentForm(instance=equipment)

    return render(request, 'admin/equipment/equipment_form.html', {
        'form': form,
        'edit_mode': True,
        'equipment': equipment,
    })


@login_required
@admin_required
def admin_equipment_delete_view(request, equipment_id):

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_equipment_list')

    equipment = get_object_or_404(Equipment.objects.all(), id=equipment_id)
    
    if not equipment.is_active:
        messages.info(request, f'Equipment {equipment.name} is already inactive.')
        return redirect('admin_equipment_list')

    equipment.is_active = False
    equipment.save(update_fields=['is_active'])
    messages.success(request, f'Equipment {equipment.name} deactivated successfully.')
    return redirect('admin_equipment_list')
