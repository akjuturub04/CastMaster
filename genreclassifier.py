#!/usr/bin/python -tt

import json
import math
import operator
import numpy as np
import unicodedata
import collections
from collections import defaultdict
import re, cPickle
import gzip
import shlex
from os import listdir
from os.path import isfile, join
import requests
import random
from collections import Counter
from collections import namedtuple
import itertools
import sys
from sys import argv

genreTuple = namedtuple('genreTuple', ['value', 'g'])
directorTuple = namedtuple('directorTuple', ['score', 'name'])

def log2(x):
  return math.log10(x)/math.log10(2)
  #return math.log(x, 2)

def getTermDict(corpus, my_category):
  genreDict = {}
  for genre in my_category:
    genreDict[genre] = Counter()
  for id in corpus:
    l = re.split(r'[\(\)\{\}\@\$\#\%\^\&\+\=\<\>\!\?\[\]\-\,\.\\\'\"\:\;\|\r\b\t\n\s+\W+]', corpus[id]["synopsis"].lower())
    for word in l:
      if word != '':
        if 'genres' in corpus[id]:
          for genre in corpus[id]['genres']:
            if genre in my_category:
              genreDict[genre][word] += 1 

  return genreDict

def totalnumoftokens(dict):
  val = 0
  B = 0
  for item in dict:
    val += dict[item]
    B += 1

  return val + B

#def NaiveBayes_Training(mydict, termsinvocab, genres, termsinaclass):
def NaiveBayes_Training(mydict):
  condprob = defaultdict(dict)
  for genre in mydict:
    total = (totalnumoftokens(mydict[genre]))
    for word in mydict[genre]:
      if word not in condprob:
        condprob[word] = defaultdict(float)
      condprob[word][genre] = float(mydict[genre][word])/total

  return condprob


def genreVectors(genres):
  result = set()
  for i in range(3):
    tl = itertools.combinations(genres, i+1)
    for e in tl:
      result.add(e)
  return result

def classify(genrevector, condprob, synopsis):

  l = re.split(r'[\(\)\{\}\@\$\#\%\^\&\+\=\<\>\!\?\[\]\-\,\.\\\'\"\:\;\|\r\b\t\n\s+\W+]', synopsis.lower()) 
  sortlist = []
  for elem in genrevector:
    resultval = 1.0
    for word in l:
      if word in condprob:
        tempval = 0.0
        for genre in elem:
          genlen = len(elem)
          if genre in condprob[word]:
            tempval += condprob[word][genre]
        tempval = float(tempval)/genlen
        resultval *= tempval

    #sortlist.append(genreTuple(g=genrevector, value = resultval))
    sortlist.append(genreTuple(value = resultval, g=elem))

  sortlist = sorted(sortlist, reverse=True)
  result = set()
  for genre in sortlist[0].g:
    result.add(genre)
  for genre in sortlist[1].g:
    result.add(genre)

  #return sorted(sortlist, reverse=True)
  return result

def directorsRanking(training_dict, genres):
  directorCount = Counter()
  directorScore = Counter()

  for id in training_dict:
    year = training_dict[id]['year']
    score = float(training_dict[id]['ratings']['critics_score'])
    categories = training_dict[id]['genres']
    for director in training_dict[id]['abridged_directors']:
      director = str(director)
      if director not in directorCount:
        directorCount[director] = Counter()
        directorScore[director] = Counter()
      if year not in directorScore[director]:
        directorScore[director][year] = defaultdict(float)
      directorCount[director][year] += 1
      #directorCount[director][year]['total'] += 1
      for category in categories:
        category = str(category)
        if category in genres:
          #if category != 'total':
            #if category not in directorScore[director][year]:
              #directorCount[director][year][category] = Counter()
              #directorScore[director][year][category] = defaultdict(float)
            directorScore[director][year][category] += score
            #directorCount[director][year][category] += 1

  for director in directorScore:
    minyear = min(directorScore[director].keys())
    maxyear = max(directorScore[director].keys())
    for year in range(minyear, maxyear+1):
      if year not in directorScore[director]:
        directorScore[director][year] = defaultdict(float)
