"""Domain services for reservation booking.

Booking is the app's money path and its most concurrency-sensitive operation.
Before this module, every availability check was a check-then-act: two requests
for the same court/time could both run the overlap ``SELECT`` and both insert a
``Reservation`` (double booking), and two equipment rentals could both read the
same ``quantity_available`` and both decrement it (overselling).

The functions here always run their reads and writes inside a single
``transaction.atomic()`` block and take a row lock with ``select_for_update()``
before re-checking availability, so a concurrent writer blocks until the first
transaction commits and then sees the committed row.

MySQL has no exclusion constraints, so this application-level lock is the only
guard until the project moves to PostgreSQL (see AUDIT.md §6), where a
``daterange`` exclusion constraint can additionally back this up in the database.
"""

from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from courts.models import Court, CourtMaintenanceBlock
from equipment.models import Equipment

from .models import Reservation, ReservationEquipment, WaitlistEntry


class SlotUnavailable(Exception):
    """Raised when a court/time slot is taken by a competing booking."""


class WaitlistError(Exception):
    """Raised when a waitlist action is not valid for the current slot state."""


def _booking_window(date, start_time, end_time):
    """Return the aware ``(start, end)`` datetimes of a same-day booking.

    All bookings are same-day, so comparing aware datetimes against the
    block windows in the project timezone is a faithful overlap test.
    """
    tz = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(date, start_time), tz),
        timezone.make_aware(datetime.combine(date, end_time), tz),
    )


def maintenance_blocks_overlapping(court, date, start_time, end_time):
    """Return maintenance/closure blocks overlapping the booking window."""
    slot_start, slot_end = _booking_window(date, start_time, end_time)
    return CourtMaintenanceBlock.objects.filter(
        court=court,
        start_datetime__lt=slot_end,
        end_datetime__gt=slot_start,
    )


def ensure_slot_available(court, date, start_time, end_time, exclude_reservation_id=None):
    """Raise :class:`SlotUnavailable` if the slot overlaps an active booking
    or falls inside a maintenance window / closure.

    Two time ranges overlap when ``start < other_end`` and ``end > other_start``;
    ranges that merely touch (09:00-11:00 vs 11:00-13:00) do not.
    """
    if maintenance_blocks_overlapping(court, date, start_time, end_time).exists():
        raise SlotUnavailable(
            f'{court.name} is unavailable for the selected time slot '
            f'(maintenance or closure).'
        )

    active = Reservation.objects.filter(
        court=court,
        date=date,
        status__in=['pending', 'confirmed'],
    )
    if exclude_reservation_id is not None:
        active = active.exclude(pk=exclude_reservation_id)
    overlapping = active.exclude(start_time__gte=end_time).exclude(end_time__lte=start_time)
    if overlapping.exists():
        raise SlotUnavailable(
            f'{court.name} is already booked for the selected time slot.'
        )


def lock_court_and_ensure_available(court, date, start_time, end_time,
                                    exclude_reservation_id=None):
    """Lock the court row and re-check availability under that lock.

    Returns the refreshed, locked ``Court`` instance. Must be called from inside
    an open transaction; the lock is held until that transaction commits.
    """
    locked_court = Court.objects.select_for_update().get(pk=court.pk)
    ensure_slot_available(
        locked_court, date, start_time, end_time, exclude_reservation_id,
    )
    return locked_court


def consume_equipment(reservation, equipment_ids):
    """Attach equipment to a reservation, decrementing stock under a row lock.

    Returns the total rental fee (as ``Decimal``). Equipment that is missing,
    inactive or out of stock is skipped rather than raising, matching the
    previous best-effort behaviour at checkout.
    """
    equipment_fee = 0
    seen = set()
    for raw_id in equipment_ids or []:
        try:
            eq_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if eq_id in seen:
            # Never attach the same inventory line twice for one reservation.
            continue
        seen.add(eq_id)

        try:
            equipment = Equipment.objects.select_for_update().get(
                id=eq_id, is_active=True,
            )
        except Equipment.DoesNotExist:
            continue

        if equipment.quantity_available <= 0:
            continue

        ReservationEquipment.objects.create(
            reservation=reservation,
            equipment=equipment,
            quantity=1,
            rental_fee=equipment.rental_price,
        )
        # Atomic decrement so a concurrent locker that slipped through cannot
        # resurrect stock with a stale in-memory value.
        Equipment.objects.filter(pk=equipment.pk).update(
            quantity_available=F('quantity_available') - 1,
        )
        equipment_fee += equipment.rental_price
    return equipment_fee


