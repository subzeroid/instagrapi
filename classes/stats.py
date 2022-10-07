def printStats(conf):
	username=conf["username"]
	cl=conf["cl"];
	my_pk = cl.user_id_from_username(username)
	my_user_id_infos = cl.user_info(my_pk);

	print("******************************************")
	print("******************************************")
	print(" >>>>>>>>>>> User: "+username);
	print(" >>>> Media Count: "+str(my_user_id_infos.media_count));
	print(" >>>>>> Following: "+str(my_user_id_infos.following_count));
	print(" >>>>>> Followers: "+str(my_user_id_infos.follower_count));
	print(" >>>>>> ");
	print(" >>>>>>> Today TS: "+str(conf["cooldown_day"]["curr"]));
	print(" >>>> Today Likes: "+str(conf["cooldown_day"]["likes"]));
	print(" >>> Today Follow: "+str(conf["cooldown_day"]["follows"]));
	print(" > Today Unfollow: "+str(conf["cooldown_day"]["unfollows"]));
	print(" >>>>>> ");
	print(" >>>>>>>> Hour Ts: "+str(conf["cooldown_hour"]["curr"]));
	print(" >>>>> Hour Likes: "+str(conf["cooldown_hour"]["likes"]));
	print(" >>>> Hour Follow: "+str(conf["cooldown_hour"]["follows"]));
	print(" >> Hour Unfollow: "+str(conf["cooldown_hour"]["unfollows"]));
	print(" >>>>>> ");
	print(" >>>>>> ");
	print(" >>>> Script Flws: "+str(conf["scripts_followers"]));
	print("******************************************")
	print("******************************************")
	print("")
			