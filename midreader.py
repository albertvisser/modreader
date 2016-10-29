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
        self.read()


    def read(self):
        outfile = os.path.basename(self.filename).replace('.mid', '.csv')
        outfile = os.path.join('/tmp', outfile)
        result = subprocess.run(['midicsv', self.filename, outfile])
        self.instruments = {} # self.read_instruments()
        self.tracks = collections.defaultdict(list)
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
                    self.tracks[track].append((tick, int(data[1])))
        # moet ik hier nog een soort "pattern map" afleiden die aangeeft welke instrumenten
        # wanneer gespeeld worden?


    def print_general_data(self, stream=sys.stdout):
        printable = "Details of module {}".format(self.filename)
        data = [printable, "=" * len(printable), '']
        for x, y in self.instruments.items():
            print('{:>2} {} (chn. {})'.format(x, y[0], y[1]), file=stream)
        if self.weirdness: print('', file=stream)
        for item in self.weirdness:
            print(item, file=stream)


    # self.data.resolution is van belang voor het weergeven op de tijdsbalk
    # ik denk dat het aangeeft hoe lang een kwart noot duurt.
    # dus daardoor delen geeft de eenheden op de tijdsbalk.
    # als ik hierbij breuken krijg zijn er achtste noten of kleine gebruikt?
    # meestal werk ik minstens in een resolutie van achtsten dus de helft lijkt me een goed
    # uitgangspunt
    # voor een drumtrack is zestienden misschien toch beter
    def print_instrument(self, trackno, stream=sys.stdout):
        ## per_line = 32
        if self.instruments[trackno][1] == 10:
            is_drumtrack, empty, factor, per_line = True, '.', 4, 64
        else:
            is_drumtrack, empty, factor, per_line = False, '...', 4, 32
        duration = self.resolution // factor
        lines = collections.defaultdict(list)
        for moment, pitch in self.tracks[trackno]:
            timing = moment // duration
            lines[pitch].append(timing)
        unlettered = set()
        for moment in range(0, timing, per_line):
            for pitch in reversed(sorted(lines)):
                if not lines[pitch]:
                    continue
                if is_drumtrack:
                    notestr = shared.get_inst_name(pitch - 35)
                    if notestr == '?':
                        unlettered.add('no letter yet for `{}`'.format(
                            shared.gm_drums[pitch - 35][1]))
                else:
                    notestr = shared.get_note_name(pitch)
                test = lines[pitch][0]
                if test > moment + per_line - 1:
                    continue
                printstr = []
                for index in range(moment, moment + per_line):
                    if lines[pitch] and lines[pitch][0] == index:
                        printstr.append(notestr)
                        lines[pitch].pop(0)
                    else:
                        printstr.append(empty)
                sep = '' if is_drumtrack else ' '
                print(sep.join(printstr), file=stream)
            print('', file=stream)
        for x in unlettered: print(x, file=stream)

def main():
    filename = '/home/albert/magiokis/data/mid/alleen_al.mid'
    test = MidiFile(filename)
    with open('/tmp/alleen_al_instruments', 'w') as _out:
        test.print_general_data(_out)
    for trackno, data in test.instruments.items():
        with open('/tmp/alleen_al_{}'.format(data[0]), 'w') as _out:
            test.print_instrument(trackno, _out)

if __name__ == "__main__":
    main()