import '../models/organization_record.dart';

class OrganizationAliasIndex {
  static const Set<String> _stopWords = {
    'a',
    'an',
    'and',
    'at',
    'for',
    'in',
    'of',
    'on',
    'the',
    'to',
  };

  final Map<String, Set<String>> _strongAliases = <String, Set<String>>{};
  final Map<String, Set<String>> _weakAliases = <String, Set<String>>{};

  List<String> lookup(String query) {
    final normalizedQuery = _normalize(query);
    if (normalizedQuery.isEmpty) {
      return const [];
    }

    final results = <String>[];
    final seen = <String>{};

    void appendMatches(Map<String, Set<String>> aliases) {
      final matches = aliases[normalizedQuery];
      if (matches == null) {
        return;
      }

      for (final match in matches) {
        final normalizedMatch = _normalize(match);
        if (seen.add(normalizedMatch)) {
          results.add(match);
        }
      }
    }

    appendMatches(_strongAliases);
    appendMatches(_weakAliases);

    if (results.isEmpty) {
      return const [];
    }

    return results;
  }

  void preloadNames(Iterable<String> names) {
    for (final name in names) {
      _learnName(name);
    }
  }

  void learnRecord(OrganizationRecord record) {
    if (!record.isValid) {
      return;
    }

    _addAlias(_strongAliases, _slugFromLink(record.link), record.name);
    _learnName(record.name);
  }

  Map<String, List<String>> snapshot() {
    final snapshot = <String, Set<String>>{};

    void mergeAliases(Map<String, Set<String>> aliases) {
      aliases.forEach((key, value) {
        snapshot.putIfAbsent(key, () => <String>{}).addAll(value);
      });
    }

    mergeAliases(_strongAliases);
    mergeAliases(_weakAliases);

    return snapshot.map((key, value) => MapEntry(key, value.toList()..sort()));
  }

  void _learnName(String rawName) {
    final name = rawName.trim();
    if (name.isEmpty) {
      return;
    }

    _addAlias(_weakAliases, _acronymFromName(name), name);

    for (final token in _tokenize(name)) {
      if (token.length >= 4) {
        _addAlias(_weakAliases, token, name);
      }
    }
  }

  void _addAlias(Map<String, Set<String>> aliases, String alias, String name) {
    if (alias.isEmpty) {
      return;
    }

    aliases.putIfAbsent(alias, () => <String>{}).add(name.trim());
  }

  String _slugFromLink(String link) {
    final trimmed = link.trim();
    if (trimmed.isEmpty) {
      return '';
    }

    final segments = trimmed.split('/').where((segment) => segment.isNotEmpty);
    if (segments.isEmpty) {
      return '';
    }

    return _normalize(segments.last);
  }

  String _acronymFromName(String name) {
    final words = _tokenize(
      name,
    ).where((word) => !_stopWords.contains(word)).toList();
    if (words.length < 2) {
      return '';
    }

    return words.map((word) => word[0]).join();
  }

  List<String> _tokenize(String text) {
    return text
        .split(RegExp(r'[^A-Za-z0-9]+'))
        .map(_normalize)
        .where((token) => token.isNotEmpty)
        .toList();
  }

  String _normalize(String value) => value.trim().toLowerCase();
}
