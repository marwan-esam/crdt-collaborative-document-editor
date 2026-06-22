import math
from pydantic import BaseModel

class PositionIdentifier(BaseModel):
  digit: int
  site_id: str


class Character(BaseModel):
  value: str
  position: list[PositionIdentifier]


BASE = 100


def generate_position_between(
    pos1: list[PositionIdentifier] | None,
    pos2: list[PositionIdentifier] | None,
    new_site_id: str
) -> list[PositionIdentifier]:
  
  if not pos1 and not pos2:
    return [PositionIdentifier(digit=BASE // 2, site_id=new_site_id)]
  
  new_pos = []
  index = 0

  while True:
    if pos1 and index < len(pos1):
      node1 = pos1[index]
    else:
      node1 = PositionIdentifier(digit=0, site_id=pos1[-1].site_id if pos1 else "")

    if pos2 and index < len(pos2):
      node2 = pos2[index]
    else:
      node2 = PositionIdentifier(digit=BASE, site_id=pos2[-1].site_id if pos2 else "")

    digit1 = node1.digit
    digit2 = node2.digit
    gap = digit2 - digit1

    if gap > 1:
      new_digit = digit1 + math.floor(gap / 2)
      new_pos.append(PositionIdentifier(digit=new_digit, site_id=new_site_id))
      return new_pos
    
    elif gap == 1:
      new_pos.append(node1)

    elif gap == 0:
      if node1.site_id < node2.site_id:
        new_pos.append(node1)
      elif node1.site_id == node2.site_id:
        new_pos.append(node1)
      else:
        raise ValueError("CRDT Order Violation: pos1 is greater than pos2")
      
    index += 1


def compare_positions(pos1: list[PositionIdentifier], pos2: list[PositionIdentifier]) -> int:
  max_length = max(len(pos1), len(pos2))

  for i in range(max_length):
    if i >= len(pos1):
      return -1
    
    if i >= len(pos2):
      return 1
    
    node1 = pos1[i]
    node2 = pos2[i]

    if node1.digit < node2.digit:
      return -1
    if node1.digit > node2.digit:
      return 1
    
    if node1.site_id < node2.site_id:
      return -1
    if node1.site_id > node2.site_id:
      return 1
    
  return 0


def find_insert_index(document: list[Character], new_char: Character) -> int:
  low = 0
  high = len(document) - 1
  while low <= high:
    mid = (low + high) // 2
    comp = compare_positions(new_char.position, document[mid].position)

    if comp == -1:
      high = mid - 1
    
    elif comp == 1:
      low = mid + 1

    else:
      return mid
    
  return low

    