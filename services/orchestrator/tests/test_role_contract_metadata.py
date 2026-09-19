from __future__ import annotations

import unittest

from app.coordination.models import WritePermission
from app.coordination.roles import ROLE_REGISTRY, get_role_contract


class RoleContractMetadataTests(unittest.TestCase):
    def test_every_canonical_role_declares_scope_and_performance_signals(self) -> None:
        self.assertGreaterEqual(len(ROLE_REGISTRY), 15)
        for role_id, contract in ROLE_REGISTRY.items():
            with self.subTest(role=role_id):
                self.assertEqual(role_id, contract.id)
                self.assertTrue(contract.writable_scope)
                self.assertTrue(contract.performance_signals)
                self.assertTrue(contract.handoff_targets)
                self.assertTrue(contract.allowed_tools)
                if contract.write_permission is WritePermission.READ_ONLY:
                    self.assertEqual(contract.writable_scope, ("none",))
                else:
                    self.assertIn("assigned_scope", contract.writable_scope)
                serialized = contract.as_dict()
                self.assertIn("writable_scope", serialized)
                self.assertIn("performance_signals", serialized)
                self.assertIn("handoff_targets", serialized)

    def test_sales_contract_is_read_only_and_non_commit_capable(self) -> None:
        sales = get_role_contract("sales")
        self.assertEqual(sales.id, "sales")
        self.assertEqual(sales.write_permission, WritePermission.READ_ONLY)
        self.assertEqual(sales.writable_scope, ("none",))
        self.assertEqual(sales.handoff_targets, ("requirements", "project_manager"))
        self.assertIn("OpportunityBrief", sales.output_contract)
        self.assertIn("unauthorized_commitment_attempts", sales.performance_signals)

    def test_aliases_return_the_same_enriched_contract(self) -> None:
        self.assertEqual(get_role_contract("verifier").id, "tester")
        self.assertTrue(get_role_contract("verifier").performance_signals)
        self.assertTrue(get_role_contract("backend").writable_scope)


if __name__ == "__main__":
    unittest.main()
