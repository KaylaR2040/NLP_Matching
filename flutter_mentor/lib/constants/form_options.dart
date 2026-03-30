import '../services/form_data_loader.dart';

/// Static option lists used by form widgets.
class FormOptions {
  static final FormDataLoader _loader = FormDataLoader();

  static const List<String> pronouns = [
    'She/her',
    'He/him',
    'They/them',
    'Prefer not to say',
    'Other',
  ];

  static const List<String> educationLevels = [
    'BS',
    'ABM',
    'MS',
    'PhD',
    'Alumni',
  ];

  static const List<String> degreeLevels = [
    'Undergraduate',
    'ABM',
    'MS',
    'PhD',
    'Other',
  ];

  static List<String> get undergradPrograms => _loader.undergradPrograms;
  static List<String> get gradPrograms => _loader.gradPrograms;
  static List<String> get abmPrograms => _loader.abmPrograms;
  static List<String> get phdPrograms => _loader.phdPrograms;

  static const List<String> industryFocusAreas = [
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

  static const List<String> studentsCountOptions = ['1 student', '2 students'];

  static const List<String> semester = ['Fall', 'Spring', 'Summer'];

  static const List<String> usStates = [
    'AL',
    'AK',
    'AZ',
    'AR',
    'CA',
    'CO',
    'CT',
    'DE',
    'FL',
    'GA',
    'HI',
    'ID',
    'IL',
    'IN',
    'IA',
    'KS',
    'KY',
    'LA',
    'ME',
    'MD',
    'MA',
    'MI',
    'MN',
    'MS',
    'MO',
    'MT',
    'NE',
    'NV',
    'NH',
    'NJ',
    'NM',
    'NY',
    'NC',
    'ND',
    'OH',
    'OK',
    'OR',
    'PA',
    'RI',
    'SC',
    'SD',
    'TN',
    'TX',
    'UT',
    'VT',
    'VA',
    'WA',
    'WV',
    'WI',
    'WY',
    'DC',
  ];

  static List<String> get ncsuOrgs => _loader.ncsuOrgs;

  static List<String> getGraduationYears() {
    final currentYear = DateTime.now().year;
    return List.generate(31, (index) => (currentYear - 25 + index).toString());
  }

  static List<String> getDegreeProgramsForLevels(List<String> levels) {
    final programs = <String>{};
    if (levels.contains('Undergraduate')) {
      programs.addAll(undergradPrograms);
    }
    if (levels.contains('ABM')) {
      programs.addAll(abmPrograms);
    }
    if (levels.contains('MS')) {
      programs.addAll(gradPrograms);
    }
    if (levels.contains('PhD')) {
      programs.addAll(phdPrograms);
    }
    final result = programs.toList();
    result.sort();
    return result;
  }
}
