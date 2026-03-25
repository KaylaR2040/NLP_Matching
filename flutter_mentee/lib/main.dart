import 'package:flutter/material.dart';
import 'package:flutter_userforms/screens/mentee_interest_form_screen.dart';
import 'constants/ncsu_themes.dart';
import 'services/form_data_loader.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mentee Portal',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.light,
      theme: NCSUTheme.light,
      darkTheme: NCSUTheme.dark,
      home: const DataLoadingScreen(),
    );
  }
}

/// Loading screen that loads form data from text files
class DataLoadingScreen extends StatefulWidget {
  const DataLoadingScreen({super.key});

  @override
  State<DataLoadingScreen> createState() => _DataLoadingScreenState();
}

class _DataLoadingScreenState extends State<DataLoadingScreen> {
  String _status = 'Loading form data...';
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      setState(() => _status = 'Loading organizations...');
      final loader = FormDataLoader();
      await loader.loadAll();
      
      setState(() => _status = 'Data loaded successfully!');
      
      // Small delay to show success message
      await Future.delayed(const Duration(milliseconds: 500));
      
      // Navigate to home screen
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const MenteeInterestFormScreen()),
        );
      }
    } catch (e) {
      setState(() {
        _status = 'Error loading data: $e';
        _hasError = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (!_hasError)
              const CircularProgressIndicator()
            else
              Icon(
                Icons.error_outline,
                size: 64,
                color: Theme.of(context).colorScheme.error,
              ),
            const SizedBox(height: 24),
            Text(
              _status,
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            if (_hasError) ...[
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  setState(() {
                    _hasError = false;
                    _status = 'Retrying...';
                  });
                  _loadData();
                },
                child: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
