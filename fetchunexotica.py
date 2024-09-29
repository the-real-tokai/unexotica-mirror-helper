#!/usr/local/bin/python3.12

"""
	fetchunexotica.py
	Creates a clean personal mirror of UnExoticA's Amiga Game Music
	Module Collection.

	Copyright © 2024 Christian Rosentreter

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <https://www.gnu.org/licenses/>.

	$Id: fetchunexotica.py 27 2024-09-29 21:59:22Z tokai $
"""

import urllib
import os
import sys
import re
import pathlib
import subprocess
import argparse
#import unicodedata

try:
	import requests
except ImportError:
	import sysconfig
	sys.path.append(os.path.join(sysconfig.get_paths()["purelib"], 'pip', '_vendor'))
	import requests

# Optional LhA archive unpacking support.
#
# See:
#	https://pypi.org/project/lhafile/
#	https://github.com/FrodeSolheim/python-lhafile/
#
has_lhafile = False
try:
	import lhafile
	has_lhafile = True
except ImportError:
	try:
		# 2nd try: import it from a local "./vendor" path
		sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor'))
		import lhafile
		has_lhafile = True
	except ImportError:
		pass



__author__  = 'Christian Rosentreter'
__version__ = '1.4'
__all__     = []



class Title():
	""" Represents a game title. """

	url_format = 'https://www.exotica.org.uk/mediawiki/index.php?{}'

	def __init__(self, raw, output_directory):
		#raw            = raw.replace(' (game)', '')  -> can't remove the extra things here, else 2 entries on the wiki can conflict, e.g. '1990' vs '1990 (game)'
		self.raw       = raw
		self.directory = raw.replace(':', ' ~').replace('?', '_').replace('/', '_').replace(' (game)', '')  # TODO: ignore unicode NFC/NFK for now (does it matter?)
		# see: https://www.mediawiki.org/wiki/Manual%3aPage_title
		self.url       = self.url_format.format(urllib.parse.urlencode({'title': raw.replace(' ', '_'), 'action': 'raw'}))

		# Handle some articles (move them to the back)
		if self.directory[0:4].upper() in ('THE ', 'DER ', 'DAS ', 'LES '):  # skipping German 'Die ' for now, because it could me '[to] die'
			self.directory = self.directory[4:] + ', ' + self.directory[0:3]
		elif self.directory[0:3].upper() in ('LE '):
			self.directory = self.directory[3:] + ', ' + self.directory[0:2]
		elif self.directory[0:2].upper() in ('A '):
			self.directory = self.directory[2:] + ', ' + self.directory[0:1]

		letter = self.directory[0:1].lower()
		if letter in "abcdefghijklmnopqrstuvwxyz":
			self.letter = letter
		else:
			self.letter = '0-9'

		self.path = os.path.join(output_directory, self.letter, self.directory)

	def __repr__(self):
		return "'" + self.raw + "'"


