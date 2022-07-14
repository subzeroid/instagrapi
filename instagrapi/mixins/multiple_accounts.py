class MultipleAccountsMixin:
    """
    Helpers for multiple accounts.
    """

    def featured_accounts_v1(self, target_user_id: int) -> dict:
        target_user_id = str(target_user_id)
        return self.private_request(
            "multiple_accounts/get_featured_accounts/",
            params={
                "target_user_id": target_user_id
            }
        )

    def get_account_family_v1(self) -> dict:
        return self.private_request("multiple_accounts/get_account_family/")
