from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import database

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingRequest(BaseModel):
    key: str
    value: str

@router.get("/{key}")
async def get_setting_endpoint(key: str):
    value = database.get_setting(key)
    if value is None:
        return {"key": key, "value": None}
    return {"key": key, "value": value}

@router.post("")
async def set_setting_endpoint(request: SettingRequest):
    database.set_setting(request.key, request.value)
    return {"status": "success", "key": request.key, "value": request.value}