class Archive():
	""" Represents a game archive file. """

	# e.g. output: http://files.exotica.org.uk/?file=exotica/media%2Faudio%2FUnExoticA%2FGame%2FRiley_Mark%2FA-10_Tank_Killer.lha
	#      input:  media/audio/UnExoticA/Game/Riley_Mark/A-10_Tank_Killer.lha

	url_format = 'https://files.exotica.org.uk/?{}'

	def __init__(self, filelink, destination_directory):
		self.url      = self.url_format.format(urllib.parse.urlencode({'file': 'exotica/' + filelink}))
		self.basedir  = pathlib.Path(destination_directory).resolve()  # resolve it into an absolute path
		self.filename = os.path.join(destination_directory, 'archive.lha')

	def is_relative_to_basedir(self, verify_path):
		""" Verifies that `verify_path` is relative to destination and not somewhere else on the disk. """

		# TODO: Does this whole check work reliably? I have no idea.
		#
		# Note: We need at least Python 3.9. `.is_relative_to()` is a string based comparision, see:
		#       https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.is_relative_to
		#
		tmp = pathlib.Path(verify_path).resolve()  # should make it absolute
		try:
			# Note: Yikes, my pylint still runs with 3.7 not 3.9++, so it triggers an error we need to silence
			if tmp.is_relative_to(self.basedir):  # pylint: disable=no-member
				return True
		except AttributeError:
			if str(tmp).startswith(str(self.basedir)):  # for Python versions older than 3.9, feels pretty equivalent.
				return True
		return False

	def extract(self):
		""" Extracts all files from the archive. """
		try:
			lha   = lhafile.Lhafile(self.filename)
			files = [info.filename for info in lha.infolist()]

			# determine a common directory prefix (we skip that during unarchiving to
			# get a flat dump of the archive content as we already have a sub directory
			# per game)
			common_base = None
			strip_base = False
			for filename in files:
				# Some archives have Windows style paths with backslashes, this seems to handle that
				convert = pathlib.Path(pathlib.PureWindowsPath(filename).as_posix())
				newbase = convert.parts[0]
				if common_base is None:
					common_base = newbase
					strip_base = True
				elif common_base != newbase:
					print(convert, "-", common_base, "-", newbase)
					strip_base = False
					break
			print(">>>> strip base:", strip_base, "->", common_base)

			for filename in files:
				convert = pathlib.Path(pathlib.PureWindowsPath(filename).as_posix())

				# strip the base, if possible
				if strip_base and convert.parts[0] == common_base:
					convert = pathlib.Path(*convert.parts[1:])

				outpath     = pathlib.Path(os.path.join(self.basedir, os.path.dirname(convert))).resolve()
				outfilename = pathlib.Path(os.path.join(self.basedir, convert)).resolve()
				#print("Orig:", filename, "Converted:", convert, "Output:", outpath, outfilename)

				if not self.is_relative_to_basedir(outfilename):
					print("\033[31mERROR: <{}> is not in our target directory <{}>, potential path traversal attack or broken archive. \033[0m".format(outfilename, self.basedir), file=sys.stderr)
					return  # sys.exit(20)

				if len(convert.parts) > 1:
					os.makedirs(outpath, exist_ok=True)
				if len(convert.parts) > 0:
					print("\033[37m>>>> +++ Extracting", filename, "to", outfilename, "\033[0m")
					with open(outfilename, 'wb') as f:
						f.write(lha.read(filename))

		except lhafile.lhafile.BadLhafile as e:
			print("\033[31mERROR: <{}> has an issue:\033[0m".format(self.filename), e, file=sys.stderr)
			if sys.platform.lower() == 'darwin':
				try:
					# Try to add a 'Red' tag, so it's clear later in Finder that something went wrong with it.
					subprocess.run(["/usr/local/bin/tag", "-a", "Red", self.basedir], check=False)
				except:  # pylint: disable=bare-except
					pass  # ignore all subprocess errors



class BoxScan():
	""" Represents a game box scan (Cover) """

	# see: https://www.mediawiki.org/wiki/Help:Linking_to_files#Direct_links_from_external_sites
	url_format = 'https://www.exotica.org.uk/wiki/Special:Redirect/file/{}'

	def __init__(self, filelink, destination_directory):
		self.url = self.url_format.format(urllib.parse.quote(filelink))
		suffix   = '.unknown'
		if filelink[-4:] in ['.png', '.jpg']:
			suffix = filelink[-4:]
		self.filename = os.path.join(destination_directory, 'Cover' + suffix)
		self.suffix = suffix

	def optimize(self):
		""" Tries to shrink file sizes of downloaded JPEG/JFIF files. """
		if self.suffix != '.jpg':
			return
		print("\033[37m>>>> +++ Optimizing", self.filename, "\033[0m")
		try:
			# TODO: switching to MozJpeg may be more effective
			subprocess.run(["jpegoptim", "--totals", "--preserve", "--preserve-perms", "--strip-all", self.filename], check=True)
		except subprocess.CalledProcessError as e:
			print("\033[31mCouldn't optimize box scan <{}>.\033[0m".format(self.filename), e, file=sys.stderr)
		except:  # pylint: disable=bare-except
			pass  # ignore all remaining subprocess errors



