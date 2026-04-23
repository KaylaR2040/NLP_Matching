import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class SelectedFile {
  final String filename;
  final List<int> bytes;

  const SelectedFile({required this.filename, required this.bytes});
}

class ApiClientException implements Exception {
  final String message;

  const ApiClientException(this.message);

  @override
  String toString() => message;
}

class ApiUnauthorizedException extends ApiClientException {
  const ApiUnauthorizedException(super.message);
}

// ApiSessionExpiredException extends ApiUnauthorizedException so that
// `on ApiUnauthorizedException` handlers in every screen catch it correctly.
class ApiSessionExpiredException extends ApiUnauthorizedException {
  const ApiSessionExpiredException(super.message);
}

class ApiClient {
  final String baseUrl;
  String? _authToken;

  static const bool _apiDebugEnabled =
      bool.fromEnvironment('WRAPPER_API_DEBUG', defaultValue: true);

  ApiClient({required String baseUrl}) : baseUrl = _normalizeBaseUrl(baseUrl) {
    _log('api_client_initialized base_url=$this.baseUrl');
  }

  String? get authToken => _authToken;

  void setAuthToken(String token) {
    _authToken = token;
  }

  void clearAuthToken() {
    _authToken = null;
  }

  static String _normalizeBaseUrl(String raw) {
    final value = raw.trim();
    if (value.isEmpty || value.contains('|')) {
      throw ApiClientException("Invalid API base URL: '$raw'");
    }
    final parsed = Uri.tryParse(value);
    if (parsed == null ||
        parsed.host.trim().isEmpty ||
        (parsed.scheme != 'http' && parsed.scheme != 'https')) {
      throw ApiClientException("Invalid API base URL: '$raw'");
    }
    final port = parsed.hasPort ? ':${parsed.port}' : '';
    return '${parsed.scheme}://${parsed.host}$port';
  }

  static void _log(String message) {
    if (_apiDebugEnabled) {
      debugPrint(message);
    }
  }

  Uri _uri(String path, {Map<String, String>? queryParameters}) {
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$baseUrl$normalizedPath')
        .replace(queryParameters: queryParameters);
  }

  Map<String, String> _jsonHeaders({bool requireAuth = true}) {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (requireAuth && _authToken != null && _authToken!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_authToken';
    }
    return headers;
  }

  Map<String, dynamic> _decodeBody(http.Response response) {
    if (response.body.trim().isEmpty) {
      return {};
    }
    final parsed = jsonDecode(response.body);
    if (parsed is Map<String, dynamic>) {
      return parsed;
    }
    return {'data': parsed};
  }

  String _truncate(String value, {int maxLength = 1200}) {
    if (value.length <= maxLength) {
      return value;
    }
    return '${value.substring(0, maxLength)}...(truncated)';
  }

  String _errorMessageFromBodyText(String bodyText) {
    final trimmed = bodyText.trim();
    if (trimmed.isEmpty) {
      return 'No response body';
    }
    try {
      final parsed = jsonDecode(trimmed);
      if (parsed is Map<String, dynamic>) {
        final detail = parsed['detail'];
        if (detail is String && detail.trim().isNotEmpty) {
          return detail.trim();
        }
        if (detail is Map<String, dynamic>) {
          final message = (detail['message'] ?? '').toString().trim();
          if (message.isNotEmpty) {
            return message;
          }
        }
        final message = (parsed['message'] ?? '').toString().trim();
        if (message.isNotEmpty) {
          return message;
        }
      }
    } catch (_) {
      // Fall back to raw text for non-JSON error bodies.
    }
    return trimmed;
  }

  void _throwIfError(
    http.Response response,
    String operation, {
    Uri? uri,
    bool expireSessionOnAuthFailure = false,
  }) {
    if (response.statusCode < 400) {
      return;
    }
    final body =
        response.body.trim().isEmpty ? 'No response body' : response.body;
    final errorMessage = _errorMessageFromBodyText(body);
    _log(
      'api_response_error operation=$operation method=HTTP status=${response.statusCode} '
      'url=${uri ?? "unknown"} body=${_truncate(body)}',
    );
    if ((response.statusCode == 401 || response.statusCode == 403) &&
        expireSessionOnAuthFailure) {
      throw ApiSessionExpiredException(
          '$operation failed (${response.statusCode}): $errorMessage');
    }
    throw ApiClientException(
        '$operation failed (${response.statusCode}): $errorMessage');
  }