def create_reservation_atomic(*, user, court, date, start_time, end_time,
                              checkout_data, status='pending'):
    """Create a reservation and consume equipment atomically.

    Locks the court row, re-checks the slot, then creates the reservation and
    attaches equipment inside one transaction. Raises :class:`SlotUnavailable`
    when the slot was taken by a competing transaction.

    The court's own ``hourly_rate`` is used for pricing rather than any value
    cached in the session, so a tampered checkout payload cannot change the
    price.
    """
    equipment_ids = list(checkout_data.get('equipment_ids', []) or [])
    with transaction.atomic():
        locked_court = lock_court_and_ensure_available(
            court, date, start_time, end_time,
        )
        reservation = Reservation.objects.create(
            user=user,
            court=locked_court,
            date=date,
            start_time=start_time,
            end_time=end_time,
            duration_hours=checkout_data.get('duration_hours') or 0.5,
            hourly_rate=locked_court.hourly_rate,
            subtotal=0,
            equipment_fee=0,
            total_amount=0,
            status=status,
            notes=checkout_data.get('notes', ''),
            match_name=checkout_data.get('match_name', ''),
            match_format=checkout_data.get('match_format', 'singles'),
            game_type=checkout_data.get('game_type', 'friendly'),
            scoring_format=checkout_data.get('scoring_format', '11'),
            points_per_game=checkout_data.get('points_per_game') or 11,
            games_to_win=checkout_data.get('games_to_win') or 2,
            win_by_two=(
                checkout_data.get('win_by_two')
                if checkout_data.get('win_by_two') is not None else True
            ),
            team1_player2_id=checkout_data.get('team1_player2_id'),
            team2_player1_id=checkout_data.get('team2_player1_id'),
            team2_player2_id=checkout_data.get('team2_player2_id'),
            team1_name=checkout_data.get('team1_name', ''),
            team2_name=checkout_data.get('team2_name', ''),
            guest_players_data=checkout_data.get('guest_players_data'),
        )
        reservation.equipment_fee = consume_equipment(reservation, equipment_ids)
        # Reservation.save() recalculates duration/subtotal/total_amount from
        # the persisted fields.
        reservation.save()

        # If this booking fills a slot the user was waiting for, mark that
        # waitlist entry as claimed so it is not offered again.
        WaitlistEntry.objects.filter(
            user=user, court=locked_court, date=date,
            start_time=start_time, end_time=end_time,
            status__in=['waiting', 'notified'],
        ).update(status='claimed', claimed_at=timezone.now())

    return reservation


def join_waitlist(*, user, court, date, start_time, end_time,
                  preferred_slot_only=True):
    """Add a user to the waitlist for a fully booked slot.

    Returns ``(entry, created)``. Raises :class:`WaitlistError` when the slot is
    still bookable, is in the past, or the user already has a pending entry.
    """
    if end_time <= start_time:
        raise WaitlistError('End time must be after start time.')

    slot_datetime = timezone.make_aware(datetime.combine(date, start_time))
    if slot_datetime < timezone.now():
        raise WaitlistError('This time slot has already passed.')

    if maintenance_blocks_overlapping(court, date, start_time, end_time).exists():
        raise WaitlistError(
            'This court is unavailable for the selected time slot '
            '(maintenance or closure).'
        )

    if ensure_slot_free(court, date, start_time, end_time):
        raise WaitlistError('This slot is still available; book it directly.')

    existing = WaitlistEntry.objects.filter(
        user=user, court=court, date=date,
        start_time=start_time, end_time=end_time,
        status__in=['waiting', 'notified'],
    ).first()
    if existing:
        return existing, False

    entry = WaitlistEntry.objects.create(
        user=user, court=court, date=date,
        start_time=start_time, end_time=end_time,
        preferred_slot_only=preferred_slot_only,
        status='waiting',
    )
    return entry, True


def ensure_slot_free(court, date, start_time, end_time):
    """Return True when no active booking overlaps the slot (inverse of
    :func:`ensure_slot_available`, without raising)."""
    try:
        ensure_slot_available(court, date, start_time, end_time)
    except SlotUnavailable:
        return False
    return True


def release_slot_and_notify_waitlist(reservation):
    """Offer a freed slot to the next waitlisted user.

    Called when a reservation is cancelled, rejected, or expired so the slot
    does not sit idle while people are queued for it.
    """
    return WaitlistEntry.notify_next(
        reservation.court, reservation.date,
        reservation.start_time, reservation.end_time,
    )


