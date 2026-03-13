from time import sleep

from pytest import mark as m
from sqlalchemy import select

from npgmlwarehouse.db.product import (
    create_upload_irods_location_records,
    get_ultimagen_target_product_records,
)
from npgmlwarehouse.db.schema import SeqProductIrodsLocations


def select_locations_byplatform(platform_name: str):
    return select(SeqProductIrodsLocations).where(
        SeqProductIrodsLocations.seq_platform_name == platform_name,
    )


@m.describe("TestProduct")
class TestProduct(object):
    @m.context("When product records are present in `useq_product_metrics` table")
    @m.it("Retrieves the product records from MLWH")
    def test_get_product_records(self, mlwh_session):
        records = get_ultimagen_target_product_records(mlwh_session, 51579)
        assert len(records) == 4

    @m.context("When there is no product records in `useq_product_metrics` table")
    @m.it("Returns an empty collection")
    def test_get_product_records_no_record(self, mlwh_session):
        records = get_ultimagen_target_product_records(mlwh_session, 40000)
        assert len(records) == 0

    @m.context("When inserting a product record in `seq_product_irods_locations`")
    @m.it("Location record is present and correct")
    def test_create_upload_irods_location_records(self, mlwh_session):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        id_product = "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32"
        coll = "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
        prod_coll = {id_product: {"irods_root_collection": coll}}
        create_upload_irods_location_records(
            mlwh_session, prod_coll, platform, pipeline
        )

        record = mlwh_session.scalars(
            select(SeqProductIrodsLocations).where(
                SeqProductIrodsLocations.id_product == id_product,
            )
        ).first()
        assert record.id_product == id_product
        assert record.seq_platform_name == platform
        assert record.pipeline_name == pipeline
        assert record.irods_root_collection == coll

    @m.context("When using an empty collection in create_upload_irods_location")
    @m.it("Function returns early")
    def test_create_upload_irods_location_empty_input(self, mlwh_session):
        platform = "Ultimagen"
        pipeline = "instrument_output"

        create_upload_irods_location_records(mlwh_session, {}, platform, pipeline)

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 0

    @m.context(
        "When inserting multiple product records in `seq_product_irods_locations`"
    )
    @m.it("Location records are present")
    def test_create_upload_irods_location_records_multiple(self, mlwh_session):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        prod_coll = {
            "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32": {
                "irods_root_collection": "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
            },
            "4710c1002d44c4dee326f91a663e223e6e8f64fe866ab84b7a5f264ae0028396": {
                "irods_root_collection": "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s2-Z0002-CATGTGCAGCCATCGAT"
            },
        }
        create_upload_irods_location_records(
            mlwh_session, prod_coll, platform, pipeline
        )

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 2

    @m.context("When inserting a product record in `seq_product_irods_locations`")
    @m.context("When a product ID is already present")
    @m.context("When the iRODS collection is the same")
    @m.context("When the duplicate record has the same values")
    @m.it("Ignores the record update")
    def test_create_upload_irods_location_records_duplicate_unique_key(
        self, mlwh_session
    ):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        id_product = "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32"
        coll = "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
        mlwh_session.add(
            SeqProductIrodsLocations(
                id_product=id_product,
                seq_platform_name=platform,
                pipeline_name=pipeline,
                irods_root_collection=coll,
            )
        )
        mlwh_session.commit()
        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1

        create_upload_irods_location_records(
            mlwh_session,
            {id_product: {"irods_root_collection": coll}},
            platform,
            pipeline,
        )

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1
        record = records.pop()
        assert record.id_product == id_product
        assert record.irods_root_collection == coll

    @m.context(
        "When inserting multiple product records in `seq_product_irods_locations`"
    )
    @m.context("When one of them has a duplicate unique key")
    @m.context("When the duplicate record has the same values")
    @m.it("Ignores the duplicate record insertion and continues")
    def test_create_upload_irods_location_records_continues_on_duplicate_unique_key(
        self, mlwh_session
    ):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        id_product_dup = (
            "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32"
        )
        coll_dup = "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
        prod_coll = {
            id_product_dup: {"irods_root_collection": coll_dup},
            "4710c1002d44c4dee326f91a663e223e6e8f64fe866ab84b7a5f264ae0028396": {
                "irods_root_collection": "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s2-Z0002-CATGTGCAGCCATCGAT"
            },
        }
        mlwh_session.add(
            SeqProductIrodsLocations(
                id_product=id_product_dup,
                seq_platform_name=platform,
                pipeline_name=pipeline,
                irods_root_collection=coll_dup,
            )
        )
        mlwh_session.commit()
        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1

        create_upload_irods_location_records(
            mlwh_session, prod_coll, platform, pipeline
        )

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 2
        for record in records:
            assert record.id_product in prod_coll
            assert (
                record.irods_root_collection
                == prod_coll[record.id_product]["irods_root_collection"]
            )

    @m.context("When inserting a product record in `seq_product_irods_locations`")
    @m.context("When the unique key is duplicated")
    @m.context("When the new pipeline name is different")
    @m.it("Updates the pipeline name")
    def test_create_upload_irods_location_records_update_pipeline(self, mlwh_session):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        newpipeline = "ultimagen_pipeline"
        id_product = "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32"
        coll = "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
        mlwh_session.add(
            SeqProductIrodsLocations(
                id_product=id_product,
                seq_platform_name=platform,
                pipeline_name=pipeline,
                irods_root_collection=coll,
            )
        )
        mlwh_session.commit()
        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1

        create_upload_irods_location_records(
            mlwh_session,
            {id_product: {"irods_root_collection": coll}},
            platform,
            newpipeline,
        )

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1
        record = records.pop()
        assert record.id_product == id_product
        assert record.irods_root_collection == coll
        assert record.pipeline_name == newpipeline

    @m.context("When inserting a product record in `seq_product_irods_locations`")
    @m.context("When the unique key is duplicated")
    @m.context("When the pipeline name is the same")
    @m.it("Ignores the row update")
    def test_create_upload_irods_location_records_duplicate_unique_key_same_pipeline(
        self, mlwh_session
    ):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        id_product = "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32"
        coll = "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
        mlwh_session.add(
            SeqProductIrodsLocations(
                id_product=id_product,
                seq_platform_name=platform,
                pipeline_name=pipeline,
                irods_root_collection=coll,
            )
        )
        mlwh_session.commit()
        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1
        last_changed = records.pop().last_changed

        sleep(2)
        create_upload_irods_location_records(
            mlwh_session,
            {id_product: {"irods_root_collection": coll}},
            platform,
            pipeline,
        )

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1
        record = records.pop()
        assert record.last_changed == last_changed

    @m.context("When inserting a product record in `seq_product_irods_locations`")
    @m.context("When the unique key is duplicated")
    @m.context("When the `irods_data_relative_path` update is not requested")
    @m.context("When the `irods_secondary_data_relative_path` update is not requested")
    @m.it("Does not issue the update to the record")
    def test_create_upload_irods_location_records_duplicate_unique_key_part_input(
        self, mlwh_session
    ):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        id_product = "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32"
        coll = "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
        data_relative_path = (
            "434523-1-Z0025-CTCGAGATTGATGAT_S1_L001_R2_001_sample.fastq.gz"
        )
        secondary_data_relative_path = "434523-1-Z0025-CTCGAGATTGATGAT.csv"
        mlwh_session.add(
            SeqProductIrodsLocations(
                id_product=id_product,
                seq_platform_name=platform,
                pipeline_name=pipeline,
                irods_root_collection=coll,
                irods_data_relative_path=data_relative_path,
                irods_secondary_data_relative_path=secondary_data_relative_path,
            )
        )
        mlwh_session.commit()
        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1
        last_changed = records.pop().last_changed

        sleep(2)
        create_upload_irods_location_records(
            mlwh_session,
            {id_product: {"irods_root_collection": coll}},
            platform,
            pipeline,
        )

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1
        record = records.pop()
        assert record.last_changed == last_changed
        assert record.irods_data_relative_path == data_relative_path
        assert record.irods_secondary_data_relative_path == secondary_data_relative_path

    @m.context("When inserting a product record in `seq_product_irods_locations`")
    @m.context("When the unique key is duplicated")
    @m.context("When the `irods_data_relative_path` is to be updated with NULL")
    @m.context(
        "When the `irods_secondary_data_relative_path` is to be updated with NULL"
    )
    @m.it("Inserts NULL in the mentioned columns")
    def test_create_upload_irods_location_records_duplicate_unique_key_update_null(
        self, mlwh_session
    ):
        platform = "Ultimagen"
        pipeline = "instrument_output"
        id_product = "244c6fce98d0261f25cedd81dbfcfc08e2207c954c8e25f471f5b6aaca144a32"
        coll = "/testZone/home/irods/ultimagen/434895-20260110_0323/434895-s1-Z0001-CAGCTCGAATGCGAT"
        data_relative_path = (
            "434523-1-Z0025-CTCGAGATTGATGAT_S1_L001_R2_001_sample.fastq.gz"
        )
        secondary_data_relative_path = "434523-1-Z0025-CTCGAGATTGATGAT.csv"
        mlwh_session.add(
            SeqProductIrodsLocations(
                id_product=id_product,
                seq_platform_name=platform,
                pipeline_name=pipeline,
                irods_root_collection=coll,
                irods_data_relative_path=data_relative_path,
                irods_secondary_data_relative_path=secondary_data_relative_path,
            )
        )
        mlwh_session.commit()
        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1

        create_upload_irods_location_records(
            mlwh_session,
            {
                id_product: {
                    "irods_root_collection": coll,
                    "irods_data_relative_path": None,
                    "irods_secondary_data_relative_path": None,
                }
            },
            platform,
            pipeline,
        )

        records = mlwh_session.scalars(select_locations_byplatform(platform)).all()
        assert len(records) == 1
        record = records.pop()
        assert record.irods_data_relative_path == None
        assert record.irods_secondary_data_relative_path == None
