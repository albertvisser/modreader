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
        for name in self.tracknames:
            for tracknum, track in enumerate(tracks):
                if track.get('name') != name:
                    continue
                data = self.read_track(tracknum, track)
                trackdata[name].extend(data)
        for name, data in trackdata.items():
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
        self.patternlists = patternlists
        self.patterndata = patterndata

        # beat/bassline tracks
        # getting the instruments involved
        bbtracks = root.findall('.//bbtrack/trackcontainer/track')
        self.bbtracknames = [x.get("name") for x in bbtracks]
        bbtrackdata = collections.defaultdict(list)
        for name in self.bbtracknames:
            for tracknum, track in enumerate(bbtracks):
                if track.get('name') != name:
                    continue
                data = self.read_track(tracknum, track, bbtrack=True)
                bbtrackdata[name].append(data)
        drumtracks = collections.defaultdict(list)
        for name, data in bbtrackdata.items():
            for num, track, len in data[0]: # enumerate(data[0]):
                ## trackdata = track[1]
                ## if trackdata:
                if track:
                    drumtracks[num].append((name, track, len)) # trackdata))
        self.bbpatterndata = drumtracks
        # getting the events involved (is dividing by 384 ok?)
        tracks = root.findall('./song/trackcontainer/track[@type="1"]')
        bbeventslist = []
        for tracknum, track in enumerate(tracks):
            for bbtco in track.findall('bbtco'):
                pos = int(bbtco.get('pos')) // shared.time_unit
                bbeventslist.append((pos, tracknum))
        bbeventslist.sort()
        bbevents = []
        for pos, pattern in bbeventslist:
            bbevents.append(pattern)
        self.bbpatternlist = bbevents

        with open('/tmp/{}-mmpdata'.format(project_name), 'w') as _out:
            print("instruments:", self.tracknames, file=_out)
            print("\npattern list:", self.patternlists, file=_out)
            print("\npatterns:", self.patterndata, file=_out)
            print("\nbb instruments:", self.bbtracknames, file=_out)
            print("\nbb pattern list:", self.bbpatterndata, file=_out)
            print("\nbb patterns:", self.bbpatternlist, file=_out)


    def read_track(self, tracknum, track, bbtrack=False):
        patterns = []
        pattlist = track.findall('pattern')
        for pattnum, patt in enumerate(pattlist):
            pattname = patt.get('name')
            pattstart = int(patt.get('pos')) // (shared.time_unit // 2 )
            pattlen = int(patt.get('len')) // shared.timing_unit
            notes = []
            notelist = patt.findall('note')
            max = shared.per_line
            for note in notelist:
                when = int(note.get('pos')) // shared.timing_unit
                if when >= max:
                    patterns.append((pattstart, notes, shared.per_line))
                    pattlen -= shared.per_line
                    pattstart += 1
                    max += shared.per_line
                    notes = []
                notes.append((int(note.get('key')), when - max + shared.per_line))
            patterns.append((pattstart, notes, pattlen))
        return patterns

    def print_general_data(self, sample_list=None, _out=sys.stdout):
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
            data.extend(shared.build_inst_list(bb_inst, "Instruments "
                "in Beat/Bassline:"))
            data.extend(shared.build_patt_header("Patterns in Beat/Bassline:"))
            data.extend(shared.build_patt_list('', '', self.bbpatternlist))

        data.extend(shared.build_inst_list([(i + 1, x) for i, x in enumerate(
            self.tracknames)]))
        data.extend(shared.build_patt_header())
        for i, x in enumerate(self.tracknames):
            data.extend(shared.build_patt_list(i + 1, x, self.patternlists[x]))

        for line in data:
            print(line, file=_out)



# v.w.b drums voorzie ik drie situaties:
#- er worden beat/bassline tracks gebruikt
#    hier moet ik nog in voorzien dat er niet alleen drums maar ook bas oid meedoet
#    theoretisch, want zelf gebruik ik dat eigenlijk niet?
    def print_beat_bassline(self, sample_list, printseq, _out=sys.stdout):
        with open('/tmp/mmp_bbpatterndata', 'w') as _o:
            pprint.pprint(self.bbpatterndata, stream=_o)
        for pattnum, pattern in self.bbpatterndata.items():
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
        for ix, pattdata in enumerate(self.patterndata[trackname]):
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

#- er worden aparte instrumenten gebruikt (to be implemented)
    def print_drums(self, sample_list, printseq, _out=sys.stdout):
        pass

    def print_instrument(self, trackname, _out=sys.stdout):
        for ix, pattdata in enumerate(self.patterndata[trackname]):
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