def expire_stale_pending_reservations(older_than_minutes=30, now=None):
    """Cancel unpaid reservations that have held their slot for too long.

    A booking is created as ``pending`` at checkout and only becomes
    ``confirmed`` once paid. If the user abandons cash/online payment the slot
    would otherwise be held forever, so anything still pending after
    ``older_than_minutes`` is cancelled, its equipment returned to stock, its
    payment marked failed, and the freed slot offered to the waitlist.

    Returns the list of expired reservation ids. Safe to run repeatedly; each
    reservation is locked so a concurrent payment is never clobbered.
    """
    cutoff = (now or timezone.now()) - timedelta(minutes=older_than_minutes)
    candidates = Reservation.objects.filter(
        status='pending', created_at__lt=cutoff,
    ).values_list('id', flat=True)

    expired_ids = []
    for reservation_id in list(candidates):
        with transaction.atomic():
            reservation = (
                Reservation.objects.select_for_update()
                .select_related('court')
                .get(pk=reservation_id)
            )
            # Re-check under the lock: it may have been paid or cancelled since.
            if reservation.status != 'pending':
                continue

            payment = _get_payment(reservation)
            if payment is not None and payment.status == 'paid':
                continue

            # Return any reserved equipment to stock.
            for rental in reservation.rented_equipment.select_related('equipment'):
                Equipment.objects.filter(pk=rental.equipment_id).update(
                    quantity_available=F('quantity_available') + rental.quantity,
                )

            reservation.status = 'cancelled'
            reservation.save(update_fields=['status'])

            if payment is not None:
                payment.status = 'failed'
                payment.payment_notes = 'Cancelled: unpaid hold expired'
                payment.save(update_fields=['status', 'payment_notes'])

        release_slot_and_notify_waitlist(reservation)
        expired_ids.append(reservation.id)

    return expired_ids


def cancel_reservations_for_block(block):
    """Cancel reservations overlapped by a new maintenance block / closure.

    For each affected pending/confirmed reservation: return its equipment to
    stock, mark it cancelled, fail any non-paid payment, and notify the owner
    (in-app notification in the ``maintenance`` category plus a cancellation
    email). Waitlist entries for the covered slots are cancelled too so users
    are not notified about slots that no longer exist.

    Returns the list of cancelled reservation ids. Safe to call again: an
    already-cancelled reservation is skipped, so re-saving a block (which
    re-runs the overlap scan) never double-cancels or re-notifies.
    """
    from notifications.email_utils import send_reservation_cancelled_email
    from notifications.models import Notification

    affected = (
        Reservation.objects
        .select_related('court', 'user')
        .filter(
            court=block.court,
            status__in=['pending', 'confirmed'],
            # Reservations on any calendar day the block touches; the precise
            # time overlap is re-checked below against each reservation window.
            date__gte=block.start_datetime.date(),
            date__lte=block.end_datetime.date(),
        )
    )

    cancelled_ids = []
    for reservation in affected:
        res_start, res_end = _booking_window(
            reservation.date, reservation.start_time, reservation.end_time,
        )
        if not (res_start < block.end_datetime and res_end > block.start_datetime):
            continue

        with transaction.atomic():
            locked = Reservation.objects.select_for_update().get(pk=reservation.pk)
            if locked.status not in ('pending', 'confirmed'):
                continue

            for rental in locked.rented_equipment.select_related('equipment'):
                Equipment.objects.filter(pk=rental.equipment_id).update(
                    quantity_available=F('quantity_available') + rental.quantity,
                )

            locked.status = 'cancelled'
            locked.save(update_fields=['status'])

            payment = _get_payment(locked)
            if payment is not None and payment.status != 'paid':
                payment.status = 'failed'
                payment.payment_notes = 'Cancelled: court closed for maintenance'
                payment.save(update_fields=['status', 'payment_notes'])

            Notification.objects.create(
                user=locked.user,
                title='Court unavailable - reservation cancelled',
                message=(
                    f'Your reservation for {locked.court.name} on '
                    f'{locked.date.strftime("%b %d, %Y")} '
                    f'({locked.start_time.strftime("%I:%M %p")} - '
                    f'{locked.end_time.strftime("%I:%M %p")}) was cancelled '
                    f'because the court is {block.get_block_type_display().lower()} '
                    f'during that time.'
                ),
                notification_type='warning',
                category='maintenance',
                priority='high',
                action_url=f'/user/reservations/{locked.id}/',
                action_text='View Details',
            )

        send_reservation_cancelled_email(locked.user, locked)
        cancelled_ids.append(locked.id)

    # Waitlist entries for the blocked court whose day overlaps the block.
    WaitlistEntry.objects.filter(
        court=block.court,
        status__in=['waiting', 'notified'],
        date__gte=block.start_datetime.date(),
        date__lte=block.end_datetime.date(),
    ).update(status='cancelled')

    return cancelled_ids


def _get_payment(reservation):
    """Return the reservation's payment or None without raising."""
    try:
        return reservation.payment
    except Exception:
        return None
