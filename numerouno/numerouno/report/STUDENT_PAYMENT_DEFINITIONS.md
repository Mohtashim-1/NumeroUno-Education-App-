# Student Payment Definitions & Reports Guide

## 📊 Key Payment Metrics Explained

### 1. **Total Unpaid Students**
- **Definition**: Counts every unpaid student enrollment across all Student Groups
- **Calculation**: Sum of all student records where `custom_invoiced = 0` or `NULL`
- **Example**: If John is unpaid in 3 different groups, he counts as 3 unpaid students
- **Use Case**: Shows the total volume of unpaid work needed

### 2. **Unique Unpaid Students** 
- **Definition**: Counts individual students who haven't paid, regardless of how many groups they're in
- **Calculation**: Count of distinct student IDs where `custom_invoiced = 0` or `NULL`
- **Example**: If John is unpaid in 3 different groups, he counts as 1 unique unpaid student
- **Use Case**: Shows how many individual students need to be contacted

### 3. **Total Paid Students**
- **Definition**: Counts every paid student enrollment across all Student Groups
- **Calculation**: Sum of all student records where `custom_invoiced = 1`
- **Example**: If Mary is paid in 2 different groups, she counts as 2 paid students
- **Use Case**: Shows total successful payment transactions

### 4. **Unique Paid Students**
- **Definition**: Counts individual students who have paid, regardless of how many groups they're in
- **Calculation**: Count of distinct student IDs where `custom_invoiced = 1`
- **Example**: If Mary is paid in 2 different groups, she counts as 1 unique paid student
- **Use Case**: Shows how many individual students have completed payments

## 🎯 Real-World Example

### Scenario: Student "John Doe" enrollments
```
Student Group A: John Doe - Unpaid
Student Group B: John Doe - Unpaid  
Student Group C: John Doe - Paid
Student Group D: Mary Smith - Paid
Student Group E: Mary Smith - Paid
```

### Results:
- **Total Unpaid Students**: 2 (John in Group A + John in Group B)
- **Unique Unpaid Students**: 1 (John Doe only)
- **Total Paid Students**: 3 (John in Group C + Mary in Group D + Mary in Group E)
- **Unique Paid Students**: 2 (John Doe + Mary Smith)

## 📈 Available Reports

### 1. **Student Payment Summary Report**
- **Location**: Reports > Numerouno > Student Payment Summary
- **Features**:
  - Shows all 4 metrics with clear definitions
  - Includes visual examples and explanations
  - Payment rate calculations
  - Charts showing payment distribution
  - Detailed breakdown by program and course

### 2. **Unpaid Students Report**
- **Location**: Reports > Numerouno > Unpaid Students
- **Features**:
  - Focuses on unpaid students only
  - Shows total unpaid and unique unpaid counts
  - Priority levels based on days unpaid
  - Email notification functionality

### 3. **Unpaid Students Dashboard**
- **Location**: Reports > Numerouno > Unpaid Students Dashboard
- **Features**:
  - Summary cards with key metrics
  - Charts and visualizations
  - Recent unpaid students list
  - Export capabilities

## 🔍 When to Use Each Metric

### Use "Total Unpaid Students" when:
- Calculating total workload for payment processing
- Estimating time needed to process all unpaid enrollments
- Planning resource allocation for payment collection

### Use "Unique Unpaid Students" when:
- Planning communication campaigns
- Estimating number of students to contact
- Calculating customer service workload
- Understanding individual student payment behavior

### Use "Total Paid Students" when:
- Calculating total revenue from successful payments
- Measuring payment processing efficiency
- Tracking payment transaction volume

### Use "Unique Paid Students" when:
- Understanding customer base size
- Calculating customer retention rates
- Planning marketing campaigns to existing customers

## 📊 Payment Rate Calculations

### Overall Payment Rate
```
Payment Rate = (Total Paid Students / Total Enrollments) × 100
```

### Example:
- Total Enrollments: 100
- Total Paid: 75
- Payment Rate: 75%

## 🎨 Visual Indicators

### Color Coding in Reports:
- **Red**: Unpaid students or high priority (>30 days)
- **Orange**: Medium priority (15-30 days)
- **Blue**: Low priority (<15 days)
- **Green**: Paid students

### Priority Levels:
- **High Priority**: >30 days unpaid
- **Medium Priority**: 15-30 days unpaid
- **Low Priority**: <15 days unpaid

## 🔧 Technical Implementation

### Database Fields Used:
- `tabStudent Group Student.custom_invoiced`: Payment status (0/1)
- `tabStudent Group Student.student`: Student ID
- `tabStudent Group Student.student_name`: Student name
- `tabStudent Group.student_group_name`: Group name
- `tabStudent Group.program`: Program name
- `tabStudent Group.course`: Course name

### Key SQL Logic:
```sql
-- Total Unpaid Students
COUNT(*) WHERE custom_invoiced = 0 OR custom_invoiced IS NULL

-- Unique Unpaid Students  
COUNT(DISTINCT student) WHERE custom_invoiced = 0 OR custom_invoiced IS NULL

-- Total Paid Students
COUNT(*) WHERE custom_invoiced = 1

-- Unique Paid Students
COUNT(DISTINCT student) WHERE custom_invoiced = 1
```

## 📋 Best Practices

1. **Regular Monitoring**: Check reports daily for new unpaid students
2. **Priority Management**: Focus on high-priority cases first
3. **Communication**: Use unique student counts for outreach planning
4. **Analysis**: Use total counts for workload and resource planning
5. **Reporting**: Include both metrics in management reports

## 🚀 Quick Actions

### Mark Students as Paid:
- Use the "Mark as Paid" utility function
- Bulk update capabilities available
- Email notifications sent automatically

### Export Data:
- All reports support Excel/PDF export
- Filter by program, course, or date ranges
- Custom date ranges for historical analysis

---

*This guide helps you understand the different ways to count and analyze student payment data in your Student Group system.* 