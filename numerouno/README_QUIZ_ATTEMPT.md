# Public Quiz Attempt System

This system allows students to attempt LMS quizzes through a public interface without requiring login.

## Features

1. **Student Group Selection**: Users can select from available student groups
2. **Student Selection**: After selecting a group, users can choose a student from that group
3. **Quiz Listing**: Shows available quizzes for the selected student and group
4. **Quiz Attempt**: Students can attempt quizzes with a modern, responsive interface
5. **Automatic Scoring**: Quizzes are automatically scored and results are displayed
6. **Unified Assessment Integration**: Quiz submissions are integrated with the unified assessment system

## Files Created

### Backend API
- `/numerouno/api/quiz_attempt.py` - API endpoints for quiz functionality

### Frontend Pages
- `/www/quiz-attempt.html` - Main quiz selection page
- `/templates/pages/quiz_attempt.html` - Quiz attempt template
- `/numerouno/page/quiz_attempt/` - Page controller and template

### Configuration
- Updated `hooks.py` to register new page routes

## API Endpoints

### 1. Get Student Groups
```
POST /api/method/numerouno.numerouno.api.quiz_attempt.get_student_groups
```
Returns all available student groups.

### 2. Get Students by Group
```
POST /api/method/numerouno.numerouno.api.quiz_attempt.get_students_by_group
Body: {"student_group": "group_name"}
```
Returns students in the specified group.

### 3. Get Available Quizzes
```
POST /api/method/numerouno.numerouno.api.quiz_attempt.get_available_quizzes
Body: {"student_group": "group_name", "student": "student_name"}
```
Returns quizzes available for the student in the group.

### 4. Get Quiz Questions
```
POST /api/method/numerouno.numerouno.api.quiz_attempt.get_quiz_questions
Body: {"quiz_name": "quiz_name"}
```
Returns quiz questions and details.

### 5. Submit Quiz Attempt
```
POST /api/method/numerouno.numerouno.api.quiz_attempt.submit_quiz_attempt
Body: {
    "quiz_name": "quiz_name",
    "student": "student_name",
    "student_group": "group_name",
    "answers": "json_string"
}
```
Submits quiz answers and returns results.

## Usage

1. **Access the Quiz Page**: Navigate to `/quiz-attempt` on your site
2. **Select Student Group**: Choose from the dropdown list of available groups
3. **Select Student**: Choose a student from the selected group
4. **Load Quizzes**: Click "Load Available Quizzes" to see available quizzes
5. **Attempt Quiz**: Click "Attempt Quiz" to start taking the quiz
6. **Submit Answers**: Answer questions and submit the quiz
7. **View Results**: See your score and pass/fail status

## Integration with Unified Assessment System

Quiz submissions are automatically processed through the unified assessment system:
- Creates LMS Quiz Submission records
- Updates Assessment Results
- Maintains proper scoring and grading
- Integrates with existing assessment workflows

## Security Features

- Guest access allowed for public quiz attempts
- Student-group validation to ensure proper access
- CSRF protection on all API endpoints
- Input validation and sanitization

## Styling

The interface uses Bootstrap 5 with custom styling:
- Responsive design for mobile and desktop
- Modern gradient backgrounds
- Interactive elements with hover effects
- Progress indicators
- Clear visual feedback for quiz states

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile responsive design
- JavaScript required for functionality
