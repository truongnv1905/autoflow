from pydantic import BaseModel


class LoginRequest(BaseModel):
	username: str
	password: str
	search_keyword: str
