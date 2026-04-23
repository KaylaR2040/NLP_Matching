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

  List<String>? _ncsuOrgs;
  List<String>? _undergradPrograms;
  List<String>? _gradPrograms;
  List<String>? _abmPrograms;
  List<String>? _phdPrograms;

  bool _isDegreeFilePath(String path) {
    return path.endsWith('undergrad_programs.txt') ||
        path.endsWith('grad_programs.txt') ||
        path.endsWith('abm_programs.txt') ||
        path.endsWith('phd_programs.txt');
  }

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

  List<String> _parseLines(String text, {bool canonicalizeDegrees = false}) {
    final values = text
        .split('\n')
        .map((line) => line.trim())
        .map((line) => canonicalizeDegrees ? _canonicalizeDegreeProgramLine(line) : line)
        .where((line) => line.isNotEmpty)
        .toSet()
        .toList();
    values.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    return values;
  }

  Future<List<String>> _loadFile(String path) async {
    try {
      final normalizeDegreeLine = _isDegreeFilePath(path);
      final data = await rootBundle.loadString(path);
      return _parseLines(data, canonicalizeDegrees: normalizeDegreeLine);
    } catch (e) {
      // ignore: avoid_print
      print('FormDataLoader: error loading asset $path: $e');
      return [];
    }
  }

  /// Try fetching [configKey] from backend; on failure fall back to [assetPath].
  Future<List<String>> _loadWithFallback(
    String configKey,
    String assetPath, {
    bool canonicalizeDegrees = false,
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
    return _loadFile(assetPath);
  }

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

  Future<List<String>> loadNcsuOrgs() async {
    _ncsuOrgs ??= await _loadWithFallback('orgs', '$_dataDir/ncsu_orgs.txt');
    return _ncsuOrgs!;
  }

  Future<List<String>> loadUndergradPrograms() async {
    // undergrad programs are not yet in the backend config — load from asset only.
    _undergradPrograms ??= await _loadFile('$_dataDir/undergrad_programs.txt');
    return _undergradPrograms!;
  }

  Future<List<String>> loadGradPrograms() async {
    _gradPrograms ??= await _loadWithFallback(
      'grad-programs',
      '$_dataDir/grad_programs.txt',
      canonicalizeDegrees: true,
    );
    return _gradPrograms!;
  }

  Future<List<String>> loadAbmPrograms() async {
    _abmPrograms ??= await _loadWithFallback(
      'abm-programs',
      '$_dataDir/abm_programs.txt',
      canonicalizeDegrees: true,
    );
    return _abmPrograms!;
  }

  Future<List<String>> loadPhdPrograms() async {
    _phdPrograms ??= await _loadWithFallback(
      'phd-programs',
      '$_dataDir/phd_programs.txt',
      canonicalizeDegrees: true,
    );
    return _phdPrograms!;
  }
}
