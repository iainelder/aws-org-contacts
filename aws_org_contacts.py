import asyncio
from typing import AsyncIterable
from dataclasses import dataclass
from dataclasses_json import dataclass_json

import aioboto3
from types_aiobotocore_organizations.type_defs import AccountTypeDef
from types_aiobotocore_account.type_defs import AlternateContactTypeDef
from types_aiobotocore_account.literals import AlternateContactTypeType
from botocore.exceptions import ClientError
from asynciolimiter import Limiter

@dataclass_json
@dataclass
class AccountContact:
    account_id: str
    contact_type: str
    email_address: str


async def account_producer(
    session: aioboto3.Session,
    queue: asyncio.Queue[AccountTypeDef | None],
    sentinels: int = 0
) -> None:

    async for account in iter_accounts(session):
        await queue.put(account)

    for _ in range(sentinels):
        await queue.put(None)


async def iter_accounts(session: aioboto3.Session) -> AsyncIterable[AccountTypeDef]:
    async with session.client("organizations") as orgs:
        pages = orgs.get_paginator("list_accounts").paginate()
        async for page in pages:
            for account in page["Accounts"]:
                yield account


async def account_consumer(
    session: aioboto3.Session,
    account_queue: asyncio.Queue[AccountTypeDef | None],
    result_queue: asyncio.Queue[AccountContact | Exception | None],
) -> None:

    while True:
        item = await account_queue.get()
        if item is None:
            await result_queue.put(None)
            account_queue.task_done()
            break
        try:
            for contact in await asyncio.gather(
                get_root_contact(session, item),
                get_alternate_contact(session, item, "BILLING"),
                get_alternate_contact(session, item, "SECURITY"),
                get_alternate_contact(session, item, "OPERATIONS"),
            ):
                if contact:
                    await result_queue.put(contact)
        except Exception as ex:
            await result_queue.put(ex)
        finally:
            account_queue.task_done()


async def get_root_contact(
    session: aioboto3.Session,
    account: AccountTypeDef,
) -> AccountContact:

    return AccountContact(
        account_id=account["Id"],
        contact_type="ROOT",
        email_address=account["Email"],
    )


# The published rate is "10 per second, burst to 15 per second".
# https://docs.aws.amazon.com/accounts/latest/reference/quotas.html
# Even then sometimes it throttles! So run at half the rate and hope it never
# throttles.
# See future work in the README for how to improve this.
limiter = Limiter(5, max_burst=7)

async def get_alternate_contact(
    session: aioboto3.Session,
    account: AccountTypeDef,
    contact_type: AlternateContactTypeType,
) -> AccountContact | None:

    args = {"AlternateContactType": contact_type, "AccountId": account["Id"]}

    async with session.client("account") as client:
        try:
            while True:
                try:
                    await limiter.wait()
                    contact: AlternateContactTypeDef = (
                        await client.get_alternate_contact(**args)
                    )["AlternateContact"]

                    return AccountContact(
                        account_id=account["Id"],
                        contact_type=contact["AlternateContactType"],
                        email_address=contact["EmailAddress"],
                    )
                except ClientError as ex:
                    message_fragment = (
                        "The management account can only be managed using the "
                        "standalone context from the management account."
                    )
                    if (
                        ex.response["Error"]["Code"] == "AccessDeniedException"
                        and message_fragment in ex.response["Error"]["Message"]
                    ):
                        del args["AccountId"]
                        continue
                    raise
        except ClientError as ex:
            if ex.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            raise


async def result_printer(
    result_queue: asyncio.Queue[AccountContact | Exception | None], sentinels: int = 0
) -> None:

    while sentinels > 0:
        item = await result_queue.get()
        if item is None:
            sentinels -= 1
            result_queue.task_done()
            continue

        # Ugly hack until I figure out consistent exception handling, such as
        # a generic result object with an optional error property.
        if isinstance(item, Exception):
            import json
            print(json.dumps(str(item)))
        else:
            print(item.to_json(), flush=True)

        result_queue.task_done()


async def main() -> None:

    session = aioboto3.Session()
    account_queue = asyncio.Queue[AccountTypeDef | None]()
    result_queue = asyncio.Queue[AccountContact | Exception | None]()
    workers = 4
    await asyncio.gather(
        account_producer(session, account_queue, sentinels=workers),
        *[
            account_consumer(session, account_queue, result_queue)
            for _ in range(workers)
        ],
        result_printer(result_queue, sentinels=workers),
    )


if __name__ == "__main__":
    asyncio.run(main())
