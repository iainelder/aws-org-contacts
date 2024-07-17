import asyncio
import random

# I extended kalmlake's great starter example.
# https://medium.com/@kalmlake/async-io-in-python-queues-0916d8b5645a

async def account_producer(
        queue: asyncio.Queue[str|None],
        sentinels: int=0
) -> None:

    for i in range(4):
        await asyncio.sleep(random.random())
        for j in range(5):
            await queue.put(f"{i}.{j}")
    for _ in range(sentinels):
        await queue.put(None)
    print(f"Finished producing")


async def account_consumer(
    account_queue: asyncio.Queue[str|None],
    result_queue: asyncio.Queue[str|Exception|None],
) -> None:

    while True:
        item = await account_queue.get()
        if item is None:
            await result_queue.put(None)
            account_queue.task_done()
            break
        try:
            await asyncio.sleep(random.random())
            if random.random() > .1:
                await result_queue.put(item)
            else:
                raise Exception("Exception")
        except Exception as ex:
            await result_queue.put(ex)
        finally:
            account_queue.task_done()


async def result_printer(
    result_queue: asyncio.Queue[str|Exception|None],
    sentinels: int=0
) -> None:

    while sentinels > 0:
        item = await result_queue.get()
        if item is None:
            sentinels -= 1
            result_queue.task_done()
            continue
        print(repr(item), flush=True)
        result_queue.task_done()


async def main() -> None:

    account_queue = asyncio.Queue[str|None]()
    result_queue = asyncio.Queue[str|Exception|None]()
    workers = 4
    await asyncio.gather(
        account_producer(account_queue, sentinels=workers),
        *[account_consumer(account_queue, result_queue) for _ in range(workers)],
        result_printer(result_queue, sentinels=workers),
    )

asyncio.run(main())
