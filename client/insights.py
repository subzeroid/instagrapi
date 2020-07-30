import time

from .decorators import check_login
from .utils import json_value
from .exceptions import UserError, ClientError, MediaError


class Insights:
    @check_login
    def insights_media_feed_all(
        self,
        post_type: str = "ALL",
        time_frame: str = "TWO_YEARS",
        data_ordering: str = "REACH_COUNT",
        count: int = None,
        sleep: int = 2,
    ) -> list:
        """Get insights for all medias from feed with page iteration with cursor and sleep timeout
        :param post_type:       Media type ("ALL", "CAROUSEL_V2", "IMAGE", "SHOPPING", "VIDEO")
        :param time_frame:      Time frame for media publishing date ("ONE_WEEK", "ONE_MONTH", "THREE_MONTHS", "SIX_MONTHS", "ONE_YEAR", "TWO_YEARS")
        :param data_ordering:   Data ordering in instagram response
        :param count:           Max media count for retrieving
        :param sleep:           Timeout between pages iterations
        :return: List with media insights
        :rtype: list
        """
        supported_post_types = ("ALL", "CAROUSEL_V2", "IMAGE", "SHOPPING", "VIDEO")
        supported_time_frames = (
            "ONE_WEEK",
            "ONE_MONTH",
            "THREE_MONTHS",
            "SIX_MONTHS",
            "ONE_YEAR",
            "TWO_YEARS",
        )
        assert post_type in supported_post_types, "Unsupported post type"
        assert time_frame in supported_time_frames, "Unsupported time frame"

        medias = []
        cursor = None
        data = {
            "surface": "post_grid",
            "doc_id": 2345520318892697,
            "locale": "en_US",
            "vc_policy": "insights_policy",
            "strip_nulls": False,
            "strip_defaults": False,
        }
        query_params = {
            "IgInsightsGridMediaImage_SIZE": 480,
            "count": 200,  # TODO Try to detect max allowed value
            # "cursor": "0",
            "dataOrdering": data_ordering,
            "postType": post_type,
            "timeframe": time_frame,
            "search_base": "USER",
            "is_user": "true",
            "queryParams": {"access_token": "", "id": self.user_id},
        }
        while True:
            if cursor:
                query_params["cursor"] = cursor

            result = self.private_request(
                "ads/graphql/", self.with_query_params(data, query_params),
            )
            if not json_value(
                result,
                "data",
                "shadow_instagram_user",
                "business_manager",
                default=None,
            ):
                raise UserError("Account is not business account", **self.last_json)

            stats = result["data"]["shadow_instagram_user"]["business_manager"][
                "top_posts_unit"
            ]["top_posts"]
            cursor = stats["page_info"]["end_cursor"]
            medias.extend(stats["edges"])

            if not stats["page_info"]["has_next_page"]:
                break
            if count is not None and len(medias) >= count:
                break
            time.sleep(sleep)

        return medias[:count]

    @check_login
    def insights_account(self) -> dict:
        """Get insights for account
        :return: Dict with insights
        :rtype: dict
        """
        data = {
            "surface": "account",
            "doc_id": 2449243051851783,
            "locale": "en_US",
            "vc_policy": "insights_policy",
            "strip_nulls": False,
            "strip_defaults": False,
        }
        query_params = {
            "IgInsightsGridMediaImage_SIZE": 360,
            "activityTab": True,
            "audienceTab": True,
            "contentTab": True,
            "query_params": {"access_token": "", "id": self.user_id},
        }

        result = self.private_request(
            "ads/graphql/", self.with_query_params(data, query_params),
        )
        res = json_value(result, "data", "shadow_instagram_user", "business_manager")
        if not res:
            raise UserError("Account is not business account", **self.last_json)
        return res

    @check_login
    def insights_media(self, media_pk: str) -> dict:
        """Get insights data for media
        :param media_pk:  Media id
        :return: Dict with insights data
        :rtype: dict
        """
        media_pk = self.media_pk(media_pk)
        data = {
            "surface": "post",
            "doc_id": 3221905377882880,
            "locale": "en_US",
            "vc_policy": "insights_policy",
            "strip_nulls": False,
            "strip_defaults": False,
        }
        query_params = {
            "query_params": {"access_token": "", "id": media_pk},
        }
        try:
            result = self.private_request(
                "ads/graphql/", self.with_query_params(data, query_params),
            )
            return result['data']['instagram_post_by_igid']
        except ClientError as e:
            raise MediaError(e.message, media_pk=media_pk, **self.last_json)
