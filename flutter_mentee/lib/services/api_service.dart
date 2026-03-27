import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/mentee_form_data.dart';

/// API service to connect the Flutter mentee form to the backend
///
/// Data flow:
///   Flutter form -> toJson() -> POST /api/mentees -> backend stores in mentees.json
///   NLP matcher reads from mentees.json (NOT from the old data/ CSV files)
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

  /// Get all submitted mentees
  static Future<List<dynamic>> getAllMentees() async {
    try {
      final url = Uri.parse('$baseUrl/mentees');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = _decodeJsonValue(response);
        if (data is List<dynamic>) {
          return data;
        }
        throw Exception(_describeUnexpectedResponse(response));
      }
      throw Exception('Failed to load mentees');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Get backend statistics
  static Future<Map<String, dynamic>> getStats() async {
    try {
      final url = Uri.parse('$baseUrl/stats');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = _decodeJsonValue(response);
        if (data is Map<String, dynamic>) {
          return data;
        }
        throw Exception(_describeUnexpectedResponse(response));
      }
      throw Exception('Failed to load statistics');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Trigger the NLP matching algorithm
  static Future<Map<String, dynamic>> runMatching({int topK = 5}) async {
    try {
      final url = Uri.parse('$baseUrl/matching/run?top_k=$topK');
      final response = await http.post(url);
      if (response.statusCode == 200) {
        final data = _decodeJsonValue(response);
        if (data is Map<String, dynamic>) {
          return data;
        }
        throw Exception(_describeUnexpectedResponse(response));
      }
      final errorData = _decodeJsonBody(response);
      throw Exception(
        errorData?['detail']?.toString() ??
            _describeUnexpectedResponse(response),
      );
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Get matches for a specific mentee
  static Future<Map<String, dynamic>> getMenteeMatches(
    String menteeId, {
    int topK = 5,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/matching/mentee/$menteeId?top_k=$topK');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = _decodeJsonValue(response);
        if (data is Map<String, dynamic>) {
          return data;
        }
        throw Exception(_describeUnexpectedResponse(response));
      }
      final errorData = _decodeJsonBody(response);
      throw Exception(
        errorData?['detail']?.toString() ??
            _describeUnexpectedResponse(response),
      );
    } catch (e) {
      throw Exception('Network error: $e');
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
