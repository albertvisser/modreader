"""
Het idee achter deze module is om na het lezen van de bestanden
de patterns uit te schrijven
"""
import collections
import pprint

noteval = dict(zip([
    int(x) for x in """\
1712 1616 1524 1440 1356 1280 1208 1140 1076 1016  960  906
 856  808  762  720  678  640  604  570  538  508  480  453
 428  404  381  360  339  320  302  285  269  254  240  226
 214  202  190  180  170  160  151  143  135  127  120  113
 107  101   95   90   85   80   75   71   67   63   60   56
""".split()], [
    x.replace('-', ' ') for x in """\
 C-0  C#0  D-0  D#0  E-0  F-0  F#0  G-0  G#0  A-0  A#0  B-0
 C-1  C#1  D-1  D#1  E-1  F-1  F#1  G-1  G#1  A-1  A#1  B-1
 C-2  C#2  D-2  D#2  E-2  F-2  F#2  G-2  G#2  A-2  A#2  B-2
 C-3  C#3  D-3  D#3  E-3  F-3  F#3  G-3  G#3  A-3  A#3  B-3
 C-4  C#4  D-4  D#4  E-4  F-4  F#4  G-4  G#4  A-4  A#4  B-4
""".split()]))
notes = ['C ', 'C#', 'D ', 'D#', 'E ', 'F ', 'F#', 'G ', 'G#', 'A ', 'A#', 'B ']

def getstring(data):
    result = ''
    for bytechar in data:
        if bytechar == b'\x00':
            continue
        result += str(bytechar)
    return result

def get_sample(data):
    name = ''
    for bytechar in data[:22]:
        if int(bytechar) > 0:
            name += chr(bytechar) # str(bytechar, encoding='ascii')
    stats = [int(x) for x in data[22:]]
    return name, stats

def get_playseq(data, length):
    result = []
    highpatt = 0
    for bytechar in data[:length]:
        test = int(bytechar)
        result.append(test)
        if test > highpatt:
            highpatt = test
    return result, highpatt

def get_notedata(data):
    sampnum = data[0] & 240
    sampnum += data[2] >> 4
    period = data[0] & 15
    period *= 256
    period += data[1]
    note = noteval[period] if period else 0
    effectnum = data[2] & 15
    effectparm = data[3]
    return sampnum, note, effectnum, effectparm

def getnotenum(x):
    octave = 12 * int(x[2])
    seq = notes.index(x[:2])
    return octave + seq

