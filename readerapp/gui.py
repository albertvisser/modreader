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
## import os.path
import pathlib
import datetime
import logging
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as gui
import PyQt5.QtCore as core
import readerapp.shared as shared
import readerapp.modreader as modreader
import readerapp.midreader as midreader
import readerapp.medreader as medreader
import readerapp.mmpreader as mmpreader
import readerapp.rppreader as rppreader
import readerapp.xmreader as xmreader

mru_filename = pathlib.Path(__file__).parent / 'mru_files'


def log(inp):
    "just a wrapper"
    logging.info(inp)


def waiting_cursor(func):
    "change the cursor before and after an operation"
    def wrap_operation(self):
        "the wrapped operation is a method without arguments"
        self.app.setOverrideCursor(gui.QCursor(core.Qt.WaitCursor))
        func(self)
        self.app.restoreOverrideCursor()
    return wrap_operation


def list_items(listbox):
    """retrieve list of items listed in listbox
    """
    return [listbox.item(i).text() for i in range(len(listbox))]


class GetDestDialog(qtw.QDialog):
    """dialog om een output filename te bepalen via tekst input of file selectie
    """
    def __init__(self, parent, text=""):
        self.parent = parent
        super().__init__(parent)
        self.resize(300, -1)
        sizer = qtw.QVBoxLayout()

        hsizer = qtw.QHBoxLayout()
        self.dest = qtw.QLineEdit(self)
        ## self.dest.setMaximumWidth(500)
        self.dest.setText(text)
        hsizer.addWidget(self.dest)
        self.button = qtw.QPushButton('Browse', self, clicked=self.browse)
        self.button.setMaximumWidth(68)
        hsizer.addWidget(self.button)
        sizer.addLayout(hsizer)

        buttonbox = qtw.QDialogButtonBox()
        buttonbox.addButton(qtw.QDialogButtonBox.Ok)
        buttonbox.addButton(qtw.QDialogButtonBox.Cancel)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        hsizer = qtw.QHBoxLayout()
        hsizer.addStretch()
        hsizer.addWidget(buttonbox)
        hsizer.addStretch()
        sizer.addLayout(hsizer)
        self.setLayout(sizer)

    def browse(self):
        """callback for the button
        """
        startdir = self.dest.text() or os.getcwd()
        path = qtw.QFileDialog.getSaveFileName(self, 'Kies een bestand', startdir)
        if path[0]:
            self.dest.setText(path[0])

    def accept(self):
        """pass the chosen name to the main screen
        """
        self.parent.newdir = self.dest.text()
        super().accept()


