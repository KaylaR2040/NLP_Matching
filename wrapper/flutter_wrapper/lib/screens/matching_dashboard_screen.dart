// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:html' as html;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../constants/ncsu_theme.dart';
import '../models/match_models.dart';
import '../services/api_client.dart';
import 'dev_dashboard_screen.dart';

class MatchingDashboardScreen extends StatefulWidget {
  final bool isDev;
  final ApiClient apiClient;
  final VoidCallback onLogout;

  const MatchingDashboardScreen({
    super.key,
    required this.isDev,
    required this.apiClient,
    required this.onLogout,
  });

  @override
  State<MatchingDashboardScreen> createState() =>
      _MatchingDashboardScreenState();
}

class _MatchingDashboardScreenState extends State<MatchingDashboardScreen> {
  SelectedFile? _mentorFile;
  SelectedFile? _menteeFile;

  bool _loading = false;
  String _status = 'Upload mentor + mentee files to begin.';

  final Map<String, MentorCardState> _mentorsById = {};
  final Map<String, MenteeRecord> _menteesById = {};
  final Set<String> _unmatchedMenteeIds = {};
  final Set<PairKey> _lockedPairs = {};
  final Set<PairKey> _rejectedPairs = {};
  final Set<PairKey> _exclusionPairs = {};
  final Map<PairKey, double> _pairMatchPercent = {};

  String? _selectedExclusionMenteeId;
  String? _selectedExclusionMentorId;

  List<MentorCardState> get _mentorCards {
    final list = _mentorsById.values.toList();
    list.sort((a, b) =>
        a.mentorName.toLowerCase().compareTo(b.mentorName.toLowerCase()));
    return list;
  }

  List<MenteeRecord> get _menteeRecords {
    final list = _menteesById.values.toList();
    list.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return list;
  }

  Future<void> _pickFile({required bool mentor}) async {
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
    setState(() {
      if (mentor) {
        _mentorFile = selected;
      } else {
        _menteeFile = selected;
      }
      _status = 'Selected ${selected.filename}';
    });
  }

