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
    resolve_watchlist_geo,
    init_db
)

client = TestClient(app)

class TestVerificationSuite(unittest.TestCase):
    """
    Comprehensive regression and verification test suite for AI Helper v3.1 (Build 20261110.1).
    """

    def test_01_version_and_build(self):
        """Verify version and build number are correctly exposed across app and health APIs."""
        self.assertEqual(__version__, "3.1.3")
        self.assertEqual(__build__, "20261110.4")

        # Verify /health
        res_h = client.get("/health")
        self.assertEqual(res_h.status_code, 200)
        data_h = res_h.json()
        self.assertEqual(data_h["status"], "healthy")
        self.assertEqual(data_h["version"], "3.1.3")
        self.assertEqual(data_h["build"], "20261110.4")

        # Verify /api/version
        res_v = client.get("/api/version")
        self.assertEqual(res_v.status_code, 200)
        data_v = res_v.json()
        self.assertEqual(data_v["version"], "3.1.3")
        self.assertEqual(data_v["build"], "20261110.4")

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

    def test_09_houston_regional_geofence_and_search_resolution(self):
        """Verify multi-region geofencing accurately resolves Houston watchlists and filters listings."""
        houston_wl = {
            "name": "🚲 Wife's Bike (Houston Local Only)",
            "query": "bike",
            "postal_code": "77002",
            "location_name": "Houston, TX",
            "max_radius_miles": 100,
            "min_price": 75,
            "max_price": 1300,
            "must_contain_any": ["liv", "giant liv", "avail", "langma", "devote", "alight", "tempt", "envie", "thrive", "Trek", "beliv", "domane", "giant"],
            "required_attributes": ["xxs", "2xs", "extra extra small", "xs", "extra small", "43cm", "44cm", "45cm", "46cm", "47cm", "4'10", "4'11", "5'0", "5'1", "5'2", "extra-small"],
            "exclude_keywords": [
                "large", "mountain", "size l", "frame l", "medium", "size m", "frame m", "xl", "extra large",
                "mens", "men's", "huffy", "schwinn", "bmx", "kids 12", "kids 16", "20 inch", "arkansas",
                "little rock", "fayetteville", "bentonville", "oklahoma", "tulsa", "ships to you", "iso", "wanted", "broken",
                "48cm", "49cm", "50cm", "51cm", "52cm", "53cm", "54cm", "55cm", "56cm", "57cm", "58cm", "59cm", "60cm", "61cm", "62cm"
            ]
        }

        # 1. Geo slug resolution
        geo_houston = resolve_watchlist_geo(houston_wl)
        self.assertEqual(geo_houston["city_slug"], "houston")
        self.assertEqual(geo_houston["metro_name"], "Houston, TX")
        self.assertAlmostEqual(geo_houston["lat"], 29.7604, places=3)

        # Austin & DFW resolution
        self.assertEqual(resolve_watchlist_geo({"postal_code": "78701"})["city_slug"], "austin")
        self.assertEqual(resolve_watchlist_geo({"postal_code": "76226"})["city_slug"], "dallas")

        # 2. Location evaluations from Houston center
        loc_h = evaluate_fb_location("Houston, TX", max_radius_miles=100, watchlist=houston_wl)
        self.assertTrue(loc_h["passed"])
        self.assertAlmostEqual(loc_h["distance_miles"], 0.0, delta=1.0)

        loc_katy = evaluate_fb_location("Katy, TX", max_radius_miles=100, watchlist=houston_wl)
        self.assertTrue(loc_katy["passed"])
        self.assertAlmostEqual(loc_katy["distance_miles"], 27.3, delta=2.0)

        loc_woodlands = evaluate_fb_location("The Woodlands, TX", max_radius_miles=100, watchlist=houston_wl)
        self.assertTrue(loc_woodlands["passed"])
        self.assertAlmostEqual(loc_woodlands["distance_miles"], 28.5, delta=2.0)

        loc_sugar = evaluate_fb_location("Sugar Land, TX", max_radius_miles=100, watchlist=houston_wl)
        self.assertTrue(loc_sugar["passed"])
        self.assertAlmostEqual(loc_sugar["distance_miles"], 18.6, delta=2.0)

        # Dallas is ~225 miles from Houston -> strictly blocked by 100 mi radius
        loc_dallas = evaluate_fb_location("Dallas, TX", max_radius_miles=100, watchlist=houston_wl)
        self.assertFalse(loc_dallas["passed"])
        self.assertIn("Outside 100 mi Radius", loc_dallas["reason"])
        self.assertIn("Houston, TX", loc_dallas["reason"])

        # Keller, TX is ~237 miles from Houston -> strictly blocked
        loc_keller = evaluate_fb_location("Keller, TX", max_radius_miles=100, watchlist=houston_wl)
        self.assertFalse(loc_keller["passed"])
        self.assertIn("Outside 100 mi Radius", loc_keller["reason"])

        # 3. Listing evaluations against Houston Watchlist
        # Valid Houston XS bike:
        item_houston_xs = {
            "title": "2024 Liv Thrive GX XS – Like New",
            "price_num": 1000.0,
            "location": "Sugar Land, TX",
            "description": "2024 Liv Thrive GX XS in Sugar Land, TX. Shimano groupset, disc brakes, size XS.",
            "gallery_photos": []
        }
        res_xs = evaluate_fb_listing_against_watchlist(item_houston_xs, houston_wl)
        self.assertEqual(res_xs["status"], "matched")

        # Wrong frame size in Houston (54cm Medium Trek in Woodlands):
        item_woodlands_med = {
            "title": "Trek Domane AL 2 Road Bike - 54cm Frame",
            "price_num": 450.0,
            "location": "The Woodlands, TX",
            "description": "Trek Domane AL 2 road bike in The Woodlands. 54cm Medium frame size.",
            "gallery_photos": []
        }
        res_med = evaluate_fb_listing_against_watchlist(item_woodlands_med, houston_wl)
        self.assertEqual(res_med["status"], "blocked")
        self.assertTrue(any("54cm" in r or "medium" in r.lower() for r in res_med["block_reasons"]))

        # Out-of-radius listing (DFW bike evaluated against Houston watchlist):
        item_dfw = {
            "title": "Liv Avail AR 4 Women's Road Bike (Size XS)",
            "price_num": 625.0,
            "location": "Keller, TX",
            "description": "Liv Avail AR 4 Women's Road Bike (Size XS) in Keller, TX",
            "gallery_photos": []
        }
        res_dfw = evaluate_fb_listing_against_watchlist(item_dfw, houston_wl)
        self.assertEqual(res_dfw["status"], "blocked")
        self.assertIn("Outside 100 mi Radius", " ".join(res_dfw["block_reasons"]))

    def test_10_anti_false_positive_and_mtb_enforcement(self):
        """Verify Missouri City, TX passes local geofence, women's bikes are not blocked by 'men's', and MTBs are blocked."""
        houston_wl = {
            "name": "🚲 Wife's Bike (Houston Local Only)",
            "query": "bike",
            "postal_code": "77002",
            "location_name": "Houston, TX",
            "max_radius_miles": 100,
            "min_price": 75,
            "max_price": 1300,
            "must_contain_any": ["liv", "giant liv", "avail", "langma", "devote", "alight", "tempt", "envie", "thrive", "Trek", "beliv", "domane", "giant"],
            "required_attributes": ["xxs", "2xs", "extra extra small", "xs", "extra small", "43cm", "44cm", "45cm", "46cm", "47cm", "4'10", "4'11", "5'0", "5'1", "5'2", "extra-small"],
            "exclude_keywords": [
                "large", "mountain", "size l", "frame l", "medium", "size m", "frame m", "xl", "extra large",
                "mens", "men's", "huffy", "schwinn", "bmx", "kids 12", "kids 16", "20 inch", "arkansas",
                "little rock", "fayetteville", "bentonville", "oklahoma", "tulsa", "ships to you", "iso", "wanted", "broken",
                "48cm", "49cm", "50cm", "51cm", "52cm", "53cm", "54cm", "55cm", "56cm", "57cm", "58cm", "59cm", "60cm", "61cm", "62cm"
            ],
            "visual_targets": "Inspect photos to identify exact model from frame decals, verify XXS/XS compact sloping top-tube geometry & seat-tube size stickers, check Carbon vs ALUXX welded aluminum, Disc vs Rim brakes, drivetrain tier, and block 20\"/24\" youth kids bikes (e.g. Liv Enchant). make sure it is a road bike and not a mountain bike."
        }

        # 1. Missouri City, TX is NOT flagged as Missouri (Out of State)
        loc_mc = evaluate_fb_location("Missouri City, TX", max_radius_miles=100, watchlist=houston_wl)
        self.assertTrue(loc_mc["passed"])
        self.assertNotIn("Missouri (Out of State)", loc_mc["reason"])
        self.assertAlmostEqual(loc_mc["distance_miles"], 18.0, delta=4.0)

        # 2. Women's bike does NOT trigger Excluded Keyword: 'men's'
        item_womens = {
            "title": "Giant OCR3 women's road bike",
            "price_num": 550.0,
            "location": "Houston, TX",
            "description": "Selling my Giant OCR3 women's road bike - lightweight, comfortable. Size XS.",
            "gallery_photos": []
        }
        res_w = evaluate_fb_listing_against_watchlist(item_womens, houston_wl)
        reasons_text = " ".join(res_w["block_reasons"])
        self.assertNotIn("Excluded Keyword/Size/Brand: 'men's'", reasons_text)
        self.assertNotIn("Excluded Keyword/Size/Brand: 'mens'", reasons_text)

        # 3. Mountain bike is strictly blocked
        item_marlin = {
            "title": "Trek Marlin 5 Gen 3",
            "price_num": 550.0,
            "location": "Houston, TX",
            "description": "7 gear Mountain Bike, XS frame.",
            "gallery_photos": []
        }
        res_m = evaluate_fb_listing_against_watchlist(item_marlin, houston_wl)
        self.assertEqual(res_m["status"], "blocked")
        self.assertTrue(any("Mountain" in r or "mountain" in r.lower() for r in res_m["block_reasons"]))

    def test_11_email_fetch_unique_constraint_and_concurrency_lock(self):
        """Verify processed_emails_v2 handles duplicate UIDs idempotently and user scan lock blocks concurrent scans."""
        from app import get_db_conn, process_user_emails, USER_SCANNING_IN_PROGRESS, USER_SCAN_LOCK

        conn = get_db_conn()
        c = conn.cursor()
        test_uid = "msg_test_unique_constraint_999"
        test_user = "user_test_unique_constraint"
        test_acc = "dominicmjuliano@gmail.com"

        # Clean up any leftover test data
        c.execute("DELETE FROM processed_emails_v2 WHERE id=? AND user_id=? AND account=?", (test_uid, test_user, test_acc))
        conn.commit()

        # 1. First insertion
        c.execute("""
            INSERT OR REPLACE INTO processed_emails_v2 
            (id, user_id, account, subject, date, body, sender, reason, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_uid, test_user, test_acc, "Test Subject 1", "2026-11-10T14:00:00", "Body 1", "sender@test.com", "Reason 1", "added"))
        conn.commit()

        # 2. Second insertion of the EXACT SAME primary key (id, user_id, account)
        # Previously raised: sqlite3.IntegrityError: UNIQUE constraint failed
        # With INSERT OR REPLACE, it MUST succeed idempotently!
        try:
            c.execute("""
                INSERT OR REPLACE INTO processed_emails_v2 
                (id, user_id, account, subject, date, body, sender, reason, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (test_uid, test_user, test_acc, "Test Subject 2 Updated", "2026-11-10T14:05:00", "Body 2", "sender@test.com", "Reason 2", "added"))
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False

        self.assertTrue(success, "INSERT OR REPLACE INTO processed_emails_v2 should NEVER fail on unique constraint!")

        # Verify the record was cleanly updated
        c.execute("SELECT subject FROM processed_emails_v2 WHERE id=? AND user_id=? AND account=?", (test_uid, test_user, test_acc))
        row = c.fetchone()
        self.assertEqual(row["subject"], "Test Subject 2 Updated")

        # Clean up
        c.execute("DELETE FROM processed_emails_v2 WHERE id=? AND user_id=? AND account=?", (test_uid, test_user, test_acc))
        conn.commit()
        conn.close()

        # 3. Verify user scan concurrency guard
        with USER_SCAN_LOCK:
            USER_SCANNING_IN_PROGRESS.add(test_user)

        try:
            res_concurrent = process_user_emails(test_user)
            self.assertEqual(res_concurrent.get("status"), "in_progress")
            self.assertEqual(res_concurrent.get("new_events"), 0)
        finally:
            with USER_SCAN_LOCK:
                USER_SCANNING_IN_PROGRESS.discard(test_user)

if __name__ == "__main__":
    unittest.main()
