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

#feature selection using mutual information
def feature_selection(termsinvocab, training_dict, genres):

  mydict = {}
  classdict = {}
  result = defaultdict(dict)
  N = float(len(training_dict))
  for term in termsinvocab:
    tempdict = {}
    for item in training_dict:
      if term.lower() in (training_dict[item][0]).lower():
        tempdict.setdefault(item, training_dict[item][1][1])
    mydict.setdefault(term, tempdict)

  for item in training_dict:
    classdict.setdefault(training_dict[item][1][1], []).append(item)

  for myclass in genres:
    for term in mydict:
      N11 = 0.0
      N10 = 0.0
      N01 = 0.0
      N00 = 0.0
      for item in mydict[term]:
        if myclass == mydict[term][item]:
          N11 += 1.0
        else:
          N10 += 1.0
      for item1 in classdict[myclass]:
        if item1 not in mydict[term].keys():
          N01 += 1.0
      N00 = N - N11 - N10 - N01
      N1x = N10 + N11
      Nx1 = N01 + N11
      N0x = N00 + N01
      Nx0 = N10 + N00
    
      if N11 != 0.0 and N10 != 0.0 and N01 != 0.0 and N00 != 0.0 and N1x != 0.0 and Nx1 != 0.0 and N0x != 0.0 and Nx0 != 0.0:
        result[term][myclass] = (N11/N)*log2((N*N11)/(N1x*Nx1)) + (N01/N)*log2((N*N01)/(N0x*Nx1)) + (N10/N)*log2((N*N10)/(N1x*Nx0)) + (N00/N)*log2((N*N00)/(N0x*Nx0))
      else:
        result[term][myclass] = (N11/N)*log2((1+N*N11)/(1+N1x*Nx1)) + (N01/N)*log2((1+N*N01)/(1+N0x*Nx1)) + (N10/N)*log2((1+N*N10)/(1+N1x*Nx0)) + (N00/N)*log2((1+N*N00)/(1+N0x*Nx0))

  return result

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

def lambdavalues(movie_genres, genres):
  lambdaDict = {}
  for item1 in movie_genres:
    for item2 in genres:
      if item2 in movie_genres[item1]:
        lambdaDict.setdefault(item, []).append("1")
      else:
        lambdaDict.setdefault(item, []).append("0")

  return lambdaDict

def PPMI(condprob, termsinvocab, genres, mydict, lambdaDict):
  pmmiDict = defaultdict(dict)
  for item in termsinvocab:
    for key in mydict:
      tempval = 0.0
      for val in genres:
        tempval += lambdaDict[key][val] * condprob[item][val]
      pmmiDict[item][key] = tempval
      
def NaiveBayes_Testing(testing_dict, category_set, condprob, STOPWORDS):
  initialDict = {}
  result = {}
  score = defaultdict(dict)
  #for item1 in testing_dict:
  for item2 in category_set:
    for item3 in testing_dict:
      if item3 not in STOPWORDS:
      #initialDict.setdefault(item3, item2)
        initialDict.setdefault(item3, testing_dict[item3][1][1])
        l = re.split(r'[\(\)\{\}\@\$\#\%\^\&\+\=\<\>\!\?\[\]\-\,\.\\\'\"\:\;\|\r\b\t\n\s+\W+]', testing_dict[item3][0].lower())
      #l = list(set(l))
        for item5 in category_set:
          score[item3][item5] = log2(0.33)
          for item4 in l:
            if item4 in condprob and item5 in condprob[item4]:
            #score[item3][item5] *= condprob[item4][item5]
              score[item3][item5] += log2(condprob[item4][item5])
          score[item3][item5] *= 0.33
  myclass = defaultdict(list)

  for item in score:
    maximum = max(score[item].values())
    for items in score[item]:
      if score[item][items] == maximum:
        #myclass[item] = items
        myclass.setdefault(item, []).append(items)
        myclass.setdefault(item, []).append(initialDict[item])
  return myclass

