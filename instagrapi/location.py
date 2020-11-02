import json

from .extractors import extract_location


class Location:

    def location_search(self, lat, lng):
        """Search location
        :return: dict Example: {"name":"NAME",
                                "external_id":234123489885123,
                                "external_id_source":"facebook_places",
                                "lat":42.0,
                                "lng":42.0,
                                "address":"ADDRESS",
                                "minimum_age":0}
        """
        params = {
            'latitude': lat,
            'longitude': lng,
            # rankToken=c544eea5-736b-4091-a916-a71a35a86474 - self.uuid?
            # fb_access_token=EAABwzLixnjYBABK2YBFkT...pKrjju4cijEGYtcbIyCSJ0j4ZD
        }
        result = self.private_request("location_search/", params=params)
        return result['venues']

    def location_build(self, location):
        """Build correct location data
        """
        if not location:
            return '{}'
        assert 'lat' in location and 'lng' in location, f'lat and lng must been in location (now {location})'
        external_id = location.get('facebook_places_id', location.get('external_id'))
        if not external_id:
            try:
                location = self.location_search(location['lat'], location['lng'])[0]
                location = {
                    "name": location['name'],
                    "address": location['address'],
                    "lat": location['lat'],
                    "lng": location['lng'],
                    "external_source": location.get('external_source', location.get('external_id_source', 'facebook_places')),
                    "facebook_places_id": location.get('facebook_places_id', location.get('external_id')),
                }
            except IndexError:
                pass
        return json.dumps(location, separators=(",", ":"))

    def location_info_a1(self, location_pk: int) -> dict:
        """Return additonal info for location by ?__a=1
        """
        data = self.public_a1_request(f"/explore/locations/{location_pk}/")
        return extract_location(data['location'])

    def location_info(self, location_pk: int) -> dict:
        """Return additonal info for location
        """
        return self.location_info_a1(location_pk)
