import unittest
from types import SimpleNamespace
from unittest.mock import patch

from campuseats.routes import role_guards
from werkzeug.exceptions import Forbidden


class RoleGuardsTestCase(unittest.TestCase):
    def test_vendor_can_access_vendor_route(self):
        # Create a simulated authenticated vendor
        vendor = SimpleNamespace(is_authenticated=True, role="vendor")

        # Simulate the current logged-in user
        with patch.object(role_guards, "current_user", vendor):

            @role_guards.vendor_required
            def protected_view():
                return "Access Granted"

            self.assertEqual(protected_view(), "Access Granted")

    def test_student_cannot_access_vendor_route(self):
        # Create a simulated authenticated student
        student = SimpleNamespace(is_authenticated=True, role="student")

        # Simulate the current logged-in user
        with patch.object(role_guards, "current_user", student):

            @role_guards.vendor_required
            def protected_view():
                return "Access Granted"

            # Verify that access is denied with HTTP 403 error
            with self.assertRaises(Forbidden):
                protected_view()

    def test_student_can_access_student_route(self):
        # Create a simulated authenticated student
        student = SimpleNamespace(is_authenticated=True, role="student")

        # Simulate the current logged-in user
        with patch.object(role_guards, "current_user", student):

            @role_guards.student_required
            def protected_view():
                return "Access Granted"

            self.assertEqual(protected_view(), "Access Granted")

    def test_vendor_cannot_access_student_route(self):
        # Create a simulated authenticated vendor
        vendor = SimpleNamespace(is_authenticated=True, role="vendor")

        # Simulate the current logged-in user
        with patch.object(role_guards, "current_user", vendor):

            @role_guards.student_required
            def protected_view():
                return "Access Granted"

            # Verify that access is denied with HTTP 403 error
            with self.assertRaises(Forbidden):
                protected_view()

    def test_logged_out_user_cannot_access_vendor_route(self):
        # Create a simulated logged-out user
        logged_out_user = SimpleNamespace(is_authenticated=False)

        # Simulate the current logged-in user
        with patch.object(role_guards, "current_user", logged_out_user):

            @role_guards.vendor_required
            def protected_view():
                return "Access Granted"

            # Verify that access is denied with HTTP 403 error
            with self.assertRaises(Forbidden):
                protected_view()

    def test_logged_out_user_cannot_access_student_route(self):
        # Create a simulated logged-out user
        logged_out_user = SimpleNamespace(is_authenticated=False)

        # Simulate the current logged-in user
        with patch.object(role_guards, "current_user", logged_out_user):

            @role_guards.student_required
            def protected_view():
                return "Access Granted"

            # Verify that access is denied with HTTP 403 error
            with self.assertRaises(Forbidden):
                protected_view()
