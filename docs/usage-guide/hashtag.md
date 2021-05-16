# Hashtag

Viewing hashtag info and medias by hashtag

| Method                                             | Return              | Description
| -------------------------------------------------- | ------------------- | ---------------------------------------
| hashtag_info(name: str)                            | Hashtag             | Return Hashtag info (id, name, picture)
| hashtag_related_hashtags(name: str)                | List[Hashtag]       | Return list of related Hashtag
| hashtag_medias_top(name: str, amount: int = 9)     | List[Media]         | Return Top posts by Hashtag
| hashtag_medias_recent(name: str, amount: int = 27) | List[Media]         | Return Most recent posts by Hashtag


Example:

``` python
>>> from instagrapi import Client

>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> hashtag = cl.hashtag_info('downhill')
>>> hashtag.dict()
{'id': 17841563089103670,
 'name': 'downhill',
 'media_count': 5178255,
 'profile_pic_url': HttpUrl('https://instagram.fhel3-1.fna.fbcdn.net/v/t51.2885-15/e35/s150x150/184304495_294863488920457_8839934375675895594_n.jpg?tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=101&_nc_ohc=L3i9yzFUBR8AX_MAXgr&edm=ABZsPhsBAAAA&ccb=7-4&oh=21a944a197506a42658e8273d92740b7&oe=60C37E35&_nc_sid=4efc9f', scheme='https', host='instagram.fhel3-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/s150x150/184304495_294863488920457_8839934375675895594_n.jpg', query='tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=101&_nc_ohc=L3i9yzFUBR8AX_MAXgr&edm=ABZsPhsBAAAA&ccb=7-4&oh=21a944a197506a42658e8273d92740b7&oe=60C37E35&_nc_sid=4efc9f')}

>>> medias = cl.hashtag_medias_top('downhill', amount=2)
>>> medias[0].dict()
{'pk': 2574092718364154697,
 'id': '2574092718364154697_376712420',
 'code': 'CO5A7BxA9tJ',
 'taken_at': datetime.datetime(2021, 5, 15, 10, 49, 45, tzinfo=datetime.timezone.utc),
 'media_type': 1,
 'product_type': '',
 'thumbnail_url': HttpUrl('https://instagram.fhel3-1.fna.fbcdn.net/v/t51.2885-15/e35/s1080x1080/186430270_473573763896149_2030909827389015824_n.jpg?tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=101&_nc_ohc=4jFHY_INCnMAX-7fObK&edm=AP_V10EBAAAA&ccb=7-4&oh=9fb0c4cdb01a7aa376a96c0df366d844&oe=60C4C01A&_nc_sid=4f375e', scheme='https', host='instagram.fhel3-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/s1080x1080/186430270_473573763896149_2030909827389015824_n.jpg', query='tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=101&_nc_ohc=4jFHY_INCnMAX-7fObK&edm=AP_V10EBAAAA&ccb=7-4&oh=9fb0c4cdb01a7aa376a96c0df366d844&oe=60C4C01A&_nc_sid=4f375e'),
 'location': {'pk': 517543,
  'name': 'Sestola',
  'address': '',
  'lng': 10.77328,
  'lat': 44.2266,
  'external_id': 103150459725396,
  'external_id_source': 'facebook_places'},
 'user': {'pk': 376712420,
  'username': 'vascobica',
  'full_name': '⚡Vasco Bica®⚡',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/96211403_922669918147090_5138958292701151232_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=tYlGX8kDuSgAX9WtBRF&edm=AP_V10EBAAAA&ccb=7-4&oh=ac96c75846d17519e53923a0ddb3aad0&oe=60C51486&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/96211403_922669918147090_5138958292701151232_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=tYlGX8kDuSgAX9WtBRF&edm=AP_V10EBAAAA&ccb=7-4&oh=ac96c75846d17519e53923a0ddb3aad0&oe=60C51486&_nc_sid=4f375e'),
  'stories': []},
 'comment_count': 8,
 'like_count': 327,
 'has_liked': None,
 'caption_text': 'Ready to fight ⚔️\n#js7 \n.\n.\n#swissmountainsports #racing #coppaitaliadh \n#mirandabikeparts\xa0#burning\xa0#jumping \xa0#whipit\xa0#scrubit\xa0#enduro\xa0#mtblife\xa0 #downhill\xa0#mountainbiking\xa0#sliding\xa0#dirt\xa0#dh\xa0 #mtb\xa0#bike\xa0#bikelife\xa0#friends\xa0#mtbswitzerland\xa0#downhillmtb\xa0#valais\xa0 #swissmountains\xa0\xa0#italy #italydownhill',
 'usertags': [{'user': {'pk': 3636959873,
    'username': 'christopherstrm',
    'full_name': 'Christopher Ström',
    'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/173775865_527371595096868_8991176723035066304_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=tbsAzTDoLtEAX_HaT9Z&edm=AP_V10EBAAAA&ccb=7-4&oh=94a18b3b4d0d39d9dbda849b4c23a5a9&oe=60C5192F&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/173775865_527371595096868_8991176723035066304_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=tbsAzTDoLtEAX_HaT9Z&edm=AP_V10EBAAAA&ccb=7-4&oh=94a18b3b4d0d39d9dbda849b4c23a5a9&oe=60C5192F&_nc_sid=4f375e'),
    'stories': []},
   'x': 0.211352657,
   'y': 0.8478260870000001}],
 'video_url': None,
 'view_count': 0,
 'video_duration': 0.0,
 'title': '',
 'resources': []}

>>> medias = cl.hashtag_medias_recent('downhill', amount=2)
>>> medias[0].dict()
{'pk': 2574205305714324167,
 'id': '2574205305714324167_2984719638',
 'code': 'CO5ahY6BzLH',
 'taken_at': datetime.datetime(2021, 5, 15, 14, 33, 27, tzinfo=datetime.timezone.utc),
 'media_type': 8,
 'product_type': '',
 'thumbnail_url': None,
 'location': {'pk': 703017966745848,
  'name': 'Le Canyon Du Diable',
  'address': '',
  'lng': 3.4480762482,
  'lat': 43.6966105493,
  'external_id': 703017966745848,
  'external_id_source': 'facebook_places'},
 'user': {'pk': 2984719638,
  'username': 'lilian.champion',
  'full_name': 'Lilian 🇨🇵',
  'profile_pic_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-19/s150x150/169115203_291696755653751_6779914563403118432_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=VEqYwd5W1FYAX_7ID-6&edm=AP_V10EBAAAA&ccb=7-4&oh=7fe193da2e706c0cafd9e1d432734891&oe=60C59786&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-19/s150x150/169115203_291696755653751_6779914563403118432_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_ohc=VEqYwd5W1FYAX_7ID-6&edm=AP_V10EBAAAA&ccb=7-4&oh=7fe193da2e706c0cafd9e1d432734891&oe=60C59786&_nc_sid=4f375e'),
  'stories': []},
 'comment_count': 0,
 'like_count': 0,
 'has_liked': None,
 'caption_text': "Quand on te prend en photo sans que tu aies demandé et que la personne t'envoie tout par mail après...😂😁🤙🏻 Merci l'inconnu du coup \n\n#downhill #mountainlovers #ytowners #vanlife #vanlifefrance",
 'usertags': [],
 'video_url': None,
 'view_count': 0,
 'video_duration': 0.0,
 'title': '',
 'resources': [{'pk': 2574205301050111226,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://instagram.fhel3-1.fna.fbcdn.net/v/t51.2885-15/e35/184312115_2977220092557985_8274386175388868273_n.jpg?tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=101&_nc_ohc=YoLLGA0cAhsAX8MxnSo&edm=AP_V10EBAAAA&ccb=7-4&oh=b0f2740aaff1d80c5f5219ffa267a186&oe=60C4273E&_nc_sid=4f375e', scheme='https', host='instagram.fhel3-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/184312115_2977220092557985_8274386175388868273_n.jpg', query='tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=101&_nc_ohc=YoLLGA0cAhsAX8MxnSo&edm=AP_V10EBAAAA&ccb=7-4&oh=b0f2740aaff1d80c5f5219ffa267a186&oe=60C4273E&_nc_sid=4f375e'),
   'media_type': 1},
  {'pk': 2574205301083731874,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://instagram.fhel6-1.fna.fbcdn.net/v/t51.2885-15/e35/186524178_143770224434390_4909324648747352588_n.jpg?tp=1&_nc_ht=instagram.fhel6-1.fna.fbcdn.net&_nc_cat=102&_nc_ohc=w6z9v4MwYg8AX9FdWk0&edm=AP_V10EBAAAA&ccb=7-4&oh=99295fa82472bf4a425fc49bd03c1310&oe=60C40AFC&_nc_sid=4f375e', scheme='https', host='instagram.fhel6-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/186524178_143770224434390_4909324648747352588_n.jpg', query='tp=1&_nc_ht=instagram.fhel6-1.fna.fbcdn.net&_nc_cat=102&_nc_ohc=w6z9v4MwYg8AX9FdWk0&edm=AP_V10EBAAAA&ccb=7-4&oh=99295fa82472bf4a425fc49bd03c1310&oe=60C40AFC&_nc_sid=4f375e'),
   'media_type': 1},
  {'pk': 2574205301066842492,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://scontent-hel3-1.cdninstagram.com/v/t51.2885-15/e35/186787154_332065288355469_7843843424299639709_n.jpg?tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_cat=109&_nc_ohc=-qZy9_HakCQAX-Cqk9v&edm=AP_V10EBAAAA&ccb=7-4&oh=031077ab2f56db0bab7ffbc920f80a41&oe=60C4F57B&_nc_sid=4f375e', scheme='https', host='scontent-hel3-1.cdninstagram.com', tld='com', host_type='domain', path='/v/t51.2885-15/e35/186787154_332065288355469_7843843424299639709_n.jpg', query='tp=1&_nc_ht=scontent-hel3-1.cdninstagram.com&_nc_cat=109&_nc_ohc=-qZy9_HakCQAX-Cqk9v&edm=AP_V10EBAAAA&ccb=7-4&oh=031077ab2f56db0bab7ffbc920f80a41&oe=60C4F57B&_nc_sid=4f375e'),
   'media_type': 1},
  {'pk': 2574205301075310332,
   'video_url': None,
   'thumbnail_url': HttpUrl('https://instagram.fhel3-1.fna.fbcdn.net/v/t51.2885-15/e35/185727252_524026898594344_9165723485744355754_n.jpg?tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=104&_nc_ohc=45NguRpEtZQAX83VSGE&edm=AP_V10EBAAAA&ccb=7-4&oh=c8c087ecfba444d9d85f7bd059f42a2a&oe=60C5C3C2&_nc_sid=4f375e', scheme='https', host='instagram.fhel3-1.fna.fbcdn.net', tld='net', host_type='domain', path='/v/t51.2885-15/e35/185727252_524026898594344_9165723485744355754_n.jpg', query='tp=1&_nc_ht=instagram.fhel3-1.fna.fbcdn.net&_nc_cat=104&_nc_ohc=45NguRpEtZQAX83VSGE&edm=AP_V10EBAAAA&ccb=7-4&oh=c8c087ecfba444d9d85f7bd059f42a2a&oe=60C5C3C2&_nc_sid=4f375e'),
   'media_type': 1}]}
```

