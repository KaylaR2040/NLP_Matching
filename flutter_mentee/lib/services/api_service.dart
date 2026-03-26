import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/mentee_form_data.dart';

/// API service to connect the Flutter mentee form to the backend
///
/// Data flow:
///   Flutter form -> toJson() -> POST /api/mentees/ -> backend stores in mentees.json
///   NLP matcher reads from mentees.json (NOT from the old data/ CSV files)
class ApiService {
  // Change this to your deployed URL in production
  static const String baseUrl = 'https://menteeform.vercel.app';

  /// Submit a mentee application to the backend
  /// Called when the form submit button is pressed
  static Future<Map<String, dynamic>> submitMenteeApplication(
      MenteeFormData formData) async {
    try {
      final url = Uri.parse('$baseUrl/mentees/');
      final jsonData = formData.toJson();
      
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(jsonData),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = json.decode(response.body);
        return {'success': true, 'data': responseData};
      } else {
        final errorData = json.decode(response.body);
        return {
          'success': false,
          'error': errorData['detail'] ?? 'Failed to submit application',
        };
      }
    } catch (e) {
      return {'success': false, 'error': 'Could not connect to server: $e'};
    }
  }

  /// Get all submitted mentees
  static Future<List<dynamic>> getAllMentees() async {
    try {
      final url = Uri.parse('$baseUrl/mentees/');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
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
        return json.decode(response.body) as Map<String, dynamic>;
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
        return json.decode(response.body) as Map<String, dynamic>;
      }
      final errorData = json.decode(response.body);
      throw Exception(errorData['detail'] ?? 'Failed to run matching');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Get matches for a specific mentee
  static Future<Map<String, dynamic>> getMenteeMatches(String menteeId,
      {int topK = 5}) async {
    try {
      final url =
          Uri.parse('$baseUrl/matching/mentee/$menteeId?top_k=$topK');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      final errorData = json.decode(response.body);
      throw Exception(errorData['detail'] ?? 'Failed to get matches');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
}