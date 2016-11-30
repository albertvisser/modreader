import sys
import os
import subprocess
import csv
import collections
import pprint
import shared
PER_LINE = 32

class MidiFile:

    def __init__(self, filename):
        self.filename = filename
        self.weirdness = []
        self.read()


    def read(self):
        outfile = os.path.basename(self.filename).replace('.mid', '.csv')
        outfile = os.path.join('/tmp', outfile)
        result = subprocess.run(['midicsv', self.filename, outfile])
        self.instruments = {}
        trackdata = collections.defaultdict(list)
        self.patterns = {}
        self.pattern_lists = collections.defaultdict(list)
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
                    self.instruments[track] = [data[0].strip(' "'), '']
                elif event == 'Note_on_c':
                    if not self.instruments[track][1]:
                        self.instruments[track][1] = int(data[0]) + 1
                    elif int(data[0]) + 1 != self.instruments[track][1]:
                        self.weirdness.append('in-track channel change on track '
                            '{} at time {}'.format(track, tick))
                    trackdata[track].append((tick, int(data[1])))
        duration = self.resolution // 4
        for trackno, track in trackdata.items():
            pattern_data = collections.defaultdict(
                lambda: collections.defaultdict(list))
            for timing, pitch in track:
                notestart = timing // duration
                pattern_no = notestart // 32
                pattern_start = pattern_no * 32
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


    def print_general_data(self, stream=sys.stdout):
        printable = "Details of module {}".format(self.filename)
        data = [printable, "=" * len(printable), '', 'instruments:']
        for x, y in self.instruments.items():
            data.append('        {:>2} {} (chn. {})'.format(x, y[0], y[1]))
        if self.weirdness:
            data.extend([''] + [x for x in self.weirdness])
        data.extend(['', 'Patterns per instrument:'])
        for track, patterns in self.pattern_lists.items():
            data.extend([
                '',
                '    {:>2} {}'.format(track, self.instruments[track][0]),
                ''])
            i = 0
            printable = ['        ']
            for seq, num in patterns:
                while seq > i:
                    printable.append(' .')
                    i += 1
                    if i % 8 == 0:
                        data.append(' '.join(printable))
                        printable = ['        ']
                if seq == i:
                    printable.append('{:>2}'.format(num))
                    i += 1
                    if i % 8 == 0:
                        data.append(' '.join(printable))
                        printable = ['        ']
            data.append(' '.join(printable))
        for item in data:
            print(item, file=stream)


    def print_instrument(self, trackno, stream=sys.stdout):
        is_drumtrack = self.instruments[trackno][1] == 10
        empty = '.' if is_drumtrack else '...'
        for number, pattern in self.patterns[trackno]:
            print('pattern {:>2}:'.format(number), file=stream)
            unlettered = set()
            printables = []
            for pitch in pattern:
                if not pattern[pitch]:
                    continue
                if is_drumtrack:
                    notestr = shared.get_inst_name(pitch - 35)
                    if notestr == '?':
                        unlettered.add('no letter yet for `{}`'.format(
                            shared.gm_drums[pitch - 35][1]))
                    else:
                        key = shared.standard_printseq.index(notestr)
                else:
                    notestr = shared.get_note_name(pitch)
                    key = pitch
                printstr = ['          ']
                index = 0
                for event in pattern[pitch]:
                    while index < event:
                        printstr.append(empty)
                        index += 1
                    printstr.append(notestr)
                    index += 1
                while index < PER_LINE:
                    printstr.append(empty)
                    index += 1
                sep = '' if is_drumtrack else ' '
                printables.append((key, sep.join(printstr)))
            printables.sort()
            if not is_drumtrack: printables.reverse()
            for key, line in printables:
                print(line, file=stream)
            print('', file=stream)
        for x in unlettered: print(x, file=stream)

def main():
    filename = '/home/albert/magiokis/data/mid/alleen_al.mid'
    test = MidiFile(filename)
    ## with open('/tmp/alleen_al_instruments', 'w') as _out:
        ## test.print_general_data(_out)
    ## for trackno, data in test.instruments.items():
        ## with open('/tmp/alleen_al_{}'.format(data[0]), 'w') as _out:
            ## test.print_instrument(trackno, _out)

if __name__ == "__main__":
    main()
