"""
Het idee achter deze module is om na het lezen van de bestanden
de patterns uit te schrijven
"""
import collections
import pprint
import shared

# de noten kloppen, maar de octaven worden in MilkyTracker 2 hoger weergegeven
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
    sampnum = data[0] & 0xF0
    sampnum += data[2] >> 4
    period = data[0] & 0x0F
    period *= 256
    period += data[1]
    note = noteval[period] if period else 0
    effectnum = data[2] & 0x0F
    effectparm = data[3]
    return sampnum, note, effectnum, effectparm

class ModFile:

    def __init__(self, filename):
        self.filename = filename
        self.samples = {}
        self.patterns = {}
        self.pattern_data = {}
        self.playseqs = collections.defaultdict(list)
        self.read()

    def read(self):
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

            for x in range(self.highpatt + 1):
                pattern = []
                for y in range(64):
                    track = []
                    for z in range(channelcount):
                        track.append([x for x in _in.read(4)])
                    pattern.append(track)
                self.patterns[x] = pattern

        data = collections.defaultdict(lambda: collections.defaultdict(list))
        for pattnum, pattern in self.patterns.items():
            sample_list = set()
            last_event = False
            for ix, track in enumerate(pattern):
                for event in track:
                    samp, note, effect, _ = get_notedata(event)
                    if note:
                        data[samp - 1][pattnum].append((ix, note))
                        sample_list.add(samp)
                    if effect == 13:
                        leng = ix + 1
                        for samp in sample_list:
                            data[samp -1][pattnum].insert(0, leng)
                        last_event = True
                        break
                if last_event:
                    break
            if not last_event:
                leng = 64
                for samp in sample_list:
                    data[samp - 1][pattnum].insert(0, leng)
        self._pattern_data = data

    def remove_duplicate_patterns(self, sampnum):
        renumber = collections.defaultdict(dict)
        pattern_list = []
        for pattnum, patt in self._pattern_data[sampnum].items():
            try:
                new_pattnum = pattern_list.index(patt) + 1
            except ValueError:
                pattern_list.append(patt)
                new_pattnum = len(pattern_list)
            renumber[pattnum] = new_pattnum
        self.pattern_data[sampnum] = pattern_list
        for seq in self.playseq:
            if seq in renumber:
                self.playseqs[sampnum].append(renumber[seq])
            else:
                self.playseqs[sampnum].append(-1)

    def remove_duplicate_drum_patterns(self, samplist):
        single_instrument_samples = [x - 1 for x, y in samplist if len(y) == 1]
        lookup = {y: x - 1 for x, y in samplist if len(y) == 1}
        samp2lett = {x - 1: y for x, y in samplist}
        drumpatterns = collections.defaultdict(lambda: collections.defaultdict(list))
        pattlengths = {}
        for sampnum, sampdata in self._pattern_data.items():
            if sampnum not in single_instrument_samples:
                continue
            samplett = samp2lett[sampnum]
            for pattnum, patt in sampdata.items():
                drumpatterns[pattnum][samplett] = patt[1:]
                pattlengths[pattnum] = patt[0]
        for sampnum, sampdata in self._pattern_data.items():
            if sampnum in single_instrument_samples:
                continue
            try:
                instletters = samp2lett[sampnum]
            except KeyError:
                continue
            for pattnum, patt in sampdata.items():
                try:
                    if patt[0] > pattlengths[pattnum]:
                        pattlengths[pattnum] = patt[0]
                except KeyError:
                    pattlengths[pattnum] = patt[0]
                for letter in instletters:
                    drumpatterns[pattnum][letter].extend(patt[1:])
                    drumpatterns[pattnum][letter].sort()
        for pattnum in drumpatterns:
            drumpatterns[pattnum]['len'] = pattlengths[pattnum]
        renumber = collections.defaultdict(dict)
        pattern_list = []
        for pattnum, patt in drumpatterns.items():
            try:
                new_pattnum = pattern_list.index(patt) + 1
            except ValueError:
                pattern_list.append(patt)
                new_pattnum = len(pattern_list)
            renumber[pattnum] = new_pattnum
        self.pattern_data['drums'] = pattern_list
        for seq in self.playseq:
            if seq in renumber:
                self.playseqs['drums'].append(renumber[seq])
            else:
                self.playseqs['drums'].append(-1)

    def print_general_data(self, _out, sample_list=None):
        if sample_list is None: sample_list = []
        drumsamples = [x - 1 for x, y in sample_list]
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
            if sample_number not in drumsamples:
                self.remove_duplicate_patterns(sample_number)

        self.remove_duplicate_drum_patterns(sample_list)

        data.extend(['', 'patterns:', ''])
        printable = print_start = '          '
        count = 8
        for sample, playseq in self.playseqs.items():
            if sample == 'drums':
                text = '    drums'
            else:
                text = '    {}:'.format(self.samples[sample][0])
            data.extend([text, ''])
            for ix, x in enumerate(playseq):
                if x == -1:
                    printable += ' . '
                else:
                    printable += '{:>2} '.format(x) # start pattern display met 1
                if (ix + 1) % count == 0:
                    data.append(printable)
                    printable = print_start
            data.extend([printable, ''])
            printable = print_start
        for text in data:
            print(text, file=_out)

    def print_drums(self, sample_list, printseq, _out):
        """collect the drum sample events and print them together

        sample_list is a list of pattern numbers associated with the instruments
        to print on this event, e.g. ((1, 'b'), (2, 's'), (4, 'bs'), (7, 'bsh'))
        printseq indicates the sequence to print these top to bottom e.g. 'hsb'
        stream is a file-like object to write the output to
        """
        for pattnum, pattern in enumerate(self.pattern_data['drums']):
            pattlen = pattern['len']
            print('pattern', pattnum + 1, file=_out)
            for inst in printseq:
                for key, events in pattern.items():
                    if key != inst: continue
                    events = [x[0] for x in events]
                    print('           ', end='', file=_out)
                    for i in range(pattlen):
                        printable = inst if i in events else '.'
                        print(printable, end='', file=_out)
                    print('', file=_out)

    def print_instrument(self, sample, _out):
        """print the events for an instrument as a piano roll

        sample is the number of the sample to print data for
        stream is a file-like object to write the output to
        """
        for pattnum, pattern in enumerate(self.pattern_data[sample - 1]):
            pattlen = pattern.pop(0)
            print('pattern', pattnum + 1, file=_out) #  display starting with 1
            notes = collections.defaultdict(list)
            for timing, note in pattern:
                notes[note].append(timing)
            for notestr in reversed(sorted([x for x in notes],
                    key=shared.getnotenum)):
                print('           ', end='', file=_out)
                events = notes[notestr]

                for tick in range(pattlen):
                    printable = notestr if tick in events else '...'
                    print(printable, end= ' ', file=_out)
                print('', file=_out)
            print('', file=_out)

