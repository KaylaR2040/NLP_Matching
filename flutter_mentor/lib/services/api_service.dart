import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/mentor_form_data.dart';

class ApiService {
  // Change this to your deployed backend URL in production
  static const String baseUrl = 'http://localhost:8000/api';

  /// Submit a mentor application to the backend
  static Future<Map<String, dynamic>> submitMentorApplication(
      MentorFormData formData) async {
    try {
      final url = Uri.parse('$baseUrl/mentors/');
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

  /// Get all submitted mentors
  static Future<List<dynamic>> getAllMentors() async {
    try {
      final url = Uri.parse('$baseUrl/mentors/');
      final response = await http.get(url);
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return [];
    } catch (e) {
      print('Error fetching mentors: $e');
      return [];
    }
  }
}
