""" This module handles contesting rules if used during the activation
Rules will be specified in separate files and the Contest class implemented
in this module will build the corresponding contest object based on
parameters specified in the activation declaration.

TODO: right now a field day contest is hardcoded, it should be externalized
from this file
"""

import re
import cabrillo
import country


prefix = re.compile(r"(?:(?=.?[a-z])[0-9a-z]{1,2}(?:(?<=3d)a)?)")


class Contest:
	""" Contest object allows to create a contest handling engine to be used
	while parsing the activation list.
	The contest is initialized with the name of the contest and additional
	parameters, after that the contest object can offer a matching function
	for the exchange and a scoring function, which also outputs a cabrillo file
	"""

	def __init__(self, name):
		""" Initialize the Contest object based on the name.
		The constructor will look for the contest definition file with the
		given name and initialize the object members from that.
		If no contest is found for that name then an exception is thrown
		"""

		# TODO: currently hardcoded for Field-Day
		if name != "fd":
			raise ValueError("Undefined contest")

		# rule for the received exchange, will be used by the qso parser
		self.exchange = re.compile(r"[0-9]{3,4}")

		# internal representation
		self.output = cabrillo.Cabrillo()
		self.exch = 0
		# multiplier is the number of countries
		self.mult = set()


	def add_qso(self, call, date, qso):
		""" Add an individual qso line to the contest list
		If the QSO does not contain received exchange and the contest does not
		allow such QSOs then it will be ignored.
		The sent exchange is automatically filled from the contest rules and
		initial parameters
		"""
		self.exch += 1
		# check call for scoring
		cty, ctyinfo = country.find(qso.callsign)
		_,band = cabrillo.clean_freq(qso.freq)
		self.mult.add((band, cty))
		if qso.callsign.endswith('/P') or qso.callsign.endswith('/M'):
			score = 3
		else:
			score = 2
		if ctyinfo['continent'] != self.continent:
			score *= 2
		self.output.add_qso(
			qso.freq,
			qso.mode,
			date,
			qso.time,
			call,
			qso.sent,
			"{:03}".format(self.exch),
			qso.callsign,
			qso.rcvd,
			getattr(qso, 'exch', '000'),
			0,
			score,
			len(self.mult))


	def configure(self, activation, config_file=None):
		""" Configure the contest header with information about the activation
		(which can contain callsign, sota reference, yoff reference, other info)
		and a config file which can hold additional contest specific information
		"""
		if config_file:
			self.output.configure_from_file(config_file)

		config = {}
		# contest is automatically configured for Field day
		config['contest'] = "FIELD-DAY"

		# get callsign from the activation
		callsign = getattr(activation, 'callsign')
		if callsign:
			config['callsign'] = callsign
			callparts = callsign.split('/')
			# portable or fixed?
			if callparts[-1] in ['P', 'M']:
				config['station'] = 2
			else:
				config['station'] = 0
			# operator field is the base callsign
			if len(callparts) > 1 and prefix.fullmatch(callparts[0]):
				callparts.pop(0)
			config['op'] = callparts[0]

		# field day location should be the sota reference or the wwff reference
		if getattr(activation, 'ref'):
			config['location'] = getattr(activation, 'ref')
			config['soapbox'] = "SOTA activation"
		elif getattr(activation, 'wwff'):
			config['location'] = getattr(activation, 'wwff')

		self.output.configure(config, True)

		# get own continent from callsign
		_, ctyinfo = country.find(callsign)
		self.continent = ctyinfo['continent']


	def __str__(self):
		""" Build a log output for the contest from the available QSOs as
		required by the contest rules, for example a Cabrillo format
		"""
		return str(self.output)
