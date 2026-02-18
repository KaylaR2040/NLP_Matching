import '../services/form_data_loader.dart';

/// Constants for form dropdown options and lists
class FormOptions {
  // Get the data loader instance
  static final FormDataLoader _loader = FormDataLoader();

  // Pronouns
  static const List<String> pronouns = [
    'She/her',
    'He/him',
    'They/them',
    'Prefer not to say',
  ];

  // Education levels
  static const List<String> educationLevels = [
    'BS',
    'MS',
    'PhD',
    'BS+MS',
  ];

  // Degree programs - Undergraduate (loaded from file)
  static List<String> get undergradPrograms => _loader.undergradPrograms;

  // Degree programs - Graduate (loaded from file)
  static List<String> get gradPrograms => _loader.gradPrograms;

  // Concentrations (loaded from file)
  static List<String> get concentrations => _loader.concentrations;

  // Academic interests
  static const List<String> academicInterests = [
    'Embedded systems',
    'Software engineering',
    'Hardware / electronics',
    'Robotics / autonomy',
    'Artificial intelligence / machine learning',
    'Data science / analytics',
    'Cybersecurity',
    'Power / energy systems',
    'Communications / signal processing',
    'Other',
  ];

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

  // Meeting frequencies
  static const List<String> meetingFrequencies = [
    'Weekly',
    'Bimonthly',
    'Monthly',
    'Flexible',
  ];

  // Communication methods
  static const List<String> communicationMethods = [
    'Video call',
    'Phone',
    'Email',
    'Messaging',
  ];

  // Months
  static const List<String> months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  // NCSU Organizations (loaded from file)
  static List<String> get ncsuOrgs => _loader.ncsuOrgs;

  /// Get years for graduation dropdown (current year + 12 years)
  static List<String> getGraduationYears() {
    final currentYear = DateTime.now().year;
    return List.generate(12, (index) => (currentYear + index).toString());
  }

  /// Get degree programs based on education level
  static List<String> getDegreeProgramsForLevel(String? educationLevel) {
    if (educationLevel == 'BS') {
      return undergradPrograms;
    }
    return gradPrograms;
  }

  /// Get meeting frequency display name
  static String getMeetingFrequencyDisplay(String frequency) {
    switch (frequency) {
      case 'Bimonthly':
        return 'Bimonthly (Every 2 weeks)';
      default:
        return frequency;
    }
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
