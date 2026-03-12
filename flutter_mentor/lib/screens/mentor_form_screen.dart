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
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
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
                    FormFieldWidgets.buildSection(context, 'Required Mentor Information'),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildEmailField(context, _formData.emailController),
                    const SizedBox(height: 6),
                    Text(
                      'This form collects emails.',
                      style: theme.textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.joinDateController,
                      'Join Date (YYYY-MM-DD)',
                      true,
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
                    _buildGraduationYearField(context),
                    const SizedBox(height: 16),
                    _buildDegreeLevelsField(context),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildDegreeProgramField(
                      context,
                      _formData.degreeLevels,
                      _formData.degreePrograms,
                      (value) => setState(() {
                        _formData.degreePrograms
                          ..clear()
                          ..addAll(value);
                      }),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.otherDegreeController,
                      'Other Degree/Major (if not listed)',
                      false,
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.otherEducationController,
                      'Other Education',
                      false,
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildTextField(
                      context,
                      _formData.currentCityStateController,
                      'Current City and State',
                      true,
                    ),
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

                    FormFieldWidgets.buildSection(context, 'Mentoring and Experience'),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildYesNoField(
                      context,
                      'Do you have previous mentoring experience, or were you once a mentee? *',
                      _formData.previousMentorship,
                      (value) => setState(() => _formData.previousMentorship = value),
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
                      (value) => setState(() {
                        _formData.industryFocusAreas
                          ..clear()
                          ..addAll(value);
                      }),
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
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiSelectChips(
                      context,
                      'Term availability (select all terms you can mentor)',
                      null,
                      FormOptions.termOptions,
                      _formData.availableTerms,
                      (value) => setState(() {
                        _formData.availableTerms
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
                      (value) => setState(() => _formData.studentsInterested = value),
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

  Widget _buildGraduationYearField(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Graduation Year *',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          value: _formData.graduationYear,
          decoration: const InputDecoration(border: OutlineInputBorder()),
          items: FormOptions.getGraduationYears()
              .map((year) => DropdownMenuItem(value: year, child: Text(year)))
              .toList(),
          onChanged: (value) => setState(() => _formData.graduationYear = value),
        ),
      ],
    );
  }

  Widget _buildDegreeLevelsField(BuildContext context) {
    return FormFieldWidgets.buildMultiSelectChips(
      context,
      'Degree level(s) from NC State *',
      'Select all that apply',
      FormOptions.degreeLevels,
      _formData.degreeLevels,
      (value) => setState(() {
        _formData.degreeLevels
          ..clear()
          ..addAll(value);
        final allowedPrograms =
            FormOptions.getDegreeProgramsForLevels(_formData.degreeLevels);
        _formData.degreePrograms
            .removeWhere((program) => !allowedPrograms.contains(program));
      }),
    );
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
