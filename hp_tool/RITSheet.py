from Tkinter import *
import os
import pandas as pd
import tkMessageBox
import pandastable
import csv
from ErrorWindow import ErrorWindow


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

        errors.extend(self.check_model())

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


    def check_model(self):
        errors = []
        try:
            dataFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Devices.csv')
            df = pd.read_csv(dataFile)
        except IOError:
            tkMessageBox.showwarning('Warning', 'Keywords reference not found!')
            return

        data = [x.lower().strip() for x in df['SeriesModel']]
        cols_to_check = [self.modelcol]
        for col in range(0, self.pt.cols):
            if col in cols_to_check:
                for row in range(0, self.pt.rows):
                    val = str(self.pt.model.getValueAt(row, col))
                    if val.lower() == 'nan' or val == '':
                        imageName = self.pt.model.getValueAt(row, 0)
                        errors.append('No camera model entered for ' + imageName + ' (row ' + str(row + 1) + ')')
                    elif val.lower() not in data:
                        errors.append('Invalid camera model ' + val + ' (row ' + str(row + 1) + ')')
        return errors
