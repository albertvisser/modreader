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

class MainFrame(qtw.QWidget):

    def __init__(self, parent=None):
        super().__init__()
        self._mru_items = set()
        self.loaded = None
        self.drums = []
        self.nondrums = []
        self.filenaam = ''
        try:
            with open('mru_files') as _in:
                for line in _in:
                    if line.strip():
                        self._mru_items.add(line.strip())
        except FileNotFoundError:
            pass
        # this should enable tabbing, but apparently it doesn't?
        self.setFocusPolicy(core.Qt.StrongFocus)
        self.create_widgets()

    def create_widgets(self):

        vbox = qtw.QVBoxLayout()

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(qtw.QLabel("Select module file:", self))
        self.ask_modfile = qtw.QComboBox(self)
        self.ask_modfile.setEditable(True)
        self.ask_modfile.addItems([x for x  in self._mru_items])
        self.ask_modfile.setEditText(self.filenaam)
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

        act = qtw.QAction('Move to right', self)
        act.setShortcut('Ctrl+Right')
        act.triggered.connect(self.move_to_right)
        self.addAction(act)
        act = qtw.QAction('Move to left', self)
        act.setShortcut('Ctrl+Left')
        act.triggered.connect(self.move_to_left)
        self.addAction(act)

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

        act = qtw.QAction('Move Up', self)
        act.setShortcut('Ctrl+Up')
        act.triggered.connect(self.move_up)
        self.addAction(act)
        act = qtw.QAction('Move Down', self)
        act.setShortcut('Ctrl+Down')
        act.triggered.connect(self.move_down)
        self.addAction(act)
        act = qtw.QAction('Assign/Edit', self)
        act.setShortcut('F2')
        act.triggered.connect(self.assign)
        self.addAction(act)
        act = qtw.QAction('Remove', self)
        act.setShortcut('Del')
        act.triggered.connect(self.remove)
        self.addAction(act)

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

        act = qtw.QAction('Enter filename', self)
        act.setShortcut('Ctrl+Home')
        act.triggered.connect(self.activate_filename)
        self.addAction(act)
        act = qtw.QAction('Open', self)
        act.setShortcut('Ctrl+F')
        act.triggered.connect(self.find_file)
        self.addAction(act)
        act = qtw.QAction('Load', self)
        act.setShortcut('Ctrl+O')
        act.triggered.connect(self.load_module)
        self.addAction(act)
        act = qtw.QAction('Left-activate', self)
        act.setShortcut('Ctrl+L')
        act.triggered.connect(self.activate_left)
        self.addAction(act)
        act = qtw.QAction('Right-activate', self)
        act.setShortcut('Ctrl+R')
        act.triggered.connect(self.activate_right)
        self.addAction(act)
        act = qtw.QAction('Save', self)
        act.setShortcut('Ctrl+S')
        act.triggered.connect(self.create_files)
        self.addAction(act)
        act = qtw.QAction('Help', self)
        act.setShortcut('F1')
        act.triggered.connect(self.help)
        self.addAction(act)
        act = qtw.QAction('Quit', self)
        act.setShortcut('Ctrl+Q')
        act.triggered.connect(self.exit)
        self.addAction(act)

        self.setLayout(vbox)
        self.ask_modfile.setFocus()

        self.show()

    def activate_filename(self, *args):
        self.ask_modfile.setFocus(True)

    def find_file(self, *args):
        """event handler voor 'zoek in directory'"""
        oupad = self.ask_modfile.currentText()
        if oupad == "":
             oupad = '/home/albert/magiokis/data/mod'
        name, pattern = qtw.QFileDialog.getOpenFileName(self, "Open File", oupad,
            "Mod files (*.mod)")
        if name != "" and name != oupad:
            self.ask_modfile.setEditText(name)
            if name not in self._mru_items:
                self._mru_items.add(name)
                self.ask_modfile.addItem(name)
            self.list_samples.clear()
            self.mark_samples.clear()

    def load_module(self, *args):
        pad = self.ask_modfile.currentText()
        if not pad:
            qtw.QMessageBox.information(self, 'Oops', 'You need to provide a '
                'filename')
            return
        self.loaded = modreader.ModFile(pad)
        self.nondrums = [x[0] for x in self.loaded.samples.values() if x[0]]
        self.list_samples.clear()
        self.list_samples.addItems(self.nondrums)
        self.mark_samples.clear()
        self.drums = []
        ## print('initial:')
        ## print(self.nondrums)
        ## print(self.drums)

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

    def move_to_right(self, *args):
        """overbrengen naar rechterlijst zodat alleen de niet-drums overblijven
        """
        selected = self.list_samples.selectedItems()
        if len(selected) == 0:
            qtw.QMessageBox.information(self, 'Oops', 'Please select one or more '
                'instruments')
            return
        templist = []
        for item in reversed(selected):
            id = self.list_samples.row(item)
            it = self.list_samples.takeItem(id)
            templist.insert(0, it)
        for item in templist:
            self.mark_samples.addItem(item)
            self.mark_samples.setCurrentItem(item)
            item.setSelected(True)
            ## self.drums.append(item)
            ## self.nondrums.remove(item)
        self.mark_samples.setFocus(True)
        ## print('after move to right:')
        ## print(self.nondrums)
        ## print(self.drums)

    def move_to_left(self, *args):
        """overbrengen naar linkerlijst (om alleen drumsamples over te houden)
        """
        selected = self.mark_samples.selectedItems()
        if len(selected) == 0:
            qtw.QMessageBox.information(self, 'Oops', 'Please select one or more '
                'instruments')
            return
        templist = []
        for item in reversed(selected):
            id = self.mark_samples.row(item)
            it = self.mark_samples.takeItem(id)
            templist.insert(0, it)
        for item in selected:
            self.list_samples.addItem(item)
            self.list_samples.setCurrentItem(item)
            item.setSelected(True)
            ## self.nondrums.append(item)
            ## self.drums.remove(item)
        self.list_samples.setFocus(True)
        ## print('after move to left:')
        ## print(self.nondrums)
        ## print(self.drums)

    def move_up(self, *args):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.mark_samples.selectedItems()
        msg = ''
        if len(selected) == 0:
            msg = 'Please select one or more instruments'
        elif len(selected) > 1:
            msg = 'One at a time, please (for now)'
        if msg:
            qtw.QMessageBox.information(self, 'Oops', msg)
            return
        ## print('\ninitial:', self.drums)
        selindx = self.mark_samples.row(selected[0])
        if selindx > 0:
            item = self.mark_samples.takeItem(selindx)
            ## item = self.drums.pop(selindx)
            ## self.drums.insert(selindx - 1, item)
            self.mark_samples.insertItem(selindx - 1, item)
            item.setSelected(True)
            self.mark_samples.scrollToItem(item)
        ## print('after move down:', self.drums)

    def move_down(self, *args):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.mark_samples.selectedItems()
        msg = ''
        if len(selected) == 0:
            msg = 'Please select one or more instruments'
        elif len(selected) > 1:
            msg = 'One at a time, please (for now)'
        if msg:
            qtw.QMessageBox.information(self, 'Oops', msg)
            return
        ## print('\ninitial:', self.drums)
        selindx = self.mark_samples.row(selected[0])
        ## if selindx < len(self.drums) - 1:
        if selindx < len(self.mark_samples) - 1:
            item = self.mark_samples.takeItem(selindx)
            ## item = self.drums.pop(selindx)
            ## self.drums.insert(selindx + 1, item)
            self.mark_samples.insertItem(selindx + 1, item)
            item.setSelected(True)
            self.mark_samples.scrollToItem(item)
        ## print('after move down:', self.drums)

    def assign(self, *args):
        """letter toekennen voor in display
        """
        selected = self.mark_samples.selectedItems()
        msg = ''
        if len(selected) == 0:
            msg = 'Please select an instrument'
        elif len(selected) > 1:
            msg = 'One at a time, please'
        if msg:
            qtw.QMessageBox.information(self, 'Oops', msg)
            return
        ## print('\ninitial:', self.drums)
        try:
            inst, data = selected[0].text().split()
        except ValueError:
            inst, data = selected[0].text(), ''
        text, ok = qtw.QInputDialog.getText(self, 'ModReaderGui',
            'Enter letter(s) to be printed for "{}"'.format(inst), text=data[1:-1])
        if ok:
            if text:
                inst += " ({})".format(text)
            selected[0].setText(inst)

    def remove(self, *args):
        selected = self.mark_samples.selectedItems()
        msg = ''
        if len(selected) == 0:
            msg = 'Please select one or more instruments'
        ## elif len(selected) > 1:
            ## msg = 'One at a time, please (for now)'
        else:
            for item in selected:
                selindex = self.mark_samples.row(item)
                if not item.text().startswith('dummy_sample ('):
                    msg = 'You can only remove dummy samples'
                    break
        if msg:
            qtw.QMessageBox.information(self, 'Oops', msg)
            return
        for item in selected:
            selindx = self.mark_samples.row(item)
            self.mark_samples.takeItem(selindx)

    def create_files(self):
        if not self.loaded:
            qtw.QMessageBox.information(self, 'Oops', 'Please load a module first')
            return

        # get all letters assigned to sample
        samples, letters = [], []
        all_item_texts = [self.mark_samples.item(x).text() for x in range(len(
            self.mark_samples))]
        try:
            for x, y in [z.rsplit(None, 1) for z in all_item_texts]:
                samples.append(x)
                letters.append(y[1:-1])
        except ValueError:
            qtw.QMessageBox.information(self, 'Oops', 'Please assign letters '
                'to *all* drumtracks')
            return

        drums = []
        nondrums = []
        printseq = "".join([x for x in letters if len(x) == 1])
        if len(printseq) != len(set(printseq)):
            qtw.QMessageBox.information(self, 'Oops', 'Please correct multiple '
                'assignments to the same letter')
            return

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
            qtw.QMessageBox.information(self, 'Oops', 'Please relocate the dummy '
                'samples so their letters are in the right position')
            return

        samples_2 = [self.list_samples.item(x).text().split()[0] for x in range(
            len(self.list_samples))]
        for num, data in self.loaded.samples.items():
            if data[0] in samples:
                ix = samples.index(data[0])
                drums.append((num + 1, letters[ix]))
            elif data[0] in samples_2:
                ix = samples_2.index(data[0])
                nondrums.append((num + 1, data[0]))

        pad = self.vraag_modfile.currentText()
        newdir = os.path.splitext(pad)[0]
        try:
            os.mkdir(newdir)
        except FileExistsError:
            pass
        datetimestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
        with open(os.path.join(newdir, '{}-general'.format(datetimestamp)),
                "w") as out:
            if drums:
                self.loaded.print_module_details(out, drums)
            else:
                self.loaded.print_module_details(out)
        if drums:
            with open(os.path.join(newdir, '{}-drums'.format(datetimestamp)),
                    "w") as out:
                self.loaded.print_drums(drums, printseq, out)
        for number, name in nondrums:
            with open(os.path.join(newdir, '{}-{}'.format(datetimestamp, name)),
                    "w") as out:
                self.loaded.print_instrument(number, out)
        qtw.QMessageBox.information(self, 'Yay', 'Done')

    def help(self, *args):
        qtw.QMessageBox.information(self, 'Keyboard Shortcuts', '\n'.join((
            'Use Alt with the underscored letters or',
            'Ctrl-Home\tto\tActivate filename field',
            'Ctrl-F\tfor\tFile selection',
            'Ctrl-O\t\tLoad indicated module',
            'Ctrl-L\t\tActivate left listbox',
            'Ctrl-right\t\tMove sample to right listbox',
            'Ctrl-R\t\tActivate right listbox',
            'Ctrl-left\t\tMove sample to left listbox',
            'Ctrl-Up\t\tMove sample up in left list',
            'Ctrl-Down\t\tMove sample down in left list',
            'F2\t\tAssign letter(s) to sample',
            'Del\t\tDelete dummy sample',
            'Ctrl-S\t\tCreate transcription files',
            'Ctrl-Q\t\tQuit the application',
            'F1\t\tShow this screen',
            )))

    def exit(self, *args):
        with open('mru_files', 'w') as _out:
            for name in self._mru_items:
                _out.write(name + '\n')
        pass # built in delay to avoid segfault
        self.close()

app = qtw.QApplication(sys.argv)
win = MainFrame()
sys.exit(app.exec_())
