import 'dart:convert';
import 'package:fuzzywuzzy/fuzzywuzzy.dart';
import 'package:http/http.dart' as http;

import '../models/organization_record.dart';
import 'organization_alias_index.dart';

/// Hybrid organization search: combines local fuzzy results with remote API.
class OrganizationSearchService {
  OrganizationSearchService({
    http.Client? client,
    OrganizationAliasIndex? aliasIndex,
  }) : _client = client ?? http.Client(),
       _aliasIndex = aliasIndex ?? OrganizationAliasIndex();

  static const String _searchUrl =
      'https://getinvolved.ncsu.edu/api/comp-navigation/graphql/getSearchEvents--getSearchForms--getSearchNews--getSearchOrganizations';

  static final OrganizationSearchService shared = OrganizationSearchService();

  final http.Client _client;
  final OrganizationAliasIndex _aliasIndex;

  /// Perform hybrid search and return ranked distinct names.
  Future<List<String>> search(
    String query,
    List<String> localOptions, {
    int limit = 50,
  }) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      return localOptions.take(limit).toList();
    }

    _aliasIndex.preloadNames(localOptions);

    final aliasHits = _aliasIndex.lookup(trimmed);
    final local = _localFuzzy(trimmed, localOptions, limit: limit);
    final remote = await _remoteSearch(trimmed, limit: limit);

    final seen = <String>{};
    final merged = <String>[];

    for (final name in [...aliasHits, ...local, ...remote]) {
      final key = name.toLowerCase().trim();
      if (seen.add(key)) {
        merged.add(name);
        if (merged.length >= limit) break;
      }
    }

    return merged;
  }

  List<String> _localFuzzy(
    String query,
    List<String> options, {
    int limit = 50,
  }) {
    final normalizedQuery = query.toLowerCase();
    final augmented = <String>[...options];

    for (final aliasMatch in _aliasIndex.lookup(normalizedQuery)) {
      if (!augmented.any(
        (option) => option.toLowerCase() == aliasMatch.toLowerCase(),
      )) {
        augmented.add(aliasMatch);
      }
    }

    final results = extractAllSorted(
      query: query,
      choices: augmented,
      cutoff: 10,
    );

    if (results.isEmpty) {
      return augmented
          .where((o) => o.toLowerCase().contains(normalizedQuery))
          .take(limit)
          .toList();
    }

    return results.map((r) => r.choice).take(limit).toList();
  }

  Future<List<String>> _remoteSearch(String query, {int limit = 50}) async {
    try {
      final response = await _client.post(
        Uri.parse(_searchUrl),
        headers: {
          'Content-Type': 'application/json',
          'Accept': '*/*',
          'apollographql-client-name': 'comp-navigation',
          'Origin': 'https://getinvolved.ncsu.edu',
          'Referer': 'https://getinvolved.ncsu.edu/',
        },
        // If the endpoint expects a different shape, adjust here.
        body: jsonEncode({'searchText': query}),
      );

      if (response.statusCode != 200) return const [];

      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      final data = decoded['data'] as Map<String, dynamic>?;
      if (data == null) return const [];

      final raw = data['getSearchOrganizations'] as List<dynamic>?;
      if (raw == null) return const [];

      final names = <String>[];

      for (final item in raw.whereType<Map<String, dynamic>>()) {
        final record = OrganizationRecord.fromMap(item);
        if (!record.isValid) {
          continue;
        }

        _aliasIndex.learnRecord(record);
        names.add(record.name);
      }

      return names.take(limit).toList();
    } catch (_) {
      return const [];
    }
  }

  Map<String, List<String>> get aliasMapSnapshot => _aliasIndex.snapshot();
}
