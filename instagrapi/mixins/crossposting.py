import json
from typing import Dict, Iterable, List, Literal, Optional
from uuid import uuid4

from instagrapi.exceptions import ClientError

FB_CROSSPOSTING_UNIFIED_CONFIG_CLIENT_DOC_ID = "216179630714134719310007237117"
FB_CROSSPOSTING_UNIFIED_CONFIG_FRIENDLY_NAME = "CrosspostingUnifiedConfigsQuery"
FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD = "xcxp_unified_crossposting_configs_root"
FB_STORY_CROSSPOSTING_SURFACE = {
    "source_surface": "STORY",
    "destination_app": "FB",
    "destination_surface": "STORY",
}
FB_FEED_CROSSPOSTING_SURFACE = {
    "source_surface": "FEED",
    "destination_app": "FB",
    "destination_surface": "FEED",
}
FB_REELS_CROSSPOSTING_SURFACE = {
    "source_surface": "REELS",
    "destination_app": "FB",
    "destination_surface": "REELS",
}
FB_CROSSPOSTING_SURFACES = [
    FB_STORY_CROSSPOSTING_SURFACE,
    FB_FEED_CROSSPOSTING_SURFACE,
    FB_REELS_CROSSPOSTING_SURFACE,
]

THREADS_LINKED_PROFILE_CLIENT_DOC_ID = "1294688273527445410149299611"
THREADS_LINKED_PROFILE_FRIENDLY_NAME = "LinkedBarcelonaProfileQuery"
THREADS_LINKED_PROFILE_ROOT_FIELD = "xcxp_fetch_linked_threads_profile"

FbDestinationType = Literal["USER", "PAGE"]


