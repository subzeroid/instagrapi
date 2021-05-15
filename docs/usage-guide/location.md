# Location

Viewing and manage location (place)

| Method                                                     | Return         | Description
| ---------------------------------------------------------- | -------------- | ----------------------------------------------------
| location_search(lat: float, lng: float)                    | List[Location] | Search Location by GEO coordinates
| location_complete(location: Location)                      | Location       | Complete blank fields
| location_build(location: Location)                         | String         | Serialized JSON
| location_info(location_pk: int)                            | Location       | Return Location info (pk, name, address, lng, lat, external_id, external_id_source)
| location_medias_top(location_pk: int, amount: int = 9)     | List[Media]    | Return Top posts by Location
| location_medias_recent(location_pk: int, amount: int = 24) | List[Media]    | Return Most recent posts by Location


Example:

``` python
>>> from instagrapi import Client

>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> location = cl.location_search(59.96, 30.29)[0]
>>> location.dict()
{'pk': None,
 'name': 'Russia, Saint-Petersburg',
 'address': 'Russia, Saint-Petersburg',
 'lng': 30.30605,
 'lat': 59.93318,
 'external_id': 107617247320879,
 'external_id_source': 'facebook_places'}

>>> location = cl.location_complete(location)
>>> location.dict()
{'pk': 107617247320879,
 'name': 'Russia, Saint-Petersburg',
 'address': 'Russia, Saint-Petersburg',
 'lng': 30.30605,
 'lat': 59.93318,
 'external_id': 107617247320879,
 'external_id_source': 'facebook_places'}

>>> cl.location_build(location)
'{"name":"Russia, Saint-Petersburg","address":"Russia, Saint-Petersburg","lat":59.93318,"lng":30.30605,"external_source":"facebook_places","facebook_places_id":107617247320879}'

>>> location = cl.location_info(107617247320879)
>>> location.dict()
{'pk': 107617247320879,
 'name': 'Russia, Saint-Petersburg',
 'address': '',
 'lng': 30.30605,
 'lat': 59.93318,
 'external_id': None,
 'external_id_source': None}

>>> medias = cl.location_medias_top(107617247320879, amount=2)
>>> medias[0].dict()
{'pk': 2574095228556148891,
 'id': '2574095228556148891_8227888596',
 'code': 'CO5BfjkHgCb',
 'taken_at': datetime.datetime(2021, 5, 15, 11, 6, 25, tzinfo=datetime.timezone.utc),
 'media_type': 2,
 'product_type': 'feed',
 'thumbnail_url': HttpUrl('https://instagram.fhel3-1.fna.fbcdn.net/v/t51.2885-15/e35/185874360_510656656615872_846247842213042525_n.jpg?tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=1&_nc_ohc=vUIk3PZPPrMAX_GGZ7n&edm=AP_V10EBAAAA&ccb=7-4&oh=e418e018b9fc07b7d6b78f0790ddb481&oe=60A24C1F&_nc_sid=4f375e', scheme='https', host='instagram.fhel3-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/185874360_510656656615872_846247842213042525_n.jpg', query='tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=1&_nc_ohc=vUIk3PZPPrMAX_GGZ7n&edm=AP_V10EBAAAA&ccb=7-4&oh=e418e018b9fc07b7d6b78f0790ddb481&oe=60A24C1F&_nc_sid=4f375e'),
 'location': {'pk': 107617247320879,
  'name': 'Russia, Saint-Petersburg',
  'address': '',
  'lng': 30.30605,
  'lat': 59.93318,
  'external_id': 107617247320879,
  'external_id_source': 'facebook_places'},
 'user': {'pk': 8227888596,
  'username': 'mzefirov',
  'full_name': 'МИХАИЛ ЗЕФИРОВ🌶️🔥ПРО ОТНОШЕНИЯ',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/54513886_664942437287042_6311410572676038656_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=mOWHIYJXbMsAX8wXvzf&edm=AP_V10EBAAAA&ccb=7-4&oh=90fa78d26bbb2c577dbc27d012c7cf09&oe=60C6A82B&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/54513886_664942437287042_6311410572676038656_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=mOWHIYJXbMsAX8wXvzf&edm=AP_V10EBAAAA&ccb=7-4&oh=90fa78d26bbb2c577dbc27d012c7cf09&oe=60C6A82B&_nc_sid=4f375e'),
  'stories': []},
 'comment_count': 94,
 'like_count': 3995,
 'has_liked': None,
 'caption_text': 'Антонина Роббинс, или немного о мотивации.\n\nСтавь ❤️и делись в сторис... это мотивирует.',
 'usertags': [],
 'video_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t50.2886-16/185466467_1373704339669543_4721533329541547409_n.mp4?_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_cat=107&_nc_ohc=IdbMAqYCjngAX987nBb&edm=AP_V10EBAAAA&ccb=7-4&oe=60A1DADD&oh=7c69dc13e5344f7095a94eb717b1ee9e&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t50.2886-16/185466467_1373704339669543_4721533329541547409_n.mp4', query='_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_cat=107&_nc_ohc=IdbMAqYCjngAX987nBb&edm=AP_V10EBAAAA&ccb=7-4&oe=60A1DADD&oh=7c69dc13e5344f7095a94eb717b1ee9e&_nc_sid=4f375e'),
 'view_count': 36295,
 'video_duration': 55.433,
 'title': '',
 'resources': []}

>>> medias = cl.location_medias_recent(107617247320879, amount=2)
>>> medias[0].dict()
{'pk': 2574187014843321420,
 'id': '2574187014843321420_5600296444',
 'code': 'CO5WXONKMxM',
 'taken_at': datetime.datetime(2021, 5, 15, 13, 57, 6, tzinfo=datetime.timezone.utc),
 'media_type': 1,
 'product_type': '',
 'thumbnail_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-15/e35/p1080x1080/186279877_479327446453989_5642409805215171470_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_cat=109&_nc_ohc=Nx9KwOGWXLYAX_bh1Dx&edm=AP_V10EBAAAA&ccb=7-4&oh=999395b5e4a3c688bcb388616f405161&oe=60C4C08C&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-15/e35/p1080x1080/186279877_479327446453989_5642409805215171470_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_cat=109&_nc_ohc=Nx9KwOGWXLYAX_bh1Dx&edm=AP_V10EBAAAA&ccb=7-4&oh=999395b5e4a3c688bcb388616f405161&oe=60C4C08C&_nc_sid=4f375e'),
 'location': {'pk': 107617247320879,
  'name': 'Russia, Saint-Petersburg',
  'address': '',
  'lng': 30.30605,
  'lat': 59.93318,
  'external_id': 107617247320879,
  'external_id_source': 'facebook_places'},
 'user': {'pk': 5600296444,
  'username': 'sultanieriabinina',
  'full_name': 'Султание Беляловна',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/92693550_492095081670507_2163230119093600256_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=_8hEZtz-JSIAX_NCxXx&edm=AP_V10EBAAAA&ccb=7-4&oh=17d2d1a8ae00765b8471cde868937c13&oe=60C69D73&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/92693550_492095081670507_2163230119093600256_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=_8hEZtz-JSIAX_NCxXx&edm=AP_V10EBAAAA&ccb=7-4&oh=17d2d1a8ae00765b8471cde868937c13&oe=60C69D73&_nc_sid=4f375e'),
  'stories': []},
 'comment_count': 0,
 'like_count': 0,
 'has_liked': None,
 'caption_text': '',
 'usertags': [{'user': {'pk': 3955327494,
    'username': '_parikmakher_irishka3127',
    'full_name': 'ИрИнА',
    'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/176040256_461659781826794_5379061705031591554_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=uVHqkpa8v0UAX-cmGUE&edm=AP_V10EBAAAA&ccb=7-4&oh=22db3640b911117484d78422eec4f778&oe=60C523D5&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/176040256_461659781826794_5379061705031591554_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=uVHqkpa8v0UAX-cmGUE&edm=AP_V10EBAAAA&ccb=7-4&oh=22db3640b911117484d78422eec4f778&oe=60C523D5&_nc_sid=4f375e'),
    'stories': []},
   'x': 0.352,
   'y': 0.292}],
 'video_url': None,
 'view_count': 0,
 'video_duration': 0.0,
 'title': '',
 'resources': []}
```
