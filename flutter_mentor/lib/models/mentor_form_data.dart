import 'package:flutter/material.dart';

/// Structured representation of a single degree entry.
class DegreeEntry {
  final String level;
  final String program;
  final String graduationYear;

  DegreeEntry({
    required this.level,
    required this.program,
    required this.graduationYear,
  });

  Map<String, String> toJson() => {
    'level': level,
    'program': program,
    'graduationYear': graduationYear,
  };
}

class MentorFormData {
  final TextEditingController emailController;
  final TextEditingController firstNameController;
  final TextEditingController lastNameController;
  final TextEditingController linkedinController;
  final List<String> pronouns;

  final List<DegreeEntry> degrees;

  final TextEditingController currentCityController;
  String? currentState;
  final TextEditingController currentJobTitleController;
  final TextEditingController currentCompanyController;

  bool? previousMentorship;
  final TextEditingController previousInvolvementController;
  final List<String> industryFocusAreas;

  final List<String> previousInvolvementOrgs;

  final TextEditingController whyInterestedController;
  final TextEditingController professionalExperienceController;
  final TextEditingController aboutYourselfController;
  String? studentsInterested;

  MentorFormData({
    TextEditingController? emailController,
    TextEditingController? firstNameController,
    TextEditingController? lastNameController,
    TextEditingController? linkedinController,
    List<String>? pronouns,
    List<DegreeEntry>? degrees,
    TextEditingController? currentCityController,
    this.currentState,
    TextEditingController? currentJobTitleController,
    TextEditingController? currentCompanyController,
    this.previousMentorship,
    TextEditingController? previousInvolvementController,
    List<String>? industryFocusAreas,
    List<String>? previousInvolvementOrgs,
    TextEditingController? whyInterestedController,
    TextEditingController? professionalExperienceController,
    TextEditingController? aboutYourselfController,
    this.studentsInterested,
  }) : emailController = emailController ?? TextEditingController(),
       firstNameController = firstNameController ?? TextEditingController(),
       lastNameController = lastNameController ?? TextEditingController(),
       linkedinController = linkedinController ?? TextEditingController(),
       pronouns = pronouns ?? [],
       degrees = degrees ?? [],
       currentCityController = currentCityController ?? TextEditingController(),
       currentJobTitleController =
           currentJobTitleController ?? TextEditingController(),
       currentCompanyController =
           currentCompanyController ?? TextEditingController(),
       previousInvolvementController =
           previousInvolvementController ?? TextEditingController(),
       industryFocusAreas = industryFocusAreas ?? [],
       previousInvolvementOrgs = previousInvolvementOrgs ?? [],
       whyInterestedController =
           whyInterestedController ?? TextEditingController(),
       professionalExperienceController =
           professionalExperienceController ?? TextEditingController(),
       aboutYourselfController =
           aboutYourselfController ?? TextEditingController();

  List<String> validate() {
    final errors = <String>[];

    if (emailController.text.trim().isEmpty ||
        !emailController.text.contains('@')) {
      errors.add('Please enter a valid email');
    }
    if (pronouns.isEmpty) {
      errors.add('At least one pronoun selection is required');
    }
    if (linkedinController.text.trim().isEmpty) {
      errors.add('LinkedIn is required');
    }
    if (firstNameController.text.trim().isEmpty) {
      errors.add('First name is required');
    }
    if (lastNameController.text.trim().isEmpty) {
      errors.add('Last name is required');
    }
    if (degrees.isEmpty) {
      errors.add('Add at least one degree entry');
    }
    for (final degree in degrees) {
      if (degree.level.isEmpty ||
          degree.program.isEmpty ||
          degree.graduationYear.isEmpty) {
        errors.add('Each degree must include level, program, and grad year');
        break;
      }
    }
    if (currentCityController.text.trim().isEmpty) {
      errors.add('Current city is required');
    }
    if (currentState == null || currentState!.trim().isEmpty) {
      errors.add('Current state is required');
    }
    if (currentJobTitleController.text.trim().isEmpty) {
      errors.add('Current job title is required');
    }
    if (currentCompanyController.text.trim().isEmpty) {
      errors.add('Current employer/company is required');
    }
    if (previousMentorship == null) {
      errors.add('Please answer the previous mentorship question');
    }
    if (industryFocusAreas.isEmpty) {
      errors.add('Select at least one industry/focus area');
    }
    if (previousMentorship == true &&
        previousInvolvementController.text.trim().isEmpty) {
      errors.add('Previous involvement is required');
    }
    if (previousMentorship == true && previousInvolvementOrgs.isEmpty) {
      errors.add('Previous involvement organizations are required');
    }
    if (whyInterestedController.text.trim().isEmpty) {
      errors.add('Why you are interested is required');
    }
    if (professionalExperienceController.text.trim().isEmpty) {
      errors.add('Professional experience is required');
    }
    if (aboutYourselfController.text.trim().isEmpty) {
      errors.add('About yourself is required');
    }
    if (studentsInterested == null) {
      errors.add('Please select how many students you can mentor');
    }

    return errors;
  }

  Map<String, dynamic> toJson() {
    final hasPreviousInvolvement = previousMentorship == true;

    return {
      'email': emailController.text.trim(),
      'linkedin': linkedinController.text.trim(),
      'firstName': firstNameController.text.trim(),
      'lastName': lastNameController.text.trim(),
      'pronouns': pronouns,
      'degrees': degrees.map((d) => d.toJson()).toList(),
      'currentCity': currentCityController.text.trim(),
      'currentState': currentState,
      'currentCityState': [
        currentCityController.text.trim(),
        if (currentState != null && currentState!.trim().isNotEmpty)
          currentState!.trim(),
      ].join(', '),
      'currentJobTitle': currentJobTitleController.text.trim(),
      'currentCompany': currentCompanyController.text.trim(),
      'previousMentorship': previousMentorship,
      'industryFocusArea': industryFocusAreas,
      // Keep required Google Form fields populated even when mentorship is "No".
      'previousInvolvement': hasPreviousInvolvement
          ? previousInvolvementController.text.trim()
          : 'N/A',
      'previousInvolvementOrgs': hasPreviousInvolvement
          ? previousInvolvementOrgs
          : ['N/A'],
      'whyInterested': whyInterestedController.text.trim(),
      'professionalExperience': professionalExperienceController.text.trim(),
      'aboutYourself': aboutYourselfController.text.trim(),
      'studentsInterested': studentsInterested,
    };
  }

  void dispose() {
    emailController.dispose();
    firstNameController.dispose();
    lastNameController.dispose();
    linkedinController.dispose();
    currentCityController.dispose();
    currentJobTitleController.dispose();
    currentCompanyController.dispose();
    previousInvolvementController.dispose();
    whyInterestedController.dispose();
    professionalExperienceController.dispose();
    aboutYourselfController.dispose();
  }
}
