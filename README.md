# aws-org-contacts

## Rate Limiting

I read [Justin Van Winkle's survey of Python rate-limiting libraries](https://gist.github.com/justinvanwinkle/d9f04950083c4554835c1a35f9d22dad), and chose to use the least "broken" one, [limits](https://limits.readthedocs.io/en/stable/).

I'm still looking for a rate limiter that can smooth out the requests such that if the rate is 10 per second, then the requests will be smoothed to roughly 1 every 100 milliseconds. Or one that just lets me set the rate at the subsecond level to get the same effect.

## Prove the queue concept

```bash
poetry run python ./async_queue.py | cat -n
```

The final output should look like this:

```
     1	Exception('Exception')
     2	'0.1'
     3	'0.2'
     4	'0.3'
     5	'1.0'
     6	'0.4'
     7	Exception('Exception')
     8	'2.0'
     9	Finished producing
    10	'1.3'
    11	'2.1'
    12	'2.2'
    13	'2.4'
    14	'1.2'
    15	'1.4'
    16	'3.0'
    17	'3.2'
    18	'3.1'
    19	'3.4'
    20	'3.3'
    21	'2.3'
```

Page level results are mostly ordered, but it's fuzzy.

The last item from page n+1 may complete before the last item from page n.

Item level results within a page are mostly shuffled.

Exceptions from the main processor propagate to the results.

Reuslts are processed and displayed while inputs are still being produced.

All inputs are processed and displayed.

## Future work

Use a class to avoid some of the excessive nesting that makes the code hard to follow.

Instantiate the clients like this. See the [aioboto3 usage doc](https://aioboto3.readthedocs.io/ en/latest/usage.html) for how to use an AsyncExitStack to make this cleaner.

```python
class OrgContacts:

    @classmethod
    async def create(cls, session: aioboto3.Session):
        self = cls()
        self.session = session
        self.org_client = await self.session.client("organizations").__aenter__()
        self.acc_client = await self.session.client("organizations").__aenter__()
        return self
```

Configure aioboto3 to retry more on throttling errors from GetAlternateContact. I don't have a simple repro, but the current structure somehow ignores the retry configuration. So the program just runs at half the advertised throttling limit to avoid throttling.

Alternatively, put failed tasks back on the queue (put account subtasks on queue). Look to orgtreepubsub for ideas. Use a framework that makes all the queue and retry plumbing easier.
