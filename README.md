# NumerUno ERP Enhancements

This repository contains customizations and automation scripts built on top of the ERPNext framework for the **NumerUno** organization.

The purpose of this project is to enhance ERPNext’s education module by adding custom features for managing:

- **Student Groups**
- **Course Schedules**
- **Student Attendance**
- **Student Cards**
- Dynamic Print Formats (with attendance, signature rendering, etc.)

---

## 🔧 Key Features

### ✅ Custom Coarse Schedule Generator
Automates the creation of `Course Schedule` and `Student Attendance` entries for a given `Student Group`.

- Uses custom date fields: `custom_from_date`, `custom_to_date`
- Automatically assigns instructors
- Initializes student attendance per day

### ✅ Dynamic Attendance in Print Format
Print format displays attendance per day based on actual records:

- Shows “P” for present and “A” for absent
- Dynamically generates day headers based on the date range
- Supports signature display from the `Student Card` doctype

### ✅ Student Card Integration
Pulls signature from the `Student Card` doctype and displays in print format with adjustable image size.

---

## 📁 Project Structure

numeruno/ ├── numeruno/ │ ├── custom/ │ │ ├── student_group.py # Python script for auto-scheduling and attendance │ │ ├── print_format/ │ │ │ └── student_attendance.html # Custom Jinja print format │ │ └── ... │ └── hooks.py └── README.md


---

## 🧠 Technologies

- **ERPNext**: v15
- **Frappe Framework**: Python + JavaScript
- **Jinja**: For print format rendering

---

## 🚀 Getting Started

1. Add `numeruno` app to your Frappe bench.
2. Install the app on your desired site:
   ```bash
   bench --site [your-site] install-app numeruno
