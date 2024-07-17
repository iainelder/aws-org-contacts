from pyrate_limiter import Rate, Limiter

# The docs for PyRateLimiter are so confusing.
# This is the best I can do using the Decorator
# https://github.com/vutran1710/PyrateLimiter/?tab=readme-ov-file#decorator

# It causes this error in the real code.
# botocore.exceptions.ClientError: An error occurred (408) when calling the ListAccounts operation:

def limiter(rate: Rate):
    def mapping(*args) -> str:
        return "limiter", 1
    return Limiter(rate, max_delay=60_000).as_decorator()(mapping)

@limiter(Rate(1, 100))
def print_n(n: int) -> None:
    print(n, end=", ", flush=True)

for n in range(40):
    print_n(n)
