import datetime
import os
import time
import asyncio
import logging

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from modbus_service import vigor_service, AirflowMode

logger = logging.getLogger(__name__)

app = FastAPI(title="Ubiflux Vigor Controller")

current_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

# Global variable to track active boost timers
active_boost_task = None
boost_end_timestamp = None

class ModeRequest(BaseModel):
    mode: int


class BoostRequest(BaseModel):
    mode: int
    duration_minutes: int


async def boost_timer_task(mode: int, duration_minutes: int):
    """Background task to hold a mode, then revert to wall unit."""
    logger.info(f"Starting boost: Mode {mode} for {duration_minutes} minutes.")
    vigor_service.set_airflow_mode(AirflowMode(mode))

    try:
        # Sleep for the requested duration
        await asyncio.sleep(duration_minutes * 60)
        logger.info("Boost complete. Reverting to wall unit.")
        vigor_service.revert_to_wall_unit()
    except asyncio.CancelledError:
        logger.info("Previous boost timer was cancelled.")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/status")
def get_status():
    global active_boost_task, boost_end_timestamp

    status = vigor_service.get_status()
    # Format temperatures (raw value is tenths of a degree, e.g., 215 = 21.5C)
    if status.get("supply_temp"):
        status["supply_temp"] = status["supply_temp"] / 10.0
    if status.get("extract_temp"):
        status["extract_temp"] = status["extract_temp"] / 10.0

    is_boosting = active_boost_task is not None and not active_boost_task.done()
    status["is_boosting"] = is_boosting
    status["remaining_seconds"] = "N/A"
    if is_boosting:
        if boost_end_timestamp is not None:
            remaining_seconds = max(0, int(boost_end_timestamp - time.time()))
            status["remaining_seconds"] = str(datetime.timedelta(seconds=remaining_seconds))

    logger.info(f"Returning status: {status}")
    return status


@app.post("/api/mode")
def set_permanent_mode(req: ModeRequest):
    global active_boost_task
    # Cancel any running timer since user requested a permanent change
    if active_boost_task:
        active_boost_task.cancel()

    success = vigor_service.set_airflow_mode(AirflowMode(req.mode))
    return {"status": "success" if success else "error"}


@app.post("/api/revert")
def revert_to_wall():
    global active_boost_task, boost_end_timestamp
    if active_boost_task:
        active_boost_task.cancel()
        active_boost_task = None  # Clear the reference
        boost_end_timestamp = None
        logger.info("Boost manually cancelled by user.")

    success = vigor_service.revert_to_wall_unit()
    return {"status": "success" if success else "error"}


@app.post("/api/boost")
async def trigger_boost(req: BoostRequest):
    global active_boost_task, boost_end_timestamp

    # If a timer is already running, cancel it before starting the new one
    if active_boost_task:
        active_boost_task.cancel()

    # Start the new background timer
    active_boost_task = asyncio.create_task(
        boost_timer_task(req.mode, req.duration_minutes)
    )
    boost_end_timestamp = time.time() + (req.duration_minutes * 60)
    return {"status": "boost_started", "duration": req.duration_minutes}