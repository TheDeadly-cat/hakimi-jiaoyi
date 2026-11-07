"""Read pinned generated descriptor bytes using only Python's standard library."""
import ast
import json
from pathlib import Path

pb = Path(r'C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029\HakimiTrade-0.7.0.dev3-candidate-r4\runtime\python\Lib\site-packages\futu\common\pb')

def fields(data):
    offset = 0
    def integer():
        nonlocal offset
        result = shift = 0
        while True:
            value = data[offset]; offset += 1
            result |= (value & 127) << shift
            if not value & 128:
                return result
            shift += 7
    result = []
    while offset < len(data):
        tag = integer(); number, kind = tag >> 3, tag & 7
        if kind == 0:
            value = integer()
        elif kind == 2:
            size = integer(); value = data[offset:offset + size]; offset += size
        elif kind in (1, 5):
            size = 8 if kind == 1 else 4; value = data[offset:offset + size]; offset += size
        else:
            raise ValueError(kind)
        result.append((number, value))
    return result

result = {}
for name in ('Trd_GetAccList', 'Trd_GetFunds', 'Trd_GetPositionList', 'Trd_GetOrderList',
             'Trd_GetOrderFee', 'Trd_PlaceOrder', 'Trd_ModifyOrder', 'Trd_Common'):
    tree = ast.parse((pb / (name + '_pb2.py')).read_text(encoding='utf-8'))
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == 'AddSerializedFile')
    raw = ast.literal_eval(call.args[0])
    messages = {}
    for number, value in fields(raw):
        if number != 4:
            continue
        message = fields(value)
        title = next(value.decode() for number, value in message if number == 1)
        rows = []
        for number, value in message:
            if number != 2:
                continue
            row = dict(fields(value))
            rows.append(dict(name=row[1].decode(), number=row[3], label=row[4], type=row[5],
                             message=row.get(6, b'').decode(), default=row.get(7, b'').decode()))
        messages[title] = rows
    result[name] = messages
print(json.dumps(result, indent=2))
