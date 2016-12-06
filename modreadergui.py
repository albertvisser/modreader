"""
modreadergui.py

reads a given module

shows the samples

offers a screen where you can associate letters with drum samples

creates a collection of files containing:
- the module name, samples list and patterns sequence
- the drumsamples together
- the other samples one-by-one
"""
import sys
import os.path
import datetime
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as gui
import PyQt5.QtCore as core
import modreader
import midreader
import medreader
import mmpreader
import rppreader

class MainFrame(qtw.QWidget):

    def __init__(self, parent=None):
        super().__init__()
        self._mru_items = []
        self.loaded = None
        self.drums = []
        self.nondrums = []
        self.filenaam = ''
        self.title = "ModReaderGui"
        self.setWindowTitle(self.title)
        try:
            with open('mru_files') as _in:
                for line in _in:
                    if line.strip():
                        self._mru_items.append(line.strip())
        except FileNotFoundError:
            pass
        # this should enable tabbing, but apparently it doesn't?
        self.setFocusPolicy(core.Qt.StrongFocus)
        self.create_widgets()
        self.create_actions()

    def create_widgets(self):

        vbox = qtw.QVBoxLayout()

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(qtw.QLabel("Select module file:", self))
        self.ask_modfile = qtw.QComboBox(self)
        self.ask_modfile.setEditable(True)
        self.ask_modfile.addItems([x for x  in self._mru_items])
        self.ask_modfile.setEditText(self.filenaam)
        self.ask_modfile.editTextChanged.connect(self.namechange)
        hbox.addWidget(self.ask_modfile)
        zoek_button = qtw.QPushButton("&Browse", self)
        zoek_button.clicked.connect(self.find_file)
        hbox.addWidget(zoek_button)
        hbox.addStretch()
        vbox.addLayout(hbox)

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        load_button = qtw.QPushButton("&Load module", self)
        load_button.clicked.connect(self.load_module)
        hbox.addWidget(load_button)
        hbox.addStretch()
        vbox.addLayout(hbox)

        hbox = qtw.QHBoxLayout()
        hbox.addWidget(qtw.QLabel("Select + Move\nDrum Samples:", self))

        self.list_samples = qtw.QListWidget(self)
        self.list_samples.setSelectionMode(qtw.QAbstractItemView.ExtendedSelection)
        hbox.addWidget(self.list_samples)

        col = qtw.QVBoxLayout()
        col.addStretch()
        move_button = qtw.QPushButton('→', self)
        move_button.clicked.connect(self.move_to_right)
        col.addWidget(move_button)
        back_button = qtw.QPushButton('←', self)
        back_button.clicked.connect(self.move_to_left)
        col.addWidget(back_button)
        col.addStretch()
        hbox.addLayout(col)

        self.mark_samples = qtw.QListWidget(self)
        self.mark_samples.setSelectionMode(qtw.QAbstractItemView.ExtendedSelection)
        hbox.addWidget(self.mark_samples)

        col = qtw.QVBoxLayout()
        col.addStretch()
        up_button = qtw.QPushButton('Move &Up', self)
        up_button.clicked.connect(self.move_up)
        col.addWidget(up_button)
        down_button = qtw.QPushButton('Move &Down', self)
        down_button.clicked.connect(self.move_down)
        col.addWidget(down_button)
        assign_button = qtw.QPushButton('&Assign letter', self)
        assign_button.clicked.connect(self.assign)
        col.addWidget(assign_button)
        self.remove_button = qtw.QPushButton('&Remove', self)
        self.remove_button.clicked.connect(self.remove)
        self.remove_button.setEnabled(False)
        col.addWidget(self.remove_button)
        col.addStretch()
        hbox.addLayout(col)
        vbox.addLayout(hbox)

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(qtw.QLabel("Destination:", self))
        self.basedir = os.path.expanduser('~/magiokis/data/transcripts')

        self.dest = qtw.QLabel(self.basedir, self)
        hbox.addWidget(self.dest)
        dest_button = qtw.QPushButton("Ch&ange", self)
        dest_button.clicked.connect(self.change_dest)
        hbox.addWidget(dest_button)
        hbox.addStretch()
        vbox.addLayout(hbox)

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        create_button = qtw.QPushButton("&Create transcription files", self)
        create_button.clicked.connect(self.create_files)
        hbox.addWidget(create_button)
        hbox.addStretch()
        vbox.addLayout(hbox)

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        quit_button = qtw.QPushButton("E&xit", self)
        quit_button.clicked.connect(self.exit)
        hbox.addWidget(quit_button)
        hbox.addStretch()
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        self.ask_modfile.setFocus()

        self.show()

    def create_actions(self):
        self.helpitems = ['Use Alt with the underscored letters or']
        self.actionlist = (
            ('Activate filename field', 'Ctrl+Home', self.activate_filename),
            ('Select a file', 'Ctrl+F', self.find_file),
            ('Load indicated module', 'Ctrl+O', self.load_module),
            ('Activate left listbox', 'Ctrl+L', self.activate_left),
            ('Move sample to right listbox', 'Ctrl+Right', self.move_to_right),
            ('Activate right listbox', 'Ctrl+R', self.activate_right),
            ('Move sample to left listbox', 'Ctrl+Left', self.move_to_left),
            ('Move sample up in left list', 'Ctrl+Up', self.move_up),
            ('Move sample down in left list', 'Ctrl+Down', self.move_down),
            ('Assign letter(s) to sample', 'F2', self.assign),
            ('Delete dummy sample', 'Del', self.remove),
            ('Create transcription files', 'Ctrl+S', self.create_files),
            ('Quit the application', 'Ctrl+Q', self.exit),
            ('Show this screen', 'F1', self.help),
            )
        for name, shortcut, callback in self.actionlist:
            act = qtw.QAction(name, self)
            act.setShortcut(shortcut)
            act.triggered.connect(callback)
            self.addAction(act)
            self.helpitems.append('{}\t\t{}'.format(shortcut, name))

    def activate_filename(self, *args):
        self.ask_modfile.setFocus(True)

    def namechange(self, *args):
        self.list_samples.clear()
        self.mark_samples.clear()

    def find_file(self, *args):
        """event handler voor 'zoek in directory'"""
        oupad = self.ask_modfile.currentText()
        if oupad == "":
             oupad = '/home/albert/magiokis/data'
        name, pattern = qtw.QFileDialog.getOpenFileName(self, "Open File", oupad,
            "Known files (*.mod *.mid *.med *mmpz *rpp)")
        if name != "" and name != oupad:
            self.ask_modfile.setEditText(name)
            if name not in self._mru_items:
                self._mru_items.append(name)
                if len(self._mru_items) > 9:
                    self._mru_items.pop(0)
                self.ask_modfile.addItem(name)

    def load_module(self, *args):
        pad = self.ask_modfile.currentText()
        msg = ''
        if not pad:
            msg = 'You need to provide a filename'
        elif not os.path.exists(pad):
            msg = 'File does not exist'
        if msg:
            qtw.QMessageBox.information(self, self.title, msg)
            return
        self.ftype = os.path.splitext(pad)[1][1:].lower()
        if self.ftype == 'mod':
            self.loaded = modreader.ModFile(pad)
            self.nondrums = [x[0] for x in self.loaded.samples.values() if x[0]]
            self.drums = []
        elif self.ftype == 'mid':
            self.loaded = midreader.MidiFile(pad)
            self.nondrums = [x[0] for x in self.loaded.instruments.values()
                if x[1] != 10]
            self.drums = [x[0] + " (*)" for x in self.loaded.instruments.values()
                if x[1] == 10]
        elif self.ftype == 'med':
            self.loaded = medreader.MedModule(pad)
            self.nondrums = self.loaded.samplenames
            self.drums = []
        elif self.ftype == 'mmpz':
            self.loaded = mmpreader.MMPFile(pad)
            self.nondrums = self.loaded.tracknames
            if self.loaded.bbtracknames:
                self.drums = ['{} ({})'.format(x, x[0])
                    for x in self.loaded.bbtracknames]
            else:
                self.drums = []
        elif self.ftype == 'rpp':
            self.loaded = rppreader.RppFile(pad)
            ## for x, y in self.loaded.patterns.items():
                ## print(y[0][1])
            self.nondrums = [y for x, y in self.loaded.instruments.items()
                if not self.loaded.patterns[x][0][1]['drumtrack']]
            self.drums = [y + ' (*)' for x, y in self.loaded.instruments.items()
                if self.loaded.patterns[x][0][1]['drumtrack']]
        self.list_samples.clear()
        self.list_samples.addItems(self.nondrums)
        self.mark_samples.clear()
        self.usedtohave = {}
        if self.drums:
            self.mark_samples.addItems(self.drums)
        self.newdir = os.path.join(self.basedir,
            os.path.splitext(os.path.basename(pad))[0]).replace('_', ' ')
        self.dest.setText(self.newdir)

    def activate_left(self, *args):
        item = self.list_samples.currentItem()
        if not item:
            item = self.list_samples.item(0)
        if item:
            self.list_samples.setCurrentItem(item)
            item.setSelected(True)
        self.list_samples.setFocus(True)

    def activate_right(self, *args):
        item = self.mark_samples.currentItem()
        if not item:
            item = self.mark_samples.item(0)
        if item:
            self.mark_samples.setCurrentItem(item)
            item.setSelected(True)
        self.mark_samples.setFocus(True)

    def check_selected(self, list, only_one=False, for_now=False):
        selected = list.selectedItems()
        msg = ''
        if len(selected) == 0:
            if only_one and not for_now:
                msg = 'Please select an instrument'
            else:
                msg = 'Please select one or more instruments'
        if not msg and len(selected) > 1 and only_one:
            msg = 'One at a time, please'
            if for_now:
                msg += ' (for now)'
        if msg:
            qtw.QMessageBox.information(self, self.title, msg)
            return
        return selected

    def move_to_right(self, *args):
        """overbrengen naar rechterlijst zodat alleen de niet-drums overblijven
        """
        selected = self.check_selected(self.list_samples)
        if not selected:
            return
        templist = []
        for item in reversed(selected):
            id = self.list_samples.row(item)
            it = self.list_samples.takeItem(id)
            templist.insert(0, it)
        self.mark_samples.clearSelection()
        for item in templist:
            test = item.text()
            try:
                letter = self.usedtohave[test]
            except KeyError:
                letter = ''.join([x.strip()[0].lower() for x in test.split('+')])
            item.setText('{} ({})'.format(test, letter))
            self.mark_samples.addItem(item)
            self.mark_samples.setCurrentItem(item)
            item.setSelected(True)
        self.mark_samples.setFocus(True)

    def move_to_left(self, *args):
        """overbrengen naar linkerlijst (om alleen drumsamples over te houden)
        """
        selected = self.check_selected(self.mark_samples)
        if not selected:
            return
        templist = []
        for item in reversed(selected):
            id = self.mark_samples.row(item)
            it = self.mark_samples.takeItem(id)
            templist.insert(0, it)
        self.list_samples.clearSelection()
        for item in templist:
            test = item.text()
            x, y = test.rsplit(' (', 1)
            item.setText(x)
            self.usedtohave[x] = y[:-1]
            self.list_samples.addItem(item)
            self.list_samples.setCurrentItem(item)
            item.setSelected(True)
        self.list_samples.setFocus(True)

    def move_up(self, *args):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.check_selected(self.mark_samples, only_one=True,
            for_now=True)
        if not selected:
            return
        selindx = self.mark_samples.row(selected[0])
        if selindx > 0:
            item = self.mark_samples.takeItem(selindx)
            self.mark_samples.insertItem(selindx - 1, item)
            item.setSelected(True)
            self.mark_samples.scrollToItem(item)

    def move_down(self, *args):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.check_selected(self.mark_samples, only_one=True,
            for_now=True)
        if not selected:
            return
        selindx = self.mark_samples.row(selected[0])
        if selindx < len(self.mark_samples) - 1:
            item = self.mark_samples.takeItem(selindx)
            self.mark_samples.insertItem(selindx + 1, item)
            item.setSelected(True)
            self.mark_samples.scrollToItem(item)

    def assign(self, *args):
        """letter toekennen voor in display
        """
        selected = self.check_selected(self.mark_samples, only_one=True)
        if not selected:
            return
        try:
            inst, data = selected[0].text().rsplit(None, 1)
        except ValueError:
            inst, data = selected[0].text(), ''
        text, ok = qtw.QInputDialog.getText(self, self.title, 'Enter letter(s) '
            'to be printed for "{}"\n("*" for a midi drumtrack)'.format(inst),
            text=data[1:-1])
        if ok:
            if text:
                inst += " ({})".format(text)
            selected[0].setText(inst)

    def remove(self, *args):
        selected = self.mark_samples.selectedItems()
        for item in selected:
            selindex = self.mark_samples.row(item)
            if not item.text().startswith('dummy_sample ('):
                qtw.QMessageBox.information(self, self.title, 'You can only remove '
                    'dummy samples')
                return
        for item in selected:
            selindx = self.mark_samples.row(item)
            self.mark_samples.takeItem(selindx)

    def change_dest(self):
        name, ok = qtw.QInputDialog.getText(self, "Change Name", "", text=self.newdir)
        if ok:
            self.newdir = name
            self.dest.setText(self.newdir)

        ## self.push()

    def push(self):
        qtw.QMessageBox.information(self, 'The Modreadergui Adventure',
            'You push a button.\n\nNothing happens.')

    def create_files(self):
        msg = ''
        if not self.loaded:
            msg = 'Please load a module first'

        if not msg: # elif test in ('.mod', '.med'):
            msg = self.check_letter_assignment()

        if msg:
            qtw.QMessageBox.information(self, self.title, msg)
            return

        try:
            os.mkdir(self.newdir)
        except FileExistsError:
            pass
        self.dts = datetime.datetime.today().strftime('%Y%m%d%H%M%S')

        go = {
            'mod': self.process_modfile,
            'mid': self.process_midifile,
            'med': self.process_medfile,
            'mmpz': self.process_mmpfile,
            'rpp': self.process_rppfile,
            }
        go[self.ftype]()
        qtw.QMessageBox.information(self, self.title, 'Done')


    def help(self, *args):
        qtw.QMessageBox.information(self, 'Keyboard Shortcuts',
            '\n'.join(self.helpitems))


    def exit(self, *args):
        with open('mru_files', 'w') as _out:
            for name in self._mru_items:
                _out.write(name + '\n')
        pass # built in delay to avoid segfault
        self.close()


    def check_letter_assignment(self):
        msg = ''
        samples, letters, printseq = [], [], ''

        # get all letters assigned to sample
        all_item_texts = [self.mark_samples.item(x).text() for x in range(len(
            self.mark_samples))]
        try:
            for x, y in [z.rsplit(None, 1) for z in all_item_texts]:
                samples.append(x)
                letters.append(y[1:-1])
        except ValueError:
            msg = 'Please assign letters to *all* drumtracks'

        if not msg:
            printseq = "".join([x for x in letters if len(x) == 1])
            test_printseq = printseq.replace('*', '')
            if len(test_printseq) != len(set(test_printseq)):
                msg = 'Please correct multiple assignments to the same letter'

        if not msg:
            ready = True
            for x in set(''.join([x for x in letters])):
                if x not in printseq:
                    new = qtw.QListWidgetItem('dummy_sample ({})'.format(x))
                    self.mark_samples.addItem(new)
                    self.mark_samples.scrollToItem(new)
                    self.mark_samples.currentItem().setSelected(False)
                    new.setSelected(True)
                    self.remove_button.setEnabled(True)
                    ready = False
            if not ready:
                msg = ' '.join(('Please relocate the dummy samples',
                    'so their letters are in the right position'))

        self._assigned = samples, letters, printseq
        return msg


    def get_general_filename(self):
        return self.get_instrument_filename('general')

    def get_drums_filename(self):
        return self.get_instrument_filename('drums')

    def get_instrument_filename(self, name):
        return os.path.join(self.newdir, '{}-{}-{}'.format(self.dts, self.ftype,
            name))

    def process_modfile(self):
        drums = []
        nondrums = []
        samples, letters, printseq = self._assigned
        samples_2 = [self.list_samples.item(x).text().split()[0] for x in range(
            len(self.list_samples))]

        for num, data in self.loaded.samples.items():
            if data[0] in samples:
                ix = samples.index(data[0])
                drums.append((num + 1, letters[ix]))
            elif data[0] in samples_2:
                ix = samples_2.index(data[0])
                nondrums.append((num + 1, data[0]))

        with open(self.get_general_filename(), "w") as out:
            if drums:
                self.loaded.print_general_data(out, drums)
            else:
                self.loaded.print_general_data(out)
        if drums:
            with open(self.get_drums_filename(), "w") as out:
                self.loaded.print_drums(drums, printseq, out)
        for number, name in nondrums:
            with open(self.get_instrument_filename(name), "w") as out:
                self.loaded.print_instrument(number, out)

    def process_midifile(self):
        # this is assuming I only have midi files that use a separate drum track
        # (instead of several tracks with one drum instrument each)
        with open(self.get_general_filename(), "w") as _out:
            self.loaded.print_general_data(_out)
        for trackno, data in self.loaded.instruments.items():
            with open(self.get_instrument_filename(data[0]), 'w') as _out:
                self.loaded.print_instrument(trackno, _out)

    def process_medfile(self):
        drums = []
        nondrums = []
        samples, letters, printseq = self._assigned
        samples_2 = [self.list_samples.item(x).text().split()[0] for x in range(
            len(self.list_samples))]

        for num, name in enumerate(self.loaded.samplenames):
            if name in samples:
                ix = samples.index(name)
                drums.append((num + 1, letters[ix]))
            elif name in samples_2:
                ix = samples_2.index(name)
                nondrums.append((num + 1, name))

        with open(self.get_general_filename(), "w") as out:
            if drums:
                self.loaded.print_general_data(out, drums)
            else:
                self.loaded.print_general_data(out)
        if drums:
            with open(self.get_drums_filename(), "w") as out:
                self.loaded.print_drums(drums, printseq, out)
        for number, name in nondrums:
            with open(self.get_instrument_filename(name), "w") as out:
                self.loaded.print_instrument(number, out)

    def process_mmpfile(self):
        drumsamples, letters, printseq = self._assigned
        inst_samples = [self.list_samples.item(x).text() for x in
            range(self.list_samples.count())]
        sample_map = list(zip(drumsamples, letters))

        with open(self.get_general_filename(), "w") as _out:
            self.loaded.print_general_data(sample_map, _out=_out)

        if [x for x, y in sample_map if y != '*']:
            if self.loaded.bbtracknames:
                with open(self.get_instrument_filename('bbdrums'), "w") as _out:
                    self.loaded.print_beat_bassline(sample_map, printseq, _out=_out)
            else:
                with open(self.get_drums_filename(), "w") as _out:
                    self.loaded.print_drums(sample_map, printseq, _out=_out)

        for trackname in [x for x, y in sample_map if y == '*']:
            with open(self.get_instrument_filename(trackname), "w") as _out:
                self.loaded.print_drumtrack(trackname, _out=_out)

        for trackname in inst_samples:
            with open(self.get_instrument_filename(trackname), "w") as _out:
                self.loaded.print_instrument(trackname,_out=_out)

    def process_rppfile(self):
        # this is assuming I only have projects that use MIDI data
        # where drums are in a separate track instead of one drum per track
        with open(self.get_general_filename(), 'w') as _out:
            self.loaded.print_general_data(_out)
        for trackno, data in self.loaded.instruments.items():
            with open(self.get_instrument_filename(data), 'w') as _out:
                self.loaded.print_instrument(trackno, _out)

app = qtw.QApplication(sys.argv)
win = MainFrame()
sys.exit(app.exec_())
