import uvicorn
from fastapi import FastAPI

from api2.routes.schedules import router as schedules_router

app = FastAPI()

app.include_router(schedules_router, prefix="/schedules")

# test endpoint
@app.get('/')
async def index():
  return {"message": "Hello, World!"}

# healthcheck endpoint
@app.get('/healthcheck', status_code=204)
def healthcheck():
  return None

if __name__ == "__main__":
  uvicorn.run(
    "api2.main:app",
    port=3000,
    host="0.0.0.0",
    reload=True,
    log_level="debug",
  )