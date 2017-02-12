import sys
import os
import subprocess
import csv
import collections
import pprint
import shared

class MidiFile:

    def __init__(self, filename):
        self.filename = filename
        self.weirdness = []
        self.instruments = {}
        self.patterns = {}
        self.pattern_lists = collections.defaultdict(list)
        self.read()


    def read(self):
        outfile = os.path.basename(self.filename).replace('.mid', '.csv')
        outfile = os.path.join('/tmp', outfile)
        result = subprocess.run(['midicsv', self.filename, outfile])
        trackdata = collections.defaultdict(set)
        with open(outfile) as _in:
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
                        self.weirdness.append('in-track channel change on track '
                            '{} at time {}'.format(track, tick))
                    if int(data[2]) != 0: # don't count velocity set to 0
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
            self.patterns[trackno] = [(x, y) for x, y in enumerate(patterns)]
            self.pattern_lists[trackno] = pattern_list
        to_pop = []
        for key, val in self.instruments.items():
            if not val[1]: to_pop.append(key)
        for key in to_pop:
            self.instruments.pop(key)
        ## with open('/tmp/mid-patterns', 'w') as _o:
            ## pprint.pprint(self.instruments, stream=_o)
            ## pprint.pprint(self.patterns, stream=_o)


    def print_general_data(self, stream=sys.stdout):
        data = shared.build_header("module", self.filename)
        data.extend(shared.build_inst_list([(x, '{} (chn. {})'.format(y[0], y[1]))
            for x, y in self.instruments.items()]))
        if self.weirdness:
            data.extend([''] + [x for x in self.weirdness])
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
        is_drumtrack = self.instruments[trackno][1] == shared.drum_channel
        empty = shared.empty_drums if is_drumtrack else shared.empty_note
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
                        unlettered.add('no letter yet for `{}`'.format(
                            shared.gm_drums[pitch - 35][1]))
                    else:
                        try:
                            key = shared.standard_printseq.index(notestr)
                        except ValueError:
                            unlettered.add('{} not in standard printseq {}'.format(
                                notestr, shared.standard_printseq))
                else:
                    notestr = shared.get_note_name(pitch)
                    key = pitch
                printstr = [shared.line_start]
                index = 0
                for event in pattern[pitch]:
                    while index < event:
                        printstr.append(empty)
                        index += 1
                    printstr.append(notestr)
                    index += 1
                while index < shared.per_line:
                    printstr.append(empty)
                    index += 1
                if is_drumtrack:
                    sep = ''
                else:
                    sep = ' '
                    printstr[0] = printstr[0][:-1]
                printables.append((key, sep.join(printstr)))
            printables.sort()
            if not is_drumtrack: printables.reverse()
            for key, line in printables:
                print(line, file=stream)
            print('', file=stream)
        for x in unlettered: print(x, file=stream)
        return unlettered


