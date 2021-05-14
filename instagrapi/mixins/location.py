import json
import time
from typing import List

from instagrapi.exceptions import (
    ClientLoginRequired,
    ClientNotFoundError,
    LocationNotFound,
)
from instagrapi.extractors import extract_location
from instagrapi.types import Location, Media


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
        return self.location_info_a1(location_pk)

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
                if amount and len(medias) >= amount:
                    break
                node = edge["node"]
                medias.append(self.media_info_gql(node["id"]))
                # time.sleep(sleep)
            if not page_info["has_next_page"] or not end_cursor:
                break
            if amount and len(medias) >= amount:
                break
            time.sleep(sleep)
        uniq_pks = set()
        medias = [m for m in medias if not (m.pk in uniq_pks or uniq_pks.add(m.pk))]
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

    def location_medias_top(
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
        try:
            return self.location_medias_top_a1(location_pk, amount, sleep)
        except ClientLoginRequired as e:
            if not self.inject_sessionid_to_public():
                raise e
            return self.location_medias_top_a1(location_pk, amount, sleep)  # retry

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

    def location_medias_recent(
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
        try:
            return self.location_medias_recent_a1(location_pk, amount, sleep)
        except ClientLoginRequired as e:
            if not self.inject_sessionid_to_public():
                raise e
            return self.location_medias_recent_a1(location_pk, amount, sleep)  # retry
