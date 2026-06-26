from app.schemas.crdt import (
  PositionIdentifier,
  Character,
  compare_positions,
  generate_position_between,
  find_insert_index
)

def test_compare_positions_basic():
  pos1 = [PositionIdentifier(digit=10, site_id="A")]
  pos2 = [PositionIdentifier(digit=20, site_id="B")]

  assert compare_positions(pos1, pos2) == -1
  assert compare_positions(pos2, pos1) == 1
  assert compare_positions(pos1, pos1) == 0


def test_compare_positions_tie_breaker():
  pos1 = [PositionIdentifier(digit=10, site_id="A")]
  pos2 = [PositionIdentifier(digit=10, site_id="B")]

  assert compare_positions(pos1, pos2) == -1
  assert compare_positions(pos2, pos1) == 1


def test_compare_positions_depth():
  pos1 = [PositionIdentifier(digit=10, site_id="A")]
  pos2 = [
    PositionIdentifier(digit=10, site_id="A"),
    PositionIdentifier(digit=5, site_id="B")
  ]

  assert compare_positions(pos1, pos2) == -1


def test_generate_position_between():
  pos = generate_position_between(None, None, "Site 1")

  assert len(pos) == 1
  assert pos[0].digit == 50

  pos1 = [PositionIdentifier(digit=10, site_id="Site 1")]
  pos2 = [PositionIdentifier(digit=20, site_id="Site 2")]
  new_pos = generate_position_between(pos1, pos2, "Site 3")

  assert len(new_pos) == 1
  assert new_pos[0].digit == 15


def test_find_insert_index():
  doc = [
    Character(value="A", position=[PositionIdentifier(digit=10, site_id="S1")]),
    Character(value="C", position=[PositionIdentifier(digit=30, site_id="S2")]),
    Character(value="E", position=[PositionIdentifier(digit=50, site_id="S3")])
  ]

  char_d = Character(value="D", position=[PositionIdentifier(digit=40, site_id="S4")])

  insert_idx = find_insert_index(doc, char_d)

  assert insert_idx == 2
