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
import os.path
import datetime
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkFileDialog
import tkinter.messagebox as tkMessageBox
import modreader


class AskString(tk.Toplevel):
    "Ask for text input"

    def __init__(self, parent, prompt='Enter some text:'):
        self.parent = parent
        super().__init__()
        frm = tk.Frame(self)
        frm.pack(fill="both", expand=True, side="top")
        tk.Label(frm, text=prompt).pack(side="top")
        self.text = tk.Entry(frm)
        self.text.pack(side="top")
        bbar = tk.Frame(frm)
        bbar.pack(fill="both", expand=True, side="top")
        tk.Label(bbar, text="").pack(side="left")
        ok_button = tk.Button(bbar, text="Ok", command=self.einde)
        ok_button.pack(side="left", padx=5, pady=5)
        ok_button.bind("<Return>", self.einde)
        ## self.bind("<Ctrl+Return>", self.einde)
        cancel_button = tk.Button(bbar, text="Cancel", command=self.destroy)
        cancel_button.pack(side="left", padx=5, pady=5)
        cancel_button.bind("<Return>", self.destroy)
        ## self.bind("<Escape>", self.destroy)
        tk.Label(bbar, text="").pack(side="left")

    def einde(self):
        self.parent.text_ = self.text.get()
        self.destroy()


