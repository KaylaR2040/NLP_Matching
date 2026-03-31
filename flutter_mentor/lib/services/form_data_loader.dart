import 'package:flutter/services.dart';

/// Loads and caches option data from text files in assets.
class FormDataLoader {
  static final FormDataLoader _instance = FormDataLoader._internal();
  factory FormDataLoader() => _instance;
  FormDataLoader._internal();

  List<String>? _ncsuOrgs;
  List<String>? _undergradPrograms;
  List<String>? _gradPrograms;
  List<String>? _abmPrograms;
  List<String>? _phdPrograms;

  Future<void> loadAll() async {
    await Future.wait([
      loadNcsuOrgs(),
      loadUndergradPrograms(),
      loadGradPrograms(),
      loadAbmPrograms(),
      loadPhdPrograms(),
    ]);
  }

  List<String> get ncsuOrgs => _ncsuOrgs ?? [];
  List<String> get undergradPrograms => _undergradPrograms ?? [];
  List<String> get gradPrograms => _gradPrograms ?? [];
  List<String> get abmPrograms => _abmPrograms ?? [];
  List<String> get phdPrograms => _phdPrograms ?? [];

  Future<List<String>> _loadFile(String path) async {
    try {
      final data = await rootBundle.loadString(path);
      final values = data
          .split('\n')
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
      values.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
      return values;
    } catch (e) {
      print('Error loading $path: $e');
      return [];
    }
  }

  Future<List<String>> loadNcsuOrgs() async {
    _ncsuOrgs ??= await _loadFile('assets/data/ncsu_orgs.txt');
    return _ncsuOrgs!;
  }

  Future<List<String>> loadUndergradPrograms() async {
    _undergradPrograms ??= await _loadFile(
      'assets/data/undergrad_programs.txt',
    );
    return _undergradPrograms!;
  }

  Future<List<String>> loadGradPrograms() async {
    _gradPrograms ??= await _loadFile('assets/data/grad_programs.txt');
    return _gradPrograms!;
  }

  Future<List<String>> loadAbmPrograms() async {
    _abmPrograms ??= await _loadFile('assets/data/abm_programs.txt');
    return _abmPrograms!;
  }

  Future<List<String>> loadPhdPrograms() async {
    _phdPrograms ??= await _loadFile('assets/data/phd_programs.txt');
    return _phdPrograms!;
  }
}
