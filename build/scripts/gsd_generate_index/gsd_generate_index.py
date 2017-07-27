#!/usr/bin/python
# Copyright (c) 2008-2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generate index.html files for a Google Storage for Developers directory.

Google Storage for Developers provides only a raw set of objects.
For some buckets we would like to be able to support browsing of the directory
tree. This utility will generate the needed index and upload/update it.
"""

import optparse
import posixpath
import re
import subprocess
import sys
import tempfile
import threading


GENERATED_INDEX = '_index.html'
NUM_THREADS = 100


def PathToLink(path):
  return path.replace('gs://', 'https://sandbox.google.com/storage/')


def FixupSize(sz):
  """Convert a size string in bytes to human readable form.

  Arguments:
    sz: a size string in bytes
  Returns:
    A human readable size in bytes/K/M/G.
  """
  sz = int(sz)
  if sz < 1000:
    sz = str(sz)
  elif sz < 1000000:
    sz = str(int(sz / 100) / 10.0) + 'K'
  elif sz < 1000000000:
    sz = str(int(sz / 100000) / 10.0) + 'M'
  else:
    sz = str(int(sz / 100000000) / 10.0) + 'G'
  return sz


def GetPathInfo(path, options):
  """Collect size, date, md5 for a give gsd path."""
  # Check current state.
  cmd = [options.gsutil, 'ls', '-L', path]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  p_stdout, _ = p.communicate()
  assert p.returncode == 0
  # Extract intersting fields.
  fields = {}
  size_search = re.search('\tContent-Length:\t([0-9]+)\n', p_stdout)
  if size_search:
    fields['size'] = FixupSize(size_search.group(1))
  else:
    fields['size'] = None

  md5_search = re.search('\t(MD5|Etag):\t([^\n]+)\n', p_stdout)
  if md5_search:
    fields['md5'] = md5_search.group(2)
  else:
    fields['md5'] = None

  date_search = re.search('\tCreation time:\t([^\n]+)\n', p_stdout)
  if date_search:
    fields['date'] = date_search.group(1)
  else:
    fields['date'] = None

  return fields


def GenerateIndex(path, children, directories, options):
  """Generate index for a given path as needed."""
  # Generate index content.
  index = ''
  index += '<html>'
  index += '<head>'
  index += '<title>Index of %s</title>' % path
  index += '</head>'
  index += '<body>'
  index += '<h1>Index of %s</h1>' % path
  index += '<table>'
  index += '<tr>'
  index += '<th align="left">Name</th>'
  index += '<th align="left">Last modified</th>'
  index += '<th align="left">Size</th>'
  index += '<th align="left">MD5</th>'
  index += '</tr>'
  index += '<tr><th colspan="4"><hr></th></tr>'
  parent = posixpath.dirname(path)
  if parent != 'gs:':
    index += '<tr>'
    index += '<td><a href="%s">Parent Directory</a></td>' % (
        PathToLink(posixpath.join(parent, GENERATED_INDEX)))
    index += '<td> </td>'
    index += '<td> </td>'
    index += '<td> </td>'
    index += '</tr>'
  for child in children:
    index += '<tr>'
    if child in directories:
      index += '<td><a href="%s">%s</a></td>' % (
          PathToLink(posixpath.join(child, GENERATED_INDEX)),
          posixpath.basename(child))
      index += '<td> </td>'
      index += '<td> </td>'
      index += '<td> </td>'
    else:
      fields = GetPathInfo(child, options)
      index += '<td><a href="%s">%s</a></td>' % (
          PathToLink(child), posixpath.basename(child))
      index += '<td>%s</td>' % fields['date']
      index += '<td><b>%s</b></td>' % fields['size']
      index += '<td>%s</td>' % fields['md5']
    index += '</tr>'
  index += '<tr><th colspan="4"><hr></th></tr>'
  index += '</table>'
  index += '</body>'
  index += '</html>'
  # Check current state.
  cmd = [options.gsutil, 'cat', posixpath.join(path, GENERATED_INDEX)]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  p_stdout, _ = p.communicate()
  # Done if it's alrady right (and the cat worked).
  if p.returncode == 0 and p_stdout == index and not options.force:
    print '%s -- skipping, up to date' % path
    return
  # Write to a file.
  f = tempfile.NamedTemporaryFile(suffix='.html')
  filename = f.name
  f.write(index)
  f.flush()
  # Upload index.
  cmd = [options.gsutil, 'cp']
  cmd += [filename, posixpath.join(path, GENERATED_INDEX)]
  p = subprocess.Popen(cmd)
  p.communicate()
  assert p.returncode == 0
  # Optionally update acl.
  if options.acl:
    cmd = [options.gsutil, 'setacl', options.acl]
    cmd += [posixpath.join(path, GENERATED_INDEX)]
    p = subprocess.Popen(cmd)
    p.communicate()
    assert p.returncode == 0
  print '%s -- updated index' % path


def IndexWorker(index_list, errors, mutex, directories, objects, options):
  while True:
    # Pluck out one index to work on, or quit if no more work left.
    mutex.acquire()
    if not index_list:
      mutex.release()
      return
    d = index_list.pop(0)
    mutex.release()
    # Find just this directories children.
    children = [o for o in objects if posixpath.dirname(o) == d]
    # Generate it.
    try:
      GenerateIndex(d, children, directories, options)
    except Exception, e:  # pylint: disable=W0703
      mutex.acquire()
      errors.append(e)
      print str(e)
      mutex.release()


def GenerateIndexes(path, options):
  """Generate all relevant indexes for a given gsd path."""
  # Get a list of objects under this prefix.
  cmd = [options.gsutil, 'ls', posixpath.join(path, '*')]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  p_stdout, _ = p.communicate()
  assert p.returncode == 0
  objects = str(p_stdout).splitlines()
  objects = [o for o in objects if posixpath.basename(o) != GENERATED_INDEX]
  objects = [path.rstrip(':') for path in objects]
  # Find common prefixes.
  directories = set()
  for o in objects:
    part = posixpath.dirname(o)
    while part.startswith(path):
      directories.add(part)
      part = posixpath.dirname(part)
  objects += list(directories)
  # Generate index for each directory.
  index_list = [i for i in directories
                if not options.path or options.path.startswith(i)]
  # Spawn workers
  mutex = threading.Lock()
  errors = []
  workers = [threading.Thread(target=IndexWorker,
                              args=(index_list, errors, mutex,
                                    directories, objects, options))
             for _ in range(0, NUM_THREADS)]
  # Start threads.
  for w in workers:
    w.start()
  # Wait for them to finish.
  for w in workers:
    w.join()
  if errors:
    return 2
  return 0


def main(argv):
  parser = optparse.OptionParser(usage='usage: %prog [options] gs://base-dir')
  parser.add_option('-p', '--path', dest='path',
                    help='only update indexes on a given path')
  parser.add_option('-a', dest='acl', help='acl to set on indexes')
  parser.add_option('-f', '--force', action='store_true', default=False,
                    dest='force', help='upload all indexes even on match')
  parser.add_option('', '--gsutil', default='gsutil',
                    dest='gsutil', help='path to gsutil')
  options, args = parser.parse_args(argv)
  if len(args) != 2 or not args[1].startswith('gs://'):
    parser.print_help()
    return 1
  return GenerateIndexes(args[1], options)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
