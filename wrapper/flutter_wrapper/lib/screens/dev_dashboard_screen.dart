import 'package:flutter/material.dart';

import '../services/api_client.dart';

class DevDashboardScreen extends StatefulWidget {
  final ApiClient apiClient;
  final VoidCallback onAuthExpired;

  const DevDashboardScreen({
    super.key,
    required this.apiClient,
    required this.onAuthExpired,
  });

  @override
  State<DevDashboardScreen> createState() => _DevDashboardScreenState();
}

class _DevDashboardScreenState extends State<DevDashboardScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  final TextEditingController _orgsController = TextEditingController();
  final TextEditingController _concentrationsController =
      TextEditingController();
  final TextEditingController _majorsController = TextEditingController();

  bool _busy = false;
  String _status = '';
  int _orgCount = 0;
  int _concentrationCount = 0;
  int _majorCount = 0;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _loadAllFiles();
  }

  @override
  void dispose() {
    _tabs.dispose();
    _orgsController.dispose();
    _concentrationsController.dispose();
    _majorsController.dispose();
    super.dispose();
  }

  Future<void> _withBusy(String message, Future<void> Function() fn) async {
    setState(() {
      _busy = true;
      _status = message;
    });
    try {
      await fn();
    } on ApiUnauthorizedException {
      if (mounted) {
        setState(() => _status = 'Session expired. Please log in again.');
      }
      widget.onAuthExpired();
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (e) {
      setState(() => _status = 'Error: $e');
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _loadAllFiles() async {
    await _withBusy('Loading dev files...', () async {
      final orgs = await widget.apiClient.getOrgsText();
      final concentrations = await widget.apiClient.getConcentrationsText();
      final majors = await widget.apiClient.getMajors();

      _orgsController.text = (orgs['text'] ?? '').toString();
      _concentrationsController.text =
          (concentrations['text'] ?? '').toString();
      _majorsController.text = (majors['text'] ?? '').toString();

      _orgCount = int.tryParse('${orgs['line_count'] ?? 0}') ?? 0;
      _concentrationCount =
          int.tryParse('${concentrations['line_count'] ?? 0}') ?? 0;
      _majorCount = int.tryParse('${majors['line_count'] ?? 0}') ?? 0;

      setState(() => _status = 'Loaded orgs, concentrations, and majors.');
    });
  }

  Future<void> _updateOrgsFromSource() async {
    await _withBusy('Running pullorgs...', () async {
      final response = await widget.apiClient.updateOrgs();
      final file = response['file'] as Map<String, dynamic>? ?? {};
      _orgsController.text = (file['text'] ?? '').toString();
      _orgCount = int.tryParse('${file['line_count'] ?? 0}') ?? 0;
      setState(() => _status = 'Updated ncsu_orgs.txt from source.');
    });
  }

  Future<void> _updateConcentrationsFromSource() async {
    await _withBusy('Running pullconcentration...', () async {
      final response = await widget.apiClient.updateConcentrations();
      final file = response['file'] as Map<String, dynamic>? ?? {};
      _concentrationsController.text = (file['text'] ?? '').toString();
      _concentrationCount = int.tryParse('${file['line_count'] ?? 0}') ?? 0;
      setState(() => _status = 'Updated concentrations.txt from source.');
    });
  }

  Future<void> _saveOrgs() async {
    await _withBusy('Saving ncsu_orgs.txt...', () async {
      await widget.apiClient.saveOrgsText(_orgsController.text);
      final refreshed = await widget.apiClient.getOrgsText();
      _orgCount = int.tryParse('${refreshed['line_count'] ?? 0}') ?? 0;
      setState(() => _status = 'Saved ncsu_orgs.txt');
    });
  }

  Future<void> _saveConcentrations() async {
    await _withBusy('Saving concentrations.txt...', () async {
      await widget.apiClient
          .saveConcentrationsText(_concentrationsController.text);
      final refreshed = await widget.apiClient.getConcentrationsText();
      _concentrationCount =
          int.tryParse('${refreshed['line_count'] ?? 0}') ?? 0;
      setState(() => _status = 'Saved concentrations.txt');
    });
  }

  Future<void> _saveMajors() async {
    await _withBusy('Saving majors.txt...', () async {
      await widget.apiClient.saveMajors(_majorsController.text);
      final refreshed = await widget.apiClient.getMajors();
      _majorCount = int.tryParse('${refreshed['line_count'] ?? 0}') ?? 0;
      setState(() => _status = 'Saved majors.txt');
    });
  }

  Widget _fileEditor({
    required String title,
    required String subtitle,
    required TextEditingController controller,
    required VoidCallback onSave,
    required int count,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        Text('$subtitle • $count entries',
            style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 10),
        Expanded(
          child: TextField(
            controller: controller,
            expands: true,
            maxLines: null,
            minLines: null,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              alignLabelWithHint: true,
            ),
          ),
        ),
        const SizedBox(height: 10),
        Align(
          alignment: Alignment.centerRight,
          child: ElevatedButton(
            onPressed: _busy ? null : onSave,
            child: const Text('Save'),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dev Dashboard'),
        bottom: TabBar(
          controller: _tabs,
          tabs: const [
            Tab(text: 'NCSU Orgs'),
            Tab(text: 'Concentrations'),
            Tab(text: 'Majors'),
          ],
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                ElevatedButton(
                  onPressed: _busy ? null : _updateOrgsFromSource,
                  child: const Text('Pull NCSU Orgs'),
                ),
                ElevatedButton(
                  onPressed: _busy ? null : _updateConcentrationsFromSource,
                  child: const Text('Pull Concentrations'),
                ),
                OutlinedButton(
                  onPressed: _busy ? null : _loadAllFiles,
                  child: const Text('Reload All Files'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(_status),
            const SizedBox(height: 10),
            Expanded(
              child: TabBarView(
                controller: _tabs,
                children: [
                  _fileEditor(
                    title: 'data/ncsu_orgs.txt',
                    subtitle: 'Manual editor for organizations',
                    controller: _orgsController,
                    onSave: _saveOrgs,
                    count: _orgCount,
                  ),
                  _fileEditor(
                    title: 'data/concentrations.txt',
                    subtitle: 'Manual editor for concentrations',
                    controller: _concentrationsController,
                    onSave: _saveConcentrations,
                    count: _concentrationCount,
                  ),
                  _fileEditor(
                    title: 'wrapper/backend/data/majors.txt',
                    subtitle: 'Manual editor for majors',
                    controller: _majorsController,
                    onSave: _saveMajors,
                    count: _majorCount,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
