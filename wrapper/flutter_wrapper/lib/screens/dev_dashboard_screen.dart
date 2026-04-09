import 'package:flutter/material.dart';

import '../constants/ncsu_theme.dart';
import '../services/api_client.dart';
import 'mentor_manager_screen.dart';

class _DevFileMeta {
  final String fileKey;
  final String label;
  final String path;
  final int lineCount;
  final bool hasUpdateScript;

  const _DevFileMeta({
    required this.fileKey,
    required this.label,
    required this.path,
    required this.lineCount,
    required this.hasUpdateScript,
  });

  factory _DevFileMeta.fromJson(Map<String, dynamic> json) {
    return _DevFileMeta(
      fileKey: (json['file_key'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
      path: (json['path'] ?? '').toString(),
      lineCount: int.tryParse('${json['line_count'] ?? 0}') ?? 0,
      hasUpdateScript: json['has_update_script'] == true,
    );
  }
}

enum _UnsavedAction {
  save,
  discard,
  cancel,
}

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

class _DevDashboardScreenState extends State<DevDashboardScreen> {
  final TextEditingController _editorController = TextEditingController();

  bool _busy = false;
  bool _dirty = false;
  bool _loadingMatchingState = false;
  bool _syncingText = false;
  String _status = 'Loading editable files...';
  String _matchingStateError = '';

  List<_DevFileMeta> _files = const [];
  String? _selectedFileKey;
  _DevFileMeta? _selectedFileMeta;
  String _matchingStatePath = '';
  List<Map<String, String>> _rejectedPairs = const [];
  List<Map<String, String>> _lockedPairs = const [];
  List<String> _excludedMenteeIds = const [];
  List<String> _excludedMentorIds = const [];

  @override
  void initState() {
    super.initState();
    _editorController.addListener(_onEditorChanged);
    _loadFileList();
    _loadMatchingState();
  }

  @override
  void dispose() {
    _editorController.removeListener(_onEditorChanged);
    _editorController.dispose();
    super.dispose();
  }

  void _onEditorChanged() {
    if (_syncingText) {
      return;
    }
    if (!_dirty) {
      setState(() => _dirty = true);
    }
  }

  Future<void> _withBusy(String message, Future<void> Function() fn) async {
    setState(() {
      _busy = true;
      _status = message;
    });
    try {
      await fn();
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
      setState(() => _status = 'Error: $e');
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _loadFileList({String? preferredKey}) async {
    await _withBusy('Loading editable file list...', () async {
      final response = await widget.apiClient.listDevFiles();
      final rows = (response['files'] as List? ?? const []);
      final files = rows
          .whereType<Map<String, dynamic>>()
          .map(_DevFileMeta.fromJson)
          .where((row) => row.fileKey.isNotEmpty)
          .toList();

      if (files.isEmpty) {
        setState(() {
          _files = const [];
          _selectedFileKey = null;
          _selectedFileMeta = null;
          _syncingText = true;
          _editorController.text = '';
          _syncingText = false;
          _dirty = false;
          _status = 'No editable files were returned by backend.';
        });
        return;
      }

      final targetKey = preferredKey ?? _selectedFileKey ?? files.first.fileKey;
      final selected = files.any((item) => item.fileKey == targetKey)
          ? targetKey
          : files.first.fileKey;

      setState(() {
        _files = files;
        _selectedFileKey = selected;
        _selectedFileMeta = files.firstWhere((row) => row.fileKey == selected);
      });

      await _loadSelectedFile();
    });
  }

  Future<void> _loadSelectedFile() async {
    final fileKey = _selectedFileKey;
    if (fileKey == null) {
      return;
    }
    final response = await widget.apiClient.getDevFile(fileKey);
    final text = (response['text'] ?? '').toString();
    final updatedCount = int.tryParse('${response['line_count'] ?? 0}') ?? 0;

    final updated = _files.map((item) {
      if (item.fileKey != fileKey) {
        return item;
      }
      return _DevFileMeta(
        fileKey: item.fileKey,
        label: item.label,
        path: item.path,
        lineCount: updatedCount,
        hasUpdateScript: item.hasUpdateScript,
      );
    }).toList();

    setState(() {
      _files = updated;
      _selectedFileMeta = updated.firstWhere((item) => item.fileKey == fileKey);
      _syncingText = true;
      _editorController.text = text;
      _syncingText = false;
      _dirty = false;
      _status = 'Loaded ${_selectedFileMeta!.label}.';
    });
  }

  Future<bool> _saveCurrentFile() async {
    final fileKey = _selectedFileKey;
    if (fileKey == null) {
      return false;
    }

    bool success = false;
    await _withBusy('Saving ${_selectedFileMeta?.label ?? fileKey}...',
        () async {
      final response = await widget.apiClient.saveDevFile(
        fileKey: fileKey,
        text: _editorController.text,
      );
      final updatedCount = int.tryParse('${response['line_count'] ?? 0}') ?? 0;
      final backupPath = (response['backup_path'] ?? '').toString();

      setState(() {
        _files = _files.map((item) {
          if (item.fileKey != fileKey) {
            return item;
          }
          return _DevFileMeta(
            fileKey: item.fileKey,
            label: item.label,
            path: item.path,
            lineCount: updatedCount,
            hasUpdateScript: item.hasUpdateScript,
          );
        }).toList();
        _selectedFileMeta =
            _files.firstWhere((item) => item.fileKey == fileKey);
        _dirty = false;
        _status = backupPath.isEmpty
            ? 'Saved ${_selectedFileMeta!.label}.'
            : 'Saved ${_selectedFileMeta!.label}. Backup: $backupPath';
      });
      success = true;
    });

    return success;
  }

  Future<void> _runUpdateScript() async {
    final file = _selectedFileMeta;
    if (file == null || !file.hasUpdateScript) {
      return;
    }

    await _withBusy('Running update script for ${file.label}...', () async {
      final response = await widget.apiClient.runDevFileUpdate(file.fileKey);
      final filePayload =
          (response['file'] as Map<String, dynamic>? ?? const {});
      final text = (filePayload['text'] ?? '').toString();
      final updatedCount =
          int.tryParse('${filePayload['line_count'] ?? 0}') ?? 0;
      final backupPath = (response['backup_path'] ?? '').toString();

      setState(() {
        _files = _files.map((item) {
          if (item.fileKey != file.fileKey) {
            return item;
          }
          return _DevFileMeta(
            fileKey: item.fileKey,
            label: item.label,
            path: item.path,
            lineCount: updatedCount,
            hasUpdateScript: item.hasUpdateScript,
          );
        }).toList();
        _selectedFileMeta =
            _files.firstWhere((item) => item.fileKey == file.fileKey);
        _syncingText = true;
        _editorController.text = text;
        _syncingText = false;
        _dirty = false;
        _status = backupPath.isEmpty
            ? 'Updated ${file.label} from script.'
            : 'Updated ${file.label}. Backup: $backupPath';
      });
    });
  }

  Future<void> _revertLastSaved() async {
    final file = _selectedFileMeta;
    if (file == null) {
      return;
    }

    await _withBusy('Reverting ${file.label} to previous saved version...',
        () async {
      final response = await widget.apiClient.revertDevFile(file.fileKey);
      final text = (response['text'] ?? '').toString();
      final updatedCount = int.tryParse('${response['line_count'] ?? 0}') ?? 0;
      final revertedFrom = (response['reverted_from'] ?? '').toString();

      setState(() {
        _files = _files.map((item) {
          if (item.fileKey != file.fileKey) {
            return item;
          }
          return _DevFileMeta(
            fileKey: item.fileKey,
            label: item.label,
            path: item.path,
            lineCount: updatedCount,
            hasUpdateScript: item.hasUpdateScript,
          );
        }).toList();
        _selectedFileMeta =
            _files.firstWhere((item) => item.fileKey == file.fileKey);
        _syncingText = true;
        _editorController.text = text;
        _syncingText = false;
        _dirty = false;
        _status = revertedFrom.isEmpty
            ? 'Reverted ${file.label}.'
            : 'Reverted ${file.label} from: $revertedFrom';
      });
    });
  }

  Future<_UnsavedAction> _promptUnsavedAction() async {
    final result = await showDialog<_UnsavedAction>(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return AlertDialog(
          title: const Text('Unsaved Changes'),
          content: const Text(
            'You have unsaved edits. Save before leaving this file?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(_UnsavedAction.cancel),
              child: const Text('Cancel'),
            ),
            OutlinedButton(
              onPressed: () =>
                  Navigator.of(context).pop(_UnsavedAction.discard),
              child: const Text('Discard'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(_UnsavedAction.save),
              child: const Text('Save'),
            ),
          ],
        );
      },
    );

    return result ?? _UnsavedAction.cancel;
  }

  Future<bool> _maybeHandleUnsavedChanges() async {
    if (!_dirty) {
      return true;
    }

    final action = await _promptUnsavedAction();
    if (action == _UnsavedAction.cancel) {
      return false;
    }
    if (action == _UnsavedAction.discard) {
      setState(() => _dirty = false);
      return true;
    }
    return _saveCurrentFile();
  }

  Future<void> _onFileSelectionChanged(String? nextFileKey) async {
    if (_busy || nextFileKey == null || nextFileKey == _selectedFileKey) {
      return;
    }

    final proceed = await _maybeHandleUnsavedChanges();
    if (!proceed) {
      return;
    }

    setState(() {
      _selectedFileKey = nextFileKey;
      _selectedFileMeta =
          _files.firstWhere((item) => item.fileKey == nextFileKey);
    });

    await _withBusy('Loading ${_selectedFileMeta?.label ?? nextFileKey}...',
        _loadSelectedFile);
  }

  Future<void> _loadMatchingState() async {
    setState(() {
      _loadingMatchingState = true;
      _matchingStateError = '';
    });

    try {
      final response = await widget.apiClient.getDevMatchingState();
      final rejected = (response['rejected_pairs'] as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map((row) => {
                'mentee_id': (row['mentee_id'] ?? '').toString(),
                'mentor_id': (row['mentor_id'] ?? '').toString(),
              })
          .toList();
      final locked = (response['locked_pairs'] as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map((row) => {
                'mentee_id': (row['mentee_id'] ?? '').toString(),
                'mentor_id': (row['mentor_id'] ?? '').toString(),
              })
          .toList();

      setState(() {
        _matchingStatePath = (response['path'] ?? '').toString();
        _rejectedPairs = rejected;
        _lockedPairs = locked;
        _excludedMenteeIds = (response['excluded_mentee_ids'] as List? ?? const [])
            .map((item) => item.toString())
            .where((item) => item.trim().isNotEmpty)
            .toList();
        _excludedMentorIds = (response['excluded_mentor_ids'] as List? ?? const [])
            .map((item) => item.toString())
            .where((item) => item.trim().isNotEmpty)
            .toList();
      });
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
      setState(() => _matchingStateError = '$e');
    } finally {
      if (mounted) {
        setState(() => _loadingMatchingState = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final selected = _selectedFileMeta;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dev Dashboard'),
        foregroundColor: NCSUColors.wolfpackWhite,
        actions: [
          TextButton.icon(
            onPressed: _busy
                ? null
                : () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => MentorManagerScreen(
                          apiClient: widget.apiClient,
                          onAuthExpired: widget.onAuthExpired,
                        ),
                      ),
                    );
                  },
            icon: const Icon(Icons.manage_accounts_outlined, color: Colors.white),
            label: const Text(
              'Mentor Manager',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  SizedBox(
                    width: 360,
                    child: DropdownButtonFormField<String>(
                      initialValue: _selectedFileKey,
                      decoration: const InputDecoration(
                        labelText: 'Editable File',
                        border: OutlineInputBorder(),
                      ),
                      items: _files
                          .map(
                            (item) => DropdownMenuItem<String>(
                              value: item.fileKey,
                              child: Text(item.label),
                            ),
                          )
                          .toList(),
                      onChanged: _onFileSelectionChanged,
                    ),
                  ),
                  OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () => _loadFileList(preferredKey: _selectedFileKey),
                    child: const Text('Reload File List'),
                  ),
                  OutlinedButton(
                    onPressed:
                        (_busy || selected == null) ? null : _revertLastSaved,
                    child: const Text('Revert To Last Backup'),
                  ),
                  ElevatedButton(
                    onPressed: (_busy || !_dirty || selected == null)
                        ? null
                        : _saveCurrentFile,
                    child: const Text('Save'),
                  ),
                  if (selected?.hasUpdateScript == true)
                    ElevatedButton(
                      onPressed: _busy ? null : _runUpdateScript,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: NCSUColors.bioIndigo,
                        foregroundColor: Colors.white,
                      ),
                      child: Text(
                        selected!.fileKey == 'ncsu_orgs'
                            ? 'Run pullorgs'
                            : 'Run pullconcentration',
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFD8D8D8)),
                ),
                child: Text(
                  _status,
                  style: Theme.of(context)
                      .textTheme
                      .bodyMedium
                      ?.copyWith(color: Colors.black87),
                ),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'Current Exclusion / Lock State',
                              style: TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                          OutlinedButton.icon(
                            onPressed: _loadingMatchingState
                                ? null
                                : _loadMatchingState,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Refresh'),
                          ),
                        ],
                      ),
                      if (_matchingStatePath.isNotEmpty)
                        Text(
                          'State file: $_matchingStatePath',
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: Colors.black87),
                        ),
                      const SizedBox(height: 6),
                      if (_loadingMatchingState)
                        const LinearProgressIndicator()
                      else if (_matchingStateError.isNotEmpty)
                        Text(
                          'Unable to load exclusion state: $_matchingStateError',
                          style: TextStyle(color: Colors.red.shade700),
                        )
                      else
                        Wrap(
                          spacing: 16,
                          runSpacing: 8,
                          children: [
                            Text('Rejected pairs: ${_rejectedPairs.length}'),
                            Text('Locked pairs: ${_lockedPairs.length}'),
                            Text(
                                'Excluded mentees: ${_excludedMenteeIds.length}'),
                            Text(
                                'Excluded mentors: ${_excludedMentorIds.length}'),
                          ],
                        ),
                      if (_rejectedPairs.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          'Rejected pairs: ${_rejectedPairs.take(8).map((pair) => "${pair['mentee_id']} -> ${pair['mentor_id']}").join(' | ')}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              if (selected != null)
                Text(
                  '${selected.path} • ${selected.lineCount} non-empty lines',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: Colors.black87),
                ),
              const SizedBox(height: 8),
              Expanded(
                child: TextField(
                  controller: _editorController,
                  enabled: !_busy && selected != null,
                  expands: true,
                  minLines: null,
                  maxLines: null,
                  decoration: InputDecoration(
                    labelText: selected == null
                        ? 'No file selected'
                        : '${selected.label} editor',
                    border: const OutlineInputBorder(),
                    alignLabelWithHint: true,
                    filled: true,
                    fillColor: Colors.white,
                  ),
                  style: const TextStyle(
                    color: Colors.black,
                    height: 1.3,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              if (_dirty)
                Text(
                  'Unsaved changes present. Save to keep your edits.',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: NCSUColors.reynoldsRed),
                ),
          ],
        ),
      ),
    );
  }
}
