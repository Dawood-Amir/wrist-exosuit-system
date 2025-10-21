# EMG-Controlled Adaptive Wrist Exosuit System

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Android](https://img.shields.io/badge/Android-Kotlin-green.svg)](https://developer.android.com/)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20Raspberry%20Pi%20%7C%20Python-lightgrey.svg)]()

A **real-time rehabilitation system** that uses surface EMG (sEMG) signals to deliver adaptive wrist assistance through machine learning and motor control.


<p align="left">
  <img src="Report/demo.gif" width="300"/>
</p>

## 📋 Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Quick Start](#quick-start)
* [Components](#components)
* [Setup Guide](#setup-guide)
* [Usage](#usage)
* [Documentation](#documentation)
* [Troubleshooting](#troubleshooting)
* [Citation](#citation)

---

## 🎯 Overview

This system provides **adaptive motor assistance for wrist rehabilitation**, interpreting forearm EMG signals to control a **cable-driven exosuit** in real time.

**Key Features**

* 🧠 Real-time EMG processing 
* 🤖 ML-driven motion classification (Ridge / MLP)
* 🛡️ Multi-layer safety system (limits, watchdogs, validation)
* 📱 Android interface for therapists and patients
* 🔧 Personalized model training for each user

---

## 🏗️ Architecture

```
WristExo/
├── android/          # Kotlin app (UI + EMG processing)
├── pythonmodule/     # Exosuit controller (Raspberry Pi)
├── trainerudp/       # ML training server (Python)
└── docs/             # Technical report + setup guide
```

---

## 🚀 Quick Start

### Prerequisites

* Python 3.7+
* Android Studio
* Myo Armband
* Raspberry Pi (or WSL for dev)

### Installation

```bash
git clone https://github.com/Dawood-Amir/wrist-exosuit-system.git
cd wrist-exosuit-system
pip install -r pythonmodule/requirements.txt
pip install -r trainerudp/requirements.txt
```

---

## 🧩 Components

### 📱 Android Application

* Streams and processes EMG data from the Myo Armband
* Classifies movements (Flexion / Extension / Co-contraction / Rest)
* Controls exosuit parameters and communicates via UDP

### 🧠 Training Server

* Optimizes ML models (Ridge / MLP) via parameter search
* Selects best feature/window configuration per user

### ⚙️ Exosuit Controller

* Runs on Raspberry Pi 5
* Executes real-time motor control (CubeMars AK60-6 via CANdle)
* Enforces position/velocity limits and safety rules

---

## 🛠️ Setup Guide

### 1️⃣ Training Server

```bash
cd trainerudp
python wrist_exo_model_trainer.py
```

Open ports: **3350, 3352, 3358, 12346, 12347**
Set server IP in Android → `UdpMotorController.getTrainingServerIp()`

### 2️⃣ Motor Controller

```bash
cd pythonmodule/controller
python main.py
```

> Set `TEST_MODE = False` in all controller files.

For WSL:

```bash
python udp_relay_for_wsl.py
```

### 3️⃣ Android App

* Open `/android/` in Android Studio
* Update IPs for controller and training server
* Build → Install → Run

---

## ▶️ Usage

### 🧾 Training Phase

1. Connect Myo Armband
2. Follow guided 4-state recording (Flexion, Extension, Isometric, Rest)
3. Choose model (Ridge / MLP) → Train → Save

### ⚡ Operation Phase

1. Select trained model
2. Adjust parameters (stiffness, speed, limits)
3. Start system → Real-time control begins

---

## 📚 Documentation

* **Technical Report:** [`emg-wrist-rehabilitation-report.pdf`](Report/emg-wrist-rehabilitation-report.pdf)
* **Setup Guide:** [`Setup Guide.pdf`](Report/Setup%20Guide.pdf)

---

## 🧩 Troubleshooting

| Issue                      | Solution                                                |
| -------------------------- | ------------------------------------------------------- |
| 🔴 Firewall blocking ports | Open ports 3350 – 12347 or temporarily disable firewall |
| ⏱️ Connection timeout      | Verify IPs and network link                             |
| ⚙️ Motor not responding    | Ensure `TEST_MODE = False`, change control_period , check CANdle wiring      |
| 📉 Training fails          | Verify feature sets and EMG signal quality              |

---

## 🤝 Contributing

Developed at **Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU)**.
For contributions or questions, contact **[dawood.a.mughal@fau.de](mailto:dawood.a.mughal@fau.de)**.

---

## 📄 Citation

> **Dawood Aamar Mughal**, *EMG-Controlled Adaptive Assistance for Wrist Rehabilitation: A Real-Time Control Platform*, FAU (2025).
> Instructors: Prof. Dr. Claudio Castellini, Prof. Dr. rer. nat. Sabine Thürauf.
> [Report PDF](docs/emg-wrist-rehabilitation-report.pdf)


