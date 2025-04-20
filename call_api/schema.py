from typing import List, Optional

from pydantic import BaseModel


class SearchRequestJobs(BaseModel):
	username: str
	password: str
	search_keyword: str
	numbers: int = 100
	location: str
	days_ago: int
	# Sorting and filtering options
	sort_by: Optional[str] = None  # 'DD' for Date Descending, 'R' for Relevance
	experience_levels: Optional[List[int]] = (
		None  # 1=Internship, 2=Entry level, 3=Associate, 4=Mid-Senior, 5=Director, 6=Executive
	)
	company_ids: Optional[List[str]] = None  # LinkedIn company IDs
	job_types: Optional[List[str]] = (
		None  # 'F'=Full-time, 'C'=Contract, 'P'=Part-time, 'T'=Temporary, 'I'=Internship, 'V'=Volunteer
	)
	remote: bool = False  # Whether to filter for remote jobs only
	industry_ids: Optional[List[str]] = None  # LinkedIn industry IDs


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
