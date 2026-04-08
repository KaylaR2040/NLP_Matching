import '../services/form_data_loader.dart';

/// Static option lists used by form widgets.
class FormOptions {
  static final FormDataLoader _loader = FormDataLoader();

  static const List<String> pronouns = [
    'He/him',
    'Other',
    'Prefer not to say',
    'She/her',
    'They/them',
  ];

  static const List<String> educationLevels = [
    'ABM',
    'Alumni',
    'BS',
    'MS',
    'PhD',
  ];

  static const List<String> degreeLevels = ['ABM', 'BS', 'MS', 'Other', 'PhD'];

  static List<String> get undergradPrograms => _loader.undergradPrograms;
  static List<String> get gradPrograms => _loader.gradPrograms;
  static List<String> get abmPrograms => _loader.abmPrograms;
  static List<String> get phdPrograms => _loader.phdPrograms;

  static const List<String> industryFocusAreas = [
    'Artificial intelligence / machine learning',
    'Communications / signal processing',
    'Cybersecurity',
    'Data science / analytics',
    'Embedded systems',
    'Hardware / electronics',
    'Other',
    'Power / energy systems',
    'Robotics / autonomy',
    'Software engineering',
  ];

  static const List<String> studentsCountOptions = ['1 student', '2 students'];

  static const List<String> semester = ['Fall', 'Spring', 'Summer'];

  static const List<String> usStates = [
    'AL',
    'AK',
    'AR',
    'AZ',
    'CA',
    'CO',
    'CT',
    'DC',
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
    'NC',
    'ND',
    'NY',
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
  ];

  static List<String> get ncsuOrgs => _sorted(_loader.ncsuOrgs);

  static List<String> getGraduationYears() {
    final currentYear = DateTime.now().year;
    return List.generate(31, (index) => (currentYear - 25 + index).toString());
  }

  static List<String> getDegreeProgramsForLevels(List<String> levels) {
    final canonicalLevels = levels.map(canonicalDegreeLevel).toSet();
    final programs = <String>{};
    if (canonicalLevels.contains('BS')) {
      programs.addAll(undergradPrograms);
    }
    if (canonicalLevels.contains('ABM')) {
      programs.addAll(abmPrograms);
    }
    if (canonicalLevels.contains('MS')) {
      programs.addAll(gradPrograms);
    }
    if (canonicalLevels.contains('PhD')) {
      programs.addAll(phdPrograms);
    }
    return _sorted(programs.toList());
  }

  static String canonicalDegreeLevel(String level) {
    final normalized = level.trim().toLowerCase().replaceAll('.', '');
    if (normalized == 'bs' || normalized == 'b s') {
      return 'BS';
    }
    if (normalized == 'ms' || normalized == 'm s') {
      return 'MS';
    }
    if (normalized == 'phd' || normalized == 'ph d') {
      return 'PhD';
    }
    if (normalized == 'abm') {
      return 'ABM';
    }
    if (normalized == 'other') {
      return 'Other';
    }
    return level.trim();
  }

  static List<String> _sorted(List<String> values) {
    final sorted = List<String>.from(values);
    sorted.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    return sorted;
  }
}