#    for year in directorScore[director]:
      for category in directorScore[director][year]:
        #if category != 'total':
          directorScore[director][year][category] = float(directorScore[director][year][category])/directorCount[director][year]
          #directorScore[director][year][category] *= float(directorCount[director][year][category])/directorCount[director][year]['total']
  
  param1 = 0.9
  paramPrev = 0.4
  paramPresent = 0.6

  for director in directorScore:
    #yearlist = sorted(directorScore[director].keys())
    minyear = min(directorScore[director].keys())
    maxyear = max(directorScore[director].keys())
    #for year in yearlist:
    for year in range(minyear, maxyear+1):
      yearset = set()
      for category in directorScore[director][year]:
        yearset.add(category)

      if (year-1) in directorScore[director]:
        for category in directorScore[director][(year-1)]:
          yearset.add(category)

      #for category in directorScore[director][year]:
      for category in yearset:
        if (year - 1) in directorScore[director]:
          if category in directorScore[director][year - 1]:
            if category in directorScore[director][year]:
              directorScore[director][year][category] = paramPrev*directorScore[director][year-1][category] + paramPresent*directorScore[director][year][category]
            else:
              directorScore[director][year][category] = param1*directorScore[director][year-1][category]
          else:
            directorScore[director][year][category] *= param1
        else:
          directorScore[director][year][category] *= param1
     
  #for director in directorScore:
  #  print director, directorScore[director]

  return directorScore

def bestDirector(directorScore, inputYear, mygenres):
  resultlist = []
  inputYear = int(inputYear)
  for director in directorScore:
    tempval = 0.0
    if inputYear in  directorScore[director]:
      #tempval = 0.0
      for genre in mygenres:
        tempval += directorScore[director][inputYear][genre]
    resultlist.append(directorTuple(score = tempval, name= director))

  resultlist = sorted(resultlist, reverse=True)
  
  directorlist = []
  for i in range(5):
    #directorlist.append(resultlist[i].name)
    directorlist.append(resultlist[i])
  return directorlist
  
  
def calculate_F1(mydict, genres):
  tp = 0.0
  fp = 0.0
  tn = 0.0
  fn = 0.0
  for item1 in genres:
    for item2 in mydict:
      if mydict[item2][0] == item1 and mydict[item2][1] == item1:
        tp += 1
      elif mydict[item2][0] == item1 and mydict[item2][1] != item1:
        fp += 1
      elif mydict[item2][0] != item1 and mydict[item2][1] == item1: 
        fn += 1
      elif mydict[item2][0] != item1 and mydict[item2][1] != item1:
        tn += 1
  val1 = tp + fp
  val2 = tp + fn
  p = tp/val1
  r = tp/val2

  f1 = (2*p*r)/(p+r)

  return f1

def main():

  filename1 = "/home/deepthi/deepthi/test/IR/project/picklefiles/MovieData"
  file = open(filename1, 'r')
  training_dict = cPickle.load(file)

  #filename2 = "/home/deepthi/deepthi/test/IR/project/picklefiles/testingPickle.pkl"
  #file = open(filename2, 'r')
  #testing_dict = cPickle.load(file)

  genres = ['Science Fiction & Fantasy', 'Mystery & Suspense', 'Romance', 'Kids & Family', 'Animation', 'Comedy', 'Horror', 'Drama', 'Action & Adventure']

  mydict = {}
  mydict = getTermDict(training_dict, genres)
  
  STOPWORDS = ['a','able','about','across','after','all','almost','also','am','among', 'an','and','any','are','as','at','be','because','been','but','by','can', 'cannot','could','dear','did','do','does','either','else','ever','every', 'for','from','get','got','had','has','have','he','her','hers','him','his', 'how','however','i','if','in','into','is','it','its','just','least','let', 'like','likely','may','me','might','most','must','my','neither','no','nor', 'not','of','off','often','on','only','or','other','our','own','rather','said', 'say','says','she','should','since','so','some','than','that','the','their', 'them','then','there','these','they','this','tis','to','too','twas','us', 'wants','was','we','were','what','when','where','which','while','who', 'whom','why','will','with','would','yet','you','your'] 

  termsinvocab = set()
  for genre in mydict:
    for word in mydict[genre]:
      termsinvocab.add(word)

  for word in STOPWORDS:
    if word in termsinvocab:
      termsinvocab.remove(word)

  condprob = {}
  condprob = NaiveBayes_Training(mydict)

  print 'Enter a query (format: \"<synopsis>\" <year> or quit to exit):'
  query = raw_input()
  while query != "quit":
    queryString = re.split(r'[\"]', query)
    i = 0
    for elem in queryString:
      if elem == '':
        del queryString[i]
      i += 1
    if len(queryString) == 2:
        r = genreVectors(genres)
        synopsis = queryString[0]
        mygenres = classify(r, condprob, synopsis)
        directorScore = directorsRanking(training_dict, mygenres)
        inputYear = queryString[1]
        myBestDirectors = bestDirector(directorScore, inputYear, mygenres)
        for item in myBestDirectors:
          print item

        print 'Enter a query:'
        query = raw_input()
    else:
      print "Syntax Error: Please enter a query of the format: \"<synopsis>\" <year>:"
      query = raw_input()

if __name__ == '__main__':
  main()
