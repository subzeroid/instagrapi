class FundraiserMixin:
    """
    Helpers for the fundraisers.
    """

    def standalone_fundraiser_info_v1(self, user_id: str):
        """
        Get fundraiser info.

        Parameters
        ----------
        user_id: str
            User id of an instagram account

        Returns
        -------
        dict
        """
        user_id = str(user_id)
        return self.private_request(f"fundraiser/{user_id}/standalone_fundraiser_info/")
