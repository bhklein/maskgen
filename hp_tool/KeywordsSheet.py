from Tkinter import *
import os
import pandas as pd
import numpy as np
import tkMessageBox
import pandastable
import csv
import datetime
from ErrorWindow import ErrorWindow
from RITSheet import HPSpreadsheet

class KeywordsSheet(HPSpreadsheet):
    def __init__(self, dir, master=None, oldImageNames=[], newImageNames=[]):
        HPSpreadsheet.__init__(self, dir, master)
        self.oldImageNames = oldImageNames
        self.newImageNames = newImageNames
        self.dir = dir
        self.master = master
        self.master.title(self.dir)
        self.saveState = True
        master.protocol("WM_DELETE_WINDOW", self.check_save)
        master.bind("<Key>", self.keypress)
        self.open_spreadsheet()


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
