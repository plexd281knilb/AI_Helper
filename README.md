# AI Helper

An AI-powered web application that pulls emails, extracts calendar events using AI, scans local grocery circulars to find the best prices, and helps you create smart grocery lists. Designed to run seamlessly in Docker on Unraid or any server.

## Features

- **Email Fetching**: Connects via IMAP to read incoming emails.
- **AI Event Extraction**: Analyzes email content to detect events, deadlines, dates, and times using Google Gemini or OpenAI.
- **Google Calendar Sync**: Add individual or batch sync events directly to Google Calendar.
- **🛒 Deals & Local Grocery Intelligence**:
  - Track weekly ads and circulars from stores like HEB, Kroger, Tom Thumb, Costco, Sprouts, Whole Foods, Walmart, and custom links.
  - Natural language AI search to compare prices and find the best local bargains.
  - Smart interactive grocery lists with category/store sorting, item check-off, and clipboard export.
  - AI meal plan list generator that auto-assigns items to the best stores.
- **Dockerized**: Easy multi-user deployment on Unraid or any Docker host with persistent SQLite storage.

## Setup

1. Copy `.env.example` to `.env` (or configure settings directly in the web UI).
2. Run `docker-compose up -d`.
3. Access the dashboard at `http://localhost:8000`.