class ModFile:

    def __init__(self, filename):
        self.filename = filename
        self.read()

    def read(self):
        self.samples = {}
        self.patterns = {}
        with open(self.filename, 'rb') as _in:

            self.name = str(_in.read(20), encoding='ascii')
            for x in range(31):
                name, stats = get_sample(_in.read(30))
                if name or stats[:2] not in ([0, 0], [1, 0], [1, 0]):
                    self.samples[x] = name, stats

            songlength = ord(_in.read(1))
            self.restart = ord(_in.read(1))
            self.playseq, self.highpatt = get_playseq(_in.read(128), songlength)
            self.modtype = str(_in.read(4), encoding='ascii')
            if self.modtype in ('M.K.', '4CHN', 'FLT4'):
                channelcount = 4
            elif self.modtype in ('6CHN'):
                channelcount = 6
            elif self.modtype in ('8CHN', 'FLT8'):
                channelcount = 8

            for x in range(self.highpatt):
                pattern = []
                for y in range(64):
                    track = []
                    for z in range(channelcount):
                        track.append([x for x in _in.read(4)])
                    pattern.append(track)
                self.patterns[x] = pattern

    def print_module_details(self, _out, sample_list=None):
        printable = "Details of module {}".format(self.filename)
        data = [printable, "=" * len(printable), '',
            'description: ' + self.name.rstrip(chr(0)), '']
        for sample_number, sample_data in self.samples.items():
            sample_name = sample_data[0]
            sample_string = ''
            if sample_list:
                for sampnum, sampstr in sample_list:
                    if sampnum == sample_number + 1:
                        sample_string = sampstr.join((' (', ')'))
            data.append(("sample {:>2}: {}".format(sample_number + 1,
                sample_name + sample_string)))
        ## print(test.restart)
        ## print(test.highpatt)
        ## print(test.modtype)
        data.append('\npatterns:')
        printable = '          '
        count = 8
        for ix, x in enumerate(self.playseq):
            printable += '{:>2} '.format(x)
            if (ix + 1) % count == 0:
                data.append(printable)
                printable = '          '
        data.append(printable)
        for text in data:
            print(text, file=_out)


    def print_drums(self, sample_list, printseq, _out):
        """collect the drum sample events and print them together

        sample_list is a list of pattern numbers associated with the instruments
        to print on this event, e.g. ((1, 'b'), (2, 's'), (4, 'bs'), (7, 'bsh'))
        printseq indicates the sequence to print these top to bottom e.g. 'hsb'
        stream is a file-like object to write the output to
        """
        # hier moet ook input bij die samples mapt op specifieke instrumenten, bv
        # dit is de bassdrum, dit is de snare, en zelfs: dit is zowel bassdrum als snare
        # (of dit aangeven d.m.v. de letter(s) die in de partituur getoond moeten worden
        all_events = collections.defaultdict(lambda: collections.defaultdict(list))
        maxlen = {}
        for pattnum, pattern in self.patterns.items():
            last_event = False
            for ix, track in enumerate(pattern):
                for event in track:
                    samp, note, effect, _ = get_notedata(event)
                    for sampnum, instruments in sample_list:
                        if samp == sampnum:
                            for ins in instruments:
                                all_events[pattnum][ins].append(ix)
                        if effect == 13:
                            last_event = True
                if last_event:
                    maxlen[pattnum] = ix
                    break
        for pattnum, pattern in all_events.items():
            print('pattern', pattnum, file=_out)
            try:
                pattlen = maxlen[pattnum]
            except KeyError:
                pattlen = 64
            for inst in printseq:
                for key, events in pattern.items():
                    if key != inst: continue
                    print('           ', end='', file=_out)
                    for i in range(pattlen):
                        printable = inst if i in events else '.'
                        print(printable, end='', file=_out)
                    print('', file=_out)

    def print_instrument_flat(self, sample, _out):
        """print the events for an instrument as a piano roll

        sample is the number of the sample to print data for
        stream is a file-like object to write the output to
        """
        all_events = []
        for pattnum, pattern in self.patterns.items():
            events = []
            notes = set()
            last_event = False
            for track in pattern:
                event_str = '...'
                for event in track:
                    samp, note, effect, _ = get_notedata(event)
                    if samp == sample:
                        event_str = note
                        notes.add(note)
                        break
                    if effect == 13:
                        last_event = True
                events.append(event_str)
                if last_event:
                    break
            if not notes:
                continue
            print('pattern {:>2}:'.format(pattnum), ' '.join(events), file=_out)

    def print_instrument(self, sample, _out):
        """print the events for an instrument as a piano roll

        sample is the number of the sample to print data for
        stream is a file-like object to write the output to
        """
        all_events = collections.defaultdict(lambda: collections.defaultdict(list))
        maxlen = {}
        notes = collections.defaultdict(set)
        for pattnum, pattern in self.patterns.items():
            events = []
            last_event = False
            for ix, track in enumerate(pattern):
                note_found = False
                for event in track:
                    samp, note, effect, _ = get_notedata(event)
                    if samp == sample and note:
                        all_events[pattnum][note].append(ix)
                        notes[pattnum].add(note)
                    if effect == 13:
                        last_event = True
                if last_event:
                    maxlen[pattnum] = ix
                    break
            if not notes:
                continue
        for pattnum, pattern in all_events.items():
            print('pattern', pattnum, file=_out)
            try:
                pattlen = maxlen[pattnum]
            except KeyError:
                pattlen = 64
            for notestr in reversed(sorted(notes[pattnum], key=getnotenum)):
                print('           ', end='', file=_out)
                ## print(notestr, end=': ', file=_out)
                for note, events in pattern.items():
                    ## print(note, events, end=' ', file=_out)
                    if note == notestr:
                        for tick in range(pattlen):
                            printable = notestr if tick in events else '...'
                            print(printable, end= ' ', file=_out)
                        break
                print('', file=_out)
            print('', file=_out)

def main2():
    test = ModFile('/home/albert/magiokis/data/mod/berendina drums variatie 1.mod')
    for x in test.samples: print(x + 1, test.samples[x])
    print(test.playseq)

    test.print_playseq_ordered(11)

    ## with open('berendina_rubberbass', 'w') as _out:
        ## test.print_instrument(2, _out)

    ## with open('berendina_guitar2', 'w') as _out:
        ## test.print_instrument(1, _out)

    ## with open('berendina_guitar2o', 'w') as _out:
        ## test.print_instrument(3, _out)

    ## with open('berendina_drums', 'w') as _out:
        ## test.print_drums((
            ## (4, 'b'), (5, 'h'), (6, 'bh'), (7, 's'), (8, 'sh'),
            ## (9, 'bsh'), (10, 't'), (11, 'th'), (12, 'bth'),
            ## (13, 'g'), (14, 'bg'), (15, 'gh'), (16, 'bgh')), 'tghsb', _out)


def main():
    test = ModFile('/home/albert/magiokis/data/mod/aha.mod')
    ## print(test.name)
    for x in test.samples: print(x + 1, test.samples[x])
    ## print(test.restart)
    ## print(test.highpatt)
    print(test.playseq)
    ## print(test.modtype)

    ## with open('pattern-output V 1', 'w') as _out:
        ## for y in test.patterns[0]:
            ## print(y, file=_out)

    ## with open('pattern.output V 2', 'w') as _out:
        ## for track in test.patterns[0]:
            ## printable = ''
            ## last_event = False
            ## for event in track:
                ## samp, note, effect, data = get_notedata(event)
                ## if samp == 0 and note == 0:
                    ## printable += '... ..  '
                ## else:
                    ## printable += '{} {:> 2}  '.format(note, int(samp))
                ## if effect == 13:
                    ## last_event = True
            ## print(printable, file=_out)
            ## if last_event:
                ## break

    ## with open('instrument_output_1', 'w') as _out:
        ## test.print_instrument_flat(5, _out)

    with open('aha_flickbass', 'w') as _out:
        test.print_instrument(5, _out)

    with open('aha_ledguitar', 'w') as _out:
        test.print_instrument(6, _out)

    ## with open('drums_output', 'w') as _out:
        ## test.print_drums(((1, 'b'), (2, 's'), (3, 'h'), (4, 'c'), (7, 'o')), _out)

if __name__ == '__main__':
    ## main()
    main2()
