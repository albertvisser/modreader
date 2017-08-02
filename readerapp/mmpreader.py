"""ModReaderGui - data processing for LMMS project file
"""
import sys
import os
import subprocess
import collections
import pprint
import logging
try:
    import lxml.etree as et
except ImportError:
    import xml.etree.ElementTree as et
import readerapp.shared as shared


def log(inp):
    "local definition to allow for picking up module name in message format"
    logging.info(inp)


def get_druminst_order(x):
    """helper function to determine order of drum instruments

    relies on standard sequence defined in settings
    """
    y = shared.get_inst_name(x + shared.octave_length + shared.note2drums)
    return shared.standard_printseq.index(y)


class MMPFile:
    """Main processing class
    """
    def __init__(self, filename):
        self.filename = filename
        self.read()

    def read(self):
        """unpack the project file if necessary, then read the XML and interpret
        into an internal data collection
        """
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
                data, data_split, pattstarts = self.read_track(track)
                trackdata[name].extend(data)
                trackdata_split[name].extend(data_split)
                self.pattern_starts[name][tracknum] = pattstarts

        ## with open('/tmp/trackdata items.1', 'w') as _o:
            ## for name, data in trackdata.items():
                ## print(name, file=_o)
                ## for item in data:
                    ## print('   ', item, file=_o)
            ## for name, data in trackdata_split.items():
                ## print(name, file=_o)
                ## for item in data:
                    ## print('   ', item, file=_o)

        for name, data in trackdata.items():
            for start, pattern, pattlen in sorted(data):
                patterndata[name].append((start, pattern, pattlen))
                patternlists[name].append(start)
        self.patternlists = patternlists
        self.patterndata = patterndata

        maxpattnum = 0
        for name, data in trackdata_split.items():
            newmax = max((x[0] for x in data))
            if newmax > maxpattnum:
                maxpattnum = newmax
        maxpattnum += 1

        patternlists = collections.defaultdict(lambda: maxpattnum * [-1])
        patterndata = collections.defaultdict(list)
        for name, data in trackdata_split.items():
            pattnum = 0     # start with 1
            got_it = []
            for seq, pattern, pattlen in sorted(data):
                try:
                    pattern_number = got_it.index(sorted(pattern)) + 1
                except ValueError:
                    got_it.append(sorted(pattern))
                    pattnum += 1
                    patterndata[name].append((pattern, pattlen))
                    pattern_number = pattnum
                patternlists[name][seq] = pattern_number
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
            for track in bbtracks:
                if track.get('name') != name:
                    continue
                data, data_split, pattstarts = self.read_track(track)
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
            for num, track, pattlen in data[0]:
                if track:
                    drumtracks[num].append((name, track, pattlen))
        self.bbpatterndata_split = drumtracks

        # getting the real pattern starts
        tracks = root.findall('./song/trackcontainer/track[@type="1"]')
        bbeventslist = []
        for tracknum, track in enumerate(tracks):
            for bbtco in track.findall('bbtco'):
                pos = int(bbtco.get('pos'))
                bbeventslist.append((pos, tracknum + 1))
        self.bbpatternlist = [(x, y) for x, y in sorted(bbeventslist)]

    def read_track(self, track):
        """helper method to break up a track into note events
        """
        patterns, patterns_split, pattstarts = [], [], []
        pattlist = track.findall('pattern')
        ## for pattnum, patt in enumerate(pattlist):
        for patt in pattlist:
            ## pattname = patt.get('name')
            pattstart = int(patt.get('pos'))
            pattstart_split = pattstart // (shared.time_unit // 2)
            pattlen = int(patt.get('len'))
            pattlen_split = pattlen // shared.timing_unit
            notes, notes_split = [], []
            notelist = patt.findall('note')
            ## notecount = shared.per_line
            notecount = 0
            for note in notelist:
                when = int(note.get('pos'))
                when_split = when // shared.timing_unit
                if when_split >= notecount + shared.per_line:
                    patterns_split.append((pattstart_split, notes_split, shared.per_line))
                    pattlen_split -= shared.per_line
                    pattstart_split += 1
                    notecount += shared.per_line
                    notes_split = []
                notes_split.append((int(note.get('key')),
                                    ## when_split - notecount + shared.per_line))
                                    when_split - notecount))
                notes.append((int(note.get('key')), when))
            pattstarts.append(pattstart)
            patterns.append((pattstart, notes, pattlen))
            patterns_split.append((pattstart_split, notes_split, pattlen_split))
        return patterns, patterns_split, pattstarts

    def print_general_data(self, sample_list=None, full=False, _out=sys.stdout):
        """create the "overview" file (sample and pattern lists)
        """
        if sample_list is None:
            sample_list = []
        data = shared.build_header("project", self.filename)
        data.extend(shared.build_inst_list([(i + 1, x) for i, x in enumerate(
            self.tracknames)]))
        if not full:
            data.extend(shared.build_patt_header())
            for i, x in enumerate(self.tracknames):
                data.extend(shared.build_patt_list(i + 1, x, self.patternlists_split[x]))
        if self.bbtracknames:
            bb_inst = []
            for i, x in enumerate(self.bbtracknames):
                y = ''
                for ins, lett in sample_list:
                    if ins == x:
                        y = lett
                        break
                if y:
                    y = y.join(('(', ')'))
                bb_inst.append((i + 1, ' '.join((x, y))))
            data.extend(shared.build_inst_list(bb_inst, "Beat/Bassline instruments:"))
            if not full:
                data.extend(shared.build_patt_header("Beat/Bassline patterns:"))
                data.extend(shared.build_patt_list('', '', [x[1] for x in
                                                            self.bbpatternlist]))
        for line in data:
            print(line.rstrip(), file=_out)

    # v.w.b drums voorzie ik drie situaties:
    # - er worden beat/bassline tracks gebruikt
    #    hier moet ik nog in voorzien dat er niet alleen drums maar ook bas oid meedoet
    #    theoretisch, want zelf gebruik ik dat eigenlijk niet?
    def print_beat_bassline(self, sample_list, printseq, _out=sys.stdout):
        """collect the beat_bassline events and print them pattern by pattern
        """
        with open('/tmp/mmp_bbpatterndata', 'w') as _o:
            pprint.pprint(self.bbpatterndata, stream=_o)
        for pattnum, pattern in self.bbpatterndata_split.items():
            print(shared.patt_start.format(pattnum + 1), file=_out)
            events = collections.defaultdict(list)
            # TODO kunnen we pattlen alstublieft uit ets anders afleiden dan het pattern?
            for pattname, pattevents, pattlen in pattern:
                for name, letter in sample_list:
                    if name == pattname:
                        pattlet = letter
                for ev in pattevents:
                    for letter in pattlet:
                        events[letter].append(ev[1])
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

    # - er word(t)(en) (een) midi drumtrack(s) gebruikt
    def print_drumtrack(self, trackname, _out=sys.stdout):
        """collect the drumtrack events and print them pattern by pattern
        """
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
        ## for x in unlettered: print(x, file=_out)
        return unlettered

    # - er worden aparte instrumenten gebruikt (to be implemented)
    def print_drums(self, sample_list, printseq, _out=sys.stdout):
        """collect the drum instrument events and print them pattern by pattern
        """
        pass

    def print_instrument(self, trackname, _out=sys.stdout):
        """print the events for an instrument as a piano roll

        trackname is the name of the track / sample to print data for
        stream is a file-like object to write the output to
        """
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
                for i in range(pattlen):
                    if i in events[pitch]:
                        corr = pitch + shared.octave_length     # for comparability
                        printable.append(shared.get_note_name(corr))
                        out = True
                    else:
                        printable.append(shared.empty_note)
                if out:
                    print(' '.join(printable), file=_out)
            print('', file=_out)

    def prepare_print_instruments(self, druminst=None):
        """build complete timeline for (drum & regular) instrument events
        """
        if not druminst:
            druminst = []
        self.druminst = druminst
        self.notes_data_dict = collections.defaultdict(dict)
        self.all_notes = collections.defaultdict(set)
        self.total_length = 0
        for trackname in self.tracknames:
            is_drumtrack = trackname in self.druminst
            # bepaal max. lengte
            start, _, lng = self.patterndata[trackname][-1]
            for pattern in self.patterndata[trackname]:
                self.all_notes[trackname].update([x[0] for x in pattern[1]])
            ## total_length = int((start + len) / shared.timing_unit)
            current_length = (start + lng) // shared.timing_unit
            self.total_length = max((current_length, self.total_length))
            empty = shared.empty[is_drumtrack]
            for note in self.all_notes[trackname]:
                self.notes_data_dict[trackname][note] = [empty] * self.total_length
            for start, pattern, lng in self.patterndata[trackname]:
                for note, timing in pattern:
                    ## idx = int((start + timing) / shared.timing_unit)
                    idx = (start + timing) // shared.timing_unit
                    if is_drumtrack:
                        notename = shared.get_inst_name(note + shared.octave_length +
                                                        shared.note2drums)
                    else:
                        notename = shared.get_note_name(note + shared.octave_length)
                    self.notes_data_dict[trackname][note][idx] = notename
            ## print(notes_data_dict, file=_out)

    def print_instrument_full(self, trackname, opts, _out=sys.stdout):
        """output an instrument timeline to a separate file/stream

        trackname indicates the instrument to process
        opts indicates how many events per line and whether to print "empty" lines
        """
        interval, clear_empty = opts
        is_drumtrack = trackname in self.druminst
        if is_drumtrack:
            interval *= 2
            notes_to_show = [x for x in sorted(self.all_notes[trackname],
                                               key=get_druminst_order)]
        else:
            notes_to_show = [x for x in reversed(sorted(self.all_notes[trackname]))]
        sep = shared.sep[is_drumtrack]
        empty_line = sep.join(interval * [shared.empty[is_drumtrack]])
        for eventindex in range(0, self.total_length, interval):
            if eventindex + interval > self.total_length:
                empty_line = sep.join(
                    (self.total_length - eventindex) * [shared.empty[is_drumtrack]])
            not_printed = True
            for note in notes_to_show:
                line = sep.join(self.notes_data_dict[trackname][note]
                                [eventindex:eventindex + interval])
                if clear_empty and (not line or line == empty_line):
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                print(empty_line, file=_out)
            print('', file=_out)

    def prepare_print_beat_bassline(self, sample_list, printseq):
        """build complete timeline for beat_bassline events
        """
        ## notes_data_dict = {}
        self.total_length = 0
        if sample_list:
            instdict = dict(sample_list)
        for pattstart, pattnum in self.bbpatternlist:
            pattdata, pattlen = self.bbpatterndata[pattnum]
            self.total_length += pattlen
        self.total_length //= shared.timing_unit
        for inst in printseq:
            self.notes_data_dict['bb'][inst] = [shared.empty_drums] * self.total_length

        for pattstart, pattnum in self.bbpatternlist:
            pattdata, pattlen = self.bbpatterndata[pattnum]
            pattlen //= shared.timing_unit
            for instname in self.bbtracknames:
                if instname in pattdata:
                    for _, timing in pattdata[instname]:
                        note = instdict[instname]
                        indx = (pattstart + timing) // shared.timing_unit
                        self.notes_data_dict['bb'][note][indx] = note

    def print_beat_bassline_full(self, printseq, opts, _out=sys.stdout):
        """output beat_bassline timeline to a separate file/stream

        printseq indicates the top-to-bottom sequence of the instruments
        opts indicates how many events per line and whether to print "empty" lines
        """
        interval, clear_empty = opts
        interval *= 2
        sep = ''

        empty_line = sep.join(interval * [shared.empty_drums])
        for eventindex in range(0, self.total_length, interval):
            if eventindex + interval > self.total_length:
                empty_line = sep.join(
                    (self.total_length - eventindex) * [shared.empty_drums])
            not_printed = True
            for note in printseq:
                line = sep.join(self.notes_data_dict['bb'][note]
                                [eventindex:eventindex + interval])
                if clear_empty and (not line or line == empty_line):
                    pass
                else:
                    print(line, file=_out)
                    not_printed = False
            if not_printed:
                ## print(empty, file=_out)
                print(shared.empty_drums, file=_out)
            print('', file=_out)

    # net als print_drums (via aparte samples) ook deze twee niet geïmplementeerd:
    def prepare_print_drums(self, sample_list):
        """build complete timeline for drumtrack events
        """
        pass

    def print_drums_full(self, sample_list, printseq, _out=sys.stdout):
        """build complete timeline for combined drum instrument events
        """
        pass

    def print_all_instruments_full(self, instlist, printseq, opts, _out=sys.stdout):
        """output all instrument timelines to the "general" file

        instlist indicates the top-to-bottom sequence of instruments
        printseq indicates the top-to-bottom sequence of drum instruments
        opts indicates how many events per line and whether to print "empty" lines
        """
        interval, clear_empty = opts
        instlist = list(instlist) + list(self.druminst)
        for eventindex in range(0, self.total_length, interval):
            for trackname in instlist:  # denk aan volgorde!
                print('{}:'.format(trackname), file=_out)
                is_drumtrack = trackname in self.druminst
                if is_drumtrack:
                    notes_to_show = [x for x in sorted(self.all_notes[trackname],
                                                       key=get_druminst_order)]
                else:
                    notes_to_show = [x for x in reversed(sorted(
                        self.all_notes[trackname]))]
                sep = shared.sep[is_drumtrack]
                empty = shared.empty[is_drumtrack]
                empty_line = sep.join(interval * [empty])
                if eventindex + interval > self.total_length:
                    empty_line = sep.join((self.total_length - eventindex) * [empty])
                not_printed = True
                for note in notes_to_show:
                    line = sep.join(self.notes_data_dict[trackname][note]
                                    [eventindex:eventindex + interval])
                    if clear_empty and (not line or line == empty_line):
                        pass
                    else:
                        print('  ', line, file=_out)
                        not_printed = False
                if not_printed:
                    print('  ', empty, file=_out)
                print('', file=_out)

            if 'bb' in self.notes_data_dict:
                print('beat-bassline', file=_out)
                sep = ''
                empty_line = sep.join(interval * [shared.empty_drums])
                if eventindex + interval > self.total_length:
                    empty_line = sep.join(
                        (self.total_length - eventindex) * [shared.empty_drums])
                not_printed = True
                for note in printseq:
                    line = sep.join(self.notes_data_dict['bb'][note]
                                    [eventindex:eventindex + interval])
                    if clear_empty and (not line or line == empty_line):
                        pass
                    else:
                        print('  ', line, file=_out)
                        not_printed = False
                if not_printed:
                    ## print('  ', empty_line, file=_out)
                    print('  ', shared.empty_drums, file=_out)
                print('', file=_out)

            print('', file=_out)
