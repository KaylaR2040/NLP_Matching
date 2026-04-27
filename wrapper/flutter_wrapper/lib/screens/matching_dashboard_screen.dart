// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:async';
import 'dart:html' as html;
import 'dart:math' as math;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../constants/ncsu_theme.dart';
import '../models/match_models.dart';
import '../services/api_client.dart';
import 'dev_dashboard_screen.dart';
import 'mentor_manager_screen.dart';
import 'mentors_directory_screen.dart';

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
  SelectedFile? _menteeFile;

  bool _loading = false;
  int _elapsedSeconds = 0;
  Timer? _progressTimer;
  // Stable display order set once after each match run — never re-sorted during dragging.
  List<String> _stableMentorOrder = const [];
  String _status =
      'Upload a mentee file to begin. Mentor data is sourced from Mentor Manager.';

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
    // Use the stable order set at run time — cards don't jump around during dragging.
    if (_stableMentorOrder.isNotEmpty) {
      return _stableMentorOrder
          .where(_mentorsById.containsKey)
          .map((id) => _mentorsById[id]!)
          .toList();
    }
    // Fallback sort before first run.
    final list = _mentorsById.values.toList();
    list.sort((a, b) => a.mentorName.toLowerCase().compareTo(b.mentorName.toLowerCase()));
    return list;
  }

  List<MenteeRecord> get _menteeRecords {
    final list = _menteesById.values.toList();
    list.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return list;
  }

  Future<void> _pickMenteeFile() async {
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
      _menteeFile = selected;
      _status =
          'Selected mentee file ${selected.filename}. Mentor source: Mentor Manager.';
    });
  }

  Future<void> _runMatch({required bool rerun}) async {
    if (!widget.isDev && _menteeFile != null) {
      // Demo users always use the server-side pre-loaded mentee data.
    } else if (widget.isDev && _menteeFile == null) {
      setState(() => _status = 'Mentee file is required.');
      return;
    }

    setState(() {
      _loading = true;
      _elapsedSeconds = 0;
      _status = rerun ? 'Rerunning matching...' : 'Running matching...';
    });

    _progressTimer?.cancel();
    _progressTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() => _elapsedSeconds++);
    });

    try {
      final blockedPairs = {..._rejectedPairs, ..._exclusionPairs};
      final payload = {
        'locked_pairs': _lockedPairs.map((pair) => pair.toJson()).toList(),
        'rejected_pairs': blockedPairs.map((pair) => pair.toJson()).toList(),
        'excluded_mentee_ids': <String>[],
        'excluded_mentor_ids': <String>[],
        'top_n': 20000,
      };

      final response = await widget.apiClient.runMatch(
        menteeFile: widget.isDev ? _menteeFile : null,
        payload: payload,
      );
      final result = (response['result'] as Map<String, dynamic>? ?? {});
      final source = (response['mentor_source'] ?? 'mentor_manager').toString();
      _applyBackendResult(result);
      setState(() {
        _status = rerun
            ? 'Rerun complete. Mentors source: $source.'
            : 'Run complete. Mentors source: $source.';
      });
    } on ApiUnauthorizedException {
      setState(() => _status = 'Session expired. Please log in again.');
      widget.onLogout();
    } catch (e) {
      setState(() => _status = 'Run failed: $e');
    } finally {
      _progressTimer?.cancel();
      _progressTimer = null;
      setState(() => _loading = false);
    }
  }

  void _applyBackendResult(Map<String, dynamic> result) {
    final assignments = (result['assignments'] as List? ?? const []);
    final rankedPairs = (result['top_ranked_pairs'] as List? ?? const []);
    final capacityByMentor =
        (result['mentor_capacity'] as Map<String, dynamic>? ?? const {});

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
      _applyMentorCapacityFromRow(row);
    }
    for (final row in assignments) {
      ensureMentor(row);
      ensureMentee(row);
      _setPairPercentFromRow(row);
      _applyMentorCapacityFromRow(row);
    }

    capacityByMentor.forEach((mentorId, details) {
      final id = mentorId.toString();
      if (!_mentorsById.containsKey(id) || details is! Map<String, dynamic>) {
        return;
      }
      final parsed = int.tryParse('${details['max_mentees'] ?? 1}') ?? 1;
      _mentorsById[id]!.maxMentees = parsed < 1 ? 1 : parsed;
    });

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

    // Set stable display order once: assigned mentors first (by count desc), then alphabetically.
    // This order never changes during the session so cards don't jump when mentees are moved.
    final ordered = _mentorsById.values.toList()
      ..sort((a, b) {
        final aHas = a.menteeIds.isNotEmpty ? 0 : 1;
        final bHas = b.menteeIds.isNotEmpty ? 0 : 1;
        if (aHas != bHas) return aHas - bHas;
        final sizeDiff = b.menteeIds.length - a.menteeIds.length;
        if (sizeDiff != 0) return sizeDiff;
        return a.mentorName.toLowerCase().compareTo(b.mentorName.toLowerCase());
      });
    _stableMentorOrder = ordered.map((m) => m.mentorId).toList();
  }

  void _applyMentorCapacityFromRow(dynamic row) {
    if (row is! Map<String, dynamic>) {
      return;
    }
    final mentorId = (row['mentor_id'] ?? '').toString();
    if (mentorId.isEmpty || !_mentorsById.containsKey(mentorId)) {
      return;
    }
    final parsed = int.tryParse('${row['mentor_capacity'] ?? 1}') ?? 1;
    _mentorsById[mentorId]!.maxMentees = parsed < 1 ? 1 : parsed;
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

  void _removeExclusionPair(PairKey pair) {
    setState(() {
      _exclusionPairs.remove(pair);
      _status = 'Removed exclusion pair.';
    });
  }

  void _clearExclusionPairs() {
    setState(() {
      _exclusionPairs.clear();
      _status = 'Cleared exclusion list.';
    });
  }

  Future<void> _resetAndRunFromScratch() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reset + Run From Scratch'),
        content: const Text(
          'This clears all locked pairs, rejected pairs, and exclusions, '
          'then runs a fresh match.\n\nAny manual assignments will be lost.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Reset & Run'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() {
      _lockedPairs.clear();
      _rejectedPairs.clear();
      _exclusionPairs.clear();
      _selectedExclusionMenteeId = null;
      _selectedExclusionMentorId = null;
      _status = 'Reset all constraints. Running fresh match...';
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
      maxSimultaneousDrags: 1,
      dragAnchorStrategy: pointerDragAnchorStrategy,
      feedback: Material(
        color: Colors.transparent,
        child: Container(
          width: 240,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(8),
            boxShadow: const [BoxShadow(blurRadius: 6, color: Colors.black26)],
          ),
          child: Text(
            mentee.name,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ),
      childWhenDragging: Opacity(
        opacity: 0.45,
        child: MouseRegion(
          cursor: SystemMouseCursors.grabbing,
          child: _menteeTile(mentee, mentorId, isLocked),
        ),
      ),
      child: MouseRegion(
        cursor: SystemMouseCursors.grab,
        child: _menteeTile(mentee, mentorId, isLocked),
      ),
    );
  }

  Widget _menteeTile(MenteeRecord mentee, String mentorId, bool isLocked) {
    final percent = _matchPercentForPair(mentee.id, mentorId);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFD8D8D8)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(Icons.drag_indicator, color: Colors.grey.shade700, size: 18),
          const SizedBox(width: 4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  mentee.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  percent == null
                      ? 'Match unavailable'
                      : '${percent.toStringAsFixed(2)}% [${_matchBand(percent)}]',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey.shade700,
                      ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
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

  Widget _buildMentorBoardCard(MentorCardState mentor) {
    final sortedMenteeIds = [...mentor.menteeIds]..sort((a, b) {
      final aPercent = _matchPercentForPair(a, mentor.mentorId) ?? -1;
      final bPercent = _matchPercentForPair(b, mentor.mentorId) ?? -1;
      final percentCompare = bPercent.compareTo(aPercent);
      if (percentCompare != 0) {
        return percentCompare;
      }

      final left = _menteesById[a]?.name ?? a;
      final right = _menteesById[b]?.name ?? b;
      return left.toLowerCase().compareTo(right.toLowerCase());
    });

    return DragTarget<String>(
      onWillAcceptWithDetails: (_) => true,
      onAcceptWithDetails: (details) =>
          _moveMenteeToMentor(details.data, mentor.mentorId),
      builder: (context, candidates, _rejected) {
        final isHovering = candidates.isNotEmpty;
        return Card(
          elevation: 0,
          child: Container(
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
                Text(
                  mentor.mentorName,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  mentor.mentorId,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: Colors.grey.shade700),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 6),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF6F6F6),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: const Color(0xFFE0E0E0)),
                  ),
                  child: Text(
                    'Capacity ${mentor.menteeIds.length}/${mentor.maxMentees}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: sortedMenteeIds.isEmpty
                      ? Center(
                          child: Text(
                            'Drop a mentee here',
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(color: Colors.grey.shade700),
                          ),
                        )
                      : Scrollbar(
                          thumbVisibility: sortedMenteeIds.length > 4,
                          child: ListView.builder(
                            primary: false,
                            itemCount: sortedMenteeIds.length,
                            itemBuilder: (context, index) {
                              final menteeId = sortedMenteeIds[index];
                              final mentee = _menteesById[menteeId];
                              if (mentee == null) {
                                return const SizedBox.shrink();
                              }
                              return _buildMenteeChip(
                                mentee: mentee,
                                mentorId: mentor.mentorId,
                              );
                            },
                          ),
                        ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildUnmatchedBoardCard() {
    final sortedUnmatched = _unmatchedMenteeIds.toList()
      ..sort((a, b) {
        final left = _menteesById[a]?.name ?? a;
        final right = _menteesById[b]?.name ?? b;
        return left.toLowerCase().compareTo(right.toLowerCase());
      });

    return DragTarget<String>(
      onWillAcceptWithDetails: (_) => true,
      onAcceptWithDetails: (details) => _moveMenteeToUnmatched(details.data),
      builder: (context, candidates, _rejected) {
        final isHovering = candidates.isNotEmpty;
        return Card(
          elevation: 0,
          child: Container(
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
                Text(
                  'Unmatched Pool',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                Expanded(
                  child: sortedUnmatched.isEmpty
                      ? Center(
                          child: Text(
                            'No unmatched mentees',
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(color: Colors.grey.shade700),
                          ),
                        )
                      : Scrollbar(
                          thumbVisibility: sortedUnmatched.length > 4,
                          child: ListView.builder(
                            primary: false,
                            itemCount: sortedUnmatched.length,
                            itemBuilder: (context, index) {
                              final menteeId = sortedUnmatched[index];
                              final mentee = _menteesById[menteeId];
                              if (mentee == null) {
                                return const SizedBox.shrink();
                              }
                              return Draggable<String>(
                                data: mentee.id,
                                maxSimultaneousDrags: 1,
                                dragAnchorStrategy: pointerDragAnchorStrategy,
                                feedback: Material(
                                  color: Colors.transparent,
                                  child: Container(
                                    width: 240,
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(8),
                                      boxShadow: const [
                                        BoxShadow(
                                            blurRadius: 6,
                                            color: Colors.black26),
                                      ],
                                    ),
                                    child: Text(
                                      mentee.name,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ),
                                child: MouseRegion(
                                  cursor: SystemMouseCursors.grab,
                                  child: Container(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 8, vertical: 8),
                                    decoration: BoxDecoration(
                                      border: Border.all(
                                          color: const Color(0xFFD8D8D8)),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(Icons.drag_indicator,
                                            size: 18,
                                            color: Colors.grey.shade700),
                                        const SizedBox(width: 4),
                                        Expanded(
                                          child: Text(
                                            mentee.name,
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildMentorColumnsGrid(double maxWidth) {
    if (_mentorCards.isEmpty) {
      return Card(
        elevation: 0,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFD0D0D0)),
          ),
          child: Center(
            child: Text(
              'No mentor columns yet.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.black54,
                  ),
            ),
          ),
        ),
      );
    }

    final maxCrossExtent = maxWidth >= 1300
        ? 380.0
        : maxWidth >= 1000
            ? 350.0
            : 320.0;
    final maxSlots = _mentorCards.fold<int>(
      0,
      (currentMax, mentor) => math.max(
        currentMax,
        math.max(mentor.maxMentees, mentor.menteeIds.length),
      ),
    );
    final visibleRows = maxSlots <= 0 ? 2 : maxSlots.clamp(2, 5);
    final cardHeight =
        (205 + (visibleRows * 40)).toDouble().clamp(285.0, 360.0);

    return GridView.builder(
      itemCount: _mentorCards.length,
      gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: maxCrossExtent,
        mainAxisExtent: cardHeight,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemBuilder: (context, index) =>
          _buildMentorBoardCard(_mentorCards[index]),
    );
  }

  Widget _buildBoardWorkspace() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final railWidth =
            (constraints.maxWidth * 0.25).clamp(320.0, 390.0).toDouble();
        final mainWidth = constraints.maxWidth - railWidth - 12;
        final useStackedLayout = mainWidth < 620;

        if (useStackedLayout) {
          return Column(
            children: [
              Expanded(
                child: _buildMentorColumnsGrid(constraints.maxWidth),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 380,
                width: double.infinity,
                child: _buildUnmatchedBoardCard(),
              ),
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: _buildMentorColumnsGrid(mainWidth),
            ),
            const SizedBox(width: 12),
            SizedBox(
              width: railWidth,
              child: _buildUnmatchedBoardCard(),
            ),
          ],
        );
      },
    );
  }

  Widget _buildExclusionBuilder() {
    final sortedPairs = _exclusionPairs.toList()
      ..sort((a, b) {
        final left = '${a.menteeId}::${a.mentorId}';
        final right = '${b.menteeId}::${b.mentorId}';
        return left.toLowerCase().compareTo(right.toLowerCase());
      });

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
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
                              child: Text(mentee.name,
                                  overflow: TextOverflow.ellipsis),
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
                if (sortedPairs.isNotEmpty)
                  OutlinedButton.icon(
                    onPressed: _clearExclusionPairs,
                    icon: const Icon(Icons.clear_all),
                    label: const Text('Clear Exclusions'),
                  ),
                Text(
                  'Exclusions: ${sortedPairs.length}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (sortedPairs.isEmpty)
              Text(
                'No exclusion pairs yet.',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Colors.black54),
              )
            else
              SizedBox(
                height: 160,
                child: ListView.separated(
                  itemCount: sortedPairs.length,
                  itemBuilder: (context, index) {
                    final pair = sortedPairs[index];
                    final mentee = _menteesById[pair.menteeId];
                    final mentor = _mentorsById[pair.mentorId];
                    final menteeLabel = mentee?.name ?? pair.menteeId;
                    final mentorLabel = mentor?.mentorName ?? pair.mentorId;
                    return ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        '$menteeLabel -> $mentorLabel',
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        '${pair.menteeId} -> ${pair.mentorId}',
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: IconButton(
                        tooltip: 'Remove',
                        onPressed: () => _removeExclusionPair(pair),
                        icon: const Icon(Icons.close),
                      ),
                    );
                  },
                  separatorBuilder: (_, __) => const Divider(height: 1),
                ),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hasResult = _mentorCards.isNotEmpty || _unmatchedMenteeIds.isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mentor Matcher Dashboard'),
        actions: [
          TextButton.icon(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => MentorsDirectoryScreen(
                    apiClient: widget.apiClient,
                    onAuthExpired: widget.onLogout,
                  ),
                ),
              );
            },
            icon: const Icon(Icons.groups_outlined, color: Colors.white),
            label: const Text('Mentors', style: TextStyle(color: Colors.white)),
          ),
          if (widget.isDev)
            TextButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => MentorManagerScreen(
                      apiClient: widget.apiClient,
                      onAuthExpired: widget.onLogout,
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.manage_accounts_outlined,
                  color: Colors.white),
              label:
                  const Text('Manager', style: TextStyle(color: Colors.white)),
            ),
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
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1650),
          child: Padding(
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
                        if (widget.isDev) ...[
                          // ── Dev: upload mentee file ──────────────────
                          OutlinedButton.icon(
                            onPressed: _loading ? null : _pickMenteeFile,
                            icon: const Icon(Icons.upload_file),
                            label: Text(_menteeFile == null
                                ? 'Upload Mentee CSV/XLSX'
                                : 'Mentees: ${_menteeFile!.filename}'),
                          ),
                        ] else ...[
                          // ── Demo: show pre-loaded chip ───────────────
                          const Chip(
                            avatar: Icon(Icons.people_outline, size: 16),
                            label: Text('Mentees: demo data (10 students)'),
                          ),
                        ],
                        // ── Mentor source chip (read-only status) ────────
                        const Chip(
                          avatar: Icon(Icons.storage_outlined, size: 16),
                          label: Text('Mentors: database'),
                        ),
                        const SizedBox(width: 4),
                        // ── Primary action ───────────────────────────────
                        ElevatedButton.icon(
                          onPressed: (_loading || (widget.isDev && _menteeFile == null))
                              ? null
                              : () => _runMatch(rerun: false),
                          icon: const Icon(Icons.play_arrow),
                          label: Text(_loading ? 'Running...' : 'Run Matching'),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 20, vertical: 12),
                          ),
                        ),
                        // ── Secondary actions ────────────────────────────
                        if (widget.isDev)
                          OutlinedButton.icon(
                            onPressed: (_loading || _menteeFile == null)
                                ? null
                                : () => _runMatch(rerun: true),
                            icon: const Icon(Icons.refresh),
                            label: const Text('Rerun'),
                          ),
                        OutlinedButton.icon(
                          onPressed: _loading ? null : _exportCurrentBoard,
                          icon: const Icon(Icons.download),
                          label: const Text('Download XLSX'),
                        ),
                        // ── Destructive action (dev only) ────────────────
                        if (widget.isDev)
                          TextButton.icon(
                            onPressed: (_loading || _menteeFile == null)
                                ? null
                                : _resetAndRunFromScratch,
                            icon: const Icon(Icons.restart_alt, size: 18),
                            label: const Text('Reset & Rerun'),
                            style: TextButton.styleFrom(
                              foregroundColor: Colors.red.shade700,
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                _buildExclusionBuilder(),
                const SizedBox(height: 8),
                if (_loading) ...[
                  LinearProgressIndicator(
                    backgroundColor: Colors.grey.shade200,
                    color: NCSUColors.wolfpackRed,
                  ),
                  const SizedBox(height: 6),
                ],
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    _loading
                        ? '$_status (${_elapsedSeconds}s elapsed — typically 20–60s)'
                        : _status,
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: NCSUColors.wolfpackBlack),
                  ),
                ),
                const SizedBox(height: 6),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Drag mentees between mentor columns and the right-side Unmatched rail. Lock preserves a pair on rerun.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.black87,
                        ),
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: hasResult
                      ? _buildBoardWorkspace()
                      : const Center(
                          child: Text('Run matching to render mentor cards.'),
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