Low level methods:

| Method                                         | Return  | Description
| ---------------------------------------------- | ------- | --------------------------------------------
| hashtag_info_a1(name: str, max_id: str = None) | Hashtag | Get information about a hashtag by Public Web API
| hashtag_info_gql(name: str, amount: int = 12, end_cursor: str = None) | Hashtag | Get information about a hashtag by Public Graphql API
| hashtag_info_v1(name: str) | Hashtag | Get information about a hashtag by Private Mobile API
| hashtag_medias_a1_chunk(name: str, max_amount: int = 27, tab_key: str = "edge_hashtag_to_top_posts\|edge_hashtag_to_media", end_cursor: str = None) | Tuple[List[Media], str] | Get chunk of medias and end_cursor by Public Web API
| hashtag_medias_a1(name: str, amount: int = 27, tab_key: str = "edge_hashtag_to_top_posts\|edge_hashtag_to_media") | List[Media] | Get medias for a hashtag by Public Web API
| hashtag_medias_v1_chunk(name: str, max_amount: int = 27, tab_key: str = "top\|recent", max_id: str = None) | Tuple[List[Media], str] | Get chunk of medias for a hashtag and max_id (cursor) by Private Mobile API
| hashtag_medias_v1(name: str, amount: int = 27, tab_key: str = "top\|recent") | List[Media] | Get medias for a hashtag by Private Mobile API
| hashtag_medias_top_a1(name: str, amount: int = 9) | List[Media] | Get top medias for a hashtag by Public Web API
| hashtag_medias_top_v1(name: str, amount: int = 9) | List[Media] | Get top medias for a hashtag by Private Mobile API
| hashtag_medias_recent_a1(name: str, amount: int = 71) | List[Media] | Get recent medias for a hashtag by Public Web API
| hashtag_medias_recent_v1(name: str, amount: int = 27) | List[Media] | Get recent medias for a hashtag by Private Mobile API

Example for [Request for loading every next time new posts from hashtag](https://github.com/adw0rd/instagrapi/issues/79):

``` python
>>> medias, cursor = cl.hashtag_medias_v1_chunk('test', max_amount=32, tab_key='recent')
>>> len(medias)
32
>>> cursor
QVFDR0dzT3FJT0V4amFjMaQ3czlGVzRKV3FNWDJqaE1mWmltWU5VWGYtbnV6RVpoOUlsR3dCN05RRmpLc2R5SVlCQTNaekV5bUVOV0F4Vno1MDkxN1Nndg==

# NEXT cursor:

>>> medias, cursor = cl.hashtag_medias_v1_chunk('test', max_amount=32, tab_key='recent', max_id=cursor)
>>> len(medias)
32
>>> cursor
QVFEUXpfM0RtaDdmMExPQ0k0UWRlaHFJa2RVdVlaX01LTzhkNF9Dd1N2UlhtVy1vSTZvMERfYW5XN205OTBRNFBCSVJ2ZTVfTG5ZMXVmY0VJbUM5TU9URQ==
```