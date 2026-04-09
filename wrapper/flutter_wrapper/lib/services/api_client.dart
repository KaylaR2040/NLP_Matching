import 'dart:convert';

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

class ApiClient {
  final String baseUrl;
  String? _authToken;

  ApiClient({required this.baseUrl});

  String? get authToken => _authToken;

  void setAuthToken(String token) {
    _authToken = token;
  }

  void clearAuthToken() {
    _authToken = null;
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

  void _throwIfError(http.Response response, String operation) {
    if (response.statusCode < 400) {
      return;
    }
    final body =
        response.body.trim().isEmpty ? 'No response body' : response.body;
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw ApiUnauthorizedException(
          '$operation failed (${response.statusCode}): $body');
    }
    throw ApiClientException(
        '$operation failed (${response.statusCode}): $body');
  }

  Future<Map<String, dynamic>> login({
    required String username,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/login'),
      headers: _jsonHeaders(requireAuth: false),
      body: jsonEncode({'username': username, 'password': password}),
    );
    _throwIfError(response, 'login');
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
    final response = await http.post(
      Uri.parse('$baseUrl/logout'),
      headers: _jsonHeaders(requireAuth: true),
      body: '{}',
    );
    _throwIfError(response, 'logout');
  }

  Future<Map<String, dynamic>> getMe() async {
    final response = await http.get(
      Uri.parse('$baseUrl/me'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'get me');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> refreshToken() async {
    final response = await http.post(
      Uri.parse('$baseUrl/token/refresh'),
      headers: _jsonHeaders(requireAuth: true),
      body: '{}',
    );
    _throwIfError(response, 'refresh token');
    final body = _decodeBody(response);
    final token = (body['token'] ?? '').toString();
    if (token.isNotEmpty) {
      _authToken = token;
    }
    return body;
  }

  Future<Map<String, dynamic>> runMatch({
    required SelectedFile menteeFile,
    required SelectedFile mentorFile,
    required Map<String, dynamic> payload,
  }) async {
    final uri = Uri.parse('$baseUrl/run_match');
    final request = http.MultipartRequest('POST', uri)
      ..fields['payload_json'] = jsonEncode(payload)
      ..files.add(http.MultipartFile.fromBytes(
        'mentee_file',
        menteeFile.bytes,
        filename: menteeFile.filename,
      ))
      ..files.add(http.MultipartFile.fromBytes(
        'mentor_file',
        mentorFile.bytes,
        filename: mentorFile.filename,
      ));

    if (_authToken != null && _authToken!.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $_authToken';
    }

    final streamed = await request.send();
    final bodyText = await streamed.stream.bytesToString();
    if (streamed.statusCode >= 400) {
      if (streamed.statusCode == 401 || streamed.statusCode == 403) {
        throw ApiUnauthorizedException(
            'run_match failed (${streamed.statusCode}): $bodyText');
      }
      throw ApiClientException(
          'run_match failed (${streamed.statusCode}): $bodyText');
    }
    final parsed = jsonDecode(bodyText);
    if (parsed is Map<String, dynamic>) {
      return parsed;
    }
    return {'data': parsed};
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
    final uri = Uri.parse('$baseUrl/mentors').replace(queryParameters: params);
    final response = await http.get(
      uri,
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'list mentors');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getMentor(String mentorId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/mentors/$mentorId'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'get mentor');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> createMentor(
      Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse('$baseUrl/mentors'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode(payload),
    );
    _throwIfError(response, 'create mentor');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> updateMentor({
    required String mentorId,
    required Map<String, dynamic> payload,
  }) async {
    final response = await http.put(
      Uri.parse('$baseUrl/mentors/$mentorId'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode(payload),
    );
    _throwIfError(response, 'update mentor');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> deactivateMentor(String mentorId) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/mentors/$mentorId'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'deactivate mentor');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> importMentorsCsv({
    required SelectedFile file,
    String sourceCsvPath = '',
    bool dryRun = false,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/mentors/import-csv'),
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

    final streamed = await request.send();
    final bodyText = await streamed.stream.bytesToString();
    if (streamed.statusCode >= 400) {
      if (streamed.statusCode == 401 || streamed.statusCode == 403) {
        throw ApiUnauthorizedException(
            'import mentors csv failed (${streamed.statusCode}): $bodyText');
      }
      throw ApiClientException(
          'import mentors csv failed (${streamed.statusCode}): $bodyText');
    }

    final parsed = jsonDecode(bodyText);
    if (parsed is Map<String, dynamic>) {
      return parsed;
    }
    return {'data': parsed};
  }

  Future<List<int>> exportMentorsCsv({bool includeInactive = true}) async {
    final response = await http.get(
      Uri.parse('$baseUrl/mentors/export-csv').replace(queryParameters: {
        'include_inactive': includeInactive ? 'true' : 'false'
      }),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'export mentors csv');
    return response.bodyBytes;
  }

  Future<List<int>> exportMentorsXlsx({bool includeInactive = true}) async {
    final response = await http.get(
      Uri.parse('$baseUrl/mentors/export-xlsx').replace(queryParameters: {
        'include_inactive': includeInactive ? 'true' : 'false'
      }),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'export mentors xlsx');
    return response.bodyBytes;
  }

  Future<Map<String, dynamic>> syncMentorsToDefaultCsv(
      {bool includeInactive = true}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/mentors/sync-to-default-csv').replace(
          queryParameters: {
            'include_inactive': includeInactive ? 'true' : 'false'
          }),
      headers: _jsonHeaders(requireAuth: true),
      body: '{}',
    );
    _throwIfError(response, 'sync mentors to default csv');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> enqueueMentorLinkedInEnrichment(
      String mentorId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/mentors/$mentorId/enrich-linkedin'),
      headers: _jsonHeaders(requireAuth: true),
      body: '{}',
    );
    _throwIfError(response, 'linkedin enrichment');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> updateOrgs() async {
    final response = await http.post(
      Uri.parse('$baseUrl/update_orgs'),
      headers: _jsonHeaders(requireAuth: true),
      body: '{}',
    );
    _throwIfError(response, 'update orgs');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> updateConcentrations() async {
    final response = await http.post(
      Uri.parse('$baseUrl/update_concentrations'),
      headers: _jsonHeaders(requireAuth: true),
      body: '{}',
    );
    _throwIfError(response, 'update concentrations');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> listDevFiles() async {
    final response = await http.get(
      Uri.parse('$baseUrl/dev/files'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'list dev files');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getDevFile(String fileKey) async {
    final response = await http.get(
      Uri.parse('$baseUrl/dev/file/$fileKey'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'get dev file');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> saveDevFile({
    required String fileKey,
    required String text,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/dev/file/save'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode({
        'file_key': fileKey,
        'text': text,
      }),
    );
    _throwIfError(response, 'save dev file');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> revertDevFile(String fileKey) async {
    final response = await http.post(
      Uri.parse('$baseUrl/dev/file/revert-last'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode({'file_key': fileKey}),
    );
    _throwIfError(response, 'revert dev file');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> runDevFileUpdate(String fileKey) async {
    final response = await http.post(
      Uri.parse('$baseUrl/dev/file/run-update'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode({'file_key': fileKey}),
    );
    _throwIfError(response, 'run dev file update');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getDevMatchingState() async {
    final response = await http.get(
      Uri.parse('$baseUrl/dev/matching-state'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'get dev matching state');
    return _decodeBody(response);
  }

  Future<Map<String, dynamic>> getMajors() async {
    final response = await http.get(
      Uri.parse('$baseUrl/get_majors'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'get majors');
    return _decodeBody(response);
  }

  Future<void> saveMajors(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/save_majors'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode({'text': text}),
    );
    _throwIfError(response, 'save majors');
  }

  Future<Map<String, dynamic>> getOrgsText() async {
    final response = await http.get(
      Uri.parse('$baseUrl/get_orgs'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'get orgs');
    return _decodeBody(response);
  }

  Future<void> saveOrgsText(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/save_orgs'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode({'text': text}),
    );
    _throwIfError(response, 'save orgs');
  }

  Future<Map<String, dynamic>> getConcentrationsText() async {
    final response = await http.get(
      Uri.parse('$baseUrl/get_concentrations'),
      headers: _jsonHeaders(requireAuth: true),
    );
    _throwIfError(response, 'get concentrations');
    return _decodeBody(response);
  }

  Future<void> saveConcentrationsText(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/save_concentrations'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode({'text': text}),
    );
    _throwIfError(response, 'save concentrations');
  }

  Future<List<int>> exportAssignments(List<Map<String, dynamic>> rows) async {
    final response = await http.post(
      Uri.parse('$baseUrl/export_assignments'),
      headers: _jsonHeaders(requireAuth: true),
      body: jsonEncode({
        'rows': rows,
        'filename': 'final_assignments.xlsx',
      }),
    );
    _throwIfError(response, 'export assignments');
    return response.bodyBytes;
  }
}
