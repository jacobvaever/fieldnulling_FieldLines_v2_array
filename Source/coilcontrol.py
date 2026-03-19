# -*- coding: utf-8 -*-
"""
Created on Tue Jun 22 16:06:09 2021

@author: rasmus.zetter
"""

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication

import sys, time

import numpy as np
from bitarray import bitarray, util
from com_monitor import ComMonitorThread
import queue
import argparse

parser = argparse.ArgumentParser(description="Unix-style argument parsing",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-v", "--verbose", action="store_true", help="increase verbosity")

args = parser.parse_args()
config = vars(args)

VERBOSE = config['verbose']
# print(config)

import basic_controls


ch_names = ['Y',
            'Z',
            'X',
            'dBy/dy',
            'dBz/dy',
            'dBz/dz',
            'dBz/dx',
            'dBy/dx']


coil_dBdI = np.array([0.4570,
                       0.6372,
                       0.9090,
                       2.6369,
                       2.6271,
                       1.4110,
                       4.8184,
                       2.4500]) * np.array([1e-6,
                                            1e-6,
                                            1e-6,
                                            1e-6/100,
                                            1e-6/100,
                                            1e-6/100,
                                            1e-6/100,
                                            1e-6/100]) #in T/A(/cm) 




coil_R = np.array([19.52,
                   13.93,
                   12.16,
                   18.48,
                   16.67,
                   14.18,
                   10.39,
                   8.51
                   ]) #Measured values, in Ohms


coil_dBdV = coil_dBdI / coil_R
min_voltage = -10
max_voltage = 10



class AppCore(QMainWindow, basic_controls.Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(AppCore, self).__init__(*args, **kwargs)

        #Load the UI Page
        # uic.loadUi('mainwindow.ui', self)
        self.setupUi(self)
        
        
        self.print_timer = QtCore.QTimer()
        
        self.print_timer.timeout.connect(lambda:self.print_rx())
        
         
        for ch in range(8):        
            self.offset_dspinbox[ch].setMinimum(coil_dBdV[ch] * min_voltage * 1e9)
            self.offset_dspinbox[ch].setMaximum(coil_dBdV[ch] * max_voltage * 1e9)
        
            self.sinamp_dspinbox[ch].setMinimum(0.0)
            self.sinamp_dspinbox[ch].setMaximum(coil_dBdV[ch]*max_voltage*1e9)
           
        self.offset_dspinbox[0].valueChanged.connect(lambda: self.setOffset(0))
        self.offset_dspinbox[1].valueChanged.connect(lambda: self.setOffset(1))
        self.offset_dspinbox[2].valueChanged.connect(lambda: self.setOffset(2))
        self.offset_dspinbox[3].valueChanged.connect(lambda: self.setOffset(3))
        self.offset_dspinbox[4].valueChanged.connect(lambda: self.setOffset(4))
        self.offset_dspinbox[5].valueChanged.connect(lambda: self.setOffset(5))
        self.offset_dspinbox[6].valueChanged.connect(lambda: self.setOffset(6))
        self.offset_dspinbox[7].valueChanged.connect(lambda: self.setOffset(7))
        
        self.sinamp_dspinbox[0].valueChanged.connect(lambda: self.setSinAmp(0))
        self.sinamp_dspinbox[1].valueChanged.connect(lambda: self.setSinAmp(1))
        self.sinamp_dspinbox[2].valueChanged.connect(lambda: self.setSinAmp(2))
        self.sinamp_dspinbox[3].valueChanged.connect(lambda: self.setSinAmp(3))
        self.sinamp_dspinbox[4].valueChanged.connect(lambda: self.setSinAmp(4))
        self.sinamp_dspinbox[5].valueChanged.connect(lambda: self.setSinAmp(5))
        self.sinamp_dspinbox[6].valueChanged.connect(lambda: self.setSinAmp(6))
        self.sinamp_dspinbox[7].valueChanged.connect(lambda: self.setSinAmp(7))
        
        self.sinfre_dspinbox[0].valueChanged.connect(lambda: self.setSinFre(0))
        self.sinfre_dspinbox[1].valueChanged.connect(lambda: self.setSinFre(1))
        self.sinfre_dspinbox[2].valueChanged.connect(lambda: self.setSinFre(2))
        self.sinfre_dspinbox[3].valueChanged.connect(lambda: self.setSinFre(3))
        self.sinfre_dspinbox[4].valueChanged.connect(lambda: self.setSinFre(4))
        self.sinfre_dspinbox[5].valueChanged.connect(lambda: self.setSinFre(5))
        self.sinfre_dspinbox[6].valueChanged.connect(lambda: self.setSinFre(6))
        self.sinfre_dspinbox[7].valueChanged.connect(lambda: self.setSinFre(7))
        
        self.sinofs_dspinbox[0].valueChanged.connect(lambda: self.setSinOfs(0))
        self.sinofs_dspinbox[1].valueChanged.connect(lambda: self.setSinOfs(1))
        self.sinofs_dspinbox[2].valueChanged.connect(lambda: self.setSinOfs(2))
        self.sinofs_dspinbox[3].valueChanged.connect(lambda: self.setSinOfs(3))
        self.sinofs_dspinbox[4].valueChanged.connect(lambda: self.setSinOfs(4))
        self.sinofs_dspinbox[5].valueChanged.connect(lambda: self.setSinOfs(5))
        self.sinofs_dspinbox[6].valueChanged.connect(lambda: self.setSinOfs(6))
        self.sinofs_dspinbox[7].valueChanged.connect(lambda: self.setSinOfs(7))
               
        self.tx_q = queue.Queue(maxsize=10000)
        self.rx_q = queue.Queue(maxsize=10000)
        self.monitor_msg_q = queue.Queue(maxsize=100)
        
        
        self.ser_monitor = ComMonitorThread('ZEROFIELD',
                                            self.tx_q,
                                            self.rx_q,
                                            self.monitor_msg_q,
                                            'auto',
                                            921600,
                                            verbose=VERBOSE,
                                            exc_callback = self.raiseDialog)
        time.sleep(3) #Sleep to allow time for COM port scan
        self.ser_monitor.start()
        
        
        #To be safe, zero all outputs
        for ch in range(8):
            self.setOffset(ch)
        ##
        
        self.print_timer.start(10) #Scan for received data every 10 ms
    
    def setOffset(self, ch):
        '''
        Set field offset for channel. Offset value is read from GUI spinbox.
        This method is meant to be called via signal-slot connection when the 
        GUI value is changed.

        Parameters
        ----------
        ch : int
            Channel to set offset for

        Returns
        -------
        None.

        '''
        field = self.offset_dspinbox[ch].value()
        value = field

        value = field / coil_dBdV[ch] * 1e-9
        
        if VERBOSE:
            print("%s (CH%d): offset magnetic field %.6f nT"%(ch_names[ch], ch+1, field))
            print("%s (CH%d): offset voltage %.6f V"%(ch_names[ch], ch+1, value))
        cmdbyte = util.int2ba(ch, length=8).tobytes()
        
        uintbytes= util.int2ba(int((2**19-1) * -value/10 + (2**19-1)), length=32).tobytes()
        
        if VERBOSE:
            print(cmdbyte + uintbytes[::-1])
            
        self.tx_q.put_nowait(cmdbyte + uintbytes[::-1])
        
    def setSinAmp(self, ch):
        '''
        Set field sine amplitude  for channel. Value is read from GUI spinbox.
        This method is meant to be called via signal-slot connection when the 
        GUI value is changed.

        Parameters
        ----------
        ch : int
            Channel to set sine amplitude for

        Returns
        -------
        None.

        '''
        field = self.sinamp_dspinbox[ch].value()
        value = field

        value = field / coil_dBdV[ch] * 1e-9
        
        if VERBOSE:
            print("%s (CH%d): sinusoid magnetic field %.6f nT"%(ch_names[ch], ch+1, field))
            print("%s (CH%d): sinusoid voltage %.6f V"%(ch_names[ch], ch+1, value))
            
        cmdbyte = util.int2ba(ch+16, length=8).tobytes()
        
        uintbytes= util.int2ba(int((2**20-1) * value/10), length=32).tobytes()
        
        if VERBOSE:
            print(cmdbyte + uintbytes[::-1])
            
        self.tx_q.put_nowait(cmdbyte + uintbytes[::-1])
        
        
    def setSinFre(self, ch):
        '''
        Set sine frequency for channel. Value is read from GUI spinbox.
        This method is meant to be called via signal-slot connection when the 
        GUI value is changed.

        Parameters
        ----------
        ch : int
            Channel to set sine frequency

        Returns
        -------
        None.

        '''
        freq = self.sinfre_dspinbox[ch].value()
        cmdbyte = util.int2ba(ch+32, length=8).tobytes()
        PSC = 500 - 1 
        fCLK = 170e6
        nSine = 256 
        
        ARR = int(fCLK/(freq*nSine*PSC+freq*nSine)-1)
        
        if VERBOSE:
            print(ARR)
        
        uintbytes= util.int2ba(ARR, length=32).tobytes()
        
        if VERBOSE:
            print(cmdbyte + uintbytes[::-1])
            
        self.tx_q.put_nowait(cmdbyte + uintbytes[::-1])
        
    def setSinOfs(self, ch):
        '''
        Set sine phase offset for channel. Value is read from GUI spinbox.
        This method is meant to be called via signal-slot connection when the 
        GUI value is changed.

        Parameters
        ----------
        ch : int
            Channel to set sine phase offset for

        Returns
        -------
        None.

        '''
        ofs = self.sinofs_dspinbox[ch].value()
        cmdbyte = util.int2ba(ch+48, length=8).tobytes()
        
        N_lut = 256 - 1
        ofs_pi_rad = int(ofs * N_lut / 2)
        
        if VERBOSE:
            print('%s (CH%d): ofs_pi_rad: %d'%(ch_names[ch], ch+1, ofs_pi_rad))
        
        uintbytes= util.int2ba(ofs_pi_rad, length=32).tobytes()
        
        if VERBOSE:
            print(cmdbyte + uintbytes[::-1])
            
        self.tx_q.put_nowait(cmdbyte + uintbytes[::-1])
    
    def closeEvent(self, event:QtGui.QCloseEvent):
        # Cleanup is handled here on program exit.
        # Close mainwindow
        self.ser_monitor.join()
        event.accept()
    
    def print_rx(self):
    
        if not self.rx_q.empty():
            rx_data = self.rx_q.get_nowait()
        
            print("Rx:")
            print(rx_data)
            
    def raiseDialog(self, message):
        # dlg = QMessageBox(self)
        # dlg.setWindowTitle("Something has gone wrong")
        # dlg.setText(str(message))
        # button = dlg.exec()

        # if button == QMessageBox.Ok:
        #     sys.exit()
        #     # sys.exit(app.exec_())
        print("dialog text:" + str(message))
        return

if __name__ == '__main__':
    app = QApplication(sys.argv)

    main = AppCore()
    main.show()
    # main.raise_()
    sys.exit(app.exec_())