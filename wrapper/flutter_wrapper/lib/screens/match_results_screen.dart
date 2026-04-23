import 'package:flutter/material.dart';

import '../constants/ncsu_theme.dart';
import '../services/api_client.dart';

class MatchResultsScreen extends StatefulWidget {
  final ApiClient apiClient;
  final VoidCallback onAuthExpired;

  const MatchResultsScreen({
    super.key,
    required this.apiClient,
    required this.onAuthExpired,
  });

  @override
  State<MatchResultsScreen> createState() => _MatchResultsScreenState();
}

class _MatchResultsScreenState extends State<MatchResultsScreen> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _results = const [];
  Map<String, dynamic>? _detail;
  int? _detailId;

  @override
  void initState() {
    super.initState();
    _loadResults();
  }

  Future<void> _loadResults() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final rows = await widget.apiClient.listMatchResults(limit: 50);
      setState(() {
        _results = rows;
        _loading = false;
      });
    } on ApiUnauthorizedException {
      widget.onAuthExpired();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _loadDetail(int id) async {
    setState(() {
      _loading = true;
      _detailId = id;
      _detail = null;
    });
    try {
      final detail = await widget.apiClient.getMatchResult(id);
      setState(() {
        _detail = detail;
        _loading = false;
      });
    } on ApiUnauthorizedException {
      widget.onAuthExpired();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
        _detailId = null;
      });
    }
  }

  String _formatDate(dynamic raw) {
    if (raw == null) return '—';
    try {
      final dt = DateTime.parse(raw.toString()).toLocal();
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
          '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return raw.toString();
    }
  }

  Widget _buildList() {
    if (_results.isEmpty) {
      return const Center(
        child: Text('No match runs recorded yet. Run a match to populate history.'),
      );
    }
    return ListView.separated(
      itemCount: _results.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final row = _results[index];
        final id = row['id'] as int?;
        final summary = row['summary'] as Map<String, dynamic>? ?? const {};
        final assignments = summary['assignments'] as int? ?? 0;
        final menteeCount = summary['mentees_input'] as int? ?? 0;

        return ListTile(
          onTap: id != null ? () => _loadDetail(id) : null,
          selected: id == _detailId,
          selectedTileColor: NCSUColors.wolfpackRed.withValues(alpha: 0.06),
          title: Text(
            _formatDate(row['run_at']),
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          subtitle: Text(
            'By: ${row['run_by'] ?? '—'} • '
            '$menteeCount mentees • '
            '$assignments assignments • '
            'Source: ${row['mentor_source'] ?? '—'}',
          ),
          trailing: const Icon(Icons.chevron_right),
        );
      },
    );
  }

  Widget _buildDetail() {
    final d = _detail;
    if (d == null) {
      return const Center(child: Text('Select a run to view details.'));
    }
    final summary = d['summary'] as Map<String, dynamic>? ?? const {};
    final assignments = (d['assignments'] as List?)?.cast<Map<String, dynamic>>() ?? const [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Run #${d['id']} — ${_formatDate(d['run_at'])}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          _kv('Run by', d['run_by']),
          _kv('Mentee source', d['mentee_source']),
          _kv('Mentor source', d['mentor_source']),
          const SizedBox(height: 12),
          Text('Summary', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          ...summary.entries.map((e) => _kv(e.key, e.value)),
          const SizedBox(height: 12),
          Text('Assignments (${assignments.length})',
              style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          ...assignments.map((a) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  '${a['mentee_name'] ?? a['mentee_id']} → '
                  '${a['mentor_name'] ?? a['mentor_id']} '
                  '(${a['match_percent'] ?? ''}%)',
                ),
              )),
        ],
      ),
    );
  }

  Widget _kv(String key, dynamic value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 160,
            child: Text(
              key,
              style: const TextStyle(fontWeight: FontWeight.w500, color: Colors.black54),
            ),
          ),
          Expanded(child: Text(value?.toString() ?? '—')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Match Run History'),
        foregroundColor: NCSUColors.wolfpackWhite,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _loadResults,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('Error: $_error', textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed: _loadResults,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : LayoutBuilder(builder: (context, constraints) {
                  if (constraints.maxWidth >= 700) {
                    return Row(
                      children: [
                        SizedBox(width: 340, child: _buildList()),
                        const VerticalDivider(width: 1),
                        Expanded(child: _buildDetail()),
                      ],
                    );
                  }
                  return _detail == null ? _buildList() : _buildDetail();
                }),
    );
  }
}
