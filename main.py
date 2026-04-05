import sys
import serial
import serial.tools.list_ports  # Used to scan for COM ports
import threading
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QDoubleSpinBox, QCheckBox, QComboBox, QPushButton)
from PyQt6.QtCore import QTimer, Qt

class FullSerialPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ultimate Embedded Serial Plotter")
        self.resize(1100, 650)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- TOP CONTROL BAR (Connection Settings) ---
        self.conn_layout = QHBoxLayout()
        
        self.conn_layout.addWidget(QLabel("Port:"))
        self.combo_port = QComboBox()
        self.refresh_ports() # Initial scan
        self.conn_layout.addWidget(self.combo_port)

        self.conn_layout.addWidget(QLabel("Baud:"))
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["9600", "115200", "921600", "2000000"])
        self.combo_baud.setCurrentText("115200")
        self.conn_layout.addWidget(self.combo_baud)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.toggle_connection)
        self.conn_layout.addWidget(self.btn_connect)

        self.main_layout.addLayout(self.conn_layout)

        # --- MIDDLE CONTROL BAR (Graph Settings) ---
        self.graph_layout = QHBoxLayout()
        
        self.check_autofit = QCheckBox("Auto-Fit Y")
        self.check_autofit.stateChanged.connect(self.toggle_autofit)
        self.graph_layout.addWidget(self.check_autofit)

        self.graph_layout.addWidget(QLabel("Min Y:"))
        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(-100000, 100000)
        self.spin_min.setValue(-3500)
        self.graph_layout.addWidget(self.spin_min)

        self.graph_layout.addWidget(QLabel("Max Y:"))
        self.spin_max = QDoubleSpinBox()
        self.spin_max.setRange(-100000, 100000)
        self.spin_max.setValue(3500)
        self.graph_layout.addWidget(self.spin_max)

        self.main_layout.addLayout(self.graph_layout)

        # --- PLOT WIDGET ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=True, y=True)
        self.main_layout.addWidget(self.plot_widget)
        self.curve = self.plot_widget.plot(pen=pg.mkPen('g', width=1.5))

        # Internal State
        self.ser = None
        self.running = False
        self.data_buffer = []
        self.window_size = 1000

        # UI Update Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)

    def refresh_ports(self):
        """ Scans the system for available serial ports """
        self.combo_port.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.combo_port.addItem(p.device)

    def toggle_connection(self):
        """ Handles Opening and Closing the Serial Port """
        if self.ser is None or not self.ser.is_open:
            # CONNECTING
            try:
                port = self.combo_port.currentText()
                baud = int(self.combo_baud.currentText())
                self.ser = serial.Serial(port, baud, timeout=0.1)
                
                self.running = True
                self.thread = threading.Thread(target=self.read_serial, daemon=True)
                self.thread.start()
                
                self.btn_connect.setText("Disconnect")
                self.btn_connect.setStyleSheet("background-color: #ff4c4c;") # Red
            except Exception as e:
                print(f"Connection Failed: {e}")
        else:
            # DISCONNECTING
            self.running = False
            if self.ser:
                self.ser.close()
            self.btn_connect.setText("Connect")
            self.btn_connect.setStyleSheet("") # Default color

    def toggle_autofit(self, state):
        is_auto = (state == 2) # 2 is 'Checked'
        self.spin_min.setEnabled(not is_auto)
        self.spin_max.setEnabled(not is_auto)

    def read_serial(self):
        while self.running:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        val = float(line)
                        self.data_buffer.append(val)
                        if len(self.data_buffer) > self.window_size:
                            self.data_buffer.pop(0)
                except:
                    continue

    def update_plot(self):
        if not self.data_buffer:
            return
            
        self.curve.setData(self.data_buffer)

        if self.check_autofit.isChecked():
            d_min, d_max = min(self.data_buffer), max(self.data_buffer)
            pad = (d_max - d_min) * 0.1 or 1
            self.plot_widget.setYRange(d_min - pad, d_max + pad, padding=0)
        else:
            self.plot_widget.setYRange(self.spin_min.value(), self.spin_max.value(), padding=0)

    def closeEvent(self, event):
        self.running = False
        if self.ser:
            self.ser.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FullSerialPlotter()
    window.show()
    sys.exit(app.exec())