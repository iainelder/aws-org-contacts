import time
from limits import RateLimitItemPerSecond
from limits.aio import storage
from limits.aio import strategies

memory_storage = storage.MemoryStorage()

moving_window = strategies.MovingWindowRateLimiter(memory_storage)

rate = RateLimitItemPerSecond(1, 1)

while not moving_window.test(rate, "test_namespace"):
    time.sleep(0.01)
assert moving_window.hit(rate, "test_namespace")
