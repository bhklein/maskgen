from Tkinter import *
import pandastable
import pandas
import ttk
import tkFileDialog
import tkMessageBox
import numpy as np
from hp_data import *


class KeywordsSheet(pandastable.Table):
    def __init__(self, dir, master=None, oldImageNames=[], newImageNames=[]):
        pandastable.Table.__init__(self, master)
        self.oldImageNames = oldImageNames
        self.newImageNames = newImageNames
        self.dir = dir
        self.master = master
        self.master.title(self.dir)
        self.saveState = True
        master.protocol("WM_DELETE_WINDOW", self.check_save)
        master.bind("<Key>", self.keypress)
        self.open_spreadsheet()

    def keypress(self, event):
        self.saveState = False

    def open_spreadsheet(self):
        self.keywordsCSV = None
        for f in os.listdir(self.dir):
            if f.endswith('.csv') and 'keywords' in f:
                self.keywordsCSV = os.path.join(self.dir, f)
        if self.keywordsCSV == None:
            self.keywordsCSV = self.createKeywordsCSV()

        self.pt = pandastable.Table(self.master)
        self.pt.show()
        self.pt.importCSV(self.keywordsCSV)

        menubar = Menu(self)
        menubar.add_command(label='Save', command=self.__exportCSV)
        menubar.add_command(label='Fill Down', command=self.__fill_down)
        menubar.add_command(label='Validate', command = self.__validate)
        menubar.add_command(label='Add column', command=self.__add_column)
        self.master.config(menu=menubar)


    def createKeywordsCSV(self):
        keywordsName = os.path.join(self.dir, datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + 'keywords.csv')
        if not os.path.exists(keywordsName):
            with open(keywordsName, 'wb') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(['Old Filename', 'New Filename', 'Keyword1', 'Keyword2', 'Keyword3'])
                for im in range(0, len(self.newImageNames)):
                    writer.writerow([os.path.basename(self.oldImageNames[im]), os.path.basename(self.newImageNames[im])] + ['']*3)

        return keywordsName

    def __exportCSV(self, showErrors=True):
        self.pt.redraw()
        if showErrors:
            self.__validate()
        self.pt.doExport(self.keywordsCSV)
        tmp = self.keywordsCSV + '-tmp.csv'
        with open(self.keywordsCSV, "rb") as source:
            rdr = csv.reader(source)
            with open(tmp, "wb") as result:
                wtr = csv.writer(result)
                for r in rdr:
                    wtr.writerow((r[1:]))
        os.remove(self.keywordsCSV)
        os.rename(tmp, self.keywordsCSV)
        tkMessageBox.showinfo('Status', 'Saved!')


    def __fill_down(self):
        selection = self.pt.getSelectionValues()
        cells = self.pt.getSelectedColumn
        rowList = range(cells.im_self.startrow, cells.im_self.endrow + 1)
        colList = range(cells.im_self.startcol, cells.im_self.endcol + 1)
        for row in rowList:
            for col in colList:
                self.pt.model.setValueAt(selection[0][0],row,col)
        self.pt.redraw()

    def __validate(self):
        try:
            keysFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'ImageKeywords.csv')
            with open(keysFile) as keys:
                keywords = keys.readlines()
        except IOError:
            tkMessageBox.showwarning('Warning', 'Keywords reference not found!')
            return

        keywords = [x.strip() for x in keywords]
        errors = []
        for row in range(0, self.pt.rows):
            for col in range(2, self.pt.cols):
                val = str(self.pt.model.getValueAt(row, col))
                if val != 'nan' and val != '' and val not in keywords:
                    errors.append('Invalid keyword for ' + str(self.pt.model.getValueAt(row, 0)) + ' (Row ' + str(row+1) + ', Keyword ' + str(col-1) + ', Value: ' + val + ')')

        if errors:
            ErrorWindow(errors).show_errors()
        else:
            tkMessageBox.showinfo('Spreadsheet Validation', 'Nice work! All entries are valid.')

    def __add_column(self):
        numCols = self.pt.cols
        new = np.empty(self.pt.rows)
        new[:] = np.NAN
        self.pt.model.df['Keyword ' + str(self.pt.cols - 1)] = pd.Series(new, index=self.pt.model.df.index)
        self.pt.redraw()

    def check_save(self):
        if self.saveState == False:
            message = 'Would you like to save before closing this sheet?'
            confirm = tkMessageBox.askyesnocancel(title="Save On Close", message=message, default=tkMessageBox.YES)
            if confirm:
                errs = self.__exportCSV(showErrors=False)
                if not errs:
                    self.master.destroy()
            elif confirm is None:
                pass
            else:
                self.master.destroy()
        else:
            self.master.destroy()


