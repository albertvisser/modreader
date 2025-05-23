"""ModReaderGui - data processing for Reaper project file
"""
import sys
import collections
import pprint
import logging
from readerapp import shared


def log(inp):
    "local definition to allow for picking up module name in message format"
    logging.info(inp)


class RppFile:
    """Main processing class
    """
    def __init__(self, filename):
        self.filename = filename
        self.procs = {
            '<TRACK': self.start_track,
            'NAME': self.process_name,
            '<ITEM': self.start_item,
            '<SOURCE': self.start_source,
            'HASDATA': self.start_data,
            'E': self.process_event,
            '>': self.finalize}

        self.weirdness = []
        # mapping van naam op trackid(s)
        self.instruments = {}
        # mapping van trackid op volgnr (s) op data
        self.patterns = collections.defaultdict(list)
        self.pattern_list = collections.defaultdict(list)
        self.short_format = None
        self.show_continual = None
        self.read()

    def start_track(self, data):
        """identify track, e.g.
          <TRACK '{604D0845-C894-4422-B3F7-3CD51F610A63}'
        """
        ## log("in start_track: {}".format(data))
        self.current_track = data[1:-1]     # do I need this if I use instrument numbers?
        self.in_track = True

    def process_name(self, data):
        """read name for current level e.g.
            NAME "Heavymetal - alleen_al"
        """
        ## log("in process_name: {}".format(data))
        name = data[1:-1]
        if not self.in_pattern:
            self.instrument_number += 1
            self.instruments[self.instrument_number] = name
        else:
            self.pattern_props = {'name': name}

    def start_item(self):  # , data):
        """start of the block containing the pattern e.g.
          <ITEM
        """
        ## log("in start_item: {}".format(data))
        self.in_pattern = True
        self.pattern_no = 0

    def start_source(self, data):
        """check source type e.g.
          <SOURCE MIDI
        """
        ## log("in start_source: {}".format(data))
        self.ignore = data != 'MIDI'
        self.in_source = True

    def start_data(self, data):
        """start of data block in case of midi, e.g.
        HASDATA 1 384 QN (zie onder)
        """
        if self.ignore:
            return
        ## log("in process_data: {}".format(data))
        self.pattern_props['resolution'] = int(data.split()[1])
        self.pattern_data = collections.defaultdict(list)
        self.timing = 0
        self.track_start = True
        self.pattern_events = collections.defaultdict(list)

    def process_event(self, data):
        """note on/off and other midi events, e.g.
        E 0 c0 14 00
        """
        if self.ignore:
            return
        ## log("in process_event: {}".format(data))
        data = data.split()
        tick = int(data[0])
        evtype = data[1][0]
        channel = data[1][1]
        pitch = int(data[2], base=16)
        velocity = data[3]
        self.timing += tick
        if self.track_start or evtype == 'c':   # start new pattern
            if self.pattern_events:
                self.patterns[self.instrument_number].append((self.pattern_no,
                                                              self.pattern_props,
                                                              self.pattern_events))
                self.pattern_list[self.instrument_number][-1].append(self.pattern_length)
                self.pattern_events = collections.defaultdict(list)
            self.pattern_no += 1
            self.pattern_start = 0 if self.track_start else self.timing
            ## self.pattern_start = self.timing
            start = self.pattern_start // (self.pattern_props['resolution'] // 4)
            self.pattern_list[self.instrument_number].append([self.pattern_no, start])
            if self.track_start:
                self.track_start = False
        if evtype != '9':   # we're only interested in `note on`
            return
        if velocity == '00':    # set volume to zero == note off
            return
        now = self.timing - self.pattern_start
        now = now // (self.pattern_props['resolution'] // 4)
        if 'drumtrack' not in self.pattern_props:
            self.pattern_props['drumtrack'] = False
            if channel == str(shared.drum_channel - 1):
                self.pattern_props['drumtrack'] = True
        self.pattern_events[pitch].append(now)
        self.pattern_length = now

    def finalize(self):  # , data):
        """end of block starting with <, same on any level:
         >
        """
        if self.in_source:
            self.patterns[self.instrument_number].append((self.pattern_no,
                                                          self.pattern_props,
                                                          self.pattern_events))
            self.pattern_list[self.instrument_number][-1].append(self.pattern_length)
            self.in_source = False
        elif self.in_pattern:
            self.in_pattern = False
        elif self.in_track:
            self.in_track = False

    def read(self):
        """read the file into internal structures
        using the preceding methods/callbacks"""
        self.in_track = self.in_pattern = self.in_source = False
        self.instrument_number = 0
        with open(self.filename) as _in:
            for line in _in:
                line = line.strip()
                try:
                    linetype, data = line.split(None, 1)
                except ValueError:
                    linetype = line
                if linetype in self.procs:
                    self.procs[linetype](data)
        with open('/tmp/rpp_patterns', 'w') as _o:
            pprint.pprint(self.pattern_list, stream=_o)
            pprint.pprint(self.patterns, stream=_o)

        self.old_patterns = self.patterns
        self.old_pattern_list = self.pattern_list
        new_patterns = collections.defaultdict(list)
        new_pattern_list = collections.defaultdict(list)
        pattstarts = collections.defaultdict(set)
        for track, pattern_start_list in self.pattern_list.items():
            new_patterns_temp = []
            new_pattern_list_temp = {}
            pattix = 0
            ## pattgen = ((x, y, z) for x, y, z in self.patterns[track])
            abspattstart = 0

            for item in pattern_start_list:

                oldpattnum, oldpattstart = item[:2]
                abspattstart += oldpattstart
                oldpattnum2, oldpattprops, oldpattdata = self.patterns[track][pattix]
                log(f"{oldpattnum} {oldpattnum2} {abspattstart}")
                if oldpattnum2 > oldpattnum or not oldpattdata:
                    continue    # no data for pattern (just event c0 after event c0)
                if oldpattnum2 != oldpattnum:     # should never happen
                    with open('/tmp/rpp_patterns', 'w') as _o:
                        pprint.pprint(self.patterns, stream=_o)
                    with open('/tmp/rpp_pattern_list', 'w') as _o:
                        pprint.pprint(self.pattern_list, stream=_o)
                    raise ValueError(f'mismatch on track {track} pattern {oldpattnum} met'
                                     f' pattern {oldpattnum2}, data dumped to /tmp')
                newpattdata = collections.defaultdict(dict)
                for pitch, events in oldpattdata.items():
                    ## newpattnum = 0
                    low_event = 0
                    highest = max(events) + shared.per_line
                    high_event = low_event + shared.per_line

                    ## pattstarts.add((low_event, high_event))
                    pattstarts[track].add(
                        (low_event + abspattstart, high_event + abspattstart))
                    while high_event <= highest:
                        new_events = [x - low_event for x in events
                                      if low_event <= x < high_event]
                        if new_events:
                            newpattstart = oldpattstart + low_event
                            newpattdata[newpattstart][pitch] = new_events
                        low_event = high_event
                        high_event += shared.per_line
                        ## pattstarts.add((low_event, high_event))
                        pattstarts[track].add(
                            (low_event + abspattstart, high_event + abspattstart))
                ## pdb.set_trace()
                pattnum = 0
                for pattstart, pattdata in sorted(newpattdata.items()):
                    pattnum += 1
                    new_pattern_list_temp[pattnum] = pattstart
                    new_patterns_temp.append((pattnum, oldpattprops, pattdata))

                pattix += 1

            previous_patterns = []
            newnum = 0
            for item in new_patterns_temp:
                patt, props, data = item
                start = new_pattern_list_temp[patt]
                if not data:
                    continue
                try:
                    num_ = previous_patterns.index(data) + 1
                except ValueError:
                    previous_patterns.append(data)
                    newnum += 1
                    num_ = newnum
                    new_patterns[track].append((num_, props, data))
                new_pattern_list[track].append((start, num_))

        self.pattstarts = {}
        for track, starts in pattstarts.items():
            ## self.pattstarts[track] = [(x, y - x) for x, y in sorted(starts)]
            self.pattstarts[track] = sorted(starts)
        ## pdb.set_trace()
        # TODO hier moet ik verder gaan opknippen om de pattern starts
        # voor de verschillende tracks in overeenstemming met elkaar te brengen
        # ook mag het laatste event van een pattern niet na het begin van de volgende vallen
        for track, pattdata in new_pattern_list.items():
            tempdict = dict(pattdata)
            new_patt_list = []
            for pattstart in self.pattstarts[track]:
                try:
                    new_patt_list.append((pattstart[0], tempdict[pattstart[0]]))
                except KeyError:
                    new_patt_list.append((pattstart[0], -1))
            new_pattern_list[track] = new_patt_list

        self.patterns = new_patterns
        self.pattern_list = new_pattern_list
        self.instruments = {x: y for x, y in self.instruments.items() if x in
                            self.pattern_list}

    def process(self, gui):
        """Create output for Reaper project

        this is assuming I only have projects that use MIDI data
        where drums are in a separate track instead of one drum per track
        """
        with open(gui.get_general_filename(), 'w') as _out:
            self.print_general_data(gui.show_continual, _out)
        # kijken of er dubbele namen zijn
        test, dubbel = set(), set()
        # for trackno, data in self.instruments.items():
        for data in self.instruments.values():
            if data in test:
                dubbel.add(data)
            else:
                test.add(data)
        self.prepare_print_instruments()
        options = (gui.max_events.value(), gui.check_nonempty.isChecked())
        if gui.check_allinone.isChecked():
            inst_list = gui.list_items(gui.list_samples)
            inst_list += [x.rsplit(' ', 1)[0] for x in gui.list_items(gui.mark_samples)]
            with open(gui.get_general_filename(), 'a') as _out:
                self.print_all_instruments_full(inst_list, options, _out)
            return []
        all_unlettered = []
        for trackno, data in self.instruments.items():
            name = data
            if name in dubbel:
                name += '-' + str(trackno)
            with open(gui.get_instrument_filename(name), 'w') as _out:
                if gui.check_full.isChecked():
                    self.print_instrument_full(trackno, options, _out)
                    unlettered = []
                else:
                    unlettered = self.print_instrument(trackno, _out)
            for line in unlettered:
                all_unlettered.append(f'track {trackno}: {line}')
        return all_unlettered

    def print_general_data(self, full=False, stream=sys.stdout):
        """create the "overview" file (sample and pattern lists)
        """
        data = shared.build_header("project", self.filename)
        data.extend(shared.build_inst_list(list(sorted(self.instruments.items()))))
        if not full:
            data.extend(shared.build_patt_header())
            for item, value in self.pattern_list.items():
                patt_list = [y for x, y in value]
                data.extend(shared.build_patt_list(item, self.instruments[item],
                                                   patt_list))
        for line in data:
            print(line.rstrip(), file=stream)

    def print_instrument(self, trackno, stream=sys.stdout):
        """print the events for an instrument as a piano roll

        trackno is the number of the track / sample to print data for
        stream is a file-like object to write the output to
        """
        data = []
        unlettered = set()
        for patt_no, props, patt_data in self.patterns[trackno]:
            data.append(shared.patt_start.format(patt_no))
            is_drumtrack = props['drumtrack']
            printables = collections.defaultdict(list)
            for key, note_events in patt_data.items():
                seqnum = 0
                events = []
                if is_drumtrack:
                    notestr = shared.get_inst_name(key + shared.note2drums)
                    if notestr == '?':
                        name = shared.gm_drums[key + shared.note2drums][1]
                        unlettered.add(f'no letter yet for `{name}`')
                    else:
                        key = shared.standard_printseq.index(notestr)
                else:
                    notestr = shared.get_note_name(key)     # (was - 12)
                factor = shared.tick_factor
                for i in range(factor * (note_events[-1] // factor + 1)):
                    if i in note_events:
                        events.append(notestr)
                    else:
                        events.append(shared.empty[is_drumtrack])
                    if (i + 1) % factor == 0:
                        seqnum += 1
                        if events != factor * [shared.empty[is_drumtrack]]:
                            delim = shared.sep[is_drumtrack]
                            printables[seqnum].append((key, delim.join(events)))
                        events = []
            for key, pattern_lines in sorted(printables.items()):
                printlines = sorted(pattern_lines)
                if not is_drumtrack:
                    printlines = reversed(printlines)
                data.extend([shared.line_start + y for x, y in printlines])
                data.append('')
        for line in data:
            print(line, file=stream)
        return unlettered

    def prepare_print_instruments(self):
        """build complete timeline for (drum and regular) instrument events
        """
        self.all_note_tracks = collections.defaultdict(
            lambda: collections.defaultdict(list))
        self.unlettered = set()
        self.all_notes = collections.defaultdict(set)
        # volgens mij moet ik hier weer uitgaan van de oldpatterns om daaruit een volledig track
        # op te bouwen
        # pattern lengtes zijn inmiddels toegevoegd in oldpatternlist, die kan ik gebruiken voor de
        # totale lengte
        self.total_length = 0
        for trackno in self.instruments:
            pattno, pattstart, pattlen = self.old_pattern_list[trackno][-1]
            log(f'{trackno} {pattno} {pattstart} {pattlen}')
            if pattstart + pattlen > self.total_length:
                self.total_length = pattstart + pattlen
                log(f'self.total_length wordt {self.total_length}')
            # determine highest event on track
            for events in self.old_patterns[trackno][-1][2].values():
                last_event = events[-1]
                if pattstart + last_event == self.total_length:
                    self.total_length += 1
                    log(f'self.total_length wordt {self.total_length}')

        test = self.total_length // 32
        if test * 32 != self.total_length:
            self.total_length = (test + 1) * 32
        log(f'{test} {self.total_length}')

        for trackno in self.instruments:
            is_drumtrack = self.old_patterns[trackno][0][1]['drumtrack']
            empty_event = shared.empty[is_drumtrack]
            pattdict = {}

            # determine all notes used on this track and "buffer" the pattern data
            for pattnum, _, pattdata in self.old_patterns[trackno]:
                self.all_notes[trackno].update(pattdata.keys())
                pattdict[pattnum] = pattdata

            # fill al the gaps between patterns beforehand
            for note in self.all_notes[trackno]:
                if is_drumtrack:
                    notestr = shared.get_inst_name(note + shared.note2drums)
                    self.all_note_tracks[trackno][notestr] = self.total_length * [empty_event]
                else:
                    self.all_note_tracks[trackno][note] = self.total_length * [empty_event]

            # fill in the separate events
            for item in self.old_pattern_list[trackno]:
                if len(item) == len(['pattnum', 'pattstart']):
                    continue    # no events found, so no length recorded
                pattnum, pattstart = item[:2]
                for note in self.all_notes[trackno]:
                    if is_drumtrack:
                        notestr = shared.get_inst_name(note + shared.note2drums)
                        if notestr == '?':
                            name = shared.gm_drums[note + shared.note2drums][1]
                            self.unlettered.add(f'no letter yet for `{name}`')
                    else:
                        notestr = shared.get_note_name(note)
                    if note not in pattdict[pattnum]:
                        continue
                    for event in pattdict[pattnum][note]:
                        # log('track {} patt {} start {} note {} event {}'.format(
                        #     trackno, pattnum, pattstart, note, event))
                        ix = notestr if is_drumtrack else note
                        event += pattstart
                        # log('{} {} {}'.format(
                        #     ix, len(self.all_note_tracks[trackno][ix]), event))
                        # if evt == len(self.all_note_tracks[trackno][ix]):
                        #     for ix2 in self.all_note_tracks[trackno]
                        self.all_note_tracks[trackno][ix][event] = notestr

    def print_instrument_full(self, trackno, opts, stream=sys.stdout):
        """output an instrument timeline to a separate file/stream

        trackno indicates the instrument to process
        opts indicates how many events per line and whether to print "empty" lines
        """
        interval, clear_empty = opts
        is_drumtrack = self.patterns[trackno][0][1]['drumtrack']
        empty_event = shared.empty[is_drumtrack]
        if is_drumtrack and self.short_format:
            interval *= 2

        full_length = self.total_length
        empty = shared.sep[is_drumtrack].join(interval * [empty_event])

        if is_drumtrack:
            all_notes = [x for x in shared.standard_printseq if x in self.all_note_tracks[trackno]]
        else:
            all_notes = list(reversed(sorted(self.all_notes[trackno])))
        delim = shared.eventsep(is_drumtrack, self.short_format)
        for eventindex in range(0, full_length, interval):
            if eventindex + interval > full_length:
                empty = delim.join((full_length - eventindex) * [empty_event])
            not_printed = True
            for note in all_notes:
                note_data = self.all_note_tracks[trackno][note]
                if is_drumtrack:
                    line = delim.join(list(note_data[eventindex:eventindex + interval]))
                else:
                    line = delim.join(note_data[eventindex:eventindex + interval])
                if clear_empty and (line == empty or not line):
                    pass
                else:
                    print(line, file=stream)
                    not_printed = False
            if not_printed:
                print(shared.empty[is_drumtrack], file=stream)
            print('', file=stream)

    def print_all_instruments_full(self, instlist, opts, stream=sys.stdout):
        """output all instrument timelines to the "general" file

        instlist indicates the top-to-bottom sequence of instruments
        opts indicates how many events per line and whether to print "empty" lines
        """
        interval, clear_empty = opts
        inst2sam = {y: x for x, y in self.instruments.items()}
        full_length = self.total_length
        for eventindex in range(0, full_length, interval):
            for instname in instlist:
                trackno = inst2sam[instname]
                is_drumtrack = self.patterns[trackno][0][1]['drumtrack']
                empty_event = shared.empty[is_drumtrack]
                if is_drumtrack:
                    print('drums:', file=stream)
                else:
                    print(f'{instname}:', file=stream)
                delim = shared.eventsep(is_drumtrack, self.short_format)
                empty = delim.join(interval * [empty_event])
                if eventindex + interval > full_length:
                    empty = delim.join((full_length - eventindex) * [empty_event])
                if is_drumtrack:
                    all_notes = [x for x in shared.standard_printseq
                                 if x in self.all_note_tracks[trackno]]
                else:
                    all_notes = list(reversed(sorted(self.all_notes[trackno])))
                not_printed = True
                for note in all_notes:
                    line = delim.join(self.all_note_tracks[trackno][note]
                                      [eventindex:eventindex + interval])
                    log(f'note {note} line: {line}')
                    if clear_empty and (line == empty or not line):
                        pass
                    else:
                        print('  ', line, file=stream)
                        not_printed = False
                if not_printed:
                    print('  ', empty_event, file=stream)
                print('', file=stream)
            print('', file=stream)