class CrossPostingMixin:
    """Helpers shared by feed and Reel cross-post upload flows."""

    def media_share_to_fb_unified_config(
        self,
        crosspost_app_surface_list: Optional[List[Dict[str, str]]] = None,
    ) -> Dict:
        """
        Get Android's unified cross-posting configuration.

        Parameters
        ----------
        crosspost_app_surface_list: List[Dict[str, str]], optional
            Source/destination surfaces to request. Defaults to Story, Feed,
            and Reels destinations.

        Returns
        -------
        Dict
            Private GraphQL response.
        """
        variables = {
            "configs_request": {
                "source_app": "IG",
                "crosspost_app_surface_list": crosspost_app_surface_list or FB_CROSSPOSTING_SURFACES,
            }
        }
        return self.private_graphql_query_request(
            friendly_name=FB_CROSSPOSTING_UNIFIED_CONFIG_FRIENDLY_NAME,
            root_field_name=FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD,
            variables=variables,
            client_doc_id=FB_CROSSPOSTING_UNIFIED_CONFIG_CLIENT_DOC_ID,
            priority="u=3, i",
            extra_headers={"X-FB-RMD": "state=URL_ELIGIBLE"},
        )

    @staticmethod
    def _crossposting_iter_dicts(value) -> Iterable[Dict[str, object]]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from CrossPostingMixin._crossposting_iter_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from CrossPostingMixin._crossposting_iter_dicts(child)

    @staticmethod
    def _crossposting_candidate_value(config: Dict[str, object], keys) -> object:
        for key in keys:
            value = config.get(key)
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _crossposting_graphql_root(config: Dict[str, object], root_field: str) -> object:
        data = (config or {}).get("data")
        if isinstance(data, dict):
            root = data.get(root_field)
            if root is not None:
                return root
            for key, value in data.items():
                if root_field in str(key):
                    return value
        return config or {}

    @staticmethod
    def _media_share_to_fb_feed_candidate(config: Dict[str, object]) -> bool:
        source_surface = str(config.get("source_surface") or "").upper()
        destination_surface = str(config.get("destination_surface") or "").upper()
        destination_app = str(config.get("destination_app") or "").upper()
        if source_surface and source_surface != "FEED":
            return False
        if destination_surface and destination_surface != "FEED":
            return False
        if destination_app and destination_app not in {"FB", "FACEBOOK"}:
            return False
        return source_surface == "FEED" or destination_surface == "FEED"

    def _media_share_to_fb_unified_destination_candidates(
        self,
        config: Dict[str, object],
    ) -> Iterable[Dict[str, object]]:
        root = self._crossposting_graphql_root(config, FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD)
        for service in self._crossposting_iter_dicts(root):
            identity_mappings = service.get("identity_mapping")
            if not isinstance(identity_mappings, list):
                continue
            custom_service_data = service.get("custom_service_data")
            surface_config = custom_service_data if isinstance(custom_service_data, dict) else service
            if not any(
                self._media_share_to_fb_feed_candidate(candidate)
                for candidate in self._crossposting_iter_dicts(surface_config)
            ):
                continue
            for identity_mapping in identity_mappings:
                if not isinstance(identity_mapping, dict):
                    continue
                destination_identities = identity_mapping.get("destination_identities")
                if not isinstance(destination_identities, list):
                    continue
                for destination in destination_identities:
                    if isinstance(destination, dict):
                        yield {
                            "source_surface": "FEED",
                            "destination_app": "FB",
                            "destination_surface": "FEED",
                            **destination,
                        }

        for candidate in self._crossposting_iter_dicts(root):
            if not self._media_share_to_fb_feed_candidate(candidate):
                continue
            merged = dict(candidate)
            for key in (
                "destination",
                "fb_destination",
                "feed_destination",
                "crosspost_destination",
                "crossposting_destination",
                "xpost_destination",
            ):
                nested = candidate.get(key)
                if isinstance(nested, dict):
                    merged.update(nested)
            yield merged

    def _media_share_to_fb_unified_config_variants(self):
        yield self.media_share_to_fb_unified_config()
        yield self.media_share_to_fb_unified_config(crosspost_app_surface_list=[FB_FEED_CROSSPOSTING_SURFACE])

    def media_share_to_fb_unified_destination(
        self,
        config: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        """
        Resolve a confirmed Facebook Feed destination from unified config.

        Parameters
        ----------
        config: Dict[str, object], optional
            Response from :meth:`media_share_to_fb_unified_config`.

        Returns
        -------
        Dict[str, object]
            Normalized destination fields.
        """
        configs = (config,) if config is not None else self._media_share_to_fb_unified_config_variants()
        for unified_config in configs:
            for candidate in self._media_share_to_fb_unified_destination_candidates(unified_config or {}):
                try:
                    return self.media_share_to_fb_destination(
                        config=candidate,
                        use_unified_config=False,
                    )
                except ClientError:
                    continue
        raise ClientError("Facebook Feed sharing unified config has no confirmed Facebook destination")

    @staticmethod
    def _crossposting_validation_bypass(value) -> Optional[List[str]]:
        if value in (None, "", []):
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                value = [value]
        if isinstance(value, (tuple, set)):
            value = list(value)
        if not isinstance(value, list):
            value = [value]
        return [str(item) for item in value]

    def media_share_to_fb_destination(
        self,
        config: Optional[Dict[str, object]] = None,
        destination_id: Optional[str] = None,
        destination_type: Optional[FbDestinationType] = None,
        validation_bypass: Optional[List[str]] = None,
        use_unified_config: bool = True,
    ) -> Dict[str, object]:
        """
        Resolve the Facebook destination used by Feed configure requests.

        Parameters
        ----------
        config: Dict[str, object], optional
            Unified config response or a confirmed destination dictionary.
        destination_id: str, optional
            Explicit Facebook destination id.
        destination_type: Literal["USER", "PAGE"], optional
            Explicit Facebook destination type.
        validation_bypass: List[str], optional
            Android validation bypass reasons.
        use_unified_config: bool, optional
            Discover a Feed destination when no explicit config is supplied.

        Returns
        -------
        Dict[str, object]
            Normalized destination fields.
        """
        has_unified_root = bool(
            config
            and (
                isinstance(config.get("data"), dict)
                or any(FB_CROSSPOSTING_UNIFIED_CONFIG_ROOT_FIELD in str(key) for key in config)
            )
        )
        if config is not None and has_unified_root:
            candidates = list(self._media_share_to_fb_unified_destination_candidates(config))
            if candidates:
                for candidate in candidates:
                    try:
                        return self.media_share_to_fb_destination(
                            config=candidate,
                            destination_id=destination_id,
                            destination_type=destination_type,
                            validation_bypass=validation_bypass,
                            use_unified_config=False,
                        )
                    except ClientError:
                        continue

        fb_config = config or {}
        explicit_destination = bool(destination_id or destination_type)
        if not fb_config and not explicit_destination and use_unified_config:
            return self.media_share_to_fb_unified_destination()
        if fb_config.get("enabled") is False or fb_config.get("is_account_linked") is False:
            raise ClientError("Facebook Feed sharing is not enabled or no Facebook account is linked")

        destination_id = destination_id or self._crossposting_candidate_value(
            fb_config,
            (
                "share_to_fb_destination_id",
                "obfuscated_identity_id",
                "feed_destination_id",
                "crosspost_destination_id",
                "crossposting_destination_id",
                "xpost_destination_id",
                "destination_id",
            ),
        )
        destination_type_value = destination_type or self._crossposting_candidate_value(
            fb_config,
            (
                "share_to_fb_destination_type",
                "identity_type",
                "crosspost_destination_type",
                "crossposting_destination_type",
                "xpost_destination_type",
                "destination_type",
                "posting_type",
            ),
        )
        destination_type_text = str(destination_type_value).upper() if destination_type_value is not None else ""
        if destination_type_text.startswith("FB_"):
            destination_type_text = destination_type_text[3:]

        if validation_bypass is None:
            validation_bypass = self._crossposting_candidate_value(
                fb_config,
                (
                    "share_to_facebook_validation_bypass",
                    "validation_bypass",
                ),
            )
        validation_bypass = self._crossposting_validation_bypass(validation_bypass)

        if not destination_id:
            raise ClientError(
                "Facebook Feed sharing configuration has no destination. "
                "Link a Facebook account/page in the Instagram app or pass destination_id."
            )
        if not destination_type_text:
            raise ClientError(
                "Facebook Feed sharing configuration has no destination type. Pass destination_type as USER or PAGE."
            )
        if destination_type_text not in {"USER", "PAGE"}:
            raise ClientError("Facebook Feed sharing destination type must be USER or PAGE")

        destination = {
            "destination_id": str(destination_id),
            "destination_type": destination_type_text,
        }
        if validation_bypass:
            destination["validation_bypass"] = validation_bypass
        return destination

    def media_share_to_fb_extra_data(
        self,
        config: Optional[Dict[str, object]] = None,
        destination_id: Optional[str] = None,
        destination_type: Optional[FbDestinationType] = None,
        validation_bypass: Optional[List[str]] = None,
        attempt_id: Optional[str] = None,
    ) -> Dict[str, object]:
        """
        Build Feed configure fields for sharing to Facebook.

        Returns
        -------
        Dict[str, object]
            Extra configure data for feed upload methods.
        """
        destination = self.media_share_to_fb_destination(
            config=config,
            destination_id=destination_id,
            destination_type=destination_type,
            validation_bypass=validation_bypass,
        )
        data = {
            "share_to_facebook": "1",
            "share_to_fb_destination_id": destination["destination_id"],
            "share_to_fb_destination_type": destination["destination_type"],
            "no_token_crosspost": "1",  # nosec B105
            "attempt_id": attempt_id or str(uuid4()),
        }
        if destination.get("validation_bypass"):
            data["share_to_facebook_validation_bypass"] = destination["validation_bypass"]
        return data

    def media_share_to_threads_config(self) -> Dict:
        """
        Get the Threads profile linked to the current Instagram account.

        Returns
        -------
        Dict
            Private GraphQL response.
        """
        return self.private_graphql_query_request(
            friendly_name=THREADS_LINKED_PROFILE_FRIENDLY_NAME,
            root_field_name=THREADS_LINKED_PROFILE_ROOT_FIELD,
            variables={},
            client_doc_id=THREADS_LINKED_PROFILE_CLIENT_DOC_ID,
            priority="u=3, i",
            extra_headers={"X-FB-RMD": "state=URL_ELIGIBLE"},
        )

    def media_share_to_threads_destination(
        self,
        config: Optional[Dict[str, object]] = None,
        destination_id: Optional[str] = None,
    ) -> Dict[str, object]:
        """
        Resolve the linked Threads profile used by configure requests.

        Parameters
        ----------
        config: Dict[str, object], optional
            Response from :meth:`media_share_to_threads_config`.
        destination_id: str, optional
            Explicit Threads profile id.

        Returns
        -------
        Dict[str, object]
            Normalized Threads destination fields.
        """
        threads_config = config
        if threads_config is None and destination_id is None:
            threads_config = self.media_share_to_threads_config()
        profile = (
            self._crossposting_graphql_root(
                threads_config or {},
                THREADS_LINKED_PROFILE_ROOT_FIELD,
            )
            if threads_config is not None
            else {}
        )
        if not isinstance(profile, dict):
            profile = {}

        destination_id = destination_id or self._crossposting_candidate_value(
            profile,
            (
                "id",
                "strong_id__",
                "destination_id",
                "obfuscated_identity_id",
            ),
        )
        if not destination_id:
            raise ClientError(
                "Threads sharing configuration has no linked Threads profile. "
                "Link a Threads profile in the Instagram app or pass destination_id."
            )

        destination = {"destination_id": str(destination_id)}
        for key in ("username", "profile_pic_url"):
            if profile.get(key):
                destination[key] = str(profile[key])
        return destination

    def media_share_to_threads_extra_data(
        self,
        config: Optional[Dict[str, object]] = None,
        destination_id: Optional[str] = None,
        validation_bypass: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """
        Build configure fields for sharing media to Threads.

        Returns
        -------
        Dict[str, object]
            Extra configure data for feed or Reel upload methods.
        """
        destination = self.media_share_to_threads_destination(
            config=config,
            destination_id=destination_id,
        )
        data = {
            "share_to_threads": "1",
            "share_to_threads_destination_id": destination["destination_id"],
        }
        validation_bypass = self._crossposting_validation_bypass(validation_bypass)
        if validation_bypass:
            data["share_to_threads_validation_bypass"] = validation_bypass
        return data

    def _media_crossposting_extra_data(
        self,
        extra_data: Optional[Dict[str, object]] = None,
        *,
        share_to_facebook: bool = False,
        share_to_threads: bool = False,
        fb_destination_id: Optional[str] = None,
        fb_destination_type: Optional[FbDestinationType] = None,
        fb_validation_bypass: Optional[List[str]] = None,
        threads_destination_id: Optional[str] = None,
        threads_validation_bypass: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        generated = {}
        if share_to_facebook:
            generated.update(
                self.media_share_to_fb_extra_data(
                    destination_id=fb_destination_id,
                    destination_type=fb_destination_type,
                    validation_bypass=fb_validation_bypass,
                )
            )
        if share_to_threads:
            generated.update(
                self.media_share_to_threads_extra_data(
                    destination_id=threads_destination_id,
                    validation_bypass=threads_validation_bypass,
                )
            )
        return {**generated, **dict(extra_data or {})}
