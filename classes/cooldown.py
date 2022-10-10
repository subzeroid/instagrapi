
def coolDownCheck(conf, coolDownMaxValues):
	a=bool(conf["cooldown_day"]["follows"] >= coolDownMaxValues["day_max_follows"]);
	b=bool(conf["cooldown_day"]["likes"] >= coolDownMaxValues["day_max_likes"]);
	c=bool(conf["cooldown_day"]["unfollows"] >= coolDownMaxValues["day_max_unfollows"]);
	d=bool(conf["cooldown_hour"]["follows"] >= coolDownMaxValues["hour_max_follows"]);
	e=bool(conf["cooldown_hour"]["likes"] >= coolDownMaxValues["hour_max_likes"]);
	f=bool(conf["cooldown_hour"]["unfollows"] >= coolDownMaxValues["hour_max_unfollows"]);

	if a and b and d and e:
		return False;

	return True;

def coolDownCheckHour(conf, coolDownMaxValues):
	d=bool(conf["cooldown_hour"]["follows"] >= coolDownMaxValues["hour_max_follows"]);
	e=bool(conf["cooldown_hour"]["likes"] >= coolDownMaxValues["hour_max_likes"]);
	f=bool(conf["cooldown_hour"]["unfollows"] >= coolDownMaxValues["hour_max_unfollows"]);

	if d and e:
		return False;

	return True;

def coolDownCheckDay(conf, coolDownMaxValues):
	a=bool(conf["cooldown_day"]["follows"] >= coolDownMaxValues["day_max_follows"]);
	b=bool(conf["cooldown_day"]["likes"] >= coolDownMaxValues["day_max_likes"]);
	c=bool(conf["cooldown_day"]["unfollows"] >= coolDownMaxValues["day_max_unfollows"]);

	if a and b:
		return False;

	return True;
