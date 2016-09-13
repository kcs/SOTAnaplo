#!/usr/bin/env python3

"""Simple log converter for SOTA
It inputs a simplified text log and converts it to SOTA CSV format.
The input is a simplified version which allows most of the data field
to be guessed by previous input.

Example of input file:
# lines starting with # are comments

# first line contains information about the activation
# multiple activations can be separated by a blank line
# blank lines right after the first line and between comments are not considered

[callsign] [date] SOTA-ref [YOFF-ref] [locator] [other notes] [...]
# fields are optional, they must be specified for the first time in a file
# after that thay will persist across activations
# if chases are also included the SOTA-ref must be set to *
# everything after the SOTA-ref is considered additional note
# and will not persist to next section (not even YOFF ref)
# one optional note is a type of contest if the SOTA operation was carried
# out within the rules of contest (for example Field-day), the type of contest
# should be specified in the format contes:_contest_type_ where _contest_type_
# will specify a rule file which determines the exchanges format and the
# scoring method (this is still need to be expanded)

# next lines hold qso data
[time] [callsign] [freq] [mode] [RST-sent] [RST-rcvd] [SOTA-ref] [notes]
# everything is optional, if not present the previous value will be reused
# however if some fields cannot be differentiated uniquely than it needs to be
# all present

# field rules:

# time will be in the format hhmm or hh:mm (numbers and optional colon)
# hour part is optional and first 0 is also optional
# examples
# 0810 or 08:10 complete time {08:10}
# 811 missing 0 {08:11}
# 9:2 missing 0s {09:02}
# 3 missing hour part {09:03}
# 05 missing hour part {09:05}
# 13 missing hour part {09:13}
# 4 missing hour part, minute less than previous, hour is incremented {10:04}

# callsign any combination of letters and numbers
# at least 1 number in the middle

# frequency decimal number in MHz n[.nnn][MHz]
# must be in a radio amateur band range

# mode a valid amateur radio mode

# RST's either RST or RS format based on mode
# if not present it is considered to be 59 or 599

# SOTA-ref is in format assoc/region-nnn

# anything else not fitting is considered notes
# a line is not allowed to consist only of notes
# further notes not meant for SOTA database can be commented out

"""
import sys
import re
from datetime import date
import os.path

from contest import Contest


class LogException(Exception):
    def __init__(self, message, pos):
        self.message = message
        self.pos = pos


# string matching functions
call_prefix = r"(?:(?=.?[a-z])[0-9a-z]{1,2}(?:(?<=3d)a)?)"
call = re.compile(r"(?:"+call_prefix+r"[0-9]?/)?"+call_prefix+r"[0-9][a-z0-9]*(?:/[0-9a-z]+)?", re.I)
sota_ref = re.compile(r"[a-z0-9]{1,3}/[a-z]{2}-[0-9]{3}", re.I)
wwff_ref = re.compile(r"[a-z0-9]{1,2}f{2}-[0-9]{3,4}", re.I)
locator = re.compile(r"[a-x]{2}[0-9]{2}[a-x]{2}", re.I)
date_reg = re.compile(r"([0-9]{4})(?P<sep>[.-])([0-9]{2})(?P=sep)([0-9]{2})")
time_reg = re.compile(r"(?P<hour>0?[0-9]|1[0-9]|2[0-3])?((?(hour)[0-5]|[0-5]?)[0-9])")
freq = re.compile(r"((?:[0-9]+\.)?[0-9]+)([kMG]?Hz|[mc]?m)?")
rst = re.compile(r"[1-5][1-9][1-9]?")
word = re.compile(r"\S+")
contest = re.compile(r"contest:(\w+)\s*")

def find_word(string, start=0):
    """Find the first word starting from `start` position
    Return the word and the position before and after the word
    """
    while start < len(string) and string[start].isspace():
        start += 1
    end = start
    while end < len(string) and not string[end].isspace():
        end += 1
    return string[start:end], start, end


