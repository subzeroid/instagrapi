MUTE_ALL_ITEMS = ("cancel", "15_minutes", "1_hour", "2_hour", "4_hour", "8_hour")
SETTING_VALUE_ITEMS = ("off", "following_only", "everyone")

try:
    from typing import Literal
    MUTE_ALL = Literal[MUTE_ALL_ITEMS]
    SETTING_VALUE = Literal[SETTING_VALUE_ITEMS]
except ImportError:
    # python <= 3.8
    MUTE_ALL = str
    SETTING_VALUE = str


class NotificationMixin:
    """
    Helpers for notification settings
    """

    def notification_settings(self, content_type: str, setting_value: str) -> bool:
        data = {
            "content_type": content_type,
            "setting_value": setting_value,
            "_uid": str(self.user_id),
            "_uuid": self.uuid,
        }
        result = self.private_request(
            "notifications/change_notification_settings/",
            data=data
        )
        return result.get("status") == "ok"

    def notification_disable(self) -> bool:
        """
        Disable All Notification

        Returns
        -------
        bool
        """
        notifications = (
            self.notification_likes,
            self.notification_like_and_comment_on_photo_user_tagged,
            self.notification_user_tagged,
            self.notification_comments,
            self.notification_comment_likes,
            self.notification_first_post,
            self.notification_new_follower,
            self.notification_follow_request_accepted,
            self.notification_connection,
            self.notification_tagged_in_bio,
            self.notification_pending_direct_share,
            self.notification_direct_share_activity,
            self.notification_direct_group_requests,
            self.notification_video_call,
            self.notification_rooms,
            self.notification_live_broadcast,
            self.notification_felix_upload_result,
            self.notification_view_count,
            self.notification_fundraiser_creator,
            self.notification_fundraiser_supporter,
            self.notification_reminders,
            self.notification_announcements,
            self.notification_report_updated,
            self.notification_login,
        )
        return all(func("off") for func in notifications)

    def notification_mute_all(self, setting_value: MUTE_ALL = "8_hour") -> bool:
        """
        Manage Mute All Notification Settings

        Parameters
        ----------
        setting_value: MUTE_ALL
            Value of settings, default "8_hour"

        Returns
        -------
        bool
        """
        assert setting_value in MUTE_ALL_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {MUTE_ALL_ITEMS}'
        return self.notification_settings("mute_all", setting_value)

    def notification_likes(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Likes Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("likes", setting_value)

    def notification_like_and_comment_on_photo_user_tagged(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Like And Comment On Photo User Tagged Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("like_and_comment_on_photo_user_tagged", setting_value)

    def notification_user_tagged(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage User Tagged NotificationSettings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("user_tagged", setting_value)

    def notification_comments(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Comments Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("comments", setting_value)

    def notification_comment_likes(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Comment Likes Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("comment_likes", setting_value)

    def notification_first_post(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage First Post Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("first_post", setting_value)

    def notification_new_follower(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage New Follower Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("new_follower", setting_value)

    def notification_follow_request_accepted(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Follow Request Accepted Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("follow_request_accepted", setting_value)

    def notification_connection(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Connection Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("connection_notification", setting_value)

    def notification_tagged_in_bio(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Tagged In Bio Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("tagged_in_bio", setting_value)

    def notification_pending_direct_share(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Pending Direct Share Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("pending_direct_share", setting_value)

    def notification_direct_share_activity(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Direct Share Activity Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("direct_share_activity", setting_value)

    def notification_direct_group_requests(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Direct Group Requests Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("direct_group_requests", setting_value)

    def notification_video_call(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Video Call Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("video_call", setting_value)

    def notification_rooms(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Rooms Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("rooms", setting_value)

    def notification_live_broadcast(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Live Broadcast Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("live_broadcast", setting_value)

    def notification_felix_upload_result(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Felix Upload Result Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("felix_upload_result", setting_value)

    def notification_view_count(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage View Count Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("view_count", setting_value)

    def notification_fundraiser_creator(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Fundraiser Creator Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("fundraiser_creator", setting_value)

    def notification_fundraiser_supporter(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Fundraiser Supporter Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("fundraiser_supporter", setting_value)

    def notification_reminders(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Notification Reminders Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("notification_reminders", setting_value)

    def notification_announcements(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Announcements Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("announcements", setting_value)

    def notification_report_updated(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Report Updated Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("report_updated", setting_value)

    def notification_login(self, setting_value: SETTING_VALUE = "off") -> bool:
        """
        Manage Login Notification Settings

        Parameters
        ----------
        setting_value: SETTING_VALUE
            Value of settings, default "off"

        Returns
        -------
        bool
        """
        assert setting_value in SETTING_VALUE_ITEMS, \
            f'Unsupported setting_value="{setting_value}" {SETTING_VALUE_ITEMS}'
        return self.notification_settings("login_notification", setting_value)
