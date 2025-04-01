from pydantic import BaseModel


class SearchRequest(BaseModel):
	username: str
	password: str
	search_keyword: str
	max_companies: int = 100


class SearchPeopleRequest(BaseModel):
	username: str
	company_url: str
