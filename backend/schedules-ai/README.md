# Schedules AI

API for generating personalized schedules, managing user data, and processing feedback.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- PostgreSQL (optional, for database support)
- Docker and Docker Compose (optional, for containerized deployment)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/auratyme-backend.git
   cd auratyme-backend/schedules-ai
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env.dev` and modify as needed
   - For development, you can use the default values

## Running the API Server

### Without JWT Authentication

```bash
# Windows
python scripts/run_api_server_no_db.py

# Unix/Linux
python scripts/run_api_server_no_db.py
```

### With JWT Authentication

#### Windows

Option 1: Using the batch script
```bash
scripts\run_api_server_with_jwt.bat
```

Option 2: Using the Python script
```bash
python scripts/run_api_server_with_jwt.py
```

#### Unix/Linux

Option 1: Using the shell script
```bash
chmod +x scripts/run_api_server_with_jwt.sh
./scripts/run_api_server_with_jwt.sh
```

Option 2: Setting environment variables manually
```bash
export ENABLE_JWT_AUTH=true
export DISABLE_DB=true
python -m api.server
```

## Testing

### Testing JWT Authentication

```bash
python scripts/test_jwt_auth.py
```

### Testing User Schedules

```bash
python scripts/test_user_schedules.py
```

### Testing APIdog Endpoints

```bash
python scripts/test_apidog_endpoints.py
```

## Docker Deployment

To run the API server in Docker:

```bash
docker-compose up schedules-ai schedules-ai-db api-gateway
```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Public Endpoints

- `GET /health`: Health check endpoint
- `GET /v1/apidog/schedules`: List all available schedules
- `GET /v1/apidog/schedule/{schedule_id}`: Get a specific schedule
- `GET /v1/apidog/latest-schedule`: Get the latest schedule

### Authenticated Endpoints

- `GET /v1/auth/schedules`: List all available schedules (requires JWT)
- `GET /v1/auth/schedule/{schedule_id}`: Get a specific schedule (requires JWT)
- `GET /v1/auth/latest-schedule`: Get the latest schedule (requires JWT)
- `GET /v1/auth/generate-token/{user_id}`: Generate a test JWT token (development only)

### User Schedules Endpoints

- `GET /v1/user-schedules`: List all schedules for the authenticated user
- `GET /v1/user-schedules/{schedule_id}`: Get a specific schedule for the authenticated user
- `POST /v1/user-schedules`: Create a new schedule for the authenticated user
- `PATCH /v1/user-schedules/{schedule_id}`: Update a schedule for the authenticated user
- `DELETE /v1/user-schedules/{schedule_id}`: Delete a schedule for the authenticated user

## License

This project is licensed under the MIT License - see the LICENSE file for details.
