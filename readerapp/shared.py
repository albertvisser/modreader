"""shared stuff for ModReader data processing modules
"""
## import os.path
import pathlib
import configparser
import logging

logging.basicConfig(filename='/tmp/modreader.log', level=logging.DEBUG,
                    format='%(asctime)s %(module)s %(message)s')


def log(inp):
    "local definition to allow for picking up module name in message format"
    logging.info(inp)


options = configparser.ConfigParser()
options.optionxform = lambda x: x
optionsfile = pathlib.Path(__file__).parents[1] / 'options.ini'
options.read(str(optionsfile))
standard_printseq = options['general']['printseq']
gm_drums = [(y, x) for x, y in options['gm_drums'].items()]
samp2other = dict(options['samp2lett'])
known_files = []
for item in options['general']['known_files'].split():
    known_files.extend([item, item.upper()])
basedir = pathlib.Path(options['general']['basedir']).expanduser()
location = pathlib.Path(options['general']['location']).expanduser()
notenames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
max_lines = per_line = 32
octave_length = 12
drum_channel = 10  # standard drums channel
note2drums = -35   # correction to calculate drum instrument for note
# note that the following just happen to have the same value but mean something different
timing_unit = 12
tick_factor = 32
time_unit = timing_unit * tick_factor
patt_start = 'pattern {:>2}:'
line_start = '            '
empty_note = '...'
empty_drums = '.'
sep_long = '   '
sep = {True: '', False: ' '}
empty = {True: empty_drums, False: empty_note}


def eventsep(is_drumtrack, short_format):
    "return the correct event separator for a give track type"
    if is_drumtrack and not short_format:
        return sep_long
    return sep[is_drumtrack]


def get_note_name(inp):
    """translate note number to note name
    """
    octave, noteval = divmod(inp, octave_length)
    return notenames[noteval].ljust(2) + str(octave)


def getnotenum(x):
    """translate note name to note number
    """
    octave = octave_length * int(x[2])
    seq = notenames.index(x[:2].strip())
    return octave + seq


def get_inst_name(inp):
    """translate note number to drum instrument name
    assumes standard drumkit mapping
    """
    try:
        return gm_drums[inp][0]
    except IndexError:
        return ' '


def build_header(filetype, filename, text=''):
    """return standard header for "general" file
    """
    title = f"Details of {filetype} {filename}"
    result = [title, '=' * len(title), '']
    if text:
        result.append(f"Description: {text}")
    else:
        result.append("No description available")
    result.extend(['', ''])
    return result


def build_inst_list(item_list, first_line=''):
    """return instrument list in standard format
    """
    if first_line == '':
        first_line = "Instruments:"
    result = [first_line, '']
    for ix, item in item_list:
        result.append(f"        {ix:>2} {item}")
    result.append('')
    return result


def build_patt_header(text=''):
    """return standard header for pattern
    """
    if text == '':
        text = 'Patterns per instrument:'
    return [text, '']


def build_patt_list(seq, text, item_list):
    """return pattern list in standard format
    """
    result = [f"    {seq:>2} {text}", ''] if text else []
    printable = []
    pattline_start = "         "
    for ix, item in enumerate(item_list):
        if ix % 8 == 0:
            if printable:
                result.append(''.join(printable))
            printable = [pattline_start]
        if item == -1:
            printable.append(" . ")
        else:
            printable.append(f"{item:>2} ")
    if printable != [pattline_start]:
        result.append(''.join(printable))
    result.append('')
    return result
