import sys
import os
import subprocess
import collections
import pprint
try:
    import lxml.etree as et
except ImportError:
    import xml.etree.ElementTree as et
import shared

class MMPFile:

    def __init__(self, filename):
        self.filename = filename
        self.read()

    def read(self):
        mmpz_time = os.stat(self.filename).st_mtime
        project_name = os.path.splitext(os.path.basename(self.filename))[0]
        project_file = '/tmp/{}.mmp'.format(project_name)
        try:
            mmp_time = os.stat(project_file).st_mtime
        except FileNotFoundError:
            mmp_time = 0
        if mmp_time < mmpz_time:
            with open(project_file, 'w') as _out:
                subprocess.run(['lmms', '-d', self.filename], stdout=_out)
        data = et.ElementTree(file=project_file)
        root = data.getroot()

        # getting the regular instruments
        tracks = root.findall('./song/trackcontainer/track[@type="0"]')
        self.tracknames = set([x.get("name") for x in tracks])

        patternlists = collections.defaultdict(list)
        patterndata = collections.defaultdict(list)
        trackdata = collections.defaultdict(list)
        trackdata_split = collections.defaultdict(list)
        self.pattern_starts = collections.defaultdict(dict)
        for name in self.tracknames:
            for tracknum, track in enumerate(tracks):
                if track.get('name') != name:
                    continue
                data, data_split, pattstarts = self.read_track(tracknum, track)
                trackdata[name].extend(data)
                trackdata_split[name].extend(data_split)
                self.pattern_starts[name][tracknum] = pattstarts

        with open('/tmp/trackdata items.1', 'w') as _o:
            for name, data in trackdata.items():
                print(name, file=_o)
                for item in data:
                ## for item in sorted(data):
                    print('   ', item, file=_o)
            for name, data in trackdata_split.items():
                print(name, file=_o)
                for item in data:
                ## for item in sorted(data):
                    print('   ', item, file=_o)

        for name, data in trackdata.items():
            for start, pattern, len in sorted(data):
                patterndata[name].append((start, pattern, len))
                patternlists[name].append(start)
        self.patternlists = patternlists
        self.patterndata = patterndata

        patternlists = collections.defaultdict(list)
        patterndata = collections.defaultdict(list)
        for name, data in trackdata_split.items():
            pattnum = 0 # start with 1
            got_it = []
            for seq, pattern, len in sorted(data):
                try:
                    pattern_number = got_it.index(sorted(pattern)) + 1
                except ValueError:
                    got_it.append(sorted(pattern))
                    pattnum += 1
                    patterndata[name].append((pattern, len))
                    pattern_number = pattnum
                patternlists[name].append(pattern_number)
        self.patternlists_split = patternlists
        self.patterndata_split = patterndata

        # beat/bassline tracks
        # getting the instruments and patterns per instrument involved
        bbtracks = root.findall('.//bbtrack/trackcontainer/track')
        self.bbtracknames = [x.get("name") for x in bbtracks]
        bbtrackdata = collections.defaultdict(dict)
        bbtrackdata_split = collections.defaultdict(list)
        bbtracklen = collections.defaultdict(list)
        for name in self.bbtracknames:
            for tracknum, track in enumerate(bbtracks):
                if track.get('name') != name:
                    continue
                data, data_split, pattstarts = self.read_track(tracknum, track, bbtrack=True)
                for pattnum, pattdata in enumerate(data):
                    if pattdata[1]:
                        bbtrackdata[pattnum + 1][name] = pattdata[1]
                        bbtracklen[pattnum + 1].append(pattdata[2])
                bbtrackdata_split[name].append(data_split)

        self.bbpatterndata = {}
        for pattnum, pattdata in bbtrackdata.items():
            self.bbpatterndata[pattnum] = (pattdata, max(bbtracklen[pattnum]))

        drumtracks = collections.defaultdict(list)
        for name, data in bbtrackdata_split.items():
            for num, track, len in data[0]: # enumerate(data[0]):
                if track:
                    drumtracks[num].append((name, track, len)) # trackdata))
        self.bbpatterndata_split = drumtracks

        # getting the real pattern starts
        tracks = root.findall('./song/trackcontainer/track[@type="1"]')
        bbeventslist = []
        for tracknum, track in enumerate(tracks):
            for bbtco in track.findall('bbtco'):
                pos = int(bbtco.get('pos')) # // shared.time_unit
                bbeventslist.append((pos, tracknum + 1))
        self.bbpatternlist = [(x, y) for x, y in sorted(bbeventslist)]


    def read_track(self, tracknum, track, bbtrack=False):
        patterns, patterns_split, pattstarts = [], [], []
        pattlist = track.findall('pattern')
        for pattnum, patt in enumerate(pattlist):
            pattname = patt.get('name')
            pattstart = int(patt.get('pos'))
            pattstart_split = pattstart // (shared.time_unit // 2 )
            pattlen = int(patt.get('len'))
            pattlen_split = pattlen // shared.timing_unit
            notes, notes_split = [], []
            notelist = patt.findall('note')
            max = shared.per_line
            for note in notelist:
                when = int(note.get('pos'))
                when_split = when // shared.timing_unit
                if when_split >= max:
                    patterns_split.append((pattstart, notes_split, shared.per_line))
                    pattlen_split -= shared.per_line
                    pattstart_split += 1
                    max += shared.per_line
                    notes_split = []
                notes_split.append((int(note.get('key')),
                    when_split - max + shared.per_line))
                notes.append((int(note.get('key')), when))
            pattstarts.append(pattstart)
            patterns.append((pattstart, notes, pattlen))
            patterns_split.append((pattstart_split, notes_split, pattlen_split))
        return patterns, patterns_split, pattstarts


    ## def get_pattern_starts(self):
        ## result = collections.defaultdict(set)
        ## for inst, instdata in self.pattern_starts.items():
            ## for track, trackdata in instdata.items():
                ## result[inst].update(set(trackdata))
        ## return result


    def print_general_data(self, sample_list=None, full=False, _out=sys.stdout):
        if sample_list is None: sample_list = []
        data = shared.build_header("project", self.filename)
        if self.bbtracknames:
            bb_inst = []
            for i, x in enumerate(self.bbtracknames):
                y = ''
                for ins, lett in sample_list:
                    if ins == x:
                        y = lett
                        break
                if y: y = y.join(('(', ')'))
                bb_inst.append((i + 1, ' '.join((x, y))))
            data.extend(shared.build_inst_list(bb_inst, "Beat/Bassline instruments:"))
            if not full:
                data.extend(shared.build_patt_header("Beat/Bassline patterns:"))
                data.extend(shared.build_patt_list('', '', [x[1] for x in
                    self.bbpatternlist]))

        data.extend(shared.build_inst_list([(i + 1, x) for i, x in enumerate(
            self.tracknames)]))
        if not full:
            data.extend(shared.build_patt_header())
            for i, x in enumerate(self.tracknames):
                data.extend(shared.build_patt_list(i + 1, x, self.patternlists[x]))

        for line in data:
            print(line.rstrip(), file=_out)



