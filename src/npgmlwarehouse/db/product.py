# -*- coding: utf-8 -*-
#
# Copyright © 2026 Genome Research Ltd. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from npgmlwarehouse.db.schema import SeqProductIrodsLocations, UseqProductMetrics


def get_ultimagen_target_product_records(session: Session, id_run: int):
    """
    Retrieves target Ultimagen product records for a run.

    Args:
        session (Session):
            Database session.
        id_run (int):
            Run ID as saved in tracking DB

    Returns:
        Sequence[UseqProductMetrics]:
            An iterable collection of product records related to the specified run ID.
            An empty Sequence is returned if no product record is found.
    """
    records = session.scalars(
        select(UseqProductMetrics).where(
            UseqProductMetrics.id_run == id_run,
            UseqProductMetrics.is_sequencing_control == 0,
            UseqProductMetrics.tag_index != 0,
        )
    )
    return records.all()


def create_upload_irods_location_records(
    session: Session,
    product_data: dict[dict],
    seq_platform_name: str,
    pipeline_name: str,
):
    """
    Insert product records identified by their product IDs into the iRODS location
    table `seq_product_irods_locations`. In the case of a duplicate entry in the database
    which corresponds to a duplicate unique key of `id_product` and `irods_root_collection`,
    the values are updated accordingly and the function will continue normally with no
    exception. If the duplicate record has equal values, the update for those values is ignored.

    `product_data` should have the following structure.

        product_data[`id_product`] = {
            "irods_root_collection": "/irods/path/to/collection1",
            "irods_data_relative_path": "/irods/path/to/data1",
            "irods_secondary_data_relative_path": "/irods/path/to/secondary/data1",
        }

    `irods_root_collection` is mandatory because it belongs to the unique key together with
    the `id_product`.
    `irods_data_relative_path` and `irods_secondary_data_relative_path` columns are optional.

    All input records (dictionaries) in `product_data` must have the same structure.
    It means that they must have the same column names specified under `product_data[id_product]`
    for each `id_product`. This is necessary for a correct bulk upsert operation, otherwise
    the function will fail.

    Args:
        session (Session):
            Database connection Session
        product_data (dict[dict]):
            Dictionary composed in the following way:
            key: sequencing product ID (str)
            value: Dictionary of Column (str), Value (str).
            Allowed column names:
                `irods_root_collection`, `irods_data_relative_path`, `irods_secondary_data_relative_path`
        seq_platform_name (str):
            Platform name common to all records
        pipeline_name (str):
            Pipeline name common to all records

    Returns:
        None
    """
    if not product_data:
        return

    to_insert = []
    for id_product, data in product_data.items():
        collection_path = data["irods_root_collection"]
        relative_data = data.get("irods_data_relative_path", False)
        secondary_rel_data = data.get("irods_secondary_data_relative_path", False)
        data_to_insert = {
            "id_product": id_product,
            "seq_platform_name": seq_platform_name,
            "pipeline_name": pipeline_name,
            "irods_root_collection": collection_path,
        }
        if relative_data is not False:
            data_to_insert["irods_data_relative_path"] = relative_data
        if secondary_rel_data is not False:
            data_to_insert["irods_secondary_data_relative_path"] = secondary_rel_data
        to_insert.append(data_to_insert)

    insert_query = insert(SeqProductIrodsLocations).values(to_insert)
    on_duplicate_kwargs = {
        "seq_platform_name": insert_query.inserted.seq_platform_name,
        "pipeline_name": insert_query.inserted.pipeline_name,
    }
    if relative_data is not False:
        on_duplicate_kwargs["irods_data_relative_path"] = (
            insert_query.inserted.irods_data_relative_path
        )
    if secondary_rel_data is not False:
        on_duplicate_kwargs["irods_secondary_data_relative_path"] = (
            insert_query.inserted.irods_secondary_data_relative_path
        )

    insert_on_duplicate = insert_query.on_duplicate_key_update(**on_duplicate_kwargs)
    session.execute(insert_on_duplicate)
    session.commit()
