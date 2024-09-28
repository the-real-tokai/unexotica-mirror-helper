# unexotica-mirror-helper


[![GitHub](https://img.shields.io/github/license/the-real-tokai/unexotica-mirror-helper?color=green&label=License&style=flat)](https://github.com/the-real-tokai/unexotica-mirror-helper/blob/master/LICENSE)
[![GitHub Code Size in Bytes](https://img.shields.io/github/languages/code-size/the-real-tokai/unexotica-mirror-helper?label=Code%20Size&style=flat)](https://github.com/the-real-tokai/unexotica-mirror-helper/)
[![Twitter Follow](https://img.shields.io/twitter/follow/binaryriot?color=blue&label=Follow%20%40binaryriot&style=flat)](https://twitter.com/binaryriot)

## Synopsis

`fetchunexotica.py` is a crude Python script to create a local and streamlined mirror of the UnExoticA Amiga games module
collection available at https://www.exotica.org.uk/wiki/UnExoticA. The script will fetch all game soundtrack archives and
their box artworks: one game per directory, sorted into alphabetical parent directories (e.g. `z/Zool/*` or `a/Ambermoon/*`,
etc.). Responsibly it tries to be as gentle as possible on Exotica's server and limit requested data/ amount of requests to
a minimum (it's still a whole bunch of requests for almost ~3,000 game soundtracks, of course.)

A full sync takes between 20 minutes and 40 minutes and needs ~4 GiB of free disk space currently (27-Sep-2024). A mirror
without the CDDA rips and stripped archive files will need around ~660 MiB (around 2 GiB needed during the process.)

## Requirements

The script has only be tested with *Python 3.12* on Mac OS X aka macOS (or whatever it is called these days). It should work
with older versions of Python 3 too, but may need minor modifications. E.g the used `Path().is_relative_to()` is only available starting
with Python 3.9 and the respective code block probably would need to be disabled or modified to work with anything older than
Python 3.9.

### Optional Dependencies

* Python module `requests` (it will automatically try to fallback to `pip`'s `request` module, if not available)
* Python module `lhafile` (https://pypi.org/project/lhafile/) for smart automatic unarchiving of the downloaded archives (recommended!)
* `Tag` command (https://github.com/jdberry/tag/) used to mark problematic directories/ games. Only
the broken "Pinball Fantasies" LhA archive triggers it currently. (OS X/ macOS only; not really needed)
* `jpegoptim` command (https://github.com/tjko/jpegoptim) for optimizing box scans.


## Usage

```bash
python3 fetchunexotica.py --destination=/Volumes/MyMirrors/UnExoticA-Mirror

# (optionally) remove archives afterwards, if not needed
# (will make updating the mirror impossible though or tricky at least)
find /Volumes/MyMirrors/UnExoticA-Mirror -name 'archive.lha' -print -delete
````

```
usage: fetchunexotica.py [-V] [-h] [--destination PATH] [--filter REGEX]
                         [--skip-cdda]

Creates a clean mirror of UnExoticA.

Startup:
  -V, --version       show version number and exit
  -h, --help          show this help message and exit

Options:
  --destination PATH  Target directory for the mirror (a non existing
                      directory will be created).
  --filter REGEX      Regular expression to limit downloads to matching
                      titles (case insensitive), e.g. ".*Zool.*"
  --skip-cdda         Skip downloading archives with CDDA (*.ogg) data of
                      CD32 games.

Report bugs, request features, or provide suggestions via
https://github.com/the-real-tokai/unexotica-mirror-helper/issues
```


## History

<table>
    <tr>
        <td valign=top>1.3</td>
        <td valign=top nowrap>28-Sep-2024</td>
        <td>
			Fix: due to improper URL quoting a few of the box scans were not downloaded<br>
		    Fix: better handling of HTTP errors<br>
			New: use `jpegoptim` to shrink down box scans after download
	    </td>
    </tr>
    <tr>
        <td valign=top>1.2</td>
        <td valign=top nowrap>27-Sep-2024</td>
        <td>Initial public source code release</td>
    </tr>
</table>


## To Do

* improve the wild output and make it more readable
* better error handling
* improve update synchronization to collect new changes from the remote wiki into an existing mirror, e.g.
  handle updating existing archives/ box artworks, if needed, or skip scheduling them entirely, if there
  was no change on the wiki. Currently this isn't handled well or at all (see comments in the code.)
* a pretty index.html (or info.html or similar) per game with the meta data and cover artwork (the
  `wikidata.txt` files are a bit hard to read as it is, but may contain useful extra details that would be lost
  otherwise)