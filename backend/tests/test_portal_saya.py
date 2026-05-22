"""
Portal Saya + My Workspace - Backend API tests
Endpoints: /api/portal/*
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_headers():
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@garment.com", "password": "Admin@123"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json().get("token") or resp.json().get("access_token")
    assert token, "No token returned"
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── SELF-SERVICE HR ──────────────────────────────────────────────────

class TestPortalProfile:
    def test_get_profile(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/profile", headers=auth_headers)
        assert r.status_code == 200
        d = r.json()
        assert "email" in d
        assert "is_linked" in d
        print(f"Profile loaded. is_linked={d['is_linked']}, email={d['email']}")

    def test_update_profile(self, auth_headers):
        r = requests.put(f"{BASE_URL}/api/portal/profile", headers=auth_headers, json={
            "nama_panggilan": "TestAdmin",
            "no_hp": "081234567890",
            "alamat": "Test Address 123"
        })
        assert r.status_code == 200
        d = r.json()
        assert d.get("nama_panggilan") == "TestAdmin"
        print(f"Profile updated: nama_panggilan={d.get('nama_panggilan')}")


class TestPortalDashboard:
    def test_get_dashboard(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/dashboard", headers=auth_headers)
        assert r.status_code == 200
        d = r.json()
        assert "is_linked" in d
        assert "todos" in d
        print(f"Dashboard loaded. is_linked={d['is_linked']}, todos={d['todos']}")


class TestPortalLeave:
    def test_get_leave_unlinked(self, auth_headers):
        """Admin is not linked to employee — expect 409"""
        r = requests.get(f"{BASE_URL}/api/portal/leave", headers=auth_headers)
        assert r.status_code == 409
        print(f"Leave returns 409 for unlinked user: {r.json().get('detail')}")

    def test_get_leave_types(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/leave-types", headers=auth_headers)
        assert r.status_code == 200
        print(f"Leave types: {len(r.json().get('items', []))} types")


class TestPortalPayslip:
    def test_get_payslips_unlinked(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/payslips", headers=auth_headers)
        assert r.status_code == 409
        print(f"Payslip returns 409 for unlinked: {r.json().get('detail')}")


# ── WORKSPACE — NOTES ────────────────────────────────────────────────

class TestWorkspaceNotes:
    note_id = None

    def test_create_note(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/portal/notes", headers=auth_headers, json={
            "title": "TEST_Note_Playwright",
            "content": "<b>Bold content</b>",
            "color": "#fef9c3"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["title"] == "TEST_Note_Playwright"
        TestWorkspaceNotes.note_id = d["id"]
        print(f"Note created: id={d['id']}")

    def test_list_notes(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/notes", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()
        print(f"Notes listed: {r.json()['total']} notes")

    def test_update_note(self, auth_headers):
        assert TestWorkspaceNotes.note_id
        r = requests.put(f"{BASE_URL}/api/portal/notes/{TestWorkspaceNotes.note_id}",
                         headers=auth_headers, json={"title": "TEST_Note_Updated"})
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_Note_Updated"

    def test_delete_note(self, auth_headers):
        assert TestWorkspaceNotes.note_id
        r = requests.delete(f"{BASE_URL}/api/portal/notes/{TestWorkspaceNotes.note_id}",
                            headers=auth_headers)
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ── WORKSPACE — TODOS ────────────────────────────────────────────────

class TestWorkspaceTodos:
    todo_id = None

    def test_create_todo(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/portal/todos", headers=auth_headers, json={
            "title": "TEST_Todo_Item",
            "priority": "high",
            "due_date": "2026-12-31"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["title"] == "TEST_Todo_Item"
        assert d["priority"] == "high"
        TestWorkspaceTodos.todo_id = d["id"]

    def test_list_todos(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/todos", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_toggle_done(self, auth_headers):
        assert TestWorkspaceTodos.todo_id
        r = requests.put(f"{BASE_URL}/api/portal/todos/{TestWorkspaceTodos.todo_id}",
                         headers=auth_headers, json={"done": True})
        assert r.status_code == 200
        assert r.json()["done"] is True

    def test_delete_todo(self, auth_headers):
        assert TestWorkspaceTodos.todo_id
        r = requests.delete(f"{BASE_URL}/api/portal/todos/{TestWorkspaceTodos.todo_id}",
                            headers=auth_headers)
        assert r.status_code == 200


# ── WORKSPACE — REMINDERS ────────────────────────────────────────────

class TestWorkspaceReminders:
    rem_id = None

    def test_create_reminder(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/portal/reminders", headers=auth_headers, json={
            "title": "TEST_Reminder",
            "remind_at": "2026-12-31T09:00:00",
            "recurrence": "once",
            "whatsapp_enabled": False
        })
        assert r.status_code == 200
        d = r.json()
        assert d["title"] == "TEST_Reminder"
        TestWorkspaceReminders.rem_id = d["id"]

    def test_list_reminders(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/reminders", headers=auth_headers)
        assert r.status_code == 200

    def test_delete_reminder(self, auth_headers):
        assert TestWorkspaceReminders.rem_id
        r = requests.delete(f"{BASE_URL}/api/portal/reminders/{TestWorkspaceReminders.rem_id}",
                            headers=auth_headers)
        assert r.status_code == 200


# ── WORKSPACE — CALENDAR ─────────────────────────────────────────────

class TestWorkspaceCalendar:
    evt_id = None

    def test_create_event(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/portal/calendar", headers=auth_headers, json={
            "title": "TEST_Event_Feb",
            "date": "2026-02-15",
            "time": "10:00",
            "description": "Test event"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["title"] == "TEST_Event_Feb"
        TestWorkspaceCalendar.evt_id = d["id"]

    def test_list_calendar(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/calendar", headers=auth_headers,
                         params={"from": "2026-02-01", "to": "2026-02-28"})
        assert r.status_code == 200
        assert "items" in r.json()

    def test_combined_calendar(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/calendar/combined", headers=auth_headers,
                         params={"from": "2026-02-01", "to": "2026-02-28"})
        assert r.status_code == 200
        d = r.json()
        assert "events" in d
        print(f"Combined calendar: {d['total']} events")

    def test_delete_event(self, auth_headers):
        assert TestWorkspaceCalendar.evt_id
        r = requests.delete(f"{BASE_URL}/api/portal/calendar/{TestWorkspaceCalendar.evt_id}",
                            headers=auth_headers)
        assert r.status_code == 200


# ── WORKSPACE — QUICK LINKS ──────────────────────────────────────────

class TestWorkspaceQuickLinks:
    link_id = None

    def test_add_quick_link(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/portal/quick-links", headers=auth_headers, json={
            "module_id": "portal-dashboard",
            "label": "TEST_Dashboard Saya",
            "portal": "self"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["module_id"] == "portal-dashboard"
        TestWorkspaceQuickLinks.link_id = d["id"]

    def test_list_quick_links(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/quick-links", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_delete_quick_link(self, auth_headers):
        assert TestWorkspaceQuickLinks.link_id
        r = requests.delete(f"{BASE_URL}/api/portal/quick-links/{TestWorkspaceQuickLinks.link_id}",
                            headers=auth_headers)
        assert r.status_code == 200


# ── NOTIFICATIONS ────────────────────────────────────────────────────

class TestNotifications:
    def test_get_notifications(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/portal/notifications", headers=auth_headers)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d
        print(f"Notifications: {d['total']} items, {d['unread']} unread")
