from database.sqlite import Database

db = Database()

collection_id = db.create_collection(
    name="Test Collection",
    description="First database test",
    collection_type="test",
)

snapshot_id = db.create_snapshot(
    collection_id=collection_id,
    server=638,
    status="complete",
    parser_version="0.2.1",
    ocr_engine="EasyOCR",
    ocr_version="1.7.2",
)

ranking_type_id = db.get_or_create_ranking_type("alliance_power")

entity_id = db.get_or_create_entity(
    entity_type="alliance",
    tag="Hpn",
    name="Club Happiness",
)

db.insert_ranking_entry(
    snapshot_id=snapshot_id,
    ranking_type_id=ranking_type_id,
    entity_id=entity_id,
    rank=1,
    value=29138866749,
)

print("DB-Test erfolgreich.")