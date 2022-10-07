from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword, ReloginAttemptExceeded, ChallengeRequired,
    SelectContactPointRecoveryForm, RecaptchaChallengeForm,
    FeedbackRequired, PleaseWaitFewMinutes, LoginRequired
)
import pathlib
import random
import time
import urllib
import urllib.request
import os
import json

cl = Client()


def newUser(u, p, t):
	confdir="conf/"+u+"/"
	udir = pathlib.Path(confdir);
	if not udir.exists():
		os.mkdir(udir);

	#### instagrapi file
	file = pathlib.Path(confdir+"login.json");
	if file.exists ():
		cl.load_settings(confdir+"login.json")
	else:
		cl.dump_settings(confdir+"login.json")

	#### bot user config
	file = pathlib.Path(confdir+"conf.json");
	conf = {"username": u, "password": p, "tags": t, "cooldown_day": {"curr": 0, "follows": 0, "likes": 0, "unfollows": 0}, "cooldown_hour": {"curr": 0, "follows": 0, "likes": 0, "unfollows": 0}, "messages": {"active": 1, "texts":{"en": "Hi Thanks for the follow! How are you?", "es": "Gracias por el follow! Como estas?"} } }
	with open(confdir+"conf.json", 'w') as fp:
			json.dump(conf, fp)

	csv = ["medias.csv", "medias_downloaded.csv", "medias_liked.csv", "medias_seen.csv", "thumbs_downloaded.csv", "followed.csv"];
	for f in csv:
		file = pathlib.Path(confdir+f);
		if not file.exists():
			file.touch();

	return

class usersLogin():
    def __init__(self, username, password, tags):
        self.username = username
        self.password = password
        self.tags = tags



