import '../services/form_data_loader.dart';

/// Static option lists used by form widgets.
class FormOptions {
  static final FormDataLoader _loader = FormDataLoader();

  // Pronouns
  static const List<String> pronouns = [
    'She/her',
    'He/him',
    'They/them',
    'Prefer not to say',
    "Other",
  ];

  // Education levels
  static const List<String> educationLevels = ['BS', 'ABM', 'MS', 'PhD'];

  // Load possible majors from files
  static List<String> get undergradPrograms => _loader.undergradPrograms;
  static List<String> get gradPrograms => _loader.gradPrograms;
  static List<String> get abmPrograms => _loader.abmPrograms;
  static List<String> get phdPrograms => _loader.phdPrograms;
  static List<String> get concentrations => _loader.concentrations;

  // Experience levels
  static const List<String> experienceLevels = [
    'No internships yet',
    'Completed 1 internship',
    'Completed 2+ internships',
    'Co-op experience',
    'Research experience',
  ];

  // Industries
  static const List<String> industries = [
    'Embedded systems',
    'Software engineering',
    'Hardware / electronics',
    'Robotics / autonomy',
    'Artificial intelligence / machine learning',
    'Data science / analytics',
    'Cybersecurity',
    'Consulting',
    'Finance / fintech',
    'Government / defense',
    'Energy / utilities',
    'Manufacturing',
    'Healthcare / medical devices',
    'Telecommunications',
    'Academia / research',
    'Startup / entrepreneurship',
    'Other',
  ];

  // Help topics
  static const List<String> helpTopics = [
    'Resume and interview preparation',
    'Internship search',
    'Technical skill development',
    'Networking',
    'Career planning',
    'Graduate school advice',
    'Work–life balance',
    'Leadership and communication',
  ];

  // Semesters
  static const List<String> semester = ['Fall', 'Spring', 'Summer'];

  // NCSU Organizations (loaded from file)
  static List<String> get ncsuOrgs => _loader.ncsuOrgs;

  /// Get years for graduation dropdown (current year + 12 years)
  static List<String> getGraduationYears() {
    final currentYear = DateTime.now().year;
    return List.generate(12, (index) => (currentYear + index).toString());
  }

  /// Returns the degree-program list for the selected education level.
  static List<String> getDegreeProgramsForLevel(String? educationLevel) {
    if (educationLevel == 'BS') {
      return undergradPrograms;
    }
    if (educationLevel == 'ABM') {
      return abmPrograms;
    }
    if (educationLevel == 'MS') {
      return gradPrograms;
    }
    if (educationLevel == 'PhD') {
      return phdPrograms;
    }
    return [];
  }

  /// Get likert scale label
  static String getLikertLabel(int value) {
    switch (value) {
      case 1:
        return 'Not important';
      case 2:
        return 'Slightly important';
      case 3:
        return 'Important';
      case 4:
        return 'Very important';
      default:
        return '';
    }
  }
}
