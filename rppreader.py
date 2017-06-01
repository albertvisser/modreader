import sys
import collections
import pprint
import shared
import logging


def log(inp):
    logging.info(inp)


class RppFile:

    def __init__(self, filename):
        self.filename = filename
        self.procs = {
            '<TRACK': self.start_track,
            'NAME': self.process_name,
            '<ITEM': self.start_item,
            '<SOURCE': self.start_source,
            'HASDATA': self.start_data,
            'E': self.process_event,
            '>': self.end_stuff}

        self.weirdness = []
        # mapping van naam op trackid(s)
        self.instruments = {}
        # mapping van trackid op volgnr (s) op data
        self.patterns = collections.defaultdict(list)
        self.pattern_list = collections.defaultdict(list)
        self.read()

    def start_track(self, data):
        """identify track, e.g.
          <TRACK '{604D0845-C894-4422-B3F7-3CD51F610A63}'
        """
        ## print("in start_track:", data)
        self.current_track = data[1:-1]     # do I need this if I use instrument numbers?
        self.in_track = True

    def process_name(self, data):
        """read name for current level e.g.
            NAME "Heavymetal - alleen_al"
        """
        ## print("in process_name:", data)
        name = data[1:-1]
        if not self.in_pattern:
            self.instrument_number += 1
            self.instruments[self.instrument_number] = name
        else:
            self.pattern_props = {'name': name}

    def start_item(self, data):
        """start of the block containing the pattern e.g.
          <ITEM
        """
        ## print("in start_item:", data)
        self.in_pattern = True
        self.pattern_no = 0

    def start_source(self, data):
        """check source type e.g.
          <SOURCE MIDI
        """
        ## print("in start_source:", data)
        self.ignore = data != 'MIDI'
        self.in_source = True

    def start_data(self, data):
        """
        start of data block in case of midi, e.g.
        HASDATA 1 384 QN (zie onder)
        """
        if self.ignore: return
        ## print("in process_data:", data)
        self.pattern_props['resolution'] = int(data.split()[1])
        self.pattern_data = collections.defaultdict(list)
        self.timing = 0
        self.track_start = True
        self.pattern_events = collections.defaultdict(list)

    def process_event(self, data):
        """
        note on/off and other midi events, e.g.
        E 0 c0 14 00
        """
        if self.ignore: return
        ## print("in process_event:", data)
        data = data.split()
        tick = int(data[0])
        evtype = data[1][0]
        channel = data[1][1]
        pitch = eval('0x' + data[2])
        ## print(pitch)
        velocity = data[3]
        self.timing += tick
        if self.track_start or evtype == 'c':   # start new pattern
            if self.pattern_events:
                self.patterns[self.instrument_number].append((self.pattern_no,
                                                              self.pattern_props,
                                                              self.pattern_events))
                self.pattern_events = collections.defaultdict(list)
            self.pattern_no += 1
            self.pattern_start = 0 if self.track_start else self.timing
            ## self.pattern_start = self.timing
            start = self.pattern_start // (self.pattern_props['resolution'] // 4)
            self.pattern_list[self.instrument_number].append((self.pattern_no, start))
            if self.track_start: self.track_start = False
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

    def end_stuff(self, data):
        """
        end of block starting with <, same on any level:
         >
        """
        if self.in_source:
            self.patterns[self.instrument_number].append((self.pattern_no,
                                                          self.pattern_props,
                                                          self.pattern_events))
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
            ## count = 0
            for line in _in:
                line = line.strip()
                try:
                    linetype, data = line.split(None, 1)
                except ValueError:
                    linetype = line
                if linetype in self.procs:
                    self.procs[linetype](data)
                ## count += 1
                ## print(count)
                ## if count > 3400:
                    ## break
        ## with open('/tmp/rpp_patterns', 'w') as _o:
            ## pprint.pprint(self.pattern_list, stream=_o)
            ## pprint.pprint(self.patterns, stream=_o)

        new_patterns = collections.defaultdict(list)
        new_pattern_list = collections.defaultdict(list)
        pattstarts = set()
        for track, pattern_start_list in self.pattern_list.items():
            new_patterns_temp = []
            new_pattern_list_temp = {}
            pattix = 0

            for item in pattern_start_list:

                oldpattnum, oldpattstart = item
                # is die pattix niet = oldpattnum - 1?
                oldpattnum2, oldpattprops, oldpattdata = self.patterns[track][pattix]
                if oldpattnum2 > oldpattnum or not oldpattdata:
                    continue    # no data for pattern (just event c0 after event c0)
                elif oldpattnum2 != oldpattnum:     # should never happen
                    with open('/tmp/rpp_patterns', 'w') as _o:
                        pprint.pprint(self.patterns, stream=_o)
                    with open('/tmp/rpp_pattern_list', 'w') as _o:
                        pprint.pprint(self.pattern_list, stream=_o)
                    raise ValueError('mismatch on track {} pattern {} met pattern {}, '
                                     'data dumped to /tmp'.format(track, oldpattnum,
                                                                  oldpattnum2))
                newpattdata = collections.defaultdict(dict)
                for pitch, events in oldpattdata.items():
                    ## newpattnum = 0
                    low_event = 0
                    highest = max(events) + shared.per_line
                    high_event = low_event + shared.per_line

                    pattstarts.add((low_event, high_event))
                    while high_event <= highest:
                        new_events = [x - low_event for x in events
                                      if low_event <= x < high_event]
                        if new_events:
                            newpattstart = oldpattstart + low_event
                            newpattdata[newpattstart][pitch] = new_events
                        low_event = high_event
                        high_event += shared.per_line
                        pattstarts.add((low_event, high_event))
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
                if not data: continue
                try:
                    num_ = previous_patterns.index(data) + 1
                except ValueError:
                    previous_patterns.append(data)
                    newnum += 1
                    num_ = newnum
                    new_patterns[track].append((num_, props, data))
                new_pattern_list[track].append((start, num_))

        self.pattstarts = [(x, y - x) for x, y in sorted(pattstarts)]
        for track, pattdata in new_pattern_list.items():
            tempdict = dict(pattdata)
            new_patt_list = []
            for pattnum, pattstart in enumerate(self.pattstarts):
                try:
                    new_patt_list.append((pattstart[0], tempdict[pattstart[0]]))
                except KeyError:
                    new_patt_list.append((pattstart[0], -1))
            new_pattern_list[track] = new_patt_list

        self.old_patterns = self.patterns
        self.patterns = new_patterns
        self.old_pattern_list = self.pattern_list
        self.pattern_list = new_pattern_list
        self.instruments = {x: y for x, y in self.instruments.items() if x in
                            self.pattern_list}

    def print_general_data(self, full=False, stream=sys.stdout):
        data = shared.build_header("project", self.filename)
        data.extend(shared.build_inst_list([(x, y) for x, y in sorted(
            self.instruments.items())]))
        if not full:
            data.extend(shared.build_patt_header())
            for item, value in self.pattern_list.items():
                patt_list = [y for x, y in value]
                data.extend(shared.build_patt_list(item, self.instruments[item],
                                                   patt_list))
        for line in data:
            print(line.rstrip(), file=stream)

    def print_instrument(self, trackno, stream=sys.stdout):
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
                        unlettered.add('no letter yet for `{}`'.format(
                            shared.gm_drums[key + shared.note2drums][1]))
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
        self.all_note_tracks = collections.defaultdict(
            lambda: collections.defaultdict(list))
        self.unlettered = set()
        self.all_notes = collections.defaultdict(set)
        for trackno in self.instruments:
            is_drumtrack = self.patterns[trackno][0][1]['drumtrack']
            pattdict = {}
            for pattnum, _, pattdata in self.patterns[trackno]:
                pattdict[pattnum] = pattdata
                self.all_notes[trackno].update(pattdata.keys())
            pattlens = dict(self.pattstarts)
            for pattstart, pattnum in self.pattern_list[trackno]:
                pattlen = pattlens[pattstart]
                for note in self.all_notes[trackno]:
                    if is_drumtrack:
                        notestr = shared.get_inst_name(note + shared.note2drums)
                        if notestr == '?':
                            self.unlettered.add('no letter yet for `{}`'.format(
                                shared.gm_drums[note + shared.note2drums][1]))
                    else:
                        notestr = shared.get_note_name(note)
                    to_extend = pattlen * [shared.empty[is_drumtrack]]
                    if pattnum != -1 and note in pattdict[pattnum]:
                        for event in pattdict[pattnum][note]:
                            to_extend[event] = notestr
                    self.all_note_tracks[trackno][note].extend(to_extend)

    def print_instrument_full(self, trackno, opts, stream=sys.stdout):
        interval, clear_empty = opts
        is_drumtrack = self.patterns[trackno][0][1]['drumtrack']
        if is_drumtrack:
            interval *= 2

        full_length = sum([y for x, y in self.pattstarts])
        empty = shared.sep[is_drumtrack].join(interval * [shared.empty[is_drumtrack]])
        all_notes = [x for x in reversed(sorted(self.all_notes[trackno]))]
        for eventindex in range(0, full_length, interval):
            not_printed = True
            for note in all_notes:
                line = shared.sep[is_drumtrack].join(self.all_note_tracks[trackno][note]
                                                     [eventindex:eventindex + interval])
                if clear_empty and line == empty:
                    pass
                else:
                    print(line, file=stream)
                    not_printed = False
            if not_printed:
                print(shared.empty[is_drumtrack], file=stream)
            print('', file=stream)

    def print_all_instruments_full(self, instlist, opts, stream=sys.stdout):
        interval, clear_empty = opts
        inst2sam = {y: x for x, y in self.instruments.items()}
        full_length = sum([y for x, y in self.pattstarts])
        for eventindex in range(0, full_length, interval):
            for instname in instlist:
                trackno = inst2sam[instname]
                is_drumtrack = self.patterns[trackno][0][1]['drumtrack']
                if is_drumtrack:
                    print('drums', file=stream)
                else:
                    print(instname, file=stream)
                delim = shared.sep[is_drumtrack]
                empty = delim.join(interval * [shared.empty[is_drumtrack]])
                all_notes = [x for x in reversed(sorted(self.all_notes[trackno]))]
                not_printed = True
                for note in all_notes:
                    line = delim.join(self.all_note_tracks[trackno][note]
                                      [eventindex:eventindex + interval])
                    if clear_empty and line == empty:
                        pass
                    else:
                        print('  ', line, file=stream)
                        not_printed = False
                if not_printed:
                    print('  ', shared.empty[is_drumtrack], file=stream)
                print('', file=stream)
            print('', file=stream)
