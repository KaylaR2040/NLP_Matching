import unittest
from unittest.mock import patch

from backend.api.services.google_forms import (
    GoogleFormConfig,
    GoogleFormResult,
    _build_payload,
    submit_google_form,
)


class _FakeResponse:
    def __init__(self, status_code: int = 200):
        self._status_code = status_code

    def getcode(self):
        return self._status_code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class GoogleFormsTests(unittest.TestCase):
    def test_build_payload_uses_field_mapping(self):
        config = GoogleFormConfig(
            form_name="mentee",
            response_url="https://example.com/formResponse",
            field_map={
                "firstName": "entry.111",
                "studentOrgs": "entry.222",
                "previousMentorship": "entry.333",
            },
            enabled=True,
            required=True,
        )

        payload = _build_payload(
            config,
            {
                "firstName": "Kayla",
                "studentOrgs": ["IEEE", "SWE"],
                "previousMentorship": True,
            },
        )

        self.assertEqual(payload["entry.111"], "Kayla")
        self.assertEqual(payload["entry.222"], "IEEE, SWE")
        self.assertEqual(payload["entry.333"], "YES")

    def test_build_payload_supports_field_mapping_for_future_forms(self):
        config = GoogleFormConfig(
            form_name="mentor",
            response_url="https://example.com/formResponse",
            field_map={
                "firstName": "entry.111",
                "profile.email": "entry.222",
                "topics": "entry.333",
                "previousMentorship": "entry.444",
            },
            enabled=True,
        )

        payload = _build_payload(
            config,
            {
                "firstName": "Kayla",
                "profile": {"email": "kayla@example.com"},
                "topics": ["NLP", "Embedded Systems"],
                "previousMentorship": False,
            },
        )

        self.assertEqual(payload["entry.111"], "Kayla")
        self.assertEqual(payload["entry.222"], "kayla@example.com")
        self.assertEqual(payload["entry.333"], "NLP, Embedded Systems")
        self.assertEqual(payload["entry.444"], "NO")

    @patch("backend.api.services.google_forms.request.urlopen")
    @patch("backend.api.services.google_forms.get_google_form_config")
    def test_submit_google_form_posts_to_google_form(
        self,
        mock_get_config,
        mock_urlopen,
    ):
        mock_get_config.return_value = GoogleFormConfig(
            form_name="mentee",
            response_url="https://example.com/formResponse",
            field_map={"firstName": "entry.1048570048"},
            enabled=True,
            required=True,
        )
        mock_urlopen.return_value = _FakeResponse(200)

        result = submit_google_form(
            "mentee",
            {"firstName": "Kayla", "lastName": "Radu"},
        )

        self.assertEqual(
            result,
            GoogleFormResult(
                forwarded=True,
                skipped=False,
                status_code=200,
                reason="Submitted to Google Form",
            ),
        )

        submitted_request = mock_urlopen.call_args[0][0]
        self.assertEqual(submitted_request.full_url, "https://example.com/formResponse")
        self.assertIn(
            "entry.1048570048=",
            submitted_request.data.decode("utf-8"),
        )

    @patch("backend.api.services.google_forms.get_google_form_config")
    def test_submit_google_form_skips_when_form_is_not_configured(
        self,
        mock_get_config,
    ):
        mock_get_config.return_value = GoogleFormConfig(form_name="mentor")

        result = submit_google_form("mentor", {"firstName": "Kayla"})

        self.assertFalse(result.forwarded)
        self.assertTrue(result.skipped)


if __name__ == "__main__":
    unittest.main()
