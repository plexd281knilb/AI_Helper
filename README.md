# AI Helper

An AI-powered web application that pulls emails, extracts calendar events using AI, scans local grocery circulars to find the best prices, and helps you create smart grocery lists. Designed to run seamlessly in Docker on Unraid or any server.

## Features

- **Multi-Account Email Ingestion**: Connects via IMAP across multiple accounts with per-account fault isolation and automated webview school announcement scraping.
- **AI Event Extraction**: Analyzes email content to detect events, deadlines, dates, and times using Google Gemini or OpenAI.
- **Google Calendar Sync**: Robust ISO parsing with individual and batch event push directly to Google Calendar.
- **Enterprise Security**: Salted PBKDF2-HMAC-SHA256 password hashing (100,000 iterations), automatic session expiration cleanup, and XSS sanitization.
- **High-Performance SQLite**: Automated schema indexing on events, accounts, history, and grocery deals for sub-millisecond multi-user queries.
- **🛒 Deals & Local Grocery Intelligence**:
  - **1-Click Zip Code Discovery**: Ingest and track weekly circulars and deals automatically across all local supermarkets (HEB, Kroger, Tom Thumb, Albertsons, Sprouts, ALDI, Whole Foods, Walmart, Costco, Sam's Club, Publix, Safeway, Central Market, Food Lion, Meijer, Hy-Vee, Wegmans, Lidl, Jewel-Osco, Vons, Ralphs, and more) based on your zip code.
  - **Stemmed Cross-Store Comparison**: Noun plural stemming and cents-to-dollars price normalization match equivalent items across stores to highlight bargains and flag better prices.
  - **Browse & Filter Deals**: Department and category filtering (Produce, Meat & Seafood, Dairy, Pantry, etc.) with live search and 1-click list adding.
  - **AI Deal Comparison**: Natural language AI search to compare prices and find the best local bargains across all your local stores.
  - **Smart Grocery Lists**: Interactive grocery lists with category/store grouping, check-off status, transparent cutout packshots, clipboard copy, and AI meal plan generator.
- **Dockerized**: Easy multi-user deployment on Unraid or any Docker host with persistent SQLite storage and integrated `/health` healthcheck.

## Setup

1. Copy `.env.example` to `.env` (or configure settings directly in the web UI).
2. Run `docker-compose up -d`.
3. Access the dashboard at `http://localhost:8000`.
