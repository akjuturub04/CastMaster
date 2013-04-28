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


def main():

  filename1 = "/home/deepthi/deepthi/test/IR/project/picklefiles/MovieData"
  file = open(filename1, 'r')
  training_dict = cPickle.load(file)

  genres = ['Science Fiction & Fantasy', 'Mystery & Suspense', 'Romance', 'Kids & Family', 'Animation', 'Comedy', 'Horror', 'Drama', 'Action & Adventure']

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
     
  for director in directorScore:
    print director, directorScore[director]
    

if __name__ == '__main__':
  main()

