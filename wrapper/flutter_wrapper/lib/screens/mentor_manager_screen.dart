// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:html' as html;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../constants/ncsu_theme.dart';
import '../models/mentor_models.dart';
import '../services/api_client.dart';

class _LinkedInConfig {
  final bool enabled;
  final String provider;
  final String disabledReason;
  final int minIntervalSeconds;

  const _LinkedInConfig({
    required this.enabled,
    required this.provider,
    required this.disabledReason,
    required this.minIntervalSeconds,
  });

  const _LinkedInConfig.unavailable()
      : enabled = false,
        provider = 'disabled',
        disabledReason = 'LinkedIn enrichment is not configured.',
        minIntervalSeconds = 0;

  factory _LinkedInConfig.fromJson(Map<String, dynamic> json) {
    return _LinkedInConfig(
      enabled: json['enabled'] == true,
      provider: (json['provider'] ?? 'disabled').toString(),
      disabledReason: (json['disabled_reason'] ?? '').toString(),
      minIntervalSeconds:
          int.tryParse('${json['min_interval_seconds'] ?? 0}') ?? 0,
    );
  }
}

class _BulkActionSpec {
  final String id;
  final String label;
  final IconData icon;
  final bool destructive;
  final VoidCallback? onPressed;
  final String disabledReason;

  const _BulkActionSpec({
    required this.id,
    required this.label,
    required this.icon,
    this.destructive = false,
    this.onPressed,
    this.disabledReason = '',
  });
}

