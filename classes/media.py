import pathlib
import os
import random
import urllib
import urllib.request
from classes.botconf import botConf;
from classes.botconf import loadCoolDownValues;

def downloadThumb(conf, pk, thumbnail_url):
	confdir = conf["confdir"]
	
	if str(pk) in open(confdir+'thumbs_downloaded.csv').read():
		print("x", end='')
		return

	if thumbnail_url is not None:
		urllib.request.urlretrieve(thumbnail_url, "downloads/temp_thumb")

	print("o", end='');
	# media checked
	file1=open(confdir+"thumbs_downloaded.csv", "a")
	file1.write(str(pk)+"\n")
	file1.close();

def downloadMedia(conf, pk, item_type, product_type):
	cl = conf["cl"]
	confdir = conf["confdir"]

	if str(pk) in open(confdir+'medias_downloaded.csv').read():
		print("[likeMedia] next")
		return

	# media checked
	file1=open(confdir+"medias_downloaded.csv", "a")
	file1.write(str(pk)+"\n")
	file1.close();

	print("[downloadMedia] Downloading media "+str(pk));
	try:
		if item_type==1:
			cl.photo_download(pk, folder='downloads');
		elif item_type==8:
			if product_type == "album":
				cl.album_download(pk, folder='downloads');
		elif item_type==2:
			if product_type == "igtv":
				cl.igtv_download(pk, folder='downloads');
			elif product_type == "video":
				cl.video_download(pk, folder='downloads');
	except Exception as e:
		print("\n[downloadMedia] Some error in feed downloads vvvv ");
		print(e)

def likeMedia(conf, pk, product_type):
	cl = conf["cl"]
	confdir = conf["confdir"]
	localBotConf = botConf(conf);
	coolDownMaxValues = loadCoolDownValues();


	a=bool(conf["cooldown_day"]["likes"] >= coolDownMaxValues["day_max_likes"]);
	b=bool(conf["cooldown_hour"]["likes"] >= coolDownMaxValues["hour_max_likes"]);
	if a or b:
		print("[likeMedia] Max cooldown reached, can't like ")
		print("[likeMedia] Day: "+str(a))
		print("[likeMedia] Hour: "+str(b))
		return;

	if product_type == 'ad':
		print("[likeMedia] Skipping ad")
		return

	if str(pk) in open(confdir+'medias_liked.csv').read():
		print("[likeMedia] next")
		return

	# media checked
	file1=open(confdir+"medias_liked.csv", "a")
	file1.write(str(pk)+"\n")
	file1.close();
	
	
	print("[likeMedia] Liking media "+str(pk));
	localBotConf.confAddLike();

	try:
		cl.media_like(pk);
	except:
		print("[likeMedia] Some error liking the media");
	

def followMediaLikers(conf, pk):
	cl = conf["cl"]
	confdir = conf["confdir"]

	print("[followMediaLikers] "+pk+" Get media likes ");
	e_media_likes = cl.media_likers(pk);
	i=0;
	r2=random.randint(0,8)
	for xx in e_media_likes:
		if i>=r2:
			print("[followMediaLikers] "+pk+" End media likes ")
			break;
		if random.randint(0,100) < 30:
			continue;
		
		print("[followMediaLikers] Following user "+xx.username+" (in media likes)");
		# Append to file at last
		followUser(conf, xx.username, xx.pk);
		i+=1;

	