import uvicorn
from fastapi import FastAPI

from call_api.api import router  # Import router từ api.py

app = FastAPI()
app.include_router(router)  # Gộp tất cả endpoints vào FastAPI

if __name__ == '__main__':
	uvicorn.run(app, host='0.0.0.0', port=8000)
