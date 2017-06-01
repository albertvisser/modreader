import sys
import struct
import collections
import shared
import logging


def log(inp):
    logging.info(inp)


def get_note_name(inp):
    """translate note number to note name

    adapted octave to be comparable to other types
    """
    if inp == 0:
        return shared.empty_note
    return shared.get_note_name(inp)


def read_string(stream, length):
    text = struct.unpack('{}s'.format(length), stream.read(length))
    try:
        result = str(text[0], encoding='utf-8')
    except UnicodeDecodeError:
        result = str(text[0], encoding='latin-1')
    return result.rstrip('\x20\x00')


class ExtModule:

    def __init__(self, filename):
        self.filename = filename
        self.pattern_data = {}
        self._pattern_map = {}
        self.pattern_lengths = []
        self.instruments = {}
        self.read()

        # pattern list en map bijwerken met uitgesplitste
        original_pattern_map = self._raw_pattern_map
        initial_pattern_list = self._raw_pattern_list
        renumber = collections.defaultdict(list)
        oldpattnum, newpattnum = -1, 0
        for pattstart in sorted(self._raw_pattern_data):
            try:
                oldpattnum = original_pattern_map[pattstart]
            except KeyError:
                pass
            newpattnum += 1
            renumber[oldpattnum].append(newpattnum)
            self._pattern_map[pattstart] = newpattnum
        self._pattern_list = []
        for patt in initial_pattern_list:
            self._pattern_list.extend(renumber[patt])

        # pattern data decoderen
        self._pattern_data = collections.defaultdict(lambda: collections.defaultdict(
            lambda: collections.defaultdict(list)))
        sampledata_found = collections.defaultdict(lambda: False)
        self.initial_patterns = {}
        for pattstart, pattdata in self._raw_pattern_data.items():
            pattnum = self._pattern_map[pattstart]
            pattlen = len(pattdata)
            if pattlen == 0:
                self._pattern_data[pattnum][0][0] = []
                self._pattern_data[pattnum][0]['len'] = pattlen
                continue
            for lineno, line in enumerate(pattdata):
                for event in line:
                    ## if event[:2] == (0, 0): continue
                    ## # log('event {} not skipped'.format(event))
                    ## note = get_note_name(event[0])
                    ## inst = event[1]
                    note, inst = event[:2]
                    if note or inst:
                        sampledata_found[inst] = True
                        self._pattern_data[pattnum][inst][note].append(lineno)
                        self._pattern_data[pattnum][inst]['len'] = pattlen
            if pattnum not in self._pattern_data:
                self._pattern_data[pattnum][0][0] = []
                self._pattern_data[pattnum][0]['len'] = pattlen
        for pattnum, pattdata in sorted(self._pattern_data.items()):
            for inst, instdata in pattdata.items():
                if instdata['len']:
                    pattlen = instdata['len']
                    break
            self.initial_patterns[pattnum] = pattlen
        samples_to_keep = []
        ## print(self.instruments, sampledata_found)
        for ix, sample in self.instruments.items():
            samp = sample[0]
            if sampledata_found[ix]:
                samples_to_keep.append((ix, samp))
        self.samplenames = samples_to_keep

    def read(self):

        # instead of repositioning while reading, read the entire file first and then
        # reposition in memory?
        # make sure the resulting patterns are 32 events tops

        with open(self.filename, 'rb') as _xm:

            read_string(_xm, 17)                # module id
            read_string(_xm, 20)                # module name
            struct.unpack('B', _xm.read(1))     # standard
            read_string(_xm, 20)                # tracker name
            struct.unpack('BB', _xm.read(2))    # tracker version
            xm_header = struct.unpack('<L8H', _xm.read(20))
            header_size, self.songlen, _ = xm_header[:3]    # restart_pos
            channel_count, pattern_count, instr_count = xm_header[3:6]
            ## freq_table, dflt_tempo, dflt_bpm = xm_header[6:]
            ## log('{}'.format(xm_header))
            pattern_table = struct.unpack('256B', _xm.read(256))
            self._raw_pattern_list = pattern_table[:int(self.songlen)]
            self._raw_pattern_map = {}

            self._raw_pattern_data = {}
            pattstart = header_size + 60
            for pattnum in range(pattern_count):
                _xm.seek(pattstart)        # position at start of pattern header
                size, _, rows, data_size = struct.unpack('<LBHH', _xm.read(9))
                log('pattern {} at {}; size {} rows {} datasize {}'.format(
                    pattnum, hex(pattstart), size, rows, data_size))
                orig_pattstart = pattstart
                pattstart += size
                self._raw_pattern_map[pattstart] = pattnum
                _xm.seek(pattstart)     # position at start of pattern data
                pattdata = []
                if data_size > 0:
                    for rownum in range(rows):
                        if rownum and rownum % shared.max_lines == 0:
                            self._raw_pattern_data[pattstart] = pattdata
                            pattstart = _xm.tell()
                            ## log('started new pattern at {}'.format(hex(pattstart)))
                            pattdata = []
                        rowdata = []
                        endpattern = False
                        for _ in range(channel_count):
                            start_byte = struct.unpack('B', _xm.read(1))[0]
                            compressed = start_byte & 0x80
                            note = inst = vol = eff = parm = 0
                            if not compressed:
                                note = start_byte
                            elif start_byte & 0x01:
                                note = struct.unpack('B', _xm.read(1))[0]
                            if not compressed or start_byte & 0x02:
                                inst = struct.unpack('B', _xm.read(1))[0]
                            if not compressed or start_byte & 0x04:
                                vol = struct.unpack('B', _xm.read(1))[0]
                            if not compressed or start_byte & 0x08:
                                eff = struct.unpack('B', _xm.read(1))[0]
                            if not compressed or start_byte & 0x10:
                                parm = struct.unpack('B', _xm.read(1))[0]
                            ## log('{}, {}, {}, {}, {}, {}, {}, {}'.format(pattnum,
                                ## rownum, channel, note, inst, vol, eff, parm))
                            rowdata.append((note, inst, vol, eff, parm))
                            if eff == 13:
                                endpattern = True
                        pattdata.append(rowdata)
                        if endpattern:
                            break
                self._raw_pattern_data[pattstart] = pattdata
                pattstart = orig_pattstart + size + data_size     # calculate next pattern start

            inst_start = pattstart
            for instnum in range(instr_count):
                _xm.seek(inst_start)
                inst_size = struct.unpack('<L', _xm.read(4))[0]     # bv 0x00000107
                inst_name = read_string(_xm, 22)                    # bv ElecBass
                _ = struct.unpack('B', _xm.read(1))[0]      # inst_type, bv 0xCF
                sampcount = struct.unpack('<H', _xm.read(2))[0]     # bv 0x0001
                samp_hdr_size = struct.unpack('<L', _xm.read(4))[0]  # bv. 0x00000028
                self.instruments[instnum + 1] = [inst_name, inst_start]
                samples = []
                _xm.seek(inst_start + inst_size)
                inst_start += inst_size
                for _ in range(sampcount):
                    test = _xm.read(18)
                    samp_header = struct.unpack('<LLLBBBBBB', test)
                    samp_name = read_string(_xm, 22)
                    samp_leng = samp_header[0]
                    samples.append((samp_name, samp_leng))
                    inst_start += samp_hdr_size + samp_leng
                self.instruments[instnum + 1].append(samples)

    def remove_duplicate_patterns(self, sampnum):
        renumber = {}
        pattern_list = []
        ## newsampnum = self.instruments[sampnum][0]
        for pattnum, data in self._pattern_data.items():
            for sampno, patt in data.items():
                if sampno != sampnum:
                    continue
                try:
                    new_pattnum = pattern_list.index(patt) + 1
                except ValueError:
                    pattern_list.append(patt)
                    new_pattnum = len(pattern_list)
                renumber[pattnum] = new_pattnum
        self.pattern_data[sampnum] = pattern_list

        for seq in self._pattern_list:
            if seq in renumber:
                self.playseqs[sampnum].append(renumber[seq])
            else:
                self.playseqs[sampnum].append(-1)

    def remove_duplicate_drum_patterns(self, samplist):
        """
        sample_list is a list of pattern numbers associated with the instruments
        to print on this event, e.g. ((1, 'b'), (2, 's'), (4, 'bs'), (7, 'bsh'))
        """
        inst2samp = {x: y[0] for x, y in enumerate(self.samplenames)}
        ## samp2inst = {y[0]: x for x, y in enumerate(self.samplenames)}
        single_instrument_samples = [inst2samp[x - 1] for x, y in samplist
                                     if len(y) == 1]
        ## lookup = {y: inst2samp[x - 1] for x, y in samplist if len(y) == 1}
        samp2lett = {inst2samp[x - 1]: y for x, y in samplist}
        drumpatterns = collections.defaultdict(lambda: collections.defaultdict(list))
        self.pattlengths = collections.defaultdict(dict)

        for pattnum, data in self._pattern_data.items():
            ## print(data)
            for sampnum, patt in data.items():
                if sampnum not in single_instrument_samples:
                    continue
                samplett = samp2lett[sampnum]
                drumpatterns[pattnum]['len'].append((samplett, patt['len']))
                # theoretisch kan dit data voor meer toonhoogten bevatten
                # maar voor mijn spullen kan ik uitgaan van één
                drumpatterns[pattnum][samplett] = [y for x, y in patt.items()
                                                   if x != 'len'][0]

        for pattnum, data in self._pattern_data.items():
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
                print('ongelijke lengtes in pattern {}: {}'.format(
                    pattnum, self.pattlengths[pattnum]))
            patt['len'] = lengths[0]

            try:
                new_pattnum = pattern_list.index(patt) + 1
            except ValueError:
                pattern_list.append(patt)
                new_pattnum = len(pattern_list)
            renumber[pattnum] = new_pattnum
        self.pattern_data['drums'] = pattern_list
        for seq in self._pattern_list:
            if seq in renumber:
                self.playseqs['drums'].append(renumber[seq])
            else:
                self.playseqs['drums'].append(-1)

    def print_general_data(self, sample_list=None, full=False, _out=sys.stdout):
        if sample_list is None: sample_list = []
        drumsamples = [x for x, y in sample_list]
        data = shared.build_header("module", self.filename)

        instruments = []
        self.playseqs = collections.defaultdict(list)
        for sampseq, sample in enumerate(self.samplenames):
            sample_name = sample[1]
            sample_string = ''
            sample_number = sampseq + 1
            if sample_list:
                for sampnum, sampstr in sample_list:
                    if sampnum == sample_number:
                        sample_string = sampstr.join((' (', ')'))
            instruments.append((sample_number, sample_name + sample_string))
            if sample_number not in drumsamples:
                self.remove_duplicate_patterns(sample_number)
        if drumsamples:
            self.remove_duplicate_drum_patterns(sample_list)
        data.extend(shared.build_inst_list(instruments))
        # pattern lengtes voor alle playseqs aanvullen
        ## combined_playseqs = collections.defaultdict(list)
        maxlen = max((len(x) for x in self.playseqs.values()))
        if maxlen != min((len(x) for x in self.playseqs.values())):
            print('Alarm! Niet alle tracks hebben evenveel pattern events',
                  file=_out)
        pattlens = [0] * (maxlen)
        for sampnum, playseq in self.playseqs.items():
            for ix, pattnum in enumerate(playseq):
                if pattnum != -1:
                    pattlen = self.pattern_data[sampnum][pattnum - 1]['len']
                    if pattlens[ix] == 0:
                        pattlens[ix] = pattlen
                    elif pattlens[ix] != pattlen:
                        print('Alarm! Verschillende lengtes voor pattern event', ix,
                              file=_out)
        self.pattlens = pattlens
        self.full_length = sum((x for x in self.pattlens))

        if not full:
            data.extend(shared.build_patt_header())
            for sample_number, sample_name in instruments:
                if sample_number not in drumsamples:
                    data.extend(shared.build_patt_list(sample_number, sample_name,
                                                       self.playseqs[sample_number]))
            if 'drums' in self._pattern_list:
                data.extend(shared.build_patt_list('', 'Drums',
                                                   self.playseqs['drums']))

        for text in data:
            print(text.rstrip(), file=_out)

    def print_drums(self, printseq, _out=sys.stdout):
        """collect the drum sample events and print them together

        printseq indicates the sequence to print these top to bottom e.g. 'hsb'
        stream is a file-like object to write the output to
        """
        for pattnum, pattern in enumerate(self.pattern_data['drums']):
            print(shared.patt_start.format(pattnum + 1), file=_out)
            pattlen = pattern.pop('len')
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
            pattlen = pattern.pop('len')
            for note in reversed(sorted([x for x in pattern])):
                print(shared.line_start, end='', file=_out)
                events = pattern[note]

                printable = []
                for tick in range(pattlen):
                    if tick in events:
                        corr = int(note) - 1    # comparability
                        next_note = shared.get_note_name(corr)
                    else:
                        next_note = shared.empty_note
                    printable.append(next_note)
                print(' '.join(printable), file=_out)
            print('', file=_out)

    def prepare_print_drums(self, printseq):
        self.all_drum_events = collections.defaultdict(list)
        ## print(self.initial_patterns, file=_out)
        for pattseq, pattnum in enumerate(self.playseqs['drums']):
            pattlen = self.pattlens[pattseq]
            initial_patt = pattlen * [shared.empty_drums]
            for inst in printseq:
                pattdata = initial_patt[:]
                if pattnum > -1:
                    for event in range(pattlen):
                        if event in self.pattern_data['drums'][pattnum - 1][inst]:
                            pattdata[event] = inst
                self.all_drum_events[inst].extend(pattdata)

    def print_drums_full(self, printseq, opts, _out=sys.stdout):
        interval, clear_empty = opts
        interval *= 2
        empty = interval * shared.empty_drums

        for eventindex in range(0, self.full_length, interval):
            not_printed = True
            for inst in printseq:
                line = ''.join(
                    self.all_drum_events[inst][eventindex:eventindex + interval])
                if clear_empty and line == empty:
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                print(shared.empty_drums, file=_out)
            print('', file=_out)

    def prepare_print_instruments(self, samplist):
        self.all_note_tracks = collections.defaultdict(
            lambda: collections.defaultdict(list))
        self.all_notes = collections.defaultdict(set)
        for sample, _ in samplist:  # sampname

            ## pattdict = collections.defaultdict(lambda: collections.defaultdict(list))
            for pattnum, pattern in enumerate(self.pattern_data[sample]):
                self.all_notes[sample].update(pattern.keys())
            self.all_notes[sample].discard('len')
            self.all_notes[sample] = [
                x for x in reversed(sorted(self.all_notes[sample]))]

            for pattseq, pattnum in enumerate(self.playseqs[sample]):
                pattlen = self.pattlens[pattseq]
                if pattnum == -1:
                    for note in self.all_notes[sample]:
                        self.all_note_tracks[sample][note].extend(
                            [shared.empty_note] * pattlen)
                    continue
                pattern = self.pattern_data[sample][pattnum - 1]
                for note in self.all_notes[sample]:
                    events = pattern[note]
                    for i in range(pattlen):
                        if i in events:
                            to_append = shared.get_note_name(
                                ## note + shared.octave_length - 1)
                                note - 1)
                        else:
                            to_append = shared.empty_note
                        self.all_note_tracks[sample][note].append(to_append)

    def print_instrument_full(self, sample, opts, _out=sys.stdout):
        interval, clear_empty = opts
        sep = ' '
        empty = sep.join(interval * [shared.empty_note])

        for eventindex in range(0, self.full_length, interval):
            not_printed = True
            for note in self.all_notes[sample]:
                tracknotes = self.all_note_tracks[sample][note]
                line = sep.join(tracknotes[eventindex:eventindex + interval])
                if clear_empty and line == empty:
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                print(shared.empty_note, file=_out)
            print('', file=_out)

    def print_all_instruments_full(self, samplist, printseq, opts, _out=sys.stdout):
        interval, clear_empty = opts

        inst2sam = {y: x for x, y in self.samplenames}
        for eventindex in range(0, self.full_length, interval):

            sep = ' '
            empty = sep.join(interval * [shared.empty_note])
            for _, sampname in samplist:
                print(sampname, file=_out)
                sample = inst2sam[sampname]
                not_printed = True
                for note in self.all_notes[sample]:
                    tracknotes = self.all_note_tracks[sample][note]
                    line = sep.join(tracknotes[eventindex:eventindex + interval])
                    if clear_empty and line == empty:
                        pass
                    else:
                        print('  ', line, file=_out)
                        not_printed = False
                if not_printed:
                    print('  ', shared.empty_note, file=_out)
                print('', file=_out)

            sep = ''
            empty = interval * shared.empty_drums
            print('drums:', file=_out)
            not_printed = True
            for inst in printseq:
                tracknotes = self.all_drum_events[inst]
                line = sep.join(tracknotes[eventindex:eventindex + interval])
                if clear_empty and line == empty:
                    pass
                else:
                    print('  ', line, file=_out)
                    not_printed = False
            if not_printed:
                print('  ', shared.empty_drums, file=_out)
            print('', file=_out)

            print('', file=_out)
