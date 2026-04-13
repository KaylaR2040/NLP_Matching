class MentorRecord {
  final String mentorId;
  final String email;
  final String firstName;
  final String lastName;
  final String fullName;
  final String linkedInUrl;
  final String profilePhotoUrl;
  final String currentCompany;
  final String currentJobTitle;
  final String currentLocation;
  final String currentCity;
  final String currentState;
  final String degreesText;
  final String industryFocusArea;
  final String professionalExperience;
  final String aboutYourself;
  final int studentsInterested;
  final String phone;
  final String preferredContactMethod;
  final bool isActive;
  final String sourceCsvPath;
  final String sourceTimestamp;
  final String lastModifiedAt;
  final String lastModifiedBy;
  final String lastEnrichedAt;
  final String enrichmentStatus;
  final Map<String, dynamic> extraFields;

  const MentorRecord({
    required this.mentorId,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.fullName,
    required this.linkedInUrl,
    required this.profilePhotoUrl,
    required this.currentCompany,
    required this.currentJobTitle,
    required this.currentLocation,
    required this.currentCity,
    required this.currentState,
    required this.degreesText,
    required this.industryFocusArea,
    required this.professionalExperience,
    required this.aboutYourself,
    required this.studentsInterested,
    required this.phone,
    required this.preferredContactMethod,
    required this.isActive,
    required this.sourceCsvPath,
    required this.sourceTimestamp,
    required this.lastModifiedAt,
    required this.lastModifiedBy,
    required this.lastEnrichedAt,
    required this.enrichmentStatus,
    required this.extraFields,
  });

  factory MentorRecord.fromJson(Map<String, dynamic> json) {
    final extras = (json['extra_fields'] as Map<String, dynamic>? ?? const {});
    final firstName = (json['first_name'] ?? '').toString();
    final lastName = (json['last_name'] ?? '').toString();
    final email = (json['email'] ?? '').toString();
    final computedName = [firstName, lastName]
        .where((value) => value.trim().isNotEmpty)
        .join(' ')
        .trim();
    final linkedInUrl = _extractLinkedInUrl(json, extras);

    return MentorRecord(
      mentorId: (json['mentor_id'] ?? '').toString(),
      email: email,
      firstName: firstName,
      lastName: lastName,
      fullName: (json['full_name'] ?? '').toString().isNotEmpty
          ? (json['full_name'] ?? '').toString()
          : (computedName.isNotEmpty ? computedName : email),
      linkedInUrl: linkedInUrl,
      profilePhotoUrl: (json['profile_photo_url'] ?? '').toString(),
      currentCompany: (json['current_company'] ?? '').toString(),
      currentJobTitle: (json['current_job_title'] ?? '').toString(),
      currentLocation: (json['current_location'] ?? '').toString(),
      currentCity: (json['current_city'] ?? '').toString(),
      currentState: (json['current_state'] ?? '').toString(),
      degreesText: (json['degrees_text'] ?? '').toString(),
      industryFocusArea: (json['industry_focus_area'] ?? '').toString(),
      professionalExperience:
          (json['professional_experience'] ?? '').toString(),
      aboutYourself: (json['about_yourself'] ?? '').toString(),
      studentsInterested:
          int.tryParse('${json['students_interested'] ?? 0}') ?? 0,
      phone: (json['phone'] ?? '').toString(),
      preferredContactMethod:
          (json['preferred_contact_method'] ?? '').toString(),
      isActive: json['is_active'] != false,
      sourceCsvPath: (json['source_csv_path'] ?? '').toString(),
      sourceTimestamp: (json['source_timestamp'] ?? '').toString(),
      lastModifiedAt: (json['last_modified_at'] ?? '').toString(),
      lastModifiedBy: (json['last_modified_by'] ?? '').toString(),
      lastEnrichedAt: (json['last_enriched_at'] ?? '').toString(),
      enrichmentStatus: (json['enrichment_status'] ?? '').toString(),
      extraFields: extras,
    );
  }

  Map<String, dynamic> toUpdatePayload() {
    return {
      'email': email,
      'first_name': firstName,
      'last_name': lastName,
      'full_name': fullName,
      'linkedin_url': linkedInUrl,
      'profile_photo_url': profilePhotoUrl,
      'current_company': currentCompany,
      'current_job_title': currentJobTitle,
      'current_location': currentLocation,
      'current_city': currentCity,
      'current_state': currentState,
      'degrees_text': degreesText,
      'industry_focus_area': industryFocusArea,
      'professional_experience': professionalExperience,
      'about_yourself': aboutYourself,
      'students_interested': studentsInterested,
      'phone': phone,
      'preferred_contact_method': preferredContactMethod,
      'is_active': isActive,
      'source_csv_path': sourceCsvPath,
      'source_timestamp': sourceTimestamp,
      'last_enriched_at': lastEnrichedAt,
      'enrichment_status': enrichmentStatus,
      'extra_fields': extraFields,
    };
  }

  MentorRecord copyWith({
    String? mentorId,
    String? email,
    String? firstName,
    String? lastName,
    String? fullName,
    String? linkedInUrl,
    String? profilePhotoUrl,
    String? currentCompany,
    String? currentJobTitle,
    String? currentLocation,
    String? currentCity,
    String? currentState,
    String? degreesText,
    String? industryFocusArea,
    String? professionalExperience,
    String? aboutYourself,
    int? studentsInterested,
    String? phone,
    String? preferredContactMethod,
    bool? isActive,
    String? sourceCsvPath,
    String? sourceTimestamp,
    String? lastModifiedAt,
    String? lastModifiedBy,
    String? lastEnrichedAt,
    String? enrichmentStatus,
    Map<String, dynamic>? extraFields,
  }) {
    return MentorRecord(
      mentorId: mentorId ?? this.mentorId,
      email: email ?? this.email,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      fullName: fullName ?? this.fullName,
      linkedInUrl: linkedInUrl ?? this.linkedInUrl,
      profilePhotoUrl: profilePhotoUrl ?? this.profilePhotoUrl,
      currentCompany: currentCompany ?? this.currentCompany,
      currentJobTitle: currentJobTitle ?? this.currentJobTitle,
      currentLocation: currentLocation ?? this.currentLocation,
      currentCity: currentCity ?? this.currentCity,
      currentState: currentState ?? this.currentState,
      degreesText: degreesText ?? this.degreesText,
      industryFocusArea: industryFocusArea ?? this.industryFocusArea,
      professionalExperience:
          professionalExperience ?? this.professionalExperience,
      aboutYourself: aboutYourself ?? this.aboutYourself,
      studentsInterested: studentsInterested ?? this.studentsInterested,
      phone: phone ?? this.phone,
      preferredContactMethod:
          preferredContactMethod ?? this.preferredContactMethod,
      isActive: isActive ?? this.isActive,
      sourceCsvPath: sourceCsvPath ?? this.sourceCsvPath,
      sourceTimestamp: sourceTimestamp ?? this.sourceTimestamp,
      lastModifiedAt: lastModifiedAt ?? this.lastModifiedAt,
      lastModifiedBy: lastModifiedBy ?? this.lastModifiedBy,
      lastEnrichedAt: lastEnrichedAt ?? this.lastEnrichedAt,
      enrichmentStatus: enrichmentStatus ?? this.enrichmentStatus,
      extraFields: extraFields ?? this.extraFields,
    );
  }
}

