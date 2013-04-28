import linecache
import string
import re
from collections import defaultdict


Movie_DB = defaultdict(set)
Dir_DB = defaultdict(set)


def ProcessLine(Line):

  Line = Line.lower()
	Genre = Line.split()[-1]
	Name = Line.partition("\t")[0].strip()
	#Genre = str(Name).split("\t")
	#print Genre, '\n'
	#print Name, '\n'
	Movie_DB[Name].add(Genre)
	
	
def ProcessDir(Line):
	Whole = Line.lower().split('(')[0].strip()
	W = Whole.partition('\t')
	Director = W[0]
	#print Director
	Mv = W[2]
	Movie = re.sub('[%s]' % re.escape('"'), ' ', Mv).strip('\t')
	#print Movie
	Dir_DB[Director].add(Movie)
	return Director

def ProcessMovie(Line, Dir):
	#Whole = Line.lower().split('(')[0].strip()
	#W = Whole.partition('\t')
	Mv = Line.lower().split('(')[0].strip()
	Movie = re.sub('[%s]' % re.escape('"'), ' ', Mv)
	#print Movie, Dir, '\n'
	Dir_DB[Dir].add(Movie)


def Genre():
	LineNo = 140850
	while (LineNo != 1538523):
		Line = linecache.getline('genres.list', LineNo)
		ProcessLine(Line)
		LineNo += 1
	
def Dirs():
	Dir = ()
	LineNo = 474
	while (LineNo != 1996522):
		Line = linecache.getline('directors.list', LineNo)
		if Line != '\n':
			ProcessMovie(Line, Dir)
		if Line == '\n':
			LineNo += 1
			Line = linecache.getline('directors.list', LineNo)
			Dir = ProcessDir(Line)
		
		LineNo += 1
	
	
def main():
	
	Genre()
	print len(Movie_DB)
	Dirs()
	print len(Dir_DB)
	
	count = 0
	
	for movies in Dir_DB.values():
		if movies in Movie_DB.keys():
			count += 1


	print count












if __name__ == '__main__':
  main()
