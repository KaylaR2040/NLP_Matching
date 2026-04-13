import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'constants/api_runtime_config.dart';
import 'constants/ncsu_theme.dart';
import 'screens/login_screen.dart';
import 'screens/matching_dashboard_screen.dart';
import 'services/api_client.dart';

void main() {
  runApp(const WrapperApp());
}

class WrapperApp extends StatefulWidget {
  const WrapperApp({super.key});

  @override
  State<WrapperApp> createState() => _WrapperAppState();
}

class _WrapperAppState extends State<WrapperApp> {
  static const _tokenStorageKey = 'wrapper_auth_token';
  static const _isDevStorageKey = 'wrapper_auth_is_dev';

  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  bool _bootstrapping = true;
  bool? _isDev;
  late final ApiClient _apiClient =
      ApiClient(baseUrl: ApiRuntimeConfig.resolveBaseUrl());

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    final token = await _secureStorage.read(key: _tokenStorageKey);
    if (token == null || token.isEmpty) {
      debugPrint('auth_state transition=no_stored_session');
      if (mounted) {
        setState(() => _bootstrapping = false);
      }
      return;
    }

    debugPrint('auth_state transition=restore_session token_present=true');
    _apiClient.setAuthToken(token);

    try {
      var me = await _apiClient.getMe();
      final expiresAt = int.tryParse('${me['expires_at'] ?? 0}') ?? 0;
      final nowSeconds = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      if (expiresAt - nowSeconds <= 300) {
        final refresh = await _apiClient.refreshToken();
        final refreshedToken = (refresh['token'] ?? '').toString();
        if (refreshedToken.isNotEmpty) {
          await _secureStorage.write(
              key: _tokenStorageKey, value: refreshedToken);
        }
        me = await _apiClient.getMe();
      }

      final isDev = me['is_dev'] == true;
      await _secureStorage.write(
        key: _isDevStorageKey,
        value: isDev ? '1' : '0',
      );
      if (mounted) {
        setState(() {
          _isDev = isDev;
          _bootstrapping = false;
        });
      }
      debugPrint('auth_state transition=restore_session_success is_dev=$isDev');
    } on ApiSessionExpiredException {
      debugPrint('auth_state transition=session_expired_redirect_login');
      _apiClient.clearAuthToken();
      await _secureStorage.delete(key: _tokenStorageKey);
      await _secureStorage.delete(key: _isDevStorageKey);
      if (mounted) {
        setState(() {
          _isDev = null;
          _bootstrapping = false;
        });
      }
    } catch (e) {
      final storedRole = await _secureStorage.read(key: _isDevStorageKey);
      final cachedIsDev = storedRole == '1'
          ? true
          : storedRole == '0'
              ? false
              : false;
      debugPrint('session_restore_non_auth_failure error=$e');
      if (mounted) {
        setState(() {
          _isDev = cachedIsDev;
          _bootstrapping = false;
        });
      }
    }
  }

  Future<void> _handleLogin(bool isDev) async {
    final token = _apiClient.authToken;
    if (token != null && token.isNotEmpty) {
      await _secureStorage.write(key: _tokenStorageKey, value: token);
      await _secureStorage.write(
          key: _isDevStorageKey, value: isDev ? '1' : '0');
    }
    if (mounted) {
      setState(() => _isDev = isDev);
    }
    debugPrint('auth_state transition=login_success is_dev=$isDev');
  }

  Future<void> _handleLogout() async {
    debugPrint('auth_state transition=logout_requested');
    try {
      await _apiClient.logout();
    } catch (_) {
      // Ignore API logout failures and still clear local session.
    }
    _apiClient.clearAuthToken();
    await _secureStorage.delete(key: _tokenStorageKey);
    await _secureStorage.delete(key: _isDevStorageKey);
    if (mounted) {
      setState(() => _isDev = null);
    }
    debugPrint('auth_state transition=logout_complete');
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NLP Mentor Matcher Wrapper',
      debugShowCheckedModeBanner: false,
      theme: NCSUTheme.light,
      home: _bootstrapping
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : _isDev == null
              ? LoginScreen(
                  apiClient: _apiClient,
                  onLogin: (isDev) {
                    _handleLogin(isDev);
                  },
                )
              : MatchingDashboardScreen(
                  isDev: _isDev!,
                  apiClient: _apiClient,
                  onLogout: () {
                    _handleLogout();
                  },
                ),
    );
  }
}
