import urllib
import urllib.request
import random
import time
from classes.media import downloadThumb;
from classes.media import downloadMedia;
from classes.media import likeMedia;
from classes.followusers import followMediaLikers;
from classes.followusers import followUser;

def getFromHashtag(conf, cursor=None):
	tags = conf["tags"].split(";");
	confdir = conf["confdir"]
	cl = conf["cl"];

	r1=random.randint(24, 32)
	r2=random.randint(0, len(tags)-1)
	# r1=2;
	
	tag=tags[r2]
	print("Getting "+str(r1)+" medias for tag "+tag);
	# medias = cl.hashtag_medias_recent(tag, amount=r1)
	if cursor is None:
		medias, cursor = cl.hashtag_medias_v1_chunk(tag, max_amount=r1, tab_key='recent')
	else:
		medias, cursor = cl.hashtag_medias_v1_chunk(tag, max_amount=r1, tab_key='recent', max_id=cursor)

	try:
		# Hastags Download all thumbnails
		print("[getHashtag] Downloading "+str(r1)+" thumbs -> ", end='')
		for x in medias:
			downloadThumb(conf, x.id, x.thumbnail_url)
			# print(x.thumbnail_url);
			
		time.sleep(random.randint(1,5))
		print("")

		# Hashtags liking medias
		for x in medias:
			print("");
			print("[getHashtag] >>> User "+x.user.username)
			print("[getHashtag] + mediaId: "+x.id+", mediaType: "+str(x.media_type), end=', ')

			if str(x.id) in open(confdir+'medias_seen.csv').read():
				print("next")
				continue
				
			# media checked
			file1=open(confdir+"medias_seen.csv", "a")
			file1.write(str(x.id)+"\n")
			file1.close()
			
			# print(x.dict())
			r1=random.uniform(0, 15);
			print("Random: "+str(r1));
			if r1<4:
				downloadMedia(conf, x.pk, x.media_type, x.product_type);
				s=random.randrange(1,10)
				time.sleep(s);

			if r1<3.5:
				likeMedia(conf, x.pk, x.product_type)
				s=random.uniform(1,20)
				time.sleep(s);

			if r1<3.3:
				followUser(conf, x.user.pk);
				

				r2=random.randint(0,100)
				if r2<20:
					followMediaLikers(conf, x.pk);
					s=random.uniform(.2,2)
					time.sleep(s);
					
				s=random.randrange(1,6)
				time.sleep(s);

			if r1<2:
				# checking user media
				e_user_medias = cl.user_medias_v1(x.user.pk, 9)
				print("[getHashtag] "+x.user.username+" Getting user medias ")
				print("[getHashtag] "+x.user.username+" Downloading thumbnails user medias ", end = '')
				for xx in e_user_medias:	
					print("o", end = '')
					# print(xx.thumbnail_url);
					if xx.thumbnail_url is not None:
						urllib.request.urlretrieve(xx.thumbnail_url, "downloads/_tempthumb")
				print("")
				
				s=random.randrange(2,9)
				time.sleep(s);
				
				for xx in e_user_medias:	
					r2=random.randint(0,100)
					if r2<20:

						print("[getHashtag] "+x.user.username+" Downloading user media "+xx.pk);
						downloadMedia(conf, xx.pk, xx.media_type, xx.product_type)
						
						s=random.randrange(1,3)
						time.sleep(s);

						if r2<10:
							print("[getHashtag] "+x.user.username+" Liking user media "+xx.pk)
							likeMedia(conf, xx.pk, xx.product_type)

						s=random.randrange(2,9)
						time.sleep(s);

				s=random.randrange(2,9)
				time.sleep(s);
	except Exception as e:
		print("Some error occurred in execution")
		print(e)

	s=random.randrange(0,9)
	if (s>6):
		print("[getHashtag] REFREEEEEEEEEEEEEEEEEEEEEESH ")
		getFromHashtag(conf, cursor)