class MainFrame(qtw.QWidget):
    """Main screen for the application
    """
    def __init__(self, app):
        self.app = app
        super().__init__()
        self.loaded = None
        self.drums = []
        self.nondrums = []
        self.filenaam = ''
        self.title = "ModReaderGui"
        self.setWindowTitle(self.title)
        try:
            self._mru_items = mru_filename.read_text().strip().split('\n')
        except FileNotFoundError:
            self._mru_items = []

        # this should enable tabbing, but apparently it doesn't?
        self.setFocusPolicy(core.Qt.StrongFocus)
        self.create_widgets()
        self.create_actions()
        self.newdir = str(shared.basedir)

    def create_widgets(self):
        """set up the GUI
        """
        vbox = qtw.QVBoxLayout()

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(qtw.QLabel("Select module file:", self))
        self.ask_modfile = qtw.QComboBox(self)
        self.ask_modfile.setEditable(True)
        self.ask_modfile.addItems([x for x in self._mru_items])
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
        hbox.addStretch()
        hbox.addWidget(qtw.QLabel("Select + Move drum samples:", self))
        hbox.addStretch()
        vbox.addLayout(hbox)

        hbox = qtw.QHBoxLayout()

        col = qtw.QVBoxLayout()
        col.addSpacing(9)
        col.addWidget(qtw.QLabel("Reorder\nremaining\ninstruments:", self))
        inst_up_button = qtw.QPushButton('Move U&p', self)
        inst_up_button.clicked.connect(self.move_inst_up)
        col.addWidget(inst_up_button)
        inst_down_button = qtw.QPushButton('Move D&own', self)
        inst_down_button.clicked.connect(self.move_inst_down)
        col.addWidget(inst_down_button)
        col.addStretch()
        hbox.addLayout(col)

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
        col.addWidget(qtw.QLabel("Reorder\ndrum samples:", self))
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

        self.dest = qtw.QLabel(str(shared.basedir), self)
        hbox.addWidget(self.dest)
        dest_button = qtw.QPushButton("Cha&nge", self)
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
        self.check_full = qtw.QCheckBox('Show as continual &timeline:', self)
        hbox.addWidget(self.check_full)
        hbox.addWidget(qtw.QLabel('Break up in max.'))
        self.max_events = qtw.QSpinBox()
        self.max_events.setValue(32)
        self.max_events.setSingleStep(8)
        hbox.addWidget(self.max_events)

        hbox.addWidget(qtw.QLabel('events '))
        self.check_nonempty = qtw.QCheckBox("Crop empty tracks", self)
        hbox.addWidget(self.check_nonempty)
        self.check_allinone = qtw.QCheckBox("All in one file", self)
        hbox.addWidget(self.check_allinone)
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
        """assign actions to keystroke combinations
        """
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
            ('Move sample up in right list', 'Ctrl+Shift+Up', self.move_inst_up),
            ('Move sample down in right list', 'Ctrl+Shift+Down', self.move_inst_down),
            ('Assign letter(s) to sample', 'F2', self.assign),
            ('Delete dummy sample', 'Del', self.remove),
            ('Focus transcription options', 'Ctrl+T', self.options),
            ('Create transcription files', 'Ctrl+S', self.create_files),
            ('Quit the application', 'Ctrl+Q', self.exit),
            ('Show this screen', 'F1', self.help))

        for name, shortcut, callback in self.actionlist:
            act = qtw.QAction(name, self)
            act.setShortcut(shortcut)
            act.triggered.connect(callback)
            self.addAction(act)
            fmt = '\t\t'
            if shortcut in ['Ctrl+Shift+Down']:
                fmt = '\t'
            self.helpitems.append('{}{}{}'.format(shortcut, fmt, name))

    def activate_filename(self):
        """Move focus to the filename field
        """
        self.ask_modfile.setFocus(True)

    def namechange(self):
        """clear the listboxes (on change of filename)
        """
        self.list_samples.clear()
        self.mark_samples.clear()

    def find_file(self):
        """event handler voor 'zoek in directory'"""
        oupad = self.ask_modfile.currentText()
        if oupad == "":
            oupad = shared.location
        name = qtw.QFileDialog.getOpenFileName(
            self, "Open File", oupad,
            "Known files ({})".format(' '.join(['*.{}'.format(x)
                                                for x in shared.known_files])))[0]
        if name != "" and name != oupad:
            self.ask_modfile.setEditText(name)
            if name not in self._mru_items:
                self._mru_items.append(name)
                if len(self._mru_items) > 9:
                    self._mru_items.pop(0)
                self.ask_modfile.addItem(name)

    @waiting_cursor
    def load_module(self):
        """load and parse the chosen file and show detected instruments
        """
        pad = self.ask_modfile.currentText()
        fn = pathlib.Path(pad)
        msg = ''
        if not pad:
            msg = 'You need to provide a filename'
        elif not fn.exists():
            msg = 'File does not exist'
        if msg:
            qtw.QMessageBox.information(self, self.title, msg)
            return
        ## self.ftype = os.path.splitext(pad)[1][1:].lower()
        self.ftype = fn.suffix[1:].lower()
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
            self.nondrums = [x[1] for x in self.loaded.samplenames]
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
            self.nondrums = [y for x, y in self.loaded.instruments.items()
                             if not self.loaded.patterns[x][0][1]['drumtrack']]
            self.drums = [y + ' (*)' for x, y in self.loaded.instruments.items()
                          if self.loaded.patterns[x][0][1]['drumtrack']]
        elif self.ftype == 'xm':
            self.loaded = xmreader.ExtModule(pad)
            self.nondrums = [x[1] for x in self.loaded.samplenames]
            self.drums = []
        self.list_samples.clear()
        self.list_samples.addItems(self.nondrums)
        self.mark_samples.clear()
        self.usedtohave = {}
        if self.drums:
            self.mark_samples.addItems(self.drums)
        self.newdir = str(shared.basedir / pathlib.Path(pad).name.replace('_', ' '))
        self.dest.setText(self.newdir)

    def activate_left(self):
        """move focus to the listbox on the left
        """
        item = self.list_samples.currentItem()
        if not item:
            item = self.list_samples.item(0)
        if item:
            self.list_samples.setCurrentItem(item)
            item.setSelected(True)
        self.list_samples.setFocus(True)

    def activate_right(self):
        """move focus to the listbox on the right
        """
        item = self.mark_samples.currentItem()
        if not item:
            item = self.mark_samples.item(0)
        if item:
            self.mark_samples.setCurrentItem(item)
            item.setSelected(True)
        self.mark_samples.setFocus(True)

    def check_selected(self, lst, only_one=False, for_now=False):
        """check if any items (instruments) were selected
        """
        selected = lst.selectedItems()
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

    def move_to_right(self):
        """overbrengen naar rechterlijst zodat alleen de niet-drums overblijven
        """
        selected = self.check_selected(self.list_samples)
        if not selected:
            return
        templist = []
        for item in reversed(selected):
            id_ = self.list_samples.row(item)
            it_ = self.list_samples.takeItem(id_)
            templist.insert(0, it_)
        self.mark_samples.clearSelection()
        for item in templist:
            test = item.text()
            try:
                letter = self.usedtohave[test]
            except KeyError:
                samps = [x.strip().lower() for x in test.split('+')]
                letter = ''
                for x in samps:
                    try:
                        letter += shared.samp2other[x]
                    except KeyError:
                        letter += x[0]
            item.setText('{} ({})'.format(test, letter))
            self.mark_samples.addItem(item)
            self.mark_samples.setCurrentItem(item)
            item.setSelected(True)
        self.mark_samples.setFocus(True)

    def move_to_left(self):
        """overbrengen naar linkerlijst (om alleen drumsamples over te houden)
        """
        selected = self.check_selected(self.mark_samples)
        if not selected:
            return
        templist = []
        for item in reversed(selected):
            id_ = self.mark_samples.row(item)
            it_ = self.mark_samples.takeItem(id_)
            templist.insert(0, it_)
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

    def move_up(self):
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

    def move_down(self):
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

    def move_inst_up(self):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.check_selected(self.list_samples, only_one=True,
                                       for_now=True)
        if not selected:
            return
        selindx = self.list_samples.row(selected[0])
        if selindx > 0:
            item = self.list_samples.takeItem(selindx)
            self.list_samples.insertItem(selindx - 1, item)
            item.setSelected(True)
            self.list_samples.scrollToItem(item)

    def move_inst_down(self):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.check_selected(self.list_samples, only_one=True,
                                       for_now=True)
        if not selected:
            return
        selindx = self.list_samples.row(selected[0])
        if selindx < len(self.list_samples) - 1:
            item = self.list_samples.takeItem(selindx)
            self.list_samples.insertItem(selindx + 1, item)
            item.setSelected(True)
            self.list_samples.scrollToItem(item)

    def assign(self):
        """letter toekennen voor in display
        """
        selected = self.check_selected(self.mark_samples, only_one=True)
        if not selected:
            return
        try:
            inst, data = selected[0].text().rsplit(None, 1)
        except ValueError:
            inst, data = selected[0].text(), ''
        text, ok_ = qtw.QInputDialog.getText(
            self, self.title,
            'Enter letter(s) to be printed for "{}"\n("*" for a midi drumtrack'
            ')'.format(inst), text=data[1:-1])
        if ok_:
            if text:
                inst += " ({})".format(text)
            selected[0].setText(inst)

    def remove(self):
        """delete superfluous item from the drum instruments list
        """
        selected = self.mark_samples.selectedItems()
        for item in selected:
            ## selindex = self.mark_samples.row(item)
            if not item.text().startswith('dummy_sample ('):
                qtw.QMessageBox.information(
                    self, self.title,
                    'You can only remove dummy samples')
                return
        for item in selected:
            selindx = self.mark_samples.row(item)
            self.mark_samples.takeItem(selindx)

    def change_dest(self):
        """callback for button to change standard output location
        """
        if GetDestDialog(self, text=self.newdir).exec_() == qtw.QDialog.Accepted:
            self.dest.setText(self.newdir)

    def push(self):
        """some leftover "humour" from when I was designing the app
        """
        qtw.QMessageBox.information(self, 'The ModReaderGui Adventure',
                                    'You push a button.\n\nNothing happens.')

    def options(self):
        """Move focus to the first button on the "options" line
        """
        self.check_full.setFocus(True)

    def create_files(self):
        """produce output and notify when ready
        """
        self.do_creation()
        qtw.QMessageBox.information(self, self.title, 'Done')

    def help(self):
        """show some help info
        """
        qtw.QMessageBox.information(self, 'Keyboard Shortcuts',
                                    '\n'.join(self.helpitems))

    def exit(self):
        """close the application
        """
        mru_filename.write_text('\n'.join(self._mru_items) + '\n')
        self.close()

    def check_letter_assignment(self):
        """Check if all drum instruments are assigned a letter
        """
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
            first = True
            for x in set(''.join([x for x in letters])):
                if x not in printseq:
                    new = qtw.QListWidgetItem('dummy_sample ({})'.format(x))
                    self.mark_samples.addItem(new)
                    self.mark_samples.scrollToItem(new)
                    self.mark_samples.currentItem().setSelected(False)
                    if first:
                        first = False
                        for item in self.mark_samples.selectedItems():
                            item.setSelected(False)
                    new.setSelected(True)
                    self.remove_button.setEnabled(True)
                    ready = False
            if not ready:
                msg = ' '.join(('Please relocate the dummy sample(s)',
                                'so their letters are in the right position'))

        self._assigned = samples, letters, printseq
        return msg

    def get_general_filename(self):
        """determine filename for overview file
        """
        return self.get_instrument_filename('general')

    def get_drums_filename(self):
        """determine filename for drum instrument file
        """
        return self.get_instrument_filename('drums')

    def get_instrument_filename(self, name):
        """determine filename for "regular" instrument file
        """
        return str(pathlib.Path(self.newdir) / '{}-{}-{}'.format(self.dts, self.ftype,
                                                           name))

    def process_modfile(self):
        """Create output for NoiseTracker/SoundTracker/MadTracker module
        """
        drums = []
        nondrums = []
        samples, letters, printseq = self._assigned

        for num, data in self.loaded.samples.items():
            if data[0] in samples:
                ix = samples.index(data[0])
                drums.append((num + 1, letters[ix]))

        for name in list_items(self.list_samples):
            ix = {y[0]: x for x, y in self.loaded.samples.items()}[name]
            nondrums.append((ix + 1, name))

        with open(self.get_general_filename(), "w") as out:
            if drums:
                self.loaded.print_general_data(drums, self.check_full.isChecked(),
                                               out)
            else:
                self.loaded.print_general_data(full=self.check_full.isChecked(),
                                               _out=out)
        self.loaded.prepare_print_instruments(nondrums)
        self.loaded.prepare_print_drums(printseq)
        options = (self.max_events.value(), self.check_nonempty.isChecked())
        if self.check_allinone.isChecked():
            druminst = [(x, y) for x, y in drums if len(y) == 1]
            log('calling print_all_instruments_full with args {} {} {} '
                '{} {}'.format(nondrums, druminst, printseq, options,
                               self.get_general_filename()))
            with open(self.get_general_filename(), 'a') as _out:
                self.loaded.print_all_instruments_full(nondrums, druminst, printseq,
                                                       options, _out)
            return
        if drums:
            with open(self.get_drums_filename(), "w") as out:
                if self.check_full.isChecked():
                    self.loaded.print_drums_full(printseq, options, out)
                else:
                    self.loaded.print_drums(printseq, out)
        for number, name in nondrums:
            with open(self.get_instrument_filename(name), "w") as out:
                if self.check_full.isChecked():
                    self.loaded.print_instrument_full(number, options, out)
                else:
                    self.loaded.print_instrument(number, out)

    def process_midifile(self):
        """Create output for MIDI

        this is assuming I only have midi files that use a separate drum track
        (instead of several tracks with one drum instrument each)
        """
        options = (self.max_events.value(), self.check_nonempty.isChecked())
        with open(self.get_general_filename(), "w") as _out:
            self.loaded.print_general_data(full=self.check_full.isChecked(),
                                           stream=_out)
        self.loaded.prepare_print_instruments()
        # kijken of er dubbele namen zijn
        test, dubbel = set(), set()
        for trackno, data in self.loaded.instruments.items():
            if data[0] in test:
                dubbel.add('-'.join((data[0], str(trackno))))
            else:
                test.add(data[0])
        if self.check_allinone.isChecked():
            inst_list = list_items(self.list_samples)
            inst_list += [x.rsplit(' ', 1)[0] for x in list_items(self.mark_samples)]
            with open(self.get_general_filename(), 'a') as _out:
                self.loaded.print_all_instruments_full(inst_list, options, _out)
            return
        for trackno, name in self.loaded.instruments.items():
            with open(self.get_instrument_filename(name), 'w') as _out:
                if self.check_full.isChecked():
                    unlettered = self.loaded.print_instrument_full(trackno, options,
                                                                   _out)
                else:
                    unlettered = self.loaded.print_instrument(trackno, _out)
            if unlettered:
                qtw.QMessageBox.information(self, self.title, '\n'.join(unlettered))

    def process_medfile(self):
        """Create output for (Octa)Med module
        """
        drums = []
        nondrums = []
        samples, letters, printseq = self._assigned
        options = (self.max_events.value(), self.check_nonempty.isChecked())

        for num, name in enumerate(self.loaded.samplenames):
            name = name[1]
            if name in samples:
                ix = samples.index(name)
                drums.append((num + 1, letters[ix]))

        for name in list_items(self.list_samples):
            ix = [y for x, y in self.loaded.samplenames].index(name)
            nondrums.append((ix + 1, name))

        with open(self.get_general_filename(), "w") as out:
            if drums:
                log('calling print_general_data with args {} {} {}'.format(
                    drums, self.check_full.isChecked(), out))
                self.loaded.print_general_data(drums, self.check_full.isChecked(),
                                               out)
            else:
                log('calling print_general_data with args {} {}'.format(
                    self.check_full.isChecked(), out))
                self.loaded.print_general_data(full=self.check_full.isChecked(),
                                               _out=out)
        log('calling prepare_print_instruments with argument {}'.format(nondrums))
        self.loaded.prepare_print_instruments(nondrums)
        self.loaded.prepare_print_drums(printseq)
        if self.check_allinone.isChecked():
            with open(self.get_general_filename(), 'a') as _out:
                self.loaded.print_all_instruments_full(nondrums, printseq,
                                                       options, _out)
            return
        if drums:
            with open(self.get_drums_filename(), "w") as out:
                if self.check_full.isChecked():
                    ## self.loaded.print_drums_full(drums, printseq, options, out)
                    self.loaded.print_drums_full(printseq, options, out)
                else:
                    ## self.loaded.print_drums(drums, printseq, out)
                    self.loaded.print_drums(printseq, out)
        for number, name in nondrums:
            with open(self.get_instrument_filename(name), "w") as out:
                if self.check_full.isChecked():
                    self.loaded.print_instrument_full(name, options, out)
                else:
                    log('calling print_instrument with args {} {}'.format(number,
                                                                          out))
                    self.loaded.print_instrument(number, out)

    def process_mmpfile(self):
        """Create output for LMMS project
        """
        drumsamples, letters, printseq = self._assigned
        inst_samples = [self.list_samples.item(x).text() for x in
                        range(self.list_samples.count())]
        sample_map = list(zip(drumsamples, letters))
        drumkits = [x for x, y in sample_map if y == '*']

        with open(self.get_general_filename(), "w") as _out:
            ## log('calling self.loaded.print_general_data with args {} {} {}'.format(
                ## inst_samples, self.check_full.isChecked(), _out))
            ## self.loaded.print_general_data(inst_samples, self.check_full.isChecked(),
                ## _out)
            log('calling print_general_data with args {} {} {}'.format(
                drumkits, self.check_full.isChecked(), _out))
            self.loaded.print_general_data(drumkits, self.check_full.isChecked(),
                                           _out)

        ## log('calling self.loaded.prepare_print_instruments with argument {}'.format(
            ## [x for x, y in sample_map if y == '*']))
        log('calling prepare_print_instruments with argument {}'.format(
            drumkits))
        self.loaded.prepare_print_instruments(drumkits)
        # m.z. self.loaded.prepare_print_instruments(inst_samples) ?
        if self.loaded.bbtracknames:
            log('calling prepare_print_beat_bassline with args {}'
                ' {}'.format(sample_map, printseq))
            self.loaded.prepare_print_beat_bassline(sample_map, printseq)
        options = (self.max_events.value(), self.check_nonempty.isChecked())
        if self.check_allinone.isChecked():
            ## instlist = [x.rsplit(' ', 1) for x in list_items(self.list_samples)]
            with open(self.get_general_filename(), 'a') as _out:
                log('calling print_all_instruments_full with args {}'
                    ' {} {} {}'.format(inst_samples, printseq, options, _out))
                self.loaded.print_all_instruments_full(inst_samples,
                                                       printseq, options, _out)
            return

        if [x for x, y in sample_map if y != '*']:
            if self.loaded.bbtracknames:
                with open(self.get_instrument_filename('bbdrums'), "w") as _out:
                    if self.check_full.isChecked():
                        log('calling print_beat_bassline_full with args'
                            ' {} {} {}'.format(printseq, options, _out))
                        self.loaded.print_beat_bassline_full(printseq, options,
                                                             _out=_out)
                    else:
                        log('calling print_beat_bassline with args {}'
                            ' {} {}'.format(sample_map, printseq, _out))
                        self.loaded.print_beat_bassline(sample_map, printseq,
                                                        _out=_out)
            else:
                with open(self.get_drums_filename(), "w") as _out:
                    log('calling print_drums with args {} {} '
                        '{}'.format(sample_map, printseq, _out))
                    self.loaded.print_drums(sample_map, printseq, _out=_out)

        for trackname in [x for x, y in sample_map if y == '*']:
            with open(self.get_instrument_filename(trackname), "w") as _out:
                if self.check_full.isChecked():
                    log('calling print_instrument_full with args '
                        '{} {} {}'.format(trackname, options, _out))
                    unlettered = self.loaded.print_instrument_full(trackname,
                                                                   options,
                                                                   _out=_out)
                else:
                    log('calling print_drumtrack with args {} '
                        '{}'.format(trackname, _out))
                    unlettered = self.loaded.print_drumtrack(trackname, _out=_out)
            if unlettered:
                qtw.QMessageBox.information(self, self.title, '\n'.join(unlettered))

        for trackname in inst_samples:
            with open(self.get_instrument_filename(trackname), "w") as _out:
                if self.check_full.isChecked():
                    log('calling print_instrument_full with args {} '
                        '{} {}'.format(trackname, options, _out))
                    self.loaded.print_instrument_full(trackname, options, _out=_out)
                else:
                    log('calling print_instrument with args {} '
                        '{}'.format(trackname, _out))
                    self.loaded.print_instrument(trackname, _out)

    def process_rppfile(self):
        """Create output for Reaper project

        this is assuming I only have projects that use MIDI data
        where drums are in a separate track instead of one drum per track
        """
        with open(self.get_general_filename(), 'w') as _out:
            self.loaded.print_general_data(self.check_full.isChecked(), _out)
        # kijken of er dubbele namen zijn
        test, dubbel = set(), set()
        for trackno, data in self.loaded.instruments.items():
            if data in test:
                dubbel.add(data)
            else:
                test.add(data)
        self.loaded.prepare_print_instruments()
        options = (self.max_events.value(), self.check_nonempty.isChecked())
        if self.check_allinone.isChecked():
            inst_list = list_items(self.list_samples)
            inst_list += [x.rsplit(' ', 1)[0] for x in list_items(self.mark_samples)]
            with open(self.get_general_filename(), 'a') as _out:
                self.loaded.print_all_instruments_full(inst_list, options, _out)
            return
        for trackno, data in self.loaded.instruments.items():
            name = data
            if name in dubbel:
                name += '-' + str(trackno)
            with open(self.get_instrument_filename(name), 'w') as _out:
                if self.check_full.isChecked():
                    unlettered = self.loaded.print_instrument_full(trackno,
                                                                   options,
                                                                   _out)
                else:
                    unlettered = self.loaded.print_instrument(trackno, _out)
            if unlettered:
                qtw.QMessageBox.information(self, self.title, '\n'.join(unlettered))

    def process_xmfile(self):
        """create output for eXtended Module
        """
        drums = []
        nondrums = []
        samples, letters, printseq = self._assigned
        samples_2 = [self.list_samples.item(x).text().split()[0] for x in range(
            len(self.list_samples))]

        for num, name in enumerate(self.loaded.samplenames):
            name = name[1]
            if name in samples:
                ix = samples.index(name)
                drums.append((num + 1, letters[ix]))
            elif name in samples_2:
                ix = samples_2.index(name)
                nondrums.append((num + 1, name))

        with open(self.get_general_filename(), "w") as out:
            if drums:
                self.loaded.print_general_data(drums, self.check_full.isChecked(),
                                               out)
            else:
                self.loaded.print_general_data(full=self.check_full.isChecked(),
                                               _out=out)
        self.loaded.prepare_print_instruments(nondrums)
        self.loaded.prepare_print_drums(printseq)
        options = (self.max_events.value(), self.check_nonempty.isChecked())
        if self.check_allinone.isChecked():
            with open(self.get_general_filename(), 'a') as _out:
                nondrums = [(x + 1, y) for x, y in enumerate(
                    list_items(self.list_samples))]
                self.loaded.print_all_instruments_full(nondrums, printseq, options,
                                                       _out)
            return
        if drums:
            with open(self.get_drums_filename(), "w") as out:
                if self.check_full.isChecked():
                    ## self.loaded.print_drums_full(drums, printseq, options, out)
                    self.loaded.print_drums_full(printseq, options, out)
                else:
                    ## self.loaded.print_drums(drums, printseq, out)
                    self.loaded.print_drums(printseq, out)
        for number, name in nondrums:
            with open(self.get_instrument_filename(name), "w") as out:
                if self.check_full.isChecked():
                    self.loaded.print_instrument_full(number, options, out)
                else:
                    self.loaded.print_instrument(number, out)

    @waiting_cursor
    def do_creation(self):
        """create output file(s)
        """
        msg = ''
        if not self.loaded:
            msg = 'Please load a module first'
        if not msg:
            msg = self.check_letter_assignment()
        if msg:
            qtw.QMessageBox.information(self, self.title, msg)
            return

        pathlib.Path(self.newdir).mkdir(exist_ok=True)
        self.dts = datetime.datetime.today().strftime('%Y%m%d%H%M%S')

        go_dict = {'mod': self.process_modfile,
                   'mid': self.process_midifile,
                   'xm': self.process_xmfile,
                   'med': self.process_medfile,
                   'mmp': self.process_mmpfile,
                   'mmpz': self.process_mmpfile,
                   'rpp': self.process_rppfile}
        go_dict[self.ftype]()


def main():
    "main function"
    app = qtw.QApplication(sys.argv)
    win = MainFrame(app)
    sys.exit(app.exec_())
