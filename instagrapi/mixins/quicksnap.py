import time
from pathlib import Path
from typing import Dict, Optional

from instagrapi.exceptions import ClientGraphqlError

QUICKSNAP_HISTORY_CLIENT_DOC_ID = "202528380816979569862257718136"
QUICKSNAP_HISTORY_FRIENDLY_NAME = "IGQuickSnapGetHistoryPaginatedQuery"
QUICKSNAP_CLIENT_ENDPOINT = "InsightsHostImpl:quick_snap_audience_picker"


class QuickSnapMixin:
    @staticmethod
    def _quick_snap_history_from_graphql_result(result: Dict) -> Dict:
        viewer = (result.get("data") or {}).get("viewer") or {}
        for key, value in viewer.items():
            if "quick_snap_paginated_history" in key and isinstance(value, dict):
                return value
        raise ClientGraphqlError("Failed to retrieve QuickSnap history")

    @staticmethod
    def _quick_snap_nav_chain() -> str:
        timestamp = time.time()
        return (
            f"DirectInboxFragment:direct_inbox:2:main_direct:{timestamp - 55:.3f}:::{timestamp - 55:.3f},"
            f"QuickSnapUnifiedFragment:quicksnap_unified_fragment:3:button:{timestamp - 20:.3f}:::{timestamp - 20:.3f},"
            f"ConstAnalyticsModule:quick_snap_camera:4:button:{timestamp - 19:.3f}:::{timestamp - 19:.3f},"
            f"{QUICKSNAP_CLIENT_ENDPOINT}:6:button:{timestamp - 5:.3f}:::{timestamp - 5:.3f}"
        )

    def quicksnap_history(self, amount: int = 20, end_cursor: Optional[str] = None) -> Dict:
        """
        Retrieve paginated QuickSnap history.

        Parameters
        ----------
        amount: int, optional
            Number of QuickSnap history items to fetch.
        end_cursor: str, optional
            Cursor from the previous response ``page_info.end_cursor``.

        Returns
        -------
        Dict
            Raw ``quick_snap_paginated_history`` payload with ``edges`` and ``page_info``.
        """
        assert self.user_id, "Login required"
        variables = {"first": amount}
        if end_cursor:
            variables["after"] = end_cursor
        result = self.private_graphql_www_request(
            friendly_name=QUICKSNAP_HISTORY_FRIENDLY_NAME,
            variables=variables,
            client_doc_id=QUICKSNAP_HISTORY_CLIENT_DOC_ID,
        )
        return self._quick_snap_history_from_graphql_result(result)

    def quicksnap_send(self, photo_path: Path, audience: str = "mutual_followers", upload_id: str = "") -> Dict:
        """
        Upload and publish a photo as a QuickSnap.

        Parameters
        ----------
        photo_path: Path
            Path to a photo file.
        audience: str, optional
            QuickSnap audience value, default ``mutual_followers``.
        upload_id: str, optional
            Upload id to reuse. Generated when omitted.

        Returns
        -------
        Dict
            Raw ``media/configure_to_quick_snap/`` response.
        """
        assert self.user_id, "Login required"
        photo_path = Path(photo_path)
        upload_id, _, _ = self.photo_rupload(photo_path, upload_id) if upload_id else self.photo_rupload(photo_path)
        nav_chain = self._quick_snap_nav_chain()
        data = {
            "original_height": "0",
            "original_width": "0",
            "include_e2ee_mentioned_user_list": "1",
            "hide_from_profile_grid": "false",
            "timezone_offset": str(self.timezone_offset),
            "source_type": "3",
            "_uid": str(self.user_id),
            "async_publish": "1",
            "device_id": self.android_device_id,
            "_uuid": self.uuid,
            "nav_chain": nav_chain,
            "audience": audience,
            "upload_id": upload_id,
            "bottom_camera_dial_selected": "11",
            "publish_id": "1",
            "product_type": "quick_snap",
            "device": self.device,
            "quick_snap_data": {},
        }
        return self.private_request(
            "media/configure_to_quick_snap/",
            self.with_default_data(data),
            headers={
                "X-IG-Client-Endpoint": QUICKSNAP_CLIENT_ENDPOINT,
                "X-IG-Nav-Chain": nav_chain,
            },
        )

    def quicksnap_delete(self, media_id: str) -> bool:
        """
        Soft-delete an active QuickSnap.

        Parameters
        ----------
        media_id: str
            QuickSnap media id.

        Returns
        -------
        bool
            ``True`` when Instagram confirms deletion.
        """
        assert self.user_id, "Login required"
        media_id = str(media_id)
        result = self.private_request(
            f"media/{media_id}/soft_delete/",
            {"media_id": media_id, "_uuid": self.uuid},
        )
        return result.get("did_delete") is True
