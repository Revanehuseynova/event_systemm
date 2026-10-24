"""Flask tətbiqinin fabrikası və HTTP marşrutları (nazik qat - yalnız HTTP ↔ servis)."""
import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from .database import Database
from .errors import AppError
from .repositories import (CategoryRepository, EventRepository, RegistrationRepository,
                           StatsRepository, UserRepository)
from .services import EventService, RegistrationService, StatsService, UserService


def create_app(db_path: str = None) -> Flask:
    app = Flask(__name__, static_folder="../static", static_url_path="")
    db = Database(db_path or os.environ.get("DB_PATH", "events.db"))
    db.init_schema()

    categories, users = CategoryRepository(db), UserRepository(db)
    events, regs, stats = EventRepository(db), RegistrationRepository(db), StatsRepository(db)
    event_svc = EventService(events, categories, regs)
    reg_svc = RegistrationService(events, users, regs)
    user_svc, stats_svc = UserService(users), StatsService(stats)

    def body() -> dict:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise AppError("Sorğunun gövdəsi düzgün JSON olmalıdır.")
        return data

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/categories")
    def list_categories():
        return jsonify(categories.all())

    @app.post("/api/login")
    def login():
        return jsonify(user_svc.login_or_register(body()))

    @app.get("/api/events")
    def list_events():
        return jsonify(event_svc.list(request.args))

    @app.post("/api/events")
    def create_event():
        return jsonify(event_svc.create(body())), 201

    @app.get("/api/events/<int:event_id>")
    def get_event(event_id):
        return jsonify(event_svc.get(event_id))

    @app.put("/api/events/<int:event_id>")
    def update_event(event_id):
        return jsonify(event_svc.update(event_id, body()))

    @app.delete("/api/events/<int:event_id>")
    def delete_event(event_id):
        event_svc.delete(event_id)
        return "", 204

    @app.get("/api/events/<int:event_id>/participants")
    def participants(event_id):
        return jsonify(event_svc.participants(event_id))

    @app.post("/api/events/<int:event_id>/register")
    def register(event_id):
        return jsonify(reg_svc.register(event_id, _user_id(body()))), 201

    @app.post("/api/events/<int:event_id>/cancel")
    def cancel(event_id):
        reg_svc.cancel(event_id, _user_id(body()))
        return "", 204

    @app.get("/api/users/<int:user_id>/registrations")
    def user_registrations(user_id):
        return jsonify(reg_svc.user_events(user_id))

    @app.get("/api/stats")
    def get_stats():
        return jsonify(stats_svc.dashboard())

    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"error": err.message}), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http(err):
        messages = {404: "Səhifə və ya resurs tapılmadı.", 405: "Bu sorğu metodu icazə verilmir."}
        return jsonify({"error": messages.get(err.code, err.description)}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception(err)
        return jsonify({"error": "Gözlənilməyən xəta baş verdi. Zəhmət olmasa bir az sonra yenidən cəhd edin."}), 500

    return app


def _user_id(data: dict) -> int:
    try:
        return int(data.get("user_id"))
    except (TypeError, ValueError):
        raise AppError("İstifadəçi identifikatoru düzgün deyil.")
