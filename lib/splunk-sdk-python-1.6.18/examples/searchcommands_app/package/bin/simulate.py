#!/usr/bin/env python
# coding=utf-8
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

from __future__ import absolute_import, division, print_function, unicode_literals
import app
import random
import csv
import os,sys
import time

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'searchcommands_app', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class SimulateCommand(GeneratingCommand):
    """ Generates a sequence of events drawn from a CSV file using repeated random sampling

    ##Syntax

    .. code-block::
        simulate csv=<path> rate=<expected_event_count> interval=<sampling_period> duration=<execution_period>
        [seed=<string>]

    ##Description

    The :code:`simulate` command uses repeated random samples of the event records in :code:`csv` for the execution
    period of :code:`duration`. Sample sizes are determined for each time :code:`interval` in :code:`duration`
    using a Poisson distribution with an average :code:`rate` specifying the expected event count during
    :code:`interval`.

    ##Example

    .. code-block::
        | simulate csv="/opt/splunk/etc/apps/searchcommands_app/data/population.csv" rate=10 interval=00:00:01 duration=00:00:02 seed=1

    This example generates events drawn from repeated random sampling of events from :code:`tweets.csv`. Events are
    drawn at an average rate of 50 per second for a duration of 5 seconds. Events are piped to the example
    :code:`countmatches` command which adds a :code:`word_count` field containing the number of words in the
    :code:`text` field of each event. The mean and standard deviation of the :code:`word_count` are then computed by
    the builtin :code:`stats` command.


    """
    csv_file = Option(
        doc='''**Syntax:** **csv=***<path>*
        **Description:** CSV file from which repeated random samples will be
        drawn''',
        name='csv', require=True, validate=validators.File())

    duration = Option(
        doc='''**Syntax:** **duration=***<time-interval>*
        **Description:** Duration of simulation''',
        require=True, validate=validators.Duration())

    interval = Option(
        doc='''**Syntax:** **interval=***<time-interval>*
        **Description:** Sampling interval''',
        require=True, validate=validators.Duration())

    rate = Option(
        doc='''**Syntax:** **rate=***<expected-event-count>*
        **Description:** Average event count during sampling `interval`''',
        require=True, validate=validators.Integer(1))

    seed = Option(
        doc='''**Syntax:** **seed=***<string>*
        **Description:** Value for initializing the random number generator ''')

    def generate(self):
        if self.seed is not None:
            random.seed(self.seed)
        records = [record for record in csv.DictReader(self.csv_file)]
        lambda_value = 1.0 / (self.rate / float(self.interval))

        duration = self.duration
        while duration > 0:
            count = int(round(random.expovariate(lambda_value)))
            start_time = time.clock()
            for record in random.sample(records, count):
                yield record
            interval = time.clock() - start_time
            if interval < self.interval:
                time.sleep(self.interval - interval)
            duration -= max(interval, self.interval)

dispatch(SimulateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
