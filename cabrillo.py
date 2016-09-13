""" Cabrillo output generator
This is a generic cabrillo format generator which can be used by the contest
builder to create an output
"""

cbr_file = """START-OF-LOG: 3.0
{fields}
{qsos}
END-OF-LOG:"""

contests = [
    "AP-SPRINT",
    "ARRL-10",
    "ARRL-160",
    "ARRL-DX-CW",
    "ARRL-DX-SSB",
    "ARRL-RR-PH",
    "ARRL-RR-DIG",
    "ARRL-RR-CW",
    "ARRL-SCR",
    "ARRL-SS-CW",
    "ARRL-SS-SSB",
    "ARRL-UHF-AUG",
    "ARRL-VHF-JAN",
    "ARRL-VHF-JUN",
    "ARRL-VHF-SEP",
    "ARRL-RTTY",
    "BARTG-RTTY",
    "CQ-160-CW",
    "CQ-160-SSB",
    "CQ-WPX-CW",
    "CQ-WPX-RTTY",
    "CQ-WPX-SSB",
    "CQ-VHF",
    "CQ-WW-CW",
    "CQ-WW-RTTY",
    "CQ-WW-SSB",
    "DARC-WAEDC-CW",
    "DARC-WAEDC-RTTY",
    "DARC-WAEDC-SSB",
    "DL-DX-RTTY",
    "DRCG-WW-RTTY",
    "FCG-FQP",
    "IARU-HF",
    "JIDX-CW",
    "JIDX-SSB",
    "NAQP-CW",
    "NAQP-SSB",
    "NA-SPRINT-CW",
    "NA-SPRINT-SSB",
    "NCCC-CQP",
    "NEQP",
    "OCEANIA-DX-CW",
    "OCEANIA-DX-SSB",
    "RDXC",
    "RSGB-IOTA",
    "SAC-CW",
    "SAC-SSB",
    "STEW-PERRY",
    "TARA-RTTY",
    "*"
]

stations = [
    "FIXED",
    "MOBILE",
    "PORTABLE",
    "ROVER",
    "ROVER-LIMITED",
    "ROVER-UNLIMITED",
    "EXPEDITION",
    "HQ",
    "SCHOOL",
]

bands = {
    '160M'   : ( 1.8, 2.0 ),
    '80M'    : ( 3.5, 4.0 ),
    '40M'    : ( 7.0, 7.3 ),
    '20M'    : ( 14.0, 14.35 ),
    '15M'    : ( 21.0, 21.45 ),
    '10M'    : ( 28.0, 29.7 ),
    '6M'     : ( 50.0, 54.0 ),
    '4M'     : ( 70.0, 70.5),
    '2M'     : ( 144.0, 148.0 ),
    '222'    : ( 219.0, 225.0 ),
    '432'    : ( 420.0, 450.0 ),
    '902'    : ( 902.0, 928.0 ),
    '1.2G'   : ( 1240.0, 1300.0 ),
    '2.3G'   : ( 2300.0, 2450.0 ),
    '3.4G'    : ( 3400.0, 3475.0 ),
    '5.7G'    : ( 5650.0, 5850.0 ),
    '10G'    : ( 10000.0, 10500.0 ),
    '24G' : ( 24000.0, 24250.0 ),
    '47G'    : ( 47000.0, 47200.0 ),
    '75G'    : ( 75500.0, 81500.0 ),
    '119G'  : ( 122250.0, 123000.0 ),
    '142G'    : ( 134000.0, 141000.0 ),
    '241G'    : ( 241000.0, 250000.0 ),
}

