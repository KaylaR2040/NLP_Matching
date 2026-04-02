import unittest

from backend.api.routes.matching_filters import (
    dedupe_mentees_by_email,
    filter_opted_out_mentors,
)


class MatchingFiltersTest(unittest.TestCase):
    def test_dedupe_mentees_by_email_keeps_first_submission(self):
        mentee_records = [
            {
                "id": "first",
                "email": "student@ncsu.edu",
                "submitted_at": "2026-01-10T10:00:00",
            },
            {
                "id": "second",
                "email": "student@ncsu.edu",
                "submitted_at": "2026-01-11T10:00:00",
            },
            {
                "id": "third",
                "email": "other@ncsu.edu",
                "submitted_at": "2026-01-12T10:00:00",
            },
        ]

        filtered, duplicate_emails, removed_duplicates = dedupe_mentees_by_email(
            mentee_records
        )

        self.assertEqual([record["id"] for record in filtered], ["first", "third"])
        self.assertEqual(duplicate_emails, 1)
        self.assertEqual(removed_duplicates, 1)

    def test_filter_opted_out_mentors_removes_false_values(self):
        mentor_records = [
            {"id": "active-default"},
            {"id": "active-explicit", "participatingThisSemester": True},
            {"id": "inactive-bool", "participatingThisSemester": False},
            {"id": "inactive-string", "participatingThisSemester": "No"},
        ]

        filtered, removed_count = filter_opted_out_mentors(mentor_records)

        self.assertEqual(
            [record["id"] for record in filtered],
            ["active-default", "active-explicit"],
        )
        self.assertEqual(removed_count, 2)


if __name__ == "__main__":
    unittest.main()
