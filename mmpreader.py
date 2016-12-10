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
        with open('/tmp/trackdata', 'w') as _out:
            print(trackdata, file=_out)
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
        ## with open('/tmp/patterndata', 'w') as _out:
            ## for name in patterndata:
                ## print(patternlists[name], file=_out)
                ## print(patterndata[name], file=_out)
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
        ## with open('/tmp/bbtracks', 'w') as _out:
            ## pprint.pprint(bbtrackdata, stream=_out)
        drumtracks = collections.defaultdict(list)
        for name, data in bbtrackdata.items():
            for num, track, len in enumerate(data[0]):
                trackdata = track[1]
                if trackdata:
                    drumtracks[num].append((name, trackdata))
        self.bbpatterndata = drumtracks
        ## with open('/tmp/bbtracks', 'w') as _out:
            ## pprint.pprint(drumtracks, stream=_out)
        # getting the events involved (is dividing by 384 ok?)
        tracks = root.findall('./song/trackcontainer/track[@type="1"]')
        bbeventslist = []
        for tracknum, track in enumerate(tracks):
            for bbtco in track.findall('bbtco'):
                pos = int(bbtco.get('pos')) // 384
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
            pattstart = int(patt.get('pos')) // 384
            pattlen = int(patt.get('len')) // 12
            ## if bbtrack:
                ## unit = int(patt.get('len')) // 32        # so we get 16th notes?
            ## else:
                ## unit = int(patt.get('len')) // 64       # so we get 16th notes?
            notes = []
            notelist = patt.findall('note')
            max = 32
            for note in notelist:
                when = int(note.get('pos')) // 12
                if when >= max:
                    patterns.append((pattstart, notes, 32))
                    pattlen -= 32
                    pattstart += 1
                    max += 32
                    notes = []
                notes.append((int(note.get('key')), when - max + 32)) # - (pattstart * 32)))
            patterns.append((pattstart, notes, pattlen))
        return patterns

    def print_general_data(self, sample_list=None, _out=sys.stdout):
        if sample_list is None: sample_list = []
        printable = "Details of project {}".format(self.filename)
        data = [printable, "=" * len(printable), '']
        if self.bbtracknames:
            data.extend(["Instruments in Beat/Bassline:", ''])
            for i, x in enumerate(self.bbtracknames):
                y = ''
                for ins, lett in sample_list:
                    if ins == x:
                        y = lett
                        break
                if y: y = y.join(('(', ')'))
                data.append("    {}: {} {}".format(i + 1, x, y))
            data.extend(["", "Patterns in Beat/Bassline:", ''])
            printable = []
            for i, x in enumerate(self.bbpatternlist):
                printable.append('{:>2}'.format(x + 1))
                if (i + 1) % 8 == 0:
                    data.append("    {}".format(' '.join(printable)))
                    printable = []
            if printable:
                    data.append("    {}".format(' '.join(printable)))
            data.extend(['', ''])

        data.extend(["Instruments:", ''])
        for i, x in enumerate(self.tracknames):
            data.append("    {}: {}".format(i + 1, x))
        data.extend(["", "Patterns per instrument:"])
        for i, x in enumerate(self.tracknames):
            ## data.extend([ '', "    {}: {}".format(i + 1, x), ''])
            z = ''
            for name, letter in sample_list:
                if name == x:
                    z = letter.join(('(', ')'))
            data.extend([ '', "    {}: {} {}".format(i + 1, x, z), ''])
            printable = []
            for j, y in enumerate(self.patternlists[x]):
                ## z = ''
                ## for name, letter in sample_list:
                    ## if name == y:
                        ## z = letter.join('(', ')')
                ## printable.append('{:>2} {}'.format(y, z))
                printable.append('{:>2}'.format(y))
                if (j + 1) % 8 == 0:
                    data.append("    {}".format(' '.join(printable)))
                    printable = []
            if printable:
                    data.append("    {}".format(' '.join(printable)))

        for line in data:
            print(line, file=_out)



# v.w.b drums voorzie ik drie situaties:
#- er worden beat/bassline tracks gebruikt
#    hier moet ik nog in voorzien dat er niet alleen drums maar ook bas oid meedoet
#    theoretisch, want zelf gebruik ik dat eigenlijk niet?
    def print_beat_bassline(self, sample_list, printseq, _out=sys.stdout):
        for pattnum, pattern, pattlen in self.bbpatterndata.items():
            print('pattern {:>2}:'.format(pattnum + 1), file=_out)
            events = collections.defaultdict(list)
            for pattname, pattevents in pattern:
                for name, letter in sample_list:
                    if name == pattname:
                        pattlet = letter
                for note, ev in pattevents:
                    for letter in pattlet:
                        events[letter].append(ev)
                ## print(letter, events[letter])
            for letter in printseq:
                printable = ['          ']
                out = False
                for x in range(pattlen):
                    if x in events[letter]:
                        printable.append(letter)
                        out = True
                    else:
                        printable.append('.')
                if out:
                    print(''.join(printable), file=_out)


#- er word(t)(en) (een) midi drumtrack(s) gebruikt
    def print_drumtrack(self, trackname, _out=sys.stdout):
        unlettered = set()
        for ix, pattdata in enumerate(self.patterndata[trackname]):
            pattern, pattlen = pattdata
            print('\npattern {:>2}:'.format(ix + 1), file=_out)
            events = collections.defaultdict(list)
            for pitch, ev in pattern:
                notestr = shared.get_inst_name(pitch - 23)
                if notestr == '?':
                    unlettered.add('no letter yet for `{}`'.format(
                        shared.gm_drums[pitch - 23][1]))
                events[notestr].append(ev)
            for letter in shared.standard_printseq:
                printable = ['          ']
                out = False
                for x in range(pattlen):
                    if x in events[letter]:
                        printable.append(letter)
                        out = True
                    else:
                        printable.append('.')
                if out:
                    print(''.join(printable), file=_out)
        for x in unlettered: print(x, file=_out)

#- er worden aparte instrumenten gebruikt
    def print_drums(self, sample_list, printseq, _out=sys.stdout):
        pass

    def print_instrument(self, trackname, _out=sys.stdout):
        for ix, pattdata in enumerate(self.patterndata[trackname]):
            pattern, pattlen = pattdata
            print('\npattern {:>2}:'.format(ix + 1), file=_out)
            events = collections.defaultdict(list)
            notes = set()
            for pitch, ev in pattern:
                events[pitch].append(ev)
                notes.add(pitch)
            for pitch in reversed(sorted(notes)):
                printable = ['          ']
                out = False
                for x in range(pattlen):
                    if x in events[pitch]:
                        printable.append(shared.get_note_name(pitch))
                        out = True
                    else:
                        printable.append('...')
                if out:
                    print(' '.join(printable), file=_out)