bands = {
    '160m'   : ( 1.8, 2.0 ),
    '80m'    : ( 3.5, 4.0 ),
    '40m'    : ( 7.0, 7.3 ),
    '30m'    : ( 10.1, 10.15 ),
    '20m'    : ( 14.0, 14.35 ),
    '17m'    : ( 18.068, 18.168 ),
    '15m'    : ( 21.0, 21.45 ),
    '12m'    : ( 24.89, 24.99 ),
    '10m'    : ( 28.0, 29.7 ),
    '6m'     : ( 50.0, 54.0 ),
    '2m'     : ( 144.0, 148.0 ),
    '1.25m'  : ( 219.0, 225.0 ),
    '70cm'   : ( 420.0, 450.0 ),
    '35cm'   : ( 902.0, 928.0 ),
    '23cm'   : ( 1240.0, 1300.0 ),
    '13cm'   : ( 2300.0, 2450.0 ),
    '9cm'    : ( 3400.0, 3475.0 ),
    '6cm'    : ( 5650.0, 5850.0 ),
    '3cm'    : ( 10000.0, 10500.0 ),
    '1.25cm' : ( 24000.0, 24250.0 ),
    '6mm'    : ( 47000.0, 47200.0 ),
    '4mm'    : ( 75500.0, 81500.0 ),
    '2.5mm'  : ( 122250.0, 123000.0 ),
    '2mm'    : ( 134000.0, 141000.0 ),
    '1mm'    : ( 241000.0, 250000.0 ),
}


def match_freq(s):
    # check if the string s is a correct amateur band frequency
    # return the string if it is or False otherwise
    # the string can either specify the frequency or the band
    # specifying the band must contain the m unit as consacrated bands
    # frequency can either specify the unit, or be a single number
    # which is considered to be in MHz, if unit is not MHz if will
    # be converted, or if missing will be added to output string
    m = freq.fullmatch(s)
    if not m:
        return False
    mul = 1.0
    if m.group(2):
        if s.endswith('m'):
            if s in bands:
                return s
            else:
                return False
        if m.group(2) == kHz:
            mul = 0.001
        elif m.group(2) == GHz:
            mul = 1000.0
    n = float(m.group(1)) * mul
    for f in bands.values():
        if n >= f[0] and n <= f[1]:
            if mul == 1.0:
                return m.group(1) + 'MHz'
            else:
                return "{:.3f}MHz".format(n)
    return False


def quote_text(string):
    """Quote a string by the CSV rules:
    if the text contains commas, newlines or quotes it will be quoted
    quotes inside the text will be doubled
    """
    if not string:
        return string
    if ',' in string or '\n' in string or '"' in string:
        # check if already quoted
        if string[0] == '"' and string[-1] == '"':
            # check if every inner quote is doubled
            if '"' not in string[1:-1].replace('""', ''):
                return string
            # if not then inner part must be doubled
            string = string[1:-1]
        # double the inner quotes and quote string
        string = '"{}"'.format(string.replace('"','""'))
    return string


class Activation:
    """Class holding information about an activation or a chase
    Activations contain information about the date and place of activation,
    callsign used and all qsos.
    Also a link to the previous activation is stored
    In a chase multiple qsos can be merged from a single day.
    """

    def __init__(self, string, prev=None):
        """Initialize the activation from the string
        At least callsign, date, and sota reference are needed, other
        information is optional.
        If a previous activation is given then the callsign and date
        can be preserved from it, but new sota reference is mandatory.
        An asterisk instead of sota reference means a chase
        """
        self.previous = prev

        # start splitting the string into words
        w, pos, end = find_word(string)
        # callsign
        m = call.fullmatch(w)
        if m:
            self.callsign = w.upper()
            w, pos, end = find_word(string, end)
        elif prev:
            self.callsign = prev.callsign
        else:
            raise LogException("Error in activation definition, missing callsign", pos)
        # date
        m = date_reg.fullmatch(w)
        if m:
            try:
                self.date = date(int(m.group(1)), int(m.group(3)), int(m.group(4)))
            except ValueError:
                raise LogException("Error in activation definition, invalid date format", pos)
            w, pos, end = find_word(string, end)
        elif prev:
            self.date = prev.date
        else:
            raise LogException("Error in activation definition, missing date", pos)
        # sota reference is mandatory
        m = sota_ref.fullmatch(w)
        if m:
            self.ref = w.upper()
        elif w == '*':
            self.ref = ''
        else:
            raise LogException("Error in activation definition, invalid SOTA reference detected", pos)

        notes = string[end:].strip()

        m = contest.search(notes)
        if m:
            self.contest = Contest(m.group(1))
            notes = notes[:m.start()] + notes[m.end():]
        else:
            self.contest = None

        self.notes = notes
        self.qsos = []

        # TODO: other information
        self.wwff = None
        self.locator = None


    def add_qso(self, string):
        """Add a QSO to list of qsos
        Consider the last qso as the previous one for the new qso
        """
        prev_qso = self.qsos[-1] if self.qsos else None
        if self.contest:
            self.qsos.append(QSO(string, prev_qso, self.contest.exchange))
        else:
            self.qsos.append(QSO(string, prev_qso))


    def print_qsos(self, format='SOTA_v2', config=None):
        if self.previous:
            self.previous.print_qsos()

        # TODO: trace, remove it from final code
        #print("Processing {} from {} with callsign {}".format(
        #    "chase" if not self.ref else "activation of {}".format(self.ref),
        #   self.date.strftime("%Y-%m-%d"), self.callsign))

        # TODO: only SOTA_v2 is understood as of now
        if format == 'SOTA_v2':
            sota_line = ['v2', self.callsign, self.ref, self.date.strftime("%d/%m/%Y")] + [''] * 6
            for qso in self.qsos:
                sota_line[4] = '{:02}{:02}'.format(qso.time[0], qso.time[1])
                sota_line[5] = qso.freq
                sota_line[6] = qso.mode
                sota_line[7] = qso.callsign
                sota_line[8] = getattr(qso, 'ref', '')
                sota_line[9] = quote_text(qso.notes)
                #sota_line[9] = quote_text(' '.join((qso.sent, qso.rcvd, qso.notes)))
                print(','.join(sota_line))
        # contest format: if a contest was specified for an activation
        # use the contest rules to determine the output format
        elif format == 'contest' and self.contest:
            self.contest.configure(self, config)
            for qso in self.qsos:
                self.contest.add_qso(self.callsign, self.date, qso)
            print(self.contest)
        else:
            raise ValueError("Unrecognized output format")


