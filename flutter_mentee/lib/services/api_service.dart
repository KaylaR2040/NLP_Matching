import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/mentee_form_data.dart';

// Backend URL for config list fetching.
// Override at build time with: --dart-define=BACKEND_CONFIG_URL=https://your-service.onrender.com
const String _backendConfigUrl = String.fromEnvironment(
  'BACKEND_CONFIG_URL',
  defaultValue: 'https://nlp-mentor-backend.onrender.com',
);

class ApiService {
  // Web app host. API requests are expected under /api on the same domain.
  static const String baseUrl = 'https://menteeform.vercel.app/api';

  /// Fetch a config list (orgs, concentrations, etc.) from the wrapper backend.
  /// Returns a sorted list of strings on success, throws on failure.
  /// Keys: 'orgs', 'concentrations', 'grad-programs', 'abm-programs', 'phd-programs'
  static Future<List<String>> fetchConfigList(String key) async {
    final url = Uri.parse('$_backendConfigUrl/config/$key');
    final response = await http
        .get(url, headers: {'Accept': 'application/json'})
        .timeout(const Duration(seconds: 6));
    if (response.statusCode == 200) {
      final decoded = json.decode(response.body);
      if (decoded is List) {
        return List<String>.from(decoded.whereType<String>());
      }
    }
    throw Exception('Config fetch failed for "$key": HTTP ${response.statusCode}');
  }

  /// Submit a mentee application to the backend
  /// Called when the form submit button is pressed
  static Future<Map<String, dynamic>> submitMenteeApplication(
    MenteeFormData formData,
  ) async {
    try {
      final url = Uri.parse('$baseUrl/mentees');
      final jsonData = formData.toJson();

      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(jsonData),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = _decodeJsonBody(response);
        if (responseData == null) {
          return {
            'success': false,
            'error':
                'Server returned ${response.statusCode} with an empty or non-JSON body.',
          };
        }
        return {'success': true, 'data': responseData};
      }

      final errorData = _decodeJsonBody(response);
      return {
        'success': false,
        'error':
            errorData?['detail']?.toString() ??
            _describeUnexpectedResponse(response),
      };
    } catch (e) {
      return {'success': false, 'error': 'Could not connect to server: $e'};
    }
  }

  static Map<String, dynamic>? _decodeJsonBody(http.Response response) {
    final decoded = _decodeJsonValue(response);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    return null;
  }

  static dynamic _decodeJsonValue(http.Response response) {
    final body = response.body.trim();
    if (body.isEmpty) {
      return null;
    }

    try {
      return json.decode(body);
    } catch (_) {
      return null;
    }
  }

  static String _describeUnexpectedResponse(http.Response response) {
    final body = response.body.trim();
    final preview = body.isEmpty
        ? 'empty response body'
        : body.substring(0, body.length > 160 ? 160 : body.length);

    return 'Server returned ${response.statusCode} with unexpected response: $preview';
  }
}
