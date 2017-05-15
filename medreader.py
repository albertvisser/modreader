import sys
import struct
import collections
import shared

def get_note_name(inp):
    """translate note number to note name

    adapted octave to be comparable to other types
    """
    if inp == 0:
        return shared.empty_note
    return shared.get_note_name(inp + 3 * shared.octave_length)

def mmd0_decode(data):
    """
    MMD0:    xynnnnnn iiiicccc dddddddd
    n = note number (0 - $3F). 0 = ---, 1 = C-1, 2 = C#1...
    i = the low 4 bits of the instrument number
    x = the 5th bit (#4) of the instrument number
    y = the 6th bit (#5) of the instrument number
    c = command number (0 - $F)
    d = databyte ($00 - $FF)
    """
    note_number = data[0] & 0x3F
    instr_hi = (data[0] & 0xC0) >> 2
    instr_lo = data[1] >> 4
    instr_number = instr_hi + instr_lo
    command = data[1] & 0x0F
    return note_number, instr_number, command, data[2]


def mmd1_decode(data):
    """
    MMD1:    xnnnnnnn xxiiiiii cccccccc dddddddd
    n = note number (0 - $7F, 0 = ---, 1 = C-1...)
    i = instrument number (0 - $3F)
    c = command ($00 - $FF)
    d = databyte ($00 - $FF)
    x = undefined, reserved for future expansion.
    """
    note_number = data[0] & 0x7F
    instr_number = data[1] & 0x3F
    return note_number, instr_number, data[2], data[3]

def read_pointer(stream):
    return struct.unpack('>L', stream.read(4))[0]

def read_string(stream, length):
    text = struct.unpack('{}s'.format(length), stream.read(length))
    try:
        result = str(text[0], encoding='utf-8')
    except UnicodeDecodeError:
        result = str(text[0], encoding='latin-1')
    return result.rstrip('\x00')