class QSO:
    """Class containing information about a qso
    It is initialized from a string and a previous qso object.
    Missing fields from the string are filled with data from previous qso
    """

    def __init__(self, string, prev=None, exchange=None):
        """Initialize qso data with the following information:
        time callsign freq mode rst_sent rest_rcvd SOTA_ref notes
        """

        words = [(m.group(), m.start(), {}) for m in word.finditer(string)]
        if not words:
            raise LogException("Empty QSO", 0)

        # try to match words into categories
        for i,w in enumerate(words):
            t = w[2]
            # time
            if i < 1:
                m = time_reg.fullmatch(w[0])
                if m:
                    t['time'] = (int(m.group(1)) if m.group(1) else None, int(m.group(2)))
            # callsign
            if i < 2:
                m = call.fullmatch(w[0])
                if m:
                    t['call'] = w[0].upper()
            # freq
            if i < 3:
                m = match_freq(w[0])
                if m:
                    t['freq'] = m
            # mode
            # TODO: add all possible modes and translations
            if i < 4:
                if w[0].lower() in ['cw', 'ssb', 'fm', 'am']:
                    t['mode'] = w[0].upper()
                elif w[0].lower() in ['data', 'psk', 'psk31', 'psk63', 'rtty', 'fsk441', 'jt65']:
                    t['mode'] = 'Data'
                elif w[0].lower() in ['other']:
                    t['mode'] = 'Other'
            # rst
            if i < 6:
                m = rst.fullmatch(w[0])
                if m:
                    t['rst'] = w[0]
            # sota ref
            m = sota_ref.fullmatch(w[0])
            if m:
                t['sota'] = w[0].upper()

            # optional contest exchange
            if exchange and i < 7:
                m = exchange.fullmatch(w[0])
                if m:
                    t['exch'] = w[0]

        # now filter the type list
        # print(words)

        typeorder = ['time', 'call', 'freq', 'mode', 'rst', 'rst', 'exch', 'sota']
        wlist = [None, None, None, None, None, None, None, None]

        lastelem = -1
        noteselem = 7
        for i,w in enumerate(words):
            for e in range(lastelem + 1, len(typeorder)):
                if typeorder[e] in w[2]:
                    lastelem = e
                    wlist[e] = w
                    break
            else:
                noteselem = i
                break

        # try to move back multiple mapped words
        felist = [(i+2,w) for i,w in enumerate(wlist[2:6]) if w]
        for i in range(6,3,-1):
            if wlist[i] is None and felist and typeorder[i] in felist[-1][1][2]:
                wlist[i] = felist[-1][1]
                wlist[felist[-1][0]] = None
                felist.pop()
            if felist and felist[-1][0] == i:
                felist.pop()

        # check for minimum change
        if wlist[1] is None and wlist[2] is None and wlist[3] is None:
            raise LogException("Invalid change from previous QSO", words[i][1])

        # now recreate all elements

        # time
        if wlist[0] is None or wlist[0][2]['time'][0] is None:
            if prev is None:
                raise LogException("Missing time value", 0)
            if wlist[0] is not None:
                self.time = (prev.time[0], wlist[0][2]['time'][1])
                if self.time[1] < prev.time[1]:
                    hour = self.time[0] + 1
                    if hour == 24:
                        hour = 0
                    self.time = (hour, self.time[1])
            else:
                self.time = prev.time
        else:
            self.time = wlist[0][2]['time']
        # call
        if wlist[1] is None:
            if prev is None:
                raise LogException("Missing callsign", 0)
            self.callsign = prev.callsign
        else:
            self.callsign = wlist[1][2]['call']
        # freq
        if wlist[2] is None:
            if prev is None:
                raise LogException("Missing frequency", 0)
            self.freq = prev.freq
        else:
            self.freq = wlist[2][2]['freq']
        # mode
        if wlist[3] is None:
            if prev is None:
                raise LogException("Missing mode", 0)
            self.mode = prev.mode
        else:
            self.mode = wlist[3][2]['mode']
        # rst
        if self.mode == 'CW' or self.mode == 'Data':
            def_rst = '599'
        else:
            def_rst = '59'

        if wlist[4] is None:
            self.sent = def_rst
        else:
            if len(wlist[4][2]['rst']) != len(def_rst):
                raise LogException("Invalid RST for this mode", 0)
            self.sent = wlist[4][2]['rst']

        if wlist[5] is None:
            self.rcvd = def_rst
        else:
            if len(wlist[5][2]['rst']) != len(def_rst):
                raise LogException("Invalid RST for this mode", 0)
            self.rcvd = wlist[5][2]['rst']

        # optional exchange
        if wlist[6] is not None:
            self.exch = wlist[6][2]['exch']

        # SOTA ref
        if wlist[7] is not None:
            self.ref = wlist[7][2]['sota']

        # notes
        if noteselem < len(words):
            self.notes = ' '.join(x[0] for x in words[noteselem:])
        else:
            self.notes = ''

        # day adjustment for multiple day activation
        if prev:
            if prev.time[0] * 60 + prev.time[1] > self.time[0] * self.time[1]:
                self.day = prev.day + 1
            else:
                self.day = prev.day
        else:
            self.day = 0


