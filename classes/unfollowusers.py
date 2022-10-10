from classes.botconf import botConf;
from classes.botconf import loadCoolDownValues;
from classes.media import downloadThumb;
import random
from datetime import datetime, tzinfo, date, timezone
import time
#import calendar

def unfollowUsers(conf):
	confdir = conf["confdir"];
	username = conf["username"]
	localBotConf = botConf(conf);
	coolDownMaxValues = loadCoolDownValues(conf);
	cl=conf["cl"]

	### get my followers
	my_pk = cl.user_id_from_username(username)
	my_user_id_infos = cl.user_info(my_pk);

	following = cl.user_following_v1(my_pk);

	print("[unfollowUser] Download profile pictures for "+str(len(following))+" followed-> ", end='');
	i=0;
	for x in following:
		if (i>=50):
			break;
		try:
			downloadThumb(conf, x.pk, x.profile_pic_url)
			i+=1;
		except:
			continue;
	print();

	i=0;
	r1=random.randint(3,7)
	for x in following:
		unfollow=True;
		a=bool(conf["cooldown_day"]["unfollows"] >= coolDownMaxValues["day_max_unfollows"]);
		d=bool(conf["cooldown_hour"]["unfollows"] >= coolDownMaxValues["hour_max_unfollows"]);
		if a or d:
			print("[unfollowUser] Max cooldown reached, can't unfollow ")
			print("[unfollowUser] Day: "+str(a))
			print("[unfollowUser] Hour: "+str(d))
			break;

		if i>=r1:
			break;

		### Unfollow just accounts followed by the scripts
		if x.pk not in open(confdir+'followed.csv').read():
			# print("[unfollowUser] "+x.username+" Not in followed.csv")
			continue;

		### Unfollow just accounts followed for at least 30d
		with open(confdir+'followed.csv', 'rt') as f:
			data = f.readlines()

		for line in data:
			if (x.pk in line):
				t = line.split(":")[0]
				diffInDays = int((time.mktime(time.strptime(str(datetime.now(timezone.utc)).split(".")[0], "%Y-%m-%d %H:%M:%S")) - float(t))/14400);
				if (diffInDays < 30):
					print("[unfollowUser] can't unfollow: "+x.username+", following since days: "+str(diffInDays))
					unfollow=False
					break

		if unfollow is True:
			try:
				print("[unfollowUser] Unfollowing "+x.username);
				localBotConf.confAddUnfollow();
				cl.user_unfollow(x.pk);
				i+=1;
			except:
				continue;
