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
        self.create_widgets()

    def create_widgets(self):

        vbox = qtw.QVBoxLayout()

        hbox = qtw.QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(qtw.QLabel("Select module file:", self))
        self.vraag_modfile = qtw.QComboBox(self)
        self.vraag_modfile.setEditable(True)
        self.vraag_modfile.addItems([x for x  in self._mru_items])
        self.vraag_modfile.setEditText(self.filenaam)
        hbox.addWidget(self.vraag_modfile)
        zoek_button = qtw.QPushButton("&Browse", self)
        zoek_button.clicked.connect(self.zoekfile)
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
        hbox.addWidget(qtw.QLabel("Mark Drum Samples:", self))

        self.list_samples = qtw.QListWidget(self)
        self.list_samples.setSelectionMode(qtw.QAbstractItemView.ExtendedSelection)
        hbox.addWidget(self.list_samples)

        col = qtw.QVBoxLayout()
        col.addStretch()
        move_button = qtw.QPushButton('->', self)
        move_button.clicked.connect(self.move_to_right)
        col.addWidget(move_button)
        back_button = qtw.QPushButton('<-', self)
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
        col.addStretch()
        hbox.addLayout(col)
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
        quit_button.clicked.connect(self.close)
        hbox.addWidget(quit_button)
        hbox.addStretch()
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        self.vraag_modfile.setFocus()

        self.show()

    def zoekfile(self, *args):
        """event handler voor 'zoek in directory'"""
        oupad = self.vraag_modfile.currentText()
        if oupad == "":
             oupad = '/home/albert/magiokis/data/mod'
        ## if oupad.endswith('.mod'):
            ## dir_, name = os.path.split(oupad)
        ## else:
            ## dir_, name = oupad, ''
        name, pattern = qtw.QFileDialog.getOpenFileName(self, "Open File", oupad,
            "Mod files (*.mod)")
        if name != "":
            self.vraag_modfile.setEditText(name)
            self.vraag_modfile.addItem(name)
            self._mru_items.add(name)

    def load_module(self, *args):
        pad = self.vraag_modfile.currentText()
        if not pad:
            qtw.QMessageBox.information(self, 'Oops', 'You need to provide a '
                'filename')
            return
        self.loaded = modreader.ModFile(pad)
        self.nondrums = [x[0] for x in self.loaded.samples.values() if x[0]]
        self.list_samples.clear()
        self.list_samples.addItems(self.nondrums)
        self.drums = []
        self.mark_samples.clear()
        ## print('initial:')
        ## print(self.nondrums)
        ## print(self.drums)

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
            ## self.drums.append(item)
            ## self.nondrums.remove(item)
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
            ## self.nondrums.append(item)
            ## self.drums.remove(item)
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
        inst = selected[0].text().split()[0]
        text, ok = qtw.QInputDialog.getText(self, 'ModReaderGui',
            'Enter letter(s) to be printed for "{}"'.format(inst))
        if ok and text:
            inst += " ({})".format(text)
            selected[0].setText(inst)

        ## selindx = selected[0]
        ## self._text = ""
        ## w = AskString(self, prompt='Enter letter(s) to be printed for "{}"'.format(
            ## self.drums[selindx]))
        ## w.focus_set()
        ## w.grab_set()
        ## w.wait_window()
        ## if self._text:
            ## inst = self.drums[selindx].split()[0]
            ## inst += " ({})".format(self._text)
            ## self.mark_samples.delete(selindx)
            ## self.mark_samples.insert(selindx, inst)
            ## self.drums[selindx] = inst
        ## print('after assign:', self.drums)


    def create_files(self):
        if not self.loaded:
            qtw.QMessageBox.information(self, 'Oops', 'Please load a module first')
            return
        samples, letters = [], []
        all_item_texts = [self.mark_samples.item(x).text() for x in range(len(
            self.mark_samples))]
        try:
            ## for x, y in [z.text().split(None, 1) for z in self.mark_samples.items()]:
            for x, y in [z.split(None, 1) for z in all_item_texts]:
                samples.append(x)
                letters.append(y[1:-1])
        except ValueError:
            qtw.QMessageBox.information(self, 'Oops', 'Please assign letters '
                'to *all* drumtracks')
            return
        self.drums = [''] * len(self.mark_samples)
        self.nondrums = [''] * len(self.list_samples)
        printseq = "".join([x for x in letters if len(x) == 1])
        samples_2 = [self.list_samples.item(x).text().split()[0] for x in range(
            len(self.list_samples))]
        for num, data in self.loaded.samples.items():
            if data[0] in samples:
                ix = samples.index(data[0])
                self.drums[ix] = (num + 1, letters[ix])
            elif data[0] in samples_2:
                ix = samples_2.index(data[0])
                self.nondrums[ix] = (num + 1, data[0])
        pad = self.vraag_modfile.currentText()
        newdir = os.path.splitext(pad)[0]
        try:
            os.mkdir(newdir)
        except FileExistsError:
            pass
        datetimestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
        with open(os.path.join(newdir, '{}-general'.format(datetimestamp)),
                "w") as out:
            self.loaded.print_module_details(out)
        if self.drums:
            with open(os.path.join(newdir, '{}-drums'.format(datetimestamp)),
                    "w") as out:
                self.loaded.print_drums(self.drums, printseq, out)
        for number, name in self.nondrums:
            with open(os.path.join(newdir, '{}-{}'.format(datetimestamp, name)),
                    "w") as out:
                self.loaded.print_instrument(number, out)
        qtw.QMessageBox.information(self, 'Yay', 'Done')

    def close(self, *args):
        with open('mru_files', 'w') as _out:
            for name in self._mru_items:
                _out.write(name + '\n')
        super().close()

app = qtw.QApplication(sys.argv)
win = MainFrame()
sys.exit(app.exec_())
