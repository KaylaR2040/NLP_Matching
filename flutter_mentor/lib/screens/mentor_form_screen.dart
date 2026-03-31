import 'package:flutter/material.dart';
import '../constants/form_options.dart';
import '../models/mentor_form_data.dart';
import '../services/api_service.dart';
import '../services/form_data_loader.dart';
import '../widgets/form_field_widgets.dart';

class MentorFormScreen extends StatefulWidget {
  const MentorFormScreen({super.key});

  @override
  State<MentorFormScreen> createState() => _MentorFormScreenState();
}

class _MentorFormScreenState extends State<MentorFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final MentorFormData _formData;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _formData = MentorFormData();
    _loadAssets();
  }

  Future<void> _loadAssets() async {
    await FormDataLoader().loadAll();
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(32),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      theme.colorScheme.primary,
                      theme.colorScheme.primary.withValues(alpha: 0.82),
                    ],
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ECE Mentor Interest Form',
                      style: theme.textTheme.headlineLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Thank you for your interest in becoming an Alumni Mentor for the ECE Program. '
                      'Please complete this form so we can match you with a current student.',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: Colors.white.withValues(alpha: 0.95),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Once received, you will get an email with further information from the Career & Alumni Specialist, Kaitlyn Godfrey.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: Colors.white.withValues(alpha: 0.92),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Questions? Contact: kngodfre@ncsu.edu',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),

              Container(
                constraints: const BoxConstraints(maxWidth: 900),
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    FormFieldWidgets.buildSection(
                      context,
                      'Required Mentor Information',
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildEmailField(
                      context,
                      _formData.emailController,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'This form collects emails.',
                      style: theme.textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.firstNameController,
                      'First Name',
                      true,
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.lastNameController,
                      'Last Name',
                      true,
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildPronounsField(
                      context,
                      _formData.pronouns,
                      (value) async {
                        final normalized = await _resolveOtherSelection(
                          value,
                          fieldLabel: 'Pronouns',
                        );
                        if (!mounted) return;
                        setState(() {
                          _formData.pronouns
                            ..clear()
                            ..addAll(normalized);
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    _buildLinkedInField(context),
                    const SizedBox(height: 16),
                    _buildDegreesSection(context),
                    const SizedBox(height: 16),
                    _buildCurrentLocationFields(context),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.currentJobTitleController,
                      'Current Job Title',
                      true,
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.currentCompanyController,
                      'Current Employer / Company',
                      true,
                    ),
                    const SizedBox(height: 32),

                    FormFieldWidgets.buildSection(
                      context,
                      'Mentoring and Experience',
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildYesNoField(
                      context,
                      'Do you have previous mentoring experience, or were you once a mentee? *',
                      _formData.previousMentorship,
                      (value) =>
                          setState(() => _formData.previousMentorship = value),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiLineTextField(
                      context,
                      _formData.previousInvolvementController,
                      'If yes, briefly explain your previous involvement',
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiSelectChips(
                      context,
                      'Industry / Focus Area *',
                      'Select all that apply',
                      FormOptions.industryFocusAreas,
                      _formData.industryFocusAreas,
                      (value) async {
                        final normalized = await _resolveOtherSelection(
                          value,
                          fieldLabel: 'Industry / Focus Area',
                        );
                        if (!mounted) return;
                        setState(() {
                          _formData.industryFocusAreas
                            ..clear()
                            ..addAll(normalized);
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildOrganizationsField(
                      context,
                      _formData.previousInvolvementOrgs,
                      (value) => setState(() {
                        _formData.previousInvolvementOrgs
                          ..clear()
                          ..addAll(value);
                      }),
                    ),
                    const SizedBox(height: 32),

                    FormFieldWidgets.buildSection(context, 'Direct Questions'),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiLineTextField(
                      context,
                      _formData.whyInterestedController,
                      'Why are you interested in becoming an ECE Alumni Mentor? *',
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiLineTextField(
                      context,
                      _formData.professionalExperienceController,
                      'Professional experience (field of interest, previous jobs, career changes) *',
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiLineTextField(
                      context,
                      _formData.aboutYourselfController,
                      'Tell us about yourself (interests, hobbies, family, etc.) *',
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildSingleSelectChips(
                      context,
                      'How many students would you be interested in mentoring? *',
                      null,
                      FormOptions.studentsCountOptions,
                      _formData.studentsInterested,
                      (value) =>
                          setState(() => _formData.studentsInterested = value),
                    ),
                    const SizedBox(height: 32),

                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _submitForm,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                        child: const Text(
                          'Submit Mentor Form',
                          style: TextStyle(fontSize: 16),
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLinkedInField(BuildContext context) {
    return FormFieldWidgets.buildTextField(
      context,
      _formData.linkedinController,
      'LinkedIn profile URL',
      false,
    );
  }

  Widget _buildCurrentLocationFields(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 2,
          child: FormFieldWidgets.buildTextField(
            context,
            _formData.currentCityController,
            'Current City',
            true,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Current State *',
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: _formData.currentState,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  hintText: 'State',
                ),
                items: FormOptions.usStates
                    .map(
                      (state) =>
                          DropdownMenuItem(value: state, child: Text(state)),
                    )
                    .toList(),
                onChanged: (value) =>
                    setState(() => _formData.currentState = value),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDegreesSection(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Degree(s) from NC State *',
              style: theme.textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            TextButton.icon(
              onPressed: _openDegreeDialog,
              icon: const Icon(Icons.add),
              label: const Text('Add degree'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (_formData.degrees.isEmpty)
          Text(
            'Add your degree level, program, and graduation year.',
            style: theme.textTheme.bodyMedium,
          )
        else
          Column(
            children: _formData.degrees
                .asMap()
                .entries
                .map(
                  (entry) => Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: ListTile(
                      title: Text(
                        '${entry.value.level} in ${entry.value.program}',
                      ),
                      subtitle: Text('Graduated ${entry.value.graduationYear}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit),
                            onPressed: () => _openDegreeDialog(
                              existing: entry.value,
                              index: entry.key,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline),
                            onPressed: () => setState(
                              () => _formData.degrees.removeAt(entry.key),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
      ],
    );
  }

  Future<void> _openDegreeDialog({DegreeEntry? existing, int? index}) async {
    String? selectedLevel = existing?.level;
    String? selectedProgram = existing?.program;
    String customProgram = '';
    if (existing != null &&
        (existing.level == 'Other' ||
            existing.program.toLowerCase().startsWith('other:'))) {
      selectedProgram = 'Other';
      customProgram = existing.program.replaceFirst(
        RegExp(r'^other:\s*', caseSensitive: false),
        '',
      );
    }
    String? selectedYear = existing?.graduationYear;

    DegreeEntry? result;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            final programOptions = selectedLevel == null
                ? <String>[]
                : List<String>.from(
                    FormOptions.getDegreeProgramsForLevels([selectedLevel!]),
                  );
            if (!programOptions.any(
              (program) => program.toLowerCase() == 'other',
            )) {
              programOptions.add('Other');
            }
            if (selectedProgram != null &&
                selectedProgram!.isNotEmpty &&
                !programOptions.contains(selectedProgram)) {
              selectedProgram = null;
            }

            return AlertDialog(
              title: Text(existing == null ? 'Add degree' : 'Edit degree'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: selectedLevel,
                    decoration: const InputDecoration(
                      labelText: 'Degree level',
                      border: OutlineInputBorder(),
                    ),
                    items: FormOptions.degreeLevels
                        .map(
                          (level) => DropdownMenuItem(
                            value: level,
                            child: Text(level),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => setStateDialog(() {
                      selectedLevel = value;
                      selectedProgram = null;
                    }),
                  ),
                  const SizedBox(height: 12),
                  if (selectedLevel == 'Other') ...[
                    const SizedBox(height: 12),
                    TextFormField(
                      initialValue: customProgram,
                      decoration: const InputDecoration(
                        labelText: 'Please type your degree program / major',
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (value) => customProgram = value,
                    ),
                  ] else ...[
                    DropdownButtonFormField<String>(
                      initialValue: selectedProgram,
                      decoration: const InputDecoration(
                        labelText: 'Degree program / major',
                        border: OutlineInputBorder(),
                      ),
                      items: programOptions
                          .map(
                            (program) => DropdownMenuItem(
                              value: program,
                              child: Text(program),
                            ),
                          )
                          .toList(),
                      onChanged: (value) => setStateDialog(() {
                        selectedProgram = value;
                        if (value != 'Other') {
                          customProgram = '';
                        }
                      }),
                    ),
                    if (selectedProgram == 'Other') ...[
                      const SizedBox(height: 12),
                      TextFormField(
                        initialValue: customProgram,
                        decoration: const InputDecoration(
                          labelText: 'Please type your degree program / major',
                          border: OutlineInputBorder(),
                        ),
                        onChanged: (value) => customProgram = value,
                      ),
                    ],
                  ],
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: selectedYear,
                    decoration: const InputDecoration(
                      labelText: 'Graduation year',
                      border: OutlineInputBorder(),
                    ),
                    items: FormOptions.getGraduationYears()
                        .map(
                          (year) =>
                              DropdownMenuItem(value: year, child: Text(year)),
                        )
                        .toList(),
                    onChanged: (value) => setStateDialog(() {
                      selectedYear = value;
                    }),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    final normalizedProgram =
                        (selectedProgram == 'Other' || selectedLevel == 'Other')
                        ? customProgram.trim()
                        : selectedProgram;
                    if (selectedLevel != null &&
                        normalizedProgram != null &&
                        normalizedProgram.isNotEmpty &&
                        selectedYear != null) {
                      result = DegreeEntry(
                        level: selectedLevel!,
                        program: normalizedProgram,
                        graduationYear: selectedYear!,
                      );
                      Navigator.pop(dialogContext);
                    }
                  },
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );

    if (result != null) {
      setState(() {
        if (index != null) {
          _formData.degrees[index] = result!;
        } else {
          _formData.degrees.add(result!);
        }
      });
    }
  }

  Future<List<String>> _resolveOtherSelection(
    List<String> rawSelection, {
    required String fieldLabel,
  }) async {
    final cleaned = List<String>.from(rawSelection);
    final hasExplicitOther = cleaned.any(
      (value) => value.trim().toLowerCase() == 'other',
    );
    if (!hasExplicitOther) {
      return cleaned;
    }

    cleaned.removeWhere((value) => value.trim().toLowerCase() == 'other');
    final customValue = await _promptForOtherValue(fieldLabel);
    if (customValue == null || customValue.isEmpty) {
      return cleaned;
    }
    cleaned.add('Other: $customValue');
    return cleaned;
  }

  Future<String?> _promptForOtherValue(String fieldLabel) async {
    final controller = TextEditingController();
    final value = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text('$fieldLabel - Other'),
          content: TextField(
            controller: controller,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: 'Please specify',
              border: OutlineInputBorder(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () =>
                  Navigator.pop(dialogContext, controller.text.trim()),
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
    controller.dispose();
    return value;
  }

  void _submitForm() async {
    final errors = _formData.validate();

    if (errors.isNotEmpty) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Form Incomplete'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Please complete the following:'),
              const SizedBox(height: 8),
              ...errors.map(
                (error) => Padding(
                  padding: const EdgeInsets.only(left: 8, top: 4),
                  child: Text('• $error'),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      return;
    }

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    final result = await ApiService.submitMentorApplication(_formData);

    if (mounted) Navigator.pop(context);

    if (result['success'] == true) {
      if (mounted) {
        showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Success'),
            content: const Text(
              'Your ECE mentor form has been submitted successfully.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    } else {
      if (mounted) {
        showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Submission Error'),
            content: Text(
              result['error']?.toString() ??
                  'Unable to submit right now. Please try again.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    }
  }

  @override
  void dispose() {
    _formData.dispose();
    super.dispose();
  }
}
