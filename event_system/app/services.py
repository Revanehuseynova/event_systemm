"""Biznes məntiqi qatı. Repository-lərdən asılıdır, HTTP-dən asılı deyil (SOLID: SRP, DIP)."""
from datetime import date

from . import validators as v
from .errors import ConflictError, NotFoundError, ValidationError


class UserService:
    def __init__(self, users):
        self.users = users

    def login_or_register(self, data: dict) -> dict:
        email = v.parse_email(data.get("email"))
        existing = self.users.get_by_email(email)
        if existing:
            return existing
        return self.users.create(v.require_text(data, "full_name", "Ad və soyad", 100), email)


class EventService:
    def __init__(self, events, categories, registrations):
        self.events, self.categories, self.registrations = events, categories, registrations

    @staticmethod
    def _decorate(event: dict) -> dict:
        event["is_past"] = event["event_date"] < date.today().isoformat()
        event["is_full"] = event["registered"] >= event["capacity"]
        return event

    def _validate(self, data: dict, require_future: bool) -> dict:
        try:
            category_id = int(data.get("category_id"))
        except (TypeError, ValueError):
            raise ValidationError("Kateqoriya seçilməlidir.")
        if not self.categories.exists(category_id):
            raise ValidationError("Seçilmiş kateqoriya mövcud deyil.")
        event_date = v.parse_date(data.get("event_date"))
        if require_future:
            v.ensure_not_past(event_date)
        return {
            "title": v.require_text(data, "title", "Ad", 150),
            "description": str(data.get("description") or "").strip()[:2000],
            "category_id": category_id,
            "event_date": event_date,
            "event_time": v.parse_time(data.get("event_time")),
            "location": v.require_text(data, "location", "Yer", 150),
            "capacity": v.parse_capacity(data.get("capacity")),
        }

    def list(self, filters: dict) -> list:
        cat = filters.get("category_id")
        rows = self.events.search(
            q=(filters.get("q") or "").strip(),
            category_id=int(cat) if str(cat or "").isdigit() else None,
            date_from=v.parse_date(filters["date_from"]) if filters.get("date_from") else None,
            date_to=v.parse_date(filters["date_to"]) if filters.get("date_to") else None,
            location=(filters.get("location") or "").strip(),
        )
        return [self._decorate(r) for r in rows]

    def get(self, event_id: int) -> dict:
        event = self.events.get(event_id)
        if not event:
            raise NotFoundError("Tədbir tapılmadı.")
        return self._decorate(event)

    def create(self, data: dict) -> dict:
        return self.get(self.events.create(self._validate(data, require_future=True)))

    def update(self, event_id: int, data: dict) -> dict:
        current = self.get(event_id)
        # Tarix dəyişməyibsə, keçmiş tədbirin digər sahələrini redaktə etmək olar
        require_future = data.get("event_date") != current["event_date"]
        clean = self._validate(data, require_future)
        if clean["capacity"] < current["registered"]:
            raise ValidationError(
                f"Limit cari qeydiyyat sayından ({current['registered']}) az ola bilməz.")
        self.events.update(event_id, clean)
        return self.get(event_id)

    def delete(self, event_id: int) -> None:
        self.get(event_id)
        self.events.delete(event_id)

    def participants(self, event_id: int) -> list:
        self.get(event_id)
        return self.registrations.participants(event_id)


class RegistrationService:
    def __init__(self, events, users, registrations):
        self.events, self.users, self.registrations = events, users, registrations

    def register(self, event_id: int, user_id: int) -> dict:
        event = self.events.get(event_id)
        if not event:
            raise NotFoundError("Tədbir tapılmadı.")
        if not self.users.get(user_id):
            raise NotFoundError("İstifadəçi tapılmadı.")
        if event["event_date"] < date.today().isoformat():
            raise ValidationError("Keçmiş tədbirə qeydiyyat mümkün deyil.")
        result = self.registrations.add_if_capacity(event_id, user_id)
        if result == "duplicate":
            raise ConflictError("Siz bu tədbirə artıq qeydiyyatdan keçmisiniz.")
        if result == "full":
            raise ConflictError("Tədbirin iştirakçı limiti dolub.")
        return self.events.get(event_id)

    def cancel(self, event_id: int, user_id: int) -> None:
        if not self.registrations.remove(event_id, user_id):
            raise NotFoundError("Belə bir qeydiyyat tapılmadı.")

    def user_events(self, user_id: int) -> list:
        return self.registrations.event_ids_of_user(user_id)


class StatsService:
    def __init__(self, stats):
        self.stats = stats

    def dashboard(self) -> dict:
        return {**self.stats.totals(), "top_events": self.stats.top_events(),
                "by_category": self.stats.by_category()}
