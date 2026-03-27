import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/mentee_form_data.dart';

class ApiService {
  // Web app host. API requests are expected under /api on the same domain.
  static const String baseUrl = 'https://menteeform.vercel.app/api';

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
