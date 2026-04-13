import 'package:flutter/foundation.dart';

class ApiRuntimeConfig {
  static const String _configuredBaseUrl =
      String.fromEnvironment('WRAPPER_API_BASE_URL', defaultValue: '');
  static const String _defaultHostedBaseUrl = String.fromEnvironment(
    'WRAPPER_DEFAULT_API_BASE_URL',
    defaultValue: 'https://nlpmatchbackend.vercel.app',
  );

  static String resolveBaseUrl() {
    final configured = _normalizeBaseUrl(_configuredBaseUrl);
    if (configured != null) {
      debugPrint('api_base_url source=dart_define value=$configured');
      return configured;
    }

    final host = Uri.base.host.toLowerCase();
    final isLocalHost = host == 'localhost' || host == '127.0.0.1';
    if (isLocalHost) {
      const localUrl = 'http://localhost:8000';
      debugPrint('api_base_url source=local_default value=$localUrl');
      return localUrl;
    }

    final hostedDefault = _normalizeBaseUrl(_defaultHostedBaseUrl);
    if (hostedDefault != null) {
      debugPrint('api_base_url source=hosted_default value=$hostedDefault');
      return hostedDefault;
    }

    final origin = Uri.base.origin;
    debugPrint('api_base_url source=origin_fallback value=$origin');
    return origin;
  }

  static String? _normalizeBaseUrl(String raw) {
    final candidate = raw.trim();
    if (candidate.isEmpty) {
      return null;
    }
    if (candidate.contains('|')) {
      debugPrint(
        "api_base_url_invalid reason=contains_pipe raw='$candidate'",
      );
      return null;
    }
    final parsed = Uri.tryParse(candidate);
    if (parsed == null || parsed.host.trim().isEmpty) {
      debugPrint(
        "api_base_url_invalid reason=parse_or_host raw='$candidate'",
      );
      return null;
    }
    final scheme = parsed.scheme.toLowerCase();
    if (scheme != 'http' && scheme != 'https') {
      debugPrint(
        "api_base_url_invalid reason=scheme raw='$candidate'",
      );
      return null;
    }
    final port = parsed.hasPort ? ':${parsed.port}' : '';
    return '${parsed.scheme}://${parsed.host}$port';
  }
}
