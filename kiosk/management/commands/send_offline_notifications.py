"""
Management command: send_offline_notifications

Checks all EKiosk instances that are currently offline and have not yet been
notified, then sends an alert email to EKIOSK_ALERT_EMAIL.

Usage:
    python manage.py send_offline_notifications

Recommended: run via cron every 5 minutes, e.g.
    */5 * * * * /path/to/venv/bin/python /app/manage.py send_offline_notifications
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings

from kiosk.models import EKiosk


def _format_bytes(value):
    if value is None:
        return "—"
    if value > 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} GB"
    return f"{value / 1_000_000:.0f} MB"


def _build_email_html(offline_kiosks):
    now_str = timezone.localtime(timezone.now()).strftime("%d %b %Y, %H:%M %Z")
    rows = ""
    for k in offline_kiosks:
        last_hb = (
            timezone.localtime(k.last_heartbeat).strftime("%d %b %Y, %H:%M %Z")
            if k.last_heartbeat else "Never"
        )
        delta_str = "—"
        if k.last_heartbeat:
            delta = timezone.now() - k.last_heartbeat
            mins = int(delta.total_seconds() // 60)
            if mins < 60:
                delta_str = f"{mins} menit yang lalu"
            else:
                hours = mins // 60
                delta_str = f"{hours} jam {mins % 60} menit yang lalu"

        region_name = k.region.name if k.region else "—"
        coords = (
            f"{float(k.latitude):.5f}, {float(k.longitude):.5f}"
            if k.latitude and k.longitude else "—"
        )

        rows += f"""
        <tr style="border-bottom:1px solid #F0EBE3;">
          <td style="padding:12px 16px;font-weight:600;color:#1A1A18;">{k.name}</td>
          <td style="padding:12px 16px;color:#7A7670;">{region_name}</td>
          <td style="padding:12px 16px;">
            <span style="background:#FDECEA;color:#C0392B;border-radius:12px;padding:3px 10px;font-size:12px;font-weight:500;">
              Offline
            </span>
          </td>
          <td style="padding:12px 16px;color:#C0392B;font-size:13px;">{delta_str}</td>
          <td style="padding:12px 16px;color:#7A7670;font-size:13px;">{last_hb}</td>
          <td style="padding:12px 16px;color:#7A7670;font-size:13px;">{k.last_ip_address or "—"}</td>
          <td style="padding:12px 16px;color:#7A7670;font-size:13px;">{_format_bytes(k.last_storage_free)}</td>
          <td style="padding:12px 16px;color:#7A7670;font-size:13px;">{k.last_app_version or "—"}</td>
          <td style="padding:12px 16px;color:#7A7670;font-size:13px;">{coords}</td>
        </tr>"""

    count = len(offline_kiosks)
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#F5F1EA;font-family:'Inter',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F1EA;padding:32px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:12px;overflow:hidden;border:1px solid #E5E0D8;">

        <!-- Header -->
        <tr>
          <td style="background:#C0392B;padding:24px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <div style="color:#FFFFFF;font-size:11px;letter-spacing:1px;text-transform:uppercase;opacity:0.8;margin-bottom:6px;">
                    eKiosk IKN &mdash; Sistem Monitoring
                  </div>
                  <div style="color:#FFFFFF;font-size:22px;font-weight:700;">
                    &#9888;&#65039; Peringatan: {count} eKiosk Offline
                  </div>
                </td>
                <td align="right">
                  <div style="background:rgba(255,255,255,0.15);border-radius:8px;padding:10px 16px;text-align:center;">
                    <div style="color:#FFFFFF;font-size:28px;font-weight:700;">{count}</div>
                    <div style="color:rgba(255,255,255,0.8);font-size:11px;">Kiosk Offline</div>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Alert timestamp -->
        <tr>
          <td style="background:#FEF2F2;border-bottom:1px solid #FECACA;padding:12px 32px;">
            <span style="color:#C0392B;font-size:13px;">
              &#128337; Terdeteksi pada: <strong>{now_str}</strong>
            </span>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:28px 32px;">
            <p style="margin:0 0 8px;font-size:15px;color:#1A1A18;">Yth. Tim Operasional eKiosk IKN,</p>
            <p style="margin:0 0 20px;font-size:14px;color:#5A5650;line-height:1.6;">
              Sistem monitoring mendeteksi <strong style="color:#C0392B;">{count} eKiosk</strong> yang
              tidak memberikan heartbeat melebihi batas waktu normal. Berikut adalah daftar kiosk
              yang perlu segera ditangani:
            </p>

            <!-- Table -->
            <div style="overflow-x:auto;border-radius:8px;border:1px solid #E5E0D8;">
              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
                <thead>
                  <tr style="background:#F9F6F1;border-bottom:2px solid #E5E0D8;">
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Nama Kiosk</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Region</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Status</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Terakhir Online</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Waktu Heartbeat</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">IP Address</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Storage</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Versi App</th>
                    <th style="padding:10px 16px;text-align:left;color:#8A8680;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Koordinat</th>
                  </tr>
                </thead>
                <tbody>
                  {rows}
                </tbody>
              </table>
            </div>

            <p style="margin:24px 0 0;font-size:13px;color:#8A8680;line-height:1.6;">
              Kiosk dinyatakan offline apabila tidak ada heartbeat selama lebih dari
              <strong>3x interval heartbeat</strong> (default: 15 menit).
              Notifikasi ini hanya dikirim sekali per kejadian offline; notifikasi berikutnya akan
              dikirim setelah kiosk kembali online lalu offline lagi.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F9F6F1;border-top:1px solid #E5E0D8;padding:16px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="font-size:12px;color:#A8A49C;">
                  eKiosk CMS &mdash; IKN Nusantara &bull; Pesan otomatis, jangan dibalas
                </td>
                <td align="right" style="font-size:12px;color:#A8A49C;">
                  {now_str}
                </td>
              </tr>
            </table>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _build_email_text(offline_kiosks):
    now_str = timezone.localtime(timezone.now()).strftime("%d %b %Y, %H:%M %Z")
    lines = [
        f"[eKiosk IKN] PERINGATAN: {len(offline_kiosks)} eKiosk Offline",
        f"Terdeteksi pada: {now_str}",
        "=" * 60,
        "",
    ]
    for k in offline_kiosks:
        last_hb = (
            timezone.localtime(k.last_heartbeat).strftime("%d %b %Y, %H:%M %Z")
            if k.last_heartbeat else "Never"
        )
        lines += [
            f"Kiosk   : {k.name}",
            f"Region  : {k.region.name if k.region else '—'}",
            f"IP      : {k.last_ip_address or '—'}",
            f"Heartbeat: {last_hb}",
            f"App Ver : {k.last_app_version or '—'}",
            f"Storage : {_format_bytes(k.last_storage_free)}",
            "-" * 40,
        ]
    lines += [
        "",
        "Kiosk dinyatakan offline bila tidak ada heartbeat > 3x interval.",
        "Notifikasi ini dikirim sekali per kejadian offline.",
    ]
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Send email alerts for eKiosk devices that are currently offline and not yet notified."

    def handle(self, *args, **options):
        alert_email = getattr(settings, 'EKIOSK_ALERT_EMAIL', 'ekioskoikn@gmail.com')

        all_kiosks = EKiosk.objects.select_related('region').all()
        to_notify = [
            k for k in all_kiosks
            if k.status == EKiosk.Status.OFFLINE and k.offline_notified_at is None
        ]

        if not to_notify:
            self.stdout.write("No new offline kiosks to notify.")
            return

        self.stdout.write(f"Found {len(to_notify)} offline kiosk(s) to notify: "
                          f"{', '.join(k.name for k in to_notify)}")

        subject = f"[eKiosk IKN] {len(to_notify)} Kiosk Offline — Tindakan Diperlukan"
        html_body = _build_email_html(to_notify)
        text_body = _build_email_text(to_notify)

        try:
            send_mail(
                subject=subject,
                message=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alert_email],
                html_message=html_body,
                fail_silently=False,
            )
            now = timezone.now()
            EKiosk.objects.filter(id__in=[k.id for k in to_notify]).update(
                offline_notified_at=now
            )
            self.stdout.write(self.style.SUCCESS(
                f"Alert sent to {alert_email} for {len(to_notify)} kiosk(s)."
            ))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to send email: {exc}"))
