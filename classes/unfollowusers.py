from classes.botconf import botConf;
from classes.botconf import loadCoolDownValues;
from classes.media import downloadThumb;
import random

def unfollowUsers(conf):
	confdir = conf["confdir"];
	username = conf["username"]
	localBotConf = botConf(conf);
	coolDownMaxValues = loadCoolDownValues();
	cl=conf["cl"]

	### get my followers
	my_pk = cl.user_id_from_username(username)
	my_user_id_infos = cl.user_info(my_pk);

	following = cl.user_following_v1(my_pk, 50);

	print("[unfollowUser] Download profile pictures for "+str(len(following))+" followed-> ", end='');
	for x in following:
		try:
			downloadThumb(conf, x.pk, x.profile_pic_url)
		except:
			continue;
	print();

	i=0;
	r1=random.randint(3,7)
	for x in following:
		a=bool(conf["cooldown_day"]["unfollows"] >= coolDownMaxValues["day_max_unfollows"]);
		d=bool(conf["cooldown_hour"]["unfollows"] >= coolDownMaxValues["hour_max_unfollows"]);
		if a or d:
			print("[unfollowUser] Max cooldown reached, can't unfollow ")
			print("[unfollowUser] Day: "+str(a))
			print("[unfollowUser] Hour: "+str(d))
			break;

		if i>=r1:
			break;

		r2=random.randint(0,100)
		if r2<55:
			try:
				print("[unfollowUser] Unfollowing "+x.username);
				localBotConf.confAddUnfollow();
				cl.user_unfollow(x.pk);
				i+=1;
			except:
				continue;
