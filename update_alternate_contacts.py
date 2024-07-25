from functools import cached_property
from typing import Iterable, Callable
from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_organizations.type_defs import AccountTypeDef
from mypy_boto3_organizations import OrganizationsClient
from mypy_boto3_account import AccountClient
import json


class MissingAccount(Exception):
    def __init__(self, account_id: str) -> None:
        self.account_id = account_id
        super().__init__(account_id)

    def __str__(self) -> str:
        return f"Missing account: {self.account_id}"


def main():

    account_index: int = 0

    def print_start(account_id: str, owner_email_address: str) -> None:
        nonlocal account_index
        print(
            f"{account_index:03}: Set alternate contacts for {account_id} to {owner_email_address}."
        )

    def print_success(*args, **kwargs) -> None:
        nonlocal account_index
        account_index += 1

    def print_error(
        account_id: str, owner_email_address: str, error: Exception
    ) -> None:
        nonlocal account_index
        print(f"{account_index:03}: Error for account {account_id}: {error}")
        account_index += 1

    updater = ContactUpdater(Session())
    print(f"Will update alternate contacts for {len(updater.owner_map)} accounts.")
    updater.update_all_contacts(print_start, print_success, print_error)


class ContactUpdater:

    def __init__(self, session: Session) -> None:
        self.session = session
        self.org_client: OrganizationsClient = session.client("organizations")
        self.acc_client: AccountClient = session.client("account")

    @cached_property
    def owner_map(self) -> dict[str, str]:
        return self.build_account_owner_map()

    @cached_property
    def accounts(self) -> dict[str, AccountTypeDef]:
        return {ac["Id"]: ac for ac in self.iter_active_accounts()}

    @cached_property
    def management_account_id(self) -> str:
        org = self.org_client.describe_organization()["Organization"]
        return org["MasterAccountId"]

    def update_all_contacts(
        self,
        start_callback: Callable[[str, str], str],
        end_callback: Callable[[str, str], str],
        error_callback: Callable[[str, str, Exception], str],
    ) -> None:
        for account_id, owner_email_address in self.owner_map.items():
            try:
                if account_id not in self.accounts:
                    raise MissingAccount(account_id)

                start_callback(account_id, owner_email_address)
                self.set_all_alternate_contacts_for_account(
                    account_id, owner_email_address
                )
                end_callback(account_id, owner_email_address)

            except MissingAccount as error:
                error_callback(account_id, owner_email_address, error)

            except ClientError as error:
                if error.response["Error"]["Code"] != "ValidationException":
                    raise
                error_callback(account_id, owner_email_address, error)

    def build_account_owner_map(self) -> dict[str, str]:
        with open("owners.jsonl") as f:
            records = [json.loads(line) for line in f]
            return {r["account_id"]: r["workload_owner"] for r in records}

    def iter_active_accounts(self) -> Iterable[AccountTypeDef]:
        pages = self.org_client.get_paginator("list_accounts").paginate()
        for page in pages:
            for account in page["Accounts"]:
                if account["Status"] == "ACTIVE":
                    yield account

    def set_all_alternate_contacts_for_account(
        self,
        account_id: str,
        email_address: str,
    ):
        for contact_type in ["BILLING", "SECURITY", "OPERATIONS"]:
            self.set_alternate_contact(account_id, contact_type, email_address)

    def set_alternate_contact(
        self,
        account_id: str,
        contact_type: str,
        email_address: str,
    ) -> None:

        args = dict(
            AccountId=account_id,
            AlternateContactType=contact_type,
            EmailAddress=email_address,
            Name="",  # TODO: Include name input.
            Title="",  # TODO: Include title input.
            PhoneNumber="0",  # TODO: Include phone number input.
        )

        if account_id == self.management_account_id:
            del args["AccountId"]

        self.acc_client.put_alternate_contact(**args)


if __name__ == "__main__":
    main()
