from fastapi import Header, HTTPException, status

from app.config import API_KEY


async def check_api_key(x_api_key: str | None = Header(default=None, alias="X-Api-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