fields = [
("CALLSIGN", "", "*"),
("CONTEST", "", contests),
("CATEGORY-ASSISTED", "", ["ASSISTED", "NON-ASSISTED"]),
("CATEGORY-BAND", "", ["ALL", "*"]),
("CATEGORY-MODE", "", ["SSB", "CW", "RTTY", "FM", "MIXED"]),
("CATEGORY-OPERATOR", "", ["SINGLE-OP", "MULTI-OP", "CHECKLOG"]),
("CATEGORY-POWER", "", ["HIGH", "LOW", "QRP"]),
("CATEGORY-STATION", "", stations),
("CATEGORY-TIME", "", ["6-HOURS", "12-HOURS", "24-HOURS"]),
("CATEGORY-TRANSMITTER", "", ["ONE", "TWO", "LIMITED", "UNLIMITED", "SWL"]),
("CATEGORY-OVERLAY", "", ["CLASSIC", "ROOKIE", "TB-WIRES", "NOVICE-TECH", "OVER-50"]),
("CERTIFICATE", "", ["YES", "NO"]),
("CLAIMED-SCORE", "{score}", None),
("CLUB", "", "*"),
("CREATED-BY", "SOTAnaplo v0.1", None),
("EMAIL", "", "*"),
("LOCATION", "", "*"),
("NAME", "", "*"),
("ADDRESS", "", "*"),
("ADDRESS-CITY", "", "*"),
("ADDRESS-STATE-PROVINCE", "", "*"),
("ADDRESS-POSTALCODE", "", "*"),
("ADDRESS-COUNTRY", "", "*"),
("OPERATORS", "", "*"),
("OFFTIME", "", "*"),
("SOAPBOX", "", "*")
]

cbr_qso = "QSO: {f:>5} {m} {d} {time:04} {sc:13} {sr:>3} {se:6} {rc:13} {rr:>3} {re:6} {t}"

cbr_mode = {
	"SSB": "PH",
	"USB": "PH",
	"LSB": "PH",
	"AM": "PH",
	"CW": "CW",
    "FM": "FM",
	"RTTY": "RY"
}


def merge_field(a,b):
	if not a:
		return b
	if type(a) is list:
		return a + [b]
	return [a, b]


def clean_freq(f):
	""" return the frequency and the corresponding band cleaned upper
	for cabrillo format
	"""
	if f.endswith('MHz'):
		freq = float(f[:-3])
	elif f.endswith('kHz'):
		freq = float(f[:-3]) / 1000
	elif f.endswith('GHz'):
		freq = float(f[:-3]) * 1000
	else:
		freq = float(f)

	if freq < 30:
		nfreq = round(freq * 1000)
	elif freq < 1000:
		nfreq = round(freq)
	elif freq < 10000:
		nfreq = "{:.1}G".format(freq / 1000)
	else:
		nfreq = "{}G".format(round(freq / 1000))

	for k,v in bands.items():
		if freq >= v[0] and freq <= v[1]:
			band = k
			break

	return nfreq, band

