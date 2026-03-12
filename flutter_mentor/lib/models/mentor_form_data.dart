import 'package:flutter/material.dart';

class MentorFormData {
  final TextEditingController emailController;
  final TextEditingController firstNameController;
  final TextEditingController lastNameController;
  final TextEditingController joinDateController;

  String? graduationYear;
  final List<String> degreeLevels;
  final List<String> degreePrograms;
  final TextEditingController otherDegreeController;
  final TextEditingController otherEducationController;

  final TextEditingController currentCityStateController;
  final TextEditingController currentJobTitleController;
  final TextEditingController currentCompanyController;

  bool? previousMentorship;
  final TextEditingController previousInvolvementController;
  final List<String> industryFocusAreas;

  final List<String> previousInvolvementOrgs;
  final List<String> availableTerms;

  final TextEditingController whyInterestedController;
  final TextEditingController professionalExperienceController;
  final TextEditingController aboutYourselfController;
  String? studentsInterested;

  MentorFormData({
    TextEditingController? emailController,
    TextEditingController? firstNameController,
    TextEditingController? lastNameController,
    TextEditingController? joinDateController,
    this.graduationYear,
    List<String>? degreeLevels,
    List<String>? degreePrograms,
    TextEditingController? otherDegreeController,
    TextEditingController? otherEducationController,
    TextEditingController? currentCityStateController,
    TextEditingController? currentJobTitleController,
    TextEditingController? currentCompanyController,
    this.previousMentorship,
    TextEditingController? previousInvolvementController,
    List<String>? industryFocusAreas,
    List<String>? previousInvolvementOrgs,
    List<String>? availableTerms,
    TextEditingController? whyInterestedController,
    TextEditingController? professionalExperienceController,
    TextEditingController? aboutYourselfController,
    this.studentsInterested,
  })  : emailController = emailController ?? TextEditingController(),
        firstNameController = firstNameController ?? TextEditingController(),
        lastNameController = lastNameController ?? TextEditingController(),
        joinDateController =
            joinDateController ?? TextEditingController(text: _todayDate()),
        degreeLevels = degreeLevels ?? [],
        degreePrograms = degreePrograms ?? [],
        otherDegreeController = otherDegreeController ?? TextEditingController(),
        otherEducationController =
            otherEducationController ?? TextEditingController(),
        currentCityStateController =
            currentCityStateController ?? TextEditingController(),
        currentJobTitleController =
            currentJobTitleController ?? TextEditingController(),
        currentCompanyController =
            currentCompanyController ?? TextEditingController(),
        previousInvolvementController =
            previousInvolvementController ?? TextEditingController(),
        industryFocusAreas = industryFocusAreas ?? [],
        previousInvolvementOrgs = previousInvolvementOrgs ?? [],
        availableTerms = availableTerms ?? [],
        whyInterestedController =
            whyInterestedController ?? TextEditingController(),
        professionalExperienceController =
            professionalExperienceController ?? TextEditingController(),
        aboutYourselfController =
            aboutYourselfController ?? TextEditingController();

  static String _todayDate() {
    final now = DateTime.now();
    final month = now.month.toString().padLeft(2, '0');
    final day = now.day.toString().padLeft(2, '0');
    return '${now.year}-$month-$day';
  }

  List<String> validate() {
    final errors = <String>[];

    if (emailController.text.trim().isEmpty ||
        !emailController.text.contains('@')) {
      errors.add('Please enter a valid email');
    }
    if (firstNameController.text.trim().isEmpty) {
      errors.add('First name is required');
    }
    if (lastNameController.text.trim().isEmpty) {
      errors.add('Last name is required');
    }
    if (graduationYear == null) {
      errors.add('Graduation year is required');
    }
    if (degreeLevels.isEmpty) {
      errors.add('Select at least one degree level');
    }
    if (degreePrograms.isEmpty && otherDegreeController.text.trim().isEmpty) {
      errors.add('Select at least one major/degree program or enter Other');
    }
    if (currentCityStateController.text.trim().isEmpty) {
      errors.add('Current city/state is required');
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
    final termMap = {
      'f25': availableTerms.contains('F25'),
      'sp25': availableTerms.contains('Sp25'),
      'f26': availableTerms.contains('F26'),
      'sp26': availableTerms.contains('Sp26'),
    };

    return {
      'email': emailController.text.trim(),
      'joinDate': joinDateController.text.trim(),
      'firstName': firstNameController.text.trim(),
      'lastName': lastNameController.text.trim(),
      'graduationYear': graduationYear,
      'degreeLevels': degreeLevels,
      'degreePrograms': degreePrograms,
      'otherDegree': otherDegreeController.text.trim(),
      'otherEducation': otherEducationController.text.trim(),
      'currentCityState': currentCityStateController.text.trim(),
      'currentJobTitle': currentJobTitleController.text.trim(),
      'currentCompany': currentCompanyController.text.trim(),
      'previousMentorship': previousMentorship,
      'industryFocusArea': industryFocusAreas,
      'previousInvolvement': previousInvolvementController.text.trim(),
      'previousInvolvementOrgs': previousInvolvementOrgs,
      'availabilityTerms': availableTerms,
      'whyInterested': whyInterestedController.text.trim(),
      'professionalExperience': professionalExperienceController.text.trim(),
      'aboutYourself': aboutYourselfController.text.trim(),
      'studentsInterested': studentsInterested,
      ...termMap,
    };
  }

  void dispose() {
    emailController.dispose();
    firstNameController.dispose();
    lastNameController.dispose();
    joinDateController.dispose();
    otherDegreeController.dispose();
    otherEducationController.dispose();
    currentCityStateController.dispose();
    currentJobTitleController.dispose();
    currentCompanyController.dispose();
    previousInvolvementController.dispose();
    whyInterestedController.dispose();
    professionalExperienceController.dispose();
    aboutYourselfController.dispose();
  }
}
