class ExploreMixin:
    """
    Helpers for the explore page
    """

    def explore_page(self):
        """
        Get explore page

        Returns
        -------
        dict
        """
        return self.private_request("discover/topical_explore/")

    def report_explore_media(self, media_pk: int):
        """
        Report media in explore page. This is equivalent to the "not interested" button

        Parameters
        ----------
        media_pk: int
            Media PK
        Returns
        -------
        bool
            True if success
        """
        params = {
            "m_pk": media_pk,
        }
        result = self.private_request("discover/explore_report/", params=params)
        return result["explore_report_status"] == "OK"

    def explore_page_media_info(self, media_pk: int):
        """
        Returns media information for a media item on the explore page

        This is the API call that happens when you're on the explore page
        and you click into a media item. It returns information about that media item
        like comments, likes, etc.
        """
        return self.private_request(
            "/v1/discover/media_metadata/", params={"media_id": media_pk}
        )["media_or_ad"]
