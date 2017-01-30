"""
Het idee achter deze module is om na het lezen van de bestanden
de patterns uit te schrijven
"""
import collections
import pprint
import shared

# de noten kloppen, maar de octaven worden in MilkyTracker 2 hoger weergegeven
# om gelijk te trekken met andere weergaven daarom maar aangepast
noteval = dict(zip([
    int(x) for x in """\
1712 1616 1524 1440 1356 1280 1208 1140 1076 1016  960  906
 856  808  762  720  678  640  604  570  538  508  480  453
 428  404  381  360  339  320  302  285  269  254  240  226
 214  202  190  180  170  160  151  143  135  127  120  113
 107  101   95   90   85   80   75   71   67   63   60   56
""".split()], [
    ## x.replace('-', ' ') for x in """\
 ## C-0  C#0  D-0  D#0  E-0  F-0  F#0  G-0  G#0  A-0  A#0  B-0
 ## C-1  C#1  D-1  D#1  E-1  F-1  F#1  G-1  G#1  A-1  A#1  B-1
 ## C-2  C#2  D-2  D#2  E-2  F-2  F#2  G-2  G#2  A-2  A#2  B-2
 ## C-3  C#3  D-3  D#3  E-3  F-3  F#3  G-3  G#3  A-3  A#3  B-3
 ## C-4  C#4  D-4  D#4  E-4  F-4  F#4  G-4  G#4  A-4  A#4  B-4
## """.split()]))
    x.replace('-', ' ') for x in """\
 C-2  C#2  D-2  D#2  E-2  F-2  F#2  G-2  G#2  A-2  A#2  B-2
 C-3  C#3  D-3  D#3  E-3  F-3  F#3  G-3  G#3  A-3  A#3  B-3
 C-4  C#4  D-4  D#4  E-4  F-4  F#4  G-4  G#4  A-4  A#4  B-4
 C-5  C#5  D-5  D#5  E-5  F-5  F#5  G-5  G#5  A-5  A#5  B-5
 C-6  C#6  D-6  D#6  E-6  F-6  F#6  G-6  G#6  A-6  A#6  B-6
""".split()]))
maxpattlen = 64

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
                for y in range(maxpattlen):
                    track = []
                    for z in range(channelcount):
                        track.append([x for x in _in.read(4)])
                    pattern.append(track)
                self.patterns[x] = pattern

        data = collections.defaultdict(lambda: collections.defaultdict(list))
        lentab = []
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
                leng = maxpattlen
                for samp in sample_list:
                    data[samp - 1][pattnum].insert(0, leng)
            lentab.append((pattnum, leng))

        self._pattern_data = collections.defaultdict(lambda: collections.defaultdict(list))
        ophogen = 0
        samples = [x for x in data.keys()]
        for pattnum, pattlen in lentab:
            split = pattlen > 32
            if split:
                newlen = pattlen - 32
            for s in samples:
                origpatt = data[s][pattnum][1:]
                if split:
                    splitix = 0
                    for ix, event in enumerate(origpatt):
                        if event[0] >= 32:
                            splitix = ix
                            break
                    if not splitix:
                        print('splitix is 0')
                        if origpatt:
                            print('we have origpatt')
                            if origpatt[0][0] >= 32: # wrschl is deze test niet nodig
                                print('start with timing > 32')
                                origpatt = [(x - 32, y) for x, y in origpatt]
                            origpatt.insert(0, 32)
                            self._pattern_data[s][pattnum + ophogen] = origpatt
                    else:
                        oldpatt, newpatt = origpatt[:splitix], origpatt[splitix:]
                        if oldpatt:
                            oldpatt.insert(0, 32)
                            self._pattern_data[s][pattnum + ophogen] = oldpatt
                        if newpatt:
                            newpatt = [(x - 32, y) for x, y in origpatt[splitix:]]
                            newpatt.insert(0, newlen)
                            self._pattern_data[s][pattnum + ophogen + 1] = newpatt
                else:
                    if data[s][pattnum]:
                        self._pattern_data[s][pattnum + ophogen] = data[s][pattnum]
            if split:
                ophogen += 1

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
        drumsamples = [x for x, y in sample_list]
        data = shared.build_header("module", self.filename, self.name.rstrip(chr(0)))

        instruments = []
        for sampseq, sample_data in self.samples.items():
            sample_name = sample_data[0]
            sample_string = ''
            sample_number = sampseq + 1
            if sample_list:
                for sampnum, sampstr in sample_list:
                    if sampnum == sample_number:
                        sample_string = sampstr.join((' (', ')'))
            instruments.append((sample_number, sample_name + sample_string))
            if sample_number not in drumsamples:
                self.remove_duplicate_patterns(sampseq)

        self.remove_duplicate_drum_patterns(sample_list)
        data.extend(shared.build_inst_list(instruments))
        data.extend(shared.build_patt_header())

        for sample_number, sample_name in instruments:
            if sample_number not in drumsamples:
                data.extend(shared.build_patt_list(sample_number, sample_name,
                    self.playseqs[sample_number - 1]))
        if 'drums' in self.playseq:
            data.extend(shared.build_patt_list('', 'Drums', self.playseqs['drums']))

        for text in data:
            print(text.rstrip(), file=_out)

    def print_drums(self, sample_list, printseq, _out):
        """collect the drum sample events and print them together

        sample_list is a list of pattern numbers associated with the instruments
        to print on this event, e.g. ((1, 'b'), (2, 's'), (4, 'bs'), (7, 'bsh'))
        printseq indicates the sequence to print these top to bottom e.g. 'hsb'
        stream is a file-like object to write the output to
        """
        for pattnum, pattern in enumerate(self.pattern_data['drums']):
            pattlen = pattern['len']
            print(shared.patt_start.format(pattnum + 1), file=_out)
            for inst in printseq:
                for key, events in pattern.items():
                    if key != inst: continue
                    events = [x[0] for x in events]
                    print(shared.line_start, end='', file=_out)
                    for i in range(pattlen):
                        printable = inst if i in events else shared.empty_drums
                        print(printable, end='', file=_out)
                    print('', file=_out)
            print('', file=_out)

    def print_instrument(self, sample, _out):
        """print the events for an instrument as a piano roll

        sample is the number of the sample to print data for
        stream is a file-like object to write the output to
        """
        for pattnum, pattern in enumerate(self.pattern_data[sample - 1]):
            pattlen = pattern.pop(0)
            print(shared.patt_start.format(pattnum + 1), file=_out) #  display starting with 1
            notes = collections.defaultdict(list)
            for timing, note in pattern:
                notes[note].append(timing)
            for notestr in reversed(sorted([x for x in notes],
                    key=shared.getnotenum)):
                print(shared.line_start, end='', file=_out)
                events = notes[notestr]

                printable = []
                for tick in range(pattlen):
                    next = notestr if tick in events else shared.empty_note
                    printable.append(next)
                print(' '.join(printable), file=_out)
            print('', file=_out)

