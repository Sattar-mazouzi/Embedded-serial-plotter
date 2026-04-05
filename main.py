import sys
import serial
import threading
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                             QHBoxLayout, QWidget, QLabel, QDoubleSpinBox)
from PyQt6.QtCore import QTimer, Qt

# --- INITIAL CONFIGURATION ---
SERIAL_PORT = 'COM6'       # Update this to your port
BAUD_RATE = 115200
WINDOW_SIZE = 1000         # Number of points shown on X-axis

class InteractiveSerialPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Sensor Plotter (Adjustable Y-Axis)")
        self.resize(1000, 600)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- CONTROL PANEL (Top Bar) ---
        self.control_layout = QHBoxLayout()
        
        # Min Y Input
        self.control_layout.addWidget(QLabel("Y Min:"))
        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(-100000, 100000)
        self.spin_min.setValue(-3500) # Initial value
        self.spin_min.valueChanged.connect(self.update_y_limits)
        self.control_layout.addWidget(self.spin_min)

        # Max Y Input
        self.control_layout.addWidget(QLabel("Y Max:"))
        self.spin_max = QDoubleSpinBox()
        self.spin_max.setRange(-100000, 100000)
        self.spin_max.setValue(3500) # Initial value
        self.spin_max.valueChanged.connect(self.update_y_limits)
        self.control_layout.addWidget(self.spin_max)

        self.control_layout.addStretch() # Pushes controls to the left
        self.main_layout.addLayout(self.control_layout)

        # --- PLOT WIDGET ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=True, y=True)
        self.main_layout.addWidget(self.plot_widget)

        # Create the curve
        self.curve = self.plot_widget.plot(pen=pg.mkPen('g', width=1.5))

        # Initial Y Limit Call
        self.update_y_limits()

        # Data buffer
        self.data_buffer = []

        # Serial setup
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        except Exception as e:
            print(f"Error: Could not open {SERIAL_PORT}. {e}")
            sys.exit()

        # Threading for Serial Reading
        self.running = True
        self.thread = threading.Thread(target=self.read_serial, daemon=True)
        self.thread.start()

        # UI Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20) # ~50 FPS

    def update_y_limits(self):
        """ Triggered whenever the SpinBoxes change """
        y_min = self.spin_min.value()
        y_max = self.spin_max.value()
        self.plot_widget.setYRange(y_min, y_max, padding=0)

    def read_serial(self):
        while self.running:
            if self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        value = float(line)
                        self.data_buffer.append(value)

                        if len(self.data_buffer) > WINDOW_SIZE:
                            self.data_buffer.pop(0)
                except (ValueError, UnicodeDecodeError):
                    continue

    def update_plot(self):
        if self.data_buffer:
            self.curve.setData(self.data_buffer)

    def closeEvent(self, event):
        self.running = False
        if self.ser.is_open:
            self.ser.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InteractiveSerialPlotter()
    window.show()
    sys.exit(app.exec())