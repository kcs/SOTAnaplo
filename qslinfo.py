#!/usr/bin/env python3

""" This module is used to keep track of qsling information stored in a file
and matching with a parsed log
"""

import json
import datetime
import re
import argparse
import sys

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

uk_call = re.compile(r"(?<=^[GM2])[UDJIMW](?=[0-9][a-z])", re.I)
uk_clubcall = re.compile(r"(?<=^[GM])[PTHNSC](?=[0-9][a-z])", re.I)


qsl_types = ('direct$', 'direct', 'bureau')
def qsl_ranking(call, key, qsl):
    """ Add qsl information to either sent or received (determined by key)
    qsl information is ranked and higher one is kept
    the order is: direct$ > direct > bureau
    """
    oqsl = getattr(call, key, None)
    for q in qsl_types:
        if q == qsl or q == oqsl:
            call[key] = q
            break

def reduce_UK_call(callsign):
    """ Change the callsign to the English version of it if it belongs to
    one of the UK entities
    """
    reduced = callsign
    if reduced[0] in 'GM':
        reduced = uk_call.sub('', reduced)
        reduced = uk_call.sub('X', reduced)
    elif reduced[0] == '2':
        reduced = uk_call.sub('E', reduced)
    return reduced


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
        self.alternate_calls = {}


    def load(self, filename):
        """ Load the contents of qsl_info from a file.
        The file should be a JSON serialization of a qsl info dict, with
        the set of qso dates serialized as list
        """
        with open(filename, 'r', encoding='utf-8') as f:
            self.qsl_info = json.load(f, object_hook = decode_set_hook(['qsos']))

        # generate also a list of altrnate calls based on the existing data
        # this is useful for adding qso-s at the correct location
        for callsign, value in self.qsl_info.items():
            # look only in lists
            if type(value) is list:
                for alternate in value:
                    # look for non-obvious roamed call differences
                    base_call = call.match(alternate['call']).group(1)
                    if base_call != callsign:
                        self.alternate_calls[base_call] = callsign
            # if the callsign is a UK call, reduce it and add as alternate
            alternate = reduce_UK_call(callsign)
            if alternate != callsign:
                self.alternate_calls[alternate] = callsign


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
            # make sure this is not a known alternate call
            normalized_call = reduce_UK_call(base_call)
            if normalized_call in self.alternate_calls:
                base_call = self.alternate_calls[normalized_call]
            elif normalized_call != base_call and normalized_call in self.qsl_info:
                base_call = normalized_call

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

            translate_qso_qsl = {'$': 'direct$', '%': 'direct', '@': 'bureau'}
            if rec in translate_qso_qsl:
                qsl_ranking(this_call, 'qsl_reveived', translate_qso_qsl[rec])
            if sen in translate_qso_qsl:
                qsl_ranking(this_call, 'qsl_sent', translate_qso_qsl[sen])

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


    def set_qsl_sent_rcvd(self, callsign, sent=True):
        if callsign.endswith('$'):
            v = 'direct$'
            callsign = callsign[:-1]
        elif callsign.endswith('*'):
            v = 'direct'
            callsign = callsign[:-1]
        else:
            v = 'bureau'
        m = call.fullmatch(callsign)
        if not m:
            raise ValueError("Invalid callsign: {}".format(callsign))
        call_info = self.qsl_info.get(m.group(1).upper())
        if type(call_info) is list:
            for c in call_info:
                if c['call'] == callsign[:m.end(1)].upper():
                    qsl_ranking(c, 'qsl_sent' if sent else 'qsl_received', v)
        elif type(call_info) is dict:
            qsl_ranking(call_info, 'qsl_sent' if sent else 'qsl_received', v)


    def change_uk_key(self, key):
        if key[0] not in 'GM2':
            return False
        basekey = reduce_UK_call(key)
        oldkey = ''
        for k in self.qsl_info.keys():
            if reduce_UK_call(k) == basekey:
                oldkey = k
        if oldkey and oldkey != key:
            self.qsl_info[key] = self.qsl_info.pop(oldkey)
            return True
        return False


    def merge_calls(self, calls, default=None):
        """ merge multiple alternate callsigns already added to the qsl info
        the calls is a list of possible alternates, default if specified will
        be used as the new key for the merged dat
        if default is not specified first element in calls will be used as key
        """
        if type(calls) is not list:
            raise ValueError("Invalid list of calls to merge")
        if default is None:
            default = calls[0]
        m = call.match(default)
        if not m:
            raise ValueError("Default callsign does not look like a valid one")
        callsign = m.group(1).upper()
        # normalize calls
        keys = []
        for c in calls:
            m = call.match(c)
            if not m:
                raise ValueError("Callsing {} is not valid".format(c))
            k = m.group(1).upper()
            if k in self.qsl_info:
                keys.append(k)
        if len(keys) == 1:
            if keys[0] != callsign:
                self.qsl_info[callsign] = self.qsl_info.pop(keys[0])
                return True
        elif len(keys) > 1:
            qsl = []
            for k in keys:
                old_qsl = self.qsl_info.pop(k)
                if type(old_qsl) is list:
                    qsl.extend(old_qsl)
                else:
                    qsl.append(old_qsl)
            self.qsl_info[callsign] = qsl
            return True
        return False


if __name__ == '__main__':
    # parse arguments
    parser = argparse.ArgumentParser(description='QSL information handling utility')
    parser.add_argument('-f', '--file',
                        help='File used for storing qsl information. If ommited `qsl.lst` is used by default')

    parser.add_argument('-b', '--blacklist', action= 'store_true',
                        help='Read a list of callsigns from standard input to be marked as non-qsling')
    parser.add_argument('-s', '--send', action = 'store_true',
                        help='Read a list of callsigns from standard input to be marked with sent.')
    parser.add_argument('-r', '--receive', action = 'store_true',
                        help='Read a list of callsigns from standard input to be marked with received.')
    parser.add_argument('-c', '--countries', action='store_true',
                        help='Display a statistics about the countries worked')
    parser.add_argument('-u', '--uk-call',
                        help='Set default UK callsign')
    parser.add_argument('-m', '--merge', nargs='+',
                        help='Merge multiple alternate callsigns')
    args = parser.parse_args()

    qsl_info = QSL()

    if args.file:
        qsl_info.load(args.file)
    else:
        qsl_info.load('qsl.lst')

    dirty = False

    if args.blacklist:
        print('Enter "no-qsl" callsigns (followed by CTRL-D):')
        lines = sys.stdin.readlines()

        for line in lines:
            calls = line.strip().split()
            for c in calls:
                qsl_info.set_no_qsl(c)
        dirty = True

    if args.send:
        print('Enter "qsl-sent" callsigns (followed by CTRL-D):')
        lines = sys.stdin.readlines()

        for line in lines:
            calls = line.strip().split()
            for c in calls:
                    qsl_info.set_qsl_sent_rcvd(c)
        dirty = True

    if args.receive:
        print('Enter "qsl-received" callsigns (followed by CTRL-D):')
        lines = sys.stdin.readlines()

        for line in lines:
            calls = line.strip().split()
            for c in calls:
                    qsl_info.set_qsl_sent_rcvd(c, False)
        dirty = True

    if args.uk_call:
        if qsl_info.change_uk_key(args.uk_call.upper()):
            dirty = True

    if args.merge:
        if qsl_info.merge_calls(args.merge):
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

