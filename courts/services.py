"""Read helpers shared between courts and reservations for maintenance blocks.

Kept separate from ``reservations.services`` to avoid a circular import:
``reservations.services`` imports ``courts.models``, so ``courts`` cannot
import from it back.
"""

from .models import CourtMaintenanceBlock


def get_maintenance_blocks_for_date(court, date):
    """Return queryset of blocks for ``court`` active at any point on ``date``.

    A block touches ``date`` when its window overlaps that calendar day in the
    project timezone.
    """
    return CourtMaintenanceBlock.objects.filter(
        court=court,
        start_datetime__date__lte=date,
        end_datetime__date__gte=date,
    )
