# Track

Viewing and downloading tracks

| Method                                                                 | Return      | Description
| ---------------------------------------------------------------------- | ----------- | --------------------------------------------
| track_info_by_canonical_id(music_canonical_id: str)                    | Track       | Get Track by music_canonical_id
| track_download_by_url(url: str, filename: str = "", folder: Path = "") | Path        | Download track by URL
| search_music(query: str)                                               | List[Track] | Return list of tracks

### Example:

```python
>>> from instagrapi import Client
>>> cl = Client()
>>> cl.login(USERNAME, PASSWORD)

>>> [media.clips_metadata['music_canonical_id'] for media in cl.reels(amount=10)]

['18159860503036324',
 '18245182426110798',
 '18156435169051995',
 '18274086877034385',
 '18243482860109137',
 '18244791958105000',
 '18310451203035205',
 '18293984647065921',
 '18154598032011335',
 '18301950994013617']

>>> cl.track_info_by_canonical_id(18159860503036324).dict()
{
'id': '2398788493765573',
'title': 'A Little Bit Goes a Long Way',
'subtitle': '',
'display_artist': 'Yheti',
'audio_cluster_id': 1054108181594434,
'artist_id': None,
'cover_artwork_uri': None,
'cover_artwork_thumbnail_uri': None,
'progressive_download_url': None,
'fast_start_progressive_download_url': None,
'reactive_audio_download_url': None,
'highlight_start_times_in_ms': [38500],
'is_explicit': False,
'dash_manifest': '<?xml version="1.0" encoding="UTF-8"?>\n<!--Generated with https://github.com/google/shaka-packager version v1.6.0-release-->\n<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:cenc="urn:mpeg:cenc:2013" xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 DASH-MPD.xsd" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" minBufferTime="PT2S" type="static" mediaPresentationDuration="PT182.137S">\n  <Period id="0">\n    <AdaptationSet id="0" contentType="audio" subsegmentAlignment="true">\n      <Representation id="0" bandwidth="130017" codecs="mp4a.40.2" mimeType="audio/mp4" audioSamplingRate="48000">\n        <AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2"/>\n        <BaseURL>https://scontent-cph2-1.xx.fbcdn.net/v/t39.12897-6/84846439_2484536748531420_3971102873273499648_n.m4a?_nc_cat=101&amp;ccb=1-7&amp;_nc_sid=02c1ff&amp;_nc_ohc=N6k7lDt_6TAAX_yKEoV&amp;_nc_ad=z-m&amp;_nc_cid=0&amp;_nc_ht=scontent-cph2-1.xx&amp;oh=00_AT9Cly5G-kzGxRceunBi8NUl5eFLEqwlMEJbWnxykUTO0Q&amp;oe=62DF3A6E</BaseURL>\n        <SegmentBase indexRange="741-1864" timescale="48000">\n          <Initialization range="0-740"/>\n        </SegmentBase>\n      </Representation>\n    </AdaptationSet>\n  </Period>\n</MPD>\n',
'uri': HttpUrl('https://scontent-cph2-1.xx.fbcdn.net/v/t39.12897-6/84846439_2484536748531420_3971102873273499648_n.m4a?_nc_cat=101&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=N6k7lDt_6TAAX_yKEoV&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT9Cly5G-kzGxRceunBi8NUl5eFLEqwlMEJbWnxykUTO0Q&oe=62DF3A6E', scheme='https', host='scontent-cph2-1.xx.fbcdn.net', tld='net', host_type='domain', port='443', path='/v/t39.12897-6/84846439_2484536748531420_3971102873273499648_n.m4a', query='_nc_cat=101&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=N6k7lDt_6TAAX_yKEoV&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT9Cly5G-kzGxRceunBi8NUl5eFLEqwlMEJbWnxykUTO0Q&oe=62DF3A6E'),
'has_lyrics': False,
'audio_asset_id': 2398788493765573,
'duration_in_ms': 182094,
'dark_message': None,
'allows_saving': True,
'territory_validity_periods': {}
}

>>> track_uri = cl.track_info_by_canonical_id(18159860503036324).uri
HttpUrl('https://scontent-cph2-1.xx.fbcdn.net/v/t39.12897-6/84846439_2484536748531420_3971102873273499648_n.m4a?_nc_cat=101&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=N6k7lDt_6TAAX_yKEoV&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT9Cly5G-kzGxRceunBi8NUl5eFLEqwlMEJbWnxykUTO0Q&oe=62DF3A6E', scheme='https', host='scontent-cph2-1.xx.fbcdn.net', tld='net', host_type='domain', port='443', path='/v/t39.12897-6/84846439_2484536748531420_3971102873273499648_n.m4a', query='_nc_cat=101&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=N6k7lDt_6TAAX_yKEoV&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT9Cly5G-kzGxRceunBi8NUl5eFLEqwlMEJbWnxykUTO0Q&oe=62DF3A6E')

>>> cl.track_download_by_url(track_uri, folder="/tmp")
PosixPath('/tmp/84846439_2484536748531420_3971102873273499648_n.m4a')

>>> cl.search_music("love")[0].dict()
{
'id': '354372829354341',
'title': 'Love Your Voice',
'subtitle': '',
'display_artist': 'JONY',
'audio_cluster_id': 410742646320351,
'artist_id': None,
'cover_artwork_uri': HttpUrl('https://cdn.fbsbx.com/v/t65.14500-21/191897578_1074647849725858_3973554110966662866_n.jpg?stp=cp0_dst-jpg_e15_p526x296_q65&_nc_cat=1&ccb=1-7&_nc_sid=cbead8&_nc_ohc=ugygksMclf4AX_u7L7g&_nc_ht=cdn.fbsbx.com&oh=00_AT89FBXl6h7Q6zytlI5cA4UIG_zQkK_DsOqyUqyXk1zyIg&oe=62DAEA82', scheme='https', host='cdn.fbsbx.com', tld='com', host_type='domain', port='443', path='/v/t65.14500-21/191897578_1074647849725858_3973554110966662866_n.jpg', query='stp=cp0_dst-jpg_e15_p526x296_q65&_nc_cat=1&ccb=1-7&_nc_sid=cbead8&_nc_ohc=ugygksMclf4AX_u7L7g&_nc_ht=cdn.fbsbx.com&oh=00_AT89FBXl6h7Q6zytlI5cA4UIG_zQkK_DsOqyUqyXk1zyIg&oe=62DAEA82'),
'cover_artwork_thumbnail_uri': HttpUrl('https://cdn.fbsbx.com/v/t65.14500-21/191897578_1074647849725858_3973554110966662866_n.jpg?stp=cp0_dst-jpg_e15_q65_s168x128&_nc_cat=1&ccb=1-7&_nc_sid=cbead8&_nc_ohc=ugygksMclf4AX_u7L7g&_nc_ht=cdn.fbsbx.com&oh=00_AT81eLXWBA5EaM20EhaMldwlyzKG1X1zA_nYNkYWf6c5cg&oe=62DAEA82', scheme='https', host='cdn.fbsbx.com', tld='com', host_type='domain', port='443', path='/v/t65.14500-21/191897578_1074647849725858_3973554110966662866_n.jpg', query='stp=cp0_dst-jpg_e15_q65_s168x128&_nc_cat=1&ccb=1-7&_nc_sid=cbead8&_nc_ohc=ugygksMclf4AX_u7L7g&_nc_ht=cdn.fbsbx.com&oh=00_AT81eLXWBA5EaM20EhaMldwlyzKG1X1zA_nYNkYWf6c5cg&oe=62DAEA82'),
'progressive_download_url': HttpUrl('https://scontent-cph2-1.xx.fbcdn.net/v/t39.12897-6/199073207_321615622853093_2366400633227710754_n.m4a?_nc_cat=1&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=UxUNJHpsoy4AX-eA1Bm&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT_IpjsOwgCikt0wNx1nS7FzEJE-1pKkzNZSXIpKCzkZhg&oe=62DE2CA8', scheme='https', host='scontent-cph2-1.xx.fbcdn.net', tld='net', host_type='domain', port='443', path='/v/t39.12897-6/199073207_321615622853093_2366400633227710754_n.m4a', query='_nc_cat=1&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=UxUNJHpsoy4AX-eA1Bm&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT_IpjsOwgCikt0wNx1nS7FzEJE-1pKkzNZSXIpKCzkZhg&oe=62DE2CA8'),
'fast_start_progressive_download_url': HttpUrl('https://scontent-cph2-1.xx.fbcdn.net/v/t39.12897-6/199073207_321615622853093_2366400633227710754_n.m4a?_nc_cat=1&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=UxUNJHpsoy4AX-eA1Bm&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT_IpjsOwgCikt0wNx1nS7FzEJE-1pKkzNZSXIpKCzkZhg&oe=62DE2CA8', scheme='https', host='scontent-cph2-1.xx.fbcdn.net', tld='net', host_type='domain', port='443', path='/v/t39.12897-6/199073207_321615622853093_2366400633227710754_n.m4a', query='_nc_cat=1&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=UxUNJHpsoy4AX-eA1Bm&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT_IpjsOwgCikt0wNx1nS7FzEJE-1pKkzNZSXIpKCzkZhg&oe=62DE2CA8'),
'reactive_audio_download_url': None,
'highlight_start_times_in_ms': [20000, 35500, 86500],
'is_explicit': False,
'dash_manifest': '<?xml version="1.0" encoding="UTF-8"?>\n<!--Generated with https://github.com/google/shaka-packager version v1.6.0-release-->\n<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:cenc="urn:mpeg:cenc:2013" xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 DASH-MPD.xsd" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" minBufferTime="PT2S" type="static" mediaPresentationDuration="PT150.372S">\n  <Period id="0">\n    <AdaptationSet id="0" contentType="audio" subsegmentAlignment="true">\n      <Representation id="0" bandwidth="130029" codecs="mp4a.40.2" mimeType="audio/mp4" audioSamplingRate="48000">\n        <AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2"/>\n        <BaseURL>https://scontent-cph2-1.xx.fbcdn.net/v/t39.12897-6/198992520_981513595929106_5731656525090532090_n.m4a?_nc_cat=1&amp;ccb=1-7&amp;_nc_sid=02c1ff&amp;_nc_ohc=ZZ6zJXs2dkAAX-B0LDK&amp;_nc_ad=z-m&amp;_nc_cid=0&amp;_nc_ht=scontent-cph2-1.xx&amp;oh=00_AT8j4tjiUNSVWv9qbkg9Ro9MzAGeW9_wXU4e0ncV0MhdZQ&amp;oe=62DECA6E</BaseURL>\n        <SegmentBase indexRange="741-1672" timescale="48000">\n          <Initialization range="0-740"/>\n        </SegmentBase>\n      </Representation>\n    </AdaptationSet>\n  </Period>\n</MPD>\n',
'uri': HttpUrl('https://scontent-cph2-1.xx.fbcdn.net/v/t39.12897-6/198992520_981513595929106_5731656525090532090_n.m4a?_nc_cat=1&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=ZZ6zJXs2dkAAX-B0LDK&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT8j4tjiUNSVWv9qbkg9Ro9MzAGeW9_wXU4e0ncV0MhdZQ&oe=62DECA6E', scheme='https', host='scontent-cph2-1.xx.fbcdn.net', tld='net', host_type='domain', port='443', path='/v/t39.12897-6/198992520_981513595929106_5731656525090532090_n.m4a', query='_nc_cat=1&ccb=1-7&_nc_sid=02c1ff&_nc_ohc=ZZ6zJXs2dkAAX-B0LDK&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent-cph2-1.xx&oh=00_AT8j4tjiUNSVWv9qbkg9Ro9MzAGeW9_wXU4e0ncV0MhdZQ&oe=62DECA6E'),
'has_lyrics': True,
'audio_asset_id': 354372829354341,
'duration_in_ms': 150329,
'dark_message': None,
'allows_saving': True,
'territory_validity_periods': {}
}

```