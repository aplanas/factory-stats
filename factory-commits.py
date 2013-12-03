#!/usr/bin/python
# Copyright (c) 2013 SUSE Linux Products GmbH
# Author: Ludwig Nussel
# Author: Stephan Kulow
#
# ./factory-commits.py --users=users openSUSE:Factory
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

try:
    import osc.conf
    import osc.core
    import osc.oscerr
except ImportError, e:
    print "*** need osc installed!"
    raise

import signal

from pprint import pprint
import os, sys, re
import logging
import optparse

try:
    from xml.etree import cElementTree as ET
except ImportError:
    import cElementTree as ET

parser = optparse.OptionParser()
parser.add_option("--debug", action="store_true", help="debug output")
parser.add_option("--verbose", action="store_true", help="verbose")
parser.add_option("--apiurl", help="obs api url")
parser.add_option("--users", metavar="FILE", help="cache users in file")

(options, args) = parser.parse_args()

if not options.users:
    print "need --users"
    sys.exit(1)

osc.conf.get_config()

logging.basicConfig()

logger = logging.getLogger("weekly")

if (options.debug):
    logger.setLevel(logging.DEBUG)
    osc.conf.config['http_debug'] = True
elif (options.verbose):
    logger.setLevel(logging.INFO)

if not options.apiurl:
    apiurl = osc.conf.config['apiurl']
else:
    apiurl = options.apiurl

def alarmhandler(signum, frame):
    logger.error("exit due to timeout")
    sys.exit(1)

if options.users and os.path.exists(options.users):
    import pickle
    f = open(options.users, 'rb')
    users = pickle.load(f)
else:
    users = {}

mainprj = args[0]
devel_packages = {}

url = osc.core.makeurl(apiurl, ['search','package'], "match=[@project='%s']" % mainprj)
f = osc.core.http_GET(url)
root = ET.parse(f).getroot()
for p in root.findall('package'):
    name = p.attrib['name']
    d = p.find('devel')
    if d != None:
        dprj = d.attrib['project']
        #if not dprj.startswith('devel:'): continue
        pkgs = devel_packages.get(dprj, [])
        pkgs.append(d.attrib['package'])
        devel_packages[dprj] = pkgs

prjs = devel_packages.keys()
prjs.append(mainprj)

import feedparser, time
from datetime import datetime
from datetime import timedelta

requests_to_check = set()
authors={}

for prj in set(prjs):
    url = osc.core.makeurl(apiurl, ['project', 'latest_commits', prj])
    f = osc.core.http_GET(url)
    d = feedparser.parse(f)
    for entry in d.entries:
        if entry.author == 'buildservice-autocommit': 
            continue
        v = "<div>" + entry.content[0].value + "</div>"
        e = ET.fromstring(v.encode('utf-8'))
        e = e.find('dl')
        list1 = [x.text for x in e.findall('dt')]
        list2 = []
        for x in e.findall('dd'):
            a = x.find('.//a')
            if a != None:
                list2.append(a.text)
            else:
                list2.append(x.text)
        infos = dict(zip(list1, list2))
        # ignore all packages not devel package
        if prj != mainprj and not infos['Package'] in devel_packages[prj]:
            continue
        # ignore old stuff
        if (datetime.now() - datetime.fromtimestamp(time.mktime(entry.published_parsed))) > timedelta(7):
            continue
        # ignore everything in factory that ended up there as request
        if prj == mainprj and infos['Request'] != None:
            continue
        #print prj, infos['Package'], infos['Request'], entry.author
        if infos['Request'] != None:
            requests_to_check.add(infos['Request'])
        else:
            count = authors.get(entry.author, 0)
            authors[entry.author] = count + 1
                        

for r in requests_to_check:
  url = osc.core.makeurl(apiurl, ['request', r])
  r = ET.parse(osc.core.http_GET(url))
  creator=None
  for h in r.findall('history'):
      creator=h.attrib['who'] # last one wins
  count = authors.get(creator, 0)
  authors[creator] = count + 1

for u in authors.keys():
    if not u in users:
        url = osc.core.makeurl(apiurl, ['person', str(u)])
        print url
        f = osc.core.http_GET(url)
        
        tree = ET.ElementTree()
        tree.parse(f)
        users[u] = '%s <%s>'%(tree.find("realname").text, tree.find("email").text)
    
if options.users:
    import pickle
    f = open(options.users, 'wb')
    pickle.dump(users, f)

authors = sorted(authors.items(), key=lambda x: x[1])
for author in authors:
  print users[author[0]], author[1]