class MedModule:

    def __init__(self, filename):
        self.filename = filename
        self.pattern_data = {}
        self.pattern_lengths = []
        self.read()
        if not self._pattern_data:
            raise ValueError('Empty module !?')
        self._all_events = collections.defaultdict(lambda: collections.defaultdict(
            lambda: collections.defaultdict(list)))
        sampledata_found = collections.defaultdict(lambda: False)
        for pattnum, pattern in enumerate(self._pattern_data):
            length, pattern = pattern
            self.pattern_lengths.append(length)
            events = []
            last_event = False
            for ix, track in enumerate(pattern):
                for note, samp in track:
                    if note:
                        sampledata_found[samp] = True
                        self._all_events[pattnum][samp]['len'] = length
                        self._all_events[pattnum][samp][note].append(ix)
        samples_to_keep = []
        for ix, samp in enumerate(self.samplenames):
            if sampledata_found[ix + 1]:
                samples_to_keep.append((ix, samp))
        self.samplenames = samples_to_keep


    def read(self):

        # instead of repositioning while reading, read the entire file first and then
        # reposition in memory?

        with open(self.filename, 'rb') as _med:

            mod_header = struct.unpack('>4s9L4HhBB', _med.read(52))
            self.modtype = str(mod_header[0], encoding='utf-8')
            if self.modtype not in ('MMD0', 'MMD1'):
                raise ValueError('Not a valid MED module')
            modlen = mod_header[1]
            songinfo_start = mod_header[2]
            blockarray_start = mod_header[4]
            instheader_start = mod_header[6]
            expansion_start = mod_header[8]

            _med.seek(songinfo_start)
            songinfo = struct.unpack('>504BHH256BHBbbb16bbb', _med.read(788))
            blockcount = songinfo[504]
            self.songlen = songinfo[505]
            self.raw_playseq = songinfo[506:506+256]
            self.sample_count = songinfo[784]

            _med.seek(blockarray_start)
            blockstart_list = []
            for i in range(blockcount):
                blockstart_list.append(read_pointer(_med))

            _med.seek(instheader_start)
            samplestart_list = []
            for i in range(self.sample_count):
                samplestart_list.append(read_pointer(_med))

            _med.seek(expansion_start)
            data = struct.unpack('>LLHHLLLHH7L7B', _med.read(63))
            instrext_start, instrext_count, instrext_len = data[1:4]
            songoms_start, songoms_len = data[4:6]
            instrinfo_start, instrinfo_count, instrinfo_len = data[6:9]

            _med.seek(songoms_start)
            self.songdesc = read_string(_med, songoms_len)

            compare = instrinfo_count == self.sample_count
            _med.seek(instrinfo_start)
            self.samplenames = []
            for i in range(instrinfo_count):
                instname = read_string(_med, instrinfo_len)
                if compare and samplestart_list[i] == 0:
                    instname += ' (unnamed)'
                self.samplenames.append(instname)

            pattern_lengths_and_data = []
            self._pattern_data = []
            self.pattern_desc = {}
            for address in blockstart_list:
                _med.seek(address)
                this_pattern = []
                if self.modtype == 'MMD0':
                    tracks, lines = struct.unpack('BB', _med.read(2))
                    this_pattern.append(lines)
                    for x in range(lines + 1):
                        linedata = []
                        for y in range(tracks):
                            notedata = struct.unpack('3B', _med.read(3))
                            linedata.append(mmd0_decode(notedata)[:2])
                        this_pattern.append(linedata)

                elif self.modtype == 'MMD1':
                    tracks, lines, address = struct.unpack('>HHL', _med.read(8))
                    for x in range(lines + 1):
                        linedata = []
                        for y in range(tracks):
                            notedata = struct.unpack('4B', _med.read(4))
                            linedata.append(mmd1_decode(notedata)[:2])
                        this_pattern.append(linedata)

                    if address:
                        _med.seek(address)
                        data = struct.unpack('>3L', _med.read(12))
                        address, length = data[1:]
                        _med.seek(address)
                        pattern_text = read_string(_med, length)
                        self.pattern_desc[i] = pattern_text

                pattern_lengths_and_data.append((lines + 1, this_pattern))

            ## with open('/tmp/01-pattern-lengths-and-data-med', 'w') as _o:
                ## for pattnum, data in enumerate(pattern_lengths_and_data):
                    ## pattlen, pattdata = data
                    ## print('pattern', pattnum, 'lengte:', pattlen, file=_o)
                    ## for event in pattdata: print('   ', event, file=_o)

            # now to split up the patterns to be no longer that 32
            new_patterns = []
            ophogen = 0
            all_patt_lengths = collections.defaultdict(list)
            newpattnums = collections.defaultdict(list)
            pattnum = 0
            for ix, pattdata in enumerate(pattern_lengths_and_data):
                pattlen, patt = pattdata
                while pattlen > shared.per_line:
                    old_pattlen = shared.per_line
                    old_patt = patt[:old_pattlen]
                    new_patterns.append((old_pattlen, old_patt))
                    pattlen -= old_pattlen
                    patt = patt[old_pattlen:]
                    all_patt_lengths[ix].append(old_pattlen)
                    newpattnums[ix].append(pattnum)
                    pattnum += 1
                new_patterns.append((pattlen, patt))
                all_patt_lengths[ix].append(pattlen)
                newpattnums[ix].append(pattnum)
                pattnum += 1

        self._pattern_data = new_patterns
        self.pattern_count = blockcount
        self.playseq, self.all_pattern_lengths = [], []
        for patt in self.raw_playseq[:self.songlen]:
            self.playseq.extend(newpattnums[patt])
            self.all_pattern_lengths.extend(all_patt_lengths[patt])
        self.all_pattern_lengths = self.all_pattern_lengths[:self.songlen]


    def checks(self):
        return (
            'songlen = {}, len of raw pattern list = {}'.format(self.songlen,
                len(self.raw_playseq)),
            'number of samples = {}, len of sample list = {}'.format(
                self.sample_count, len(self.samplenames)),
            'number of patterns = {}, len of pattern data list = {}'.format(
                self.pattern_count, len(self.pattern_data))
            )

    def remove_duplicate_patterns(self, sampnum):
        renumber = {} # collections.defaultdict(dict)
        pattern_list = []
        newsampnum = self.samplenames[sampnum][0] + 1
        for pattnum, data in self._all_events.items():
            for sampno, patt in data.items():
                if sampno != newsampnum:
                    continue
                try:
                    new_pattnum = pattern_list.index(patt) + 1
                except ValueError:
                    pattern_list.append(patt)
                    new_pattnum = len(pattern_list)
                renumber[pattnum] = new_pattnum
        self.pattern_data[sampnum + 1] = pattern_list
        for ix, seq in enumerate(self.playseq):
            if ix >= self.songlen:
                break
            if seq in renumber:
                self.playseqs[sampnum + 1].append(renumber[seq])
            else:
                self.playseqs[sampnum + 1].append(-1)

    def remove_duplicate_drum_patterns(self, samplist):

        inst2samp = {x: y[0] + 1 for x, y in enumerate(self.samplenames)}
        samp2inst = {y[0] + 1: x for x,y in enumerate(self.samplenames)}
        single_instrument_samples = [inst2samp[x - 1] for x, y in samplist
            if len(y) == 1]
        lookup = {y: inst2samp[x - 1] for x, y in samplist if len(y) == 1}
        samp2lett = {inst2samp[x - 1]: y for x, y in samplist}
        drumpatterns = collections.defaultdict(lambda: collections.defaultdict(list))
        self.pattlengths = collections.defaultdict(dict)

        for pattnum, data in self._all_events.items():
            for sampnum, patt in data.items():
                if sampnum not in single_instrument_samples:
                    continue
                samplett = samp2lett[sampnum]
                drumpatterns[pattnum]['len'].append((samplett, patt['len']))
                # theoretisch kan dit data voor meer toonhoogten bevatten
                # maar voor mijn spullen kan ik uitgaan van één
                drumpatterns[pattnum][samplett] = [y for x, y in patt.items()
                    if x != 'len'][0]

        for pattnum, data in self._all_events.items():
            for sampnum, patt in data.items():
                if sampnum in single_instrument_samples:
                    continue
                try:
                    instletters = samp2lett[sampnum]
                except KeyError:
                    continue

                for letter in instletters:
                    drumpatterns[pattnum]['len'].append((letter, patt['len']))
                    # theoretisch kan dit data voor meer toonhoogten bevatten
                    # maar voor mijn spullen kan ik uitgaan van één
                    drumpatterns[pattnum][letter].extend([y for x, y in patt.items()
                        if x != 'len'][0])
                    drumpatterns[pattnum][letter].sort()

        renumber = {}
        pattern_list = []
        for pattnum, patt in drumpatterns.items():
            lengths = [x[1] for x in patt['len']]
            if max(lengths) != lengths[0] or min(lengths) != lengths[0]:
                print('ongelijke lengtes in pattern {}: {}'.format(pattnum, lengths))
            patt['len'] = lengths[0]

            try:
                new_pattnum = pattern_list.index(patt) + 1
            except ValueError:
                pattern_list.append(patt)
                new_pattnum = len(pattern_list)
            renumber[pattnum] = new_pattnum
        self.pattern_data['drums'] = pattern_list
        for ix, seq in enumerate(self.playseq):
            if ix >= self.songlen:
                break
            if seq in renumber:
                self.playseqs['drums'].append(renumber[seq])
            else:
                self.playseqs['drums'].append(-1)


    def print_general_data(self, sample_list=None, full=False, _out=sys.stdout):
        if sample_list is None:
            drumsamples = sample_list = []
        else:
            drumsamples = [x for x, y in sample_list]
        data = shared.build_header("module", self.filename, self.songdesc)

        instruments = []
        self.playseqs = collections.defaultdict(list)
        for sampseq, sample in enumerate(self.samplenames):
            sample_name = sample[1]
            sample_string = ''
            sample_number = sampseq + 1 # start met 1 ipv 0
            if sample_list:
                for sampnum, sampstr in sample_list:
                    if sampnum == sample_number:
                        sample_string = sampstr.join((' (', ')'))
            instruments.append((sample_number, sample_name + sample_string))
            if sample_number not in drumsamples:
                self.remove_duplicate_patterns(sampseq)
        if drumsamples:
            self.remove_duplicate_drum_patterns(sample_list)
        data.extend(shared.build_inst_list(instruments))

        if not full:
            data.extend(shared.build_patt_header())
            for sample_number, sample_name in instruments:
                if sample_number not in drumsamples:
                    data.extend(shared.build_patt_list(sample_number, sample_name,
                        self.playseqs[sample_number]))
            if 'drums' in self.playseqs:
                data.extend(shared.build_patt_list('', 'Drums',
                    self.playseqs['drums']))

        for text in data:
            print(text.rstrip(), file=_out)


    def print_drums(self, sample_list, printseq, _out=sys.stdout):
        """collect the drum sample events and print them together

        sample_list is a list of pattern numbers associated with the instruments
        to print on this event, e.g. ((1, 'b'), (2, 's'), (4, 'bs'), (7, 'bsh'))
        printseq indicates the sequence to print these top to bottom e.g. 'hsb'
        stream is a file-like object to write the output to
        """
        for pattnum, pattern in enumerate(self.pattern_data['drums']):
            print(shared.patt_start.format(pattnum + 1), file=_out)
            ## pattlen = pattern.pop('len')
            pattlen = pattern['len']
            for inst in printseq:
                for key, events in pattern.items():
                    if key != inst: continue
                    print(shared.line_start, end='', file=_out)
                    for i in range(pattlen):
                        printable = inst if i in events else shared.empty_drums
                        print(printable, end='', file=_out)
                    print('', file=_out)
            print('', file=_out)

    def print_instrument(self, sample, _out=sys.stdout):
        """print the events for an instrument as a piano roll

        sample is the number of the sample to print data for
        stream is a file-like object to write the output to
        """
        for pattnum, pattern in enumerate(self.pattern_data[sample]):
            print(shared.patt_start.format(pattnum + 1), file=_out)
            pattlen = pattern['len']
            for note in reversed(sorted([x for x in pattern if x != 'len'])):
                print(shared.line_start, end='', file=_out)
                events = pattern[note]

                printable = []
                for tick in range(pattlen):
                    if tick in events:
                        corr = note + 3 * shared.octave_length - 1 # comparability
                        next = shared.get_note_name(corr)
                    else:
                        next = shared.empty_note
                    printable.append(next)
                print(' '.join(printable), file=_out)
            print('', file=_out)

    def prepare_print_drums(self, printseq):
        self.all_drum_tracks = collections.defaultdict(list)
        for pattseq, pattnum in enumerate(self.playseqs['drums']):
            if pattnum == -1:
                pattlen = self.all_pattern_lengths[pattseq]
                for inst in printseq:
                    self.all_drum_tracks[inst].extend([shared.empty_drums] * pattlen)
                continue
            pattern = self.pattern_data['drums'][pattnum - 1]

            for inst in printseq:
                events = [x for x in pattern[inst]]
                for i in range(pattern['len']):
                    to_append = inst if i in events else shared.empty_drums
                    self.all_drum_tracks[inst].append(to_append)

    def print_drums_full(self, sample_list, printseq, opts, _out=sys.stdout):
        interval, clear_empty = opts
        interval *= 2
        empty = interval * shared.empty_drums
        total_length = sum(self.all_pattern_lengths)
        for eventindex in range(0, total_length, interval):
            not_printed = True
            for inst in printseq:
                line = ''.join(
                    self.all_drum_tracks[inst][eventindex:eventindex+interval])
                if clear_empty and line == empty:
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                print(empty, file=_out)
            print('', file=_out)

    def prepare_print_instruments(self, instlist):
        self.all_note_tracks = collections.defaultdict(
            lambda: collections.defaultdict(list))
        self.all_notes = collections.defaultdict(set)

        for sampnum, sample in instlist:

            for pattnum, pattern in enumerate(self.pattern_data[sampnum]):
                self.all_notes[sample].update(pattern.keys())
            self.all_notes[sample].discard('len')
            self.all_notes[sample] = [
                x for x in reversed(sorted(self.all_notes[sample]))]

            for pattseq, pattnum in enumerate(self.playseqs[sampnum]):
                if pattnum == -1:
                    pattlen = self.all_pattern_lengths[pattseq]
                    for note in self.all_notes[sample]:
                        self.all_note_tracks[sample][note].extend(
                            [shared.empty_note] * pattlen)
                    continue
                pattern = self.pattern_data[sampnum][pattnum - 1]
                for note in self.all_notes[sample]:
                    events = pattern[note]
                    for i in range(pattern['len']):
                        if i in events:
                            to_append = shared.get_note_name(
                                note + 3 * shared.octave_length - 1)
                        else:
                            to_append = shared.empty_note
                        self.all_note_tracks[sample][note].append(to_append)

    def print_instrument_full(self, sample, opts, _out=sys.stdout):
        """print the events for an instrument as a piano roll

        sample is the number of the sample to print data for
        stream is a file-like object to write the output to
        """
        interval, clear_empty = opts
        sep = ' '
        empty = sep.join(interval * [shared.empty_note])
        total_length = sum(self.all_pattern_lengths)
        for eventindex in range(0, total_length, interval):
            not_printed = True
            for note in self.all_notes[sample]:
                events = self.all_note_tracks[sample][note]
                line = sep.join(events[eventindex:eventindex+interval])
                if clear_empty and line == empty:
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                print(empty, file=_out)
            print('', file=_out)


    def print_all_instruments_full(self, instlist, printseq, opts, _out=sys.stdout):
        interval, clear_empty, instlist = opts
        total_length = sum(self.all_pattern_lengths)

        for eventindex in range(0, total_length, interval):

            sep = ' '
            empty = sep.join(interval * [shared.empty_note])
            for sampnum, sample in instlist:
                print('{}:'.format(sample), file=_out)
                not_printed = True
                for note in self.all_notes[sample]:
                    line = sep.join(
                        self.all_note_tracks[sample][note][eventindex:eventindex+interval])
                    if clear_empty and line == empty:
                        pass
                    else:
                        print('  ', line, file=_out)
                        not_printed = False
                if not_printed:
                    print('  ', empty, file=_out)
                print('', file=_out)

            sep = ''
            empty = sep.join(interval * [shared.empty_drums])
            print('drums:', file=_out)
            not_printed = True
            for inst in printseq:
                line = sep.join(
                    self.all_drum_tracks[inst][eventindex:eventindex+interval])
                if clear_empty and line == empty:
                    pass
                else:
                    print('  ', line, file=_out)
                    not_printed = False
            if not_printed:
                print('  ', empty, file=_out)
            print('', file=_out)

            print('', file=_out)



