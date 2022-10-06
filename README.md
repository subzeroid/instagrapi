# Human Simulation Instagram Bot
This bot is intended to legally increase the number of your instagram followers,   
trying to act as a human, to avoid instagram suspensions.

##### Just clone it on your PC and begin to use

```
python instabot.py new
```

it creates new user, asking for username, password and tags.  
Conf is saved in ./conf/$(USERNAME)/

```
python instabot.py 
```

it will ask for user, and should start automatically  

You can add as many accounts as you want

This bot is intended to increase legally the number of your followers,   
trying to act as a human.

This bot is "tag based", and search for the last posts for the tags you specify 
(The logic is that users that a user that just posted something, if he receive a like or a follow, it's active and propense to exchange the follow)

#### This bot has a **cooldown function**, you can configure cooldown values
in the file "./cool_down_conf.json"

The bot doesn't like or follow, if cooldown values are over, **for the day or for the current hour** (till 00 of the next hour)
cooldown periods are account defined. So, if you finish likes and follows for one account, you can jump to the next one.

Bots act in this way:  
- It downloads the thumbnails of the media  
- randomly download some image/video/album full resolution  
- rendomly likes it  
- randomly follow the user, with higher chances to follow users with less followers  
- randomly follow users that liked the media (generally there aren't too much because the posts are new, but that's depends by tags)  
- randomly check user infos  
- randomly get user posts  
- it downloads user posts thumbnails (like the mobile app do)   
- randomly open the user post  
- randomly likes it  
- randomly refresh the page, passing the cursor  
- randomly wait random times; every 10 execution average, it sleeps for 1-4 hours.  

It logs everything, it's noisy => It's the first version.

It saves all pk and id of   
- users followed  
- medias visualized  
- medias donloaded  
- medias liked  
- thumbs downloaded  
so it avoid to duplicate actions  

files are kept clean, just last 100 lines are kept (you can change this value, it's hardcoded, but easy to find, in ./classes/init.py, function cleanFiles(), var linesToKeep = 100)  
download directory is kept clean, all downloaded files are deleted at every execution.   
If you want to keep all history and all downloaded files, you can comment  

initDirs();  
cleanFiles(conf);  

lines in instabot.py, around line ~100  
(Do it just after first execution, because it creates automatically the download directory. If you coment it, you'll need to create the dir manually)
