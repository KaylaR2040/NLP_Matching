// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:html' as html;

import 'package:flutter/material.dart';

import '../models/mentor_models.dart';
import '../services/api_client.dart';

class MentorsDirectoryScreen extends StatefulWidget {
  final ApiClient apiClient;
  final VoidCallback onAuthExpired;

  const MentorsDirectoryScreen({
    super.key,
    required this.apiClient,
    required this.onAuthExpired,
  });

  @override
  State<MentorsDirectoryScreen> createState() => _MentorsDirectoryScreenState();
}

class _MentorsDirectoryScreenState extends State<MentorsDirectoryScreen> {
  final TextEditingController _queryController = TextEditingController();
  final TextEditingController _companyController = TextEditingController();
  final TextEditingController _locationController = TextEditingController();

  bool _loading = false;
  String _status = 'Loading mentors...';
  bool _activeOnly = true;
  bool _linkedInOnly = false;

  List<MentorRecord> _items = const [];
  int _total = 0;

  @override
  void initState() {
    super.initState();
    _loadMentors();
  }

  @override
  void dispose() {
    _queryController.dispose();
    _companyController.dispose();
    _locationController.dispose();
    super.dispose();
  }

  void _goBack() {
    if (Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
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
        activeOnly: _activeOnly,
        hasLinkedIn: _linkedInOnly ? true : null,
        company: _companyController.text,
        location: _locationController.text,
        limit: 1000,
      );

      final parsed = MentorsListResult.fromJson(response);
      setState(() {
        _items = parsed.items;
        _total = parsed.total;
        _status = parsed.items.isEmpty
            ? 'No mentors matched your filters.'
            : 'Showing ${parsed.items.length} of ${parsed.total} mentors.';
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
        _items = const [];
        _total = 0;
        _status = 'Failed to load mentors: $e';
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  void _openLinkedIn(String url) {
    if (url.trim().isEmpty) {
      return;
    }
    html.window.open(url.trim(), '_blank');
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

    final fallback = mentor.fullName.trim();
    if (fallback.isNotEmpty) {
      return fallback.characters.first.toUpperCase();
    }
    return '?';
  }

  Widget _mentorCard(MentorRecord mentor) {
    final hasPhoto = mentor.profilePhotoUrl.trim().isNotEmpty;
    final hasLinkedIn = mentor.linkedInUrl.trim().isNotEmpty;
    final company = mentor.currentCompany.trim();
    final title = mentor.currentJobTitle.trim();
    final location = mentor.currentLocation.trim().isNotEmpty
        ? mentor.currentLocation.trim()
        : [mentor.currentCity.trim(), mentor.currentState.trim()]
            .where((value) => value.isNotEmpty)
            .join(', ');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundImage:
                      hasPhoto ? NetworkImage(mentor.profilePhotoUrl) : null,
                  child: hasPhoto ? null : Text(_initialsFor(mentor)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        mentor.fullName.trim().isNotEmpty
                            ? mentor.fullName.trim()
                            : mentor.email,
                        style: Theme.of(context).textTheme.titleMedium,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        title.isNotEmpty ? title : 'Title not provided',
                        style: Theme.of(context).textTheme.bodyMedium,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (company.isNotEmpty)
              _lineItem(Icons.business_outlined, company)
            else
              _lineItem(Icons.business_outlined, 'Company not provided'),
            const SizedBox(height: 4),
            if (location.isNotEmpty)
              _lineItem(Icons.location_on_outlined, location)
            else
              _lineItem(Icons.location_on_outlined, 'Location not provided'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (mentor.industryFocusArea.trim().isNotEmpty)
                  Chip(
                    label: SizedBox(
                      width: 130,
                      child: Text(
                        mentor.industryFocusArea.trim(),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                Chip(
                  label: Text(mentor.isActive ? 'Active' : 'Inactive'),
                ),
              ],
            ),
            const Spacer(),
            Row(
              children: [
                if (hasLinkedIn)
                  ElevatedButton.icon(
                    onPressed: () => _openLinkedIn(mentor.linkedInUrl),
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('LinkedIn'),
                  )
                else
                  OutlinedButton.icon(
                    onPressed: null,
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('No LinkedIn URL'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _lineItem(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 16),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        leading: IconButton(
          tooltip: 'Back',
          onPressed: _goBack,
          icon: const Icon(Icons.arrow_back),
        ),
        title: const Text('Mentors Directory'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(14),
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
                    SizedBox(
                      width: 300,
                      child: TextField(
                        controller: _queryController,
                        decoration: const InputDecoration(
                          labelText: 'Search name, email, company, title',
                          border: OutlineInputBorder(),
                        ),
                        onSubmitted: (_) => _loadMentors(),
                      ),
                    ),
                    SizedBox(
                      width: 220,
                      child: TextField(
                        controller: _companyController,
                        decoration: const InputDecoration(
                          labelText: 'Company filter',
                          border: OutlineInputBorder(),
                        ),
                        onSubmitted: (_) => _loadMentors(),
                      ),
                    ),
                    SizedBox(
                      width: 220,
                      child: TextField(
                        controller: _locationController,
                        decoration: const InputDecoration(
                          labelText: 'Location filter',
                          border: OutlineInputBorder(),
                        ),
                        onSubmitted: (_) => _loadMentors(),
                      ),
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Checkbox(
                          value: _activeOnly,
                          onChanged: _loading
                              ? null
                              : (value) {
                                  setState(() => _activeOnly = value ?? true);
                                  _loadMentors();
                                },
                        ),
                        const Text('Active only'),
                      ],
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Checkbox(
                          value: _linkedInOnly,
                          onChanged: _loading
                              ? null
                              : (value) {
                                  setState(
                                      () => _linkedInOnly = value ?? false);
                                  _loadMentors();
                                },
                        ),
                        const Text('Has LinkedIn'),
                      ],
                    ),
                    ElevatedButton.icon(
                      onPressed: _loading ? null : _loadMentors,
                      icon: const Icon(Icons.search),
                      label: const Text('Apply Filters'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(_status),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _items.isEmpty
                      ? Center(
                          child: Text(
                            _total == 0
                                ? 'No mentors available yet.'
                                : 'No mentors matched your filters.',
                          ),
                        )
                      : LayoutBuilder(
                          builder: (context, constraints) {
                            final width = constraints.maxWidth;
                            int crossAxisCount = 1;
                            if (width >= 1500) {
                              crossAxisCount = 4;
                            } else if (width >= 1100) {
                              crossAxisCount = 3;
                            } else if (width >= 700) {
                              crossAxisCount = 2;
                            }

                            return GridView.builder(
                              itemCount: _items.length,
                              gridDelegate:
                                  SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: crossAxisCount,
                                crossAxisSpacing: 10,
                                mainAxisSpacing: 10,
                                mainAxisExtent: crossAxisCount == 1 ? 292 : 272,
                              ),
                              itemBuilder: (context, index) {
                                return _mentorCard(_items[index]);
                              },
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
