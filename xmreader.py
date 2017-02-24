import logging
logging.basicConfig(filename='/tmp/xmreader.log',level=logging.DEBUG)
log = logging.info
import pprint
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

class ExtModule:

    def __init__(self, filename):
        log('\n'.join(('', '---- *** ----', '')))
        self.filename = filename
        self.pattern_data = {}
        self.pattern_lengths = []
        self.playseqs = collections.defaultdict(list)
        self.instruments = {}
        self.read()
        ## if not self._pattern_data:
            ## raise ValueError('Empty module !?')
        ## self._all_events = collections.defaultdict(lambda: collections.defaultdict(
            ## lambda: collections.defaultdict(list)))
        ## sampledata_found = collections.defaultdict(lambda: False)
        ## for pattnum, pattern in enumerate(self._pattern_data):
            ## length, pattern = pattern
            ## self.pattern_lengths.append(length)
            ## events = []
            ## last_event = False
            ## for ix, track in enumerate(pattern):
                ## for note, samp in track:
                    ## if note:
                        ## sampledata_found[samp] = True
                        ## self._all_events[pattnum][samp]['len'] = length
                        ## self._all_events[pattnum][samp][note].append(ix)
        ## samples_to_keep = []
        ## for ix, samp in enumerate(self.samplenames):
            ## if sampledata_found[ix + 1]:
                ## samples_to_keep.append((ix, samp))
        ## self.samplenames = samples_to_keep


    def read(self):

        # instead of repositioning while reading, read the entire file first and then
        # reposition in memory?
        # make sure the resulting patterns are 32 events tops

        with open(self.filename, 'rb') as _xm:

            xm_id = read_string(_xm, 17)
            module_name = read_string(_xm, 20)
            x1A = struct.unpack('B', _xm.read(1))
            tracker_name = read_string(_xm, 20)
            tracker_ver = '.'.join([str(x) for x in
                struct.unpack('BB', _xm.read(2))])
            xm_header = struct.unpack('<L8H', _xm.read(20))
            header_size, song_length, restart_pos = xm_header[:3]
            channel_count, pattern_count, instr_count = xm_header[3:6]
            freq_table, dflt_tempo, dflt_bpm = xm_header[6:]
            log('{}'.format(xm_header))
            pattern_table = struct.unpack('256B', _xm.read(256))
            initial_pattern_list = pattern_table[:int(song_length)]
            pattern_map = {}

            initial_pattern_data = {}
            pattstart = header_size + 60
            for pattnum in range(pattern_count):
                "read pattern data"
                _xm.seek(pattstart)        # position at start of pattern header
                size, _, rows, data_size = struct.unpack('<LBHH', _xm.read(9))
                log('pattern {} at {}; size {} rows {} datasize {}'.format(
                    pattnum, hex(pattstart), size, rows, data_size))
                orig_pattstart = pattstart
                pattstart += size
                pattern_map[pattstart] = pattnum
                _xm.seek(pattstart) # position at start of pattern data
                pattdata = []
                if data_size > 0:
                    for rownum in range(rows):
                        if rownum and rownum % 32 == 0:
                            initial_pattern_data[pattstart] = pattdata
                            pattstart = _xm.tell()
                            pattdata = []
                        rowdata = []
                        endpattern = False
                        for channel in range(channel_count):
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
                initial_pattern_data[pattstart] = pattdata
                pattstart = orig_pattstart + size + data_size     # calculate next pattern start

            inst_start = pattstart
            print(hex(inst_start))

            for instnum in range(instr_count):
                _xm.seek(inst_start)
                inst_size = struct.unpack('<L', _xm.read(4))[0]     # bv 0x00000107
                inst_name = read_string(_xm, 22)                    # bv ElecBass
                inst_type = struct.unpack('B', _xm.read(1))[0]      # bv 0xCF
                sampcount = struct.unpack('<H', _xm.read(2))[0]     # bv 0x0001
                samp_hdr_size = struct.unpack('<L', _xm.read(4))[0] # bv. 0x00000028
                self.instruments[instnum] = [inst_name, inst_start]
                samples = []
                _xm.seek(inst_start + inst_size)
                inst_start += inst_size + samp_hdr_size
                for sampnum in range(sampcount):
                    print(hex(_xm.tell()))
                    test = _xm.read(18)
                    samp_header = struct.unpack('<LLLBBBBBB', test)
                    samp_name = read_string(_xm, 22)
                    samp_leng = samp_header[0]
                    samples.append((samp_name, samp_leng))
                    inst_start += samp_leng
                self.instruments[instnum].append(samples)


        with open('/tmp/xm_data', 'w') as _o:
            for inst, data in self.instruments.items():
                name, start, samples = data
                print(inst, name, hex(start), file=_o)
                for name, len in samples:
                    print('   ', name, hex(len), file=_o)
            print(initial_pattern_list, file=_o)
            for start, num in sorted(pattern_map.items()):
                print(hex(start), num, file=_o)
            for patt, data in sorted(initial_pattern_data.items()):
                print(hex(patt), file=_o)
                for line in data:
                    print('   ', line, file=_o)


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
                print('ongelijke lengtes in pattern {}: {}'.format(pattnum,
                    self.pattlengths[pattnum]))
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


    def print_general_data(self, _out, sample_list=None):
        if sample_list is None: sample_list = []
        drumsamples = [x for x, y in sample_list]
        data = shared.build_header("module", self.filename, self.songdesc)

        instruments = []
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
        data.extend(shared.build_patt_header())

        for sample_number, sample_name in instruments:
            if sample_number not in drumsamples:
                data.extend(shared.build_patt_list(sample_number, sample_name,
                    self.playseqs[sample_number]))
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

    def print_instrument(self, sample, _out):
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
                        corr = note + 3 * shared.octave_length - 1 # comparability
                        next = shared.get_note_name(corr)
                    else:
                        next = shared.empty_note
                    printable.append(next)
                print(' '.join(printable), file=_out)
            print('', file=_out)

