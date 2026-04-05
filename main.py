import sys
import serial
import threading
import pyqtgraph as pg
import numpy as np  # Added for faster min/max calculation
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                             QHBoxLayout, QWidget, QLabel, QDoubleSpinBox, QCheckBox)
from PyQt6.QtCore import QTimer, Qt

# --- CONFIGURATION ---
SERIAL_PORT = 'COM6'       # Update to your port
BAUD_RATE = 115200
WINDOW_SIZE = 1000         

class AutoFitSerialPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Serial Plotter (Manual & Auto-Fit)")
        self.resize(1000, 600)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- CONTROL PANEL ---
        self.control_layout = QHBoxLayout()
        
        # Auto-Fit Checkbox
        self.check_autofit = QCheckBox("Auto-Fit Y-Axis")
        self.check_autofit.setChecked(False)
        self.check_autofit.stateChanged.connect(self.toggle_autofit)
        self.control_layout.addWidget(self.check_autofit)

        # Manual Min Y
        self.lbl_min = QLabel("Y Min:")
        self.control_layout.addWidget(self.lbl_min)
        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(-100000, 100000)
        self.spin_min.setValue(-3500)
        self.spin_min.valueChanged.connect(self.manual_limit_change)
        self.control_layout.addWidget(self.spin_min)

        # Manual Max Y
        self.lbl_max = QLabel("Y Max:")
        self.control_layout.addWidget(self.lbl_max)
        self.spin_max = QDoubleSpinBox()
        self.spin_max.setRange(-100000, 100000)
        self.spin_max.setValue(3500)
        self.spin_max.valueChanged.connect(self.manual_limit_change)
        self.control_layout.addWidget(self.spin_max)

        self.control_layout.addStretch()
        self.main_layout.addLayout(self.control_layout)

        # --- PLOT ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=True, y=True)
        self.main_layout.addWidget(self.plot_widget)

        self.curve = self.plot_widget.plot(pen=pg.mkPen('g', width=1.5))

        # Data buffer
        self.data_buffer = []

        # Serial setup
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit()

        self.running = True
        self.thread = threading.Thread(target=self.read_serial, daemon=True)
        self.thread.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)

    def toggle_autofit(self, state):
        """ Disables manual inputs if Auto-Fit is active """
        is_auto = (state == Qt.CheckState.Checked.value)
        self.spin_min.setEnabled(not is_auto)
        self.spin_max.setEnabled(not is_auto)

    def manual_limit_change(self):
        """ Updates limits only if Auto-Fit is OFF """
        if not self.check_autofit.isChecked():
            self.plot_widget.setYRange(self.spin_min.value(), self.spin_max.value(), padding=0)

    def read_serial(self):
        while self.running:
            if self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        self.data_buffer.append(float(line))
                        if len(self.data_buffer) > WINDOW_SIZE:
                            self.data_buffer.pop(0)
                except:
                    continue

    def update_plot(self):
        if not self.data_buffer:
            return

        # Update data
        self.curve.setData(self.data_buffer)

        # Handle Auto-Fit logic
        if self.check_autofit.isChecked():
            data_min = min(self.data_buffer)
            data_max = max(self.data_buffer)
            
            # Add 10% padding so the line isn't touching the edge
            range_val = data_max - data_min
            if range_val == 0: range_val = 1 # Prevent division by zero/flat line issues
            
            padding = range_val * 0.1
            self.plot_widget.setYRange(data_min - padding, data_max + padding, padding=0)
            
            # Sync the spin boxes to show the current auto-calculated limits
            self.spin_min.setValue(data_min - padding)
            self.spin_max.setValue(data_max + padding)

    def closeEvent(self, event):
        self.running = False
        self.ser.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoFitSerialPlotter()
    window.show()
    sys.exit(app.exec())