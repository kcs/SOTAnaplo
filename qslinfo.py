#!/usr/bin/env python3

""" This module is used to keep track of qsling information stored in a file
and matching with a parsed log
"""

import json
import datetime
import re
import argparse

import country


def decode_set_hook(keys):
    """ Decode JSON obj fields containing an array as set instead of list
    The name of fields which must be changed are given in keys
    If keys is None then all lists are decoded as sets
    """
    def hook(obj):
        for k in obj.keys():
            if (keys is None or k in keys):
                if type(obj[k]) is list:
                    obj[k] = set(obj[k])
                elif type(obj[k]) is dict:
                    obj[k] = decode_set_hook(None)(obj[k])
        return obj
    return hook


def encode_set_as_list(obj):
    if type(obj) is set:
        return sorted(obj)
    raise TypeError


call_prefix = r"(?:(?=.?[a-z])[0-9a-z]{1,2}(?:(?<=3d)a)?)"
call = re.compile(r"(?:"+call_prefix+r"[0-9]?/)?("+call_prefix+r"[0-9][a-z0-9]*)(?:/[0-9a-z]+){0,2}", re.I)


class QSL:
    """ This class contains information about all callsigns contacted and
    their qsling status.
    It also offers some statistics and notifications about qsling status

    QSL information is stored in a dictionary which can be saved as a JSON file
    containing keys for each different callsign contacted and an associated
    value of either a dict or a list of dicts. A dictionary assigned to
    a callsign contains the country code, qsl sent and qsl received information
    or o non-qsling policy and a list of contact dates for each variant of the
    callsing. When a callsign roams to other country (by CEPT rule) then
    for each separate country a same structured dict is associated and the
    callsign will have a list of these dicts
    """
    def __init__(self):
        self.qsl_info = {}
        self.countries = {}
        self.stat_list = {}


    def load(self, filename):
        """ Load the contents of qsl_info from a file.
        The file should be a JSON serialization of a qsl info dict, with
        the set of qso dates serialized as list
        """
        with open(filename, 'r', encoding='utf-8') as f:
            self.qsl_info = json.load(f, object_hook = decode_set_hook(['qsos']))


    def save(self, filename):
        """ Save the contents of qsl_info into a file.
        The qsl information is serialized into a JSON format with the qso sets
        implemented as lists
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.qsl_info, f, ensure_ascii=False, sort_keys=True,
                      indent=4,
                      default=encode_set_as_list)


    def calls(self):
        """ Generator to iterate through all callsigns in the list of qsl info
        """
        for value in self.qsl_info.values():
            if type(value) is list:
                for v in value:
                    yield v
            else:
                yield value


    def update_countries(self):
        """ Update the qsl info by country based on the current qsl status
        of the stored callsigns
        """
        for call_info in self.calls():
            cty = country.fix4dxcc(call_info['country'])
            if call_info.get('qsl_received') or self.countries.get(cty) == 'confirmed':
                status = 'confirmed'
            elif call_info.get('qsl_sent') or self.countries.get(cty) == 'unconfirmed':
                status = 'unconfirmed'
            else:
                status = None
            self.countries[cty] = status


    def add_qsos(self, qsos, qso_date):
        """ Add a list of new qsos to the QSL info list
        All newly added qso is specially marked for later statistics.
        If the qso with the given date already existed in the qslinfo,
        the given date is treated as newly added for statistics purposes,
        so a log can be analyzed multiple times
        """

        date_str = qso_date.strftime('%Y-%m-%d')
        qso_time = (0,0)
        for qso in qsos:
            if qso.time[0] < qso_time[0] or (qso.time[0] == qso_time[0] and qso.time[1] < qso_time[1]):
                qso_date += datetime.timedelta(days=1)
                date_str = qso_date.strftime('%Y-%m-%d')
            qso_time = qso.time

            base_call = call.match(qso.callsign)
            roam_call = qso.callsign[:base_call.end(1)]
            base_call = base_call.group(1)
            if base_call in self.qsl_info:
                this_call = self.qsl_info[base_call]
                if type(this_call) is list:
                    call_list = [x for x in this_call if x.get('call') == roam_call]
                    if not call_list:
                        this_call = {
                            'call': roam_call,
                            'country': country.find(roam_call)[0]
                        }
                        self.qsl_info[base_call].append(this_call)
                    else:
                        this_call = call_list[0]
                else:
                    if this_call.get('call') != roam_call:
                        this_call = {
                            'call': roam_call,
                            'country': country.find(roam_call)[0]
                        }
                        self.qsl_info[base_call] = [self.qsl_info[base_call], this_call]
            else:
                this_call = {
                    'call': roam_call,
                    'country': country.find(roam_call)[0]
                }
                self.qsl_info[base_call] = this_call

            # add the qso date to this call
            if 'qsos' not in this_call:
                this_call['qsos'] = {}
            if qso.callsign not in this_call['qsos']:
                this_call['qsos'][qso.callsign] = set()

            this_call['qsos'][qso.callsign].add(date_str)

            rec = getattr(qso, 'qsl_rcvd', None)
            sen = getattr(qso, 'qsl_sent', None)

            orec = getattr(this_call, 'qsl_received', None)
            osen = getattr(this_call, 'qsl_sent', None)

            if orec == 'direct$' or rec == '$':
                this_call['qsl_received'] = 'direct$'
            elif orec == 'direct' or rec == '%':
                this_call['qsl_received'] = 'direct'
            elif orec == 'bureau' or rec == '@':
                this_call['qsl_received'] = 'bureau'

            if osen == 'direct$' or sen == '$':
                this_call['qsl_sent'] = 'direct$'
            elif osen == 'direct' or sen == '%':
                this_call['qsl_sent'] = 'direct'
            elif osen == 'bureau' or sen == '@':
                this_call['qsl_sent'] = 'bureau'

            # add the qso date to the new call list, for statistical purposes
            self.stat_list[base_call] = (this_call, date_str)


    def print_stat(self, handle = None):
        self.update_countries()

        countries = {}
        for callsign, (call_info, date_str) in self.stat_list.items():
            if call_info.get('qsl_received') or call_info.get('qsl_sent') or call_info.get('noqsl'):
                continue
            if callsign != call_info['call'] and self.countries[call_info['country']] == 'confirmed':
                # roamed calls are displayed only if the country is not confirmed
                continue

            if call_info['country'] not in countries:
                countries[call_info['country']] = []
            countries[call_info['country']].append(callsign)

        for cty in sorted(countries.keys()):
            print('{} {}: {}'.format(cty, country.country_name(cty), self.countries[cty] if self.countries.get(cty) else 'new!'), file=handle)
            for c in sorted(countries[cty]):
                print('  {}'.format(c), file=handle)


    def set_no_qsl(self, callsign):
        m = call.fullmatch(callsign)
        if not m:
            raise ValueError("Invalid callsign: {}".format(callsign))
        call_info = self.qsl_info.get(m.group(1).upper())
        if type(call_info) is list:
            for c in call_info:
                c['noqsl'] = True
        elif type(call_info) is dict:
            call_info['noqsl'] = True


if __name__ == '__main__':
    # parse arguments
    parser = argparse.ArgumentParser(description='QSL information handling utility')
    parser.add_argument('-f', '--file',
                        help='File used for storing qsl information. If ommited `qsl.lst` is used by default')

    parser.add_argument('-b', '--blacklist',
                        help='A file containing callsigns on each line. Each callsign if present in the qsl info database will be marked as non-qsling')
    parser.add_argument('-c', '--countries', action='store_true',
                        help='Display a statistics about the countries worked')
    args = parser.parse_args()

    print(args)
    qsl_info = QSL()

    if args.file:
        qsl_info.load(args.file)
    else:
        qsl_info.load('qsl.lst')

    dirty = False

    if args.blacklist:
        with open(args.blacklist, 'r', encoding='utf-8') as f:
            for line in f:
                calls = line.strip().split()
                for c in calls:
                    qsl_info.set_no_qsl(c)
        dirty = True

    if args.countries:
        qsl_info.update_countries()
        confirmed = [x for x in qsl_info.countries.keys() if qsl_info.countries[x] == 'confirmed']
        print('Confirmed countries: {}\n{}'.format(len(confirmed), ' '.join(sorted(confirmed))))
        unconfirmed = [x for x in qsl_info.countries.keys() if qsl_info.countries[x] == 'unconfirmed']
        print('Unconfirmed countries: {}\n{}'.format(len(unconfirmed), ' '.join(sorted(unconfirmed))))
        new = [x for x in qsl_info.countries.keys() if not qsl_info.countries[x]]
        print('New countries: {}\n{}'.format(len(new), ' '.join(sorted(new))))

        lc = {}
        for i in qsl_info.calls():
            if ((i['country'] in unconfirmed or i['country'] in new) and
                ('qsl_recived' not in i and 'qsl_sent' not in i and 'noqsl' not in i)):
                if i['country'] not in lc:
                    lc[i['country']] = []
                lc[i['country']].append(i['call'])

        for cty in sorted(lc.keys()):
            print('{} {}: {}'.format(cty, country.country_name(cty), qsl_info.countries[cty] if qsl_info.countries.get(cty) else 'new!'))
            for c in sorted(lc[cty]):
                print('  {}'.format(c))



    if dirty:
        if args.file:
            qsl_info.save(args.file)
        else:
            qsl_info.save('qsl.lst')

