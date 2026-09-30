import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta, date as date_type
import calendar
from accounts.decorators import admin_required, staff_or_admin_required, user_required
from .models import (
    Reservation, ReservationEquipment, CancellationRequest, CancellationPolicy,
    WaitlistEntry,
)
from .services import (
    WaitlistError, join_waitlist, release_slot_and_notify_waitlist,
)
from .forms import ReservationForm, ReservationApprovalForm, CancellationRequestForm, AdminReservationForm, MATCH_FORMAT_CHOICES, GAME_TYPE_CHOICES, SCORING_FORMAT_CHOICES
from payments.models import Payment, PaymentLog, Refund
from scoring.models import MatchSettings
from notifications.models import Notification
from notifications.email_utils import (
    send_reservation_submitted_email,
    send_reservation_confirmed_email,
    send_reservation_rejected_email,
    send_reservation_cancelled_email,
    send_reservation_completed_email,
    send_reservation_modification_email,
    send_refund_confirmed_email,
)
from equipment.models import Equipment
from accounts.models import User
from courts.models import Court


def _build_guest_players_data(g1_p2='', g2_p1='', g2_p2=''):
    """Build guest_players_data JSON from individual guest field values."""
    guests = []
    if g1_p2:
        parts = g1_p2.split('|', 1)
        guests.append({'team': 1, 'player': 2, 'full_name': parts[0], 'nickname': parts[1] if len(parts) > 1 else ''})
    if g2_p1:
        parts = g2_p1.split('|', 1)
        guests.append({'team': 2, 'player': 1, 'full_name': parts[0], 'nickname': parts[1] if len(parts) > 1 else ''})
    if g2_p2:
        parts = g2_p2.split('|', 1)
        guests.append({'team': 2, 'player': 2, 'full_name': parts[0], 'nickname': parts[1] if len(parts) > 1 else ''})
    return json.dumps(guests) if guests else None


def _get_cancellation_time_limit():
    """Minutes after reservation creation during which cancellations AND edits
    are allowed, taken from the active cancellation policy (defaults to 20)."""
    policy = CancellationPolicy.objects.filter(is_active=True).first()
    return policy.time_limit_minutes if policy else 20


