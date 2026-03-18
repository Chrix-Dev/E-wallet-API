from fastapi import HTTPException, status
from app.core.redis import redis_client


async def rate_limit(key: str, max_requests: int, window_seconds: int):
    # key is unique per user per action e.g "rate:transfer:user-id"
    current = await redis_client.get(key)

    if current and int(current) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {window_seconds} seconds."
        )

    # increment the counter
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)  # reset the window after N seconds
    await pipe.execute()