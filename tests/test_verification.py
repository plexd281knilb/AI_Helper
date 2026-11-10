import os
import sys
import unittest
import json
import sqlite3
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import (
    app,
    __version__,
    __build__,
    clean_display_event_title,
    parse_flexible_iso_datetime,
    evaluate_fb_listing_against_watchlist,
    evaluate_fb_location,
    init_db
)

client = TestClient(app)

class TestVerificationSuite(unittest.TestCase):
    """
    Comprehensive regression and verification test suite for AI Helper v3.1 (Build 20261110.1).
    """

    def test_01_version_and_build(self):
        """Verify version and build number are correctly exposed across app and health APIs."""
        self.assertEqual(__version__, "3.1.0")
        self.assertEqual(__build__, "20261110.1")

        # Verify /health
        res_h = client.get("/health")
        self.assertEqual(res_h.status_code, 200)
        data_h = res_h.json()
        self.assertEqual(data_h["status"], "healthy")
        self.assertEqual(data_h["version"], "3.1.0")
        self.assertEqual(data_h["build"], "20261110.1")

        # Verify /api/version
        res_v = client.get("/api/version")
        self.assertEqual(res_v.status_code, 200)
        data_v = res_v.json()
        self.assertEqual(data_v["version"], "3.1.0")
        self.assertEqual(data_v["build"], "20261110.1")

        # Verify UI version tags in static/index.html
        with open(os.path.join(ROOT_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('>v3.1</span>', html)
        self.assertIn('<span class="brand-badge-mini">v3.1</span>', html)
        self.assertIn('<span class="brand-badge">v3.1</span>', html)

    def test_02_database_schema(self):
        """Verify database initialization and migrations execute without errors."""
        init_db()
        test_db = os.path.join(ROOT_DIR, "data", "app.db")
        self.assertTrue(os.path.exists(test_db))
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in c.fetchall()]
        expected_tables = [
            "users", "sessions", "email_accounts", "events",
            "processed_emails_v2", "grocery_stores", "grocery_lists",
            "grocery_list_items", "grocery_price_history", "meal_plans",
            "fb_watchlists", "fb_listings"
        ]
        for t in expected_tables:
            self.assertIn(t, tables, f"Table {t} should exist in database")
        conn.close()

    def test_03_title_cleaning_and_deduplication(self):
        """Verify event title suffix normalization correctly standardizes child tags."""
        self.assertEqual(
            clean_display_event_title("Veterans Day Assembly (Leo - 2nd Grade)"),
            "Veterans Day Assembly - Leo"
        )
        self.assertEqual(
            clean_display_event_title("Veterans Day Assembly - Leo (2nd Grade)"),
            "Veterans Day Assembly - Leo"
        )
        self.assertEqual(
            clean_display_event_title("PE with a Parent (Leo - 2nd Grade)"),
            "PE with a Parent - Leo"
        )
        self.assertEqual(
            clean_display_event_title("Varsity Football vs Guyer High"),
            "Varsity Football vs Guyer High"
        )

    def test_04_datetime_parsing(self):
        """Verify flexible datetime parsing handles multiple US localized and standard formats."""
        dt1 = parse_flexible_iso_datetime("2026-11-11T09:00:00")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.year, 2026)
        self.assertEqual(dt1.month, 11)
        self.assertEqual(dt1.day, 11)

        dt2 = parse_flexible_iso_datetime("11/11/2026, 9:00:00 AM")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.hour, 9)

        dt3 = parse_flexible_iso_datetime("2026-11-19")
        self.assertIsNotNone(dt3)
        self.assertEqual(dt3.day, 19)

    def test_05_fb_sniper_blocks_keller_54cm_trek(self):
        """Verify the Keller, TX 54cm Medium Trek (#1110750468384718) is strictly blocked."""
        watchlist = {
            "name": "Wife's Bike Watchlist",
            "query": "road bike",
            "category": "bicycles",
            "postal_code": "76262",
            "location_name": "Argyle / DFW, TX",
            "max_radius_miles": 100,
            "allowed_states": ["TX", "Texas"],
            "min_price": 75,
            "max_price": 1600,
            "must_contain_any": ["liv", "giant", "trek", "specialized"],
            "required_attributes": ["xxs", "2xs", "extra extra small", "xs", "extra small", "x-small", "x small", "39.5", "40cm", "42cm", "43cm", "44cm", "45cm", "46cm", "47cm", "48cm"],
            "exclude_keywords": "large, mountain, size l, frame l, medium, size m, frame m, xl, extra large, mens, men's, huffy, schwinn, bmx, kids 12, kids 16, 20 inch, arkansas, little rock, fayetteville, bentonville, oklahoma, tulsa, ships to you, iso, wanted, broken. 48cm, 49cm, 50cm, 51cm, 52cm, 53cm, 54cm, 55cm, 56cm, 57cm, 58cm, 59cm, 60cm, 61cm, 62cm"
        }

        # Case A: Real seller description containing 54CM (Medium Sized Frame)
        item_full = {
            "fb_item_id": "fb_1110750468384718",
            "title": "Trek Tri Road Bike",
            "price_str": "$275",
            "price_num": 275.0,
            "location": "Keller, TX",
            "description": "Trek 1000 Alpha road bike with triathlon bars attached. 54CM (Medium Sized Frame)",
            "gallery_photos": ["https://example.com/bike.jpg"]
        }
        res_full = evaluate_fb_listing_against_watchlist(item_full, watchlist)
        self.assertEqual(res_full["status"], "blocked")
        reasons_full = " ".join(res_full["block_reasons"])
        self.assertTrue("54cm" in reasons_full.lower() or "50cm" in reasons_full.lower() or "medium" in reasons_full.lower())

        # Case B: Placeholder description (before scrape)
        item_placeholder = {
            "fb_item_id": "fb_1110750468384718",
            "title": "Trek Tri Road Bike",
            "price_str": "$275",
            "price_num": 275.0,
            "location": "Keller, TX",
            "description": "Live Facebook Marketplace listing #1110750468384718 in Keller, TX (Seller: Vijay Hiremath)",
            "gallery_photos": ["https://example.com/bike.jpg"]
        }
        res_ph = evaluate_fb_listing_against_watchlist(item_placeholder, watchlist)
        # Should be blocked because unisex adult road bike without verified XXS/XS size
        self.assertEqual(res_ph["status"], "blocked")
        self.assertIn("Missing Required Size/Spec", " ".join(res_ph["block_reasons"]))

    def test_06_fb_sniper_geofence_and_out_of_state(self):
        """Verify geofence enforcement up to 100 miles and out-of-state blocking."""
        # Local Keller, TX (~13 miles from Argyle) should pass within 100 miles
        loc_local = evaluate_fb_location("Keller, TX", max_radius_miles=100)
        self.assertTrue(loc_local["passed"])
        self.assertLessEqual(loc_local["distance_miles"], 100)

        # Distant Texas city outside 45 miles but inside 100 miles (e.g. Cleburne ~62 miles)
        loc_cleburne = evaluate_fb_location("Cleburne, TX", max_radius_miles=100)
        self.assertTrue(loc_cleburne["passed"])

        # Out-of-state (Oklahoma, Arkansas) must always be blocked
        loc_ok = evaluate_fb_location("Tulsa, OK", max_radius_miles=100)
        self.assertFalse(loc_ok["passed"])

        loc_ar = evaluate_fb_location("Fayetteville, AR", max_radius_miles=100)
        self.assertFalse(loc_ar["passed"])

    def test_07_public_endpoints_accessible(self):
        """Verify public landing page and legal compliance routes are accessible without auth."""
        for path in ("/", "/privacy", "/terms", "/favicon.ico"):
            res = client.get(path)
            self.assertEqual(res.status_code, 200, f"Route {path} should be publicly accessible")

    def test_08_protected_api_endpoints_gated(self):
        """Verify sensitive APIs return 401 when no session cookie is provided."""
        for path in ("/api/events", "/api/history", "/api/groceries/stores", "/api/groceries/feed", "/api/meals/current", "/api/facebook/overview"):
            res = client.get(path)
            self.assertIn(res.status_code, (401, 403), f"Route {path} should be protected by verify_auth")

if __name__ == "__main__":
    unittest.main()
