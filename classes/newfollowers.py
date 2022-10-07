from classes.botconf import botConf;
from classes.botconf import loadCoolDownValues;
from classes.media import downloadThumb;
import random
from datetime import datetime, tzinfo, date, timezone
import time
#import calendar

from langdetect import detect

def getNewFollowers(conf, cursor=None):
	cl=conf["cl"]
	confdir = conf["confdir"]
	username = conf["username"]
	localBotConf = botConf(conf);


	my_pk = cl.user_id_from_username(username)
	my_user_id_infos = cl.user_info(my_pk);
	# followers = cl.user_followers(my_pk);
	followers, cursor = cl.user_followers_v1_chunk(my_pk, 100, cursor)

	for x in followers:
		if x.pk not in open(confdir+'followers.csv').read():
			print("[GetNewFollowers] Registering follower "+x.username);
			file1=open(confdir+"followers.csv", "a")
			file1.write(x.pk+"\n")
			file1.close()

			if x.pk in open(confdir+"followed.csv").read():
				#get when followed
				with open(confdir+'followed.csv', 'rt') as f:
					data = f.readlines()
				
				diffInDays=None
				for line in data:
					if (x.pk in line):
						t = line.split(":")[0]
						diffInDays = int((time.mktime(time.strptime(str(datetime.now(timezone.utc)).split(".")[0], "%Y-%m-%d %H:%M:%S")) - float(t))/14400);

				print("[GetNewFollowers] User "+x.username+" is a NEW follower, followed "+str(diffInDays)+" days ago");
				sendMessage(conf, x.pk)
				time.sleep(10)

	return


def sendMessage(conf, pk):
	cl=conf["cl"]
	confdir = conf["confdir"]
	username = conf["username"]

	#### Send Message part
	if conf["messages"]["active"] == 0:
		return

	if pk in open(confdir+'messages.csv').read():
		return
	
	user_info = cl.user_info(pk);
	bio = user_info.biography;
	lan = detect(bio);
	if lan not in conf["messages"].keys():
		lan = "en"
	m = conf["messages"]["texts"][lan];

	print("[SendMessage] Sending Message in "+lan);
	file1=open(confdir+"messages.csv", "a")
	file1.write(pk+"\n")
	file1.close()

	# cl.direct_send(m, [9518783079]);
	cl.direct_send(m, [pk]);