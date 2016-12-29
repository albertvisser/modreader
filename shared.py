# shared stuff

notenames = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
gm_drums = [
    ('b', 'Acoustic Bass Drum'), ('b', 'Bass Drum 1'), ('?', 'Side Stick'),
    ('s', 'Acoustic Snare'), ('?', 'Hand Clap'), ('s', 'Electric Snare'),
    ('F', 'Low Floor Tom'), ('h', 'Closed Hi Hat'), ('f', 'High Floor Tom'),
    ('H', 'Pedal Hi-Hat'), ('g', 'Low Tom'), ('o', 'Open Hi-Hat'),
    ('G', 'Low-Mid Tom'), ('d', 'Hi Mid Tom'), ('1', 'Crash Cymbal 1'),
    ('d', 'High Tom'), ('r', 'Ride Cymbal 1'), ('C', 'Chinese Cymbal'),
    ('?', 'Ride Bell'), ('?', 'Tambourine'), ('S', 'Splash Cymbal'),
    ('?', 'Cowbell'), ('2', 'Crash Cymbal 2'), ('?', 'Vibraslap'),
    ('R', 'Ride Cymbal 2'), ('?', 'Hi Bongo'), ('?', 'Low Bongo'),
    ('?', 'Mute Hi Conga'), ('?', 'Open Hi Conga'), ('?', 'Low Conga'),
    ('?', 'High Timbale'), ('?', 'Low Timbale'), ('?', 'High Agogo'),
    ('?', 'Low Agogo'), ('?', 'Cabasa'), ('?', 'Maracas'),
    ('?', 'Short Whistle'), ('?', 'Long Whistle '), ('?', 'Short Guiro'),
    ('?', 'Long Guiro'), ('?', 'Claves'), ('?', 'Hi Wood Block'),
    ('?', 'Low Wood Block'), ('?', 'Mute Cuica'), ('?', 'Open Cuica'),
    ('?', 'Mute Triangle'), ('?', 'Open Triangle'),
    ]
standard_printseq = 'SCcRrOoHhGgDdsFfbB'
per_line = 32
octave_length = 12
drum_channel = 10 # standard drums channel
note2drums = -35 # correction to calculate drum instrument for note
# note that the following just happen to have the same value but mean something different
timing_unit = 12
tick_factor = 32
time_unit = timing_unit * tick_factor
patt_start = 'pattern {:>2}:'
line_start = '            '
## pattern_header = '        '
## line_header = pattern_header + '    '
empty_note = '...'
empty_drums = '.'

def get_note_name(inp):
    """translate note number to note name
    """
    octave, noteval = divmod(inp, octave_length)
    return notenames[noteval].ljust(2) + str(octave)

def getnotenum(x):
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
    title = "Details of {} {}".format(filetype, filename)
    result = [title, '=' * len(title), '']
    if text:
        result.append("Description: {}".format(text))
    else:
        result.append("No description available")
    result.extend(['', ''])
    return result

def build_inst_list(item_list, first_line=''):
    if first_line == '':
        first_line = "Instruments:"
    result = [first_line, '']
    for ix, item in item_list:
        result.append("        {:>2} {}".format(ix, item))
    result.append('')
    return result

def build_patt_header(text=''):
    if text == '':
        text = 'Patterns per instrument:'
    return [text, '', '']

def build_patt_list(seq, text, item_list):
    result = ["    {:>2} {}".format(seq, text), '']
    printable = []
    line_start = "         "
    for ix, item in enumerate(item_list):
        if ix % 8 == 0:
            if printable:
                result.append(''.join(printable))
            printable = [line_start]
        if item == -1:
            printable.append(" . ")
        else:
            printable.append("{:>2} ".format(item))
    if printable != [line_start]:
        result.append(''.join(printable))
    result.append('')
    return result
