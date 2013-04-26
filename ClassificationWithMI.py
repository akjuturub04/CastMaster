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

from sys import argv

def log2(x):
  return math.log10(x)/math.log10(2)
  #return math.log(x, 2)

def getTermDict(corpus, my_category):
  l = []
  counter = {}
  for item1 in my_category:
    for item2 in corpus:
      if corpus[item2][1][1] == item1:
        l += re.split(r'[\(\)\{\}\@\$\#\%\^\&\+\=\<\>\!\?\[\]\-\,\.\\\'\"\:\;\|\r\b\t\n\s+\W+]', corpus[item2][0].lower())

    counter[item1] = collections.Counter(l)
    del counter[item1]['']

  return counter

def totalnumoftokens(dict):
  val = 0
  B = 0
  for item in dict:
    val += dict[item]
    B += 1

  return val + B

# Feature selection using mutual information
def feature_selection(termsinvocab, training_dict, classes):

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

  for myclass in classes:
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

def NaiveBayes_Training(mydict, termsinvocab, classes, termsinaclass):

  prior = {}
  condprob = defaultdict(dict)
  for item in classes:
    prior[item] = 1.0/3
    #for term in termsinvocab:
    for term in termsinaclass[item]:
      if term in mydict[item]:
        #if MIScore[term][item] > 0.000010005:
        condprob[term][item] = (mydict[item][term] + 1.0)/(totalnumoftokens(mydict[item]))
      else:
        #if MIScore[term][item] > 0.000010005:
        condprob[term][item] = (1.0)/(totalnumoftokens(mydict[item]))

  return condprob

def NaiveBayes_Testing(testing_dict, category_set, condprob):
  initialDict = {}
  result = {}
  score = defaultdict(dict)
  #for item1 in testing_dict:
  for item2 in category_set:
    for item3 in testing_dict:
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

def calculate_F1(mydict, classes):
  tp = 0.0
  fp = 0.0
  tn = 0.0
  fn = 0.0
  for item1 in classes:
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

  filename1 = "/home/deepthi/deepthi/test/IR/hw3/data1.pkl"
  file = gzip.GzipFile(filename1, 'rb')
  training_dict = cPickle.load(file)

  filename2 = "/home/deepthi/deepthi/test/IR/hw3/data2.pkl"
  file = gzip.GzipFile(filename2, 'rb')
  testing_dict = cPickle.load(file)

  training_set = ["bing", "amazon", "twitter", "yahoo", "google", "beyonce", "bieber", "television", "movies", "music", "obama", "america", "congress", "senate", "lawmakers"]
  testing_set = ["apple", "facebook", "westeros", "gonzaga", "banana"]
  classes = ["rt_Entertainment", "rt_Business", "rt_Politics"]

  mydict = {}
  mydict = getTermDict(training_dict, classes)

  termsinvocab = []
  for item in mydict:
    termsinvocab += mydict[item].keys()
  termsinvocab = list(set(termsinvocab))
  #termsinvocab = [w for w in termsinvocab if not w in stopwords.words('english')]

  MIScore = {}
  MIScore = feature_selection(termsinvocab, training_dict, classes)
  #for item in MIScore:
  #  print item, MIScore[item]
  newdict = {}
  for item1 in MIScore:
    for item2 in classes:
      newdict.setdefault(item2, []).append(MIScore[item1][item2])

  avg = {}
  for item in newdict:
    #avg[item] = np.mean(newdict[item])*(15.0/8)
    mylist = sorted(newdict[item], reverse=True)
    #myindex = len(mylist)
    myindex =  3500
    avg[item] = mylist[myindex]
    

  termsinaclass = {}
  for item1 in classes:
    for item2 in MIScore:
      if MIScore[item2][item1] < avg[item1]:
        termsinaclass.setdefault(item1, []).append(item2)

  condprob = {}
  condprob = NaiveBayes_Training(mydict, termsinvocab, classes, termsinaclass)

  #for item in condprob:
  #  print item, condprob[item]

  result = {}
  result = NaiveBayes_Testing(testing_dict, classes, condprob)

  for item in result:
    #if result[item][0] != result[item][1]:
    print item, result[item]

  myf1 = calculate_F1(result, classes)
  print "F1 is: ", myf1

if __name__ == '__main__':
  main()
