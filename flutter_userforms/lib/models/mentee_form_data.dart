import 'package:flutter/material.dart';

/// Model class to hold all mentee form data
class MenteeFormData {
  // Contact + Identity
  final TextEditingController emailController;
  final TextEditingController firstNameController;
  final TextEditingController lastNameController;
  String? pronouns;
  
  // Education + Academic Status
  String? educationLevel;
  String? graduationMonth;
  String? graduationYear;
  String? degreeProgram;
  final List<String> academicInterests;
  
  // Experience + Involvement
  bool? previousMentorship;
  List<String> studentOrgs;
  String? experienceLevel;
  
  // Career Interests
  final List<String> industriesOfInterest;
  final TextEditingController aboutYourselfController;
  
  // Matching Priorities (1-4 scale)
  double matchByIndustry;
  double matchByDegree;
  double matchByClubs;
  double matchByIdentity;
  double matchByGradYears;
  
  // Mentoring Preferences
  final List<String> helpTopics;
  String? meetingFrequency;
  final List<String> communicationMethods;

  MenteeFormData({
    TextEditingController? emailController,
    TextEditingController? firstNameController,
    TextEditingController? lastNameController,
    this.pronouns,
    this.educationLevel,
    this.graduationMonth,
    this.graduationYear,
    this.degreeProgram,
    List<String>? academicInterests,
    this.previousMentorship,
    List<String>? studentOrgs,
    this.experienceLevel,
    List<String>? industriesOfInterest,
    TextEditingController? aboutYourselfController,
    this.matchByIndustry = 2,
    this.matchByDegree = 2,
    this.matchByClubs = 2,
    this.matchByIdentity = 2,
    this.matchByGradYears = 2,
    List<String>? helpTopics,
    this.meetingFrequency,
    List<String>? communicationMethods,
  })  : emailController = emailController ?? TextEditingController(),
        firstNameController = firstNameController ?? TextEditingController(),
        lastNameController = lastNameController ?? TextEditingController(),
        academicInterests = academicInterests ?? [],
        studentOrgs = studentOrgs ?? [],
        industriesOfInterest = industriesOfInterest ?? [],
        aboutYourselfController = aboutYourselfController ?? TextEditingController(),
        helpTopics = helpTopics ?? [],
        communicationMethods = communicationMethods ?? [];

  /// Validate all required fields and return list of errors
  List<String> validate() {
    final errors = <String>[];
    
    if (emailController.text.isEmpty || !emailController.text.endsWith('@ncsu.edu')) {
      errors.add('Please provide a valid NCSU email');
    }
    if (firstNameController.text.isEmpty) {
      errors.add('First name is required');
    }
    if (lastNameController.text.isEmpty) {
      errors.add('Last name is required');
    }
    if (pronouns == null) {
      errors.add('Pronouns selection is required');
    }
    if (educationLevel == null) {
      errors.add('Education level is required');
    }
    if (graduationMonth == null || graduationYear == null) {
      errors.add('Graduation date (month and year) is required');
    }
    if (degreeProgram == null) {
      errors.add('Degree program is required');
    }
    if (academicInterests.isEmpty) {
      errors.add('At least one academic interest is required');
    }
    if (previousMentorship == null) {
      errors.add('Previous mentorship question is required');
    }
    if (experienceLevel == null) {
      errors.add('Experience level is required');
    }
    if (industriesOfInterest.isEmpty) {
      errors.add('At least one industry is required');
    }
    if (helpTopics.isEmpty) {
      errors.add('At least one help topic is required');
    }
    if (meetingFrequency == null) {
      errors.add('Meeting frequency is required');
    }
    if (communicationMethods.isEmpty) {
      errors.add('At least one communication method is required');
    }
    
    return errors;
  }

  /// Convert form data to JSON for submission
  Map<String, dynamic> toJson() {
    return {
      'email': emailController.text,
      'firstName': firstNameController.text,
      'lastName': lastNameController.text,
      'pronouns': pronouns,
      'educationLevel': educationLevel,
      'graduationMonth': graduationMonth,
      'graduationYear': graduationYear,
      'degreeProgram': degreeProgram,
      'academicInterests': academicInterests,
      'previousMentorship': previousMentorship,
      'studentOrgs': studentOrgs,
      'experienceLevel': experienceLevel,
      'industriesOfInterest': industriesOfInterest,
      'aboutYourself': aboutYourselfController.text,
      'matchByIndustry': matchByIndustry,
      'matchByDegree': matchByDegree,
      'matchByClubs': matchByClubs,
      'matchByIdentity': matchByIdentity,
      'matchByGradYears': matchByGradYears,
      'helpTopics': helpTopics,
      'meetingFrequency': meetingFrequency,
      'communicationMethods': communicationMethods,
    };
  }

  /// Dispose controllers
  void dispose() {
    emailController.dispose();
    firstNameController.dispose();
    lastNameController.dispose();
    aboutYourselfController.dispose();
  }
}
