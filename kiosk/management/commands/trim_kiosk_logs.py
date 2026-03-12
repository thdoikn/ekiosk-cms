"""
Management command: trim_kiosk_logs

Deletes KioskLog entries older than a specified number of days.
This keeps log retention time-based instead of per-kiosk count-based,
which is simpler and more efficient for regular heartbeat data.

Usage:
    python manage.py trim_kiosk_logs             # default: delete logs older than 7 days
    python manage.py trim_kiosk_logs --days 14   # delete logs older than 14 days

Recommended cron (daily at 02:00):
    0 2 * * * /path/to/venv/bin/python /app/manage.py trim_kiosk_logs
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from kiosk.models import KioskLog


class Command(BaseCommand):
    help = "Delete KioskLog entries older than a specified number of days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Delete logs older than this many days (default: 7)",
        )

    def handle(self, *args, **options):
        days = options["days"]

        if days < 1:
            self.stderr.write(self.style.ERROR("--days must be at least 1"))
            return

        cutoff = timezone.now() - timedelta(days=days)

        deleted, _ = KioskLog.objects.filter(
            checked_at__lt=cutoff
        ).delete()

        if deleted:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted} log entries older than {days} days."
                )
            )
        else:
            self.stdout.write("No old logs to delete.")
