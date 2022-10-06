import pathlib
import os
import glob

def initDirs():
	f=pathlib.Path("downloads");
	if not f.exists():
		print("Dir 'downloads' not exists")
		try: 
			os.mkdir("downloads")
		except:
			print("Can't create downloads directory")
			print("Manually create a dir called 'downloads' and execute again")
			quit()

	else:
		print("Clean 'downloads' dir ", end="")
		files = glob.glob('downloads/*');

		for f in files:
		    try:
		        os.remove(f)
		    except OSError as e:
		        print("Error: %s : %s" % (f, e.strerror))
		        
		print("....Done")

def cleanFiles(conf):
	linesToKeep=100;
	confdir = conf["confdir"]
	csv = ["medias.csv", "medias_downloaded.csv", "medias_liked.csv", "medias_seen.csv", "thumbs_downloaded.csv", "followed.csv"];

	for f in csv:
		with open(confdir+f, 'r+') as fp:
		    # read an store all lines into list
		    lines = fp.readlines()
		    if (len(lines) < linesToKeep):
		    	continue

		    num = len(lines)-linesToKeep;	
		    # move file pointer to the beginning of a file
		    fp.seek(0)
		    # truncate the file
		    fp.truncate()

		    # start writing lines
		    # iterate line and line number
		    for i, line in enumerate(lines):
		        # delete line number 5 and 8
		        # note: list index start from 0
		        if i >= num:
		            fp.write(line)