String _extractLinkedInUrl(
  Map<String, dynamic> json,
  Map<String, dynamic> extraFields,
) {
  final directCandidates = [
    json['linkedin_url'],
    json['linkedin'],
    json['linkedinUrl'],
    json['profile_link'],
    json['profile_url'],
  ];
  for (final candidate in directCandidates) {
    final value = (candidate ?? '').toString().trim();
    if (value.isNotEmpty) {
      return value;
    }
  }

  for (final entry in extraFields.entries) {
    final key = _normalizeHeader(entry.key);
    if (key == 'linkedin' ||
        key == 'linkedin url' ||
        key == 'linkedin_url' ||
        key == 'linkedin profile' ||
        key == 'linkedin profile url' ||
        key == 'profile link' ||
        key == 'profile url') {
      final value = (entry.value ?? '').toString().trim();
      if (value.isNotEmpty) {
        return value;
      }
    }
  }
  return '';
}

String _normalizeHeader(String value) {
  return value
      .trim()
      .toLowerCase()
      .replaceAll('_', ' ')
      .replaceAll(RegExp(r'\s+'), ' ');
}

class MentorsListResult {
  final List<MentorRecord> items;
  final int total;

  const MentorsListResult({
    required this.items,
    required this.total,
  });

  factory MentorsListResult.fromJson(Map<String, dynamic> json) {
    final rawItems = (json['items'] as List? ?? const []);
    final items = rawItems
        .whereType<Map<String, dynamic>>()
        .map(MentorRecord.fromJson)
        .toList();
    return MentorsListResult(
      items: items,
      total: int.tryParse('${json['total'] ?? items.length}') ?? items.length,
    );
  }
}

class MentorImportReport {
  final int rowsRead;
  final int added;
  final int reactivated;
  final int skippedDuplicates;
  final int invalid;
  final int errors;
  final List<Map<String, dynamic>> reactivatedRows;
  final List<Map<String, dynamic>> duplicateRows;
  final List<Map<String, dynamic>> invalidRows;
  final List<Map<String, dynamic>> errorRows;

  const MentorImportReport({
    required this.rowsRead,
    required this.added,
    required this.reactivated,
    required this.skippedDuplicates,
    required this.invalid,
    required this.errors,
    required this.reactivatedRows,
    required this.duplicateRows,
    required this.invalidRows,
    required this.errorRows,
  });

  factory MentorImportReport.fromJson(Map<String, dynamic> json) {
    final rawErrors = (json['error_rows'] as List? ?? const []);
    final rawDuplicates = (json['duplicate_rows'] as List? ?? const []);
    final rawInvalid = (json['invalid_rows'] as List? ?? const []);
    final rawReactivated = (json['reactivated_rows'] as List? ?? const []);
    return MentorImportReport(
      rowsRead: int.tryParse('${json['rows_read'] ?? 0}') ?? 0,
      added: int.tryParse('${json['added'] ?? 0}') ?? 0,
      reactivated: int.tryParse('${json['reactivated'] ?? 0}') ?? 0,
      skippedDuplicates:
          int.tryParse('${json['skipped_duplicates'] ?? 0}') ?? 0,
      invalid: int.tryParse('${json['invalid'] ?? 0}') ?? 0,
      errors: int.tryParse('${json['errors'] ?? 0}') ?? 0,
      reactivatedRows: rawReactivated
          .whereType<Map<String, dynamic>>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList(),
      duplicateRows: rawDuplicates
          .whereType<Map<String, dynamic>>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList(),
      invalidRows: rawInvalid
          .whereType<Map<String, dynamic>>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList(),
      errorRows: rawErrors
          .whereType<Map<String, dynamic>>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList(),
    );
  }
}