def main2():
    test = ModFile('/home/albert/magiokis/data/mod/berendina drums variatie 1.mod')
    ## for x in test.samples: print(x + 1, test.samples[x])
    ## with open('/tmp/mod-output-patterns', 'w') as _o:
        ## pprint.pprint(test.patterns, stream=_o)
    with open('/tmp/mod-output-pattern_data', 'w') as _o:
        pprint.pprint(test.pattern_data, stream=_o)
        ## pprint.pprint(test.renumber, stream=_o)
        ## pprint.pprint(test.new_pattern_data, stream=_o)
        ## print(test.samples, file=_o)
        ## print(test.playseq, file=_o)
    with open('/tmp/mod-output-general_data', 'w') as _o:
        samplist = (
            (4, 'b'), (5, 'h'), (6, 'bh'), (7, 's'), (8, 'sh'),
            (9, 'bsh'), (10, 'd'), (11, 'dh'), (12, 'bdh'),
            (13, 'g'), (14, 'bg'), (15, 'gh'), (16, 'bgh')
        )
        test.print_general_data(_o, samplist)
        test.print_drums(samplist, 'hdgsb', _o)
        test.print_instrument(1, _o)
        ## pprint.pprint(test.new_pattern_data, stream=_o)
        ## print(test.playseq, file=_o)
    return
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
