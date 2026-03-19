# -*- coding: utf-8 -*-


from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QDoubleSpinBox, QSizePolicy, QApplication, QMainWindow

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("Biplanar coil control")
        MainWindow.resize(800, 600)
        self.centralwidget = QWidget(MainWindow)
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        # self.centralwidget.setSizePolicy(sizePolicy)
        # self.centralwidget.setObjectName("centralwidget")
        # self.gridLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        # # self.gridLayoutWidget.setGeometry(QtCore.QRect(-1, -1, 801, 561))
        # self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        # self.gridLayout = QtWidgets.QGridLayout()
        # # self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        # # self.gridLayout.setContentsMargins(0, 0, 0, 0)
        # self.gridLayout.setObjectName("gridLayout")
        
        
        self.gridLayout = QGridLayout()
        self.centralwidget.setLayout(self.gridLayout)
        
        
        self.gridLayout.setRowStretch(0, 1);
        for row in range(1, 9):
            self.gridLayout.setRowStretch(row, 3);

        
        self.gridLayout.setRowMinimumHeight(0,50)
        
        self.gridLayout.setColumnStretch(0, 1);
        self.gridLayout.setColumnStretch(1, 2);
        self.gridLayout.setColumnStretch(2, 2);
        self.gridLayout.setColumnStretch(3, 2);
        self.gridLayout.setColumnStretch(4, 2);
        
        self.sinamp_dspinbox = [None]*8
        self.sinfre_dspinbox = [None]*8
        self.offset_dspinbox = [None]*8
        
        self.sinofs_dspinbox = [None]*8
        
        for ch in range(8):

            self.sinamp_dspinbox[ch] = QDoubleSpinBox()
            self.sinamp_dspinbox[ch].setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
            self.sinamp_dspinbox[ch].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            self.sinamp_dspinbox[ch].setSuffix("")
            self.sinamp_dspinbox[ch].setDecimals(3)
            self.sinamp_dspinbox[ch].setMinimum(0.0)
            self.sinamp_dspinbox[ch].setMaximum(10.0)
            self.sinamp_dspinbox[ch].setSingleStep(0.1)
            self.sinamp_dspinbox[ch].setObjectName("sinamp_ch%d_dspinbox"%ch)
            self.gridLayout.addWidget(self.sinamp_dspinbox[ch], ch+1, 2, 1, 1)
            
            self.offset_dspinbox[ch] = QDoubleSpinBox()
            self.offset_dspinbox[ch].setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
            self.offset_dspinbox[ch].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            self.offset_dspinbox[ch].setSuffix("")
            self.offset_dspinbox[ch].setDecimals(3)
            self.offset_dspinbox[ch].setMinimum(-10.0)
            self.offset_dspinbox[ch].setMaximum(10.0)
            self.offset_dspinbox[ch].setSingleStep(0.1)
            self.offset_dspinbox[ch].setObjectName("offset_ch%d_dspinbox"%ch)
            self.gridLayout.addWidget(self.offset_dspinbox[ch], ch+1, 1, 1, 1)
            
            self.sinfre_dspinbox[ch] = QDoubleSpinBox()
            self.sinfre_dspinbox[ch].setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
            self.sinfre_dspinbox[ch].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            self.sinfre_dspinbox[ch].setSuffix("")
            self.sinfre_dspinbox[ch].setDecimals(1)
            self.sinfre_dspinbox[ch].setMinimum(1)
            self.sinfre_dspinbox[ch].setMaximum(200.0)
            self.sinfre_dspinbox[ch].setSingleStep(1.0)
            self.sinfre_dspinbox[ch].setObjectName("sinfre_ch%d_dspinbox"%ch)
            self.sinfre_dspinbox[ch].setProperty("value", 10.0)
            self.gridLayout.addWidget(self.sinfre_dspinbox[ch], ch+1, 3, 1, 1)
            
            self.sinofs_dspinbox[ch] = QDoubleSpinBox()
            self.sinofs_dspinbox[ch].setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
            self.sinofs_dspinbox[ch].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            self.sinofs_dspinbox[ch].setSuffix("")
            self.sinofs_dspinbox[ch].setDecimals(3)
            self.sinofs_dspinbox[ch].setMinimum(0)
            self.sinofs_dspinbox[ch].setMaximum(2)
            self.sinofs_dspinbox[ch].setSingleStep(0.1)
            self.sinofs_dspinbox[ch].setObjectName("sinofs_ch%d_dspinbox"%ch)
            self.sinofs_dspinbox[ch].setProperty("value", 0.0)
            self.gridLayout.addWidget(self.sinofs_dspinbox[ch], ch+1, 4, 1, 1)
            
        self.label_4 = QLabel()
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)
        
        self.label_2 = QLabel()
        self.label_2.setMaximumSize(QtCore.QSize(16777215, 40))
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 1, 1, 1)
        
        self.label = QLabel()
        self.label.setMaximumSize(QtCore.QSize(16777215, 40))
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 2, 1, 1)
        
        self.label_3 = QLabel()
        self.label_3.setMaximumSize(QtCore.QSize(16777215, 40))
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 0, 3, 1, 1)
        
        
        self.label_31 = QLabel()
        self.label_3.setMaximumSize(QtCore.QSize(16777215, 40))
        self.label_31.setAlignment(QtCore.Qt.AlignCenter)
        self.label_31.setObjectName("label_31")
        self.gridLayout.addWidget(self.label_31, 0, 4, 1, 1)
       

        self.label_5 = QLabel()
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 1, 0, 1, 1)
        
        self.label_6 = QLabel()
        self.label_6.setAlignment(QtCore.Qt.AlignCenter)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 2, 0, 1, 1)
        
        self.label_7 = QLabel()
        self.label_7.setAlignment(QtCore.Qt.AlignCenter)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 3, 0, 1, 1)
        
        self.label_8 = QLabel()
        self.label_8.setAlignment(QtCore.Qt.AlignCenter)
        self.label_8.setObjectName("label_8")
        self.gridLayout.addWidget(self.label_8, 4, 0, 1, 1)
        
        self.label_9 = QLabel()
        self.label_9.setAlignment(QtCore.Qt.AlignCenter)
        self.label_9.setObjectName("label_9")
        self.gridLayout.addWidget(self.label_9, 5, 0, 1, 1)
        
        self.label_10 = QLabel()
        self.label_10.setAlignment(QtCore.Qt.AlignCenter)
        self.label_10.setObjectName("label_10")
        self.gridLayout.addWidget(self.label_10, 6, 0, 1, 1)
        
        self.label_11 = QLabel()
        self.label_11.setAlignment(QtCore.Qt.AlignCenter)
        self.label_11.setObjectName("label_11")
        self.gridLayout.addWidget(self.label_11, 7, 0, 1, 1)
        
        self.label_12 = QLabel()
        self.label_12.setAlignment(QtCore.Qt.AlignCenter)
        self.label_12.setObjectName("label_12")
        self.gridLayout.addWidget(self.label_12, 8, 0, 1, 1)
        
        MainWindow.setCentralWidget(self.centralwidget)
        # self.statusbar = QStatusBar(MainWindow)
        # self.statusbar.setObjectName("statusbar")
        # MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "ZEROFIELD coil control"))
        self.label_4.setText(_translate("MainWindow", "Field component (channel)"))
        self.label_2.setText(_translate("MainWindow", "Field offset (nT/(cm))"))
        self.label.setText(_translate("MainWindow", "Sine amplitude (nT/(cm))"))
        self.label_3.setText(_translate("MainWindow", "Sine frequency (Hz)"))
        self.label_31.setText(_translate("MainWindow", "Sine phase offset (pi*rad)"))
        self.label_5.setText(_translate("MainWindow", "Y (CH1)"))
        self.label_6.setText(_translate("MainWindow", "Z (CH2)"))
        self.label_7.setText(_translate("MainWindow", "X (CH3)"))
        self.label_8.setText(_translate("MainWindow", "dBy/dy (CH4)"))
        self.label_9.setText(_translate("MainWindow", "dBz/dy (CH5)"))
        self.label_10.setText(_translate("MainWindow", "dBz/dz (CH6)"))
        self.label_11.setText(_translate("MainWindow", "dBz/dx (CH7)"))
        self.label_12.setText(_translate("MainWindow", "dBy/dx (CH8)"))
        
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
