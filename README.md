# Gitea Webhook to Plane Integration

This FastAPI application receives webhooks from Gitea and posts comments to Plane issues when pull requests are created or updated.

## Setup

### 1. Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Plane API Configuration
PLANE_API_TOKEN=your_plane_api_token_here
WORKSPACE_SLUG=aoc
PLANE_BASE_URL=https://plane.loolootest.com
```

### 2. Running with Docker Compose

```bash
# Build and start the application
docker-compose up --build

# Run in detached mode (background)
docker-compose up -d --build

# Stop the application
docker-compose down

# View logs
docker-compose logs -f fastapi-app
```

### 3. API Endpoints

- **GET /**: Health check endpoint
- **POST /gitea-webhook**: Webhook endpoint for Gitea

### 4. Local Development

The Docker setup includes volume mounting for hot reload during development. Any changes to the Python files will automatically restart the application.

### 5. Testing

The application will be available at `http://localhost:8000`

You can test the health endpoint:

```bash
curl http://localhost:8000/
```

## How it Works

1. Gitea sends a webhook to `/gitea-webhook` when a pull request is created/updated
2. The application extracts the Plane task ID from the pull request body
3. If a Plane link is found, it posts a comment to the corresponding Plane issue
4. The comment includes pull request details and a link back to the PR