# v.w.b drums voorzie ik drie situaties:
#- er worden beat/bassline tracks gebruikt
#    hier moet ik nog in voorzien dat er niet alleen drums maar ook bas oid meedoet
#    theoretisch, want zelf gebruik ik dat eigenlijk niet?
    def print_beat_bassline(self, sample_list, printseq, _out=sys.stdout):
        with open('/tmp/mmp_bbpatterndata', 'w') as _o:
            pprint.pprint(self.bbpatterndata, stream=_o)
        for pattnum, pattern in self.bbpatterndata_split.items():
            print(shared.patt_start.format(pattnum + 1), file=_out)
            events = collections.defaultdict(list)
            for pattname, pattevents, pattlen in pattern:
                for name, letter in sample_list:
                    if name == pattname:
                        pattlet = letter
                for note, ev in pattevents:
                    for letter in pattlet:
                        events[letter].append(ev)
            for letter in printseq:
                printable = [shared.line_start]
                out = False
                for x in range(pattlen):
                    if x in events[letter]:
                        printable.append(letter)
                        out = True
                    else:
                        printable.append(shared.empty_drums)
                if out:
                    print(''.join(printable), file=_out)
            print('', file=_out)


#- er word(t)(en) (een) midi drumtrack(s) gebruikt
    def print_drumtrack(self, trackname, _out=sys.stdout):
        unlettered = set()
        for ix, pattdata in enumerate(self.patterndata_split[trackname]):
            pattern, pattlen = pattdata
            print(shared.patt_start.format(ix + 1), file=_out)
            events = collections.defaultdict(list)
            for pitch, ev in pattern:
                druminst = pitch + shared.octave_length + shared.note2drums
                notestr = shared.get_inst_name(druminst)
                if notestr == '?':
                    unlettered.add('no letter yet for `{}`'.format(
                        shared.gm_drums[druminst][1]))
                events[notestr].append(ev)
            for letter in shared.standard_printseq:
                printable = [shared.line_start]
                out = False
                for x in range(pattlen):
                    if x in events[letter]:
                        printable.append(letter)
                        out = True
                    else:
                        printable.append(shared.empty_drums)
                if out:
                    print(''.join(printable), file=_out)
            print('', file=_out)
        for x in unlettered: print(x, file=_out)
        return unlettered

