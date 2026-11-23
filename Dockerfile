FROM python:3.11-slim

ARG CONTAINER_ICON_URL=https://raw.githubusercontent.com/plexd281knilb/AI_Helper/main/static/images/ai-helper-logo.png

LABEL net.unraid.docker.icon="${CONTAINER_ICON_URL}" \
      org.opencontainers.image.icon="${CONTAINER_ICON_URL}" \
      net.unraid.docker.webui="http://[IP]:[PORT:8000]/" \
      org.opencontainers.image.title="AI Helper" \
      org.opencontainers.image.description="Intelligent Email Scheduling, Meal Planner & Local Deals" \
      org.opencontainers.image.source="https://github.com/plexd281knilb/AI_Helper"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