class _SelectAllMentorsIntent extends Intent {
  const _SelectAllMentorsIntent();
}

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
  bool _loadingLinkedInConfig = false;
  bool _bulkLinkedInUpdating = false;
  String _status = 'Loading mentors...';
  List<MentorRecord> _mentors = const [];
  final Set<String> _selectedMentorIds = <String>{};
  final Set<String> _enrichingMentorIds = <String>{};

  _LinkedInConfig _linkedInConfig = const _LinkedInConfig.unavailable();

  @override
  void initState() {
    super.initState();
    _loadLinkedInConfig();
    _loadMentors();
  }

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  bool? get _selectAllValue {
    if (_mentors.isEmpty || _selectedMentorIds.isEmpty) {
      return false;
    }
    if (_selectedMentorIds.length == _mentors.length) {
      return true;
    }
    return null;
  }

  void _syncSelectionToVisible() {
    final visibleIds = _mentors.map((mentor) => mentor.mentorId).toSet();
    _selectedMentorIds
        .removeWhere((mentorId) => !visibleIds.contains(mentorId));
  }

  void _goBack() {
    if (Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
    }
  }

  void _openLinkedIn(String url) {
    final normalized = url.trim();
    if (normalized.isEmpty) {
      return;
    }
    html.window.open(normalized, '_blank');
  }

  Future<void> _loadLinkedInConfig() async {
    setState(() => _loadingLinkedInConfig = true);
    try {
      final response = await widget.apiClient.getLinkedInEnrichmentConfig();
      if (!mounted) {
        return;
      }
      setState(() {
        _linkedInConfig = _LinkedInConfig.fromJson(response);
      });
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _linkedInConfig = const _LinkedInConfig.unavailable();
      });
    } finally {
      if (mounted) {
        setState(() => _loadingLinkedInConfig = false);
      }
    }
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
        _syncSelectionToVisible();
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
        _selectedMentorIds.clear();
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
        return _MentorEditorDialog(
          initial: mentor,
          apiClient: widget.apiClient,
          onAuthExpired: widget.onAuthExpired,
          onMentorEnriched: _applyMentorEnrichedUpdate,
          linkedInEnrichmentEnabled: _linkedInConfig.enabled,
          linkedInDisabledReason: _linkedInConfig.disabledReason,
        );
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

  void _applyMentorEnrichedUpdate(MentorRecord updated) {
    setState(() {
      _mentors = _mentors
          .map((mentor) =>
              mentor.mentorId == updated.mentorId ? updated : mentor)
          .toList();
      _status = 'Updated ${updated.fullName} from LinkedIn.';
    });
  }

  String _linkedInUpdateDisabledReason({
    required bool hasLinkedIn,
  }) {
    if (!hasLinkedIn) {
      return 'No LinkedIn URL is saved for this mentor.';
    }
    if (!_linkedInConfig.enabled) {
      final reason = _linkedInConfig.disabledReason.trim();
      return reason.isNotEmpty
          ? reason
          : 'LinkedIn enrichment is currently not enabled.';
    }
    return '';
  }

  Future<void> _updateFromLinkedIn(MentorRecord mentor) async {
    final hasLinkedIn = mentor.linkedInUrl.trim().isNotEmpty;
    final disabledReason =
        _linkedInUpdateDisabledReason(hasLinkedIn: hasLinkedIn);
    if (disabledReason.isNotEmpty) {
      _showSnack(disabledReason, isError: true);
      return;
    }

    setState(() => _enrichingMentorIds.add(mentor.mentorId));
    try {
      final response = await widget.apiClient
          .enqueueMentorLinkedInEnrichment(mentor.mentorId);
      final status = (response['enrichment_status'] ?? '').toString();
      final message =
          (response['message'] ?? 'LinkedIn enrichment completed.').toString();
      final mentorJson = response['mentor'];
      if (mentorJson is Map<String, dynamic>) {
        _applyMentorEnrichedUpdate(MentorRecord.fromJson(mentorJson));
      }
      if (status == 'throttled') {
        setState(() {
          _status =
              'LinkedIn update for ${mentor.fullName} is already in progress.';
        });
      } else if (status == 'success' || status == 'partial') {
        _showSnack(message);
      } else {
        _showSnack(message, isError: true);
      }
      await _loadMentors();
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('LinkedIn update failed: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() => _enrichingMentorIds.remove(mentor.mentorId));
      }
    }
  }

  Future<void> _importCsv() async {
    final picked = await FilePicker.platform.pickFiles(
      withData: true,
      type: FileType.custom,
      allowedExtensions: const ['csv', 'xlsx', 'xls'],
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
        sourceCsvPath: selected.filename,
      );
      final report = MentorImportReport.fromJson(response);
      final duplicateCount = report.skippedDuplicates;
      final invalidCount = report.invalid;
      final summary =
          'Import complete: added ${report.added}, duplicates $duplicateCount, invalid $invalidCount, errors ${report.errors}.';
      setState(() => _status = summary);
      _showSnack(
        summary,
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
        ..download = 'mentor_manager_export.csv'
        ..style.display = 'none';
      html.document.body?.children.add(anchor);
      anchor.click();
      anchor.remove();
      html.Url.revokeObjectUrl(url);
      _showSnack('Exported mentor_manager_export.csv');
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('CSV export failed: $e', isError: true);
    }
  }

  Future<void> _exportXlsx() async {
    try {
      final bytes =
          await widget.apiClient.exportMentorsXlsx(includeInactive: true);
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..download = 'mentor_real_export.xlsx'
        ..style.display = 'none';
      html.document.body?.children.add(anchor);
      anchor.click();
      anchor.remove();
      html.Url.revokeObjectUrl(url);
      _showSnack('Exported mentor_real_export.xlsx');
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('XLSX export failed: $e', isError: true);
    }
  }

  Future<void> _bulkDeleteSelected() async {
    if (_selectedMentorIds.isEmpty) {
      return;
    }

    final count = _selectedMentorIds.length;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Selected Mentors'),
        content: Text(
          'Delete $count selected mentor record${count == 1 ? '' : 's'} from Mentor Manager?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: NCSUColors.reynoldsRed,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm != true) {
      return;
    }

    try {
      final response =
          await widget.apiClient.bulkDeleteMentors(_selectedMentorIds.toList());
      final deleted = int.tryParse('${response['deleted'] ?? 0}') ?? 0;
      final notFound = (response['not_found_mentor_ids'] as List? ?? const [])
          .map((item) => item.toString())
          .where((item) => item.trim().isNotEmpty)
          .toList();

      setState(() {
        _selectedMentorIds.clear();
      });

      if (notFound.isEmpty) {
        _showSnack('Deleted $deleted mentor record${deleted == 1 ? '' : 's'}.');
      } else {
        _showSnack(
          'Deleted $deleted mentor record${deleted == 1 ? '' : 's'}. ${notFound.length} records were already missing.',
        );
      }
      await _loadMentors();
    } on ApiUnauthorizedException {
      if (!mounted) {
        return;
      }
      widget.onAuthExpired();
      Navigator.of(context).pop();
    } catch (e) {
      _showSnack('Bulk delete failed: $e', isError: true);
    }
  }

  void _toggleMentorSelection(String mentorId, bool selected) {
    setState(() {
      if (selected) {
        _selectedMentorIds.add(mentorId);
      } else {
        _selectedMentorIds.remove(mentorId);
      }
    });
  }

  void _toggleSelectAll(bool select) {
    setState(() {
      if (select) {
        _selectedMentorIds
          ..clear()
          ..addAll(_mentors.map((mentor) => mentor.mentorId));
      } else {
        _selectedMentorIds.clear();
      }
    });
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

  String _initialsFor(MentorRecord mentor) {
    final parts = [mentor.firstName, mentor.lastName]
        .where((part) => part.trim().isNotEmpty)
        .toList();
    if (parts.isNotEmpty) {
      return parts
          .map((part) => part.trim().characters.first.toUpperCase())
          .join('')
          .substring(0, parts.length > 1 ? 2 : 1);
    }
    final fallback =
        mentor.fullName.trim().isNotEmpty ? mentor.fullName : mentor.email;
    return fallback.characters.first.toUpperCase();
  }

  String _locationFor(MentorRecord mentor) {
    if (mentor.currentLocation.trim().isNotEmpty) {
      return mentor.currentLocation.trim();
    }
    return [mentor.currentCity.trim(), mentor.currentState.trim()]
        .where((value) => value.isNotEmpty)
        .join(', ');
  }

  Widget _activityBadge(bool isActive) {
    final color = isActive ? Colors.green.shade700 : Colors.grey.shade600;
    final label = isActive ? 'Active' : 'Inactive';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: color,
                ),
          ),
        ],
      ),
    );
  }

  Widget _detailChip({
    required IconData icon,
    required String label,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFFF7F7F7),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFE3E3E3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: Colors.grey.shade700),
          const SizedBox(width: 5),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 270),
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }

  List<_BulkActionSpec> _bulkActions() {
    final linkedInDisabledReason =
        _loading ? 'Mentor list is loading.' : _bulkLinkedInDisabledReason();
    return [
      _BulkActionSpec(
        id: 'linkedin',
        label: 'Update Selected from LinkedIn',
        icon: Icons.auto_fix_high_outlined,
        onPressed: linkedInDisabledReason.isEmpty
            ? _bulkUpdateSelectedFromLinkedIn
            : null,
        disabledReason: linkedInDisabledReason,
      ),
      _BulkActionSpec(
        id: 'delete',
        label: 'Delete Selected',
        icon: Icons.delete_outline,
        destructive: true,
        onPressed:
            _selectedMentorIds.isEmpty || _loading || _bulkLinkedInUpdating
                ? null
                : _bulkDeleteSelected,
        disabledReason: _selectedMentorIds.isEmpty
            ? 'Select one or more mentors first.'
            : (_bulkLinkedInUpdating
                ? 'LinkedIn bulk update is currently running.'
                : ''),
      ),
    ];
  }

  String _bulkLinkedInDisabledReason() {
    if (_bulkLinkedInUpdating) {
      return 'LinkedIn bulk update is already running.';
    }
    if (_selectedMentorIds.isEmpty) {
      return 'Select one or more mentors first.';
    }
    if (!_linkedInConfig.enabled) {
      final reason = _linkedInConfig.disabledReason.trim();
      return reason.isNotEmpty
          ? reason
          : 'LinkedIn enrichment is currently not enabled.';
    }
    final selectedMentors = _mentors
        .where((mentor) => _selectedMentorIds.contains(mentor.mentorId))
        .toList();
    if (selectedMentors.isEmpty) {
      return 'Selected mentors are no longer visible. Reload and retry.';
    }
    final withLinkedIn = selectedMentors
        .where((mentor) => mentor.linkedInUrl.trim().isNotEmpty)
        .length;
    if (withLinkedIn <= 0) {
      return 'Selected mentors need LinkedIn URLs before update.';
    }
    return '';
  }

  Future<void> _bulkUpdateSelectedFromLinkedIn() async {
    final disabledReason = _bulkLinkedInDisabledReason();
    if (disabledReason.isNotEmpty) {
      _showSnack(disabledReason, isError: true);
      return;
    }

    final selectedMentors = _mentors
        .where((mentor) => _selectedMentorIds.contains(mentor.mentorId))
        .toList();
    final candidates = selectedMentors
        .where((mentor) => mentor.linkedInUrl.trim().isNotEmpty)
        .toList();
    final skippedNoLinkedIn = selectedMentors.length - candidates.length;
    if (candidates.isEmpty) {
      _showSnack(
        'Selected mentors need LinkedIn URLs before update.',
        isError: true,
      );
      return;
    }

    setState(() {
      _bulkLinkedInUpdating = true;
      _status =
          'Updating ${candidates.length} selected mentor${candidates.length == 1 ? '' : 's'} from LinkedIn...';
    });

    var successCount = 0;
    var partialCount = 0;
    var failedCount = 0;
    var throttledCount = 0;
    var disabledCount = 0;

    try {
      for (final mentor in candidates) {
        if (!mounted) {
          return;
        }

        setState(() => _enrichingMentorIds.add(mentor.mentorId));
        try {
          final response = await widget.apiClient
              .enqueueMentorLinkedInEnrichment(mentor.mentorId);
          final status = (response['enrichment_status'] ?? '').toString();
          final mentorJson = response['mentor'];

          if (mentorJson is Map<String, dynamic>) {
            final updated = MentorRecord.fromJson(mentorJson);
            setState(() {
              _mentors = _mentors
                  .map(
                      (row) => row.mentorId == updated.mentorId ? updated : row)
                  .toList();
            });
          }

          switch (status) {
            case 'success':
              successCount += 1;
              break;
            case 'partial':
              partialCount += 1;
              break;
            case 'throttled':
              throttledCount += 1;
              break;
            case 'disabled':
              disabledCount += 1;
              break;
            default:
              failedCount += 1;
              break;
          }
        } on ApiUnauthorizedException {
          if (!mounted) {
            return;
          }
          widget.onAuthExpired();
          Navigator.of(context).pop();
          return;
        } catch (_) {
          failedCount += 1;
        } finally {
          if (mounted) {
            setState(() => _enrichingMentorIds.remove(mentor.mentorId));
          }
        }
      }
    } finally {
      if (mounted) {
        setState(() => _bulkLinkedInUpdating = false);
      }
    }

    final summary = [
      'LinkedIn bulk update finished:',
      '$successCount success',
      '$partialCount partial',
      '$failedCount failed',
      if (throttledCount > 0) '$throttledCount throttled',
      if (disabledCount > 0) '$disabledCount disabled',
      if (skippedNoLinkedIn > 0) '$skippedNoLinkedIn skipped (no LinkedIn URL)',
    ].join(', ');

    if (!mounted) {
      return;
    }
    setState(() => _status = summary);
    _showSnack(
      summary,
      isError: successCount == 0 && partialCount == 0,
    );
    await _loadMentors();
  }

  Widget _buildMentorRow(MentorRecord mentor) {
    final isSelected = _selectedMentorIds.contains(mentor.mentorId);
    final hasPhoto = mentor.profilePhotoUrl.trim().isNotEmpty;
    final hasLinkedIn = mentor.linkedInUrl.trim().isNotEmpty;
    final location = _locationFor(mentor);
    final isEnriching = _enrichingMentorIds.contains(mentor.mentorId);
    final linkedInDisabledReason =
        _linkedInUpdateDisabledReason(hasLinkedIn: hasLinkedIn);
    final canUpdateLinkedIn = !_loading &&
        !_bulkLinkedInUpdating &&
        !isEnriching &&
        linkedInDisabledReason.isEmpty;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isSelected
              ? NCSUColors.wolfpackRed.withOpacity(0.5)
              : const Color(0xFFDCDCDC),
          width: isSelected ? 1.4 : 1,
        ),
      ),
      color: isSelected ? const Color(0xFFFFF5F4) : Colors.white,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Checkbox(
              value: isSelected,
              onChanged: (_loading || _bulkLinkedInUpdating)
                  ? null
                  : (value) =>
                      _toggleMentorSelection(mentor.mentorId, value ?? false),
            ),
            const SizedBox(width: 4),
            CircleAvatar(
              radius: 19,
              backgroundImage:
                  hasPhoto ? NetworkImage(mentor.profilePhotoUrl) : null,
              child: hasPhoto ? null : Text(_initialsFor(mentor)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            mentor.fullName.trim().isNotEmpty
                                ? mentor.fullName
                                : mentor.email,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: FontWeight.w700),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        _activityBadge(mentor.isActive),
                      ],
                    ),
                    Text(
                      mentor.email,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: Colors.black54),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        _detailChip(
                          icon: Icons.business_outlined,
                          label: mentor.currentCompany.trim().isNotEmpty
                              ? mentor.currentCompany.trim()
                              : 'Company not set',
                        ),
                        _detailChip(
                          icon: Icons.work_outline,
                          label: mentor.currentJobTitle.trim().isNotEmpty
                              ? mentor.currentJobTitle.trim()
                              : 'Title not set',
                        ),
                        _detailChip(
                          icon: Icons.location_on_outlined,
                          label: location.isNotEmpty
                              ? location
                              : 'Location not set',
                        ),
                        _detailChip(
                          icon: Icons.history,
                          label: mentor.lastEnrichedAt.trim().isNotEmpty
                              ? 'LinkedIn sync: ${mentor.lastEnrichedAt.trim()}'
                              : 'LinkedIn sync: never',
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(
                          onPressed: hasLinkedIn
                              ? () => _openLinkedIn(mentor.linkedInUrl)
                              : null,
                          icon: const Icon(Icons.open_in_new, size: 16),
                          label: const Text('Open LinkedIn'),
                        ),
                        Tooltip(
                          message: linkedInDisabledReason.isEmpty
                              ? (isEnriching
                                  ? 'Updating from LinkedIn...'
                                  : 'Update from LinkedIn')
                              : linkedInDisabledReason,
                          child: OutlinedButton.icon(
                            onPressed: canUpdateLinkedIn
                                ? () => _updateFromLinkedIn(mentor)
                                : null,
                            icon: isEnriching
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2),
                                  )
                                : const Icon(Icons.auto_awesome_outlined,
                                    size: 16),
                            label: Text(isEnriching
                                ? 'Updating...'
                                : 'Update from LinkedIn'),
                          ),
                        ),
                        TextButton.icon(
                          onPressed: (_loading || _bulkLinkedInUpdating)
                              ? null
                              : () => _openEditor(mentor: mentor),
                          icon: const Icon(Icons.edit_outlined, size: 16),
                          label: const Text('Edit'),
                        ),
                        TextButton.icon(
                          onPressed: (_loading || _bulkLinkedInUpdating)
                              ? null
                              : () => _deactivateMentor(mentor),
                          icon: const Icon(Icons.person_off_outlined, size: 16),
                          label: const Text('Deactivate'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bulkActions = _bulkActions();

    return Shortcuts(
      shortcuts: const <ShortcutActivator, Intent>{
        SingleActivator(LogicalKeyboardKey.keyA, meta: true):
            _SelectAllMentorsIntent(),
        SingleActivator(LogicalKeyboardKey.keyA, control: true):
            _SelectAllMentorsIntent(),
      },
      child: Actions(
        actions: <Type, Action<Intent>>{
          _SelectAllMentorsIntent: CallbackAction<_SelectAllMentorsIntent>(
            onInvoke: (_intent) {
              if (_loading || _bulkLinkedInUpdating || _mentors.isEmpty) {
                return null;
              }
              final shouldSelectAll =
                  _selectedMentorIds.length != _mentors.length;
              _toggleSelectAll(shouldSelectAll);
              return null;
            },
          ),
        },
        child: Focus(
          autofocus: true,
          child: Scaffold(
            appBar: AppBar(
              automaticallyImplyLeading: false,
              leading: IconButton(
                tooltip: 'Back',
                onPressed: _goBack,
                icon: const Icon(Icons.arrow_back),
              ),
              title: const Text('Mentor Manager (Dev)'),
            ),
            body: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1400),
                child: Padding(
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
                                width: 340,
                                child: TextField(
                                  controller: _queryController,
                                  decoration: const InputDecoration(
                                    labelText: 'Search mentors',
                                    border: OutlineInputBorder(),
                                    prefixIcon: Icon(Icons.search),
                                  ),
                                  onSubmitted: (_) => _loadMentors(),
                                ),
                              ),
                              ElevatedButton.icon(
                                onPressed: (_loading || _bulkLinkedInUpdating)
                                    ? null
                                    : _loadMentors,
                                icon: const Icon(Icons.refresh),
                                label: const Text('Reload'),
                              ),
                              ElevatedButton.icon(
                                onPressed: (_loading || _bulkLinkedInUpdating)
                                    ? null
                                    : () => _openEditor(),
                                icon: const Icon(Icons.person_add_alt_1),
                                label: const Text('Add Mentor'),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Wrap(
                            spacing: 10,
                            runSpacing: 10,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              OutlinedButton.icon(
                                onPressed: (_loading || _bulkLinkedInUpdating)
                                    ? null
                                    : _importCsv,
                                icon: const Icon(Icons.upload_file),
                                label: const Text('Import CSV/XLSX'),
                              ),
                              OutlinedButton.icon(
                                onPressed: (_loading || _bulkLinkedInUpdating)
                                    ? null
                                    : _exportCsv,
                                icon: const Icon(Icons.description_outlined),
                                label: const Text('Export CSV'),
                              ),
                              OutlinedButton.icon(
                                onPressed: (_loading || _bulkLinkedInUpdating)
                                    ? null
                                    : _exportXlsx,
                                icon: const Icon(Icons.download),
                                label: const Text('Export XLSX'),
                              ),
                              if (_loadingLinkedInConfig)
                                const Chip(
                                  avatar: SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2),
                                  ),
                                  label: Text(
                                      'Checking LinkedIn configuration...'),
                                )
                              else if (!_linkedInConfig.enabled)
                                Chip(
                                  avatar:
                                      const Icon(Icons.info_outline, size: 16),
                                  label: Text(
                                    _linkedInConfig.disabledReason
                                            .trim()
                                            .isNotEmpty
                                        ? _linkedInConfig.disabledReason.trim()
                                        : 'LinkedIn enrichment is not enabled.',
                                  ),
                                )
                              else
                                Chip(
                                  avatar: const Icon(Icons.verified_outlined,
                                      size: 16),
                                  label: Text(
                                    'LinkedIn provider: ${_linkedInConfig.provider}',
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 10),
                          child: Wrap(
                            spacing: 12,
                            runSpacing: 10,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Checkbox(
                                    tristate: true,
                                    value: _selectAllValue,
                                    onChanged: (_loading ||
                                            _bulkLinkedInUpdating ||
                                            _mentors.isEmpty)
                                        ? null
                                        : (value) =>
                                            _toggleSelectAll(value == true),
                                  ),
                                  const Text(
                                      'Select all visible (Cmd/Ctrl + A)'),
                                ],
                              ),
                              Text(
                                '${_selectedMentorIds.length} selected',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.copyWith(
                                      fontWeight: FontWeight.w600,
                                    ),
                              ),
                              for (final action in bulkActions)
                                Tooltip(
                                  message: action.onPressed == null &&
                                          action.disabledReason
                                              .trim()
                                              .isNotEmpty
                                      ? action.disabledReason.trim()
                                      : action.label,
                                  child: OutlinedButton.icon(
                                    onPressed: action.onPressed,
                                    style: action.destructive
                                        ? OutlinedButton.styleFrom(
                                            foregroundColor:
                                                NCSUColors.reynoldsRed,
                                          )
                                        : null,
                                    icon: Icon(action.icon),
                                    label: Text(action.label),
                                  ),
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
                                : ListView.builder(
                                    itemCount: _mentors.length,
                                    itemBuilder: (context, index) =>
                                        _buildMentorRow(_mentors[index]),
                                  ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _MentorEditorDialog extends StatefulWidget {
  final MentorRecord? initial;
  final ApiClient apiClient;
  final VoidCallback onAuthExpired;
  final void Function(MentorRecord updated)? onMentorEnriched;
  final bool linkedInEnrichmentEnabled;
  final String linkedInDisabledReason;

  const _MentorEditorDialog({
    required this.initial,
    required this.apiClient,
    required this.onAuthExpired,
    this.onMentorEnriched,
    required this.linkedInEnrichmentEnabled,
    required this.linkedInDisabledReason,
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
  bool _dirty = false;
  bool _enriching = false;
  String _lastEnrichedAt = '';
  late Map<String, dynamic> _initialSnapshot;

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
    _lastEnrichedAt = record?.lastEnrichedAt ?? '';

    _initialSnapshot = _snapshot();
    _controllers
        .forEach((controller) => controller.addListener(_onFieldChanged));
  }

  @override
  void dispose() {
    _controllers
        .forEach((controller) => controller.removeListener(_onFieldChanged));
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

  List<TextEditingController> get _controllers => [
        _emailController,
        _firstNameController,
        _lastNameController,
        _linkedInController,
        _photoController,
        _companyController,
        _titleController,
        _locationController,
        _cityController,
        _stateController,
        _degreesController,
        _industryController,
        _experienceController,
        _aboutController,
        _studentsController,
        _phoneController,
        _preferredContactController,
      ];

  void _onFieldChanged() {
    final isDirtyNow = !_snapshotEquals(_snapshot(), _initialSnapshot);
    if (isDirtyNow != _dirty) {
      setState(() => _dirty = isDirtyNow);
    }
  }

  Map<String, dynamic> _snapshot() {
    return {
      'email': _emailController.text.trim(),
      'first_name': _firstNameController.text.trim(),
      'last_name': _lastNameController.text.trim(),
      'linkedin_url': _linkedInController.text.trim(),
      'profile_photo_url': _photoController.text.trim(),
      'current_company': _companyController.text.trim(),
      'current_job_title': _titleController.text.trim(),
      'current_location': _locationController.text.trim(),
      'current_city': _cityController.text.trim(),
      'current_state': _stateController.text.trim(),
      'degrees_text': _degreesController.text.trim(),
      'industry_focus_area': _industryController.text.trim(),
      'professional_experience': _experienceController.text.trim(),
      'about_yourself': _aboutController.text.trim(),
      'students_interested': _studentsController.text.trim(),
      'phone': _phoneController.text.trim(),
      'preferred_contact_method': _preferredContactController.text.trim(),
      'is_active': _isActive,
    };
  }

  bool _snapshotEquals(Map<String, dynamic> a, Map<String, dynamic> b) {
    if (a.length != b.length) {
      return false;
    }
    for (final entry in a.entries) {
      if (!b.containsKey(entry.key)) {
        return false;
      }
      if (b[entry.key] != entry.value) {
        return false;
      }
    }
    return true;
  }

  Future<void> _attemptDismiss() async {
    if (!_dirty) {
      Navigator.of(context).pop();
      return;
    }

    final shouldDiscard = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Discard Unsaved Changes?'),
          content: const Text(
            'You have unsaved mentor edits. Discard changes and close?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Keep Editing'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Discard'),
            ),
          ],
        );
      },
    );

    if (shouldDiscard == true && mounted) {
      Navigator.of(context).pop();
    }
  }

  MentorRecord _recordFromFields({MentorRecord? seed}) {
    final firstName = _firstNameController.text.trim();
    final lastName = _lastNameController.text.trim();
    final email = _emailController.text.trim();
    final fullName = [firstName, lastName]
        .where((value) => value.isNotEmpty)
        .join(' ')
        .trim();

    final existing = seed ?? widget.initial;
    return MentorRecord(
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
          : 'mentor_manager',
      sourceTimestamp: existing?.sourceTimestamp ?? '',
      lastModifiedAt: existing?.lastModifiedAt ?? '',
      lastModifiedBy: existing?.lastModifiedBy ?? '',
      lastEnrichedAt: existing?.lastEnrichedAt ?? '',
      enrichmentStatus: existing?.enrichmentStatus ?? '',
      extraFields: existing?.extraFields ?? const {},
    );
  }

  void _applyRecordToControllers(MentorRecord mentor,
      {bool resetSnapshot = true}) {
    _emailController.text = mentor.email;
    _firstNameController.text = mentor.firstName;
    _lastNameController.text = mentor.lastName;
    _linkedInController.text = mentor.linkedInUrl;
    _photoController.text = mentor.profilePhotoUrl;
    _companyController.text = mentor.currentCompany;
    _titleController.text = mentor.currentJobTitle;
    _locationController.text = mentor.currentLocation;
    _cityController.text = mentor.currentCity;
    _stateController.text = mentor.currentState;
    _degreesController.text = mentor.degreesText;
    _industryController.text = mentor.industryFocusArea;
    _experienceController.text = mentor.professionalExperience;
    _aboutController.text = mentor.aboutYourself;
    _studentsController.text = '${mentor.studentsInterested}';
    _phoneController.text = mentor.phone;
    _preferredContactController.text = mentor.preferredContactMethod;
    _isActive = mentor.isActive;
    _lastEnrichedAt = mentor.lastEnrichedAt;
    if (resetSnapshot) {
      _initialSnapshot = _snapshot();
      _dirty = false;
    } else {
      _onFieldChanged();
    }
  }

  Future<void> _updateFromLinkedIn() async {
    final existing = widget.initial;
    if (existing == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Save this mentor first, then run LinkedIn update.')),
      );
      return;
    }

    if (_dirty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content:
                Text('Save or discard current edits before LinkedIn update.')),
      );
      return;
    }

    if (!widget.linkedInEnrichmentEnabled) {
      final reason = widget.linkedInDisabledReason.trim().isNotEmpty
          ? widget.linkedInDisabledReason.trim()
          : 'LinkedIn enrichment is currently not enabled.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(reason)),
      );
      return;
    }

    if (_linkedInController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('No LinkedIn URL is saved for this mentor.')),
      );
      return;
    }

    setState(() => _enriching = true);
    try {
      final response = await widget.apiClient
          .enqueueMentorLinkedInEnrichment(existing.mentorId);
      final status = (response['enrichment_status'] ?? '').toString();
      final message =
          (response['message'] ?? 'LinkedIn update completed.').toString();
      final mentorJson = response['mentor'];
      if (mentorJson is Map<String, dynamic>) {
        final updated = MentorRecord.fromJson(mentorJson);
        _applyRecordToControllers(updated, resetSnapshot: true);
        widget.onMentorEnriched?.call(updated);
      }

      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            status == 'throttled'
                ? 'LinkedIn update is already in progress for this mentor.'
                : message,
          ),
          backgroundColor: (status == 'success' ||
                  status == 'partial' ||
                  status == 'throttled')
              ? null
              : Colors.red.shade700,
        ),
      );
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('LinkedIn update failed: $e'),
          backgroundColor: Colors.red.shade700,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _enriching = false);
      }
    }
  }

  void _save() {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    Navigator.of(context).pop(_recordFromFields());
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
    final linkedInDisabledReason = !widget.linkedInEnrichmentEnabled
        ? (widget.linkedInDisabledReason.trim().isNotEmpty
            ? widget.linkedInDisabledReason.trim()
            : 'LinkedIn enrichment is currently not enabled.')
        : '';
    final canUpdateLinkedIn = widget.initial != null &&
        widget.linkedInEnrichmentEnabled &&
        !_enriching &&
        _linkedInController.text.trim().isNotEmpty &&
        !_dirty;

    return PopScope(
      canPop: !_dirty,
      onPopInvokedWithResult: (didPop, _result) {
        if (!didPop) {
          _attemptDismiss();
        }
      },
      child: AlertDialog(
        title: Row(
          children: [
            Expanded(child: Text(title)),
            if (_dirty)
              Text(
                'Unsaved changes',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.orange.shade800,
                    ),
              ),
          ],
        ),
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
                  const SizedBox(height: 8),
                  if (widget.initial != null)
                    Row(
                      children: [
                        Tooltip(
                          message: linkedInDisabledReason.isNotEmpty
                              ? linkedInDisabledReason
                              : _linkedInController.text.trim().isEmpty
                                  ? 'No LinkedIn URL is saved for this mentor.'
                                  : (_dirty
                                      ? 'Save/discard unsaved edits before update'
                                      : 'Pull latest profile details from LinkedIn provider'),
                          child: ElevatedButton.icon(
                            onPressed:
                                canUpdateLinkedIn ? _updateFromLinkedIn : null,
                            icon: _enriching
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2),
                                  )
                                : const Icon(Icons.auto_awesome_outlined),
                            label: Text(_enriching
                                ? 'Updating...'
                                : 'Update from LinkedIn'),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Last updated from LinkedIn: ${_lastEnrichedAt.isNotEmpty ? _lastEnrichedAt : '-'}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      ],
                    ),
                  if (widget.initial != null &&
                      linkedInDisabledReason.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        linkedInDisabledReason,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey.shade700,
                            ),
                      ),
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
                        onChanged: (value) {
                          setState(() => _isActive = value ?? true);
                          _onFieldChanged();
                        },
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
            onPressed: _enriching ? null : _attemptDismiss,
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: _enriching ? null : _save,
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
}
