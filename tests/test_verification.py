import os
import sys
import tempfile
import unittest
import json
import sqlite3
import atexit
import shutil

_TEMP_TEST_DIR = tempfile.mkdtemp(prefix="ai_helper_test_")
os.environ["AI_HELPER_DATA_DIR"] = _TEMP_TEST_DIR
os.environ["AI_HELPER_DB_FILE"] = os.path.join(_TEMP_TEST_DIR, "test_app.db")
atexit.register(lambda: shutil.rmtree(_TEMP_TEST_DIR, ignore_errors=True))

from fastapi.testclient import TestClient

# Ensure root directory is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import (
    app,
    DB_FILE,
    __version__,
    __build__,
    canonicalize_identifier,
    clean_display_event_title,
    build_parsing_prompt_instructions,
    post_process_extracted_event,
    guess_deal_category,
    detect_beef_grade,
    format_deal_price_and_notes,
    sanitize_deal_price_and_notes,
    parse_numeric_price,
    is_safe_public_url,
    is_safe_public_hostname,
    is_valid_public_origin,
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
        """Verify database initialization and migrations execute without errors in isolated test DB."""
        init_db()
        test_db = DB_FILE
        self.assertTrue(test_db.startswith(_TEMP_TEST_DIR), "Tests must run against isolated temp SQLite DB")
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

    def test_12_security_21point_confusables_sql_52char_and_ui(self):
        """Verify Unicode confusables (SPOTIFY), 52-char & SQL-syntax usernames, SSRF, RBAC, ReDoS & UI checks."""
        # 1. Unicode confusable canonicalization
        self.assertEqual(canonicalize_identifier("\u0405\u0420\u041E\u0422\u0406\u0492\u0423"), "spotify")
        self.assertEqual(canonicalize_identifier("\uFF33\uFF30\uFF2F\uFF34\uFF29\uFF26\uFF39"), "spotify")
        self.assertEqual(canonicalize_identifier("\u212A\u017F"), "ks")

        # 2. SSRF & public origin & regex metacharacter escaping checks
        self.assertFalse(is_safe_public_url("http://169.254.169.254/latest/meta-data/"))
        self.assertFalse(is_safe_public_url("http://127.0.0.1:8080/"))
        self.assertFalse(is_safe_public_url("file:///etc/passwd"))
        self.assertFalse(is_valid_public_origin("javascript:alert(1)"))
        self.assertTrue(is_valid_public_origin("https://helper.example.com"))

        # Member names with regex metacharacters must not crash or trigger backtracking
        self.assertEqual(
            clean_display_event_title("Practice (Leo[+?*( - 2nd Grade)", child_names=["Leo[+?*("], self_name="Mom(a+)+"),
            "Practice - Leo[+?*("
        )

        # 3. Initial admin setup, login, confusable/SQL/52-char user creation & session revocation
        admin_res = client.post("/api/auth/register", json={"username": "spotify", "password": "AdminPassword!1"})
        self.assertEqual(admin_res.json().get("status"), "success")

        login_admin = client.post("/api/auth/login", json={"username": "spotify", "password": "AdminPassword!1"})
        self.assertEqual(login_admin.json().get("status"), "success")

        # Confusable collision blocked even by admin
        dup_confusable = client.post("/api/users", json={"username": "\u0405\u0420\u041E\u0422\u0406\u0492\u0423", "password": "Pass!1234", "role": "user"})
        self.assertIn("already exists", dup_confusable.json().get("error", ""))

        # 52-char and SQL-syntax usernames succeed cleanly and parameterize safely
        u52 = "A" * 52
        self.assertEqual(client.post("/api/users", json={"username": u52, "password": "User52Pass!1", "role": "user"}).json().get("status"), "success")
        sql_user = "Robert'); DROP TABLE users;--"
        self.assertEqual(client.post("/api/users", json={"username": sql_user, "password": "SqlUserPass!1", "role": "user"}).json().get("status"), "success")

        # Log in as non-admin SQL-syntax user using isolated TestClient
        c2 = TestClient(app)
        l2 = c2.post("/api/auth/login", json={"username": sql_user, "password": "SqlUserPass!1"})
        self.assertEqual(l2.json().get("status"), "success")
        self.assertIn("Cache-Control", l2.headers)
        self.assertIn("no-store", l2.headers["Cache-Control"])

        # Non-admin cannot upload client_secret.json (403)
        sec_up = c2.post("/api/upload_client_secret", files={"file": ("client_secret.json", b"{}", "application/json")})
        self.assertEqual(sec_up.status_code, 403)

        # Malicious Google verification path returns 404 (not raw unescaped HTML)
        g_bad = c2.get("/google<script>alert(1)<.html")
        self.assertEqual(g_bad.status_code, 404)

        # Grocery list IDOR check returns 404 for unknown / non-owned list
        idor_res = c2.get("/api/groceries/lists/nonexistent-list-id/items")
        self.assertEqual(idor_res.status_code, 404)

        # Password reset revokes active session of target user
        users_list = client.get("/api/users").json()
        sql_uid = next(u["id"] for u in users_list if u["username"] == sql_user)
        upd = client.put(f"/api/users/{sql_uid}", json={"password": "NewRotatedPassword!2"})
        self.assertEqual(upd.json().get("status"), "success")
        self.assertEqual(c2.get("/api/events").status_code, 401)

        # 4. UI Light/Dark theme, viewport-fit=cover, mobile 16px rules & no purple gradient tokens
        with open(os.path.join(ROOT_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
            html_doc = f.read()
        self.assertIn("viewport-fit=cover", html_doc)
        self.assertIn('data-theme="light"', html_doc)
        self.assertIn("ai_helper_theme", html_doc)
        self.assertIn("-webkit-backdrop-filter", html_doc)
        self.assertNotIn("user-scalable=no", html_doc)

    def test_13_school_wide_kids_attribution(self):
        """Verify school-wide Liberty Christian events (e.g., Jeans Day) are attributed to Kids, never Dominic."""
        # 1. Prompt instructions explicitly enforce "- Kids" for school-wide events
        prompt_text = build_parsing_prompt_instructions({})
        self.assertIn("- Kids", prompt_text)
        self.assertIn("NEVER attribute school-wide, student, or general school community events", prompt_text)

        # 2. Title cleaner normalizes (Kids) suffix cleanly
        self.assertEqual(clean_display_event_title("Jeans Day (Kids)"), "Jeans Day - Kids")

        # 3. LLM output erroneously labeled "- Dominic" for Jeans Day at Liberty Christian is corrected to "- Kids"
        ev_jeans_dominic = {
            "title": "Jeans Day - Dominic",
            "date": "2026-11-20T09:00:00",
            "location": "Liberty Christian School, Argyle, Texas",
            "description": "General school $3 Jeans Day for the community, tracked for Dominic."
        }
        res_jeans = post_process_extracted_event(
            ev_jeans_dominic,
            {},
            subject="Liberty Christian Weekly Update",
            body="Friday, November 20 is a general school $3 Jeans Day for the community. 2nd grade notes below."
        )
        self.assertIsNotNone(res_jeans)
        self.assertEqual(res_jeans["title"], "Jeans Day - Kids")
        self.assertNotIn("Dominic", res_jeans["title"])
        self.assertNotIn("tracked for Dominic", res_jeans["description"])
        self.assertIn("tracked for the kids", res_jeans["description"])

        # 4. School-wide Jeans Day without suffix isn't hijacked by passing 2nd grade mention in newsletter body
        ev_jeans_raw = {
            "title": "Jeans Day",
            "date": "2026-11-20T09:00:00",
            "location": "Liberty",
            "description": "School-wide $3 Jeans Day"
        }
        res_raw = post_process_extracted_event(
            ev_jeans_raw,
            {},
            subject="All-School Newsletter",
            body="Friday is $3 Jeans Day. Also 2nd grade has a reading log due next week."
        )
        self.assertEqual(res_raw["title"], "Jeans Day - Kids")
        self.assertEqual(res_raw["location"], "Liberty Christian School, Argyle, Texas")

        # 5. Single-child event still goes to that child
        ev_leo = {
            "title": "Spelling Bee",
            "date": "2026-11-20T09:00:00",
            "location": "Liberty Christian School",
            "description": "2nd grade spelling bee in the lower school auditorium."
        }
        res_leo = post_process_extracted_event(ev_leo, {}, subject="2nd Grade Update", body="2nd grade spelling bee")
        self.assertEqual(res_leo["title"], "Spelling Bee - Leo")

        # 6. Personal adult event & Class of 2006 alumni event still go to Dominic
        ev_dentist = {
            "title": "Dentist Appointment",
            "date": "2026-11-21T10:00:00",
            "location": "Argyle Dental",
            "description": "Routine cleaning"
        }
        res_dentist = post_process_extracted_event(ev_dentist, {}, subject="Appointment Reminder", body="Your dental cleaning is tomorrow.")
        self.assertEqual(res_dentist["title"], "Dentist Appointment - Dominic")

        ev_alumni = {
            "title": "Class of 2006 Reunion - Dominic",
            "date": "2026-11-22T18:00:00",
            "location": "Liberty Christian School, Argyle, Texas",
            "description": "20-year alumni dinner"
        }
        res_alumni = post_process_extracted_event(ev_alumni, {}, subject="LCS Class of 2006 Alumni Reunion", body="Join fellow Class of 2006 alumni.")
        self.assertEqual(res_alumni["title"], "Class of 2006 Reunion - Dominic")

        # 7. UI Kids filter pill & Quick Add option present
        with open(os.path.join(ROOT_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
            html_doc = f.read()
        self.assertIn('id="fam-pill-Kids"', html_doc)
        self.assertIn('value="Kids"', html_doc)

    def test_14_filter_unwanted_public_legal_and_preorder_events(self):
        """Verify class action hearings, unconfirmed community/speaker breakfasts, and meal preorder flyers are blocked."""
        # 1. CVS Class Action Final Approval Hearing
        ev_cvs = {
            "title": "CVS Class Action Final Approval Hearing - Dominic",
            "date": "2026-12-01T08:30:00",
            "location": "Zoom",
            "description": "The Court will hold the Final Approval Hearing to consider the proposed settlement."
        }
        self.assertIsNone(post_process_extracted_event(
            ev_cvs, {}, subject="Notice of Proposed Class Action Settlement",
            body="The Court will hold the Final Approval Hearing to consider the proposed settlement."
        ))

        # 2. Unconfirmed community/church speaker breakfast flyer
        ev_breakfast = {
            "title": "Dr. McCullough Speaking at Marty B's Men's Bible Breakfast - Dominic",
            "date": "2026-11-24T06:30:00",
            "location": "Marty B's",
            "description": "Men's Bible Breakfast with breakfast, coffee, worship, and an encouraging message from Dr. McCullough, attended by Dominic."
        }
        self.assertIsNone(post_process_extracted_event(
            ev_breakfast, {}, subject="Tuesday Men's Bible Breakfast at Marty B's",
            body="Join us Tuesday morning for breakfast, coffee, worship, and an encouraging message from Dr. McCullough."
        ))

        # 3. Optional food/tailgate meal preorder solicitation
        ev_tailgate = {
            "title": "Tailgate Meal Preorder Deadline - Dominic",
            "date": "2026-11-25T16:00:00",
            "location": "",
            "description": "Deadline to preorder meals from The Hamburger Man for the community tailgate and dinner event for Dominic and family."
        }
        self.assertIsNone(post_process_extracted_event(
            ev_tailgate, {}, subject="Community Tailgate Meal Preorder",
            body="Don't forget to preorder meals from The Hamburger Man by Wednesday at 4 PM for the community tailgate."
        ))

        # 4. Confirmed paid order / RSVP should still pass if explicit confirmation exists
        ev_confirmed_rsvp = {
            "title": "Men's Bible Breakfast - Dominic",
            "date": "2026-11-24T06:30:00",
            "location": "Marty B's",
            "description": "RSVP confirmed for Dominic."
        }
        self.assertIsNotNone(post_process_extracted_event(
            ev_confirmed_rsvp, {}, subject="RSVP Confirmed: Men's Bible Breakfast",
            body="Thank you for registering! Your RSVP confirmed your seat at Marty B's."
        ))

        # 5. Generated web & favicon images exist and are served properly
        for img_name in ("ai-helper-logo.jpg", "ai-helper-hero.jpg"):
            img_path = os.path.join(ROOT_DIR, "static", "images", img_name)
            self.assertTrue(os.path.exists(img_path), f"Missing generated image: {img_path}")
            res_img = client.get(f"/static/images/{img_name}")
            self.assertEqual(res_img.status_code, 200)
        res_fav = client.get("/favicon.ico")
        self.assertEqual(res_fav.status_code, 200)
        self.assertEqual(res_fav.headers.get("content-type"), "image/jpeg")

    def test_15_grocery_categorization_and_lb_pricing(self):
        """Verify non-meat items never pollute Meat & Seafood, Prime Rib isn't tagged USDA Prime, and /lb units are preserved."""
        # 1. Non-meat items that previously polluted Meat & Seafood
        self.assertEqual(
            guess_deal_category("Eplumivor 300 Pcs Square Air Fryer Liners Disposable, 7.5 inch Natural Wood Pulp Parchment Baking Paper for Fried Chicken Fries Wings Veggies"),
            "Household & Personal"
        )
        self.assertEqual(
            guess_deal_category("Stove Top Stuffing Mix, 1 Box, for Dinner Sides and Thanksgiving Dinner, Turkey, 6 oz"),
            "Pantry & Dry Goods"
        )
        self.assertEqual(
            guess_deal_category("Taylor Farms or Fresh Express Chopped Salad Kits or Original Kits"),
            "Produce"
        )
        # 1b. Electronics & Tech never pollute Produce ("Apple" in chip/device names) and "table" doesn't match "vegetable"
        self.assertEqual(
            guess_deal_category("MacBook Pro Laptop (16-inch) - Apple M5 Max Chip, Built for Apple Intelligence, 18-core CPU, 40-core GPU, 48GB Memory, 2TB SSD Storage."),
            "Electronics & Tech"
        )
        self.assertEqual(guess_deal_category("Apple iPad Air 11-inch"), "Electronics & Tech")
        self.assertEqual(guess_deal_category("Samsung 65-inch OLED 4K TV"), "Electronics & Tech")
        self.assertEqual(guess_deal_category("Mixed Vegetables"), "Produce")
        self.assertEqual(guess_deal_category("Honeycrisp Apples 3 lb"), "Produce")
        self.assertEqual(guess_deal_category("Motts Apple Juice"), "Beverages")
        self.assertEqual(guess_deal_category("Bakery Fresh Apple Pie"), "Bakery & Deli")
        self.assertEqual(guess_deal_category("Applewood Smoked Bacon"), "Meat & Seafood")

        # 2. Real Meat & Seafood items still match Meat & Seafood
        self.assertEqual(guess_deal_category("USDA Prime Beef Boneless Top Sirloin Steaks"), "Meat & Seafood")
        self.assertEqual(guess_deal_category("8 Pc. Fried, Spicy, Roasted or Mango Habanero Mixed Chicken"), "Meat & Seafood")
        self.assertEqual(guess_deal_category("Catfish Nuggets"), "Meat & Seafood")
        self.assertEqual(guess_deal_category("Bacon-Wrapped Stuffed Jalapeños"), "Meat & Seafood")

        # 3. Prime Rib Dinner shouldn't falsely trigger USDA Prime grade
        self.assertEqual(detect_beef_grade("Prime Rib Dinner", "Meat & Seafood"), "none")
        self.assertEqual(detect_beef_grade("USDA Prime Beef Boneless Top Sirloin Steaks", "Meat & Seafood"), "prime")
        self.assertEqual(detect_beef_grade("H-E-B Prime 1 Beef Chuck Roast", "Meat & Seafood"), "prime")

        # 4. Per-lb pricing context preserves /lb unit instead of defaulting to /ea
        p1, _ = format_deal_price_and_notes(7.99, "SAVE up to $3 per lb.", "", "HEB", "H-E-B Boneless Wagyu Beef Shoulder Roast")
        self.assertEqual(p1, "$7.99/lb")
        self.assertEqual(parse_numeric_price(p1)["unit"], "lb")

        p2, _ = sanitize_deal_price_and_notes("$0.97", "SAVE up to $1.21 per lb.")
        self.assertEqual(p2, "$0.97/lb")
        self.assertEqual(parse_numeric_price(p2)["unit"], "lb")

        # 5. Cached bulk butcher meat cuts without notes (e.g. Albertsons Sirloin / Kroger Turkey) infer /lb, while packaged/dinner stay /ea
        p3, _ = sanitize_deal_price_and_notes("$9.99", "", item_name="USDA Prime Beef Boneless Top Sirloin Steaks", category="Meat & Seafood")
        self.assertEqual(p3, "$9.99/lb")
        self.assertEqual(parse_numeric_price(p3)["unit"], "lb")

        p4, _ = sanitize_deal_price_and_notes("$0.88", "", item_name="Butterball Whole Turkey", category="Meat & Seafood")
        self.assertEqual(p4, "$0.88/lb")

        p5, _ = sanitize_deal_price_and_notes("$99.99", "", item_name="Prime Rib Dinner", category="Meat & Seafood")
        self.assertEqual(p5, "$99.99")
        self.assertEqual(parse_numeric_price(p5)["unit"], "ea")

        p6, _ = format_deal_price_and_notes(3.99, "", "", "Oscar Mayer", "Oscar Mayer Bacon 12-16 oz.", post_price="ea when you buy 4")
        self.assertEqual(p6, "$3.99/ea")
        self.assertEqual(parse_numeric_price(p6)["unit"], "ea")

        # 6. Deal titles must never be line-clamped/truncated with ellipsis in UI
        with open(os.path.join(ROOT_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
            html_doc = f.read()
        self.assertNotIn("-webkit-line-clamp", html_doc)

    def test_16_deep_audit_ssrf_bounds_and_ui_unslop(self):
        """Verify SSRF mail/webhook guards, settings clamping, and 20-point UI design-system standards."""
        # 1. Mail/SMTP hostname SSRF blocking
        for bad_host in ("127.0.0.1", "localhost", "169.254.169.254", "192.168.1.50", "10.0.0.5", "db.internal", "nas.local", "http://imap.gmail.com"):
            self.assertFalse(is_safe_public_hostname(bad_host), f"Host should be blocked: {bad_host}")
        self.assertTrue(is_safe_public_hostname("8.8.8.8", default_port=993))

        # 2. Authenticate as admin (reusing spotify user from test_12 if already created)
        c = TestClient(app)
        login_res = c.post("/api/auth/login", json={"username": "spotify", "password": "AdminPassword!1"})
        if login_res.json().get("status") != "success":
            c.post("/api/auth/register", json={"username": "spotify", "password": "AdminPassword!1"})
            c.post("/api/auth/login", json={"username": "spotify", "password": "AdminPassword!1"})

        # Account test & save block internal hosts
        r_test = c.post("/api/accounts/test", json={"email_user": "a@b.com", "email_pass": "pw", "email_host": "127.0.0.1:993"})
        self.assertEqual(r_test.status_code, 400)
        r_save = c.post("/api/accounts", json={"email_user": "a@b.com", "email_pass": "pw", "email_host": "169.254.169.254"})
        self.assertEqual(r_save.status_code, 400)

        # Notification settings block non-Discord webhooks and private SMTP hosts
        r_wh = c.post("/api/notifications/settings", json={"discord_webhook_url": "http://127.0.0.1:8080/hook"})
        self.assertEqual(r_wh.status_code, 400)
        r_smtp = c.post("/api/notifications/settings", json={"smtp_host": "10.0.0.1"})
        self.assertEqual(r_smtp.status_code, 400)

        # Settings bounds clamping & provider validation
        r_bad_prov = c.post("/api/settings/ai", json={"ai_provider": "evil_provider"})
        self.assertEqual(r_bad_prov.status_code, 400)
        r_clamp = c.post("/api/settings/ai", json={"ai_provider": "gemini", "fetch_interval_minutes": 1, "lookback_days": 999, "email_fetch_limit": 9999})
        self.assertEqual(r_clamp.status_code, 200)
        s_read = c.get("/api/settings").json()
        self.assertEqual(s_read["fetch_interval_minutes"], 5)
        self.assertEqual(s_read["lookback_days"], 90)
        self.assertEqual(s_read["email_fetch_limit"], 200)

        # 3. UI 20-point unslop assertions (no purple slop, prefers-reduced-motion, tabular-nums, text-wrap: balance)
        with open(os.path.join(ROOT_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
            html_doc = f.read()
        for purple_tok in ("#a855f7", "#d8b4fe", "#7c3aed", "#8b5cf6", "#a78bfa", "rgba(168, 85, 247", "rgba(147, 51, 234"):
            self.assertNotIn(purple_tok, html_doc, f"Purple slop token found in UI: {purple_tok}")
        self.assertIn("prefers-reduced-motion", html_doc)
        self.assertIn("tabular-nums", html_doc)
        self.assertIn("text-wrap: balance", html_doc)

        # 4. Docker / Unraid container icon image and OCI labels
        self.assertTrue(os.path.exists(os.path.join(ROOT_DIR, "static", "images", "ai-helper-logo.png")))
        with open(os.path.join(ROOT_DIR, "Dockerfile"), "r", encoding="utf-8") as f:
            dockerfile_txt = f.read()
        self.assertIn("net.unraid.docker.icon", dockerfile_txt)
        self.assertIn("org.opencontainers.image.icon", dockerfile_txt)
        self.assertIn("ai-helper-logo.png", dockerfile_txt)

if __name__ == "__main__":
    unittest.main()
