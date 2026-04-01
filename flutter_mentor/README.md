# flutter_mentor

## Overview
The `flutter_mentor` project is a Flutter application designed to facilitate mentorship by providing forms for mentors and mentees, as well as a platform to display mentor questions. The application integrates with a Python script for data processing, enabling advanced functionalities.

## Project Structure
```
flutter_mentor
├── lib
│   ├── main.dart
│   ├── models
│   │   ├── mentor.dart
│   │   ├── mentee.dart
│   │   └── question.dart
│   ├── screens
│   │   ├── home_screen.dart
│   │   ├── mentor_form_screen.dart
│   │   ├── mentee_form_screen.dart
│   │   └── questions_screen.dart
│   ├── widgets
│   │   ├── form_field_widget.dart
│   │   └── question_card_widget.dart
│   ├── services
│   │   ├── api_service.dart
│   │   └── python_integration_service.dart
│   └── utils
│       └── constants.dart
├── assets
│   └── data
│       └── mentor_questions.json
├── python_scripts
│   ├── data_processor.py
│   └── requirements.txt
├── web
│   └── index.html
├── pubspec.yaml
└── README.md
```

## Features
- **Mentor and Mentee Forms**: Users can fill out forms to register as mentors or mentees.
- **Question Display**: A dedicated screen to view mentor questions imported from a JSON file.
- **Data Processing**: Integration with a Python script for advanced data processing tasks.

## Setup Instructions
1. **Clone the Repository**: 
   ```
   git clone <repository-url>
   cd flutter_mentor
   ```

2. **Install Dependencies**: 
   ```
   flutter pub get
   ```

3. **Run the Application**: 
   ```
   flutter run
   ```

## Deployment Process
1. Build the Flutter web application using the command:
   ```
   flutter build web
   ```

2. Choose a hosting platform like Vercel or Firebase Hosting.

3. For Vercel:
   - Create a new project and link it to your GitHub repository or upload the build folder directly.
   - Configure the project settings in Vercel, ensuring that the output directory is set to `build/web`.

4. Deploy the application, and Vercel will provide a live URL for your Flutter web app.

## TODO List:
Implement Semester OptIn/OptOut per Kaitlyn's request
Add "thank you for filling out form" page after form is submitted instead on blank screen

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License - see the LICENSE file for details.