  Future<void> _runMatch({required bool rerun}) async {
    if (_mentorFile == null || _menteeFile == null) {
      setState(() => _status = 'Both mentor and mentee files are required.');
      return;
    }

    setState(() {
      _loading = true;
      _status = rerun ? 'Rerunning matching...' : 'Running matching...';
    });

    try {
      final blockedPairs = {..._rejectedPairs, ..._exclusionPairs};
      final payload = {
        'locked_pairs': _lockedPairs.map((pair) => pair.toJson()).toList(),
        'rejected_pairs': blockedPairs.map((pair) => pair.toJson()).toList(),
        'excluded_mentee_ids': <String>[],
        'excluded_mentor_ids': <String>[],
        'top_n': 5000,
      };

      final response = await widget.apiClient.runMatch(
        menteeFile: _menteeFile!,
        mentorFile: _mentorFile!,
        payload: payload,
      );
      final result = (response['result'] as Map<String, dynamic>? ?? {});
      _applyBackendResult(result);
      setState(() => _status = rerun ? 'Rerun complete.' : 'Run complete.');
    } on ApiUnauthorizedException {
      setState(() => _status = 'Session expired. Please log in again.');
      widget.onLogout();
    } catch (e) {
      setState(() => _status = 'Run failed: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  void _applyBackendResult(Map<String, dynamic> result) {
    final assignments = (result['assignments'] as List? ?? const []);
    final rankedPairs = (result['top_ranked_pairs'] as List? ?? const []);

    _mentorsById.clear();
    _menteesById.clear();
    _unmatchedMenteeIds.clear();
    _pairMatchPercent.clear();

    void ensureMentor(dynamic row) {
      final mentorId = (row['mentor_id'] ?? '').toString();
      final mentorName = (row['mentor_name'] ?? mentorId).toString();
      if (mentorId.isEmpty) {
        return;
      }
      _mentorsById.putIfAbsent(
        mentorId,
        () => MentorCardState(mentorId: mentorId, mentorName: mentorName),
      );
    }

    void ensureMentee(dynamic row) {
      final menteeId = (row['mentee_id'] ?? '').toString();
      final menteeName = (row['mentee_name'] ?? menteeId).toString();
      if (menteeId.isEmpty) {
        return;
      }
      _menteesById[menteeId] = MenteeRecord(id: menteeId, name: menteeName);
    }

    for (final row in rankedPairs) {
      ensureMentor(row);
      ensureMentee(row);
      _setPairPercentFromRow(row);
    }
    for (final row in assignments) {
      ensureMentor(row);
      ensureMentee(row);
      _setPairPercentFromRow(row);
    }

    final assigned = <String>{};
    for (final row in assignments) {
      final mentorId = (row['mentor_id'] ?? '').toString();
      final menteeId = (row['mentee_id'] ?? '').toString();
      if (!_mentorsById.containsKey(mentorId) ||
          !_menteesById.containsKey(menteeId)) {
        continue;
      }
      _mentorsById[mentorId]!.menteeIds.add(menteeId);
      assigned.add(menteeId);
    }

    for (final menteeId in _menteesById.keys) {
      if (!assigned.contains(menteeId)) {
        _unmatchedMenteeIds.add(menteeId);
      }
    }
  }

  void _setPairPercentFromRow(dynamic row) {
    final menteeId = (row['mentee_id'] ?? '').toString();
    final mentorId = (row['mentor_id'] ?? '').toString();
    if (menteeId.isEmpty || mentorId.isEmpty) {
      return;
    }

    final raw = row['match_percent'];
    double? value;
    if (raw is num) {
      value = raw.toDouble();
    } else if (raw != null) {
      value = double.tryParse(raw.toString().replaceAll('%', '').trim());
    }
    if (value == null) {
      return;
    }

    _pairMatchPercent[PairKey(menteeId: menteeId, mentorId: mentorId)] = value;
  }

  double? _matchPercentForPair(String menteeId, String mentorId) {
    return _pairMatchPercent[PairKey(menteeId: menteeId, mentorId: mentorId)];
  }

  String _matchBand(double? percent) {
    if (percent == null) {
      return 'unknown';
    }
    if (percent >= 90) {
      return 'exceptional';
    }
    if (percent >= 75) {
      return 'strong';
    }
    if (percent >= 60) {
      return 'decent';
    }
    if (percent >= 45) {
      return 'possible';
    }
    return 'weak';
  }

  void _moveMenteeToMentor(String menteeId, String mentorId) {
    if (!_mentorsById.containsKey(mentorId) ||
        !_menteesById.containsKey(menteeId)) {
      return;
    }
    setState(() {
      for (final mentor in _mentorsById.values) {
        mentor.menteeIds.remove(menteeId);
      }
      _unmatchedMenteeIds.remove(menteeId);
      _mentorsById[mentorId]!.menteeIds.add(menteeId);

      _lockedPairs.removeWhere(
          (pair) => pair.menteeId == menteeId && pair.mentorId != mentorId);
      _rejectedPairs.remove(PairKey(menteeId: menteeId, mentorId: mentorId));
    });
  }

  void _breakPair(String menteeId, String mentorId) {
    setState(() {
      _mentorsById[mentorId]?.menteeIds.remove(menteeId);
      _unmatchedMenteeIds.add(menteeId);
      _lockedPairs.remove(PairKey(menteeId: menteeId, mentorId: mentorId));
      _rejectedPairs.add(PairKey(menteeId: menteeId, mentorId: mentorId));
    });
  }

  void _moveMenteeToUnmatched(String menteeId) {
    setState(() {
      for (final mentor in _mentorsById.values) {
        mentor.menteeIds.remove(menteeId);
      }
      _lockedPairs.removeWhere((pair) => pair.menteeId == menteeId);
      _unmatchedMenteeIds.add(menteeId);
    });
  }

  void _toggleLock(String menteeId, String mentorId) {
    final key = PairKey(menteeId: menteeId, mentorId: mentorId);
    setState(() {
      if (_lockedPairs.contains(key)) {
        _lockedPairs.remove(key);
      } else {
        _lockedPairs.add(key);
      }
    });
  }

  void _addExclusionPair() {
    final menteeId = _selectedExclusionMenteeId;
    final mentorId = _selectedExclusionMentorId;
    if (menteeId == null || mentorId == null) {
      return;
    }
    setState(() {
      _exclusionPairs.add(PairKey(menteeId: menteeId, mentorId: mentorId));
      _status = 'Added exclusion pair.';
    });
  }

  Future<void> _resetAndRunFromScratch() async {
    setState(() {
      _lockedPairs.clear();
      _rejectedPairs.clear();
      _exclusionPairs.clear();
      _selectedExclusionMenteeId = null;
      _selectedExclusionMentorId = null;
      _status = 'Reset constraints. Running from scratch...';
    });
    await _runMatch(rerun: false);
  }

  Future<void> _exportCurrentBoard() async {
    final rows = <Map<String, dynamic>>[];
    for (final mentor in _mentorCards) {
      for (final menteeId in mentor.menteeIds) {
        final mentee = _menteesById[menteeId];
        final matchPercent = _matchPercentForPair(menteeId, mentor.mentorId);
        final isLocked = _lockedPairs
            .contains(PairKey(menteeId: menteeId, mentorId: mentor.mentorId));
        rows.add({
          'mentor_id': mentor.mentorId,
          'mentor_name': mentor.mentorName,
          'mentee_id': menteeId,
          'mentee_name': mentee?.name ?? menteeId,
          'match_percent': matchPercent?.toStringAsFixed(2) ?? '',
          'match_band': _matchBand(matchPercent),
          'lock_status': isLocked ? 'locked' : 'unlocked',
        });
      }
    }

    for (final menteeId in _unmatchedMenteeIds) {
      final mentee = _menteesById[menteeId];
      rows.add({
        'mentor_id': '',
        'mentor_name': 'UNMATCHED',
        'mentee_id': menteeId,
        'mentee_name': mentee?.name ?? menteeId,
        'match_percent': '',
        'match_band': '',
        'lock_status': 'unlocked',
      });
    }

    try {
      final bytes = await widget.apiClient.exportAssignments(rows);
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..download = 'final_assignments.xlsx'
        ..style.display = 'none';
      html.document.body?.children.add(anchor);
      anchor.click();
      anchor.remove();
      html.Url.revokeObjectUrl(url);
      setState(() => _status = 'Downloaded final_assignments.xlsx');
    } on ApiUnauthorizedException {
      setState(() => _status = 'Session expired. Please log in again.');
      widget.onLogout();
    } catch (e) {
      setState(() => _status = 'Export failed: $e');
    }
  }

  Widget _buildMenteeChip({
    required MenteeRecord mentee,
    required String mentorId,
  }) {
    final key = PairKey(menteeId: mentee.id, mentorId: mentorId);
    final isLocked = _lockedPairs.contains(key);

    return Draggable<String>(
      data: mentee.id,
      feedback: Material(
        color: Colors.transparent,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(8),
            boxShadow: const [BoxShadow(blurRadius: 6, color: Colors.black26)],
          ),
          child: Text(mentee.name),
        ),
      ),
      childWhenDragging: Opacity(
        opacity: 0.45,
        child: _menteeTile(mentee, mentorId, isLocked),
      ),
      child: _menteeTile(mentee, mentorId, isLocked),
    );
  }

