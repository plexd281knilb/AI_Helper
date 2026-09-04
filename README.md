# AI Helper

An AI-powered web application that pulls emails, extracts calendar events using AI, scans local grocery circulars to find the best prices, and helps you create smart grocery lists. Designed to run seamlessly in Docker on Unraid or any server.

## Features

- **Email Fetching**: Connects via IMAP to read incoming emails.
- **AI Event Extraction**: Analyzes email content to detect events, deadlines, dates, and times using Google Gemini or OpenAI.
- **Google Calendar Sync**: Add individual or batch sync events directly to Google Calendar.
- **🛒 Deals & Local Grocery Intelligence**:
  - **1-Click Zip Code Discovery**: Ingest and track weekly circulars and deals automatically across all local supermarkets (HEB, Kroger, Tom Thumb, Albertsons, Sprouts, ALDI, Whole Foods, Walmart, Costco, Target, etc.) based on your zip code.
  - **Browse & Filter Deals**: Department and category filtering (Produce, Meat & Seafood, Dairy, Pantry, etc.) with live search and 1-click list adding.
  - **AI Deal Comparison**: Natural language AI search to compare prices and find the best local bargains across all your local stores.
  - **Smart Grocery Lists**: Interactive grocery lists with category/store grouping, check-off status, clipboard copy, and AI meal plan generator.
- **Dockerized**: Easy multi-user deployment on Unraid or any Docker host with persistent SQLite storage.

## Setup

1. Copy `.env.example` to `.env` (or configure settings directly in the web UI).
2. Run `docker-compose up -d`.
3. Access the dashboard at `http://localhost:8000`.
