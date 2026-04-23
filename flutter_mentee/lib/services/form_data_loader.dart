import 'package:flutter/services.dart';
import 'api_service.dart';

/// Loads and caches option data.
/// Primary source: wrapper backend API (/config/* endpoints).
/// Fallback: bundled asset .txt files (used when backend is unreachable).
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

  List<String> _parseAsset(String data, {bool canonicalizeDegrees = false}) {
    final values = data
        .split('\n')
        .map((line) => canonicalizeDegrees
            ? _canonicalizeDegreeProgramLine(line)
            : line.trim())
        .where((line) => line.isNotEmpty)
        .toSet()
        .toList();
    values.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    return values;
  }

  /// Try fetching [configKey] from backend; on failure fall back to [assetFileName].
  Future<List<String>> _loadWithFallback(
    String configKey,
    String assetFileName, {
    bool canonicalizeDegrees = false,
    List<String> defaultValues = const [],
  }) async {
    try {
      final items = await ApiService.fetchConfigList(configKey);
      if (items.isNotEmpty) {
        if (canonicalizeDegrees) {
          final normalized = items
              .map(_canonicalizeDegreeProgramLine)
              .where((s) => s.isNotEmpty)
              .toSet()
              .toList()
            ..sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
          return normalized;
        }
        return items;
      }
    } catch (_) {
      // Backend unreachable — fall through to asset.
    }
    try {
      final data = await rootBundle.loadString(_dataPath(assetFileName));
      return _parseAsset(data, canonicalizeDegrees: canonicalizeDegrees);
    } catch (e) {
      // ignore: avoid_print
      print('FormDataLoader: error loading asset $assetFileName: $e');
      return defaultValues;
    }
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

  Future<List<String>> loadNcsuOrgs() async {
    if (_ncsuOrgs != null) return _ncsuOrgs!;
    _ncsuOrgs = await _loadWithFallback('orgs', 'ncsu_orgs.txt');
    return _ncsuOrgs!;
  }

  Future<List<String>> loadUndergradPrograms() async {
    if (_undergradPrograms != null) return _undergradPrograms!;
    // undergrad programs are not in the backend config yet — load from asset only.
    try {
      final data = await rootBundle.loadString(_dataPath('undergrad_programs.txt'));
      _undergradPrograms = _parseAsset(data, canonicalizeDegrees: true);
    } catch (e) {
      _undergradPrograms = ['Computer Engineering', 'Electrical Engineering'];
    }
    return _undergradPrograms!;
  }

  Future<List<String>> loadGradPrograms() async {
    if (_gradPrograms != null) return _gradPrograms!;
    _gradPrograms = await _loadWithFallback(
      'grad-programs',
      'grad_programs.txt',
      canonicalizeDegrees: true,
      defaultValues: ['Computer Engineering - MS', 'Electrical Engineering - MS'],
    );
    return _gradPrograms!;
  }

  Future<List<String>> loadConcentrations() async {
    if (_concentrations != null) return _concentrations!;
    _concentrations = await _loadWithFallback('concentrations', 'concentrations.txt');
    return _concentrations!;
  }

  Future<List<String>> loadAbmPrograms() async {
    if (_abmPrograms != null) return _abmPrograms!;
    _abmPrograms = await _loadWithFallback(
      'abm-programs',
      'abm_programs.txt',
      canonicalizeDegrees: true,
      defaultValues: ['Computer Engineering - ABM', 'Electrical Engineering - ABM'],
    );
    return _abmPrograms!;
  }

  Future<List<String>> loadPhdPrograms() async {
    if (_phdPrograms != null) return _phdPrograms!;
    _phdPrograms = await _loadWithFallback(
      'phd-programs',
      'phd_programs.txt',
      canonicalizeDegrees: true,
      defaultValues: ['Computer Engineering - PhD', 'Electrical Engineering - PhD'],
    );
    return _phdPrograms!;
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
