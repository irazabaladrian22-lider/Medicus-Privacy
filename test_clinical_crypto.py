import unittest

from medicus_privacy.modules.clinical_crypto import (
    decrypt_clinical_text,
    encrypt_clinical_text,
)


class ClinicalCryptoTests(unittest.TestCase):
    def test_context_round_trip_and_tamper_detection(self):
        key = b"c" * 32
        context = "patient:1|appointment:2|field:diagnostico"
        token = encrypt_clinical_text("Dato reservado", key, context)
        self.assertNotIn("Dato reservado", token)
        self.assertEqual(
            decrypt_clinical_text(token, key, context),
            "Dato reservado",
        )
        with self.assertRaises(ValueError):
            decrypt_clinical_text(token, key, context + "-alterado")
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(ValueError):
            decrypt_clinical_text(tampered, key, context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
