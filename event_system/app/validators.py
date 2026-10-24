"""Giriş məlumatlarının yoxlanılması (təkrar məntiqi bir yerdə saxlayır)."""
import re
from datetime import date, datetime

from .errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def require_text(data: dict, field: str, label: str, max_len: int = 200) -> str:
    value = str(data.get(field) or "").strip()
    if not value:
        raise ValidationError(f"'{label}' sahəsi boş ola bilməz.")
    if len(value) > max_len:
        raise ValidationError(f"'{label}' maksimum {max_len} simvol ola bilər.")
    return value


def parse_date(value) -> str:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValidationError("Tarix YYYY-MM-DD formatında olmalıdır.")


def parse_time(value) -> str:
    try:
        return datetime.strptime(str(value), "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ValidationError("Saat HH:MM formatında olmalıdır.")


def parse_capacity(value) -> int:
    try:
        capacity = int(value)
    except (TypeError, ValueError):
        raise ValidationError("İştirakçı limiti tam ədəd olmalıdır.")
    if capacity <= 0:
        raise ValidationError("İştirakçı limiti 0-dan böyük olmalıdır.")
    return capacity


def parse_email(value) -> str:
    email = str(value or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("E-poçt ünvanı düzgün deyil.")
    return email


def ensure_not_past(date_iso: str) -> None:
    if date.fromisoformat(date_iso) < date.today():
        raise ValidationError("Tədbirin tarixi keçmişdə ola bilməz.")