def main():
	""" Rock'n'Roll'n'Amiga! """

	ap = argparse.ArgumentParser(
		description=('Creates a clean mirror of UnExoticA\'s Amiga Game Music Module Collection.'),
		epilog='Report bugs, request features, or provide suggestions via https://github.com/the-real-tokai/unexotica-mirror-helper/issues',
		add_help=False,
	)

	g = ap.add_argument_group('Startup')
	g.add_argument('-V', '--version',      action='version',               help="show version number and exit", version='%(prog)s {}'.format(__version__), )
	g.add_argument('-h', '--help',         action='help',                  help='show this help message and exit')

	g = ap.add_argument_group('Options')
	g.add_argument('--destination', metavar='PATH',  type=str, help='Target directory for the mirror (a non existing directory will be created).', default='./UnExoticA-Mirror')
	g.add_argument('--filter',      metavar='REGEX', type=str, help='Regular expression to limit downloads to matching titles (case insensitive), e.g. ".*Zool.*"', default='.')
	g.add_argument('--skip-cdda',                    action='store_true', help='Skip downloading archives with CDDA (*.ogg) data of CD32 games.')
	user_input = ap.parse_args()

	output_directory = os.path.realpath(os.path.expanduser(user_input.destination))
	print("Mirroring data to <{}>".format(output_directory))

	filter_regex  = re.compile(user_input.filter, re.IGNORECASE)


	session = requests.Session()
	session.headers.update({
		'User-Agent': 'UnExoticA Mirror Helper/{} +https://github.com/the-real-tokai/unexotica-mirror-helper'.format(__version__)
	})
	assert_status_hook = lambda response, *args, **kwargs: response.raise_for_status()  # pylint: disable=unnecessary-lambda-assignment
	session.hooks["response"] = [assert_status_hook]


	# ------------------------------------------------------------------------------------------------
	#  Build up the list of game titles that shall be fetched
	#

	titles = []

	# Note: click on "edit" in the wiki and then replace "action=edit" with "action=raw" in the URL
	response = session.get('https://www.exotica.org.uk/mediawiki/index.php?title=UnExoticA/Games_By_Title/ALL&action=raw', timeout=20)
	text     = response.content.decode('UTF-8')

	collecting = False
	for line_id, line in enumerate(iter(text.splitlines())):
		#print(lineid, line)
		if line == '<!-- BEGIN AUTO:INDEX -->':
			collecting = True
			continue
		if line == '<!-- END AUTO:INDEX -->':
			break
		if collecting and line[0:3] == '|[[':
			fields = line.split('|')
			title  = fields[1].replace('[', '').replace(']', '')
			if filter_regex.match(title):
				titles.append(Title(title, output_directory))

	print("Following titles matched the filter:", titles)


	# ############################################################################################## #
	# ++++++ DEFAULT BLOCKAGE ++++++                                                                 #
	# ############################################################################################## #
	#
	#  Note: This limits things to a max. of 10 entries by default.  Disabling this check (`if 0:`) or
	#        using an alternative regular expression (e.g. `.*`) will workaround this.  But BEFORE you
	#        do this *MAKE SURE* you understand the implications to the service. It is best to contact
	#        the maintainers of "exotica.co.uk" first BEFORE doing any full mirroring. Ideally someone
	#        else already made a mirror and shares it via BitTorrent and you will not have to parasite
	#        any server ressources unnecessarily. Be considerate!
	#
	#        e.g.:
	#        <insert magnet link(s) here>
	#
	if 1:  # pylint: disable=using-constant-test
		if user_input.filter == '.':
			print("\033[35m++++ Limiting to 10 entries. This will not be a full mirror! ++++\033[0m")
			titles = titles[0:10]  # limit to 10 entries.
	# ############################################################################################## #



	# ------------------------------------------------------------------------------------------------
	#  Build up the lists of archives and box scans that shall be fetched
	#

	downloadlink_regex  = re.compile(r'\|file=(.*\.lha)\|')
	coverfilename_regex = re.compile(r'\|boxscan=(.*\.(jpg|png))')

	archives = []
	boxscans = []

	for title_id, title in enumerate(titles):
		print("\033[1mProcessing...", title.path, '\033[0m ---', title.raw, '---\033[37m', title.url, '\033[0m') #, r.status_code)
		os.makedirs(title.path, exist_ok=True)

		datafile = os.path.join(title.path, 'wikidata.txt')
		olddata  = None
		try:
			with open(datafile, 'rb') as f:
				olddata = f.read()
		except FileNotFoundError:
			pass

		try:
			r = session.get(title.url, timeout=10)
			newdata = r.content

			if olddata != newdata:
				if olddata is not None:
					print(">>>> \033[32mwiki entry was updated compared to previous run.\033[0m")
				else:
					print(">>>> \033[32mnew wiki entry discovered.\033[0m")
				with open(datafile, 'wb') as f:
					f.write(newdata)
			else:
				print(">>>> wiki entry was not updated, no change required.")

			# TODO: Only add if the wiki entry (above) was updated
			#
			# TODO: Check file date and use If-Modified-Since header and then handle the http return
			#       code while downloading
			#
			decoded = newdata.decode('UTF-8')
			link = downloadlink_regex.search(decoded).group(1)
			if (user_input.skip_cdda is True and not '_CDDA' in link) or (user_input.skip_cdda is False):
				a = Archive(link, title.path)
				if not os.path.isfile(a.filename):
					print(">>>> new archive scheduled for download:", a.url, "---", a.filename)
					archives.append(a)
				else:
					print(">>>> archive already downloaded.")  # TODO: archive may not be the same though
			else:
				print(">>>> skip CDDA archive (CDDA filter active).")

			link = coverfilename_regex.search(decoded).group(1)
			if link != 'BlankBoxscan.png':
				bs = BoxScan(link, title.path)
				if not os.path.isfile(bs.filename):
					print(">>>> new box scan scheduled for download:", bs.url, "---", bs.filename)
					boxscans.append(bs)
				else:
					print(">>>> box scan already downloaded.")

		except requests.exceptions.RequestException as e:
			print("\033[31mCouldn't fetch <{}>.\033[0m".format(title.url), e, file=sys.stderr)
		except AttributeError as e:
			print("\033[31mCouldn't extract link(s).\033[0m", e, file=sys.stderr)



	# ------------------------------------------------------------------------------------------------
	#  Download all scheduled archives
	#

	for archive_id, archive in enumerate(archives):

		print("Fetching <{}>…".format(archive.url))

		try:
			r = session.get(archive.url, timeout=20)
			data = r.content

			# https://en.wikipedia.org/wiki/LHA_(file_format)
			# check for -lhX-
			if (data[2] != 0x2d or  # -
			    data[3] != 0x6c or  # l
			    data[4] != 0x68 or  # h
			    # skip data[5]
			    data[6] != 0x2d):   # -
				raise ValueError('Not an lha archive.')

			print(">>>> Saving to", archive.filename)
			with open(archive.filename, 'wb') as f:
				f.write(data)

			if has_lhafile:
				archive.extract()
			else:
				print(">>>> Skip extracting, no 'lhafile' module available.", file=sys.stderr)

		except requests.exceptions.RequestException as e:
			print("\033[31mCouldn't download archive <{}>.\033[0m".format(archive.url), e, file=sys.stderr)
		except ValueError as e:
			print("\033[31mCouldn't handle file <{}>. May not be an archive.\033[0m".format(archive.url), e, file=sys.stderr)



	# ------------------------------------------------------------------------------------------------
	#  Download all scheduled box scans
	#

	for bs_id, bs in enumerate(boxscans):

		print("Fetching <{}>…".format(bs.url))

		try:
			r = session.get(bs.url, timeout=20)
			data = r.content

			print(">>>> Saving to", bs.filename)
			with open(bs.filename, 'wb') as f:
				f.write(r.content)

			bs.optimize()

		except requests.exceptions.RequestException as e:
			print("\033[31mCouldn't download box scan <{}>.\033[0m".format(bs.url), e, file=sys.stderr)


if __name__ == '__main__':
	main()
