import asyncio
from asynciolimiter import Limiter


rate_limiter = Limiter(10 / 1, max_burst=15)


async def request():
    await rate_limiter.wait()  # Wait for a slot to be available.
    print("hello world")  # do stuff


async def main():
    await asyncio.gather(*(request() for _ in range(10)))


asyncio.run(main())
