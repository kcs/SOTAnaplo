""" This module allows identifying the country/continent of a given callsign
The country information is loaded from the cty.dat file which should be
downloaded from http://www.country-files.com/big-cty/
"""

import re

countries = {}
fixcalls = {}
prefixes = []
country = None

prefixfilter = re.compile(r'(?:(?P<exact>=)?(?P<prefix>[A-Z0-9/]+)[][(){}<>~A-Z0-9]*)|;')
with open("cty.dat", 'r') as ctyfile:
	for line in ctyfile:
		if country is None:
			# first line
			country = [x.strip() for x in line.split(':')]
			country_code = country[7]
			countries[country_code] = {'name': country[0],
			                           'cq': country[1],
			                           'itu': country[2],
			                           'continent': country[3]}
		else:
			# prefix lines
			for prefix in prefixfilter.finditer(line):
				if prefix.group(0) == ';':
					# end of country data
					country = None
					break
				elif prefix.group('exact'):
					# exact call
					fixcalls[prefix.group('prefix')] = country_code
				else:
					# normal prefix
					prefixes.append((prefix.group('prefix'), country_code))


def find(call):
	if call in fixcalls:
		code = fixcalls[call]
	cprefixes = [x for x in prefixes if call.startswith(x[0])]
	if cprefixes:
		code = max(cprefixes, key = lambda z: len(z[0]))[1]
	else:
		raise ValueError('Unrecognized callsign')
	return code, countries[code]
