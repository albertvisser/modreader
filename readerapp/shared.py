"""shared stuff for ModReader data processing modules
"""
import os.path
import configparser
import logging

logging.basicConfig(filename='/tmp/modreader.log', level=logging.DEBUG,
                    format='%(asctime)s %(module)s %(message)s')


def log(inp):
    "local definition to allow for picking up module name in message format"
    logging.info(inp)


options = configparser.ConfigParser()
options.optionxform = lambda x: x
optionsfile = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'options.ini')
options.read(optionsfile)
standard_printseq = options['general']['printseq']
gm_drums = [(y, x) for x, y in options['gm_drums'].items()]
samp2other = {x: y for x, y in options['samp2lett'].items()}
known_files = options['general']['known_files'].split()
basedir = os.path.expanduser(options['general']['basedir'])
location = os.path.expanduser(options['general']['location'])
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
sep = {True: '', False: ' '}
empty = {True: empty_drums, False: empty_note}


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
    title = "Details of {} {}".format(filetype, filename)
    result = [title, '=' * len(title), '']
    if text:
        result.append("Description: {}".format(text))
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
        result.append("        {:>2} {}".format(ix, item))
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
    if text:
        result = ["    {:>2} {}".format(seq, text), '']
    else:
        result = []
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
            printable.append("{:>2} ".format(item))
    if printable != [pattline_start]:
        result.append(''.join(printable))
    result.append('')
    return result
