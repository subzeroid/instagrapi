from instagrapi.extractors import extract_location


class FbSearchMixin:

    def fbsearch_places(self, query: str, lat: float = 40.74, lng: float = -73.94):
        params = {
            'search_surface': 'places_search_page',
            'timezone_offset': self.timezone_offset,
            'lat': lat,
            'lng': lng,
            'count': 30,
            'query': query,
        }
        result = self.private_request("fbsearch/places/", params=params)
        locations = []
        for item in result['items']:
            locations.append(extract_location(item['location']))
        return locations
