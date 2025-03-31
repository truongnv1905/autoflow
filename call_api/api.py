from fastapi import APIRouter

from call_api.linkedin_func import search_companies
from call_api.schema import LoginRequest
from call_api.session_manager import check_session

router = APIRouter()


@router.post('/linkedin/')
async def search(data: LoginRequest):
	return await search_companies(data)


@router.get('/check_session/{username}')
async def check(username: str):
	return check_session(username)
