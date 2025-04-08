from pydantic import BaseModel


class SearchRequestJobs(BaseModel):
	username: str
	password: str
	search_keyword: str
	numbers: int = 100
	location: str
	days_ago: int


class SearchRequestCompanies(BaseModel):
	username: str
	password: str
	search_keyword: str
	numbers: int = 100
	location: str
	after_time: str


class SearchPeopleRequest(BaseModel):
	username: str
	company_url: str
