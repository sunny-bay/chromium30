#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Closes tree if configured masters have failed tree-closing steps.

Given a list of masters, gatekeeper_ng will get a list of the latest builds from
the specified masters. It then checks if any tree-closing steps have failed, and
if so closes the tree and emails appropriate parties. Configuration for which
steps to close and which parties to notify are in a local gatekeeper.json file.
"""

from contextlib import closing
import datetime
import getpass
import hashlib
import hmac
import itertools
import json
import logging
import multiprocessing
import operator
import optparse
import os
import random
import re
import sys
import urllib
import urllib2

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', '..')

# Buildbot status enum.
SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(6)


def get_pwd(password_file):
  if os.path.isfile(password_file):
    return open(password_file, 'r').read().strip()
  return getpass.getpass()


def update_status(tree_message, tree_status_url, username, password):
  """Connects to chromium-status and closes the tree."""
  #TODO(xusydoc): append status if status is already closed.
  params = urllib.urlencode({
      'message': tree_message,
      'username': username,
      'password': password
  })

  # Standard urllib doesn't raise an exception on 403, urllib2 does.
  f = urllib2.urlopen(tree_status_url, params)
  f.close()
  logging.info('success')


def get_root_json(master_url):
  """Pull down root JSON which contains builder and build info."""
  logging.info('opening %s' % (master_url + '/json'))
  with closing(urllib2.urlopen(master_url + '/json')) as f:
    return json.load(f)


def find_new_builds(master_url, root_json, build_db):
  """Given a dict of previously-seen builds, find new builds on each builder.

  Note that we use the 'cachedBuilds here since it should be faster, and this
  script is meant to be run frequently enough that it shouldn't skip any builds.

  'Frequently enough' means 1 minute in the case of Buildbot or cron, so the
  only way for gatekeeper_ng to be overwhelmed is if > cachedBuilds builds
  complete within 1 minute. As cachedBuilds is scaled per number of slaves per
  builder, the only way for this to really happen is if a build consistently
  takes < 1 minute to complete.
  """
  new_builds = {}
  build_db[master_url] = build_db.get(master_url, {})
  for buildername, builder in root_json['builders'].iteritems():
    candidate_builds = set(builder['cachedBuilds'] + builder['currentBuilds'])
    if buildername in build_db[master_url]:
      new_builds[buildername] = [x for x in candidate_builds
                                 if x > build_db[master_url][buildername]]
    else:
      new_builds[buildername] = candidate_builds

    # This is a heuristic, as currentBuilds may become completed by the time we
    # scan them. The buildDB is fixed up later to account for this.
    completed = set(builder['cachedBuilds']) - set(builder['currentBuilds'])
    if completed:
      build_db[master_url][buildername] = max(completed)

  return new_builds


def find_new_builds_per_master(masters, build_db):
  """Given a list of masters, find new builds and collect them under a dict."""
  builds = {}
  master_jsons = {}
  for master in masters:
    root_json = get_root_json(master)
    master_jsons[master] = root_json
    builds[master] = find_new_builds(master, root_json, build_db)
  return builds, master_jsons


def get_build_json(url_pair):
  url, master = url_pair
  logging.debug('opening %s...' % url)
  with closing(urllib2.urlopen(url)) as f:
    return json.load(f), master


def get_build_jsons(master_builds, build_db, processes):
  """Get all new builds on specified masters.

  This takes a dict in the form of [master][builder][build], formats that URL
  and appends that to url_list. Then, it forks out and queries each build_url
  for build information.
  """
  pool = multiprocessing.Pool(processes=processes)
  url_list = []
  for master, builder_dict in master_builds.iteritems():
    for builder, new_builds in builder_dict.iteritems():
      for build in new_builds:
        safe_builder = urllib.quote(builder)
        url = master + '/json/builders/%s/builds/%s' % (safe_builder, build)
        url_list.append((url, master))
  # The async/get is so that ctrl-c can interrupt the scans.
  # See http://stackoverflow.com/questions/1408356/
  # keyboard-interrupts-with-pythons-multiprocessing-pool
  builds = filter(bool, pool.map_async(get_build_json, url_list).get(9999999))

  for build_json, master in builds:
    if build_json.get('results', None) is not None:
      build_db[master][build_json['builderName']] = max(
          build_json['number'],
          build_db[master][build_json['builderName']])
  return builds


def check_builds(master_builds, master_jsons, build_db, gatekeeper_config):
  """Given a gatekeeper configuration, see which builds have failed."""
  failed_builds = []
  for build_json, master_url in master_builds:
    gatekeeper_sections = gatekeeper_config.get(master_url, [])
    for gatekeeper_section in gatekeeper_sections:
      gatekeeper = gatekeeper_section.get(build_json['builderName'], {})
      steps = build_json['steps']
      forgiving = set(gatekeeper.get('forgiving_steps', []))
      closing_steps = set(gatekeeper.get('closing_steps', [])) | forgiving
      tree_notify = set(gatekeeper.get('tree_notify', []))
      sheriff_classes = set(gatekeeper.get('sheriff_classes', []))
      finished = [s for s in steps if s.get('isFinished')]
      close_tree = gatekeeper.get('close_tree', True)
      respect_build_status = gatekeeper.get('respect_build_status', False)

      successful_steps = set(s['name'] for s in finished
                             if (s.get('results', [FAILURE])[0] == SUCCESS or
                                 s.get('results', [FAILURE])[0] == WARNINGS))

      unsatisfied_steps = closing_steps - successful_steps

      finished_steps = set(s['name'] for s in finished)
      # Build is not yet finished, don't penalize on unstarted/unfinished steps.
      if build_json.get('results', None) is None:
        unsatisfied_steps &= finished_steps

      # If the entire build failed.
      if (not unsatisfied_steps and 'results' in build_json and
          build_json['results'] != SUCCESS and respect_build_status):
        unsatisfied_steps.add('[overall build status]')

      buildbot_url = master_jsons[master_url]['project']['buildbotURL']
      project_name = master_jsons[master_url]['project']['title']

      logging.debug('%sbuilders/%s/builds/%d ----', buildbot_url,
                    build_json['builderName'], build_json['number'])
      logging.debug('  build steps: %s', ', '.join(s['name'] for s in steps))
      logging.debug('  closing steps: %s', ', '.join(closing_steps))
      logging.debug('  finished steps: %s', ', '.join(finished_steps))
      logging.debug('  successful: %s', ', '.join(successful_steps))
      logging.debug('  build complete: %s', bool(
          build_json.get('results', None) is not None))
      logging.debug('  unsatisfied steps: %s', ', '.join(unsatisfied_steps))
      logging.debug('  set to close tree: %s', close_tree)
      logging.debug('  build failed: %s', bool(unsatisfied_steps))
      logging.debug('----')


      if unsatisfied_steps:
        build_db[master_url][build_json['builderName']] = max(
            build_json['number'],
            build_db[master_url][build_json['builderName']])

        failed_builds.append({'base_url': buildbot_url,
                              'build': build_json,
                              'close_tree': close_tree,
                              'forgiving_steps': forgiving,
                              'project_name': project_name,
                              'sheriff_classes': sheriff_classes,
                              'tree_notify': tree_notify,
                              'unsatisfied': unsatisfied_steps,
                             })

  return failed_builds


def allowed_keys(test_dict, *keys):
  keys = keys + ('comment',)
  assert all(k in keys for k in test_dict), (
      'not valid: %s; allowed: %s' % (
          ', '.join(set(test_dict.keys()) - set(keys)),
          ', '.join(keys)))


def load_gatekeeper_config(filename):
  """Loads and verifies config json, constructs builder config dict.

  The gatekeeper json configuration file has two main sections: 'masters'
  and 'categories.' The following shows the breakdown of a possible config,
  but note that all nodes are optional (including the root 'masters' and
  'categories' nodes).

  A builder ultimately needs 4 lists (sets):
    closing_steps: steps which close the tree on failure or omission
    forgiving_steps: steps which close the tree but don't email committers
    tree_notify: any additional emails to notify on tree failure
    sheriff_classes: classes of sheriffs to notify on build failure

  Builders can inherit these properties from categories, they can inherit
  tree_notify and sheriff_classes from their master, and they can have these
  properties assigned in the builder itself. Any property not specified
  is considered blank (empty set), and inheritance is always constructive (you
  can't remove a property by inheriting or overwriting it). Builders can inherit
  categories from their master.

  A master consists of zero or more sections, which specify which builders are
  watched by the section and what action should be taken. A section can specify
  tree_closing to be false, which causes the section to only send out emails
  instead of closing the tree. A section or builder can also specify to respect
  a build's failure status with respect_build_status.

  The 'comment' key can be put anywhere and is ignored by the parser.

  # Python, not JSON.
  {
    'masters': {
      'http://build.chromium.org/p/chromium.win': [
        {
          'sheriff_classes': ['sheriff_win'],
          'tree_notify': ['a_watcher@chromium.org'],
          'categories': ['win_extra'],
          'builders': {
            'XP Tests (1)': {
              'categories': ['win_tests'],
              'closing_steps': ['xp_special_step'],
              'forgiving_steps': ['archive'],
              'tree_notify': ['xp_watchers@chromium.org'],
              'sheriff_classes': ['sheriff_xp'],
            }
          }
        }
      ]
    },
    'categories': {
      'win_tests': {
        'comment': 'this is for all windows testers',
        'closing_steps': ['startup_test'],
        'forgiving_steps': ['boot_windows'],
        'tree_notify': ['win_watchers@chromium.org'],
        'sheriff_classes': ['sheriff_win_test']
      },
      'win_extra': {
        'closing_steps': ['extra_win_step']
      }
    }
  }

  In this case, XP Tests (1) would be flattened down to:
    closing_steps: ['startup_test', 'win_tests']
    forgiving_steps: ['archive', 'boot_windows']
    tree_notify: ['xp_watchers@chromium.org', 'win_watchers@chromium.org',
                  'a_watcher@chromium.org']
    sheriff_classes: ['sheriff_win', 'sheriff_win_test', 'sheriff_xp']

  Again, fields are optional and treated as empty lists/sets if not present.
  """

  master_keys = ['sheriff_classes', 'tree_notify']
  builder_keys = ['forgiving_steps', 'closing_steps', 'tree_notify',
                  'sheriff_classes']

  with open(filename) as f:
    raw_gatekeeper_config = json.load(f)

  allowed_keys(raw_gatekeeper_config, 'categories', 'masters')

  categories = raw_gatekeeper_config.get('categories', {})
  masters = raw_gatekeeper_config.get('masters', {})

  for category in categories.values():
    allowed_keys(category, *builder_keys)

  gatekeeper_config = {}
  for master_url, master_sections in masters.iteritems():
    for master_section in master_sections:
      gatekeeper_config.setdefault(master_url, []).append({})
      allowed_keys(master_section, 'builders', 'categories', 'close_tree',
                   'respect_build_status', *master_keys)

      builders = master_section.get('builders', {})
      for buildername, builder in builders.iteritems():
        allowed_keys(builder, 'categories', *builder_keys)
        for item in builder.values():
          assert isinstance(item, list)
          assert all(isinstance(elem, basestring) for elem in item)

        gatekeeper_config[master_url][-1].setdefault(buildername, {})
        gatekeeper_builder = gatekeeper_config[master_url][-1][buildername]

        # Populate with empty defaults.
        for k in builder_keys:
          gatekeeper_builder.setdefault(k, set())

        # Inherit any values from the master.
        for k in master_keys:
          gatekeeper_builder[k] |= set(master_section.get(k, []))

        gatekeeper_builder['close_tree'] = master_section.get('close_tree',
                                                              True)
        gatekeeper_builder['respect_build_status'] = master_section.get(
            'respect_build_status', False)

        # Inherit any values from the categories.
        all_categories = (builder.get('categories', []) +
                          master_section.get( 'categories', []))
        for c in all_categories:
          for k in builder_keys:
            gatekeeper_builder[k] |= set(categories[c].get(k, []))

        # Add in any builder-specific values.
        for k in builder_keys:
          gatekeeper_builder[k] |= set(builder.get(k, []))

  return gatekeeper_config


def parse_sheriff_file(url):
  """Given a sheriff url, download and parse the appropirate sheriff list."""
  with closing(urllib2.urlopen(url)) as f:
    line = f.readline()
  usernames_matcher_ = re.compile(r'document.write\(\'([\w, ]+)\'\)')
  usernames_match = usernames_matcher_.match(line)
  sheriffs = set()
  if usernames_match:
    usernames_str = usernames_match.group(1)
    if usernames_str != 'None (channel is sheriff)':
      for sheriff in usernames_str.split(', '):
        if sheriff.count('@') == 0:
          sheriff += '@google.com'
        sheriffs.add(sheriff)
  return sheriffs


def get_sheriffs(classes, base_url):
  """Given a list of sheriff classes, download and combine sheriff emails."""
  sheriff_sets = (parse_sheriff_file(base_url % cls) for cls in classes)
  return reduce(operator.or_, sheriff_sets, set())


def hash_message(message, url, secret):
  # Make this backwards compatable with python 2.6, since total_seconds()
  # exists only in python 2.7.
  utc_now_td = (datetime.datetime.utcnow() -
      datetime.datetime.utcfromtimestamp(0))

  utc_now = utc_now_td.days * 86400 + utc_now_td.seconds
  salt = random.getrandbits(32)
  hasher = hmac.new(secret, '%s:%d:%d' % (message, utc_now, salt),
                    hashlib.sha256)
  client_hash = hasher.hexdigest()

  return {'message': message,
          'time': utc_now,
          'salt': salt,
          'url': url,
          'sha256': client_hash,
         }


def submit_email(email_app, build_data, secret):
  """Submit json to a mailer app which sends out the alert email."""

  url = email_app + '/email'
  data = hash_message(json.dumps(build_data, sort_keys=True), url, secret)

  req = urllib2.Request(url, urllib.urlencode({'json': json.dumps(data)}))
  with closing(urllib2.urlopen(req)) as f:
    code = f.getcode()
    if code != 200:
      response = f.read()
      raise Exception('error connecting to email app: code %d %s' % (
          code, response))


def close_tree_if_failure(failed_builds, username, password, tree_status_url,
                          set_status, sheriff_url, default_from_email,
                          email_app_url, secret):
  """Given a list of failed builds, close the tree and email tree watchers."""
  if not failed_builds:
    logging.info( 'no failed builds!')
    return

  logging.info('%d failed builds found, closing the tree...' %
               len(failed_builds))
  closing_builds = [b for b in failed_builds if b['close_tree']]
  if closing_builds:
    # Close on first failure seen.
    msg = 'Tree is closed (Automatic: "%(steps)s" on "%(builder)s" %(blame)s)'
    tree_status = msg % {'steps': ','.join(closing_builds[0]['unsatisfied']),
                         'builder': failed_builds[0]['build']['builderName'],
                         'blame':
                         ','.join(failed_builds[0]['build']['blame'])
                        }

    logging.info('closing the tree with message: \'%s\'' % tree_status)
    if set_status:
      update_status(tree_status, tree_status_url, username, password)
    else:
      logging.info('set-status not set, not connecting to chromium-status!')
  # Email everyone that should be notified.
  emails_to_send = []
  for failed_build in failed_builds:
    waterfall_url = failed_build['base_url'].rstrip('/') + '/waterfall'
    build_url = '%s/builders/%s/builds/%d' % (
        failed_build['base_url'].rstrip('/'),
        failed_build['build']['builderName'],
        failed_build['build']['number'])
    project_name = failed_build['project_name']
    fromaddr = failed_build['build'].get('fromAddr', default_from_email)

    tree_notify = failed_build['tree_notify']

    if failed_build['unsatisfied'] <= failed_build['forgiving_steps']:
      blamelist = set()
    else:
      blamelist = set(failed_build['build']['blame'])

    sheriffs = get_sheriffs(failed_build['sheriff_classes'], sheriff_url)
    watchers = list(tree_notify | blamelist | sheriffs)


    build_data = {
        'build_url': build_url,
        'from_addr': fromaddr,
        'project_name': project_name,
        'steps': [],
        'unsatisfied': list(failed_build['unsatisfied']),
        'waterfall_url': waterfall_url,
    }

    for field in ['builderName', 'number', 'reason']:
      build_data[field] = failed_build['build'][field]

    build_data['result'] = failed_build['build'].get('results', 0)
    build_data['blamelist'] = failed_build['build']['blame']
    build_data['changes'] = failed_build['build'].get('sourceStamp', {}).get(
        'changes', [])

    build_data['revisions'] = [x['revision'] for x in build_data['changes']]

    for step in failed_build['build']['steps']:
      new_step = {}
      for field in ['text', 'name', 'logs']:
        new_step[field] = step[field]
      new_step['started'] = step.get('isStarted', False)
      new_step['urls'] = step.get('urls', [])
      new_step['results'] = step.get('results', [0, None])[0]
      build_data['steps'].append(new_step)

    if email_app_url and watchers:
      emails_to_send.append((watchers, json.dumps(build_data, sort_keys=True)))

    buildnum = failed_build['build']['number']
    steps = failed_build['unsatisfied']
    builder = failed_build['build']['builderName']
    logging.info(
        'to %s: failure in %s build %s: %s' % (', '.join(watchers),
                                                        builder, buildnum,
                                                        list(steps)))
    if not email_app_url:
      logging.warn('no email_app_url specified, no email sent!')

  # Deduplicate emails.
  keyfunc = lambda x: x[1]
  for k, g in itertools.groupby(sorted(emails_to_send, key=keyfunc), keyfunc):
    watchers = list(reduce(operator.or_, [set(e[0]) for e in g], set()))
    build_data = json.loads(k)
    build_data['recipients'] = watchers
    submit_email(email_app_url, build_data, secret)



def get_build_db(filename):
  """Open the build_db file.

  filename: the filename of the build db.
  """
  build_db = None
  if os.path.isfile(filename):
    print 'loading build_db from', filename
    with open(filename) as f:
      build_db = json.load(f)

  return build_db or {}


def save_build_db(build_db, filename):
  """Save the build_db file.

  build_db: dictionary to jsonize and store as build_db.
  filename: the filename of the build db.
  """
  print 'saving build_db to', filename
  with open(filename, 'wb') as f:
    json.dump(build_db, f)


def get_options():
  prog_desc = 'Closes the tree if annotated builds fail.'
  usage = '%prog [options] <one or more master urls>'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--build-db', default='build_db.json',
                    help='records the last-seen build for each builder')
  parser.add_option('--clear-build-db', action='store_true',
                    help='reset build_db to be empty')
  parser.add_option('--sync-build-db', action='store_true',
                    help='don\'t process any builds, but update build_db '
                         'to the latest build numbers')
  parser.add_option('--skip-build-db-update', action='store_true',
                    help='don\' write to the build_db, overridden by sync and'
                         ' clear db options')
  parser.add_option('--password-file', default='.status_password',
                    help='password file to update chromium-status')
  parser.add_option('-s', '--set-status', action='store_true',
                    help='close the tree by connecting to chromium-status')
  parser.add_option('--status-url',
                    default='https://chromium-status.appspot.com/status',
                    help='URL for the status app')
  parser.add_option('--status-user', default='buildbot@chromium.org',
                    help='username for the status app')
  parser.add_option('--sheriff-url',
                    default='http://build.chromium.org/p/chromium/%s.js',
                    help='URL pattern for the current sheriff list')
  parser.add_option('--parallelism', default=16,
                    help='up to this many builds can be queried simultaneously')
  parser.add_option('--default-from-email',
                    default='buildbot@chromium.org',
                    help='default email address to send from')
  parser.add_option('--email-app-url',
                    default='https://chromium-gatekeeper-mailer.appspot.com',
                    help='URL of the application to send email from')
  parser.add_option('--email-app-secret-file',
                    default='.gatekeeper_secret',
                    help='file containing secret used in email app auth')
  parser.add_option('--no-email-app', action='store_true',
                    help='don\'t send emails')
  parser.add_option('--json', default='gatekeeper.json',
                    help='location of gatekeeper configuration file')
  parser.add_option('--verify', action='store_true',
                    help='verify that the gatekeeper config file is correct')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='turn on extra debugging information')

  options, args = parser.parse_args()

  options.email_app_secret = None
  options.password = None

  if options.verify:
    return options, args

  if not args:
    parser.error('you need to specify at least one master URL')

  if options.no_email_app:
    options.email_app_url = None

  if options.email_app_url:
    if os.path.exists(options.email_app_secret_file):
      with open(options.email_app_secret_file) as f:
        options.email_app_secret = f.read().strip()
    else:
      parser.error('Must provide email app auth with  %s.' % (
          options.email_app_secret_file))

  args = [url.rstrip('/') for url in args]

  return options, args


def main():
  options, args = get_options()

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.INFO)

  gatekeeper_config = load_gatekeeper_config(options.json)

  if options.verify:
    return 0

  masters = set(args)
  if not masters <= set(gatekeeper_config):
    print 'The following masters are not present in the gatekeeper config:'
    for m in masters - set(gatekeeper_config):
      print '  ' + m
    return 1

  if options.clear_build_db:
    build_db = {}
    save_build_db(build_db, options.build_db)
  else:
    build_db = get_build_db(options.build_db)

  new_builds, master_jsons = find_new_builds_per_master(masters, build_db)
  if options.sync_build_db:
    save_build_db(build_db, options.build_db)
    return 0
  build_jsons = get_build_jsons(new_builds, build_db, options.parallelism)
  failed_builds = check_builds(build_jsons, master_jsons, build_db,
                               gatekeeper_config)
  if options.set_status:
    options.password = get_pwd(options.password_file)

  close_tree_if_failure(failed_builds, options.status_user, options.password,
                        options.status_url, options.set_status,
                        options.sheriff_url, options.default_from_email,
                        options.email_app_url, options.email_app_secret)

  if not options.skip_build_db_update:
    save_build_db(build_db, options.build_db)

  return 0


if __name__ == '__main__':
  sys.exit(main())