class Application(tk.Frame):

    def __init__(self, master=None):
        super().__init__(master)
        self.pack()
        self._mru_items = set()
        self.loaded = None
        self.drums = []
        self.nondrums = []
        try:
            with open('mru_files') as _in:
                for line in _in:
                    if line.strip():
                        self._mru_items.add(line.strip())
        except FileNotFoundError:
            pass
        self.create_widgets()

    def create_widgets(self):

        # select filename stuff
        frm = tk.Frame(self)
        frm.pack(fill="both", expand=True, side="top")
        tk.Label(frm, text="Select module file:", width=17).pack(side="left")
        self.filenaam = tk.StringVar()
        self.vraag_modfile = ttk.Combobox(frm, width=40)
        self.vraag_modfile['values'] = [x for x in self._mru_items]
        self.vraag_modfile['textvariable'] = self.filenaam
        self.vraag_modfile.pack(side=tk.LEFT, padx=5, pady=5)
        zoek_button = tk.Button(frm, text="Browse", command=self.zoekfile,
                                underline=0)
        zoek_button.pack(side=tk.LEFT, padx=5)
        zoek_button.bind('<Return>', self.zoekfile)
        self.bind_all('<Alt-KeyPress-B>', self.zoekfile)
        tk.Label(frm, text="").pack(side=tk.RIGHT)

        load_button = tk.Button(self)
        load_button["text"] = "Load module"
        load_button["command"] = self.load_module
        load_button["underline"] = 0
        load_button.pack(side="top")
        load_button.bind('<Return>', self.load_module)
        self.bind_all('<Alt-KeyPress-L>', self.load_module)

        frm = tk.Frame(self)
        frm.pack(fill="both", expand=True, side="top")
        tk.Label(frm, text="Mark Drum Samples:", width=17).pack(side="left")
        self.sample_list = tk.StringVar()
        self.list_samples = tk.Listbox(frm, listvariable=self.sample_list,
                                       exportselection=False)
        self.list_samples['selectmode'] = 'extended'
        self.list_samples.pack(side="left")

        frm2 = tk.Frame(frm)
        frm2.pack(expand=True, side="left")
        move_button = tk.Button(frm2)
        move_button['text'] = '->'
        move_button['command'] = self.move_to_right
        move_button.pack()
        move_button.bind('<Return>', self.move_to_right)
        self.bind_all('<Alt-KeyPress-Right>', self.move_to_right)
        back_button = tk.Button(frm2)
        back_button['text'] = '<-'
        back_button['command'] = self.move_to_left
        back_button.pack()
        back_button.bind('<Return>', self.move_to_left)
        self.bind_all('<Alt-KeyPress-Left>', self.move_to_left)
        self.sample_marks = tk.StringVar()
        self.mark_samples = tk.Listbox(frm, listvariable=self.sample_marks,
                                       exportselection=False)
        self.mark_samples['selectmode'] = 'extended'
        self.mark_samples.pack(side="left")

        frm2 = tk.Frame(frm)
        frm2.pack(expand=True, side="left")
        up_button = tk.Button(frm2)
        up_button['text'] = 'Move Up'
        up_button['underline'] = 5
        up_button['command'] = self.move_up
        up_button.pack()
        up_button.bind('<Return>', self.move_up)
        self.bind_all('<Alt-KeyPress-U>', self.move_up)
        self.bind_all('<Alt-KeyPress-Up>', self.move_up)
        down_button = tk.Button(frm2)
        down_button['text'] = 'Move Down'
        down_button['underline'] = 5
        down_button['command'] = self.move_down
        down_button.pack()
        down_button.bind('<Return>', self.move_down)
        self.bind_all('<Alt-KeyPress-D>', self.move_down)
        self.bind_all('<Alt-KeyPress-Down>', self.move_down)
        assign_button = tk.Button(frm2)
        assign_button['text'] = 'Assign letter'
        assign_button["underline"] = 0
        assign_button['command'] = self.assign
        assign_button.pack()
        assign_button.bind('<Return>', self.assign)
        self.bind_all('<Alt-KeyPress-A>', self.assign)

        create_button = tk.Button(self)
        create_button["text"] = "Create transcription files"
        create_button["command"] = self.create_files
        create_button["underline"] = 0
        create_button.pack(side="top")
        create_button.bind('<Return>', self.create_files)
        self.bind_all('<Alt-KeyPress-C>', self.create_files)

        quit_button = tk.Button(self, text="QUIT", fg="red", command=self.quit)
        quit_button.pack(side="top")
        back_button.bind('<Return>', self.quit)
        self.bind_all('<Control-KeyPress-Q>', self.quit)

    def zoekfile(self):
        """event handler voor 'zoek in directory'"""
        oupad = self.filenaam.get()
        if oupad == "":
            oupad = '/home/albert/magiokis/data/mod'
        if oupad.endswith('.mod'):
            dir_, name = os.path.split(oupad)
        else:
            dir_, name = oupad, ''
        pad = tkFileDialog.askopenfilename(initialdir=dir_, initialfile=name)
        if pad != "":
            self.filenaam.set(pad)
            self._mru_items.add(pad)

    def load_module(self):
        pad = self.filenaam.get()
        if not pad:
            tkMessageBox.showinfo('Oops', 'You need to provide a filename')
            return
        self.loaded = modreader.ModFile(pad)
        self.nondrums = [x[0] for x in self.loaded.samples.values() if x[0]]
        self.list_samples.delete(0, "end")
        for x in self.nondrums:
            self.list_samples.insert("end", x)
        self.drums = []
        self.mark_samples.delete(0, "end")
        ## print('initial:')
        ## print(self.nondrums)
        ## print(self.drums)

    def move_to_right(self):
        """overbrengen naar rechterlijst zodat alleen de niet-drums overblijven
        """
        selected = self.list_samples.curselection()
        if len(selected) == 0:
            tkMessageBox.showinfo('Oops', 'Please select one or more instruments')
            return
        for item in [self.nondrums[x] for x in selected]:
            self.mark_samples.insert("end", item)
            self.drums.append(item)
            self.nondrums.remove(item)
        for index in reversed(selected):
            self.list_samples.delete(index)
        ## print('after move to right:')
        ## print(self.nondrums)
        ## print(self.drums)

    def move_to_left(self):
        """overbrengen naar linkerlijst (om alleen drumsamples over te houden)
        """
        selected = self.mark_samples.curselection()
        if len(selected) == 0:
            tkMessageBox.showinfo('Oops', 'Please select one or more instruments')
            return
        for item in [self.drums[x] for x in selected]:
            self.list_samples.insert("end", item)
            self.nondrums.append(item)
            self.drums.remove(item)
        for index in reversed(selected):
            self.mark_samples.delete(index)
        ## print('after move to left:')
        ## print(self.nondrums)
        ## print(self.drums)

    def move_up(self):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.mark_samples.curselection()
        msg = ''
        if len(selected) == 0:
            msg = 'Please select one or more instruments'
        elif len(selected) > 1:
            msg = 'One at a time, please (for now)'
        if msg:
            tkMessageBox.showinfo('Oops', msg)
            return
        ## print('\ninitial:', self.drums)
        selindx = selected[0]
        if selindx > 0:
            self.mark_samples.delete(selindx)
            item = self.drums.pop(selindx)
            self.drums.insert(selindx - 1, item)
            self.mark_samples.insert(selindx - 1, item)
        ## print('after move down:', self.drums)

    def move_down(self):
        """entry verplaatsen voor realiseren juiste volgorde
        """
        selected = self.mark_samples.curselection()
        msg = ''
        if len(selected) == 0:
            msg = 'Please select one or more instruments'
        elif len(selected) > 1:
            msg = 'One at a time, please (for now)'
        if msg:
            tkMessageBox.showinfo('Oops', msg)
            return
        ## print('\ninitial:', self.drums)
        selindx = selected[0]
        if selindx < len(self.drums) - 1:
            self.mark_samples.delete(selindx)
            item = self.drums.pop(selindx)
            self.drums.insert(selindx + 1, item)
            self.mark_samples.insert(selindx + 1, item)
        ## print('after move down:', self.drums)

    def assign(self):
        """letter toekennen voor in display
        """
        selected = self.mark_samples.curselection()
        msg = ''
        if len(selected) == 0:
            msg = 'Please select an instrument'
        elif len(selected) > 1:
            msg = 'One at a time, please'
        if msg:
            tkMessageBox.showinfo('Oops', msg)
            return
        ## print('\ninitial:', self.drums)
        selindx = selected[0]
        self.text_ = ""
        win = AskString(self, prompt='Enter letter(s) to be printed for "{}"'.format(
            self.drums[selindx]))
        win.focus_set()
        win.grab_set()
        win.wait_window()
        if self.text_:
            inst = self.drums[selindx].split()[0]
            inst += " ({})".format(self.text_)
            self.mark_samples.delete(selindx)
            self.mark_samples.insert(selindx, inst)
            self.drums[selindx] = inst
        ## print('after assign:', self.drums)

    def create_files(self):
        if not self.loaded:
            tkMessageBox.showinfo('Oops', 'Please load a module first')
            return
        samples, letters = [], []
        try:
            for x, y in [z.split(None, 1) for z in self.drums]:
                samples.append(x)
                letters.append(y[1:-1])
        except ValueError:
            tkMessageBox.showinfo('Oops', 'Please assign letters to all drumtracks')
            return
        printseq = "".join([x for x in letters if len(x) == 1])
        samples_2 = [x.split()[0] for x in self.nondrums if x]
        for num, data in self.loaded.samples.items():
            if data[0] in samples:
                ix = samples.index(data[0])
                self.drums[ix] = (num + 1, letters[ix])
            elif data[0] in samples_2:
                ix = samples_2.index(data[0])
                self.nondrums[ix] = (num + 1, data[0])
        pad = self.filenaam.get()
        newdir = os.path.splitext(pad)[0]
        try:
            os.mkdir(newdir)
        except FileExistsError:
            pass
        datetimestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
        with open(os.path.join(newdir, '{}-basic'.format(datetimestamp)),
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
        tkMessageBox.showinfo('Yay', 'Done')

    def quit(self):
        with open('mru_files', 'w') as _out:
            for name in self._mru_items:
                _out.write(name + '\n')
        root.destroy()

root = tk.Tk()
app = Application(master=root)
app.mainloop()
