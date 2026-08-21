# AI Helper

An AI-powered web application that pulls emails, extracts calendar events using AI, and presents them in a dashboard to easily add to Google Calendar. Designed to run in a Docker container on Unraid.

## Features

- **Email Fetching**: Connects via IMAP to read incoming emails.
- **AI Processing**: Analyzes email content to detect events, dates, and times.
- **Dashboard**: Web UI to view detected events.
- **Google Calendar Integration**: Add events directly to your calendar with a click.
- **Dockerized**: Easy deployment on Unraid or any Docker host.

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials.
2. Run `docker-compose up -d`.
3. Access the dashboard at `http://localhost:8000`.
