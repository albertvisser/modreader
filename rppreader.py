import sys
import collections
import pprint
import shared

"""
Dit is een of ander xml-achtig formaat dat ook een soort van elementen kent
deze beginnen met <elementnaam en eindigen met > op een volgende regel
Er wordt wel ingesprogen dus beginnen en eindes zijn makkelijk te matchen
De voor mij interessantste stukken zijn:
<REAPER_PROJECT 0.1
  ...
  <TRACK '{604D0845-C894-4422-B3F7-3CD51F610A63}'
    NAME "Heavymetal - alleen_al"
    ...
    <ITEM
      ...
      NAME "Heavymetal - alleen_al.MID"
      ...
      <SOURCE MIDI
        HASDATA 1 384 QN (zie onder)
        E 0 c0 14 00
        ...
      >
    >
  >
>


    midi (gedumpt met python-midi)                           reaper
                                                            <SOURCE MIDI
   midi.Pattern(format=1, resolution=384,                     HASDATA 1 384 QN
                                                                E 0 c0 14 00
   midi.ControlChangeEvent(tick=0, channel=0, data=[32, 0]),    E 0 b0 20 00
   midi.ControlChangeEvent(tick=0, channel=0, data=[0, 11]),    E 0 b0 00 0b
   midi.ProgramChangeEvent(tick=0, channel=0, data=[20]),
   midi.NoteOnEvent(tick=0, channel=0, data=[64, 109]),         E 0 90 40 6d
   midi.NoteOffEvent(tick=244, channel=0, data=[64, 109]),      E 244 80 40 6d
   midi.NoteOnEvent(tick=332, channel=0, data=[64, 109]),       E 332 90 40 6d
   midi.NoteOffEvent(tick=244, channel=0, data=[64, 109]),      E 244 80 40 6d
   midi.NoteOnEvent(tick=140, channel=0, data=[64, 109]),       E 140 90 40 6d
   midi.NoteOffEvent(tick=192, channel=0, data=[64, 109]),      E 192 80 40 6d
   midi.NoteOnEvent(tick=0, channel=0, data=[66, 109]),         E 0 90 42 6d
   midi.NoteOffEvent(tick=216, channel=0, data=[66, 109]),      E 216 80 42 6d
   midi.NoteOnEvent(tick=168, channel=0, data=[67, 109]),       E 168 90 43 6d
   midi.NoteOffEvent(tick=204, channel=0, data=[67, 109]),      E 204 80 43 6d
   midi.NoteOnEvent(tick=372, channel=0, data=[66, 109]),       E 372 90 42 6d
   midi.NoteOffEvent(tick=216, channel=0, data=[66, 109]),      E 216 80 42 6d
   midi.NoteOnEvent(tick=360, channel=0, data=[64, 109]),       E 360 90 40 6d
   midi.NoteOffEvent(tick=244, channel=0, data=[64, 109]),      E 244 80 40 6d
   midi.NoteOnEvent(tick=140, channel=0, data=[62, 109]),       E 140 90 3e 6d
   midi.NoteOffEvent(tick=274, channel=0, data=[62, 109]),      E 274 80 3e 6d
   midi.NoteOnEvent(tick=302, channel=0, data=[62, 109]),       E 302 90 3e 6d
   midi.NoteOffEvent(tick=274, channel=0, data=[62, 109]),      E 274 80 3e 6d
   midi.NoteOnEvent(tick=110, channel=0, data=[62, 109]),       E 110 90 3e 6d
   midi.NoteOffEvent(tick=192, channel=0, data=[62, 109]),      E 192 80 3e 6d
   midi.NoteOnEvent(tick=0, channel=0, data=[64, 109]),         E 0 90 40 6d
   midi.NoteOffEvent(tick=244, channel=0, data=[64, 109]),      E 244 80 40 6d
   midi.NoteOnEvent(tick=140, channel=0, data=[62, 109]),       E 140 90 3e 6d
   midi.NoteOffEvent(tick=274, channel=0, data=[62, 109]),      E 274 80 3e 6d

vreemd genoeg is in de reaper data de "tick value" decimaal en de rest in hex...

bij de drums zie ik dit:
   midi.ControlChangeEvent(tick=0, channel=9, data=[32, 0]),    E 0 c9 06 00
   midi.ControlChangeEvent(tick=0, channel=9, data=[0, 11]),    E 0 b9 20 00
   midi.ProgramChangeEvent(tick=0, channel=9, data=[6]),        E 0 b9 00 0b
   midi.NoteOnEvent(tick=0, channel=9, data=[42, 121]),         E 0 99 2a 79
   midi.NoteOnEvent(tick=0, channel=9, data=[35, 112]),         E 0 99 23 70
   midi.NoteOffEvent(tick=78, channel=9, data=[42, 121]),       E 78 89 2a 79
   midi.NoteOffEvent(tick=82, channel=9, data=[35, 112]),       E 82 89 23 70
het lijkt erop dat die derde waarde niet alleen het type event aangeeft maar ook
het channel number
"""

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
            '>': self.end_stuff,
            }
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
        self.current_track = data[1:-1] # do I need this if I use instrument numbers?
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
        if self.track_start or evtype == 'c': # start new pattern
            if self.pattern_events:
                self.patterns[self.instrument_number].append((self.pattern_no,
                    self.pattern_props, self.pattern_events))
                self.pattern_events = collections.defaultdict(list)
            self.pattern_no += 1
            self.pattern_start = 0 if self.track_start else self.timing
            ## self.pattern_start = self.timing
            self.pattern_list[self.instrument_number].append((self.pattern_no,
                self.pattern_start // (self.pattern_props['resolution'] // 4)))
            if self.track_start: self.track_start = False
        if evtype != '9': # we're only interested in `note on`
            return
        if velocity == '00': # set volume to zero == note off
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
                self.pattern_props, self.pattern_events))
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
        with open('/tmp/rpp_patterns', 'w') as _o:
            pprint.pprint(self.pattern_list, stream=_o)
            pprint.pprint(self.patterns, stream=_o)

        new_patterns = collections.defaultdict(list)
        new_pattern_list = collections.defaultdict(list)
        for track, pattern_start_list in self.pattern_list.items():
            new_patterns_temp = []
            new_pattern_list_temp = []
            newpattnum = 0
            pattix = 0
            for ix, item in enumerate(pattern_start_list):
                oldpattnum, oldpattstart = item
                oldpattnum2, oldpattprops, oldpattdata = self.patterns[track][pattix]
                if oldpattnum2 > oldpattnum or not oldpattdata:
                    continue # no data for pattern (just event c0 after event c0)
                elif oldpattnum2 != oldpattnum: # should never happen
                ## if oldpattnum2 != oldpattnum: # should never happen
                    with open('/tmp/rpp_patterns', 'w') as _o:
                        pprint.pprint(self.patterns, stream=_o)
                    with open('/tmp/rpp_pattern_list', 'w') as _o:
                        pprint.pprint(self.pattern_list, stream=_o)
                    raise ValueError('mismatch on track {} pattern {} met pattern {}, data '
                        'dumped to /tmp'.format(track, oldpattnum, oldpattnum2))
                pattix += 1
                high_event = 0
                data_started = False
                while True:
                    newpattdata = {}
                    low_event = high_event
                    newpattstart = oldpattstart + low_event
                    high_event += shared.per_line
                    for instval, instdata in oldpattdata.items():
                        print(instval, instdata, file=_o)
                        print(low_event, high_event, end=' ', file=_o)
                        new_instdata = [x - low_event for x in instdata
                            if low_event <= x < high_event]
                        print(new_instdata, file=_o)
                        if new_instdata:
                            newpattdata[instval] = new_instdata
                    if newpattdata:
                        data_started = True
                    elif data_started:
                        break
                    newpattnum += 1
                    new_pattern_list_temp.append((newpattnum, newpattstart))
                    new_patterns_temp.append((newpattnum, oldpattprops,
                        newpattdata))

            previous_patterns = []
            newnum = 0
            for ix, item in enumerate(new_patterns_temp):
                patt, start = new_pattern_list_temp[ix]
                num, props, data = item
                if not data: continue
                try:
                    num_ = previous_patterns.index(data) + 1
                except ValueError:
                    previous_patterns.append(data)
                    newnum += 1
                    num_ = newnum
                    new_patterns[track].append((num_, props, data))
                new_pattern_list[track].append((num_, start))
        self.patterns = new_patterns
        self.pattern_list = new_pattern_list
        self.instruments = {x: y for x, y in self.instruments.items() if x in
            self.pattern_list}


    def print_general_data(self, stream=sys.stdout):
        data = shared.build_header("project", self.filename)
        data.extend(shared.build_inst_list([(x, y) for x, y in sorted(
            self.instruments.items())]))
        data.extend(shared.build_patt_header())
        for item, value in self.pattern_list.items():
            counter = 1
            patt_list = []
            for pattnum, pattstart in value:
                test = pattstart // 32
                while test > counter:
                    patt_list.append(-1)
                    counter += 1
                patt_list.append(pattnum)
                counter += 1
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
                    empty, delim = shared.empty_drums, ''
                    if notestr == '?':
                        unlettered.add('no letter yet for `{}`'.format(
                            shared.gm_drums[key + shared.note2drums][1]))
                    else:
                        key = shared.standard_printseq.index(notestr)
                else:
                    notestr = shared.get_note_name(key) #  - 12)
                    empty, delim = shared.empty_note, ' '
                factor = shared.tick_factor
                for i in range(factor * (note_events[-1] // factor + 1)):
                    if i in note_events:
                        events.append(notestr)
                    else:
                        events.append(empty)
                    if (i + 1) % factor == 0:
                        seqnum += 1
                        if events != factor * [empty]:
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