  void _throwMultipartIfError(
    int statusCode,
    String operation,
    String bodyText, {
    required Uri uri,
    bool expireSessionOnAuthFailure = false,
  }) {
    _log(
      'api_response_error operation=$operation method=MULTIPART status=$statusCode '
      'url=$uri body=${_truncate(bodyText)}',
    );
    final errorMessage = _errorMessageFromBodyText(bodyText);
    if ((statusCode == 401 || statusCode == 403) &&
        expireSessionOnAuthFailure) {
      throw ApiSessionExpiredException(
          '$operation failed ($statusCode): $errorMessage');
    }
    throw ApiClientException('$operation failed ($statusCode): $errorMessage');
  }

  Future<http.Response> _request({
    required String method,
    required Uri uri,
    required String operation,
    bool requireAuth = true,
    // Default true: any 401/403 on an authenticated call triggers re-login.
    // Pass false only for calls where 401 has different semantics (e.g. login).
    bool expireSessionOnAuthFailure = true,
    Object? body,
    Map<String, String>? headers,
  }) async {
    _log('api_request method=$method url=$uri');
    try {
      final mergedHeaders = headers ?? _jsonHeaders(requireAuth: requireAuth);
      late final http.Response response;
      switch (method.toUpperCase()) {
        case 'GET':
          response = await http.get(uri, headers: mergedHeaders);
          break;
        case 'POST':
          response = await http.post(uri, headers: mergedHeaders, body: body);
          break;
        case 'PUT':
          response = await http.put(uri, headers: mergedHeaders, body: body);
          break;
        case 'DELETE':
          response = await http.delete(uri, headers: mergedHeaders, body: body);
          break;
        default:
          throw ApiClientException('Unsupported method: $method');
      }
      _throwIfError(
        response,
        operation,
        uri: uri,
        expireSessionOnAuthFailure: expireSessionOnAuthFailure,
      );
      return response;
    } on ApiClientException {
      rethrow;
    } catch (e) {
      _log(
        'api_transport_error operation=$operation method=$method url=$uri error=$e',
      );
      throw ApiClientException('$operation failed (network): $e');
    }
  }

  Future<Map<String, dynamic>> _sendMultipartJson({
    required String operation,
    required http.MultipartRequest request,
    // Default true: any 401/403 triggers re-login (same as _request).
    bool expireSessionOnAuthFailure = true,
  }) async {
    _log('api_request method=MULTIPART url=${request.url}');
    try {
      final streamed = await request.send();
      final bodyText = await streamed.stream.bytesToString();
      if (streamed.statusCode >= 400) {
        _throwMultipartIfError(
          streamed.statusCode,
          operation,
          bodyText,
          uri: request.url,
          expireSessionOnAuthFailure: expireSessionOnAuthFailure,
        );
      }
      if (bodyText.trim().isEmpty) {
        return {};
      }
      final parsed = jsonDecode(bodyText);
      if (parsed is Map<String, dynamic>) {
        return parsed;
      }
      return {'data': parsed};
    } on ApiClientException {
      rethrow;
    } catch (e) {
      _log(
        'api_transport_error operation=$operation method=MULTIPART '
        'url=${request.url} error=$e',
      );
      throw ApiClientException('$operation failed (network): $e');
    }
  }

