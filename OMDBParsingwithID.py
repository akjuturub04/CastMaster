import linecache
import string
import re
from collections import defaultdict
import requests
import json

Movie_DB = []
Movie_Master_DB = defaultdict()

def ProcessLine(Line):

  
	Name = Line.partition("(")[0].strip()
	#Genre = str(Name).split("\t")
	#print Genre, '\n'
	#print Name, '\n'
	Movie_DB.append(Name)
	
	
def movie():
	LineNo = 1631910
	while (LineNo != 2522745):
		Line = linecache.getline('movies.list', LineNo)
		ProcessLine(Line)
		LineNo += 1
	
	
def OMDB(movies):
	
	moviepart = movies.split()
	name = ""
	for part in moviepart:
		name += part + '%20'
	name = name[:-3]
	#print name
	
	url = 'http://www.omdbapi.com/?t=' + name
	#print url
	r = requests.get(url)
	r.json()
	
	Name = ""
	Year = ""
	Genre = ""
	Director = ""
	Rate = ""
	Movie = defaultdict()
	
	ID = 0
	info = json.loads(r.content)
	if info["Response"] == "True":
		#ID = str(info["imdbID"])
		Movie_Master_DB[ID] = info
		ID += 1
	
	
	
def main():

	print 'Getting movie names\n'
	movie()
	print 'Number of movies collected =', len(Movie_DB)
	print 'Getting movie info from IMDB\n'
	for movies in Movie_DB:
		OMDB(movies)
	
	print len(Movie_Master_DB)
	#for keys in Movie_Master_DB.keys():
	#	print keys, Movie_Master_DB[keys]
	
if __name__ == '__main__':
  main()
