from fastapi import APIRouter, Depends, Request
import datetime

from api2.middleware.auth import verify_token
from api2.dependencies import get_scheduler
from src.core.scheduler import ScheduleInputData

router = APIRouter(dependencies=[Depends(verify_token)])

@router.post('/generate')
async def generate(request: Request):

  scheduler = get_scheduler()

  input_data = ScheduleInputData(
    tasks=[],
    user_id=request.state.userId, 
    target_date=datetime.date.today(),
    fixed_events_input=[],
    preferences=[]
  )

  generated_schedule = await scheduler.generate_schedule(input_data)

  print(request.state.userId)
  print(generated_schedule)

  return None