def genreVectors(genres):
  result = set()
  for i in range(len(genres)):
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
  
  return sorted(sortlist, reverse=True)
  #return max(sortlist)
  
     
     
        

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
  #tmptermsinvocab = list(set(termsinvocab)) 

  for word in STOPWORDS:
    if word in termsinvocab:
      termsinvocab.remove(word)

  #termsinvocab = [w for w in termsinvocab if not w in stopwords.words('english')]

  #MIScore = {}
  #MIScore = feature_selection(termsinvocab, training_dict, genres)
  #for item in MIScore:
  #  print item, MIScore[item]
  #newdict = {}
  #for item1 in MIScore:
  #  for item2 in genres:
  #    newdict.setdefault(item2, []).append(MIScore[item1][item2])

  #avg = {}
  #for item in newdict:
  #  #avg[item] = np.mean(newdict[item])*(15.0/8)
  #  mylist = sorted(newdict[item], reverse=True)
  #  #myindex = len(mylist)
  #  myindex = 4000
  #  avg[item] = mylist[myindex]
    

  #termsinaclass = {}
  #for item1 in genres:
  #  for item2 in MIScore:
  #    if MIScore[item2][item1] < avg[item1]:
  #      termsinaclass.setdefault(item1, []).append(item2)

  condprob = {}
  #condprob = NaiveBayes_Training(mydict, termsinvocab, genres, termsinaclass)
  condprob = NaiveBayes_Training(mydict)

  #for item in condprob:
  #  print item, condprob[item]

  r = genreVectors(genres)
  #for item in r:
  #  print item

  #synopsis = "Pixar returns to their first success with Toy Story 3. The movie begins with Andy leaving for college and donating his beloved toys -- including Woody (Tom Hanks) and Buzz (Tim Allen) -- to a daycare. While the crew meets new friends, including Ken (Michael Keaton), they soon grow to hate their new surroundings and plan an escape. The film was directed by Lee Unkrich from a script co-authored by Little Miss Sunshine scribe Michael Arndt. ~ Perry Seibert, Rovi "
 
  synopsis = "Batman raises the stakes in his war on crime. With the help of Lieutenant Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the city streets. The partnership proves to be effective, but they soon find themselves prey to a reign of chaos unleashed by a rising criminal mastermind known to the terrified citizens of Gotham as The Joker."

  #synopsis = "A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers"

  #synopsis = "Christopher Nolan steps back into the director's chair for this sequel to Batman Begins, which finds the titular superhero coming face to face with his greatest nemesis -- the dreaded Joker. Christian Bale returns to the role of Batman, Maggie Gyllenhaal takes over the role of Rachel Dawes (played by Katie Holmes in Batman Begins), and Brokeback Mountain star Heath Ledger dons the ghoulishly gleeful Joker makeup previously worn by Jack Nicholson and Cesar Romero. Just as it begins to appear as if Batman, Lt. James Gordon (Gary Oldman), and District Attorney Harvey Dent (Aaron Eckhart) are making headway in their tireless battle against the criminal element, a maniacal, wisecracking fiend plunges the streets of Gotham City into complete chaos. ~ Jason Buchanan, Rovi"

  synopsis = sys.argv[1]

  rTuple = classify(r, condprob, synopsis)
  for item in rTuple:
    print item


#  lambdaDict = lambdavalues(movie_genres, genres) 
#
#  PMMIDict = {}

#  PMMIDict = PPMI(condprob, termsinvocab, genres, mydict, lambdaDict)
#
#  result = {}
#  result = NaiveBayes_Testing(testing_dict, genres, condprob, STOPWORDS)
#
#  for item in result:
#    #if result[item][0] != result[item][1]:
#    print item, result[item]
#
#  myf1 = calculate_F1(result, genres)
#  print "F1 is: ", myf1

if __name__ == '__main__':
  main()
