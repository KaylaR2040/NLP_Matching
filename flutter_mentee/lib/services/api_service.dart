import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import '../models/mentee_form_data.dart';

/// API service to connect the Flutter mentee form to the backend
///
/// Data flow:
///   Flutter form -> toJson() -> POST /api/mentees -> backend stores in mentees.json
///   NLP matcher reads from mentees.json (NOT from the old data/ CSV files)
class ApiService {
  // Web app host. API requests are expected under /api on the same domain.
  static const String baseUrl = 'https://menteeform.vercel.app/api';
  static const String _googleFormEndpoint =
      'https://docs.google.com/forms/d/e/1FAIpQLScEp0vvZtkpEtWFxPthh5xbGr0rcEt5k6Zd8CjbTeXHT-VskA/formResponse';

  /// Submit a mentee application to the backend
  /// Called when the form submit button is pressed
  static Future<Map<String, dynamic>> submitMenteeApplication(
    MenteeFormData formData,
  ) async {
    try {
      final url = Uri.parse(_googleFormEndpoint);
      final submissionId = const Uuid().v4();
      final submittedAt = DateTime.now().toIso8601String();

      final body = {
        'entry.949801267': formData.emailController.text.trim(),
        'entry.926900860': formData.firstNameController.text.trim(),
        'entry.1983684609': formData.lastNameController.text.trim(),
        'entry.1976491083': formData.pronouns ?? '',
        'entry.1337254110': formData.educationLevel ?? '',
        'entry.1583993810': formData.graduationSemester ?? '',
        'entry.1943297115': formData.graduationYear ?? '',
        'entry.2094001975': _joinList(formData.degreePrograms),
        'entry.1479506346': formData.hasConcentration ? 'Yes' : 'No',
        'entry.1579760704': _joinList(formData.concentrations),
        'entry.2117423693': formData.phdSpecializationController.text.trim(),
        'entry.705448099': _boolToYesNo(formData.previousMentorship),
        'entry.562009089': _joinList(formData.studentOrgs),
        'entry.2016076981': formData.experienceLevel ?? '',
        'entry.867933932': _joinList(formData.industriesOfInterest),
        'entry.1834469658': formData.aboutYourselfController.text.trim(),
        'entry.162617210': formData.matchByIndustry.toString(),
        'entry.549463769': formData.matchByDegree.toString(),
        'entry.1801459898': formData.matchByClubs.toString(),
        'entry.76037252': formData.matchByIdentity.toString(),
        'entry.1948682182': formData.matchByGradYears.toString(),
        'entry.1538022217': _joinList(formData.helpTopics),
        'entry.1192108296': submissionId,
        'entry.1799865324': submittedAt,
      };

      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: body,
      );

      if (response.statusCode >= 200 && response.statusCode < 400) {
        return {'success': true};
      }

      return {
        'success': false,
        'error': _describeUnexpectedResponse(response),
      };
    } catch (e) {
      return {'success': false, 'error': 'Could not connect to server: $e'};
    }
  }

  static String _joinList(List<String> values) => values.join(', ');

  static String _boolToYesNo(bool? value) {
    if (value == null) return '';
    return value ? 'Yes' : 'No';
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
