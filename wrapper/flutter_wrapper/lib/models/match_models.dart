class PairKey {
  final String menteeId;
  final String mentorId;

  const PairKey({required this.menteeId, required this.mentorId});

  @override
  bool operator ==(Object other) =>
      other is PairKey &&
      other.menteeId == menteeId &&
      other.mentorId == mentorId;

  @override
  int get hashCode => Object.hash(menteeId, mentorId);

  Map<String, dynamic> toJson() => {
        'mentee_id': menteeId,
        'mentor_id': mentorId,
      };
}

class MenteeRecord {
  final String id;
  final String name;

  const MenteeRecord({required this.id, required this.name});
}

class MentorCardState {
  final String mentorId;
  final String mentorName;
  final List<String> menteeIds;
  int maxMentees;

  MentorCardState({
    required this.mentorId,
    required this.mentorName,
    this.maxMentees = 1,
    List<String>? menteeIds,
  }) : menteeIds = menteeIds ?? [];
}