class ErrorWindow(Toplevel):
    def __init__(self, errors, master=None):
        Toplevel.__init__(self, master)
        self.wm_title('Spreadsheet Validation')
        self.errors = errors

    def show_errors(self):
        scrollbar = Scrollbar(self)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Listbox(self, width=80)
        listbox.pack()

        for i in self.errors:
            listbox.insert(END, i)

        # attach listbox to scrollbar
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)


class HPSpreadsheet(pandastable.Table):
    def __init__(self, dir, master=None):
        pandastable.Table.__init__(self, master)
        self.dir = dir
        self.master = master
        self.master.title(self.dir)
        self.saveState = True
        master.protocol("WM_DELETE_WINDOW", self.check_save)
        master.bind("<Key>", self.keypress)
        self.open_spreadsheet()

    def keypress(self, event):
        self.saveState = False

    def open_spreadsheet(self):
        self.ritCSV = None
        for f in os.listdir(self.dir):
            if f.endswith('.csv') and 'rit' in f:
                self.ritCSV = os.path.join(self.dir, f)

        self.pt = pandastable.Table(self.master)
        self.pt.show()
        self.pt.importCSV(self.ritCSV)
        self.original = self.pt.model.df

        self.obfiltercol = self.pt.model.df.columns.get_loc('HP-OnboardFilter')
        self.reflectionscol = self.pt.model.df.columns.get_loc('Reflections')
        self.shadcol = self.pt.model.df.columns.get_loc('Shadows')
        self.modelcol = self.pt.model.df.columns.get_loc('CameraModel')
        self.hdrcol = self.pt.model.df.columns.get_loc('HP-HDR')

        self.color_code_cells()

        menubar = Menu(self)
        menubar.add_command(label='Save', command=self.__exportCSV)
        menubar.add_command(label='Fill Down', command=self.__fill_down)
        menubar.add_command(label='Validate', command=self.__validate)
        self.master.config(menu=menubar)

    def color_code_cells(self):
        notnans = self.pt.model.df.notnull()
        redcols = [self.obfiltercol, self.reflectionscol, self.shadcol, self.modelcol, self.hdrcol]
        for row in range(0, self.pt.rows):
            for col in range(0, self.pt.cols):
                x1, y1, x2, y2 = self.pt.getCellCoords(row, col)
                if col in redcols :
                    rect = self.pt.create_rectangle(x1, y1, x2, y2,
                                                    fill='#ff5b5b',
                                                    outline='#084B8A',
                                                    tag='cellrect')
                else:
                    x1, y1, x2, y2 = self.pt.getCellCoords(row, col)
                    if notnans.iloc[row, col]:
                        rect = self.pt.create_rectangle(x1, y1, x2, y2,
                                                     fill='#c1c1c1',
                                                     outline='#084B8A',
                                                     tag='cellrect')
                self.pt.lift('cellrect')
        self.pt.redraw()

    def __exportCSV(self, showErrors=True):
        self.pt.redraw()
        if showErrors:
            self.__validate()
        self.pt.doExport(self.ritCSV)
        tmp = self.ritCSV + '-tmp.csv'
        with open(self.ritCSV, "rb") as source:
            rdr = csv.reader(source)
            with open(tmp, "wb") as result:
                wtr = csv.writer(result)
                for r in rdr:
                    wtr.writerow((r[1:]))
        os.remove(self.ritCSV)
        os.rename(tmp, self.ritCSV)
        self.saveState = True
        tkMessageBox.showinfo('Status', 'Saved!')


    def __fill_down(self):
        selection = self.pt.getSelectionValues()
        cells = self.pt.getSelectedColumn
        rowList = range(cells.im_self.startrow, cells.im_self.endrow + 1)
        colList = range(cells.im_self.startcol, cells.im_self.endcol + 1)
        for row in rowList:
            for col in colList:
                self.pt.model.setValueAt(selection[0][0],row,col)
        self.pt.redraw()

    def __validate(self):
        errors = []
        booleanCols = [self.obfiltercol, self.reflectionscol, self.shadcol, self.hdrcol]
        for col in range(0, self.pt.cols):
            if col in booleanCols:
                for row in range(0, self.pt.rows):
                    val = str(self.pt.model.getValueAt(row, col))
                    if val.title() == 'True' or val.title() == 'False':
                        self.pt.model.setValueAt(val.title(), row, col)
                    else:
                        currentColName = list(self.pt.model.df.columns.values)[col]
                        errors.append('Invalid entry at column ' + currentColName + ', row ' + str(row + 1) + '. Value must be True or False')

        if errors:
            ErrorWindow(errors).show_errors()

        return errors

    def check_save(self):
        if self.saveState == False:
            message = 'Would you like to save before closing this sheet?'
            confirm = tkMessageBox.askyesnocancel(title="Save On Close", message=message, default=tkMessageBox.YES)
            if confirm:
                errs = self.__exportCSV(showErrors=False)
                if not errs:
                    self.master.destroy()
            elif confirm is None:
                pass
            else:
                self.master.destroy()
        else:
            self.master.destroy()