@login_required
@user_required
def reservation_list_view(request):
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    
    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        reservations = reservations.filter(
            Q(id__icontains=search_query) |
            Q(court__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        reservations = reservations.filter(date__gte=date_from)
    if date_to:
        reservations = reservations.filter(date__lte=date_to)
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    allowed_sort_fields = ['id', 'date', 'start_time', 'duration_hours', 'total_amount', 'status', 'created_at']
    if sort_by.lstrip('-') in allowed_sort_fields:
        if sort_order == 'asc' and sort_by.startswith('-'):
            sort_by = sort_by[1:]
        elif sort_order == 'desc' and not sort_by.startswith('-'):
            sort_by = '-' + sort_by
        reservations = reservations.order_by(sort_by)
    
    # Calculate stats from the FULL (unfiltered) queryset for summary cards
    all_user_reservations = Reservation.objects.filter(user=request.user)
    confirmed_count = all_user_reservations.filter(status='confirmed').count()
    pending_count = all_user_reservations.filter(status='pending').count()
    completed_count = all_user_reservations.filter(status='completed').count()
    total_count = all_user_reservations.count()
    
    # Pagination
    paginator = Paginator(reservations, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Mark which reservations can still be edited (same window as cancellation)
    edit_time_limit = _get_cancellation_time_limit()
    now = timezone.now()
    for res in page_obj.object_list:
        res.can_edit = (now - res.created_at) <= timedelta(minutes=edit_time_limit)
    
    return render(request, 'user/reservations/reservation_list.html', {
        'reservations': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'total_count': total_count,
        'confirmed_count': confirmed_count,
        'pending_count': pending_count,
        'completed_count': completed_count,
    })


@login_required
@user_required
def reservation_create_view(request):
    active_settings = MatchSettings.objects.filter(is_active=True).first()
    
    initial_court_id = request.GET.get('court') or request.POST.get('court')

    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user)
        equipment_ids = request.POST.getlist('equipment')
        
        if form.is_valid():
            # Store validated data in session instead of creating reservation
            checkout_token = str(uuid.uuid4())
            
            court = form.cleaned_data['court']
            date = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            
            # Re-verify slot availability on the server
            from reservations.services import maintenance_blocks_overlapping
            if maintenance_blocks_overlapping(court, date, start_time, end_time).exists():
                messages.error(request, 'This court is unavailable for the selected time slot (maintenance or closure). Please select a different slot.')
                equipment_list = Equipment.objects.filter(quantity_available__gt=0, is_active=True)
                return render(request, 'user/reservations/reservation_create.html', {
                    'form': form,
                    'equipment_list': equipment_list
                })

            overlapping = Reservation.objects.filter(
                court=court,
                date=date,
                status__in=['confirmed', 'pending']
            ).exclude(
                start_time__gte=end_time
            ).exclude(
                end_time__lte=start_time
            )
            
            if overlapping.exists():
                messages.error(request, 'Sorry, this time slot was just booked. Please select a different slot.')
                equipment_list = Equipment.objects.filter(quantity_available__gt=0, is_active=True)
                return render(request, 'user/reservations/reservation_create.html', {
                    'form': form,
                    'equipment_list': equipment_list
                })
            
            # Check if slot is in the past
            slot_datetime = datetime.combine(date, start_time)
            if timezone.is_naive(slot_datetime):
                slot_datetime = timezone.make_aware(slot_datetime)
            if slot_datetime < timezone.now():
                messages.error(request, 'This time slot has already passed. Please select a future time.')
                equipment_list = Equipment.objects.filter(quantity_available__gt=0, is_active=True)
                return render(request, 'user/reservations/reservation_create.html', {
                    'form': form,
                    'equipment_list': equipment_list
                })
            
            # Calculate duration and pricing
            start_dt = datetime.combine(date, start_time)
            end_dt = datetime.combine(date, end_time)
            duration_hours = round((end_dt - start_dt).total_seconds() / 3600, 1)
            hourly_rate = float(court.hourly_rate)
            subtotal = hourly_rate * duration_hours
            
            # Store in session
            request.session['checkout_data'] = {
                'court_id': court.id,
                'date': date.isoformat(),
                'start_time': start_time.strftime('%H:%M'),
                'end_time': end_time.strftime('%H:%M'),
                'duration_hours': duration_hours,
                'hourly_rate': hourly_rate,
                'subtotal': subtotal,
                'notes': form.cleaned_data.get('notes', ''),
                'equipment_ids': [int(eid) for eid in equipment_ids if eid],
                'match_name': form.cleaned_data.get('match_name', ''),
                'match_format': form.cleaned_data.get('match_format', 'singles'),
                'game_type': form.cleaned_data.get('game_type', 'friendly'),
                'scoring_format': form.cleaned_data.get('scoring_format', '11'),
                'points_per_game': form.cleaned_data.get('points_per_game') or 11,
                'games_to_win': form.cleaned_data.get('games_to_win') or 2,
                'win_by_two': form.cleaned_data.get('win_by_two') if form.cleaned_data.get('win_by_two') is not None else True,
                # Match participants (convert empty strings to None for FK fields)
                'team1_player2_id': form.cleaned_data.get('team1_player2_search') or None,
                'team2_player1_id': form.cleaned_data.get('team2_player1_search') or None,
                'team2_player2_id': form.cleaned_data.get('team2_player2_search') or None,
                'guest_team1_p2': form.cleaned_data.get('guest_team1_p2', ''),
                'guest_team2_p1': form.cleaned_data.get('guest_team2_p1', ''),
                'guest_team2_p2': form.cleaned_data.get('guest_team2_p2', ''),
                # Build guest_players_data JSON
                # Team names (captured directly from POST since they're not form fields)
                'team1_name': request.POST.get('team1_name', '').strip(),
                'team2_name': request.POST.get('team2_name', '').strip(),
                # Build guest_players_data JSON
                'guest_players_data': _build_guest_players_data(
                    form.cleaned_data.get('guest_team1_p2', ''),
                    form.cleaned_data.get('guest_team2_p1', ''),
                    form.cleaned_data.get('guest_team2_p2', '')
                ),
            }
            
            messages.success(request, 'Please review your booking and complete payment.')
            return redirect('checkout_page', checkout_token=checkout_token)
        else:
            # Convert non-field validation errors to floating toast messages
            for error in form.non_field_errors():
                messages.error(request, error)
            equipment_list = Equipment.objects.filter(quantity_available__gt=0, is_active=True)
            return render(request, 'user/reservations/reservation_create.html', {
                'form': form,
                'equipment_list': equipment_list
            })
    else:
        # GET request
        initial_data = {}
        if initial_court_id:
            try:
                court = Court.objects.get(id=initial_court_id, is_active=True)
                initial_data['court'] = court.id
            except Court.DoesNotExist:
                pass
        
        if active_settings:
            initial_data['match_format'] = active_settings.format
            initial_data['game_type'] = active_settings.game_type
            initial_data['scoring_format'] = active_settings.scoring_format
            initial_data['points_per_game'] = active_settings.points_per_game
            initial_data['games_to_win'] = active_settings.games_to_win
            initial_data['win_by_two'] = active_settings.win_by_two
        
        form = ReservationForm(user=request.user, initial=initial_data)
    
    equipment_list = Equipment.objects.filter(quantity_available__gt=0, is_active=True)
    
    return render(request, 'user/reservations/reservation_create.html', {
        'form': form,
        'equipment_list': equipment_list
    })


@login_required
def reservation_detail_view(request, reservation_id):
    """View reservation details - accessible by both the reservation owner and staff/admin."""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    is_authorized = reservation.user == request.user or request.user.is_staff_user()
    if not is_authorized:
        messages.error(request, 'You do not have permission to view this reservation.')
        return redirect('reservation_list')
    
    # Editing is only allowed within the same time window as cancellation
    time_limit_minutes = _get_cancellation_time_limit()
    can_edit = (timezone.now() - reservation.created_at) <= timedelta(minutes=time_limit_minutes)

    # Inform the user when they were redirected here by the expired editing countdown
    if request.GET.get('expired'):
        messages.info(
            request,
            f'Your editing window has expired. Editing is only allowed within '
            f'{time_limit_minutes} minutes of reservation creation.'
        )

    # Reservation match fields are stored as raw codes (no model choices), so map to
    # human-readable labels using the same choice tuples the forms use.
    return render(request, 'user/reservations/reservation_detail.html', {
        'reservation': reservation,
        'can_edit': can_edit,
        'match_format_display': dict(MATCH_FORMAT_CHOICES).get(reservation.match_format, reservation.match_format),
        'game_type_display': dict(GAME_TYPE_CHOICES).get(reservation.game_type, reservation.game_type),
        'scoring_format_display': dict(SCORING_FORMAT_CHOICES).get(reservation.scoring_format, reservation.scoring_format),
    })


@login_required
@staff_or_admin_required
def staff_reservations_view(request):
    
    reservations = Reservation.objects.select_related('user', 'court', 'court__site').prefetch_related('payment').all().order_by('-created_at')
    
    
    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        reservations = reservations.filter(
            Q(id__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    # Filter by date
    date_filter = request.GET.get('date', '')
    if date_filter:
        reservations = reservations.filter(date=date_filter)
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # Validate sort field to prevent injection
    allowed_sort_fields = ['id', 'date', 'start_time', 'duration_hours', 'total_amount', 'status', 'created_at', 'user__username']
    if sort_by.lstrip('-') in allowed_sort_fields:
        if sort_order == 'asc' and sort_by.startswith('-'):
            sort_by = sort_by[1:]
        elif sort_order == 'desc' and not sort_by.startswith('-'):
            sort_by = '-' + sort_by
        reservations = reservations.order_by(sort_by)
    else:
        reservations = reservations.order_by('-created_at')
    
    # Stats for summary cards (from full unfiltered queryset)
    base_qs = Reservation.objects.all()
    total_count = base_qs.count()
    pending_count = base_qs.filter(status='pending').count()
    confirmed_count = base_qs.filter(status='confirmed').count()
    completed_count = base_qs.filter(status='completed').count()
    cancelled_count = base_qs.filter(status='cancelled').count()
    
    # Pagination
    paginator = Paginator(reservations, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'staff/reservations.html', {
        'reservations': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'total_count': total_count,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
    })


@login_required
@staff_or_admin_required
def approve_reservation_view(request, reservation_id):
    
    res_qs = Reservation.objects.all()
    reservation = get_object_or_404(res_qs, id=reservation_id)
    
    if request.method == 'POST':
        form = ReservationApprovalForm(request.POST, instance=reservation)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.approved_by = request.user
            reservation.approved_at = timezone.now()
            reservation.save()
            
            # Notify user
            Notification.objects.create(
                user=reservation.user,
                message=f"Your reservation #{reservation.id} has been {reservation.status}."
            )
            
            # Send email notification
            if reservation.status == 'confirmed':
                send_reservation_confirmed_email(reservation.user, reservation)
            elif reservation.status == 'rejected':
                reason = form.cleaned_data.get('admin_notes', '')
                send_reservation_rejected_email(reservation.user, reservation, reason)
            elif reservation.status == 'completed':
                send_reservation_completed_email(reservation.user, reservation)
            
            messages.success(request, f'Reservation #{reservation.id} has been {reservation.status}.')
            return redirect('staff_reservations')
    else:
        form = ReservationApprovalForm(instance=reservation)
    
    return render(request, 'admin/reservations/approve_reservation.html', {
        'form': form,
        'reservation': reservation
    })


@login_required
@user_required
def reservation_edit_view(request, reservation_id):
    """Allow users to edit their pending reservations (court, date, time, notes, equipment)"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    # Only pending reservations can be edited
    if reservation.status not in ['pending']:
        messages.error(request, 'Only pending reservations can be edited.')
        return redirect('reservation_detail', reservation_id=reservation.id)
    
    # Editing is only allowed within the same time window as cancellation
    time_limit_minutes = _get_cancellation_time_limit()
    time_since_creation = timezone.now() - reservation.created_at
    is_within_time_limit = time_since_creation <= timedelta(minutes=time_limit_minutes)

    if not is_within_time_limit:
        messages.error(
            request,
            f'Editing is only allowed within {time_limit_minutes} minutes of reservation creation. '
            f'Your reservation was created {time_since_creation.total_seconds() / 60:.1f} minutes ago.'
        )
        return redirect('reservation_detail', reservation_id=reservation.id)
    
    # Get available equipment
    equipment_list = Equipment.objects.filter(quantity_available__gt=0, is_active=True)
    
    # Get currently rented equipment IDs
    current_equipment_ids = list(reservation.rented_equipment.values_list('equipment_id', flat=True))
    
    if request.method == 'POST':
        form = ReservationForm(request.POST, instance=reservation, user=request.user)
        equipment_ids = request.POST.getlist('equipment')
        
        if form.is_valid():
            updated_reservation = form.save(commit=False)
            updated_reservation.hourly_rate = updated_reservation.court.hourly_rate
            
            # Recalculate duration from time slot (in case user changed it)
            start_dt = datetime.combine(updated_reservation.date, updated_reservation.start_time)
            end_dt = datetime.combine(updated_reservation.date, updated_reservation.end_time)
            duration_hours = (end_dt - start_dt).total_seconds() / 3600
            updated_reservation.duration_hours = duration_hours
            
            # Recalculate pricing
            hourly_rate = float(updated_reservation.hourly_rate)
            updated_reservation.subtotal = hourly_rate * duration_hours
            
            # Handle equipment changes
            new_equipment_ids = [int(eid) for eid in equipment_ids if eid]
            
            # Return old equipment that was removed
            for rental in reservation.rented_equipment.all():
                if rental.equipment_id not in new_equipment_ids:
                    rental.equipment.quantity_available += rental.quantity
                    rental.equipment.save()
                    rental.delete()
            
            # Add new equipment
            equipment_fee = 0
            for eq_id in new_equipment_ids:
                if eq_id not in current_equipment_ids:
                    try:
                        equipment = Equipment.objects.get(id=eq_id, is_active=True)
                        if equipment.quantity_available > 0:
                            ReservationEquipment.objects.create(
                                reservation=reservation,
                                equipment=equipment,
                                quantity=1,
                                rental_fee=equipment.rental_price
                            )
                            equipment_fee += float(equipment.rental_price)
                            equipment.quantity_available -= 1
                            equipment.save()
                    except Equipment.DoesNotExist:
                        pass
                else:
                    # Keep existing equipment fee
                    rental = reservation.rented_equipment.get(equipment_id=eq_id)
                    equipment_fee += float(rental.rental_fee)
            
            # Recalculate totals
            updated_reservation.equipment_fee = equipment_fee
            updated_reservation.total_amount = updated_reservation.subtotal + equipment_fee
            updated_reservation.save()
            
            # Update payment amount if still pending
            try:
                payment = reservation.payment
                if payment.status == 'pending':
                    payment.amount = updated_reservation.total_amount
                    payment.save()
            except Payment.DoesNotExist:
                pass
            except AttributeError:
                pass
            
            # Notify user
            Notification.objects.create(
                user=request.user,
                message=f"Your reservation #{reservation.id} has been updated."
            )
            send_reservation_modification_email(request.user, reservation, 'Reservation details updated')
            
            messages.success(request, 'Reservation updated successfully!')
            return redirect('reservation_detail', reservation_id=reservation.id)
    else:
        initial_data = {}
        if reservation.start_time and reservation.end_time:
            initial_data['time_slot'] = f"{reservation.start_time.strftime('%H:%M')}-{reservation.end_time.strftime('%H:%M')}"
        form = ReservationForm(instance=reservation, user=request.user, initial=initial_data)
    
    return render(request, 'user/reservations/reservation_edit.html', {
        'form': form,
        'reservation': reservation,
        'equipment_list': equipment_list,
        'current_equipment_ids': current_equipment_ids,
        'is_within_time_limit': is_within_time_limit,
        'time_limit_minutes': time_limit_minutes,
        'time_remaining': timedelta(minutes=time_limit_minutes) - time_since_creation,
    })


@login_required
@user_required
def cancel_reservation_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    if reservation.status in ['completed', 'cancelled']:
        messages.error(request, 'This reservation cannot be cancelled.')
        return redirect('reservation_list')

    # Get active cancellation policy
    cancellation_policy = CancellationPolicy.objects.filter(is_active=True).first()
    if not cancellation_policy:
        # Create default policy if none exists
        cancellation_policy = CancellationPolicy.objects.create(
            name='Default Cancellation Policy',
            time_limit_minutes=20,
            deduction_percentage=30,
            is_active=True
        )

    # Check if cancellation is within time limit
    time_since_creation = timezone.now() - reservation.created_at
    time_limit_minutes = cancellation_policy.time_limit_minutes
    is_within_time_limit = time_since_creation <= timedelta(minutes=time_limit_minutes)

    if not is_within_time_limit:
        messages.error(request, f'Cancellation is only allowed within {time_limit_minutes} minutes of reservation creation. Your reservation was created {time_since_creation.total_seconds() / 60:.1f} minutes ago.')
        return redirect('reservation_list')

    if request.method == 'POST':
        form = CancellationRequestForm(request.POST)
        if form.is_valid():
            cancellation = form.save(commit=False)
            cancellation.reservation = reservation
            cancellation.requested_by = request.user
            cancellation.is_within_time_limit = is_within_time_limit

            # Calculate deduction based on policy
            deduction_percentage = cancellation_policy.deduction_percentage
            deduction_amount = (reservation.total_amount * deduction_percentage) / 100
            refund_amount = reservation.total_amount - deduction_amount

            cancellation.deduction_percentage = deduction_percentage
            cancellation.deduction_amount = deduction_amount
            cancellation.cancellation_note = f'A {deduction_percentage}% cancellation fee (₱{deduction_amount:,.2f}) has been applied. Refund amount: ₱{refund_amount:,.2f}.'
            cancellation.save()

            # Update reservation status
            reservation.status = 'cancelled'
            reservation.save()

            # Offer the freed slot to the next waitlisted user
            release_slot_and_notify_waitlist(reservation)

            # Update payment status to refunded
            try:
                payment = reservation.payment
                if payment.status == 'paid':
                    payment.status = 'refunded'
                    payment.save()

                    # Create refund record with deducted amount
                    Refund.objects.create(
                        payment=payment,
                        amount=refund_amount,
                        reason=f"{cancellation.reason} ({deduction_percentage}% cancellation fee applied)",
                        status='processed',
                        requested_by=request.user
                    )
            except Payment.DoesNotExist:
                pass
            except AttributeError:
                pass

            # Return equipment
            for rental in reservation.rented_equipment.all():
                rental.equipment.quantity_available += rental.quantity
                rental.equipment.save()

            # Notify staff
            staff_users = User.objects.filter(role__in=['super_admin', 'staff'])
            for staff in staff_users:
                Notification.objects.create(
                    user=staff,
                    message=f"Reservation #{reservation.id} has been cancelled by {request.user.username} with {deduction_percentage}% deduction."
                )
            
            # Send cancellation email to user
            send_reservation_cancelled_email(reservation.user, reservation)

            # Format success message with refund details
            refund_method_display = dict(cancellation.REFUND_METHOD_CHOICES).get(cancellation.refund_method, 'GCash')
            processing_time = "5-7 business days" if cancellation.refund_method == 'card' else "24-48 hours"

            success_message = (
                f"Booking #{reservation.id:06d} has been cancelled successfully. "
                f"A {deduction_percentage}% cancellation fee (₱{deduction_amount:,.2f}) has been applied. "
                f"Refund of ₱{refund_amount:,.2f} will be processed via {refund_method_display} "
                f"within {processing_time}."
            )

            messages.success(request, success_message)
            return redirect('reservation_list')
        else:
            # Convert form field errors to floating toast messages
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    else:
        form = CancellationRequestForm()

    # Calculate deduction amounts for display
    deduction_percentage = cancellation_policy.deduction_percentage
    deduction_amount = (reservation.total_amount * deduction_percentage) / 100
    refund_amount = reservation.total_amount - deduction_amount

    return render(request, 'user/cancel_reservation.html', {
        'form': form,
        'reservation': reservation,
        'is_within_time_limit': is_within_time_limit,
        'time_limit_minutes': time_limit_minutes,
        'time_remaining': timedelta(minutes=time_limit_minutes) - time_since_creation if is_within_time_limit else None,
        'deduction_percentage': deduction_percentage,
        'deduction_amount': deduction_amount,
        'refund_amount': refund_amount,
    })


@login_required
@staff_or_admin_required
def staff_refund_processing_view(request):
    """Dedicated page for staff to process refunds (mark as sent) for approved cancellations."""
    cancellations = CancellationRequest.objects.select_related(
        'reservation', 'reservation__user', 'reservation__court',
        'reservation__court__site', 'requested_by'
    ).filter(
        approved=True,
        refund_processed=False
    ).order_by('-approved_at')


    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        cancellations = cancellations.filter(
            Q(reservation__id__icontains=search_query) |
            Q(reservation__user__username__icontains=search_query) |
            Q(reservation__user__email__icontains=search_query) |
            Q(reservation__court__name__icontains=search_query)
        )

    # Filter by refund method
    method_filter = request.GET.get('method', '')
    if method_filter:
        cancellations = cancellations.filter(refund_method=method_filter)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        cancellations = cancellations.filter(approved_at__date__gte=date_from)
    if date_to:
        cancellations = cancellations.filter(approved_at__date__lte=date_to)

    # Stats
    total_pending = cancellations.count()
    base_qs = CancellationRequest.objects.all()
    total_approved_all = base_qs.filter(approved=True).count()
    total_processed = base_qs.filter(refund_processed=True).count()
    gcash_count = cancellations.filter(refund_method='gcash').count()
    paypal_count = cancellations.filter(refund_method='paypal').count()

    # Handle POST
    if request.method == 'POST':
        cancellation_id = request.POST.get('cancellation_id')
        refund_notes = request.POST.get('refund_notes', '').strip()

        c_qs = CancellationRequest.objects.all()
        cancellation = get_object_or_404(c_qs, id=cancellation_id)

        if cancellation.approved and not cancellation.refund_processed:
            cancellation.refund_processed = True
            cancellation.refund_processed_at = timezone.now()
            cancellation.processed_by = request.user
            cancellation.save()

            # Update payment
            try:
                payment = cancellation.reservation.payment
                payment.status = 'refunded'
                payment.payment_notes = refund_notes or payment.payment_notes
                payment.save()

                # Log
                PaymentLog.objects.create(
                    payment=payment,
                    action='Refund Processed via Counter',
                    details=f'Refund for cancellation #{cancellation.id} processed by {request.user.get_full_name() or request.user.username}. Notes: {refund_notes or "-"}',
                    performed_by=request.user
                )
            except Payment.DoesNotExist:
                pass
            except AttributeError:
                pass

            Notification.objects.create(
                user=cancellation.requested_by,
                message=f"Your refund of ₱{cancellation.reservation.total_amount - cancellation.deduction_amount:,.2f} for Reservation #{cancellation.reservation.id} has been sent. "
            )

            messages.success(request, f'Refund for cancellation #{cancellation.id} (Reservation #{cancellation.reservation.id}) marked as processed.')
            return redirect('staff_refund_processing')
        else:
            messages.error(request, 'This cancellation is not eligible for refund processing.')
            return redirect('staff_refund_processing')

    # Pagination
    paginator = Paginator(cancellations, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'staff/refund_processing.html', {
        'cancellations': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'method_filter': method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_pending': total_pending,
        'total_approved_all': total_approved_all,
        'total_processed': total_processed,
        'gcash_count': gcash_count,
        'paypal_count': paypal_count,
    })


@login_required
@staff_or_admin_required
def staff_refund_history_view(request):
    """Staff view showing all processed refunds with date, amount, method, and staff who processed them."""
    cancellations = CancellationRequest.objects.select_related(
        'reservation', 'reservation__user', 'reservation__court',
        'reservation__court__site', 'approved_by', 'processed_by'
    ).filter(
        refund_processed=True
    ).order_by('-refund_processed_at')


    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        cancellations = cancellations.filter(
            Q(reservation__id__icontains=search_query) |
            Q(reservation__user__username__icontains=search_query) |
            Q(reservation__user__email__icontains=search_query) |
            Q(reservation__court__name__icontains=search_query) |
            Q(processed_by__username__icontains=search_query)
        )

    # Filter by refund method
    method_filter = request.GET.get('method', '')
    if method_filter:
        cancellations = cancellations.filter(refund_method=method_filter)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        cancellations = cancellations.filter(refund_processed_at__date__gte=date_from)
    if date_to:
        cancellations = cancellations.filter(refund_processed_at__date__lte=date_to)

    # Stats summary
    total_refunds = cancellations.count()
    total_refund_amount = sum(float(c.reservation.total_amount - c.deduction_amount) for c in cancellations)
    gcash_count = cancellations.filter(refund_method='gcash').count()
    paypal_count = cancellations.filter(refund_method='paypal').count()

    # Pagination
    paginator = Paginator(cancellations, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Annotate each cancellation with pre-calculated refund amount
    cancellations_list = list(page_obj.object_list)
    for c in cancellations_list:
        c.refund_amount = c.reservation.total_amount - c.deduction_amount

    return render(request, 'staff/refund_history.html', {
        'cancellations': cancellations_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'method_filter': method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_refunds': total_refunds,
        'total_refund_amount': total_refund_amount,
        'gcash_count': gcash_count,
        'paypal_count': paypal_count,
    })


@login_required
@staff_or_admin_required
def staff_cancellations_view(request):
    """Staff view to list, filter, and process cancellation requests."""
    cancellations = CancellationRequest.objects.select_related(
        'reservation', 'reservation__user', 'reservation__court',
        'reservation__court__site', 'requested_by'
    ).all()


    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        cancellations = cancellations.filter(
            Q(reservation__id__icontains=search_query) |
            Q(reservation__user__username__icontains=search_query) |
            Q(reservation__user__email__icontains=search_query) |
            Q(reservation__court__name__icontains=search_query)
        )

    # Filter by status (approved/rejected/pending)
    status_filter = request.GET.get('status', '')
    if status_filter == 'pending':
        cancellations = cancellations.filter(approved__isnull=True)
    elif status_filter == 'approved':
        cancellations = cancellations.filter(approved=True)
    elif status_filter == 'rejected':
        cancellations = cancellations.filter(approved=False)

    # Filter by refund status
    refund_filter = request.GET.get('refund', '')
    if refund_filter == 'processed':
        cancellations = cancellations.filter(refund_processed=True)
    elif refund_filter == 'pending':
        cancellations = cancellations.filter(refund_processed=False, approved=True)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        cancellations = cancellations.filter(requested_at__date__gte=date_from)
    if date_to:
        cancellations = cancellations.filter(requested_at__date__lte=date_to)

    # Sort
    sort_by = request.GET.get('sort_by', '-requested_at')
    sort_order = request.GET.get('sort_order', 'desc')
    allowed_sort_fields = ['id', 'requested_at', 'approved_at', 'deduction_amount', 'refund_method']
    # For sorting by reservation fields
    if sort_by == 'reservation__user__username':
        cancellations = cancellations.order_by(f"{'-' if sort_order == 'desc' else ''}reservation__user__username")
    elif sort_by == 'reservation__total_amount':
        cancellations = cancellations.order_by(f"{'-' if sort_order == 'desc' else ''}reservation__total_amount")
    elif sort_by.lstrip('-') in allowed_sort_fields:
        if sort_order == 'asc' and sort_by.startswith('-'):
            sort_by = sort_by[1:]
        elif sort_order == 'desc' and not sort_by.startswith('-'):
            sort_by = '-' + sort_by
        cancellations = cancellations.order_by(sort_by)
    else:
        cancellations = cancellations.order_by('-requested_at')

    # Stats for summary cards
    total_qs = CancellationRequest.objects.all()
    pending_count = total_qs.filter(approved__isnull=True).count()
    approved_count = total_qs.filter(approved=True).count()
    refund_pending = total_qs.filter(approved=True, refund_processed=False).count()

    # Handle POST: approve/reject cancellation or mark refund as processed
    if request.method == 'POST':
        action = request.POST.get('action')
        cancellation_id = request.POST.get('cancellation_id')

        if not action or not cancellation_id:
            messages.error(request, 'Missing action or cancellation ID.')
            return redirect('staff_cancellations')

        c_qs = CancellationRequest.objects.all()
        cancellation = get_object_or_404(c_qs, id=cancellation_id)

        if action == 'approve':
            cancellation.approved = True
            cancellation.approved_by = request.user
            cancellation.approved_at = timezone.now()
            cancellation.save()

            # Notify user
            Notification.objects.create(
                user=cancellation.requested_by,
                message=f"Your cancellation request for Reservation #{cancellation.reservation.id} has been approved. Refund of ₱{cancellation.reservation.total_amount - cancellation.deduction_amount:,.2f} will be processed within 24-48 hours."
            )
            messages.success(request, f'Cancellation #{cancellation.id} approved successfully.')

        elif action == 'reject':
            cancellation.approved = False
            cancellation.approved_by = request.user
            cancellation.approved_at = timezone.now()
            cancellation.save()

            Notification.objects.create(
                user=cancellation.requested_by,
                message=f"Your cancellation request for Reservation #{cancellation.reservation.id} has been reviewed and was not approved. Please contact support for more details."
            )
            messages.warning(request, f'Cancellation #{cancellation.id} rejected.')

        elif action == 'mark_refunded':
            cancellation.refund_processed = True
            cancellation.refund_processed_at = timezone.now()
            cancellation.processed_by = request.user
            cancellation.save()

            # Update payment
            try:
                payment = cancellation.reservation.payment
                payment.status = 'refunded'
                payment.save()
            except Payment.DoesNotExist:
                pass
            except AttributeError:
                pass

            Notification.objects.create(
                user=cancellation.requested_by,
                message=f"Your refund of ₱{cancellation.reservation.total_amount - cancellation.deduction_amount:,.2f} for Reservation #{cancellation.reservation.id} has been processed."
            )
            messages.success(request, f'Refund for cancellation #{cancellation.id} marked as processed.')

        return redirect('staff_cancellations')

    # Pagination
    paginator = Paginator(cancellations, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'staff/cancellations.html', {
        'cancellations': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'status_filter': status_filter,
        'refund_filter': refund_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'refund_pending': refund_pending,
        'total_count': total_qs.count(),
    })


@login_required
def calendar_view(request):
    # Get current month and year
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    
    # Calculate calendar data
    cal = calendar.Calendar(calendar.SUNDAY)
    month_days = cal.monthdayscalendar(year, month)
    
    # Get reservations for this month
    if request.user.is_normal_user():
        reservations = Reservation.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month,
            status__in=['confirmed', 'pending']
        )
    else:
        reservations = Reservation.objects.filter(
            date__year=year,
            date__month=month,
            status__in=['confirmed', 'pending']
        )
    
    # Group reservations by date
    reservation_dict = {}
    for res in reservations:
        day = res.date.day
        if day not in reservation_dict:
            reservation_dict[day] = []
        reservation_dict[day].append(res)

    # Create a list of days with reservations for easier template access
    days_with_reservations = list(reservation_dict.keys())

    month_name = calendar.month_name[month]

    return render(request, 'admin/reservations/reservation_calendar.html', {
        'month_days': month_days,
        'month_name': month_name,
        'year': year,
        'month': month,
        'reservations': reservation_dict,
        'days_with_reservations': days_with_reservations,
        'prev_month': month - 1 if month > 1 else 12,
        'next_month': month + 1 if month < 12 else 1,
        'prev_year': year if month > 1 else year - 1,
        'next_year': year if month < 12 else year + 1,
    })


# Admin CRUD Views

@login_required
@admin_required
def admin_reservation_list_view(request):

    reservations = Reservation.objects.select_related('user', 'court').all().order_by('-created_at')
    

    search_query = request.GET.get('search', '').strip()
    if search_query:
        reservations = reservations.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(court__name__icontains=search_query)
        )

    status_filter = request.GET.get('status', '')
    if status_filter:
        reservations = reservations.filter(status=status_filter)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        reservations = reservations.filter(date__gte=date_from)
    if date_to:
        reservations = reservations.filter(date__lte=date_to)

    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    allowed_sort_fields = ['id', 'date', 'duration_hours', 'total_amount', 'status', 'created_at', 'user__username', 'court__name']
    if sort_by.lstrip('-') in allowed_sort_fields:
        if sort_order == 'asc' and sort_by.startswith('-'):
            sort_by = sort_by[1:]
        elif sort_order == 'desc' and not sort_by.startswith('-'):
            sort_by = '-' + sort_by
        reservations = reservations.order_by(sort_by)

    # Pagination
    paginator = Paginator(reservations, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/reservations/reservation_list.html', {
        'reservations': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'sort_order': sort_order,
    })


@login_required
@admin_required
def admin_reservation_create_view(request):

    if request.method == 'POST':
        form = AdminReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            # Set user if not provided
            if not reservation.user:
                reservation.user = request.user
            # Calculate totals with proper None handling
            hourly_rate = float(reservation.hourly_rate) if reservation.hourly_rate else 0.0
            duration_hours = float(reservation.duration_hours) if reservation.duration_hours else 0.0
            reservation.subtotal = hourly_rate * duration_hours
            reservation.total_amount = reservation.calculate_total()
            reservation.save()

            # Create payment record
            Payment.objects.create(
                reservation=reservation,
                amount=reservation.total_amount,
                status='pending'
            )

            messages.success(request, f'Reservation #{reservation.id} created successfully.')
            return redirect('admin_reservation_list')
    else:
        form = AdminReservationForm()

    return render(request, 'admin/reservations/reservation_form.html', {
        'form': form,
        'edit_mode': False,
    })


@login_required
@admin_required
def admin_reservation_edit_view(request, reservation_id):

    reservation = get_object_or_404(Reservation.objects.all(), id=reservation_id)

    if request.method == 'POST':
        form = AdminReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            updated_reservation = form.save(commit=False)
            # Recalculate totals
            updated_reservation.subtotal = float(updated_reservation.hourly_rate) * float(updated_reservation.duration_hours)
            updated_reservation.total_amount = updated_reservation.calculate_total()
            updated_reservation.save()

            messages.success(request, f'Reservation #{reservation.id} updated successfully.')
            return redirect('admin_reservation_list')
    else:
        form = AdminReservationForm(instance=reservation)

    return render(request, 'admin/reservations/reservation_form.html', {
        'form': form,
        'edit_mode': True,
        'reservation': reservation,
    })


@login_required
@admin_required
def admin_reservation_delete_view(request, reservation_id):

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('admin_reservation_list')

    reservation = get_object_or_404(Reservation.objects.all(), id=reservation_id)

    if reservation.status == 'cancelled':
        messages.info(request, f'Reservation #{reservation.id} is already cancelled.')
        return redirect('admin_reservation_list')

    # Return equipment if any
    for rental in reservation.rented_equipment.all():
        rental.equipment.quantity_available += rental.quantity
        rental.equipment.save()

    # Update reservation status
    reservation.status = 'cancelled'
    reservation.save(update_fields=['status'])

    # Offer the freed slot to the next waitlisted user
    release_slot_and_notify_waitlist(reservation)

    # Update any non-paid related payment
    Payment.objects.filter(reservation=reservation).exclude(status='paid').update(status='cancelled')

    messages.success(request, f'Reservation #{reservation.id} cancelled successfully.')
    return redirect('admin_reservation_list')


@login_required
def get_time_slots_api(request):
    """API endpoint to get time slots (with status) for a court and date.

    Each slot has a status: 'available', 'booked' or 'unavailable'.
    Pass exclude_reservation=<id> when editing a reservation so the user's
    own booking does not mark the slot as booked.
    """
    court_id = request.GET.get('court_id')
    date_str = request.GET.get('date')
    exclude_str = request.GET.get('exclude_reservation', '')

    if not court_id or not date_str:
        return JsonResponse({'error': 'Court ID and date are required'}, status=400)

    try:
        court = Court.objects.get(id=court_id, is_active=True)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Court.DoesNotExist:
        return JsonResponse({'error': 'Court not found'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    exclude_reservation_id = None
    if exclude_str:
        try:
            exclude_reservation_id = int(exclude_str)
        except ValueError:
            return JsonResponse({'error': 'Invalid exclude_reservation'}, status=400)

    from courts.views import _build_time_slots
    slots = _build_time_slots(court, date, exclude_reservation_id=exclude_reservation_id)

    return JsonResponse({'slots': slots})


@login_required
def get_monthly_availability_api(request):
    """API endpoint to check which dates in a month have available slots."""
    court_id = request.GET.get('court_id')
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))

    if not court_id:
        return JsonResponse({'error': 'Court ID is required'}, status=400)

    try:
        court = Court.objects.get(id=court_id, is_active=True)
    except Court.DoesNotExist:
        return JsonResponse({'error': 'Court not found'}, status=404)

    cal = calendar.Calendar()
    month_days = [d for d in cal.itermonthdates(year, month) if d.month == month]

    # Get reservations for this court and month
    reservations = Reservation.objects.filter(
        court=court,
        date__year=year,
        date__month=month,
        status__in=['confirmed', 'pending']
    ).values_list('date', flat=True).distinct()

    # Skip past dates and check availability for future dates
    today = timezone.now().date()
    availability = {}
    for d in month_days:
        if d < today:
            availability[d.isoformat()] = 'past'
        else:
            slots = court.get_time_slots(d)
            has_available = any(s['available'] for s in slots)
            availability[d.isoformat()] = 'available' if has_available else 'full'

    return JsonResponse({
        'availability': availability,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'today': today.isoformat(),
    })


@login_required
def verify_slot_api(request):
    """API endpoint to verify a specific time slot is still available.
    Called inline before allowing user to proceed to confirmation step."""
    court_id = request.GET.get('court_id')
    date_str = request.GET.get('date')
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    if not all([court_id, date_str, start_str, end_str]):
        return JsonResponse({'available': False, 'message': 'Missing required parameters.'}, status=400)

    try:
        court = Court.objects.get(id=court_id, is_active=True)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start = datetime.strptime(start_str, '%H:%M').time()
        end = datetime.strptime(end_str, '%H:%M').time()
    except (Court.DoesNotExist, ValueError):
        return JsonResponse({'available': False, 'message': 'Invalid court or date/time format.'}, status=400)

    # Check if slot is in the past
    slot_datetime = timezone.make_aware(datetime.combine(date, start))
    if slot_datetime < timezone.now():
        return JsonResponse({'available': False, 'message': 'This time slot has already passed.'})

    # Check for maintenance blocks / closures
    from reservations.services import maintenance_blocks_overlapping
    if maintenance_blocks_overlapping(court, date, start, end).exists():
        return JsonResponse({
            'available': False,
            'message': 'This court is unavailable for the selected time slot (maintenance or closure).'
        })

    # Check for overlapping reservations
    overlapping = Reservation.objects.filter(
        court=court,
        date=date,
        status__in=['confirmed', 'pending']
    ).exclude(
        start_time__gte=end
    ).exclude(
        end_time__lte=start
    )

    if overlapping.exists():
        return JsonResponse({
            'available': False,
            'message': 'Sorry, this time slot was just booked by another user. Please select a different slot.'
        })

    return JsonResponse({'available': True, 'message': 'Slot is available.'})


# ==================== WAITLIST ====================

@login_required
@user_required
def waitlist_list_view(request):
    """Show the signed-in user's active waitlist entries."""
    entries = WaitlistEntry.objects.filter(
        user=request.user,
    ).select_related('court', 'court__site').order_by('-created_at')

    return render(request, 'user/reservations/waitlist_list.html', {
        'entries': entries,
    })


@login_required
@user_required
def waitlist_join_view(request, court_id):
    """Join the waitlist for a fully booked court/time slot."""
    court = get_object_or_404(Court, id=court_id, is_active=True)

    if request.method != 'POST':
        return redirect('court_detail', court_id=court.id)

    try:
        slot_date = datetime.strptime(request.POST.get('date', ''), '%Y-%m-%d').date()
        start_time = datetime.strptime(request.POST.get('start', ''), '%H:%M').time()
        end_time = datetime.strptime(request.POST.get('end', ''), '%H:%M').time()
    except ValueError:
        messages.error(request, 'Invalid date or time for the waitlist.')
        return redirect('court_detail', court_id=court.id)

    try:
        entry, created = join_waitlist(
            user=request.user, court=court, date=slot_date,
            start_time=start_time, end_time=end_time,
        )
    except WaitlistError as exc:
        messages.error(request, str(exc))
        return redirect('court_detail', court_id=court.id)

    if created:
        messages.success(
            request,
            'You have been added to the waitlist. We will notify you if the '
            'slot opens up.',
        )
    else:
        messages.info(request, 'You are already on the waitlist for this slot.')
    return redirect('waitlist_list')


@login_required
@user_required
def waitlist_leave_view(request, entry_id):
    """Remove the signed-in user from a waitlist entry."""
    entry = get_object_or_404(WaitlistEntry, id=entry_id, user=request.user)

    if request.method != 'POST':
        return redirect('waitlist_list')

    if entry.status in ('waiting', 'notified'):
        entry.status = 'cancelled'
        entry.save()
        messages.success(request, 'You have left the waitlist.')
    else:
        messages.info(request, 'This waitlist entry can no longer be cancelled.')

    return redirect('waitlist_list')
