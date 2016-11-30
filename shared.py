# shared stuff

notenames = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
gm_drums = [
    ('b', 'Acoustic Bass Drum'), ('b', 'Bass Drum 1'), ('?', 'Side Stick'),
    ('s', 'Acoustic Snare'), ('?', 'Hand Clap'), ('s', 'Electric Snare'),
    ('f', 'Low Floor Tom'), ('h', 'Closed Hi Hat'), ('f', 'High Floor Tom'),
    ('H', 'Pedal Hi-Hat'), ('g', 'Low Tom'), ('o', 'Open Hi-Hat'),
    ('g', 'Low-Mid Tom'), ('d', 'Hi Mid Tom'), ('c', 'Crash Cymbal 1'),
    ('d', 'High Tom'), ('r', 'Ride Cymbal 1'), ('C', 'Chinese Cymbal'),
    ('?', 'Ride Bell'), ('?', 'Tambourine'), ('S', 'Splash Cymbal'),
    ('?', 'Cowbell'), ('c', 'Crash Cymbal 2'), ('?', 'Vibraslap'),
    ('r', 'Ride Cymbal 2'), ('?', 'Hi Bongo'), ('?', 'Low Bongo'),
    ('?', 'Mute Hi Conga'), ('?', 'Open Hi Conga'), ('?', 'Low Conga'),
    ('?', 'High Timbale'), ('?', 'Low Timbale'), ('?', 'High Agogo'),
    ('?', 'Low Agogo'), ('?', 'Cabasa'), ('?', 'Maracas'),
    ('?', 'Short Whistle'), ('?', 'Long Whistle '), ('?', 'Short Guiro'),
    ('?', 'Long Guiro'), ('?', 'Claves'), ('?', 'Hi Wood Block'),
    ('?', 'Low Wood Block'), ('?', 'Mute Cuica'), ('?', 'Open Cuica'),
    ('?', 'Mute Triangle'), ('?', 'Open Triangle'),
    ]
standard_printseq = 'SCcRrOoHhGgDdsFfbB'

def get_note_name(inp):
    """translate note number to note name
    """
    octave, noteval = divmod(inp, 12)
    return notenames[noteval].ljust(2) + str(octave)

def getnotenum(x):
    octave = 12 * int(x[2])
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

