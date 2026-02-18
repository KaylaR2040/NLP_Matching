import 'package:flutter/services.dart';

/// Service to load form data from text files in assets
class FormDataLoader {
  static final FormDataLoader _instance = FormDataLoader._internal();
  factory FormDataLoader() => _instance;
  FormDataLoader._internal();

  // Cached data
  List<String>? _ncsuOrgs;
  List<String>? _undergradPrograms;
  List<String>? _gradPrograms;
  List<String>? _concentrations;

  /// Load all data files at app startup
  Future<void> loadAll() async {
    await Future.wait([
      loadNcsuOrgs(),
      loadUndergradPrograms(),
      loadGradPrograms(),
      loadConcentrations(),
    ]);
  }

  /// Load NCSU organizations from text file
  Future<List<String>> loadNcsuOrgs() async {
    if (_ncsuOrgs != null) return _ncsuOrgs!;
    
    try {
      final data = await rootBundle.loadString('assets/data/ncsu_orgs.txt');
      _ncsuOrgs = data
          .split('\n')
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
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
      final data = await rootBundle.loadString('assets/data/undergrad_programs.txt');
      _undergradPrograms = data
          .split('\n')
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
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
      final data = await rootBundle.loadString('assets/data/grad_programs.txt');
      _gradPrograms = data
          .split('\n')
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
      print('Loaded ${_gradPrograms!.length} graduate programs');
      return _gradPrograms!;
    } catch (e) {
      print('Error loading grad programs: $e');
      _gradPrograms = ['Computer Engineering - MS', 'Electrical Engineering - MS'];
      return _gradPrograms!;
    }
  }

  /// Load concentrations from text file
  Future<List<String>> loadConcentrations() async {
    if (_concentrations != null) return _concentrations!;
    
    try {
      final data = await rootBundle.loadString('assets/data/concentrations.txt');
      _concentrations = data
          .split('\n')
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
      print('Loaded ${_concentrations!.length} concentrations');
      return _concentrations!;
    } catch (e) {
      print('Error loading concentrations: $e');
      _concentrations = ['VLSI', 'Power Electronics', 'Signal Processing'];
      return _concentrations!;
    }
  }

  // Getters for cached data (use after loadAll() completes)
  List<String> get ncsuOrgs => _ncsuOrgs ?? [];
  List<String> get undergradPrograms => _undergradPrograms ?? [];
  List<String> get gradPrograms => _gradPrograms ?? [];
  List<String> get concentrations => _concentrations ?? [];

  /// Check if all data is loaded
  bool get isLoaded =>
      _ncsuOrgs != null &&
      _undergradPrograms != null &&
      _gradPrograms != null &&
      _concentrations != null;
}
