import os

from call_api.utils import config

SESSION_DIR = config.config['session_manager']['dir_data']


def get_session_path(username: str) -> str:
	return os.path.join(SESSION_DIR, username)


def check_session(username: str) -> dict:
	session_path = get_session_path(username)
	return {'exists': os.path.exists(session_path)}
