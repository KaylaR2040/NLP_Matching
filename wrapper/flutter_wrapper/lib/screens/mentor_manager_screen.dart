// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:html' as html;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../models/mentor_models.dart';
import '../services/api_client.dart';

class MentorManagerScreen extends StatefulWidget {
  final ApiClient apiClient;
  final VoidCallback onAuthExpired;

  const MentorManagerScreen({
    super.key,
    required this.apiClient,
    required this.onAuthExpired,
  });

  @override
  State<MentorManagerScreen> createState() => _MentorManagerScreenState();
}

class _MentorManagerScreenState extends State<MentorManagerScreen> {
  final TextEditingController _queryController = TextEditingController();

  bool _loading = false;
  String _status = 'Loading mentors...';
  List<MentorRecord> _mentors = const [];

  @override
  void initState() {
    super.initState();
    _loadMentors();
  }

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _loadMentors() async {
    setState(() {
      _loading = true;
      _status = 'Loading mentors...';
    });

    try {
      final response = await widget.apiClient.listMentors(
        query: _queryController.text,
        activeOnly: null,
        limit: 1000,
      );
      final parsed = MentorsListResult.fromJson(response);
      setState(() {
        _mentors = parsed.items;
        _status = 'Loaded ${parsed.total} mentors.';
      });
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      setState(() => _status = 'Session expired. Please log in again.');
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _status = 'Failed to load mentors: $e';
        _mentors = const [];
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _openEditor({MentorRecord? mentor}) async {
    final result = await showDialog<MentorRecord>(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return _MentorEditorDialog(initial: mentor);
      },
    );
    if (result == null) {
      return;
    }

    setState(() {
      _loading = true;
      _status = mentor == null ? 'Creating mentor...' : 'Updating mentor...';
    });

    try {
      if (mentor == null) {
        await widget.apiClient.createMentor(result.toUpdatePayload());
        _showSnack('Mentor created.');
      } else {
        await widget.apiClient.updateMentor(
          mentorId: mentor.mentorId,
          payload: result.toUpdatePayload(),
        );
        _showSnack('Mentor updated.');
      }
      await _loadMentors();
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _status = 'Save failed: $e';
      });
      _showSnack('Save failed: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _deactivateMentor(MentorRecord mentor) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Deactivate Mentor'),
          content: Text('Deactivate ${mentor.fullName}?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Deactivate'),
            ),
          ],
        );
      },
    );

    if (confirm != true) {
      return;
    }

    try {
      await widget.apiClient.deactivateMentor(mentor.mentorId);
      _showSnack('Mentor deactivated.');
      await _loadMentors();
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('Deactivate failed: $e', isError: true);
    }
  }

  Future<void> _enqueueEnrichment(MentorRecord mentor) async {
    try {
      final response = await widget.apiClient
          .enqueueMentorLinkedInEnrichment(mentor.mentorId);
      _showSnack(response['message']?.toString() ?? 'Enrichment queued.');
      await _loadMentors();
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('Enrichment queue failed: $e', isError: true);
    }
  }

  Future<void> _importCsv() async {
    final picked = await FilePicker.platform.pickFiles(
      withData: true,
      type: FileType.custom,
      allowedExtensions: const ['csv'],
    );
    if (picked == null ||
        picked.files.isEmpty ||
        picked.files.first.bytes == null) {
      return;
    }

    final selected = SelectedFile(
      filename: picked.files.first.name,
      bytes: picked.files.first.bytes!,
    );

    try {
      final response = await widget.apiClient.importMentorsCsv(
        file: selected,
        sourceCsvPath: 'nlp_project/data/mentor_real.csv',
      );
      final report = MentorImportReport.fromJson(response);
      _showSnack(
        'Import complete: created ${report.created}, updated ${report.updated}, unchanged ${report.unchanged}, skipped ${report.skipped}, errors ${report.errors}.',
      );
      await _loadMentors();
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('Import failed: $e', isError: true);
    }
  }

  Future<void> _exportCsv() async {
    try {
      final bytes =
          await widget.apiClient.exportMentorsCsv(includeInactive: true);
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..download = 'mentor_real_export.csv'
        ..style.display = 'none';
      html.document.body?.children.add(anchor);
      anchor.click();
      anchor.remove();
      html.Url.revokeObjectUrl(url);
      _showSnack('Exported mentor_real_export.csv');
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('Export failed: $e', isError: true);
    }
  }

  Future<void> _syncToCanonicalCsv() async {
    try {
      final response = await widget.apiClient.syncMentorsToDefaultCsv();
      _showSnack(
        'Synced ${response['rows']} mentors to ${response['output_path']}.',
      );
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('Sync failed: $e', isError: true);
    }
  }

  void _showSnack(String message, {bool isError = false}) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red.shade700 : null,
      ),
    );
  }

  String _missingSummary(MentorRecord mentor) {
    final missing = <String>[];
    if (mentor.currentCompany.trim().isEmpty) {
      missing.add('company');
    }
    if (mentor.currentJobTitle.trim().isEmpty) {
      missing.add('title');
    }
    final location = mentor.currentLocation.trim().isNotEmpty ||
        mentor.currentCity.trim().isNotEmpty ||
        mentor.currentState.trim().isNotEmpty;
    if (!location) {
      missing.add('location');
    }
    if (mentor.linkedInUrl.trim().isEmpty) {
      missing.add('LinkedIn');
    }
    return missing.join(', ');
  }

  List<DataRow> _buildRows() {
    return _mentors.map((mentor) {
      final missing = _missingSummary(mentor);
      final location = mentor.currentLocation.trim().isNotEmpty
          ? mentor.currentLocation.trim()
          : [mentor.currentCity.trim(), mentor.currentState.trim()]
              .where((value) => value.isNotEmpty)
              .join(', ');

      return DataRow(
        cells: [
          DataCell(Text(mentor.fullName.trim().isNotEmpty
              ? mentor.fullName
              : mentor.email)),
          DataCell(Text(
              mentor.currentCompany.isEmpty ? '-' : mentor.currentCompany)),
          DataCell(Text(
              mentor.currentJobTitle.isEmpty ? '-' : mentor.currentJobTitle)),
          DataCell(Text(location.isEmpty ? '-' : location)),
          DataCell(Text(mentor.linkedInUrl.isEmpty ? '-' : 'Available')),
          DataCell(Text(mentor.isActive ? 'Active' : 'Inactive')),
          DataCell(Text(
              mentor.lastModifiedAt.isEmpty ? '-' : mentor.lastModifiedAt)),
          DataCell(
            Row(
              children: [
                IconButton(
                  tooltip: 'Edit Mentor',
                  onPressed:
                      _loading ? null : () => _openEditor(mentor: mentor),
                  icon: const Icon(Icons.edit_outlined),
                ),
                IconButton(
                  tooltip: 'Deactivate Mentor',
                  onPressed: _loading ? null : () => _deactivateMentor(mentor),
                  icon: const Icon(Icons.person_off_outlined),
                ),
                IconButton(
                  tooltip: 'Queue LinkedIn Enrichment',
                  onPressed: _loading ? null : () => _enqueueEnrichment(mentor),
                  icon: const Icon(Icons.auto_awesome_outlined),
                ),
              ],
            ),
          ),
          DataCell(
            Text(
              missing.isEmpty ? 'Complete' : 'Missing: $missing',
              style: TextStyle(
                color: missing.isEmpty
                    ? Colors.green.shade700
                    : Colors.orange.shade800,
              ),
            ),
          ),
        ],
      );
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mentor Manager (Dev)'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    SizedBox(
                      width: 320,
                      child: TextField(
                        controller: _queryController,
                        decoration: const InputDecoration(
                          labelText: 'Search mentors',
                          border: OutlineInputBorder(),
                        ),
                        onSubmitted: (_) => _loadMentors(),
                      ),
                    ),
                    ElevatedButton.icon(
                      onPressed: _loading ? null : _loadMentors,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Reload'),
                    ),
                    ElevatedButton.icon(
                      onPressed: _loading ? null : () => _openEditor(),
                      icon: const Icon(Icons.person_add_alt_1),
                      label: const Text('Add Mentor'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _loading ? null : _importCsv,
                      icon: const Icon(Icons.upload_file),
                      label: const Text('Import CSV'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _loading ? null : _exportCsv,
                      icon: const Icon(Icons.download),
                      label: const Text('Export CSV'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _loading ? null : _syncToCanonicalCsv,
                      icon: const Icon(Icons.sync),
                      label: const Text('Sync To mentor_real.csv'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(_status),
            const SizedBox(height: 8),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _mentors.isEmpty
                      ? const Center(
                          child: Text('No mentor records found.'),
                        )
                      : SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: ConstrainedBox(
                            constraints: BoxConstraints(
                              minWidth: MediaQuery.of(context).size.width - 40,
                            ),
                            child: SingleChildScrollView(
                              child: DataTable(
                                columns: const [
                                  DataColumn(label: Text('Name')),
                                  DataColumn(label: Text('Company')),
                                  DataColumn(label: Text('Title')),
                                  DataColumn(label: Text('Location')),
                                  DataColumn(label: Text('LinkedIn')),
                                  DataColumn(label: Text('Status')),
                                  DataColumn(label: Text('Last Updated')),
                                  DataColumn(label: Text('Actions')),
                                  DataColumn(label: Text('Completeness')),
                                ],
                                rows: _buildRows(),
                              ),
                            ),
                          ),
                        ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MentorEditorDialog extends StatefulWidget {
  final MentorRecord? initial;

  const _MentorEditorDialog({
    required this.initial,
  });

  @override
  State<_MentorEditorDialog> createState() => _MentorEditorDialogState();
}

class _MentorEditorDialogState extends State<_MentorEditorDialog> {
  final _formKey = GlobalKey<FormState>();

  late final TextEditingController _emailController;
  late final TextEditingController _firstNameController;
  late final TextEditingController _lastNameController;
  late final TextEditingController _linkedInController;
  late final TextEditingController _photoController;
  late final TextEditingController _companyController;
  late final TextEditingController _titleController;
  late final TextEditingController _locationController;
  late final TextEditingController _cityController;
  late final TextEditingController _stateController;
  late final TextEditingController _degreesController;
  late final TextEditingController _industryController;
  late final TextEditingController _experienceController;
  late final TextEditingController _aboutController;
  late final TextEditingController _studentsController;
  late final TextEditingController _phoneController;
  late final TextEditingController _preferredContactController;

  bool _isActive = true;

  @override
  void initState() {
    super.initState();
    final record = widget.initial;
    _emailController = TextEditingController(text: record?.email ?? '');
    _firstNameController = TextEditingController(text: record?.firstName ?? '');
    _lastNameController = TextEditingController(text: record?.lastName ?? '');
    _linkedInController =
        TextEditingController(text: record?.linkedInUrl ?? '');
    _photoController =
        TextEditingController(text: record?.profilePhotoUrl ?? '');
    _companyController =
        TextEditingController(text: record?.currentCompany ?? '');
    _titleController =
        TextEditingController(text: record?.currentJobTitle ?? '');
    _locationController =
        TextEditingController(text: record?.currentLocation ?? '');
    _cityController = TextEditingController(text: record?.currentCity ?? '');
    _stateController = TextEditingController(text: record?.currentState ?? '');
    _degreesController = TextEditingController(text: record?.degreesText ?? '');
    _industryController =
        TextEditingController(text: record?.industryFocusArea ?? '');
    _experienceController =
        TextEditingController(text: record?.professionalExperience ?? '');
    _aboutController = TextEditingController(text: record?.aboutYourself ?? '');
    _studentsController =
        TextEditingController(text: '${record?.studentsInterested ?? 0}');
    _phoneController = TextEditingController(text: record?.phone ?? '');
    _preferredContactController =
        TextEditingController(text: record?.preferredContactMethod ?? '');
    _isActive = record?.isActive ?? true;
  }

  @override
  void dispose() {
    _emailController.dispose();
    _firstNameController.dispose();
    _lastNameController.dispose();
    _linkedInController.dispose();
    _photoController.dispose();
    _companyController.dispose();
    _titleController.dispose();
    _locationController.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _degreesController.dispose();
    _industryController.dispose();
    _experienceController.dispose();
    _aboutController.dispose();
    _studentsController.dispose();
    _phoneController.dispose();
    _preferredContactController.dispose();
    super.dispose();
  }

  void _save() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final firstName = _firstNameController.text.trim();
    final lastName = _lastNameController.text.trim();
    final email = _emailController.text.trim();
    final fullName = [firstName, lastName]
        .where((value) => value.isNotEmpty)
        .join(' ')
        .trim();

    final existing = widget.initial;
    final mentor = MentorRecord(
      mentorId: existing?.mentorId ?? email,
      email: email,
      firstName: firstName,
      lastName: lastName,
      fullName: fullName.isNotEmpty ? fullName : (existing?.fullName ?? email),
      linkedInUrl: _linkedInController.text.trim(),
      profilePhotoUrl: _photoController.text.trim(),
      currentCompany: _companyController.text.trim(),
      currentJobTitle: _titleController.text.trim(),
      currentLocation: _locationController.text.trim(),
      currentCity: _cityController.text.trim(),
      currentState: _stateController.text.trim(),
      degreesText: _degreesController.text.trim(),
      industryFocusArea: _industryController.text.trim(),
      professionalExperience: _experienceController.text.trim(),
      aboutYourself: _aboutController.text.trim(),
      studentsInterested: int.tryParse(_studentsController.text.trim()) ?? 0,
      phone: _phoneController.text.trim(),
      preferredContactMethod: _preferredContactController.text.trim(),
      isActive: _isActive,
      sourceCsvPath: existing?.sourceCsvPath.isNotEmpty == true
          ? existing!.sourceCsvPath
          : 'nlp_project/data/mentor_real.csv',
      sourceTimestamp: existing?.sourceTimestamp ?? '',
      lastModifiedAt: existing?.lastModifiedAt ?? '',
      lastModifiedBy: existing?.lastModifiedBy ?? '',
      lastEnrichedAt: existing?.lastEnrichedAt ?? '',
      enrichmentStatus: existing?.enrichmentStatus ?? '',
      extraFields: existing?.extraFields ?? const {},
    );

    Navigator.of(context).pop(mentor);
  }

  Widget _textField({
    required TextEditingController controller,
    required String label,
    int maxLines = 1,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      maxLines: maxLines,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.initial == null ? 'Add Mentor' : 'Edit Mentor';

    return AlertDialog(
      title: Text(title),
      content: SizedBox(
        width: 820,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _emailController,
                        label: 'Email',
                        validator: (value) {
                          if ((value ?? '').trim().isEmpty) {
                            return 'Email is required';
                          }
                          return null;
                        },
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _firstNameController,
                        label: 'First Name',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _lastNameController,
                        label: 'Last Name',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    SizedBox(
                      width: 370,
                      child: _textField(
                        controller: _linkedInController,
                        label: 'LinkedIn URL',
                      ),
                    ),
                    SizedBox(
                      width: 370,
                      child: _textField(
                        controller: _photoController,
                        label: 'Profile Photo URL',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _companyController,
                        label: 'Current Company',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _titleController,
                        label: 'Current Job Title',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _locationController,
                        label: 'Current Location',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _cityController,
                        label: 'Current City',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _stateController,
                        label: 'Current State',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _degreesController,
                        label: 'Degrees',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _industryController,
                        label: 'Industry Focus Area',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _studentsController,
                        label: 'Students Interested',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _phoneController,
                        label: 'Phone',
                      ),
                    ),
                    SizedBox(
                      width: 240,
                      child: _textField(
                        controller: _preferredContactController,
                        label: 'Preferred Contact Method',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                _textField(
                  controller: _experienceController,
                  label: 'Professional Experience',
                  maxLines: 3,
                ),
                const SizedBox(height: 10),
                _textField(
                  controller: _aboutController,
                  label: 'About Yourself',
                  maxLines: 3,
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Checkbox(
                      value: _isActive,
                      onChanged: (value) =>
                          setState(() => _isActive = value ?? true),
                    ),
                    const Text('Active mentor'),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _save,
          child: const Text('Save'),
        ),
      ],
    );
  }
}