  Future<Map<String, dynamic>> login({
    required String username,
    required String password,
  }) async {
    final uri = _uri('/login');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'login',
      requireAuth: false,
      // 401 here = wrong credentials, not session expiry — don't trigger re-login flow.
      expireSessionOnAuthFailure: false,
      body: jsonEncode({'username': username, 'password': password}),
    );
    final body = _decodeBody(response);
    final token = (body['token'] ?? '').toString();
    if (token.isEmpty) {
      throw const ApiClientException('login response missing token');
    }
    _authToken = token;
    return body;
  }

  Future<void> logout() async {
    if (_authToken == null || _authToken!.isEmpty) {
      return;
    }
    final uri = _uri('/logout');
    await _request(
      method: 'POST',
      uri: uri,
      operation: 'logout',
      body: '{}',
    );
  }

  Future<Map<String, dynamic>> getMe() async {
    final uri = _uri('/me');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get me',
      expireSessionOnAuthFailure: true,
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> refreshToken() async {
    final uri = _uri('/token/refresh');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'refresh token',
      body: '{}',
      expireSessionOnAuthFailure: true,
    );
    final body = _decodeBody(response);
    final token = (body['token'] ?? '').toString();
    if (token.isNotEmpty) {
      _authToken = token;
    }
    return body;
  }

  Future<Map<String, dynamic>> runMatch({
    required SelectedFile menteeFile,
    required Map<String, dynamic> payload,
  }) async {
    final uri = _uri('/run_match');
    final request = http.MultipartRequest('POST', uri)
      ..fields['payload_json'] = jsonEncode(payload)
      ..files.add(http.MultipartFile.fromBytes(
        'mentee_file',
        menteeFile.bytes,
        filename: menteeFile.filename,
      ));

    if (_authToken != null && _authToken!.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $_authToken';
    }
    return _sendMultipartJson(operation: 'run_match', request: request);
  }

  Future<Map<String, dynamic>> listMentors({
    String query = '',
    bool? activeOnly,
    bool? hasLinkedIn,
    String company = '',
    String location = '',
    int offset = 0,
    int limit = 200,
  }) async {
    final params = <String, String>{
      if (query.trim().isNotEmpty) 'q': query.trim(),
      if (activeOnly != null) 'active_only': activeOnly ? 'true' : 'false',
      if (hasLinkedIn != null) 'has_linkedin': hasLinkedIn ? 'true' : 'false',
      if (company.trim().isNotEmpty) 'company': company.trim(),
      if (location.trim().isNotEmpty) 'location': location.trim(),
      'offset': '$offset',
      'limit': '$limit',
    };
    final uri = _uri('/mentors', queryParameters: params);
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'list mentors',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getMentor(String mentorId) async {
    final uri = _uri('/mentors/$mentorId');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get mentor',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> createMentor(
      Map<String, dynamic> payload) async {
    final uri = _uri('/mentors');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'create mentor',
      body: jsonEncode(payload),
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> updateMentor({
    required String mentorId,
    required Map<String, dynamic> payload,
  }) async {
    final uri = _uri('/mentors/$mentorId');
    final response = await _request(
      method: 'PUT',
      uri: uri,
      operation: 'update mentor',
      body: jsonEncode(payload),
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> deactivateMentor(String mentorId) async {
    final uri = _uri('/mentors/$mentorId');
    final response = await _request(
      method: 'DELETE',
      uri: uri,
      operation: 'deactivate mentor',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> importMentorsCsv({
    required SelectedFile file,
    String sourceCsvPath = '',
    bool dryRun = false,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      _uri('/mentors/import-csv'),
    )
      ..fields['source_csv_path'] = sourceCsvPath
      ..fields['dry_run'] = dryRun ? 'true' : 'false'
      ..files.add(http.MultipartFile.fromBytes(
        'file',
        file.bytes,
        filename: file.filename,
      ));

    if (_authToken != null && _authToken!.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $_authToken';
    }
    return _sendMultipartJson(
        operation: 'import mentors csv', request: request);
  }

  Future<List<int>> exportMentorsCsv({bool includeInactive = true}) async {
    final uri = _uri(
      '/mentors/export-csv',
      queryParameters: {'include_inactive': includeInactive ? 'true' : 'false'},
    );
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'export mentors csv',
    );
    return response.bodyBytes;
  }

  Future<List<int>> exportMentorsXlsx({bool includeInactive = true}) async {
    final uri = _uri(
      '/mentors/export-xlsx',
      queryParameters: {'include_inactive': includeInactive ? 'true' : 'false'},
    );
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'export mentors xlsx',
    );
    return response.bodyBytes;
  }

  Future<Map<String, dynamic>> enqueueMentorLinkedInEnrichment(
      String mentorId) async {
    final uri = _uri('/mentors/$mentorId/enrich-linkedin');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'linkedin enrichment',
      body: '{}',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getLinkedInEnrichmentConfig() async {
    final uri = _uri('/mentors/linkedin-enrichment/config');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get linkedin enrichment config',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> bulkDeleteMentors(List<String> mentorIds) async {
    final uri = _uri('/mentors/bulk-delete');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'bulk delete mentors',
      body: jsonEncode({'mentor_ids': mentorIds}),
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> updateOrgs() async {
    final uri = _uri('/update_orgs');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'update orgs',
      body: '{}',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> updateConcentrations() async {
    final uri = _uri('/update_concentrations');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'update concentrations',
      body: '{}',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> listDevFiles() async {
    final uri = _uri('/dev/files');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'list dev files',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getDevFile(String fileKey) async {
    final uri = _uri('/dev/file/$fileKey');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get dev file',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> saveDevFile({
    required String fileKey,
    required String text,
  }) async {
    final uri = _uri('/dev/file/save');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'save dev file',
      body: jsonEncode({
        'file_key': fileKey,
        'text': text,
      }),
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> revertDevFile(String fileKey) async {
    final uri = _uri('/dev/file/revert-last');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'revert dev file',
      body: jsonEncode({'file_key': fileKey}),
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> runDevFileUpdate(String fileKey) async {
    final uri = _uri('/dev/file/run-update');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'run dev file update',
      body: jsonEncode({'file_key': fileKey}),
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getDevMatchingState() async {
    final uri = _uri('/dev/matching-state');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get dev matching state',
    );
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getMajors() async {
    final uri = _uri('/get_majors');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get majors',
    );
    return _decodeBody(response);
  }

  Future<void> saveMajors(String text) async {
    final uri = _uri('/save_majors');
    await _request(
      method: 'POST',
      uri: uri,
      operation: 'save majors',
      body: jsonEncode({'text': text}),
    );
  }

  Future<Map<String, dynamic>> getOrgsText() async {
    final uri = _uri('/get_orgs');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get orgs',
    );
    return _decodeBody(response);
  }

  Future<void> saveOrgsText(String text) async {
    final uri = _uri('/save_orgs');
    await _request(
      method: 'POST',
      uri: uri,
      operation: 'save orgs',
      body: jsonEncode({'text': text}),
    );
  }

  Future<Map<String, dynamic>> getConcentrationsText() async {
    final uri = _uri('/get_concentrations');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get concentrations',
    );
    return _decodeBody(response);
  }

  Future<void> saveConcentrationsText(String text) async {
    final uri = _uri('/save_concentrations');
    await _request(
      method: 'POST',
      uri: uri,
      operation: 'save concentrations',
      body: jsonEncode({'text': text}),
    );
  }

  Future<List<int>> exportAssignments(List<Map<String, dynamic>> rows) async {
    final uri = _uri('/export_assignments');
    final response = await _request(
      method: 'POST',
      uri: uri,
      operation: 'export assignments',
      body: jsonEncode({
        'rows': rows,
        'filename': 'final_assignments.xlsx',
      }),
    );
    return response.bodyBytes;
  }

  Future<List<Map<String, dynamic>>> listMatchResults({int limit = 20}) async {
    final uri = _uri('/match-results', queryParameters: {'limit': '$limit'});
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'list match results',
    );
    // Backend returns a JSON array, not an object, so decode directly.
    final decoded = jsonDecode(response.body);
    if (decoded is List) {
      return decoded.whereType<Map<String, dynamic>>().toList();
    }
    return const [];
  }

  Future<Map<String, dynamic>> getMatchResult(int id) async {
    final uri = _uri('/match-results/$id');
    final response = await _request(
      method: 'GET',
      uri: uri,
      operation: 'get match result',
    );
    return _decodeBody(response);
  }
}
