from limits import storage
memory_storage = storage.MemoryStorage()

from limits import strategies
moving_window = strategies.MovingWindowRateLimiter(memory_storage)

from limits import parse
one_per_minute = parse("1/minute")

from limits import RateLimitItemPerSecond, R
some_per_second = parse("10/second")

import time

for i in range(100):
    while not moving_window.test(some_per_second, "test_namespace"):
        time.sleep(0.01)
    assert moving_window.hit(some_per_second, "test_namespace")
    print(i)

# TODO: Try https://github.com/upstash/ratelimit-py
