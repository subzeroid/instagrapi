import pathlib
import json
import os

def loadCoolDownValues():
	f = pathlib.Path("cool_down_conf.json");
	if not f.exists():
		print("[loadConf] 1. File cool_down_conf not found. Fetch the git again");
		quit()
	conf = "";
	try:
		f = open("cool_down_conf.json");

	except Exception as e:
		print("[loadConf] 2. File cool_down_conf not found ")
		print(e);
		quit();
	conf = json.load(f)
	f.close()
	return conf;

def loadConf(user, cl):
	confdir = "conf/"+user+"/"
	f = pathlib.Path(confdir+"conf.json");
	if not f.exists():
		print("[loadConf] 1. File conf not found in "+confdir)
		quit()
	conf = "";
	try:
		f = open(confdir+"conf.json");

	except Exception as e:
		print("[loadConf] 2. File conf not found in "+confdir)
		print(e);
		quit();

	conf = json.load(f)
	f.close()
	conf["confdir"]=confdir;
	conf["cl"]=cl;
	return conf;

class botConf():
	def __init__(self, conf):
		self.conf=conf;

	def writeConf(self):
		tconf=self.conf.copy();
		confdir=tconf["confdir"];
		tconf.pop("cl", None);
		with open(confdir+"conf.json", 'w') as fp:
			json.dump(tconf, fp)

	def resetTodayConf(self, d):
		print("****************************************** ")
		print(" ******************** Reset DAILY counters");
		print("****************************************** ")
		self.conf["cooldown_day"]["likes"] = 0;
		self.conf["cooldown_day"]["follows"] = 0;
		self.conf["cooldown_day"]["unfollows"] = 0;
		self.conf["cooldown_day"]["curr"] = d;
		self.writeConf();

	def resetHourConf(self, d):
		print("****************************************** ")
		print(" ******************** Reset HOUR counters");
		print("****************************************** ")
		self.conf["cooldown_hour"]["likes"] = 0;
		self.conf["cooldown_hour"]["follows"] = 0;
		self.conf["cooldown_hour"]["unfollows"] = 0;
		self.conf["cooldown_hour"]["curr"] = d;
		self.writeConf();

	def confAddLike(self):
		self.conf["cooldown_day"]["likes"] += 1;
		self.conf["cooldown_hour"]["likes"] += 1;
		self.writeConf();

	def confAddFollow(self):
		self.conf["cooldown_day"]["follows"] += 1;
		self.conf["cooldown_hour"]["follows"] += 1;
		self.writeConf();

	def confAddUnfollow(self):
		self.conf["cooldown_day"]["unfollows"] += 1;
		self.conf["cooldown_hour"]["unfollows"] += 1;
		self.writeConf();