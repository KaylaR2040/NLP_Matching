class OrganizationRecord {
  const OrganizationRecord({required this.name, required this.link});

  final String name;
  final String link;

  factory OrganizationRecord.fromMap(Map<String, dynamic> json) {
    final name = json['primaryText']?.toString().trim() ?? '';
    final link = json['link']?.toString().trim() ?? '';
    return OrganizationRecord(name: name, link: link);
  }

  bool get isValid => name.isNotEmpty;
}