  Widget _menteeTile(MenteeRecord mentee, String mentorId, bool isLocked) {
    final percent = _matchPercentForPair(mentee.id, mentorId);
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFD8D8D8)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(mentee.name, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(
                  percent == null
                      ? 'Match: score unavailable'
                      : 'Match: ${percent.toStringAsFixed(2)}% [${_matchBand(percent)}]',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey.shade700,
                      ),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: isLocked ? 'Unlock Pair' : 'Lock Pair',
            icon: Icon(isLocked ? Icons.lock : Icons.lock_open),
            color: isLocked ? NCSUColors.bioIndigo : Colors.grey.shade700,
            onPressed: () => _toggleLock(mentee.id, mentorId),
          ),
          IconButton(
            tooltip: 'Break Match',
            icon: const Icon(Icons.close),
            color: NCSUColors.reynoldsRed,
            onPressed: () => _breakPair(mentee.id, mentorId),
          ),
        ],
      ),
    );
  }

  Widget _buildMentorCard(MentorCardState mentor) {
    return DragTarget<String>(
      onWillAcceptWithDetails: (_) => true,
      onAcceptWithDetails: (details) =>
          _moveMenteeToMentor(details.data, mentor.mentorId),
      builder: (context, candidates, rejected) {
        final isHovering = candidates.isNotEmpty;
        return Card(
          child: Container(
            width: 380,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isHovering
                    ? NCSUColors.wolfpackRed
                    : const Color(0xFFD0D0D0),
                width: isHovering ? 2 : 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(mentor.mentorName,
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 6),
                Text(
                  mentor.mentorId,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: Colors.grey.shade700),
                ),
                const SizedBox(height: 8),
                if (mentor.menteeIds.isEmpty)
                  Text(
                    'Drop a mentee here',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: Colors.grey.shade700),
                  ),
                for (final menteeId in mentor.menteeIds)
                  if (_menteesById.containsKey(menteeId))
                    _buildMenteeChip(
                      mentee: _menteesById[menteeId]!,
                      mentorId: mentor.mentorId,
                    ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildUnmatchedPool() {
    return DragTarget<String>(
      onWillAcceptWithDetails: (_) => true,
      onAcceptWithDetails: (details) => _moveMenteeToUnmatched(details.data),
      builder: (context, candidates, rejected) {
        return Container(
          width: 320,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border.all(
              color: candidates.isNotEmpty
                  ? NCSUColors.wolfpackRed
                  : const Color(0xFFD0D0D0),
              width: candidates.isNotEmpty ? 2 : 1,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Unmatched Pool',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Expanded(
                child: ListView(
                  children: _unmatchedMenteeIds.map((id) {
                    final mentee = _menteesById[id];
                    if (mentee == null) {
                      return const SizedBox.shrink();
                    }
                    return Draggable<String>(
                      data: mentee.id,
                      feedback: Material(
                        color: Colors.transparent,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(8),
                            boxShadow: const [
                              BoxShadow(blurRadius: 6, color: Colors.black26)
                            ],
                          ),
                          child: Text(mentee.name),
                        ),
                      ),
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 8),
                        decoration: BoxDecoration(
                          border: Border.all(color: const Color(0xFFD8D8D8)),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(mentee.name),
                            const SizedBox(height: 2),
                            Text(
                              'Drop onto a mentor to rematch',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: Colors.grey.shade700),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildExclusionBuilder() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SizedBox(
              width: 280,
              child: DropdownButtonFormField<String>(
                initialValue: _selectedExclusionMenteeId,
                decoration: const InputDecoration(labelText: 'Mentee'),
                items: _menteeRecords
                    .map((mentee) => DropdownMenuItem(
                          value: mentee.id,
                          child:
                              Text(mentee.name, overflow: TextOverflow.ellipsis),
                        ))
                    .toList(),
                onChanged: (value) =>
                    setState(() => _selectedExclusionMenteeId = value),
              ),
            ),
            SizedBox(
              width: 280,
              child: DropdownButtonFormField<String>(
                initialValue: _selectedExclusionMentorId,
                decoration: const InputDecoration(labelText: 'Mentor'),
                items: _mentorCards
                    .map((mentor) => DropdownMenuItem(
                          value: mentor.mentorId,
                          child: Text(mentor.mentorName,
                              overflow: TextOverflow.ellipsis),
                        ))
                    .toList(),
                onChanged: (value) =>
                    setState(() => _selectedExclusionMentorId = value),
              ),
            ),
            ElevatedButton(
              onPressed: _addExclusionPair,
              child: const Text('Add to Exclusion List'),
            ),
            if (_exclusionPairs.isNotEmpty)
              Text('Exclusions: ${_exclusionPairs.length}',
                  style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mentor Matcher Dashboard'),
        actions: [
          if (widget.isDev)
            TextButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => DevDashboardScreen(
                      apiClient: widget.apiClient,
                      onAuthExpired: widget.onLogout,
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.settings, color: Colors.white),
              label: const Text('Dev', style: TextStyle(color: Colors.white)),
            ),
          TextButton.icon(
            onPressed: widget.onLogout,
            icon: const Icon(Icons.logout, color: Colors.white),
            label: const Text('Logout', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed:
                          _loading ? null : () => _pickFile(mentor: true),
                      child: Text(_mentorFile == null
                          ? 'Upload Mentor File'
                          : _mentorFile!.filename),
                    ),
                    ElevatedButton(
                      onPressed:
                          _loading ? null : () => _pickFile(mentor: false),
                      child: Text(_menteeFile == null
                          ? 'Upload Mentee File'
                          : _menteeFile!.filename),
                    ),
                    ElevatedButton(
                      onPressed:
                          _loading ? null : () => _runMatch(rerun: false),
                      child: Text(_loading ? 'Running...' : 'Run Matching'),
                    ),
                    OutlinedButton(
                      onPressed: _loading ? null : () => _runMatch(rerun: true),
                      child: const Text('Rerun'),
                    ),
                    OutlinedButton(
                      onPressed: _loading ? null : _resetAndRunFromScratch,
                      child: const Text('Reset + Run From Scratch'),
                    ),
                    OutlinedButton(
                      onPressed: _loading ? null : _exportCurrentBoard,
                      child: const Text('Download Final XLSX'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            _buildExclusionBuilder(),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                _status,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: NCSUColors.wolfpackBlack),
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Row(
                children: [
                  Expanded(
                    child: _mentorCards.isEmpty
                        ? const Center(
                            child: Text('Run matching to render mentor cards.'))
                        : SingleChildScrollView(
                            child: Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children:
                                  _mentorCards.map(_buildMentorCard).toList(),
                            ),
                          ),
                  ),
                  const SizedBox(width: 10),
                  _buildUnmatchedPool(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
