import json
import time
from typing import List, Tuple

from instagrapi.exceptions import ClientNotFoundError, LocationNotFound
from instagrapi.extractors import extract_location, extract_media_v1
from instagrapi.types import Location, Media

tab_keys_a1 = ('edge_location_to_top_posts', 'edge_location_to_media')
tab_keys_v1 = ('ranked', 'recent')


class LocationMixin:
    """
    Helper class to get location
    """

    def location_search(self, lat: float, lng: float) -> List[Location]:
        """
        Get locations using lat and long

        Parameters
        ----------
        lat: float
            Latitude you want to search for
        lng: float
            Longitude you want to search for

        Returns
        -------
        List[Location]
            List of objects of Location
        """
        params = {
            "latitude": lat,
            "longitude": lng,
            # rankToken=c544eea5-726b-4091-a916-a71a35a76474 - self.uuid?
            # fb_access_token=EAABwzLixnjYBABK2YBFkT...pKrjju4cijEGYtcbIyCSJ0j4ZD
        }
        result = self.private_request("location_search/", params=params)
        locations = []
        for venue in result["venues"]:
            if "lat" not in venue:
                venue["lat"] = lat
                venue["lng"] = lng
            locations.append(extract_location(venue))
        return locations

    def location_complete(self, location: Location) -> Location:
        """
        Smart complete of location

        Parameters
        ----------
        location: Location
            An object of location

        Returns
        -------
        Location
            An object of Location
        """
        assert location and isinstance(
            location, Location
        ), f'Location is wrong "{location}" ({type(location)})'
        if location.pk and not location.lat:
            # search lat and lng
            info = self.location_info(location.pk)
            location.lat = info.lat
            location.lng = info.lng
        if not location.external_id and location.lat:
            # search extrernal_id and external_id_source
            try:
                venue = self.location_search(location.lat, location.lng)[0]
                location.external_id = venue.external_id
                location.external_id_source = venue.external_id_source
            except IndexError:
                pass
        if not location.pk and location.external_id:
            info = self.location_info(location.external_id)
            if info.name == location.name or (
                info.lat == location.lat and info.lng == location.lng
            ):
                location.pk = location.external_id
        return location

    def location_build(self, location: Location) -> str:
        """
        Build correct location data

        Parameters
        ----------
        location: Location
            An object of location

        Returns
        -------
        str
        """
        if not location:
            return "{}"
        if not location.external_id and location.lat:
            try:
                location = self.location_search(location.lat, location.lng)[0]
            except IndexError:
                pass
        data = {
            "name": location.name,
            "address": location.address,
            "lat": location.lat,
            "lng": location.lng,
            "external_source": location.external_id_source,
            "facebook_places_id": location.external_id,
        }
        return json.dumps(data, separators=(",", ":"))

    def location_info_a1(self, location_pk: int) -> Location:
        """
        Get a location using location pk

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location

        Returns
        -------
        Location
            An object of Location
        """
        try:
            data = self.public_a1_request(f"/explore/locations/{location_pk}/") or {}
            if not data.get("location"):
                raise LocationNotFound(location_pk=location_pk, **data)
            return extract_location(data["location"])
        except ClientNotFoundError:
            raise LocationNotFound(location_pk=location_pk)

    def location_info_v1(self, location_pk: int) -> Location:
        """
        Get a location using location pk

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location

        Returns
        -------
        Location
            An object of Location
        """
        result = self.private_request(f"locations/{location_pk}/location_info/")
        return extract_location(result)

    def location_info(self, location_pk: int) -> Location:
        """
        Get a location using location pk

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location

        Returns
        -------
        Location
            An object of Location
        """
        try:
            location = self.location_info_a1(location_pk)
        except Exception:
            # Users do not understand the output of such information and create bug reports
            # such this - https://github.com/adw0rd/instagrapi/issues/364
            # if not isinstance(e, ClientError):
            #     self.logger.exception(e)
            location = self.location_info_v1(location_pk)
        return location

    def location_medias_a1_chunk(
        self, location_pk: int, max_amount: int = 24, sleep: float = 0.5, tab_key: str = "", max_id: str = None
    ) -> Tuple[List[Media], str]:
        """
        Get chunk of medias and end_cursor by Public Web API

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        max_amount: int, optional
            Maximum number of media to return, default is 24
        sleep: float, optional
            Timeout between requests, default is 0.5
        tab_key: str, optional
            Tab Key, default value is ""
        end_cursor: str, optional
            End Cursor, default value is None

        Returns
        -------
        Tuple[List[Media], str]
            List of objects of Media and end_cursor
        """
        assert tab_key in tab_keys_a1, f'You must specify one of the options for "tab_key" {tab_keys_a1}'
        unique_set = set()
        medias = []
        end_cursor = None
        while True:
            data = self.public_a1_request(
                f"/explore/locations/{location_pk}/",
                params={"max_id": end_cursor} if end_cursor else {},
            )["location"]
            page_info = data["edge_location_to_media"]["page_info"]
            end_cursor = page_info["end_cursor"]
            edges = data[tab_key]["edges"]
            for edge in edges:
                if max_amount and len(medias) >= max_amount:
                    break
                node = edge["node"]
                # check uniq
                media_pk = node["id"]
                if media_pk in unique_set:
                    continue
                unique_set.add(media_pk)
                # Enrich media: Full user, usertags and video_url
                medias.append(self.media_info_gql(media_pk))
            if not page_info["has_next_page"] or not end_cursor:
                break
            if max_amount and len(medias) >= max_amount:
                break
            time.sleep(sleep)
        return medias, end_cursor

    def location_medias_a1(
        self, location_pk: int, amount: int = 24, sleep: float = 0.5, tab_key: str = ""
    ) -> List[Media]:
        """
        Get medias for a location

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 24
        sleep: float, optional
            Timeout between requests, default is 0.5
        tab_key: str, optional
            Tab Key, default value is ""

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        assert tab_key in tab_keys_a1, f'You must specify one of the options for "tab_key" {tab_keys_a1}'
        medias, _ = self.location_medias_a1_chunk(location_pk, amount, sleep, tab_key)
        if amount:
            medias = medias[:amount]
        return medias

    def location_medias_v1_chunk(
        self, location_pk: int, max_amount: int = 63, tab_key: str = "", max_id: str = None
    ) -> Tuple[List[Media], str]:
        """
        Get chunk of medias for a location and max_id (cursor) by Private Mobile API

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        max_amount: int, optional
            Maximum number of media to return, default is 27
        tab_key: str, optional
            Tab Key, default value is ""
        max_id: str
            Max ID, default value is None

        Returns
        -------
        Tuple[List[Media], str]
            List of objects of Media and max_id
        """
        assert tab_key in tab_keys_v1, f'You must specify one of the options for "tab_key" {tab_keys_a1}'
        data = {
            "_uuid": self.uuid,
            "session_id": self.client_session_id,
            "tab": tab_key
        }
        medias = []
        while True:
            result = self.private_request(
                f"locations/{location_pk}/sections/",
                params={"max_id": max_id} if max_id else {},
                data=data,
            )
            for section in result["sections"]:
                layout_content = section.get("layout_content") or {}
                nodes = layout_content.get("medias") or []
                for node in nodes:
                    if max_amount and len(medias) >= max_amount:
                        break
                    media = extract_media_v1(node["media"])
                    medias.append(media)
            if not result["more_available"]:
                break
            if max_amount and len(medias) >= max_amount:
                break
            max_id = result["next_max_id"]
        return medias, max_id

    def location_medias_v1(
        self, location_pk: int, amount: int = 63, tab_key: str = ""
    ) -> List[Media]:
        """
        Get medias for a location by Private Mobile API

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 63
        tab_key: str, optional
            Tab Key, default value is ""

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        assert tab_key in tab_keys_v1, f'You must specify one of the options for "tab_key" {tab_keys_a1}'
        medias, _ = self.location_medias_v1_chunk(location_pk, amount, tab_key)
        if amount:
            medias = medias[:amount]
        return medias

    def location_medias_top_a1(
        self, location_pk: int, amount: int = 9, sleep: float = 0.5
    ) -> List[Media]:
        """
        Get top medias for a location

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 9
        sleep: float, optional
            Timeout between requests, default is 0.5

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        return self.location_medias_a1(
            location_pk, amount, sleep=sleep, tab_key="edge_location_to_top_posts"
        )

    def location_medias_top_v1(
        self, location_pk: int, amount: int = 21
    ) -> List[Media]:
        """
        Get top medias for a location

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 21

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        return self.location_medias_v1(location_pk, amount, tab_key="ranked")

    def location_medias_top(
        self, location_pk: int, amount: int = 27, sleep: float = 0.5
    ) -> List[Media]:
        """
        Get top medias for a location

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 27
        sleep: float, optional
            Timeout between requests, default is 0.5

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        try:
            return self.location_medias_top_a1(location_pk, amount, sleep)
        except Exception:
            # Users do not understand the output of such information and create bug reports
            # such this - https://github.com/adw0rd/instagrapi/issues/364
            # if not isinstance(e, ClientError):
            #     self.logger.exception(e)
            return self.location_medias_top_v1(location_pk, amount)

    def location_medias_recent_a1(
        self, location_pk: int, amount: int = 24, sleep: float = 0.5
    ) -> List[Media]:
        """
        Get recent medias for a location

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 24
        sleep: float, optional
            Timeout between requests, default is 0.5

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        return self.location_medias_a1(
            location_pk, amount, sleep=sleep, tab_key="edge_location_to_media"
        )

    def location_medias_recent_v1(
        self, location_pk: int, amount: int = 63
    ) -> List[Media]:
        """
        Get recent medias for a location

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 63

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        return self.location_medias_v1(location_pk, amount, tab_key="recent")

    def location_medias_recent(
        self, location_pk: int, amount: int = 63, sleep: float = 0.5
    ) -> List[Media]:
        """
        Get recent medias for a location

        Parameters
        ----------
        location_pk: int
            Unique identifier for a location
        amount: int, optional
            Maximum number of media to return, default is 63
        sleep: float, optional
            Timeout between requests, default is 0.5

        Returns
        -------
        List[Media]
            List of objects of Media
        """
        try:
            return self.location_medias_recent_a1(location_pk, amount, sleep)
        except Exception:
            # Users do not understand the output of such information and create bug reports
            # such this - https://github.com/adw0rd/instagrapi/issues/364
            # if not isinstance(e, ClientError):
            #     self.logger.exception(e)
            return self.location_medias_recent_v1(location_pk, amount)