class HPGUI(Frame):

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.grid()
        self.oldImageNames = []
        self.newImageNames = []
        self.createWidgets()

    def load_input(self):
        d = tkFileDialog.askdirectory(initialdir=os.path.expanduser('~'))
        self.inputdir.delete(0, 'end')
        self.inputdir.insert(0, d)

    def load_output(self):
        d = tkFileDialog.askdirectory(initialdir=os.path.expanduser('~'))
        self.outputdir.delete(0, 'end')
        self.outputdir.insert(0, d)

    def select_metadatafile(self):
        f = tkFileDialog.askopenfilename()
        self.metadatafilename.delete(0, 'end')
        self.metadatafilename.insert(0,f)

    def select_preferencesfile(self):
        f = tkFileDialog.askopenfilename()
        self.prefsfilename.delete(0, 'end')
        self.prefsfilename.insert(0,f)

    def preview_filename(self):
        prefs = parse_prefs(self.prefsfilename.get())
        testNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                    prefs['organization'] + prefs['username'] + '-' + prefs['seq']
        if self.additionalinfo.get():
            testNameStr += '-' + self.additionalinfo.get()
        tkMessageBox.showinfo('Filename Preview', testNameStr)


    def go(self):
        shortFields = ['collReq', 'localcam', 'locallens', 'hd']
        kwargs = {'preferences':self.prefsfilename.get(),
                  'metadata':self.metadatafilename.get(),
                  'imgdir':self.inputdir.get(),
                  'outputdir':self.outputdir.get(),
                  'recursive':self.recBool.get(),
                  'additionalInfo':self.additionalinfo.get(),
                  }
        for fieldNum in xrange(len(shortFields)):
            kwargs[shortFields[fieldNum]] = self.attributes[self.descriptionFields[fieldNum]].get()


        (self.oldImageNames, self.newImageNames) = process(**kwargs)
        aSheet = Toplevel(self)
        sheet = HPSpreadsheet(os.path.join(self.outputdir.get(), 'csv'), master=aSheet)
        self.keywordsbutton.config(state=NORMAL)
        #self.kvpairsbutton.config(state=NORMAL)
        # sheet.open_spreadsheet()

    def open_keywords_sheet(self):
        keywordsSheet = Toplevel(self)
        keywords = KeywordsSheet(os.path.join(self.outputdir.get(), 'csv'), master=keywordsSheet, newImageNames=self.newImageNames, oldImageNames=self.oldImageNames)

    def createWidgets(self):
        self.recBool = BooleanVar()
        self.recBool.set(False)
        self.inputSelector = Button(self, text='Input directory: ', command=self.load_input, width=20)
        self.inputSelector.grid(row=0,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.recbox = Checkbutton(self, text='Include subdirectories', variable=self.recBool)
        self.recbox.grid(row=0, column=3, ipadx=5, ipady=5, padx=5, pady=5)
        self.inputdir = Entry(self)
        self.inputdir.insert(END, os.getcwd())
        #self.inputdir.insert(END, 'C:\\Users\\SmithA\\Desktop\\Tooltesting\\test1')
        self.inputdir.grid(row=0, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=2)

        self.outputSelector = Button(self, text='Output directory: ', command=self.load_output, width=20)
        self.outputSelector.grid(row=1, column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.outputdir = Entry(self, width=20)
        self.outputdir.insert(END, os.getcwd())
        #self.outputdir.insert(END, 'C:\\Users\\SmithA\\Desktop\\Tooltesting\\test2')
        self.outputdir.grid(row=1, column=1, ipadx=2, ipady=5, padx=5, pady=5, columnspan=2)

        self.metadatalabel = Button(self, text='Metadata file: ', command=self.select_metadatafile, width=20)
        self.metadatalabel.grid(row=0, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        self.metadatafilename = Entry(self, width=20)
        self.metadatafilename.insert(END, os.path.join(os.getcwd(), 'metadata.txt'))
        self.metadatafilename.grid(row=0, column=6, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)

        self.prefsbutton = Button(self, text='Preferences file: ', command=self.select_preferencesfile, width=20)
        self.prefsbutton.grid(row=1, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        self.prefsfilename = Entry(self, width=20)
        self.prefsfilename.insert(END, os.path.join(os.getcwd(), 'preferences.txt'))
        self.prefsfilename.grid(row=1, column=6, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)

        self.additionallabel = Label(self, text='Additional Text to add at end of new filenames: ')
        self.additionallabel.grid(row=2, column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=3)
        self.additionalinfo = Entry(self, width=10)
        self.additionalinfo.grid(row=2, column=3, ipadx=5, ipady=5, padx=5, pady=5, sticky='W')

        self.previewbutton = Button(self, text='Preview filename', command=self.preview_filename, bg='cyan')
        self.previewbutton.grid(row=2, column=4)

        self.sep1 = ttk.Separator(self, orient=HORIZONTAL).grid(row=3, columnspan=8, sticky='EW')
        self.descriptionFields = ['Coll. Request ID', 'Local Camera ID', 'Local Lens ID', 'Hard Drive Location']

        self.descriptionlabel = Label(self, text='Enter global camera information. This information cannot be pulled '
                                                 'from exif data.')
        self.descriptionlabel.grid(row=4,columnspan=8, sticky='W')
        row = 5
        col = 0
        self.attributes = {}
        for field in self.descriptionFields:
            self.attrlabel = Label(self, text=field).grid(row=row, column=col, ipadx=5, ipady=5, padx=5, pady=5)
            self.attributes[field] = Entry(self, width=10)
            self.attributes[field].grid(row=row, column=col+1, ipadx=0, ipady=5, padx=5, pady=5)
            col += 2
            if col == 8:
                row += 1
                col = 0

        lastLoc = self.attributes['Hard Drive Location'].grid_info()
        lastRow = int(lastLoc['row'])

        self.sep2 = ttk.Separator(self, orient=HORIZONTAL).grid(row=lastRow+1, columnspan=8, sticky='EW')

        self.okbutton = Button(self, text='Load ', command=self.go, width=20, bg='green')
        self.okbutton.grid(row=lastRow+2,column=0, ipadx=5, ipady=5, sticky='E')
        self.cancelbutton = Button(self, text='Cancel', command=self.quit, width=20, bg='red')
        self.cancelbutton.grid(row=lastRow+2, column=6, ipadx=5, ipady=5, padx=5, sticky='W')

        self.keywordsbutton = Button(self, text='Enter Keywords', command=self.open_keywords_sheet, state=DISABLED, width=20)
        self.keywordsbutton.grid(row=lastRow+2, column=2, ipadx=5, ipady=5, padx=5, sticky='E')

        # self.kvpairsbutton = Button(self, text='Enter K/V Pairs', command=self.open_kv_sheet, state=DISABLED, width=20)
        # self.kvpairsbutton.grid(row=lastRow+2, column=4, ipadx=5, ipady=5, padx=5, sticky='W')


def main():
    root = Tk()
    root.resizable(width=False, height=False)
    root.wm_title('HP GUI')
    app = HPGUI(master=root)
    app.mainloop()

if __name__ == '__main__':
    main()