#- er worden aparte instrumenten gebruikt (to be implemented)
    def print_drums(self, sample_list, printseq, _out=sys.stdout):
        pass

    def print_instrument(self, trackname, _out=sys.stdout):
        for ix, pattdata in enumerate(self.patterndata_split[trackname]):
            pattern, pattlen = pattdata
            print(shared.patt_start.format(ix + 1), file=_out)
            events = collections.defaultdict(list)
            notes = set()
            for pitch, ev in pattern:
                events[pitch].append(ev)
                notes.add(pitch)
            for pitch in reversed(sorted(notes)):
                printable = [shared.line_start[:-1]]
                out = False
                for x in range(pattlen):
                    if x in events[pitch]:
                        corr = pitch + shared.octave_length # for comparability
                        printable.append(shared.get_note_name(corr))
                        out = True
                    else:
                        printable.append(shared.empty_note)
                if out:
                    print(' '.join(printable), file=_out)
            print('', file=_out)

    def print_instrument_full(self, trackname, options, _out=sys.stdout):
        interval, clear_empty = options
        is_drumtrack = trackname == 'drums'
        if is_drumtrack:
            interval *= 2
            sep = ''
            empty = shared.empty_drums
        else:
            sep = ' '
            empty = shared.empty_note
        empty_line = sep.join(interval * [empty])
        # bepaal max. lengte
        start, _, lng = self.patterndata[trackname][-1]
        notes_data_dict = {}
        all_notes = set()
        for pattern in self.patterndata[trackname]:
            all_notes.update([x[0] for x in pattern[1]])
        ## total_length = int((start + len) / shared.timing_unit)
        total_length = (start + lng) // shared.timing_unit
        for note in all_notes:
            notes_data_dict[note] = [empty] * total_length
        for start, pattern, lng in self.patterndata[trackname]:
            for note, timing in pattern:
                ## idx = int((start + timing) / shared.timing_unit)
                idx = (start + timing) // shared.timing_unit
                if is_drumtrack:
                    notes_data_dict[note][idx] = shared.get_inst_name(note +
                        shared.octave_length + shared.note2drums)
                else:
                    notes_data_dict[note][idx] = shared.get_note_name(note +
                        shared.octave_length)
        ## print(notes_data_dict, file=_out)
        if is_drumtrack:
            notes_to_show = [x for x in sorted(all_notes,
                key=lambda x: shared.standard_printseq.index(shared.get_inst_name(
                x + shared.octave_length + shared.note2drums)))]
        else:
            notes_to_show = [x for x in reversed(sorted(all_notes))]
        for eventindex in range(0, total_length, interval):
            not_printed = True
            for note in notes_to_show:
                line = sep.join(notes_data_dict[note][eventindex:eventindex+interval])
                if clear_empty and line == empty_line:
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                print(empty_line, file=_out)
            print('', file=_out)

    def print_beat_bassline_full(self, sample_list, printseq, opts, _out=sys.stdout):
        interval, clear_empty = opts
        # bepaal max. lengte
        # self.bbtracknames: list of instrument names
        # self.bbpatterndata: dict of pattern_number mapped to :
        #         dict of instrument names mapped to:
        #             tuple of : list of tuples of note & timing, pa
        # self.bbpatternlist: list of tuples: start, pattern_number
        """
        {pattern_start: [(sample_name, [(pitch, time), ...], length), ...], ...}
        """
        interval *= 2
        sep = ''
        notes_data_dict = {}
        total_length = 0
        if sample_list:
            instdict = dict(sample_list)
        for pattstart, pattnum in self.bbpatternlist:
            pattdata, pattlen = self.bbpatterndata[pattnum]
            total_length += pattlen
        total_length //= shared.timing_unit #  (shared.tick_factor // 2)
        ## for inst in self.bbtracknames:
        for inst in printseq:
            notes_data_dict[inst] = [shared.empty_drums] * total_length
        ## print(notes_data_dict, file=_out)
        ## return

        for pattstart, pattnum in self.bbpatternlist:
            pattdata, pattlen = self.bbpatterndata[pattnum]
            pattlen //= shared.timing_unit #  (shared.tick_factor // 2)
            for instname in self.bbtracknames:
                if instname in pattdata:
                    for _, timing in pattdata[instname]:
                        note = instdict[instname]
                        indx = (pattstart + timing) // shared.timing_unit
                        notes_data_dict[note][indx] = note
        ## print(notes_data_dict, file=_out)
        ## return

        empty_line = sep.join(interval * [shared.empty_drums])
        for eventindex in range(0, total_length, interval):
            not_printed = True
            for note in printseq:
                line = sep.join(notes_data_dict[note][eventindex:eventindex+interval])
                if clear_empty and line == empty_line:
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                print(empty, file=_out)
            print('', file=_out)



