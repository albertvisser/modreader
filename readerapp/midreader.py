"""ModReaderGui - data processing for MIDI file format
"""
import sys
## import os
import pathlib
import subprocess
import csv
import collections
import logging
from readerapp import shared


def log(inp):
    "local definition to allow for picking up module name in message format"
    logging.info(inp)


class MidiFile:
    """Main processing class
    """
    def __init__(self, filename):
        self.filename = filename
        self.weirdness = []
        self.instruments = {}
        self.patterns = {}
        self.pattern_lists = collections.defaultdict(list)
        self.short_format = None
        self.show_continual = None
        self.read()

    def read(self):
        """convert the midi file into a csv and read and interpret that to
        build the internal data collection
        """
        outfile = pathlib.Path(self.filename).with_suffix('.csv').name
        outfile = pathlib.Path('/tmp') / outfile
        subprocess.run(['midicsv', self.filename, str(outfile)], check=False)
        trackdata = collections.defaultdict(set)
        with outfile.open() as _in:
            csvdata = csv.reader(_in)
            for line in csvdata:
                track, tick, event, *data = line
                track = int(track) - 1
                tick = int(tick)
                event = event.strip()
                if track == -1 and event == 'Header':
                    self.resolution = int(data[2])
                elif event == 'Title_t':
                    test = data[0].strip(' "')
                    if test:
                        self.instruments[track] = [test, '']
                elif event == 'Note_on_c':
                    if not self.instruments[track][1]:
                        self.instruments[track][1] = int(data[0]) + 1
                    elif int(data[0]) + 1 != self.instruments[track][1]:
                        self.weirdness.append('in-track channel change on track {track}'
                                              ' at time {tick}')
                    if int(data[2]) != 0:   # don't count velocity set to 0
                        trackdata[track].add((tick, int(data[1])))
        duration = self.resolution // 4
        for trackno, track in trackdata.items():
            pattern_data = collections.defaultdict(
                lambda: collections.defaultdict(list))
            for timing, pitch in sorted(track):
                notestart = timing // duration
                pattern_no = notestart // shared.tick_factor
                pattern_start = pattern_no * shared.tick_factor
                pattern_data[pattern_no][pitch].append(notestart - pattern_start)
            patterns = []
            pattern_list = []
            for pattern_no, pattern in pattern_data.items():
                try:
                    pattern_id = patterns.index(pattern)
                except ValueError:
                    pattern_id = len(patterns)
                    patterns.append(pattern)
                pattern_list.append((pattern_no, pattern_id))
            # self.patterns[trackno] = [(x, y) for x, y in enumerate(patterns)]
            self.patterns[trackno] = list(enumerate(patterns))
            self.pattern_lists[trackno] = pattern_list
        to_pop = []
        for key, val in self.instruments.items():
            if not val[1]:
                to_pop.append(key)
        for key in to_pop:
            self.instruments.pop(key)

    def process(self, gui):
        """Create output for MIDI

        this is assuming I only have midi files that use a separate drum track
        (instead of several tracks with one drum instrument each)
        """
        options = (gui.max_events.value(), gui.check_nonempty.isChecked())
        with open(gui.get_general_filename(), "w") as _out:
            self.print_general_data(full=self.show_continual, stream=_out)
        self.prepare_print_instruments()
        # kijken of er dubbele namen zijn
        test, dubbel = set(), set()
        for trackno, data in self.instruments.items():
            if data[0] in test:
                dubbel.add('-'.join((data[0], str(trackno))))
            else:
                test.add(data[0])
        if gui.check_allinone.isChecked():
            inst_list = gui.list_items(gui.list_samples)
            inst_list += [x.rsplit(' ', 1)[0] for x in gui.list_items(gui.mark_samples)]
            with open(gui.get_general_filename(), 'a') as _out:
                self.print_all_instruments_full(inst_list, options, _out)
            return []
        for trackno, name in self.instruments.items():
            with open(gui.get_instrument_filename(name), 'w') as _out:
                if gui.check_full.isChecked():
                    self.print_instrument_full(trackno, options, _out)
                else:
                    self.print_instrument(trackno, _out)
        return []

    def print_general_data(self, full=False, stream=sys.stdout):
        """create the "overview" file (sample and pattern lists)
        """
        data = shared.build_header("module", self.filename)
        data.extend(shared.build_inst_list([(x, f'{y[0]} (chn. {y[1]})')
                                            for x, y in self.instruments.items()]))
        if self.weirdness:
            data.extend([''] + list(self.weirdness))
        if not full:
            data.extend(shared.build_patt_header())
            for track, patterns in self.pattern_lists.items():
                patt_list = []
                i = 0
                for seq, num in patterns:
                    while seq > i:
                        patt_list.append(-1)
                        i += 1
                    if seq == i:
                        patt_list.append(num + 1)
                        i += 1
                data.extend(shared.build_patt_list(track, self.instruments[track][0],
                                                   patt_list))

        for item in data:
            print(item.rstrip(), file=stream)

    def print_instrument(self, trackno, stream=sys.stdout):
        """print the events for an instrument as a piano roll

        trackno is the number of the midi track / sample to print data for
        stream is a file-like object to write the output to
        """
        is_drumtrack = self.instruments[trackno][1] == shared.drum_channel
        for number, pattern in self.patterns[trackno]:
            print(shared.patt_start.format(number + 1), file=stream)
            unlettered = set()
            printables = []
            for pitch in pattern:
                if not pattern[pitch]:
                    continue
                if is_drumtrack:
                    notestr = shared.get_inst_name(pitch + shared.note2drums)
                    if notestr == '?':
                        unlettered.add(f'no letter yet for `{shared.gm_drums[pitch - 35][1]}`')
                    else:
                        try:
                            key = shared.standard_printseq.index(notestr)
                        except ValueError:
                            unlettered.add(f'{notestr} not in standard printseq'
                                           f' {shared.standard_printseq}')
                else:
                    notestr = shared.get_note_name(pitch)
                    key = pitch
                printstr = [shared.line_start]
                index = 0
                for event in pattern[pitch]:
                    while index < event:
                        printstr.append(shared.empty[is_drumtrack])
                        index += 1
                    printstr.append(notestr)
                    index += 1
                while index < shared.per_line:
                    printstr.append(shared.empty[is_drumtrack])
                    index += 1
                if not is_drumtrack:
                    printstr[0] = printstr[0][:-1]
                printables.append((key, shared.sep[is_drumtrack].join(printstr)))
            printables.sort()
            if not is_drumtrack:
                printables.reverse()
            for key, line in printables:
                print(line, file=stream)
            print('', file=stream)
        for x in unlettered:
            print(x, file=stream)
        return unlettered

    def prepare_print_instruments(self):
        """build complete timeline for (drum & regular) instrument events
        """
        self.all_track_notes = collections.defaultdict(
            lambda: collections.defaultdict(list))
        self.all_notevals = collections.defaultdict(set)
        self.total_length = 0
        for trackno, trackdata in self.instruments.items():
            is_drumtrack = trackdata[1] == shared.drum_channel

            patterns = dict(self.patterns[trackno])
            for _, pattdict in self.patterns[trackno]:
                self.all_notevals[trackno].update(list(pattdict.keys()))
            pattlist = []
            seq = 0
            for pattseq, pattnum in sorted(self.pattern_lists[trackno]):
                while pattseq > seq:
                    pattlist.append((seq, -1))
                    seq += 1
                pattlist.append((pattseq, pattnum))
                seq += 1
            for pattseq, pattnum in pattlist:
                empty_event = shared.empty[is_drumtrack]
                if pattnum == -1:
                    for note in self.all_notevals[trackno]:
                        self.all_track_notes[trackno][note].extend([empty_event] * shared.per_line)
                    continue
                for note in self.all_notevals[trackno]:
                    if note in patterns[pattnum]:
                        events = patterns[pattnum][note]
                        for tick in range(shared.per_line):
                            if tick in events:
                                if is_drumtrack:
                                    to_append = shared.get_inst_name(note + shared.note2drums)
                                else:
                                    to_append = shared.get_note_name(note)
                            else:
                                to_append = empty_event
                            self.all_track_notes[trackno][note].append(to_append)
                    else:
                        self.all_track_notes[trackno][note].extend([empty_event] * shared.per_line)
            test = len(self.all_track_notes[trackno][note])
            ## print(test)
            self.total_length = max(test, self.total_length)

    def print_instrument_full(self, trackno, opts, stream=sys.stdout):
        """output an instrument timeline to a separate file/stream

        trackno indicates the instrument to process
        opts indicates how many events per line and whether to print "empty" lines
        """
        interval, clear_empty = opts
        is_drumtrack = self.instruments[trackno][1] == shared.drum_channel
        all_track_notes = self.all_track_notes[trackno]
        ## all_notevals = self.all_notevals[trackno]

        empty_event = shared.empty[is_drumtrack]
        if is_drumtrack:
            if self.short_format:
                interval *= 2
            notes_to_show = list(
                sorted(self.all_notevals[trackno],
                       key=lambda x: shared.standard_printseq.index(shared.get_inst_name(
                           x + shared.note2drums))))
        else:
            notes_to_show = list(reversed(sorted(self.all_notevals[trackno])))

        sep = shared.eventsep(is_drumtrack, self.short_format)
        empty_line = sep.join(interval * [empty_event])
        for eventindex in range(0, self.total_length, interval):
            if eventindex + interval > self.total_length:
                empty_line = sep.join((self.total_length - eventindex) * [empty_event])
            not_printed = True
            for note in notes_to_show:
                notes = all_track_notes[note]
                line = sep.join(notes[eventindex:eventindex + interval])
                if clear_empty and (line == empty_line or not line):
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
        inst2sam = {y[0]: (x, y) for x, y in self.instruments.items()}

        for eventindex in range(0, self.total_length, interval):

            for instname in instlist:
                trackno, trackdata = inst2sam[instname]
                is_drumtrack = trackdata[1] == shared.drum_channel
                sep = shared.eventsep(is_drumtrack, self.short_format)
                empty_event = shared.empty[is_drumtrack]
                empty_line = sep.join(interval * [empty_event])
                if eventindex + interval > self.total_length:
                    empty_line = sep.join((self.total_length - eventindex) * [empty_event])
                all_track_notes = self.all_track_notes[trackno]
                all_notevals = self.all_notevals[trackno]

                if is_drumtrack:
                    notes_to_show = list(
                        sorted(all_notevals, key=lambda x: shared.standard_printseq.index(
                            shared.get_inst_name(x + shared.note2drums))))
                    print('drums:', file=stream)
                else:
                    notes_to_show = list(reversed(sorted(all_notevals)))
                    print(f'{instname}:', file=stream)

                not_printed = True
                for note in notes_to_show:
                    notes = all_track_notes[note]
                    line = sep.join(notes[eventindex:eventindex + interval])
                    if clear_empty and (line == empty_line or not line):
                        pass
                    else:
                        print('  ', line, file=stream)
                        not_printed = False
                if not_printed:
                    print('  ', empty_event, file=stream)
                print('', file=stream)
            print('', file=stream)
