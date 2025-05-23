import sys
import os
import csv
import cv2
import qrcode
import pickle
import face_recognition
import firebase_admin
from firebase_admin import messaging, credentials
from datetime import datetime
from fpdf import FPDF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget,
    QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem, QComboBox,
    QInputDialog, QFileDialog
)
from PyQt5.QtGui import QPixmap
from pyzbar.pyzbar import decode

# Directories
KNOWN_FACES_DIR = "known_faces"
ENCODINGS_FILE = "encodings.pkl"
ATTENDANCE_FILE = "attendance.csv"
USERS_FILE = "users.csv"
QR_CODES_DIR = "qr_codes"

# Ensure directories exist
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(QR_CODES_DIR, exist_ok=True)

# Firebase Initialization
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)

def send_notification(title, body, token=None):
    """
    Send a notification via Firebase.
    If 'token' is provided, sends to that device; otherwise, sends to topic.
    """
    notification = messaging.Notification(
        title=title,
        body=body
    )
    if token:
        message = messaging.Message(
            notification=notification,
            token=token
        )
    else:
        message = messaging.Message(
            notification=notification,
            topic="attendance_notifications"
        )
    response = messaging.send(message)
    print("Notification sent:", response)

def get_token_for_user(username):
    if not os.path.exists("tokens.csv"):
        return None
    with open("tokens.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 2 and row[0] == username:
                return row[1]
    return None

def mark_attendance(student_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ATTENDANCE_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([student_id, timestamp])

def encode_faces():
    known_encodings = []
    known_names = []
    for filename in os.listdir(KNOWN_FACES_DIR):
        image_path = os.path.join(KNOWN_FACES_DIR, filename)
        image = face_recognition.load_image_file(image_path)
        encoding = face_recognition.face_encodings(image)
        if encoding:
            known_encodings.append(encoding[0])
            known_names.append(os.path.splitext(filename)[0])
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump((known_encodings, known_names), f)

def verify_login(username, password, role):
    if not os.path.exists(USERS_FILE):
        QMessageBox.warning(None, "Error", "User database not found!")
        return False
    with open(USERS_FILE, "r") as f:
        reader = csv.reader(f)
        users_list = list(reader)
        for row in users_list:
            if len(row) == 3 and row[0] == username and row[1] == password and row[2].strip().lower() == role:
                return True
    return False

def load_attendance(username):
    attendance_data = []
    if not os.path.exists(ATTENDANCE_FILE):
        return []
    with open(ATTENDANCE_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if username == "admin" or username in row[0]:
                attendance_data.append(row)
    return attendance_data

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - Smart Attendance System")
        self.setGeometry(100, 100, 300, 250)
        layout = QVBoxLayout()
        self.role_selector = QComboBox()
        self.role_selector.addItems(["Admin", "Student"])
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)
        container = QWidget()
        container.setLayout(layout)
        layout.addWidget(QLabel("Select Role"))
        layout.addWidget(self.role_selector)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        self.setCentralWidget(container)
        self.setStyleSheet("""
            QWidget {
                font-family: Arial;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #aaa;
                border-radius: 4px;
            }
        """)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        role = self.role_selector.currentText().lower()
        if verify_login(username, password, role):
            self.hide()
            self.attendance_app = AttendanceApp(role, username)
            self.attendance_app.show()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password")

class AttendanceApp(QMainWindow):
    def __init__(self, role, username):
        super().__init__()
        self.role = role
        self.username = username
        self.setWindowTitle(f"Smart Attendance System - {role.capitalize()}")
        self.setGeometry(100, 100, 650, 550)
        layout = QVBoxLayout()
        self.label = QLabel(f"Welcome, {username}")
        layout.addWidget(self.label)
        self.attendance_table = QTableWidget()
        self.load_attendance_data()
        layout.addWidget(self.attendance_table)
        if self.role == "admin":
            self.manage_users_button = QPushButton("Manage Users")
            layout.addWidget(self.manage_users_button)
        self.face_button = QPushButton("Face Recognition")
        self.face_button.clicked.connect(self.recognize_face)
        layout.addWidget(self.face_button)
        self.generate_qr_button = QPushButton("Generate QR Code")
        self.generate_qr_button.clicked.connect(self.generate_qr_code)
        layout.addWidget(self.generate_qr_button)
        self.scan_qr_button = QPushButton("Scan QR Code")
        self.scan_qr_button.clicked.connect(self.scan_qr_code)
        layout.addWidget(self.scan_qr_button)
        if self.role == "admin":
            self.export_pdf_button = QPushButton("Export Attendance as PDF")
            self.export_pdf_button.clicked.connect(self.export_attendance_pdf)
            layout.addWidget(self.export_pdf_button)
            # ----------- BUTTON FOR SENDING NOTIFICATION -----------
            self.send_notification_button = QPushButton("Send Notification")
            self.send_notification_button.clicked.connect(self.send_custom_notification)
            layout.addWidget(self.send_notification_button)
            # -------------------------------------------------------
        self.qr_label = QLabel()
        layout.addWidget(self.qr_label)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setStyleSheet("""
            QWidget {
                font-family: Arial;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                margin-bottom: 6px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #aaa;
                border-radius: 4px;
            }
            QTableWidget {
                background: #f6f6f6;
                border: 1px solid #ccc;
            }
            QLabel {
                font-size: 16px;
                margin-bottom: 8px;
            }
        """)

    def load_attendance_data(self):
        data = load_attendance(self.username)
        self.attendance_table.setRowCount(len(data))
        self.attendance_table.setColumnCount(2)
        self.attendance_table.setHorizontalHeaderLabels(["Student", "Timestamp"])
        for row_idx, row_data in enumerate(data):
            for col_idx, cell in enumerate(row_data):
                self.attendance_table.setItem(row_idx, col_idx, QTableWidgetItem(cell))

    def scan_qr_code(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            QMessageBox.warning(self, "Error", "Webcam not found!")
            return
        QMessageBox.information(self, "Instructions", "Show QR Code in front of the camera.")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                QMessageBox.warning(self, "Error", "Could not capture image.")
                break
            decoded_objects = decode(frame)
            if decoded_objects:
                for obj in decoded_objects:
                    student_id = obj.data.decode("utf-8")
                    if student_id:
                        mark_attendance(student_id)
                        student_token = get_token_for_user(student_id)
                        if student_token:
                            send_notification("Attendance Marked", f"{student_id} has been marked present.", token=student_token)
                        else:
                            send_notification("Attendance Marked", f"{student_id} has been marked present.")
                        cap.release()
                        cv2.destroyAllWindows()
                        QMessageBox.information(self, "Attendance Marked", f"Attendance marked for {student_id}")
                        self.load_attendance_data()
                        return
            cv2.imshow("QR Code Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

    def recognize_face(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "Error", "Webcam not found!")
            return
        if not os.path.exists(ENCODINGS_FILE):
            QMessageBox.warning(self, "Error", "Face encodings file not found! Run face encoding first.")
            return
        with open(ENCODINGS_FILE, "rb") as f:
            known_encodings, known_names = pickle.load(f)
        QMessageBox.information(self, "Instructions", "Press ESC or close the window to exit at any time.\nPosition your face in front of the camera.")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                QMessageBox.warning(self, "Error", "Could not capture image.")
                break
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_encodings, face_encoding)
                name = "Unknown"
                if True in matches:
                    match_index = matches.index(True)
                    name = known_names[match_index]
                    mark_attendance(name)
                    student_token = get_token_for_user(name)
                    if student_token:
                        send_notification("Attendance Marked", f"{name} has been marked present.", token=student_token)
                    else:
                        send_notification("Attendance Marked", f"{name} has been marked present.")
                    cap.release()
                    cv2.destroyAllWindows()
                    QMessageBox.information(self, "Attendance Marked", f"Attendance marked for {name}")
                    self.load_attendance_data()
                    return
            cv2.imshow("Face Recognition", frame)
            # Allow user to close window or press ESC to exit
            key = cv2.waitKey(1)
            if key == 27 or cv2.getWindowProperty("Face Recognition", cv2.WND_PROP_VISIBLE) < 1:
                break
        cap.release()
        cv2.destroyAllWindows()

    def generate_qr_code(self):
        student_id, ok = QInputDialog.getText(self, "Generate QR Code", "Enter Student ID:")
        if ok and student_id:
            qr = qrcode.make(student_id)
            qr_path = os.path.join(QR_CODES_DIR, f"{student_id}.png")
            qr.save(qr_path)
            pixmap = QPixmap(qr_path)
            self.qr_label.setPixmap(pixmap)
            self.qr_label.setScaledContents(True)
            QMessageBox.information(self, "QR Code Generated", f"QR Code saved at: {qr_path}")

    def export_attendance_pdf(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if file_path:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            data = load_attendance(self.username)
            pdf.cell(100, 10, "Student", border=1)
            pdf.cell(80, 10, "Timestamp", border=1)
            pdf.ln()
            for row in data:
                pdf.cell(100, 10, row[0], border=1)
                pdf.cell(80, 10, row[1], border=1)
                pdf.ln()
            try:
                pdf.output(file_path)
                QMessageBox.information(self, "PDF Exported", f"Attendance data exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not export PDF: {str(e)}")

    def send_custom_notification(self):
        title, ok1 = QInputDialog.getText(self, "Send Notification", "Enter Notification Title:")
        if not ok1 or not title:
            return
        body, ok2 = QInputDialog.getText(self, "Send Notification", "Enter Notification Body:")
        if not ok2 or not body:
            return
        recipient, ok3 = QInputDialog.getText(self, "Send Notification", "Enter username to send to (leave blank for all):")
        try:
            if ok3 and recipient:
                token = get_token_for_user(recipient)
                if token:
                    send_notification(title, body, token=token)
                    QMessageBox.information(self, "Notification Sent", f"Notification sent to {recipient}!")
                else:
                    QMessageBox.warning(self, "User Not Found", "Token for user not found. Sending to all instead.")
                    send_notification(title, body)
                    QMessageBox.information(self, "Notification Sent", "Notification sent to all!")
            else:
                send_notification(title, body)
                QMessageBox.information(self, "Notification Sent", "Notification sent to all!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send notification: {str(e)}")

if __name__ == "__main__":
    encode_faces()
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())
