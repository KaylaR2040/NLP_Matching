import 'package:flutter/material.dart';

class MenteeFormData {

  // Personal info
  final TextEditingController emailController;
  final TextEditingController firstNameController;
  final TextEditingController lastNameController;
  String? pronouns;
  
  // Education + academic status
  String? educationLevel;
  String? graduationSemester;
  String? graduationYear;
  final List<String> degreePrograms;
  bool hasConcentration;
  final List<String> concentrations;
  final TextEditingController phdSpecializationController;
  
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

  MenteeFormData({
    TextEditingController? emailController,
    TextEditingController? firstNameController,
    TextEditingController? lastNameController,
    this.pronouns,
    this.educationLevel,
    this.graduationSemester,
    this.graduationYear,
    List<String>? degreePrograms,
    this.hasConcentration = false,
    List<String>? concentrations,
    TextEditingController? phdSpecializationController,
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
  })  : emailController = emailController ?? TextEditingController(),
        firstNameController = firstNameController ?? TextEditingController(),
        lastNameController = lastNameController ?? TextEditingController(),
        degreePrograms = degreePrograms ?? [],
        concentrations = concentrations ?? [],
        phdSpecializationController = phdSpecializationController ?? TextEditingController(),
        studentOrgs = studentOrgs ?? [],
        industriesOfInterest = industriesOfInterest ?? [],
        aboutYourselfController = aboutYourselfController ?? TextEditingController(),
        helpTopics = helpTopics ?? [];

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
    if (graduationSemester == null || graduationYear == null) {
      errors.add('Graduation date (semester and year) is required');
    }
    if (degreePrograms.isEmpty) {
      errors.add('At least one degree program is required');
    }
    if ((educationLevel == 'BS' || educationLevel == 'ABM') && hasConcentration && concentrations.isEmpty) {
      errors.add('Please select at least one concentration or turn off the concentration toggle');
    }
    if (educationLevel == 'PhD' && phdSpecializationController.text.trim().isEmpty) {
      errors.add('Please enter your PhD specialization');
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
    return errors;
  }


  Map<String, dynamic> toJson() {
    return {
      'email': emailController.text,
      'firstName': firstNameController.text,
      'lastName': lastNameController.text,
      'pronouns': pronouns,
      'educationLevel': educationLevel,
      'graduationSemester': graduationSemester,
      'graduationYear': graduationYear,
      'degreePrograms': degreePrograms,
      'hasConcentration': hasConcentration,
      'concentrations': concentrations,
      'phdSpecialization': phdSpecializationController.text.trim(),
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
    };
  }

  /// Dispose controllers
  void dispose() {
    emailController.dispose();
    firstNameController.dispose();
    lastNameController.dispose();
    aboutYourselfController.dispose();
    phdSpecializationController.dispose();
  }
}
