from re import search
from unittest import mock

import botocore
from boto3 import client
from moto import mock_rds

from tests.providers.aws.audit_info_utils import (
    AWS_ACCOUNT_NUMBER,
    AWS_REGION_US_EAST_1,
    set_mocked_aws_audit_info,
)

make_api_call = botocore.client.BaseClient._make_api_call


def mock_make_api_call(self, operation_name, kwarg):
    if operation_name == "DescribeDBEngineVersions":
        return {
            "DBEngineVersions": [
                {
                    "Engine": "mysql",
                    "EngineVersion": "8.0.32",
                    "DBEngineDescription": "description",
                    "DBEngineVersionDescription": "description",
                },
            ]
        }
    # if operation_name == "DescribeDBClusterSnapshotAttributes":
    #     return {
    #         "DBClusterSnapshotAttributesResult": {
    #             "DBClusterSnapshotIdentifier": "test-snapshot",
    #             "DBClusterSnapshotAttributes": [
    #                 {"AttributeName": "restore", "AttributeValues": ["all"]}
    #             ],
    #         }
    #     }
    return make_api_call(self, operation_name, kwarg)


class Test_rds_snapshots_public_access:
    @mock_rds
    @mock.patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
    def test_rds_no_snapshots(self):
        from prowler.providers.aws.services.rds.rds_service import RDS

        audit_info = set_mocked_aws_audit_info([AWS_REGION_US_EAST_1])

        with mock.patch(
            "prowler.providers.aws.lib.audit_info.audit_info.current_audit_info",
            new=audit_info,
        ):
            with mock.patch(
                "prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access.rds_client",
                new=RDS(audit_info),
            ):
                # Test Check
                from prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access import (
                    rds_snapshots_public_access,
                )

                check = rds_snapshots_public_access()
                result = check.execute()

                assert len(result) == 0

    @mock_rds
    @mock.patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
    def test_rds_private_snapshot(self):
        conn = client("rds", region_name=AWS_REGION_US_EAST_1)
        conn.create_db_instance(
            DBInstanceIdentifier="db-primary-1",
            AllocatedStorage=10,
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
        )

        conn.create_db_snapshot(
            DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
        )

        from prowler.providers.aws.services.rds.rds_service import RDS

        audit_info = set_mocked_aws_audit_info([AWS_REGION_US_EAST_1])

        with mock.patch(
            "prowler.providers.aws.lib.audit_info.audit_info.current_audit_info",
            new=audit_info,
        ):
            with mock.patch(
                "prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access.rds_client",
                new=RDS(audit_info),
            ):
                # Test Check
                from prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access import (
                    rds_snapshots_public_access,
                )

                check = rds_snapshots_public_access()
                result = check.execute()

                assert len(result) == 1
                assert result[0].status == "PASS"
                assert search(
                    "is not shared",
                    result[0].status_extended,
                )
                assert result[0].resource_id == "snapshot-1"

    @mock_rds
    @mock.patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
    def test_rds_public_snapshot(self):
        conn = client("rds", region_name=AWS_REGION_US_EAST_1)
        conn.create_db_instance(
            DBInstanceIdentifier="db-primary-1",
            AllocatedStorage=10,
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
        )

        conn.create_db_snapshot(
            DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
        )

        from prowler.providers.aws.services.rds.rds_service import RDS

        audit_info = set_mocked_aws_audit_info([AWS_REGION_US_EAST_1])

        with mock.patch(
            "prowler.providers.aws.lib.audit_info.audit_info.current_audit_info",
            new=audit_info,
        ):
            with mock.patch(
                "prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access.rds_client",
                new=RDS(audit_info),
            ) as service_client:
                # Test Check
                from prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access import (
                    rds_snapshots_public_access,
                )

                service_client.db_snapshots[0].public = True
                check = rds_snapshots_public_access()
                result = check.execute()

                assert len(result) == 1
                assert result[0].status == "FAIL"
                assert search(
                    "is public",
                    result[0].status_extended,
                )
                assert result[0].resource_id == "snapshot-1"
                assert result[0].region == AWS_REGION_US_EAST_1
                assert (
                    result[0].resource_arn
                    == f"arn:aws:rds:{AWS_REGION_US_EAST_1}:{AWS_ACCOUNT_NUMBER}:snapshot:snapshot-1"
                )
                assert result[0].resource_tags == []

    @mock_rds
    @mock.patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
    def test_rds_cluster_private_snapshot(self):
        conn = client("rds", region_name=AWS_REGION_US_EAST_1)
        conn.create_db_cluster(
            DBClusterIdentifier="db-primary-1",
            AllocatedStorage=10,
            Engine="postgres",
            DBClusterInstanceClass="db.m1.small",
            MasterUsername="root",
            MasterUserPassword="hunter2000",
        )

        conn.create_db_cluster_snapshot(
            DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
        )
        from prowler.providers.aws.services.rds.rds_service import RDS

        audit_info = set_mocked_aws_audit_info([AWS_REGION_US_EAST_1])

        with mock.patch(
            "prowler.providers.aws.lib.audit_info.audit_info.current_audit_info",
            new=audit_info,
        ):
            with mock.patch(
                "prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access.rds_client",
                new=RDS(audit_info),
            ):
                # Test Check
                from prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access import (
                    rds_snapshots_public_access,
                )

                check = rds_snapshots_public_access()
                result = check.execute()

                assert len(result) == 1
                assert result[0].status == "PASS"
                assert search(
                    "is not shared",
                    result[0].status_extended,
                )
                assert result[0].resource_id == "snapshot-1"
                assert result[0].region == AWS_REGION_US_EAST_1
                assert (
                    result[0].resource_arn
                    == f"arn:aws:rds:{AWS_REGION_US_EAST_1}:{AWS_ACCOUNT_NUMBER}:cluster-snapshot:snapshot-1"
                )
                assert result[0].resource_tags == []

    @mock_rds
    @mock.patch("botocore.client.BaseClient._make_api_call", new=mock_make_api_call)
    def test_rds_cluster_public_snapshot(self):
        conn = client("rds", region_name=AWS_REGION_US_EAST_1)
        conn.create_db_cluster(
            DBClusterIdentifier="db-primary-1",
            AllocatedStorage=10,
            Engine="postgres",
            DBClusterInstanceClass="db.m1.small",
            MasterUsername="root",
            MasterUserPassword="hunter2000",
        )

        conn.create_db_cluster_snapshot(
            DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
        )
        from prowler.providers.aws.services.rds.rds_service import RDS

        audit_info = set_mocked_aws_audit_info([AWS_REGION_US_EAST_1])

        with mock.patch(
            "prowler.providers.aws.lib.audit_info.audit_info.current_audit_info",
            new=audit_info,
        ):
            with mock.patch(
                "prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access.rds_client",
                new=RDS(audit_info),
            ) as service_client:
                # Test Check
                from prowler.providers.aws.services.rds.rds_snapshots_public_access.rds_snapshots_public_access import (
                    rds_snapshots_public_access,
                )

                service_client.db_cluster_snapshots[0].public = True
                check = rds_snapshots_public_access()
                result = check.execute()

                assert len(result) == 1
                assert result[0].status == "FAIL"
                assert search(
                    "is public",
                    result[0].status_extended,
                )
                assert result[0].resource_id == "snapshot-1"
                assert result[0].region == AWS_REGION_US_EAST_1
                assert (
                    result[0].resource_arn
                    == f"arn:aws:rds:{AWS_REGION_US_EAST_1}:{AWS_ACCOUNT_NUMBER}:cluster-snapshot:snapshot-1"
                )
                assert result[0].resource_tags == []
