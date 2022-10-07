from classes.botconf import botConf;
from classes.botconf import loadCoolDownValues;
from classes.media import downloadThumb;
import random
from datetime import datetime, tzinfo, date, timezone
import time
#import calendar


def followUser(conf, pk):
	confdir = conf["confdir"];
	localBotConf = botConf(conf);
	coolDownMaxValues = loadCoolDownValues();
	cl=conf["cl"]

	a=bool(conf["cooldown_day"]["follows"] >= coolDownMaxValues["day_max_follows"]);
	d=bool(conf["cooldown_hour"]["follows"] >= coolDownMaxValues["hour_max_follows"]);
	if a or d:
		print("[followUser] Max cooldown reached, can't follow ")
		print("[followUser] Day: "+str(a))
		print("[followUser] Hour: "+str(d))
		return;

	if pk in open(confdir+'followed.csv').read():
		return
	
	r2=random.randint(0,100)
	follower_count=0;
	if r2<45:
		e_user_info = cl.user_info(pk);
		follower_count=e_user_info.follower_count;
		print("[followUser] "+e_user_info.username+" Got User infos");
		print("[followUser] "+e_user_info.username+" Download profile picture -> ", end='');
		try:
			downloadThumb(conf, e_user_info.pk, e_user_info.profile_pic_url)
		except:
			print("[followUser][ERROR] Error downlading Thumb");
			print(e_user_info);
		print()
	
	now_ts=str(time.mktime(time.strptime(str(datetime.now(timezone.utc)).split(".")[0], "%Y-%m-%d %H:%M:%S")))
	if follower_count < 1400:
		print("[followUser] Following user");
		# Append to file at last
		file1=open(confdir+"followed.csv", "a")
		file1.write(now_ts+":"+pk+"\n")
		file1.close()

		localBotConf.confAddFollow();
		cl.user_follow(pk) 

def followMediaLikers(conf, pk):
	cl = conf["cl"]
	confdir = conf["confdir"]

	print("[followMediaLikers] "+pk+" Get media likes ");
	e_media_likes = cl.media_likers(pk);
	i=0;
	r2=random.randint(0,4)
	for xx in e_media_likes:
		if i>=r2:
			print("[followMediaLikers] "+pk+" End media likes ")
			break;
		if random.randint(0,100) < 30:
			continue;
		
		print("[followMediaLikers] Following user "+xx.username+" (in media likes)");
		# Append to file at last
		followUser(conf, xx.pk);
		i+=1;
