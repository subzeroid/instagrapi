# Location

| Method                                                     | Return         | Description
| ---------------------------------------------------------- | -------------- | -----------------------------------------------------------------------
| location_search(lat: float, lng: float)                    | List[Location] | Search Location by GEO coordinates
| location_complete(location: Location)                      | Location       | Complete blank fields
| location_build(location: Location)                         | String         | Serialized JSON
| location_info(location_pk: int)                            | Location       | Return Location info (pk, name, address, lng, lat, external_id, external_id_source)
| location_medias_top(location_pk: int, amount: int = 9)     | List[Media]    | Return Top posts by Location
| location_medias_recent(location_pk: int, amount: int = 24) | List[Media]    | Return Most recent posts by Location