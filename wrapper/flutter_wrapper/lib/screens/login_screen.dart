import 'package:flutter/material.dart';

import '../services/api_client.dart';

class LoginScreen extends StatefulWidget {
  final ApiClient apiClient;
  final ValueChanged<bool> onLogin;

  const LoginScreen({
    super.key,
    required this.apiClient,
    required this.onLogin,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  String _error = '';
  bool _submitting = false;
  bool _obscurePassword = true;

  Future<void> _submit() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text;
    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = 'Username and password are required.');
      return;
    }

    setState(() {
      _submitting = true;
      _error = '';
    });

    try {
      final response = await widget.apiClient.login(
        username: username,
        password: password,
      );
      final isDev = response['is_dev'] == true;
      widget.onLogin(isDev);
    } on ApiClientException catch (e) {
      setState(() {
        _error = e.message;
      });
    } catch (_) {
      setState(() {
        _error = 'Login failed. Try again.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Card(
            margin: const EdgeInsets.all(24),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Mentor Matcher Login',
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _usernameController,
                    decoration: const InputDecoration(labelText: 'Username'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    decoration: InputDecoration(
                      labelText: 'Password',
                      suffixIcon: TextButton(
                        onPressed: () {
                          setState(() => _obscurePassword = !_obscurePassword);
                        },
                        child: Text(_obscurePassword ? 'Show' : 'Hide'),
                      ),
                    ),
                    onSubmitted: (_) {
                      if (!_submitting) {
                        _submit();
                      }
                    },
                  ),
                  const SizedBox(height: 16),
                  if (_error.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(_error,
                          style: TextStyle(
                              color: Theme.of(context).colorScheme.error)),
                    ),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _submitting ? null : _submit,
                      child: Text(_submitting ? 'Signing in...' : 'Login'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
