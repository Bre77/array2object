#!/usr/bin/env python
#
# Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A command line utility that submits event data to Splunk from stdin."""

from __future__ import absolute_import
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import splunklib.client as client

try:
    from utils import *
except ImportError:
    raise Exception("Add the SDK repository to your PYTHONPATH to run the examples "
                    "(e.g., export PYTHONPATH=~/splunk-sdk-python.")

RULES = {
    "eventhost": {
        'flags': ["--eventhost"],
        'help': "The event's host value"
    },
    "source": {
        'flags': ["--eventsource"],
        'help': "The event's source value"
    },
    "sourcetype": {
        'flags': ["--sourcetype"],
        'help': "The event's sourcetype"
    }
}

def main(argv):
    usage = 'usage: %prog [options] <index>'
    opts = parse(argv, RULES, ".splunkrc", usage=usage)

    if len(opts.args) == 0: error("Index name required", 2)
    index = opts.args[0]

    kwargs_splunk = dslice(opts.kwargs, FLAGS_SPLUNK)
    service = client.connect(**kwargs_splunk)

    if index not in service.indexes:
        error("Index '%s' does not exist." % index, 2)

    kwargs_submit = dslice(opts.kwargs, 
        {'eventhost':'host'}, 'source', 'sourcetype')

    #
    # The following code uses the Splunk streaming receiver in order
    # to reduce the buffering of event data read from stdin, which makes
    # this tool a little friendlier for submitting large event streams,
    # however if the buffering is not a concern, you can achieve the
    # submit somewhat more directly using Splunk's 'simple' receiver, 
    # as follows:
    #
    #   event = sys.stdin.read()
    #   service.indexes[index].submit(event, **kwargs_submit)
    #

    cn = service.indexes[index].attach(**kwargs_submit)
    try:
        while True:
            line = sys.stdin.readline().rstrip('\r\n')
            if len(line) == 0: break
            cn.write(line)
    finally:
        cn.close()

if __name__ == "__main__":
    main(sys.argv[1:])

