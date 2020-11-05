import json
from typing import List

from .extractors import extract_location
from .types import Location


class LocationMixin:

    def location_search(self, lat: float, lng: float) -> List[Location]:
        """Search location
        """
        params = {
            'latitude': lat,
            'longitude': lng,
            # rankToken=c544eea5-726b-4091-a916-a71a35a76474 - self.uuid?
            # fb_access_token=EAABwzLixnjYBABK2YBFkT...pKrjju4cijEGYtcbIyCSJ0j4ZD
        }
        result = self.private_request("location_search/", params=params)
        locations = []
        for venue in result['venues']:
            if 'lat' not in venue:
                venue['lat'] = lat
                venue['lng'] = lng
            locations.append(extract_location(venue))
        return locations

    def location_complete(self, data: dict) -> dict:
        """Smart complete of location
        """
        if data and not data.get('lat') and data.get('id'):
            loc = self.location_info(data['id'])
            if not loc.external_id:
                try:
                    venue = self.location_search(loc.lat, loc.lng)[0]
                    loc.external_id = venue.external_id
                    loc.external_id_source = venue.external_id_source
                except IndexError:
                    pass
            data = loc.dict()
        return data

    def location_build(self, location: Location) -> str:
        """Build correct location data
        """
        if not location:
            return '{}'
        assert location.lat and location.lng, f'Error! lat and lng must been in location (now {location})'
        if not location.external_id:
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
            "facebook_places_id": location.external_id
        }
        return json.dumps(data, separators=(",", ":"))

    def location_info_a1(self, location_pk: int) -> Location:
        """Return additonal info for location by ?__a=1
        """
        data = self.public_a1_request(f"/explore/locations/{location_pk}/")
        return extract_location(data['location'])

    def location_info(self, location_pk: int) -> Location:
        """Return additonal info for location
        """
        return self.location_info_a1(location_pk)
