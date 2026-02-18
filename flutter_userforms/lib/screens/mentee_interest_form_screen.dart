import 'package:flutter/material.dart';
import '../constants/form_options.dart';
import '../models/mentee_form_data.dart';
import '../widgets/form_field_widgets.dart';

class MenteeInterestFormScreen extends StatefulWidget {
  const MenteeInterestFormScreen({super.key});

  @override
  State<MenteeInterestFormScreen> createState() =>
      _MenteeInterestFormScreenState();
}

class _MenteeInterestFormScreenState extends State<MenteeInterestFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final MenteeFormData _formData;

  @override
  void initState() {
    super.initState();
    _formData = MenteeFormData();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            children: [
              // Header
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(32),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      theme.colorScheme.primary,
                      theme.colorScheme.primary.withValues(alpha: 0.8),
                    ],
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Mentee Interest Form',
                      style: theme.textTheme.headlineLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Please fill out all required fields',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: Colors.white.withValues(alpha: 0.9),
                      ),
                    ),
                  ],
                ),
              ),
              
              // Form Content
              Container(
                constraints: const BoxConstraints(maxWidth: 800),
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Contact + Identity Section
                    FormFieldWidgets.buildSection(context, 'Contact + Identity'),
                    FormFieldWidgets.buildEmailField(context, _formData.emailController),
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
                      (value) => setState(() => _formData.pronouns = value),
                    ),
                    const SizedBox(height: 32),
                    
                    // Education + Academic Status Section
                    FormFieldWidgets.buildSection(context, 'Education + Academic Status'),
                    FormFieldWidgets.buildEducationLevelField(
                      context,
                      _formData.educationLevel,
                      (value) => setState(() {
                        _formData.educationLevel = value;
                        // Reset degree program if education level changes
                        if (value != null) _formData.degreeProgram = null;
                      }),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildGraduationDateField(
                      context,
                      _formData.graduationMonth,
                      _formData.graduationYear,
                      (value) => setState(() => _formData.graduationMonth = value),
                      (value) => setState(() => _formData.graduationYear = value),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildDegreeProgramField(
                      context,
                      _formData.educationLevel,
                      _formData.degreeProgram,
                      (value) => setState(() => _formData.degreeProgram = value),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiSelectChips(
                      context,
                      'Academic interests or focus areas *',
                      'Select all that apply',
                      FormOptions.academicInterests,
                      _formData.academicInterests,
                      (value) => setState(() {
                        _formData.academicInterests.clear();
                        _formData.academicInterests.addAll(value);
                      }),
                    ),
                    const SizedBox(height: 32),
                    
                    // Experience + Involvement Section
                    FormFieldWidgets.buildSection(context, 'Experience + Involvement'),
                    FormFieldWidgets.buildYesNoField(
                      context,
                      'Have you participated in a mentorship program before? *',
                      _formData.previousMentorship,
                      (value) => setState(() => _formData.previousMentorship = value),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildOrganizationsField(
                      context,
                      _formData.studentOrgs,
                      (value) => setState(() => _formData.studentOrgs = value),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildSingleSelectChips(
                      context,
                      'Current experience level *',
                      null,
                      FormOptions.experienceLevels,
                      _formData.experienceLevel,
                      (value) => setState(() => _formData.experienceLevel = value),
                    ),
                    const SizedBox(height: 32),
                    
                    // Career Interests Section
                    FormFieldWidgets.buildSection(context, 'Career Interests'),
                    FormFieldWidgets.buildMultiSelectChips(
                      context,
                      'Industries you are interested in pursuing *',
                      'Select all that apply',
                      FormOptions.industries,
                      _formData.industriesOfInterest,
                      (value) => setState(() {
                        _formData.industriesOfInterest.clear();
                        _formData.industriesOfInterest.addAll(value);
                      }),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiLineTextField(
                      context,
                      _formData.aboutYourselfController,
                      'Tell us about yourself, your interests, or anything you would like a mentor to know',
                    ),
                    const SizedBox(height: 32),
                    
                    // Matching Priorities Section
                    FormFieldWidgets.buildSection(context, 'Matching Priorities'),
                    FormFieldWidgets.buildMatchingPrioritiesInfo(context),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildLikertScale(
                      context,
                      'Matching by industry',
                      _formData.matchByIndustry,
                      (val) => setState(() => _formData.matchByIndustry = val),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildLikertScale(
                      context,
                      'Matching by degree or major',
                      _formData.matchByDegree,
                      (val) => setState(() => _formData.matchByDegree = val),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildLikertScale(
                      context,
                      'Matching by shared clubs or interests',
                      _formData.matchByClubs,
                      (val) => setState(() => _formData.matchByClubs = val),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildLikertScale(
                      context,
                      'Matching by shared identity or background',
                      _formData.matchByIdentity,
                      (val) => setState(() => _formData.matchByIdentity = val),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildLikertScale(
                      context,
                      'Matching with a mentor within 5 years of graduation',
                      _formData.matchByGradYears,
                      (val) => setState(() => _formData.matchByGradYears = val),
                    ),
                    const SizedBox(height: 32),
                    
                    // Mentoring Preferences Section
                    FormFieldWidgets.buildSection(context, 'Mentoring Preferences'),
                    FormFieldWidgets.buildMultiSelectChips(
                      context,
                      'Topics you would like help with *',
                      'Select all that apply',
                      FormOptions.helpTopics,
                      _formData.helpTopics,
                      (value) => setState(() {
                        _formData.helpTopics.clear();
                        _formData.helpTopics.addAll(value);
                      }),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildSingleSelectChips(
                      context,
                      'Preferred meeting frequency *',
                      'This is a one-semester mentorship program',
                      FormOptions.meetingFrequencies,
                      _formData.meetingFrequency,
                      (value) => setState(() => _formData.meetingFrequency = value),
                    ),
                    const SizedBox(height: 16),
                    FormFieldWidgets.buildMultiSelectChips(
                      context,
                      'Preferred communication methods *',
                      'Select all that apply',
                      FormOptions.communicationMethods,
                      _formData.communicationMethods,
                      (value) => setState(() {
                        _formData.communicationMethods.clear();
                        _formData.communicationMethods.addAll(value);
                      }),
                    ),
                    const SizedBox(height: 32),
                    
                    // Submit Button
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
                          'Submit Form',
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

  /// Submit form after validation
  void _submitForm() {
    // Validate all required fields using the model
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
              ...errors.map((error) => Padding(
                padding: const EdgeInsets.only(left: 8, top: 4),
                child: Text('• $error'),
              )),
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
    
    // Success dialog - in a real app, you would submit _formData.toJson() to a backend
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Success!'),
        content: const Text('Your mentee interest form has been submitted successfully.'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.pop(context);
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _formData.dispose();
    super.dispose();
  }
}
