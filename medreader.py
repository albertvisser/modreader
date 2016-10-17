import struct
import collections
import shared

def get_note_name(inp):
    """translate note number to note name
    """
    if inp == 0:
        return '...'
    return shared.get_note_name(inp - 1)

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
    return str(text[0], encoding='utf-8').rstrip('\x00')


class MedModule:

    def __init__(self, filename):
        self.filename = filename
        self.read()


    def read(self):

        # instead of repositioning while reading, read the entire file first and then
        # reposition in memory?

        with open(self.filename, 'rb') as _med:

            mod_header = struct.unpack('>4s9L4HhBB', _med.read(52))
            self.modtype = str(mod_header[0], encoding='utf-8')
            if self.modtype not in ('MMD0', 'MMD1'):
                return
            modlen = mod_header[1]
            songinfo_start = mod_header[2]
            blockarray_start = mod_header[4]
            instheader_start = mod_header[6]
            expansion_start = mod_header[8]

            _med.seek(songinfo_start)
            songinfo = struct.unpack('>504BHH256BHBbbb16bbb', _med.read(788))
            blockcount = songinfo[504]
            self.songlen = songinfo[505]
            self.pattern_list = songinfo[506:506+256]
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
                    instname += ' (empty)'
                self.samplenames.append(instname)

            self.pattern_lengths = []
            self.pattern_data = []
            self.pattern_desc = {}
            ## for i in range(blockcount):
            for address in blockstart_list:
                ## _med.seek(blockstart_list[i])
                _med.seek(address)
                this_pattern = []
                if self.modtype == 'MMD0':
                    tracks, lines = struct.unpack('BB', _med.read(2))
                    self.pattern_lengths.append(lines)
                    for x in range(lines + 1):
                        linedata = []
                        for y in range(tracks):
                            notedata = struct.unpack('3B', _med.read(3))
                            linedata.append(mmd0_decode(notedata)[:2])
                        this_pattern.append(linedata)

                elif self.modtype == 'MMD1':
                    tracks, lines, address = struct.unpack('>HHL', _med.read(8))
                    self.pattern_lengths.append(lines)
                    for x in range(lines):
                        linedata = []
                        for y in range(tracks):
                            notedata = struct.unpack('4B', _med.read(4))
                            linedata.append(mmd1_decode(notedata)[:2])
                        this_pattern.append(linedata)

                    if address:
                        _med.seek(address)
                        data = struct.unpack('>3L', _med.read(12))
                        address, len = data[1:]
                        _med.seek(address)
                        pattern_text = read_string(_med, len)
                        self.pattern_desc[i] = pattern_text

                self.pattern_data.append(this_pattern)
            self.pattern_count = blockcount

    def checks(self):
        print('songlen == len of pattern list (this is ok)?', end=' ')
        print(self.songlen == len(self.pattern_list))
        print('number of samples == len of sample list?', end=' ')
        print(self.sample_count == len(self.samplenames))
        print('number of patterns == len of pattern data list?', end=' ')
        print(self.pattern_count == len(self.pattern_data))

    def print_general_data(self, _out, sample_list=None):
        printable = "Details of module {}".format(self.filename)
        data = [printable, "=" * len(printable), '',
            'description: ' + self.songdesc, '']
        for sample_number, sample_name in enumerate(self.samplenames):
            sample_string = ''
            if sample_list:
                for sampnum, sampstr in sample_list:
                    if sampnum == sample_number + 1:
                        sample_string = sampstr.join((' (', ')'))
            if sample_number > 0:
                data.append(("sample {:>2}: {}".format(sample_number,
                    sample_name + sample_string)))

        data.append('patterns:')
        printable = '          '
        count = 8
        for ix in range(self.songlen):
            printable += '{:>2} '.format(self.pattern_list[ix])
            if (ix + 1) % count == 0:
                data.append(printable)
                printable = '          '
        data.append(printable)

        if self.pattern_desc:
            data.append('')
        for i, x in self.pattern_desc.items():
            data.append('       {:>2}: {}'.format(i, x))

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
        for pattnum, pattern in enumerate(self.pattern_data):
            if len(pattern) == 0: continue
            last_event = False
            for ix, track in enumerate(pattern):
                for note, samp in track:
                    for sampnum, instruments in sample_list:
                        if samp == sampnum:
                            for ins in instruments:
                                all_events[pattnum][ins].append(ix)
        for pattnum, pattern in all_events.items():
            print('pattern', pattnum, file=_out)
            pattlen = self.pattern_lengths[pattnum] + 1
            for inst in printseq:
                for key, events in pattern.items():
                    if key != inst: continue
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
        all_events = collections.defaultdict(lambda: collections.defaultdict(list))
        maxlen = {}
        notes = collections.defaultdict(set)
        for pattnum, pattern in enumerate(self.pattern_data):
            events = []
            last_event = False
            for ix, track in enumerate(pattern):
                note_found = False
                for note, samp in track:
                    if samp == sample:
                        all_events[pattnum][note].append(ix)
                        notes[pattnum].add(note)
            if not notes:
                continue
        for pattnum, pattern in all_events.items():
            print('pattern', pattnum, file=_out)
            pattlen = self.pattern_lengths[pattnum] + 1
            for notestr in reversed(sorted(notes[pattnum])):
                print('           ', end='', file=_out)
                for note, events in pattern.items():
                    if note == notestr:
                        for tick in range(pattlen):
                            printable = get_note_name(notestr) if tick in events else '...'
                            print(printable, end= ' ', file=_out)
                        break
                print('', file=_out)
            print('', file=_out)


if __name__ == "__main__":
    test = MedModule('/home/albert/magiokis/data/med/alleenal.med')
    ## test = MedModule('/home/albert/magiokis/data/med/alsjener.med')
    test.checks()
    with open('/tmp/alleenal.patterns', 'w') as _out:
    ## with open('/tmp/alsjener.patterns', 'w') as _out:
        for i in range(test.pattern_count):
            extra = ''
            if i in test.pattern_desc:
                extra = ' ({})'.format(test.pattern_desc[i])
            print('\npattern {:>2}{}:\n'.format(i, extra), file=_out)
            for line in test.pattern_data[i]:
                print(line, file=_out)
    with open('/tmp/alleenal.instrument', 'w') as _out:
    ## with open('/tmp/alsjener.instrument', 'w') as _out:
        test.print_instrument(3, _out)
        ## test.print_instrument(11, _out)
    mapping = ((2, 'b'), (4, 'd'), (5, 'h'))
    ## mapping = ((2, 'b'), (3, 's'), (5, 'h'), (8, 'c'), (9, 'r'), (10, 'C'))
    with open('/tmp/alleenal.drums', 'w') as _out:
    ## with open('/tmp/alsjener.drums', 'w') as _out:
        test.print_drums(mapping, 'hdb', _out)
        ## test.print_drums(mapping, 'Ccrhsb', _out)
    with open('/tmp/alleenal.general', 'w') as _out:
    ## with open('/tmp/alsjener.general', 'w') as _out:
        test.print_module_details(_out, mapping)
