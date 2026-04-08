import 'package:flutter/services.dart';

/// Loads and caches option data from text files in assets.
class FormDataLoader {
  static final FormDataLoader _instance = FormDataLoader._internal();
  static const String _dataDir = 'assets/data';
  factory FormDataLoader() => _instance;
  FormDataLoader._internal();

  // Cached options loaded at startup.
  List<String>? _ncsuOrgs;
  List<String>? _undergradPrograms;
  List<String>? _gradPrograms;
  List<String>? _abmPrograms;
  List<String>? _phdPrograms;
  List<String>? _concentrations;

  String _dataPath(String fileName) => '$_dataDir/$fileName';

  String _canonicalizeDegreeProgramLine(String raw) {
    var value = raw.trim();
    value = value.replaceAll(
      RegExp(r'\bM\.?\s*S\.?\b', caseSensitive: false),
      'MS',
    );
    value = value.replaceAll(
      RegExp(r'\bB\.?\s*S\.?\b', caseSensitive: false),
      'BS',
    );
    value = value.replaceAll(
      RegExp(r'\bPh\.?\s*D\.?\b', caseSensitive: false),
      'PhD',
    );
    value = value.replaceAll(RegExp(r'\s+'), ' ');
    return value;
  }

  /// Loads all files required by the form before rendering options.
  Future<void> loadAll() async {
    await Future.wait([
      loadNcsuOrgs(),
      loadUndergradPrograms(),
      loadGradPrograms(),
      loadAbmPrograms(),
      loadPhdPrograms(),
      loadConcentrations(),
    ]);
  }

  /// Load NCSU organizations from text file
  Future<List<String>> loadNcsuOrgs() async {
    if (_ncsuOrgs != null) return _ncsuOrgs!;

    try {
      final data = await rootBundle.loadString(_dataPath('ncsu_orgs.txt'));
      _ncsuOrgs = data
          .split('\n')
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
      _ncsuOrgs!.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
      print('Loaded ${_ncsuOrgs!.length} NCSU organizations');
      return _ncsuOrgs!;
    } catch (e) {
      print('Error loading NCSU orgs: $e');
      _ncsuOrgs = [];
      return _ncsuOrgs!;
    }
  }

  /// Load undergraduate programs from text file
  Future<List<String>> loadUndergradPrograms() async {
    if (_undergradPrograms != null) return _undergradPrograms!;

    try {
      final data = await rootBundle.loadString(
        _dataPath('undergrad_programs.txt'),
      );
      _undergradPrograms = data
          .split('\n')
          .map((line) => _canonicalizeDegreeProgramLine(line))
          .where((line) => line.isNotEmpty)
          .toList();
      _undergradPrograms!.sort(
        (a, b) => a.toLowerCase().compareTo(b.toLowerCase()),
      );
      print('Loaded ${_undergradPrograms!.length} undergraduate programs');
      return _undergradPrograms!;
    } catch (e) {
      print('Error loading undergrad programs: $e');
      _undergradPrograms = ['Computer Engineering', 'Electrical Engineering'];
      return _undergradPrograms!;
    }
  }

  /// Load graduate programs from text file
  Future<List<String>> loadGradPrograms() async {
    if (_gradPrograms != null) return _gradPrograms!;

    try {
      final data = await rootBundle.loadString(_dataPath('grad_programs.txt'));
      _gradPrograms = data
          .split('\n')
          .map((line) => _canonicalizeDegreeProgramLine(line))
          .where((line) => line.isNotEmpty)
          .toList();
      _gradPrograms!.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
      print('Loaded ${_gradPrograms!.length} graduate programs');
      return _gradPrograms!;
    } catch (e) {
      print('Error loading grad programs: $e');
      _gradPrograms = [
        'Computer Engineering - MS',
        'Electrical Engineering - MS',
      ];
      return _gradPrograms!;
    }
  }

  /// Load concentrations from text file
  Future<List<String>> loadConcentrations() async {
    if (_concentrations != null) return _concentrations!;
    try {
      final data = await rootBundle.loadString(_dataPath('concentrations.txt'));
      _concentrations = data
          .split('\n')
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
      _concentrations!.sort(
        (a, b) => a.toLowerCase().compareTo(b.toLowerCase()),
      );
      print('Loaded ${_concentrations!.length} concentrations');
      return _concentrations!;
    } catch (e) {
      print('Error loading concentrations: $e');
      _concentrations = [];
      return _concentrations!;
    }
  }

  /// Load ABM programs from text file
  Future<List<String>> loadAbmPrograms() async {
    if (_abmPrograms != null) return _abmPrograms!;

    try {
      final data = await rootBundle.loadString(_dataPath('abm_programs.txt'));
      _abmPrograms = data
          .split('\n')
          .map((line) => _canonicalizeDegreeProgramLine(line))
          .where((line) => line.isNotEmpty)
          .toList();
      _abmPrograms!.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
      print('Loaded ${_abmPrograms!.length} ABM programs');
      return _abmPrograms!;
    } catch (e) {
      print('Error loading ABM programs: $e');
      _abmPrograms = [
        'Computer Engineering - ABM',
        'Electrical Engineering - ABM',
      ];
      return _abmPrograms!;
    }
  }

  /// Load PhD programs from text file
  Future<List<String>> loadPhdPrograms() async {
    if (_phdPrograms != null) return _phdPrograms!;

    try {
      final data = await rootBundle.loadString(_dataPath('phd_programs.txt'));
      _phdPrograms = data
          .split('\n')
          .map((line) => _canonicalizeDegreeProgramLine(line))
          .where((line) => line.isNotEmpty)
          .toList();
      _phdPrograms!.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
      print('Loaded ${_phdPrograms!.length} PhD programs');
      return _phdPrograms!;
    } catch (e) {
      print('Error loading PhD programs: $e');
      _phdPrograms = [
        'Computer Engineering - PhD',
        'Electrical Engineering - PhD',
      ];
      return _phdPrograms!;
    }
  }

  // Read-only getters (safe after loadAll completes).
  List<String> get ncsuOrgs => _ncsuOrgs ?? [];
  List<String> get undergradPrograms => _undergradPrograms ?? [];
  List<String> get gradPrograms => _gradPrograms ?? [];
  List<String> get abmPrograms => _abmPrograms ?? [];
  List<String> get phdPrograms => _phdPrograms ?? [];
  List<String> get concentrations => _concentrations ?? [];

  /// True once all required files are loaded or defaulted.
  bool get isLoaded =>
      _ncsuOrgs != null &&
      _undergradPrograms != null &&
      _gradPrograms != null &&
      _abmPrograms != null &&
      _phdPrograms != null &&
      _concentrations != null;
}
