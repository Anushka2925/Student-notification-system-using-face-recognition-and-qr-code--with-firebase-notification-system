# Student-notification-system-using-face-recognition-and-qr-code--with-firebase-notification-system
# Smart Attendance System 📸📲✅

A **Smart Attendance System** for educational institutions that integrates **Face Recognition**, **QR Code scanning**, and **Firebase Cloud Messaging (FCM)** for real-time notifications and attendance tracking.

---

## 🚀 Features

- 🎭 **Face Recognition Attendance** using OpenCV and face_recognition
- 📱 **QR Code Scanning** for instant attendance marking
- 🧾 **QR Code Generation** for each class/session
- 🔔 **Firebase Cloud Messaging (FCM)** for real-time notifications
- 📊 **Real-Time Dashboard** for viewing attendance logs
- 📥 **Export Attendance Reports** as CSV/PDF
- 🔐 **Role-Based Access** for Admin, Teacher, and Student
- 🌑 **Dark Mode UI** for better usability
- 📸 **Auto-Save Captured Faces** of new users for training
- 📈 **Attendance History** view per user
- 🔑 **Username-Password Authentication** using SQLite (no Firebase Auth)

---

## 🛠️ Tech Stack

- **Frontend**: Android App (Java/Kotlin or Flutter)
- **Backend**: Flask (Python)
- **Database**: SQLite
- **Notifications**: Firebase Cloud Messaging (FCM)
- **Face Recognition**: `face_recognition` library, OpenCV
- **QR Code**: `qrcode` and `opencv-python`

---

## 📦 Installation

### 🔧 Backend (Flask API)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/smart-attendance-system.git
   cd smart-attendance-system/backend


python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
Fork the repository

Create a new branch (feature/my-feature)

Commit your changes

Push to the branch

Create a pull request
