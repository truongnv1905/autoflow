from fastapi import APIRouter

from call_api import google_func, linkedin_func
from call_api.schema import SearchPeopleRequest, SearchRequestJobs
from call_api.session_manager import check_session

router = APIRouter()


@router.post('/linkedin/search_companies')
async def linkedin_search_companies(data: SearchRequestJobs):
	return await linkedin_func.search_companies(data)


@router.post('/linkedin/search_employees')
async def linkedin_search_employees(data: SearchPeopleRequest):
	return await linkedin_func.get_info_employees(data)


@router.post('/linkedin/search_jobs')
async def linkedin_search_jobs(data: SearchRequestJobs):
	return await linkedin_func.search_jobs(data)


@router.post('/google/search_jobs')
async def google_search_jobs(data: SearchRequestJobs):
	return await google_func.searching_jobs(data)


@router.post('/google/search_company_linkedin')
async def google_search_company_linkedin(username: str, password: str, company_name: str, location: str):
	"""
	Search for a company's LinkedIn profile using Google search

	Args:
	    company_name: Name of the company to search for
	    location: Location of the company

	Returns:
	    str: LinkedIn URL of the company if found, empty string otherwise
	"""
	return await google_func.search_company_linkedin(username, password, company_name, location)


@router.get('/check_session/{username}')
async def check(username: str):
	return check_session(username)
