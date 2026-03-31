import '../services/form_data_loader.dart';

/// Static option lists used by form widgets.
class FormOptions {
  static final FormDataLoader _loader = FormDataLoader();

  // Pronouns
  static const List<String> pronouns = [
    'He/him',
    "Other",
    'Prefer not to say',
    'She/her',
    'They/them',
  ];

  // Education levels
  static const List<String> educationLevels = ['ABM', 'BS', 'MS', 'PhD'];

  // Load possible majors from files
  static List<String> get undergradPrograms => _loader.undergradPrograms;
  static List<String> get gradPrograms => _loader.gradPrograms;
  static List<String> get abmPrograms => _loader.abmPrograms;
  static List<String> get phdPrograms => _loader.phdPrograms;
  static List<String> get concentrations => _sorted(_loader.concentrations);

  // Experience levels
  static const List<String> experienceLevels = [
    'Completed 1 internship',
    'Completed 2+ internships',
    'Co-op experience',
    'No internships yet',
    'Research experience',
  ];

  // Industries
  static const List<String> industries = [
    'Academia / research',
    'Artificial intelligence / machine learning',
    "ASIC Design & Verification",
    'Consulting',
    'Cybersecurity',
    'Data science / analytics',
    'Embedded systems',
    'Energy / utilities',
    'Finance / fintech',
    'Government / defense',
    'Hardware / electronics',
    'Healthcare / medical devices',
    'Manufacturing',
    'Other',
    'Robotics / autonomy',
    'Software engineering',
    'Startup / entrepreneurship',
    'Telecommunications',
  ];

  // Help topics
  static const List<String> helpTopics = [
    'Career planning',
    'Graduate school advice',
    'Internship search',
    'Leadership and communication',
    'Networking',
    'Resume and interview preparation',
    'Technical skill development',
    'Work–life balance',
  ];

  // Semesters
  static const List<String> semester = ['Fall', 'Spring', 'Summer'];

  // NCSU Organizations (loaded from file)
  static List<String> get ncsuOrgs => _sorted(_loader.ncsuOrgs);

  /// Get years for graduation dropdown (current year + 12 years)
  static List<String> getGraduationYears() {
    final currentYear = DateTime.now().year;
    return List.generate(12, (index) => (currentYear + index).toString());
  }

  /// Returns the degree-program list for the selected education level.
  static List<String> getDegreeProgramsForLevel(String? educationLevel) {
    if (educationLevel == 'BS') {
      return _sorted(undergradPrograms);
    }
    if (educationLevel == 'ABM') {
      return _sorted(abmPrograms);
    }
    if (educationLevel == 'MS') {
      return _sorted(gradPrograms);
    }
    if (educationLevel == 'PhD') {
      return _sorted(phdPrograms);
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

  static List<String> _sorted(List<String> values) {
    final sorted = List<String>.from(values);
    sorted.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    return sorted;
  }
}
