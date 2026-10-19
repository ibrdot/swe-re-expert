"""Regression tests for the explicit confirmation required by Service Bus deletes."""

from __future__ import annotations

import contextlib
import io
import os
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "azure-servicebus-py"
    / "scripts"
    / "setup_servicebus.py"
)


class ServiceBusDeleteGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_modules = {
            name: sys.modules.get(name)
            for name in (
                "azure",
                "azure.identity",
                "azure.servicebus",
                "azure.servicebus.management",
            )
        }
        self.deleted: list[tuple[str, ...]] = []

        azure = types.ModuleType("azure")
        azure.__path__ = []
        identity = types.ModuleType("azure.identity")
        identity.DefaultAzureCredential = type("Credential", (), {})
        servicebus = types.ModuleType("azure.servicebus")
        servicebus.__path__ = []
        management = types.ModuleType("azure.servicebus.management")

        deleted = self.deleted

        class MockClient:
            @classmethod
            def from_connection_string(cls, _connection_string):
                return cls()

            def delete_queue(self, name):
                deleted.append(("queue", name))

            def delete_topic(self, name):
                deleted.append(("topic", name))

            def delete_subscription(self, topic, name):
                deleted.append(("subscription", topic, name))

        management.ServiceBusAdministrationClient = MockClient
        for name in (
            "QueueProperties",
            "TopicProperties",
            "SubscriptionProperties",
            "SqlRuleFilter",
            "CorrelationRuleFilter",
        ):
            setattr(management, name, type(name, (), {}))

        sys.modules.update(
            {
                "azure": azure,
                "azure.identity": identity,
                "azure.servicebus": servicebus,
                "azure.servicebus.management": management,
            }
        )
        self.environment = patch.dict(os.environ, {"SERVICEBUS_CONNECTION_STRING": "test-only"})
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        for name, module in self.previous_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def run_cli(self, arguments: list[str]) -> int | None:
        old_argv = sys.argv
        sys.argv = [str(SCRIPT), *arguments]
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                runpy.run_path(str(SCRIPT), run_name="__main__")
        except SystemExit as error:
            return int(error.code)
        finally:
            sys.argv = old_argv
        return None

    def test_each_delete_requires_confirmation_before_client_creation(self) -> None:
        commands = [
            (["queue", "delete", "demo-queue"], ["queue", "delete", "demo-queue", "--confirm-delete"], ("queue", "demo-queue")),
            (["topic", "delete", "demo-topic"], ["topic", "delete", "demo-topic", "--confirm-delete"], ("topic", "demo-topic")),
            (["subscription", "delete", "demo-topic", "demo-sub"], ["subscription", "delete", "demo-topic", "demo-sub", "--confirm-delete"], ("subscription", "demo-topic", "demo-sub")),
        ]
        for without_confirmation, with_confirmation, expected in commands:
            with self.subTest(command=without_confirmation):
                self.deleted.clear()
                self.assertEqual(self.run_cli(without_confirmation), 2)
                self.assertEqual(self.deleted, [])
                self.assertIsNone(self.run_cli(with_confirmation))
                self.assertEqual(self.deleted[-1], expected)


if __name__ == "__main__":
    unittest.main()
