#!/usr/bin/env python
'''github-pr-stats

Usage:
   github-pr-stats <user> <repo>
   github-pr-stats (-h | --help)

Options:
   -h --help           Show this screen.
'''

# May you recognize your weaknesses and share your strengths.
# May you share freely, never taking more than you give.
# May you find love and love everyone you find.

from __future__ import division

import signal
import sys
from collections import defaultdict

from ascii_graph import Pyasciigraph
from docopt import docopt
from envoy import run
from github3 import authorize, login, GitHub
from numpy import array, median

# Stack traces are ugly; why would we want to print one on ctrl-c?
def nice_sigint(signal, frame):
   print("")
   sys.exit(0)
signal.signal(signal.SIGINT, nice_sigint)

arguments = docopt(__doc__)

# Use a stored OAuth token so we don't have to ask for the user's password
# every time (or save the password on disk!).
token = run('git config --global github-pr-stats.token').std_out.strip()
if not token:
   from getpass import getpass
   user = password = ''

   while not user:
      user = raw_input('Username: ')
   while not password:
      password = getpass('Password: ')

   auth = authorize(user, password,
                    scopes=['repo'],
                    note='github-pr-stats',
                    note_url='https://github.com/xiongchiamiov/github-pr-stats')
   token = auth.token
   # We need to un-unicode token for now.
   # https://github.com/kennethreitz/envoy/issues/34
   run("git config --global github-pr-stats.token '%s'" % str(token))
gh = login(token=token)

repo = gh.repository(arguments['<user>'], arguments['<repo>'])
stats = {
   'count': 0,
   'merged': 0,
   'daysOpen': [],
   'daysOpenHistogram': defaultdict(int),
}
for pr in repo.iter_pulls(state='closed'):
   daysOpen = (pr.closed_at - pr.created_at).days
   print '#%s (%s): %s - %s (%s days)' \
       % (pr.number, pr.is_merged(), pr.created_at, pr.closed_at, daysOpen)
   stats['count'] += 1
   if pr.is_merged():
      stats['merged'] += 1
   stats['daysOpen'].append(daysOpen)
   stats['daysOpenHistogram'][daysOpen] += 1

percentageMerged = round(100 - (stats['count'] / stats['merged']), 2)
print '%s%% (%s of %s) closed pulls merged.' % (percentageMerged, stats['merged'], stats['count'])

# It'd be a lot nicer to do these calculations using
# http://www.python.org/dev/peps/pep-0450/ or even
# https://pypi.python.org/pypi/stats/ instead of the
# sometimes-difficult-to-install Numpy.  But alas, we're stuck with that for
# Python 2.x.
daysOpen = array(stats['daysOpen'])
mean = daysOpen.mean()
median = median(daysOpen) # I don't know why narray doesn't have this as a method.
stdDev = daysOpen.std()
min = daysOpen.min()
max = daysOpen.max()
print 'Days open: %s (mean) %s (median) %s (std. dev.) %s (min) %s (max)' \
    % (mean, median, stdDev, min, max)

# Touch every value in the range to ensure the defaultdict counts them as
# keys.  This allows us to make a histogram without gaps.
for i in range(min, max):
   stats['daysOpenHistogram'][i]

# Work around a bug in ascii_graph.
# https://github.com/kakwa/py-ascii-graph/issues/3
daysOpenHistogram = [(str(key), value) \
                     for (key, value) \
                     in stats['daysOpenHistogram'].items()]
graph = Pyasciigraph()
for line in graph.graph('', daysOpenHistogram):
   print line

