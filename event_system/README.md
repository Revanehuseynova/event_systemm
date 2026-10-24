# Universitet Tədbirlərinin İdarə Edilməsi və Qeydiyyat Sistemi

Fənn: Proqramlaşdırma texnologiyaları · Fərdi layihə (SDF)

## 1. İşə salmaq
```bash
pip install -r requirements.txt
python run.py                    # http://127.0.0.1:5000
python -m unittest discover -v   # testlər
```
Verilənlər bazası (`events.db`) ilk işə salınmada avtomatik yaranır.

## 2. Arxitektura və texnologiya seçimi
```
Brauzer (HTML/CSS/JS)  ──fetch/JSON──►  Flask marşrutları (app/__init__.py)
                                              │
                                        Servislər (app/services.py)   ← biznes qaydaları
                                              │
                                      Repository-lər (app/repositories.py) ← SQL
                                              │
                                         SQLite (schema.sql)
```
| Texnologiya | Niyə seçildi |
|---|---|
| **Python + Flask** | Yüngül, öyrənmək asan, REST API üçün kifayətdir; Django-nun ağır strukturuna ehtiyac yoxdur. |
| **SQLite** | Quraşdırma tələb etmir, FK/UNIQUE/CHECK dəstəyi var, layihə həcminə uyğundur (production üçün PostgreSQL-ə keçid yalnız repository qatını dəyişir). |
| **Vanilla JS** | Framework asılılığı yoxdur; `fetch` ilə backend-lə real əlaqə qurulur. |
| **unittest** | Python-un daxilindədir, əlavə paket tələb etmir. |
| **Git** | Versiya idarəetməsi. |

**SOLID / Clean Code:** hər sinif tək məsuliyyət daşıyır (SRP) – marşrut yalnız HTTP, servis biznes qaydaları, repository yalnız SQL. Servislər konkret DB-yə deyil, ötürülən repository-lərə bağlıdır (DIP). Validasiya `validators.py`-da mərkəzləşib (təkrar kod yoxdur). Xətalar `AppError` iyerarxiyası ilə idarə olunur.

## 3. Verilənlər bazası
```
categories 1───* events 1───* registrations *───1 users
```
| Cədvəl | Əsas sahələr | Qeyd |
|---|---|---|
| categories | id PK, name UNIQUE | Kateqoriyalar (5 standart) |
| users | id PK, full_name, email UNIQUE | |
| events | id PK, title, description, category_id FK, event_date, event_time, location, capacity CHECK(>0) | |
| registrations | id PK, event_id FK, user_id FK, created_at, **UNIQUE(event_id, user_id)** | Əlaqə cədvəli (many-to-many) |

- **Təkrar qeydiyyat:** `UNIQUE(event_id, user_id)` bazada təmin edir – kod səhv etsə belə dublikat yaranmaz.
- **Bütövlük:** `FOREIGN KEY` + `PRAGMA foreign_keys=ON`; tədbir silinəndə qeydiyyatlar `ON DELETE CASCADE` ilə silinir.
- **Limit:** qeydiyyat `BEGIN IMMEDIATE` transaksiyasında (say yoxla → əlavə et) atomik icra olunur; paralel sorğularda limit aşılmır (test 11).
- **Təhlükəsizlik:** bütün SQL sorğuları parametrlidir (`?`), frontend-də istifadəçi mətni `textContent` ilə escape olunur (XSS).

## 4. API
| Metod | Yol | Təsvir |
|---|---|---|
| POST | /api/login | Giriş / avtomatik qeydiyyat (e-poçt ilə) |
| GET/POST | /api/events | Siyahı (`q, category_id, location, date_from, date_to`) / yaratmaq |
| GET/PUT/DELETE | /api/events/{id} | Oxu / redaktə / sil |
| GET | /api/events/{id}/participants | İştirakçılar |
| POST | /api/events/{id}/register, /cancel | Qeydiyyat / ləğv (`user_id`) |
| GET | /api/stats | İdarə paneli statistikası |

## 5. Məlum məhdudiyyətlər
- Giriş sadələşdirilib (parolsuz, e-poçtla). Real sistemdə parol/OAuth və admin rolu əlavə olunmalıdır.
- Tədbirləri hər istifadəçi redaktə edə bilir (rol sistemi yoxdur).

## 6. Fərdi əlavə funksiya
Müəllimin sizə verdiyi əlavə funksiya bura əlavə olunmalıdır (`docs/` qovluğunda təsvir edin).
