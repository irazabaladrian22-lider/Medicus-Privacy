import unittest

from medicus_privacy.modules import seguridad


class SeguridadTests(unittest.TestCase):
    def test_hash_password(self):
        password_hash = seguridad.hash_password("ClaveSegura123")
        self.assertTrue(
            seguridad.verificar_password("ClaveSegura123", password_hash)
        )
        self.assertFalse(
            seguridad.verificar_password("incorrecta", password_hash)
        )
        self.assertNotIn("ClaveSegura123", password_hash)

    def test_aes_gcm_round_trip_and_integrity(self):
        encrypted = seguridad.cifrar_datos(
            "Diagnostico confidencial",
            "ClaveMedica123",
        )
        self.assertTrue(encrypted.startswith("aesgcm$v1$"))
        self.assertEqual(
            seguridad.descifrar_datos(encrypted, "ClaveMedica123"),
            "Diagnostico confidencial",
        )
        with self.assertRaises(ValueError):
            seguridad.descifrar_datos(encrypted, "clave incorrecta")

        tampered = encrypted[:-1] + ("A" if encrypted[-1] != "A" else "B")
        with self.assertRaises(ValueError):
            seguridad.descifrar_datos(tampered, "ClaveMedica123")

    def test_empty_values_and_generated_key(self):
        self.assertEqual(seguridad.cifrar_datos("", "clave"), "")
        self.assertEqual(seguridad.descifrar_datos("", "clave"), "")
        self.assertEqual(len(seguridad.generar_clave()), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
