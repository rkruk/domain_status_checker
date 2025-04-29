import unittest
from error_checker import is_valid_domain, categorize_response, load_hosting_patterns

class TestErrorChecker(unittest.TestCase):
    def test_is_valid_domain(self):
        self.assertTrue(is_valid_domain("example.com"))
        self.assertTrue(is_valid_domain("sub.example.com"))
        self.assertFalse(is_valid_domain("http://example.com"))
        self.assertFalse(is_valid_domain("invalid_domain"))

    def test_categorize_response(self):
        patterns = load_hosting_patterns()
        self.assertEqual(categorize_response("jest utrzymywana na serwerach IQ PL", patterns), "iq_error")
        self.assertEqual(categorize_response("This domain is parked", patterns), "godaddy_error")
        self.assertEqual(categorize_response("404 Not Found", patterns), "custom_404")
        self.assertEqual(categorize_response("Some random text", patterns), "custom")

if __name__ == "__main__":
    unittest.main()
