from fastapi import APIRouter

from call_api.linkedin_func import get_info_employees, search_companies
from call_api.schema import SearchPeopleRequest, SearchRequest
from call_api.session_manager import check_session

router = APIRouter()


@router.post('/linkedin/search_companies')
async def search(data: SearchRequest):
	return await search_companies(data)


@router.post('/linkedin/search_employees')
async def search_employees(data: SearchPeopleRequest):
	return await get_info_employees(data)


@router.get('/check_session/{username}')
async def check(username: str):
	return check_session(username)