def parse_input(handle, format=None):
    comment_line = False
    blank_line = False
    possible_blank_line = False
    activation = None
    qso = None
    errors = []
    cnt = 0
    # go though the lines
    for line in handle:
        cnt += 1
        s,d,c = line.partition('#')
        s = s.strip()
        if not s:
            if d:
                possible_blank_line = False
                comment_line = True
            elif activation and activation.qsos:
                if comment_line:
                    possible_blank_line = True
                    comment_line = False
                else:
                    blank_line = True
            continue
        comment_line = False
        if possible_blank_line:
            blank_line = True
            possible_blank_line = False
        # normal line found
        # if previous line was a blank line
        try:
            if blank_line or not activation:
                activation = Activation(s, activation)
                blank_line = False
            else:
                activation.add_qso(s)
        except LogException as e:
            errors.append((cnt, str(e), s, e.pos))

    # if any error found, print it on stderr
    if errors:
        for e in errors:
            print("{}:{}: {}\n {}\n {:>{}}".format(
                handle.name, e[0], e[1], e[2], '^', e[3] + 1),
                file=sys.stderr)
    else:
        if format == 'contest':
            activation.print_qsos(format='contest', config=os.path.splitext(handle.name)[0] + '.cts')
        elif format:
            activation.print_qsos(format=format)
        else:
            activation.print_qsos()


if __name__ == '__main__':
    # no options right now, but it may have later on
    # so check remaining args
    files = sys.argv[1:]

    # simple argument handling, replace later on with argument parsing
    if '-c' in files:
        files.remove('-c')
        contest_output = True
    else:
        contest_output = False

    if not files:
        files = ['-']
    for file in files:
        if file == '-':
            parse_input(sys.stdin)
        else:
            with open(file, 'r') as f:
                if contest_output:
                    parse_input(f, format='contest')
                else:
                    parse_input(f)
