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

from datetime import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from courts.models import Court
from equipment.models import Equipment

from .models import Reservation, ReservationEquipment, WaitlistEntry


class SlotUnavailable(Exception):
    """Raised when a court/time slot is taken by a competing booking."""


class WaitlistError(Exception):
    """Raised when a waitlist action is not valid for the current slot state."""


def ensure_slot_available(court, date, start_time, end_time, exclude_reservation_id=None):
    """Raise :class:`SlotUnavailable` if the slot overlaps an active booking.

    Two time ranges overlap when ``start < other_end`` and ``end > other_start``;
    ranges that merely touch (09:00-11:00 vs 11:00-13:00) do not.
    """
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
