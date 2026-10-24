"""Test ssenariləri (unittest). İşə salmaq: python -m unittest discover -v"""
import os
import tempfile
import threading
import unittest
from datetime import date, timedelta

from app import create_app

FUTURE = (date.today() + timedelta(days=30)).isoformat()
PAST = (date.today() - timedelta(days=30)).isoformat()


class BaseCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.client = create_app(self.path).test_client()

    def tearDown(self):
        os.remove(self.path)

    def make_event(self, **over):
        data = {"title": "AI Konfransı", "description": "Test", "category_id": 1,
                "event_date": FUTURE, "event_time": "10:00", "location": "Zal 1", "capacity": 2}
        data.update(over)
        return self.client.post("/api/events", json=data)

    def make_user(self, n=1):
        r = self.client.post("/api/login", json={"full_name": f"Tələbə {n}", "email": f"t{n}@univ.az"})
        return r.get_json()["id"]


class TestEvents(BaseCase):
    def test_01_create_event_success(self):
        r = self.make_event()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["registered"], 0)

    def test_02_empty_required_field_rejected(self):
        self.assertEqual(self.make_event(title="  ").status_code, 400)

    def test_03_past_date_and_bad_capacity_rejected(self):
        self.assertEqual(self.make_event(event_date=PAST).status_code, 400)
        self.assertEqual(self.make_event(capacity=0).status_code, 400)
        self.assertEqual(self.make_event(event_date="31-12-2030").status_code, 400)

    def test_04_search_by_name_category_and_no_result(self):
        self.make_event(title="Python Təlimi", category_id=3)
        self.make_event(title="Robot Müsabiqəsi", category_id=4)
        self.assertEqual(len(self.client.get("/api/events?q=python").get_json()), 1)
        self.assertEqual(len(self.client.get("/api/events?category_id=4").get_json()), 1)
        self.assertEqual(self.client.get("/api/events?q=yoxdur").get_json(), [])

    def test_05_update_and_delete(self):
        eid = self.make_event().get_json()["id"]
        r = self.client.put(f"/api/events/{eid}", json={
            "title": "Yeni ad", "category_id": 1, "event_date": FUTURE,
            "event_time": "11:30", "location": "Zal 2", "capacity": 5})
        self.assertEqual(r.get_json()["title"], "Yeni ad")
        self.assertEqual(self.client.delete(f"/api/events/{eid}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/events/{eid}").status_code, 404)

    def test_06_capacity_cannot_drop_below_registered(self):
        eid = self.make_event(capacity=3).get_json()["id"]
        for n in (1, 2):
            self.client.post(f"/api/events/{eid}/register", json={"user_id": self.make_user(n)})
        r = self.client.put(f"/api/events/{eid}", json={
            "title": "A", "category_id": 1, "event_date": FUTURE,
            "event_time": "10:00", "location": "Y", "capacity": 1})
        self.assertEqual(r.status_code, 400)


class TestRegistration(BaseCase):
    def test_07_register_success_and_count(self):
        eid, uid = self.make_event().get_json()["id"], self.make_user()
        r = self.client.post(f"/api/events/{eid}/register", json={"user_id": uid})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["registered"], 1)

    def test_08_duplicate_registration_blocked(self):
        eid, uid = self.make_event().get_json()["id"], self.make_user()
        self.client.post(f"/api/events/{eid}/register", json={"user_id": uid})
        r = self.client.post(f"/api/events/{eid}/register", json={"user_id": uid})
        self.assertEqual(r.status_code, 409)

    def test_09_capacity_limit_enforced(self):
        eid = self.make_event(capacity=2).get_json()["id"]
        codes = [self.client.post(f"/api/events/{eid}/register", json={"user_id": self.make_user(n)}).status_code
                 for n in (1, 2, 3)]
        self.assertEqual(codes, [201, 201, 409])

    def test_10_cancel_frees_a_seat(self):
        eid = self.make_event(capacity=1).get_json()["id"]
        u1, u2 = self.make_user(1), self.make_user(2)
        self.client.post(f"/api/events/{eid}/register", json={"user_id": u1})
        self.assertEqual(self.client.post(f"/api/events/{eid}/register", json={"user_id": u2}).status_code, 409)
        self.assertEqual(self.client.post(f"/api/events/{eid}/cancel", json={"user_id": u1}).status_code, 204)
        self.assertEqual(self.client.post(f"/api/events/{eid}/register", json={"user_id": u2}).status_code, 201)

    def test_11_concurrent_registration_never_exceeds_capacity(self):
        eid = self.make_event(capacity=3).get_json()["id"]
        users = [self.make_user(n) for n in range(8)]
        results = []

        def go(uid):
            results.append(self.client.post(f"/api/events/{eid}/register", json={"user_id": uid}).status_code)

        threads = [threading.Thread(target=go, args=(u,)) for u in users]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(self.client.get(f"/api/events/{eid}").get_json()["registered"], 3)


class TestSecurityAndStats(BaseCase):
    def test_12_sql_injection_attempt_is_harmless(self):
        self.make_event()
        r = self.client.get("/api/events", query_string={"q": "'; DROP TABLE events;--"})
        self.assertEqual(r.get_json(), [])
        self.assertEqual(len(self.client.get("/api/events").get_json()), 1)

    def test_13_invalid_email_and_bad_json(self):
        self.assertEqual(self.client.post("/api/login", json={"full_name": "A", "email": "xx"}).status_code, 400)
        self.assertEqual(self.client.post("/api/events", data="not json").status_code, 400)

    def test_14_stats(self):
        e1 = self.make_event(title="A", category_id=1).get_json()["id"]
        self.make_event(title="B", category_id=2)
        for n in (1, 2):
            self.client.post(f"/api/events/{e1}/register", json={"user_id": self.make_user(n)})
        s = self.client.get("/api/stats").get_json()
        self.assertEqual((s["total_events"], s["total_registrations"]), (2, 2))
        self.assertEqual(s["top_events"][0]["title"], "A")
        self.assertEqual({c["category"]: c["events"] for c in s["by_category"]}["Seminar"], 1)

    def test_15_duplicate_message_even_when_event_is_full(self):
        eid, uid = self.make_event(capacity=1).get_json()["id"], self.make_user()
        self.client.post(f"/api/events/{eid}/register", json={"user_id": uid})
        r = self.client.post(f"/api/events/{eid}/register", json={"user_id": uid})
        self.assertEqual(r.status_code, 409)
        self.assertIn("artıq", r.get_json()["error"])

    def test_16_wrong_method_returns_405_json(self):
        r = self.client.patch("/api/events/1")
        self.assertEqual(r.status_code, 405)
        self.assertIn("error", r.get_json())


if __name__ == "__main__":
    unittest.main()