class Cabrillo:
	""" This is an object containing all the information needed for the
	Cabrillo header and the QSOs
	"""
	def __init__(self, config=None):
		""" Initialize the generator object with an optional config
		"""

		self.score = 0
		self.mult = 0
		self.qsos = []
		self.fields = {}

		# qso information by majority vote
		self.mode = None
		self.band = None

		if config:
			self.configure(config)


	def configure(self, config):
		""" Configure the contest fields
		The config parameter must be list of 26 elements either specifying the
		text to be inserted to the given field or the index of the available
		field contents
		"""
		if len(config) != len(fields):
			raise ValueError("Invalid Cabrillo configuration")

		for i in range(len(fields)):
			if config[i] is not None:
				if type(config[i]) is int:
					if fields[i][2][config[i]] != '*':
						self.fields[i] = fields[i][2][config[i]]
				else:
					self.fields[i] = config[i]
			elif fields[i][1] and i not in self.fields:
				self.fields[i] = fields[i][1]


	def configure_from_file(self, config_file):
		""" Configure the contest fields reading them from a file
		Only certain fields can be configured this way
		"""
		config = [None] * len(fields)
		# parse the config file for additional configurations
		with open(config_file, 'r', encoding='utf-8') as f:
			i = 0
			for line in f:
				i += 1
				line = line.strip()
				if line:
					code = line.split('=',1)
					if len(code) != 2 or not code[0] or not code[1]:
						raise ValueError("Invalid configuration line {}".format(i))
					if code[0] == 'name':
						if config[17]:
							raise ValueError("Field `name` given multiple times")
						config[17] = code[1]
					elif code[0] == 'email':
						if config[15]:
							raise ValueError("Field `email` given multiple times")
						config[15] = code[1]
					elif code[0] == 'address':
						config[18] = merge_field(config[18], code[1])
					elif code[0] == 'city':
						config[19] = merge_field(config[19], code[1])
					elif code[0] == 'state':
						config[20] = merge_field(config[20], code[1])
					elif code[0] == 'province':
						config[20] = merge_field(config[20], code[1])
					elif code[0] == 'postalcode':
						config[21] = merge_field(config[21], code[1])
					elif code[0] == 'country':
						config[22] = merge_field(config[22], code[1])
					elif code[0] == 'op':
						config[23] = merge_field(config[23], code[1])
					elif code[0] == 'category':
						cats = code[1].split()
						for cat in cats:
							if cat == 'sosb':
								config[5] = 0
								config[3] = 1
							elif cat == 'somb':
								config[5] = 0
								config[3] = 0
							elif cat == 'momb':
								config[5] = 1
								config[3] = 0
							# power
							elif cat.upper() in fields[6][2]:
								config[6] = fields[6][2].index(cat.upper())
							# mode
							elif cat.upper() in fields[4][2]:
								config[4] = fields[4][2].index(cat.upper())
							elif cat == 'assisted':
								config[2] = 0
							# TODO maybe other categories
					elif code[0] == 'club':
						if config[13]:
							raise ValueError("Field `club` given multiple times")
						config[13] = code[1]
					else:
						raise ValueError('Invalid configuration in line {}'.format(i))
		# if not specified non-assisted is default
		if config[2] is None:
			config[2] = 1
		# if op not specified send this as checklog
		if config[5] is None:
			config[5] = 2
		# normally only one transmitter
		if config[9] is None:
			config[9] = 0

		self.configure(config)



	def add_qso(self, freq, mode, date, time, call_sent, rst_sent, exch_sent, call_rcvd, rst_rcvd, exch_rcvd, t, score, mult):
		nfreq, band = clean_freq(freq)
		self.qsos.append(cbr_qso.format(
				f = nfreq,
				m = cbr_mode.get(mode.upper(), mode),
				d = date.strftime("%Y-%m-%d"),
				time = time[0] * 100 + time[1],
				sc = call_sent.upper(),
				sr = rst_sent,
				se = exch_sent,
				rc = call_rcvd.upper(),
				rr = rst_rcvd,
				re = exch_rcvd,
				t = t
			))
		self.score += score
		self.mult = mult

		if not self.mode and mode.upper() in fields[4][2]:
			self.mode = fields[4][2].index(mode.upper())
		elif mode.upper() in fields[4][2] and self.mode != fields[4][2].index(mode.upper()):
			self.mode = 4

		if self.band is None:
			self.band = band
		elif self.band != band:
			self.band = 0


	def fields_str(self):
		for i in range(len(fields)):
			if i in self.fields:
				if type(self.fields[i]) in [list, tuple]:
					for f in self.fields[i]:
						yield "{}: {}".format(fields[i][0], f)
				else:
					yield "{}: {}".format(fields[i][0], self.fields[i])
			# implicit guesses of band and mode
			elif i == 3 and self.band is not None:
				yield "{}: {}".format(fields[3][0], fields[3][2][0] if self.band == 0 else self.band)
			elif i == 4 and self.mode is not None:
				yield "{}: {}".format(fields[4][0], fields[4][2][self.mode])


	def __str__(self):
		return cbr_file.format(
			fields = "\n".join(self.fields_str()).format(score=self.score * self.mult),
			qsos = "\n".join(self.qsos)
		)
