#!/usr/bin/python
# Copyright (c) 2013 SUSE Linux Products GmbH
# Author: Ludwig Nussel
#
# ./weekly.py --pickle=factory --users=users openSUSE:Factory
# ./weekly.py --pickle=factory --users=users --verbose openSUSE:Factory
# ./weekly.py --pickle=factory openSUSE:Factory --users=users --split > weekly.dat && gnuplot weekly.plot
# ./weekly.py --pickle=factory openSUSE:Factory --users=users --split --mathplot
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

def check_date(option, opt_str, value, parser):
    r = re.compile(r'\d{4}-\d{2}-\d{2}')
    if not r.match(value):
        raise optparse.OptionValueError("%s must be in format YYYY-MM-DD"%opt_str)
    setattr(parser.values, option.dest, value)

parser = optparse.OptionParser()
parser.add_option("--dry", action="store_true", help="dry run")
parser.add_option("--debug", action="store_true", help="debug output")
parser.add_option("--verbose", action="store_true", help="verbose")
parser.add_option("--peruser", action="store_true", help="peruser")
parser.add_option("--split", action="store_true", help="split")
parser.add_option("--mathplot", action="store_true", help="use mathplot")
parser.add_option("--apiurl", help="obs api url")
parser.add_option("--pickle", metavar="FILE", help="serialize and load from file")
parser.add_option("--users", metavar="FILE", help="cache users in file")
parser.add_option("--timeout", action="store", type='int', help="timeout in seconds")
parser.add_option("--not-before", type='string', metavar="DATE",
        help="don't print dates before this date",
        action='callback', callback=check_date)
parser.add_option("--not-after", type='string', metavar="DATE",
        help="don't print dates after this date",
        action='callback', callback=check_date)

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

if options.timeout:
    signal.signal(signal.SIGALRM, alarmhandler)
    signal.alarm(options.timeout)

if options.pickle and os.path.exists(options.pickle):
    import pickle
    f = open(options.pickle, 'rb')
    data = pickle.load(f)
else:
    data = None

if options.users and os.path.exists(options.users):
    import pickle
    f = open(options.users, 'rb')
    users = pickle.load(f)
else:
    users = {}

if data is None:
    prj = args[0]
    url = osc.core.makeurl(apiurl, ['statistics', 'active_request_creators',prj], query={ 'raw' : '1'})
    f = osc.core.http_GET(url)
    import json
    data = json.load(f)

#if options.debug:
#    pprint(data)

if options.pickle and not os.path.exists(options.pickle):
    import pickle
    f = open(options.pickle, 'wb')
    pickle.dump(data, f)

from datetime import date, timedelta, datetime
from collections import defaultdict
lastdate = None
weekly = {}

if options.not_before is not None:
    not_before_year, not_before_month, not_before_day = ( int(i) for i in options.not_before.split('-') )
else:
    not_before_year, not_before_month, not_before_day = (None, None, None)
if options.not_after is not None:
    not_after_year, not_after_month, not_after_day =  ( int(i) for i in options.not_after.split('-') )
else:
    not_after_year, not_after_month, not_after_day = (None, None,None)



acc = {}
for i in data:
    d = i['created_at'].split('T')[0].split('-')
    d = [ int(j) for j in d ]

    if not_before_year is not None:
        if d[0] < not_before_year:
            continue
        if d[0] == not_before_year and d[1] < not_before_month:
            continue
        if d[0] == not_before_year and d[1] < not_before_month:
            continue
        if d[0] == not_before_year and d[1] == not_before_month and d[2] < not_before_day:
            continue
    if not_after_year is not None:
        if d[0] > not_after_year:
            continue
        if d[0] == not_after_year and d[1] > not_after_month:
            continue
        if d[0] == not_after_year and d[1] == not_after_month and d[2] == not_after_day:
            continue

    u = i['creator']

    if not u in users:
        url = osc.core.makeurl(apiurl, ['person', str(u)])
        print url
        f = osc.core.http_GET(url)
        
        tree = ET.ElementTree()
        tree.parse(f)
        users[u] = '%s <%s>'%(tree.find("realname").text, tree.find("email").text)
    
    u = users[u]
    acc[u] = acc.get(u, 0) + 1



if options.users:
    import pickle
    f = open(options.users, 'wb')
    pickle.dump(users, f)

# print "Total", len(acc)
# if acc is not None:
#     top = sorted(((v, k) for k, v in acc.iteritems()), reverse=True)[:100]
#     f = open('total.csv', 'w')
#     for t in top:
#         print >>f, (u'%s, %s'%(t[1], t[0])).encode('utf-8')


# sys.exit(1)
    


for i in data:
    d = i['created_at'].split('T')[0].split('-')
    d = [ int(j) for j in d ]

    if not_before_year is not None:
        if d[0] < not_before_year:
            continue
        if d[0] == not_before_year and d[1] < not_before_month:
            continue
    if not_after_year is not None:
        if d[0] > not_after_year:
            continue
        if d[0] == not_after_year and d[1] > not_after_month:
            continue

    d = date(d[0], d[1], d[2])
    d = d + timedelta(6-d.weekday()) # accumulate on sunday
    d = d.isoformat()
    u = i['creator']

    if not u in users:
        url = osc.core.makeurl(apiurl, ['person', str(u)])
        print url
        f = osc.core.http_GET(url)
        
        tree = ET.ElementTree()
        tree.parse(f)
        users[u] = '%s <%s>'%(tree.find("realname").text, tree.find("email").text)
    
    u = users[u]

    t = weekly.get(d, {})
    n = t.get(u, 0) + 1
    t[u] = n
    weekly[d] = t

if options.users:
    import pickle
    f = open(options.users, 'wb')
    pickle.dump(users, f)

if weekly is not None:
    yaxis1 = []
    yaxis2 = []
    yaxis3 = []
    for d in sorted(weekly.keys()):
        contribs = weekly[d]
        top = sorted(((v, k) for k, v in contribs.iteritems()), reverse=True)[:20]
        f = open(d+'.csv', 'w')
        for t in top:
            print >>f, (u'%s, %s'%(t[1], t[0])).encode('utf-8')
