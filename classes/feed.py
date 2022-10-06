import random
from classes.media import downloadMedia;
from classes.media import likeMedia;

def gefFromFeed(conf):
	cl=conf["cl"];
	feed = cl.get_timeline_feed();
	
	if 'results' in feed:
		print("Got "+str(feed['num_results'])+" results");

	# Feed Download Medias
	print("[Feed] From feed, downloading all medias ");
	for item in feed['feed_items']:
		downloadMedia(conf, item['media_or_ad']['pk'], item['media_or_ad']['media_type'], item['media_or_ad']['product_type'])
		
	print("")
	# Feed like
	for item in feed['feed_items']:
		feed_item_content = item['media_or_ad']
		feed_item_pk = feed_item_content['pk'];
		feed_product_type = feed_item_content['product_type'];
		
		r1=random.randint(0, 10);
		if r1<4:
			likeMedia(conf, feed_item_pk, feed_product_type);
